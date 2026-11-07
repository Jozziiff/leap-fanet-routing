"""Phase-0 runtime harness for UavNetSim-v1 v1.0.1 (benchmark and fact checks).

Runs one simulation in the current process without editing any upstream file.
Parameters that upstream hard-codes are overridden at runtime:

* config values (N, SIM_TIME, MAX_TTL, LOGGING_LEVEL, INITIAL_ENERGY) are set
  before the simulator modules are imported (they are read at import time);
* the routing class is swapped by rebinding ``entities.drone.Dsdv``
  (``entities/drone.py:106`` resolves that module global at call time);
* the Poisson rate (hard-coded ``rate = 5`` at ``entities/drone.py:142``) is
  overridden by replacing each drone's ``rng_drone`` with a subclass whose
  ``expovariate`` ignores the passed rate and uses ours. Its internal state is
  copied, and ``expovariate`` consumes exactly one ``random()`` draw either way,
  so the random stream (destinations, later draws) is unchanged;
* the mean speed (hard-coded ``speed = 10`` at ``simulator/simulator.py:63``)
  is overridden after construction with the same formulas as
  ``entities/drone.py:84-91``.

Optional probes observe the run and never draw random numbers. This file is
throwaway Phase-0 tooling; the permanent mechanism is patches P1-P7 (SPEC 4.3).

Run it in a fresh process per simulation (UPSTREAM_FACTS M4), with the working
directory set to a scratch folder (upstream writes ``running_log.log`` there).
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import math
import os
import random
import sys
import time
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")  # plt.show() becomes a no-op

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

ROUTING = {
    "dsdv": ("routing.dsdv.dsdv", "Dsdv"),
    "greedy": ("routing.greedy.greedy", "Greedy"),
    "grad": ("routing.grad.grad", "Grad"),
    "opar": ("routing.opar.opar", "Opar"),
    "q_routing": ("routing.q_routing.q_routing", "QRouting"),
    "qgeo": ("routing.qgeo.qgeo", "QGeo"),
    "qfanet": ("routing.qfanet.qfanet", "QFanet"),
}


class _RateOverride(random.Random):
    """``random.Random`` whose ``expovariate`` always uses a fixed rate (1/s)."""

    def __init__(self, rate_per_s: float) -> None:
        super().__init__()
        self._rate_per_s = rate_per_s

    def expovariate(self, lambd: float = 1.0) -> float:
        # ``lambd`` is upstream's hard-coded 5 (entities/drone.py:142); it is ignored on purpose.
        return super().expovariate(self._rate_per_s)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--n", type=int, default=10, help="number of drones")
    p.add_argument("--sim-time-s", type=float, default=30.0)
    p.add_argument("--seed", type=int, default=2025)
    p.add_argument("--routing", choices=sorted(ROUTING), default="dsdv")
    p.add_argument(
        "--speed", type=float, default=None, help="mean speed in m/s (default: upstream value 10, untouched)"
    )
    p.add_argument(
        "--rate",
        type=float,
        default=None,
        help="Poisson rate per drone in pkt/s (default: upstream value 5, untouched)",
    )
    p.add_argument(
        "--energy", choices=["on", "off"], default="on", help="off = INITIAL_ENERGY 1e9 J (SPEC patch P7)"
    )
    p.add_argument("--log-level", choices=["INFO", "WARNING"], default="WARNING")
    p.add_argument(
        "--trace", action="store_true", help="record traffic, trajectories, sleep times and hop counts"
    )
    p.add_argument("--out", type=Path, required=True, help="result JSON path")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    from utils import config

    config.NUMBER_OF_DRONES = args.n
    config.MAX_TTL = args.n + 1  # upstream computes this at import (utils/config.py:45)
    config.SIM_TIME = args.sim_time_s * 1e6
    config.LOGGING_LEVEL = getattr(logging, args.log_level)
    if args.energy == "off":
        config.INITIAL_ENERGY = 1e9

    import importlib

    import simpy

    import entities.drone as drone_mod
    from simulator.simulator import Simulator

    module_name, class_name = ROUTING[args.routing]
    drone_mod.Dsdv = getattr(importlib.import_module(module_name), class_name)

    trace: dict = {"gen": [], "deliv": {}, "traj": [], "sleep_s": {}}
    if args.trace:
        _install_packet_probes(drone_mod, trace)

    env = simpy.Environment()
    channel_states = {i: simpy.Resource(env, capacity=1) for i in range(args.n)}

    stdout_buf = io.StringIO()
    t0 = time.perf_counter()
    with contextlib.redirect_stdout(stdout_buf):
        sim = Simulator(seed=args.seed, env=env, channel_states=channel_states, n_drones=args.n)
        for d in sim.drones:
            if args.rate is not None:
                rng = _RateOverride(args.rate)
                rng.setstate(d.rng_drone.getstate())
                d.rng_drone = rng
            if args.speed is not None:
                d.speed = args.speed
                d.velocity = [
                    args.speed * math.cos(d.direction) * math.cos(d.pitch),
                    args.speed * math.sin(d.direction) * math.cos(d.pitch),
                    args.speed * math.sin(d.pitch),
                ]
                d.velocity_mean = args.speed
        if args.trace:
            env.process(_sampler(env, sim, trace))
        t_build = time.perf_counter() - t0
        env.run(until=config.SIM_TIME)
    wall_s = time.perf_counter() - t0

    m = sim.metrics
    delivered = len(m.datapacket_arrived)
    result = {
        "args": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
        "python": sys.version.split()[0],
        "wall_s": wall_s,
        "build_s": t_build,
        "generated": m.datapacket_generated_num,
        "delivered": delivered,
        "pdr_pct": 100.0 * delivered / m.datapacket_generated_num if m.datapacket_generated_num else None,
        "e2e_delay_ms": (sum(m.deliver_time_dict.values()) / delivered / 1e3) if delivered else None,
        "hop_cnt_upstream": (sum(m.hop_cnt_dict.values()) / delivered) if delivered else None,
        "control_packet_num": m.control_packet_num,
        "collision_num": m.collision_num,
        "stdout_tail": stdout_buf.getvalue().splitlines()[-9:],
    }
    if args.trace:
        result["trace"] = trace
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result))


def _install_packet_probes(drone_mod, trace: dict) -> None:
    """Record data-packet generation, true hop path and TTL at delivery."""
    from entities.packet import DataPacket
    from phy.phy import Phy
    from simulator.metrics import Metrics

    class TracedDataPacket(DataPacket):
        def __init__(self, src_drone, *a, **kw):
            super().__init__(src_drone, *a, **kw)
            self.hop_senders: tuple[int, ...] = ()
            trace["gen"].append(
                [
                    self.creation_time,
                    src_drone.identifier,
                    self.dst_drone.identifier,
                    self.packet_id,
                    self.channel_id,
                ]
            )

    drone_mod.DataPacket = TracedDataPacket  # generation site: entities/drone.py:166

    orig_unicast = Phy.unicast

    def unicast(self, packet, next_hop_id):
        # One entry per hop: retransmissions by the same sender do not append.
        if isinstance(packet, TracedDataPacket):
            me = self.my_drone.identifier
            if not packet.hop_senders or packet.hop_senders[-1] != me:
                packet.hop_senders = packet.hop_senders + (me,)
        return orig_unicast(self, packet, next_hop_id)

    Phy.unicast = unicast

    orig_calc = Metrics.calculate_metrics

    def calculate_metrics(self, received_packet):
        trace["deliv"][str(received_packet.packet_id)] = [
            received_packet.get_current_ttl(),
            len(received_packet.hop_senders),
        ]
        return orig_calc(self, received_packet)

    Metrics.calculate_metrics = calculate_metrics


def _sampler(env, sim, trace: dict):
    """Sample positions and sleep state every 0.1 s, offset by 0.05 s from mobility steps."""
    yield env.timeout(0.05e6)
    while True:
        trace["traj"].append([env.now] + [list(d.coords) for d in sim.drones])
        for d in sim.drones:
            if d.sleep and str(d.identifier) not in trace["sleep_s"]:
                trace["sleep_s"][str(d.identifier)] = env.now / 1e6
        yield env.timeout(0.1e6)


if __name__ == "__main__":
    main()
