"""Collect per-run result JSONs into one tidy table (one row per run).

Usage::

    python -m analysis.aggregate results/raw/exp_a_diagnostic [more dirs ...] --out results/exp_a.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

LOSS_CAUSES = ("LINK_BREAK", "COLLISION", "NO_ROUTE", "QUEUE_OVERFLOW", "TTL", "EXPIRED", "DISCARD", "OTHER")
SCALARS = (
    "generated",
    "delivered",
    "in_flight",
    "lost",
    "pdr",
    "delay_mean_ms",
    "delay_p95_ms",
    "hops_true_mean",
    "hops_upstream_mean",
    "lbr_all",
    "lbr_vs_collision",
    "loss_link_break_per_generated",
    "route_computations",
    "rr",
    "tx_data_attempts",
    "ack_timeouts",
    "nrl_upstream",
    "control_packets_upstream",
    "control_tx_frames",
    "control_tx_bits",
    "collision_num_upstream",
)


def row_from_result(path: Path) -> dict:
    r = json.loads(path.read_text())
    c, m = r["config"], r["metrics"]
    row = {
        "experiment": path.parent.parent.name,
        "label": path.parent.name,
        "protocol": c["protocol"],
        "params": c["params"],
        "n": c["n"],
        "speed": c["speed"],
        "rate": c["rate"],
        "seed": c["seed"],
        "wall_s": r["meta"]["wall_s"],
        "commit": (r["meta"]["repo"] or {}).get("commit"),
        "dirty": (r["meta"]["repo"] or {}).get("dirty"),
    }
    row.update({k: m.get(k) for k in SCALARS})
    for cause in LOSS_CAUSES:
        count = m["losses"].get(cause, 0)
        row[f"loss_{cause}"] = count
        row[f"share_{cause}"] = count / m["lost"] if m["lost"] else None
    recomp = m.get("recomputations", {})
    for kind in ("WAIT_RETRY", "DISCOVERY", "RETRY_SWITCH"):
        row[f"recomp_{kind}"] = recomp.get(kind, 0)
    for kind, count in (m.get("leap_events") or {}).items():
        row[f"leap_{kind}"] = count
    pred = m.get("prediction") or {}
    for key in (
        "precision",
        "recall",
        "lead_time_mean_s",
        "lead_time_median_s",
        "warnings_true_positive",
        "warnings_false_positive",
        "breaks_on_used_links",
        "breaks_warned",
    ):
        row[f"pred_{key}"] = pred.get(key)
    return row


def load(dirs: list[Path]) -> pd.DataFrame:
    """All finished runs under ``dirs`` (files ``<label>/<config>.json``; event logs are skipped)."""
    paths = sorted(
        p for d in dirs for p in Path(d).glob("*/*.json") if not p.name.endswith(".events.jsonl.gz")
    )
    return pd.DataFrame([row_from_result(p) for p in paths])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dirs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    df = load(a.dirs)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out, index=False)
    print(f"{len(df)} runs -> {a.out}")


if __name__ == "__main__":
    main()
