"""Run one UavNetSim-v1 simulation and write a result JSON.

Configuration is injected into ``utils.config`` before any simulator module is imported (patch P1),
because several values are read at import time (UPSTREAM_FACTS M3). Run one simulation per process
(M4): ``config`` is module state and the global packet-ID counters are never reset.

Defaults are the testbed of SPEC §8.1: 30 s runs, traffic in [2 s, 27 s], energy depletion disabled
(P7), logging at WARNING, matplotlib's non-interactive backend (P5: ``plt.show()`` becomes a no-op).
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import math
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

REPO = Path(__file__).resolve().parents[1]
UPSTREAM_COMMIT = "a5622c5d0a9f7b62b4e1d5a7dcc8978f34f0c85f"
ENERGY_OFF_J = 1e9  # P7: never reaches ENERGY_THRESHOLD within a run


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--protocol", default="greedy", help="name in routing/registry.py")
    p.add_argument("--n", type=int, default=30, help="number of drones")
    p.add_argument("--speed", type=float, default=10.0, help="mean speed (m/s)")
    p.add_argument("--rate", type=float, default=1.0, help="Poisson rate per drone (packets/s)")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--sim-time-s", type=float, default=30.0)
    p.add_argument("--traffic-start-s", type=float, default=2.0)
    p.add_argument("--traffic-end-s", type=float, default=None, help="default: sim time - 3 s")
    p.add_argument("--energy", choices=["off", "on"], default="off", help="off = patch P7")
    p.add_argument("--params", default="{}", help="JSON dict of protocol parameters")
    p.add_argument("--no-recorder", action="store_true", help="hooks disabled (golden test)")
    p.add_argument("--events", type=Path, default=None, help="also write the event log (JSON lines)")
    p.add_argument("--out", type=Path, required=True)
    return p.parse_args(argv)


def git_state() -> dict[str, object]:
    """Commit hash of this repository and whether the working tree has uncommitted changes."""
    try:
        head = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "-C", str(REPO), "status", "--porcelain", "--untracked-files=no"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}
    return {"commit": head, "dirty": dirty}


def configure(args: argparse.Namespace) -> None:
    """Write the run configuration into ``utils.config`` (must run before importing the simulator)."""
    sys.path.insert(0, str(REPO))
    from utils import config

    end_s = args.traffic_end_s if args.traffic_end_s is not None else args.sim_time_s - 3.0
    config.NUMBER_OF_DRONES = args.n
    config.MAX_TTL = args.n + 1  # recomputed: upstream evaluates it at import (M3)
    config.SIM_TIME = args.sim_time_s * 1e6
    config.LOGGING_LEVEL = logging.WARNING
    config.ROUTING_PROTOCOL = args.protocol
    config.ROUTING_PARAMS = json.loads(args.params)
    config.DRONE_SPEED = args.speed
    config.TRAFFIC_RATE = args.rate
    config.TRAFFIC_START = args.traffic_start_s * 1e6
    config.TRAFFIC_END = end_s * 1e6 if math.isfinite(end_s) else float("inf")
    if args.energy == "off":
        config.INITIAL_ENERGY = ENERGY_OFF_J


def run(args: argparse.Namespace) -> dict:
    configure(args)
    import simpy

    from instrumentation import hooks
    from instrumentation.recorder import Recorder
    from simulator.simulator import Simulator
    from utils import config

    recorder = None if args.no_recorder else Recorder(keep_events=args.events is not None)
    hooks.REC = recorder

    env = simpy.Environment()
    channel_states = {i: simpy.Resource(env, capacity=1) for i in range(args.n)}
    stdout = io.StringIO()
    t0 = time.perf_counter()
    with contextlib.redirect_stdout(stdout):
        sim = Simulator(seed=args.seed, env=env, channel_states=channel_states, n_drones=args.n)
        if recorder is not None:
            recorder.attach(sim)
        env.run(until=config.SIM_TIME)
    wall_s = time.perf_counter() - t0

    m = sim.metrics
    result = {
        "config": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
        "meta": {
            "repo": git_state(),
            "upstream_commit": UPSTREAM_COMMIT,
            "python": sys.version.split()[0],
            "wall_s": wall_s,
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        },
        "upstream_metrics": {
            "generated": m.datapacket_generated_num,
            "delivered": len(m.datapacket_arrived),
            "delay_mean_ms": (sum(m.deliver_time_dict.values()) / len(m.deliver_time_dict) / 1e3)
            if m.deliver_time_dict
            else None,
            "hop_count_mean": (sum(m.hop_cnt_dict.values()) / len(m.hop_cnt_dict))
            if m.hop_cnt_dict
            else None,
            "control_packet_num": m.control_packet_num,
            "collision_num": m.collision_num,
        },
        "metrics": recorder.summary() if recorder is not None else None,
    }
    if recorder is not None and args.events is not None:
        recorder.write_events(args.events)
    return result


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = run(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, indent=1))
    tmp.replace(args.out)  # atomic: a result file exists only if the run finished


if __name__ == "__main__":
    main()
