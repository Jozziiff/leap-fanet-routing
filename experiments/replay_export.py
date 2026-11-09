"""Export the demo runs (``demo.sh``) as replay data for the defense slides.

Two modes:

``record``
    Run one simulation in this fresh process with the demo configuration and dump drone positions and
    velocities (sampled every ``--frame-dt-s``) plus the recorder's packet events as JSON.
``bundle``
    Record Greedy and LEAP-GR (one subprocess each), check that their totals equal the demo's, select
    the moments where Greedy loses a packet to a link break while LEAP-GR, at the same drone, sees the
    same neighbour about to leave and switches, and write ``slides/assets/replay-data.js``.

Every number shown by the replay comes from these two recorded runs of the committed code.

Example
-------
    python experiments/replay_export.py bundle --out slides/assets/replay-data.js
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEMO = {"n": 20, "speed": 20.0, "rate": 2.0, "seed": 1, "sim_time_s": 15.0}  # identical to demo.sh
LEAP_PARAMS = {"tau_th_s": 0.25}  # identical to demo.sh: the threshold frozen for every experiment (D-016)
TX_OUTCOME_WINDOW_US = 20_000  # a data frame's reception outcome follows its transmission within 20 ms


def record(args: argparse.Namespace) -> None:
    """Simulate one protocol with the demo configuration and write frames and events to ``args.dump``."""
    sys.path.insert(0, str(REPO / "experiments"))
    import run_one

    run_args = run_one.parse_args(
        [
            "--protocol", args.protocol,
            "--params", json.dumps(LEAP_PARAMS if args.protocol == "leap" else {}),
            "--n", str(DEMO["n"]),
            "--speed", str(DEMO["speed"]),
            "--rate", str(DEMO["rate"]),
            "--seed", str(DEMO["seed"]),
            "--sim-time-s", str(DEMO["sim_time_s"]),
            "--out", str(args.dump),
        ]
    )  # fmt: skip
    run_one.configure(run_args)
    import simpy

    from instrumentation import hooks
    from instrumentation.recorder import Recorder
    from simulator.simulator import Simulator
    from utils import config

    rec = Recorder(keep_events=True)
    hooks.REC = rec
    env = simpy.Environment()
    frames: list = []

    def sampler(sim):
        while True:
            frames.append(
                [
                    round(env.now / 1e6, 3),
                    [[round(c, 1) for c in d.coords] + [round(v, 2) for v in d.velocity] for d in sim.drones],
                ]
            )
            yield env.timeout(args.frame_dt_s * 1e6)

    with contextlib.redirect_stdout(io.StringIO()):
        sim = Simulator(
            seed=DEMO["seed"],
            env=env,
            channel_states={i: simpy.Resource(env, capacity=1) for i in range(DEMO["n"])},
            n_drones=DEMO["n"],
        )
        rec.attach(sim)
        env.process(sampler(sim))
        env.run(until=config.SIM_TIME)
    keep = {"GEN", "TX", "RX", "DROP", "DELIVERED", "WARNING", "PROACTIVE_SWITCH"}
    events = [list(e) for e in rec.events if e[1] in keep]
    Path(args.dump).write_text(
        json.dumps(
            {
                "protocol": args.protocol,
                "commit": run_one.git_state(),
                "summary": rec.summary(),
                "frames": frames,
                "events": events,
            }
        )
    )


def attempts(events: list) -> list[list]:
    """Unicast data transmissions with the outcome at the intended receiver: [t_s, pid, src, dst, n, outcome]."""
    rx: dict[tuple[int, int, int], list[tuple[float, str]]] = {}
    for t, kind, pid, node, detail in events:
        if kind == "RX" and detail is not None:
            rx.setdefault((pid, detail[0], node), []).append((t, detail[1]))
    out = []
    for t, kind, pid, node, detail in events:
        if kind != "TX" or detail is None or detail[0] is None:
            continue
        dst, n = detail
        outcome = "NO_RX"
        for t_rx, o in rx.get((pid, node, dst), []):
            if t <= t_rx <= t + TX_OUTCOME_WINDOW_US:
                outcome = o
                break
        out.append([round(t / 1e6, 6), pid, node, dst, n, outcome])
    return out


def compact(run: dict) -> dict:
    """Keep what the slide draws: frames, transmissions, drops, deliveries, generations, switches."""
    ev = run["events"]
    m = run["summary"]
    switches = []
    last_warning: dict[tuple[int, int], tuple[int, float]] = {}
    for t, kind, pid, node, detail in ev:
        if kind == "WARNING":
            last_warning[(pid, node)] = (detail[0], detail[1])
        elif kind == "PROACTIVE_SWITCH":
            greedy_pick, tau = last_warning.get((pid, node), (None, detail[1]))
            switches.append([round(t / 1e6, 6), pid, node, greedy_pick, detail[0], round(tau, 3)])
    return {
        "protocol": run["protocol"],
        "commit": (run["commit"]["commit"] or "")[:7],
        "totals": {
            "generated": m["generated"],
            "delivered": m["delivered"],
            "link_break": m["losses"]["LINK_BREAK"],
            "collision": m["losses"]["COLLISION"],
            "other": m["lost"] - m["losses"]["LINK_BREAK"] - m["losses"]["COLLISION"],
            "switches": m.get("leap_events", {}).get("PROACTIVE_SWITCH", 0),
        },
        "frames": run["frames"],
        "tx": attempts(ev),
        "drops": [[round(t / 1e6, 6), pid, node, d] for t, k, pid, node, d in ev if k == "DROP"],
        "delivered": [[round(t / 1e6, 6), pid, node, d] for t, k, pid, node, d in ev if k == "DELIVERED"],
        "gen": [[round(t / 1e6, 6), pid, node, d] for t, k, pid, node, d in ev if k == "GEN"],
        "switches": switches,
    }


def moments(greedy: dict, leap: dict, limit: int) -> tuple[list[dict], int]:
    """Packets Greedy lost to a link break while LEAP-GR, at the same drone, switched away from the same pick."""
    sw = {(s[1], s[2]): s for s in leap["switches"]}
    delivered = {d[1]: d for d in leap["delivered"]}
    gen = {g[1]: g for g in greedy["gen"]}
    found = []
    for t, pid, node, cause in greedy["drops"]:
        if cause != "LINK_BREAK" or pid not in delivered:
            continue
        tries = [a for a in greedy["tx"] if a[1] == pid and a[2] == node]
        if not tries:
            continue
        pick = tries[-1][3]
        s = sw.get((pid, node))
        if s is None or s[3] != pick:
            continue
        path = [a for a in leap["tx"] if a[1] == pid and a[0] >= s[0] and a[5] == "OK"]
        found.append(
            {
                "pid": pid,
                "src": gen[pid][2],
                "dst": gen[pid][3],
                "node": node,
                "pick": pick,
                "greedy_tries": tries,
                "greedy_drop_t": t,
                "switch": s,
                "leap_path": path,
                "leap_delivered_t": delivered[pid][0],
                "leap_hops": delivered[pid][3],
            }
        )
    found.sort(key=lambda m: m["greedy_tries"][0][0])
    picked, used, last_t = [], set(), -1.0
    for m in found:  # distinct situations (drone, Greedy's pick), spread over the run
        if (m["node"], m["pick"]) in used or m["greedy_tries"][0][0] - last_t < 1.0:
            continue
        picked.append(m)
        used.add((m["node"], m["pick"]))
        last_t = m["greedy_tries"][0][0]
    return picked[:limit], len(found)


def demo_totals(cast: Path) -> dict[str, tuple[int, int, int]]:
    """Generated, delivered and link-break counts per protocol, read from the recorded demo's summary table."""
    text = "".join(json.loads(line)[2] for line in cast.read_text().splitlines()[1:])
    rows = {}
    for line in text.replace("\r", "").splitlines():
        for label in ("packets generated", "packets delivered", "lost to link breaks"):
            if line.startswith(label):
                rows[label] = [int(x) for x in line[len(label) :].split()]
    cols = list(zip(rows["packets generated"], rows["packets delivered"], rows["lost to link breaks"]))
    return {"greedy": cols[0], "leap": cols[1]}


def bundle(args: argparse.Namespace) -> None:
    keep = Path(args.keep)
    keep.mkdir(parents=True, exist_ok=True)
    procs = []
    for protocol in ("greedy", "leap"):
        dump = keep / f"{protocol}.json"
        if dump.exists() and not args.rerun:
            continue
        cmd = [
            sys.executable,
            "-W",
            "ignore",
            __file__,
            "record",
            "--protocol",
            protocol,
            "--dump",
            str(dump),
        ]
        cmd += ["--frame-dt-s", str(args.frame_dt_s)]
        procs.append((protocol, subprocess.Popen(cmd, cwd=REPO)))
    for protocol, p in procs:
        if p.wait() != 0:
            raise SystemExit(f"recording {protocol} failed")
    runs = {pr: compact(json.loads((keep / f"{pr}.json").read_text())) for pr in ("greedy", "leap")}
    if args.check_cast:
        expected = demo_totals(Path(args.check_cast))
        for protocol in ("greedy", "leap"):
            got = runs[protocol]["totals"]
            mine = (got["generated"], got["delivered"], got["link_break"])
            print(f"{protocol}: replay {mine} | demo {tuple(expected[protocol])}")
            if mine != tuple(expected[protocol]):
                raise SystemExit("the replay does not reproduce the recorded demo")
    picked, n_matched = moments(runs["greedy"], runs["leap"], args.moments)
    data = {"config": DEMO, "r_max_m": 249.3, "kappa": 0.9, "tau_th_s": LEAP_PARAMS["tau_th_s"], "runs": runs, "moments": picked,
            "n_matched_moments": n_matched}  # fmt: skip
    Path(args.out).write_text(
        "/* Generated by experiments/replay_export.py from two recorded runs of the committed code. */\n"
        "window.REPLAY = " + json.dumps(data, separators=(",", ":")) + ";\n"
    )
    print(f"wrote {args.out}: {len(picked)} moments shown, {n_matched} matching moments in the run")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=["record", "bundle"])
    ap.add_argument("--protocol", default="greedy")
    ap.add_argument("--dump", type=Path)
    ap.add_argument("--frame-dt-s", type=float, default=0.05)
    ap.add_argument("--out", type=Path, default=REPO / "slides/assets/replay-data.js")
    ap.add_argument("--moments", type=int, default=4)
    ap.add_argument("--check-cast", default=None, help="recorded demo (asciinema) whose totals must match")
    ap.add_argument("--keep", default="results/raw/replay", help="folder for the raw recordings")
    ap.add_argument("--rerun", action="store_true", help="record again even if the raw recordings exist")
    a = ap.parse_args()
    if a.mode == "record":
        record(a)
    else:
        bundle(a)


if __name__ == "__main__":
    main()
