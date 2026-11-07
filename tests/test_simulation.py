"""Short end-to-end runs: interface (T2), paired seeds (T5), conservation (T6), hop counts (T8), golden (T4).

Each simulation runs in a fresh process through ``experiments/run_one.py`` (UPSTREAM_FACTS M4).
The golden test takes several minutes and is marked ``slow`` (``pytest -m slow``).
"""

from __future__ import annotations

import gzip
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RUN_ONE = REPO / "experiments" / "run_one.py"
PHASE0 = REPO / "results" / "phase0"


def run(tmp_path: Path, name: str, *args: str, events: bool = False) -> dict:
    out = tmp_path / f"{name}.json"
    cmd = [sys.executable, "-W", "ignore", str(RUN_ONE), "--out", str(out), *args]
    if events:
        cmd += ["--events", str(tmp_path / f"{name}.events.jsonl.gz")]
    subprocess.run(cmd, cwd=tmp_path, check=True, capture_output=True)
    return json.loads(out.read_text())


SHORT = ("--n", "8", "--sim-time-s", "5", "--traffic-start-s", "0.5", "--traffic-end-s", "4", "--rate", "2")


@pytest.mark.parametrize("protocol", ["dsdv", "greedy", "grad", "opar", "q_routing", "qgeo", "qfanet"])
def test_every_protocol_runs_and_conserves_packets(tmp_path, protocol):
    """T2 + T6: each registered protocol runs; generated = delivered + losses + in flight."""
    m = run(tmp_path, protocol, "--protocol", protocol, *SHORT)["metrics"]
    assert m["generated"] > 0
    assert m["generated"] == m["delivered"] + m["lost"] + m["in_flight"]
    assert m["losses"]["OTHER"] <= 0.02 * m["generated"]


def test_same_seed_same_traffic_across_protocols(tmp_path):
    """T5: traffic (time, source, destination) is identical across protocols for one seed (M22)."""
    gens = []
    for protocol in ("greedy", "dsdv"):
        run(tmp_path, protocol, "--protocol", protocol, *SHORT, events=True)
        with gzip.open(tmp_path / f"{protocol}.events.jsonl.gz", "rt") as fh:
            gens.append([e[:1] + e[2:] for e in map(json.loads, fh) if e[1] == "GEN"])
    assert gens[0] and gens[0] == gens[1]


def test_true_hops_never_exceed_upstream_ttl_count(tmp_path):
    """T8: upstream's hop count counts retransmissions (M20), so it is >= the true hop count."""
    m = run(
        tmp_path,
        "greedy",
        "--protocol",
        "greedy",
        "--n",
        "20",
        "--sim-time-s",
        "5",
        "--traffic-start-s",
        "0.5",
        "--traffic-end-s",
        "4",
        "--rate",
        "5",
    )["metrics"]
    assert m["hops_true_mean"] <= m["hops_upstream_mean"] + 1e-12


@pytest.mark.slow
@pytest.mark.parametrize(
    ("reference", "args"),
    [
        ("golden/dsdv_default_warning", ("--protocol", "dsdv", "--rate", "5", "--energy", "on")),
        ("bench/n10_l5", ("--protocol", "greedy", "--rate", "5", "--energy", "off")),
    ],
)
def test_golden_hooks_on_equals_phase0_reference(tmp_path, reference, args):
    """T4: with the recorder attached and upstream values, metrics equal the Phase-0 runs exactly.

    The Phase-0 references were produced with upstream files untouched (DECISIONS D-002).
    """
    ref = json.loads((PHASE0 / reference / "result.json").read_text())
    r = run(
        tmp_path,
        "golden",
        *args,
        "--n",
        "10",
        "--speed",
        "10",
        "--seed",
        "2025",
        "--traffic-start-s",
        "0",
        "--traffic-end-s",
        "inf",
    )
    up = r["upstream_metrics"]
    assert up["generated"] == ref["generated"]
    assert up["delivered"] == ref["delivered"]
    assert up["delay_mean_ms"] == ref["e2e_delay_ms"]
    assert up["hop_count_mean"] == ref["hop_cnt_upstream"]
    assert up["control_packet_num"] == ref["control_packet_num"]
    assert up["collision_num"] == ref["collision_num"]
