"""Analyse Phase-0 traced runs to confirm UPSTREAM_FACTS M20, M22 and M26.

Usage::

    python check_facts.py --m20 RUN.json [RUN.json ...]
    python check_facts.py --m22 RUN_A.json RUN_B.json [RUN_C.json ...]
    python check_facts.py --m26 RUN.json [RUN.json ...]

Each RUN.json is a result written by ``harness.py --trace``.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def check_m20(paths: list[Path]) -> None:
    """Upstream hop count (TTL at destination) vs true hop count (distinct senders)."""
    for p in paths:
        r = _load(p)
        deliv = r["trace"]["deliv"]
        ttl = [v[0] for v in deliv.values()]
        hops = [v[1] for v in deliv.values()]
        inflated = sum(t > h for t, h in zip(ttl, hops))
        under = sum(t < h for t, h in zip(ttl, hops))
        excess = Counter(t - h for t, h in zip(ttl, hops))
        n = len(deliv)
        print(
            f"[M20] {p.parent.name}: delivered={n}  mean TTL-at-dst={sum(ttl) / n:.3f}  "
            f"mean true hops={sum(hops) / n:.3f}  upstream hop_cnt={r['hop_cnt_upstream']:.3f}"
        )
        print(
            f"      packets with TTL > true hops: {inflated} ({100 * inflated / n:.1f} %), "
            f"TTL < true hops: {under};  distribution of (TTL - hops): {dict(sorted(excess.items()))}"
        )


def check_m22(paths: list[Path]) -> None:
    """Same seed, different protocols: traffic and trajectories identical? MAC draws?"""
    runs = [_load(p) for p in paths]
    names = [f"{r['args']['routing']}" for r in runs]
    ref, ref_name = runs[0], names[0]
    ref_gen = [(g[0], g[1], g[2]) for g in ref["trace"]["gen"]]
    ref_traj = ref["trace"]["traj"]
    for r, name in zip(runs[1:], names[1:]):
        gen = [(g[0], g[1], g[2]) for g in r["trace"]["gen"]]
        same_gen = gen == ref_gen
        n_cmp = min(len(r["trace"]["traj"]), len(ref_traj))
        max_dev = 0.0
        for a, b in zip(ref_traj[:n_cmp], r["trace"]["traj"][:n_cmp]):
            assert a[0] == b[0]
            for pa, pb in zip(a[1:], b[1:]):
                max_dev = max(max_dev, max(abs(x - y) for x, y in zip(pa, pb)))
        ch_ref = [g[4] for g in ref["trace"]["gen"]]
        ch = [g[4] for g in r["trace"]["gen"]]
        k = min(len(ch), len(ch_ref))
        ch_diff = sum(x != y for x, y in zip(ch_ref[:k], ch[:k]))
        print(
            f"[M22] {ref_name} vs {name}: generated {len(ref_gen)} vs {len(gen)}; "
            f"(t, src, dst) sequences identical: {same_gen}"
        )
        print(
            f"      trajectories: {n_cmp} samples x {len(ref_traj[0]) - 1} drones, "
            f"max |coord diff| = {max_dev:.3e} m"
        )
        print(
            f"      sub-channel of data packets differs for {ch_diff}/{k} packets "
            f"(rng_channel_assignment not paired)"
        )


def check_m26(paths: list[Path]) -> None:
    """Time at which each drone enters sleep with the default energy model."""
    for p in paths:
        r = _load(p)
        sleep = r["trace"]["sleep_s"]
        n = r["args"]["n"]
        times = sorted(sleep.values())
        last_gen = max((g[0] for g in r["trace"]["gen"]), default=0) / 1e6
        rng = f"{times[0]:.2f}-{times[-1]:.2f} s" if times else "none"
        print(
            f"[M26] speed={r['args']['speed']} m/s energy={r['args']['energy']}: "
            f"{len(sleep)}/{n} drones asleep, first-detected sleep times {rng}; "
            f"last packet generated at {last_gen:.2f} s; PDR={r['pdr_pct']:.1f} %"
        )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--m20", nargs="+", type=Path, default=[])
    ap.add_argument("--m22", nargs="+", type=Path, default=[])
    ap.add_argument("--m26", nargs="+", type=Path, default=[])
    a = ap.parse_args()
    if a.m20:
        check_m20(a.m20)
    if a.m22:
        check_m22(a.m22)
    if a.m26:
        check_m26(a.m26)


if __name__ == "__main__":
    main()
