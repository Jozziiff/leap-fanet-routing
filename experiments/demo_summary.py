"""Print a side-by-side summary of result JSONs written by ``run_one.py`` (used by ``demo.sh``).

Example
-------
    python experiments/demo_summary.py out/greedy.json out/leap.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROWS: list[tuple[str, str]] = [
    ("packets generated", "generated"),
    ("packets delivered", "delivered"),
    ("delivery ratio (PDR)", "pdr"),
    ("lost to link breaks", "link_break"),
    ("lost to collisions", "collision"),
    ("lost, other causes", "other"),
    ("still in flight at the end", "in_flight"),
    ("proactive switches", "switches"),
]


def load(path: Path) -> dict[str, object]:
    """Read one result file and keep the numbers shown in the demo."""
    d = json.loads(path.read_text())
    m = d["metrics"]
    return {
        "protocol": d["config"]["protocol"],
        "commit": (d["meta"]["repo"]["commit"] or "?")[:7],
        "generated": m["generated"],
        "delivered": m["delivered"],
        "pdr": f"{100 * m['pdr']:.1f} %",
        "link_break": m["losses"]["LINK_BREAK"],
        "collision": m["losses"]["COLLISION"],
        "other": m["lost"] - m["losses"]["LINK_BREAK"] - m["losses"]["COLLISION"],
        "in_flight": m["in_flight"],
        "switches": m.get("leap_events", {}).get("PROACTIVE_SWITCH", "-"),
    }


def main(paths: list[str]) -> None:
    runs = [load(Path(p)) for p in paths]
    names = ["LEAP-GR" if r["protocol"] == "leap" else str(r["protocol"]).capitalize() for r in runs]
    width = 28
    print(f"{'':<{width}}" + "".join(f"{n:>12}" for n in names))
    print("-" * (width + 12 * len(runs)))
    for label, key in ROWS:
        print(f"{label:<{width}}" + "".join(f"{r[key]!s:>12}" for r in runs))
    print("-" * (width + 12 * len(runs)))
    print(
        f"commit {runs[0]['commit']} · same seed, same traffic and trajectories · one demo seed, not a result"
    )


if __name__ == "__main__":
    main(sys.argv[1:])
