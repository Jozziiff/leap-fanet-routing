"""Run an experiment defined in a YAML file: every (protocol variant, configuration, seed), in parallel.

Each simulation runs in its own fresh process (``run_one.py``, UPSTREAM_FACTS M4). Finished runs are
skipped, so an interrupted sweep resumes where it stopped. ``--shard i/K`` splits the run list between
K machines with the same deterministic, cost-balanced assignment on every machine.

YAML format::

    name: exp_a_diagnostic
    seeds: [1, 2, 3]
    fixed: {sim_time_s: 30, traffic_start_s: 2, traffic_end_s: 27, energy: "off"}
    reference: {n: 30, speed: 10, rate: 1}
    sweeps: {n: [10, 20, 30, 40, 50], speed: [5, 10, 15, 20], rate: [0.5, 1, 2, 5]}
    variants:
      - greedy                                   # label = protocol name
      - {label: leap, protocol: leap, params: {tau_th_s: 1.0}}

Configurations are one-factor-at-a-time around ``reference`` (SPEC §8.1); a ``configs`` list of explicit
dicts can be given instead of ``sweeps``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
RUN_ONE = REPO / "experiments" / "run_one.py"

# Wall-time model from the Phase-0 benchmark (LAB_NOTEBOOK 2026-11-07): seconds per 30-s run.
COST_FACTOR = {"grad": 3.5}


@dataclass(frozen=True)
class Run:
    label: str
    protocol: str
    params: str  # JSON
    n: int
    speed: float
    rate: float
    seed: int
    fixed: tuple = field(default=())

    @property
    def cost(self) -> float:
        return max(35.0 * self.n - 97.0, 60.0) * COST_FACTOR.get(self.protocol, 1.0)

    def out_path(self, root: Path) -> Path:
        return root / self.label / f"n{self.n}_v{self.speed:g}_r{self.rate:g}_s{self.seed}.json"

    def command(self, out: Path) -> list[str]:
        cmd = [
            sys.executable,
            "-W",
            "ignore",
            str(RUN_ONE),
            "--protocol",
            self.protocol,
            "--params",
            self.params,
            "--n",
            str(self.n),
            "--speed",
            str(self.speed),
            "--rate",
            str(self.rate),
            "--seed",
            str(self.seed),
            "--out",
            str(out),
            "--events",
            str(out.with_suffix(".events.jsonl.gz")),
        ]
        for key, value in self.fixed:
            cmd += [f"--{key.replace('_', '-')}", str(value)]
        return cmd


def expand(spec: dict) -> list[Run]:
    """All runs of an experiment, without duplicates, in a stable order."""
    if "configs" in spec:
        configs = [dict(c) for c in spec["configs"]]
    else:
        ref = spec["reference"]
        configs = []
        for var, values in spec["sweeps"].items():
            for value in values:
                c = dict(ref)
                c[var] = value
                if c not in configs:
                    configs.append(c)
    fixed = tuple(sorted((spec.get("fixed") or {}).items()))
    runs: list[Run] = []
    for v in spec["variants"]:
        v = {"label": v, "protocol": v} if isinstance(v, str) else v
        params = json.dumps(v.get("params", {}), sort_keys=True)
        for c in configs:
            for seed in spec["seeds"]:
                r = Run(
                    v["label"],
                    v["protocol"],
                    params,
                    int(c["n"]),
                    float(c["speed"]),
                    float(c["rate"]),
                    int(seed),
                    fixed,
                )
                if r not in runs:
                    runs.append(r)
    return runs


def shard(runs: list[Run], index: int, count: int) -> list[Run]:
    """Longest-processing-time assignment of runs to ``count`` machines; returns machine ``index``'s runs."""
    loads = [0.0] * count
    mine: list[Run] = []
    for r in sorted(runs, key=lambda r: (-r.cost, r.label, r.n, r.speed, r.rate, r.seed)):
        k = loads.index(min(loads))
        loads[k] += r.cost
        if k == index:
            mine.append(r)
    return mine


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config", type=Path)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--shard", default="0/1", help="i/K: run machine i's share of K (0-based)")
    ap.add_argument("--out-root", type=Path, default=REPO / "results" / "raw")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    spec = yaml.safe_load(a.config.read_text())
    root = a.out_root / spec["name"]
    index, count = (int(x) for x in a.shard.split("/"))
    runs = shard(expand(spec), index, count)
    todo = [r for r in runs if not r.out_path(root).exists()]
    est_h = sum(r.cost for r in todo) / a.workers / 3600
    print(
        f"{spec['name']}: shard {index}/{count}: {len(runs)} runs, {len(todo)} to do, "
        f"estimated {est_h:.1f} h with {a.workers} workers",
        flush=True,
    )
    if a.dry_run or not todo:
        return

    logs = root / "_logs"
    logs.mkdir(parents=True, exist_ok=True)

    def launch(r: Run) -> tuple[Run, int, float]:
        out = r.out_path(root)
        out.parent.mkdir(parents=True, exist_ok=True)
        log = logs / f"{r.label}_{out.stem}.log"
        t0 = time.time()
        with log.open("w") as fh:
            rc = subprocess.run(
                r.command(out), check=False, cwd=logs, stdout=fh, stderr=subprocess.STDOUT
            ).returncode
        return r, rc, time.time() - t0

    t_start = time.time()
    done = failed = 0
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futures = [pool.submit(launch, r) for r in sorted(todo, key=lambda r: -r.cost)]
        for fut in as_completed(futures):
            r, rc, dt = fut.result()
            done += 1
            failed += rc != 0
            elapsed = (time.time() - t_start) / 3600
            print(
                f"[{done}/{len(todo)}] {'OK ' if rc == 0 else 'ERR'} {r.label} {r.out_path(root).stem} "
                f"{dt:.0f}s | elapsed {elapsed:.2f} h",
                flush=True,
            )
    print(f"finished: {done - failed} ok, {failed} failed", flush=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
