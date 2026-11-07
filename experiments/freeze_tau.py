"""Freeze LEAP's threshold tau_th from Exp C with a pre-registered rule, and write the Exp B config for LEAP.

Rule (DECISIONS D-016, fixed before the sweep finished): compute the mean PDR over the tuning seeds for each
tau_th; among the values whose mean PDR is within ``--tolerance`` (default 0.005, i.e. 0.5 percentage points)
of the best, choose the smallest (closest to Greedy, fewest proactive switches). Refuses to run unless every
expected tuning run finished, so a partial sweep can never freeze the threshold.

Usage::

    python experiments/freeze_tau.py --results <dir>/exp_c_tuning --out experiments/configs/exp_b_leap.yaml \
        --summary docs/tau_freeze.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

TAUS_S = (0.25, 0.5, 1.0, 2.0, 4.0)
SEEDS = (100, 101, 102)

CONFIG_TEMPLATE = """# Experiment B, part 2: LEAP-select (A1) and LEAP (A2) (SPEC §7, §8; R8, R9).
# tau_th = {tau:g} s, frozen from Exp C by the pre-registered rule of DECISIONS D-016 (experiments/freeze_tau.py).
# Same 11 configurations and seeds 1-3 as Exp A (Greedy, GRAd reused) and as the reactive control (part 1).
name: exp_b_comparison
seeds: [1, 2, 3]
fixed:
  sim_time_s: 30
  traffic_start_s: 2
  traffic_end_s: 27
  energy: "off"
reference: {{n: 30, speed: 10, rate: 1}}
sweeps:
  n: [10, 20, 30, 40, 50]
  speed: [5, 10, 15, 20]
  rate: [0.5, 1, 2, 5]
variants:
  - {{label: leap_select, protocol: leap, params: {{tau_th_s: {tau:g}, repair: "off"}}}}
  - {{label: leap, protocol: leap, params: {{tau_th_s: {tau:g}, repair: predictive}}}}
"""


def collect(results: Path) -> dict[float, list[float]]:
    pdr: dict[float, list[float]] = {}
    for tau in TAUS_S:
        values = []
        for seed in SEEDS:
            path = results / f"leap_tau{tau:g}" / f"n30_v20_r1_s{seed}.json"
            if not path.exists():
                sys.exit(f"missing tuning run {path}: refusing to freeze tau_th")
            values.append(json.loads(path.read_text())["metrics"]["pdr"])
        pdr[tau] = values
    return pdr


def choose(pdr: dict[float, list[float]], tolerance: float) -> float:
    means = {tau: statistics.mean(v) for tau, v in pdr.items()}
    best = max(means.values())
    return min(tau for tau, m in means.items() if m >= best - tolerance)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--summary", type=Path, required=True)
    ap.add_argument("--tolerance", type=float, default=0.005)
    a = ap.parse_args()
    pdr = collect(a.results)
    tau = choose(pdr, a.tolerance)
    greedy = [
        json.loads((a.results / "greedy" / f"n30_v20_r1_s{s}.json").read_text())["metrics"]["pdr"]
        for s in SEEDS
    ]
    summary = {
        "rule": "smallest tau_th with mean PDR within tolerance of the best (D-016)",
        "tolerance": a.tolerance,
        "seeds": list(SEEDS),
        "config": {"n": 30, "speed": 20, "rate": 1},
        "pdr_by_tau": {f"{t:g}": v for t, v in pdr.items()},
        "mean_pdr_by_tau": {f"{t:g}": statistics.mean(v) for t, v in pdr.items()},
        "greedy_pdr": greedy,
        "chosen_tau_th_s": tau,
    }
    a.out.write_text(CONFIG_TEMPLATE.format(tau=tau))
    a.summary.write_text(json.dumps(summary, indent=1) + "\n")
    print(f"tau_th frozen at {tau:g} s; mean PDR by tau: {summary['mean_pdr_by_tau']}")


if __name__ == "__main__":
    main()
