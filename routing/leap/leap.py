"""LEAP-GR: Link-Expiration-Aware Predictive Greedy Routing (SPEC §6).

LEAP behaves exactly like Greedy forwarding unless Greedy's chosen neighbor is predicted to leave radio
range within ``tau_th_s``. Then it switches, before the break, to the neighbor with the most progress
among those predicted to stay in range (a one-hop backup, re-evaluated for every packet at every hop).
On an ACK timeout, the MAC calls :meth:`penalize` before retrying; with ``repair="predictive"`` LEAP
redirects the remaining retries to such a backup if the current next hop is predicted to break.

Everything else (hello period, neighbor lifetime, ACK handling, waiting list, virtual-force messages) is
Greedy's code, inherited unchanged; the MAC is untouched.

Parameters (``config.ROUTING_PARAMS``, all optional):

``tau_th_s`` (default 0.25, the value frozen from the tuning runs, ``docs/tau_freeze.json``)
    Lifetime threshold (s). ``0`` disables the prediction-based switch.
``repair`` (default ``"predictive"``)
    ``"off"`` (variant LEAP-select), ``"predictive"`` (LEAP) or ``"reactive"`` (control variant: switch to
    the best other neighbor after every ACK timeout, without prediction).
``kappa`` (default 0.9)
    Range used for the prediction, as a fraction of ``R_max`` (interference margin).
``extra_hello_bits`` (default 128)
    Hello size increase for velocity and timestamp (3 x 32 + 32 bits).
``xl`` (default ``False``), ``xl_beta`` (default 0.2)
    Bonus B1, cross-layer: each node keeps, per neighbor, an exponential moving average ``f`` of ACK
    timeouts (``f <- (1 - beta) f + beta * [timeout]``; success = ACK received) and ranks candidates,
    Greedy's pick included, by ``progress * (1 - f)`` instead of progress. The MAC is only read.
``warn_tau_s`` (default ``tau_th_s``)
    Threshold for logging prediction warnings; with ``tau_th_s = 0`` and ``warn_tau_s > 0`` the protocol
    behaves as Greedy and only logs (shadow mode, for prediction-quality measurements).
"""

from __future__ import annotations

from entities.packet import AckPacket
from instrumentation import hooks
from phy.large_scale_fading import maximum_communication_range
from routing.greedy.greedy import Greedy
from routing.leap.leap_packet import LeapHelloPacket
from routing.leap.leap_table import LeapNeighborTable
from routing.leap.link_lifetime import let_3d
from simulator.log import logger
from utils import config
from utils.util_function import euclidean_distance_3d

DEFAULTS = {"tau_th_s": 0.25, "repair": "predictive", "kappa": 0.9, "extra_hello_bits": 128}
REPAIR_MODES = ("off", "predictive", "reactive")


class Leap(Greedy):
    """Greedy forwarding with link-lifetime-aware next-hop choice and predictive repair."""

    def __init__(self, simulator, my_drone):
        super().__init__(simulator, my_drone)
        params = {**DEFAULTS, **config.ROUTING_PARAMS}
        self.tau_th_s = float(params["tau_th_s"])
        self.repair = str(params["repair"])
        if self.repair not in REPAIR_MODES:
            raise ValueError(f"repair must be one of {REPAIR_MODES}, got {self.repair!r}")
        self.kappa = float(params["kappa"])
        self.extra_hello_bits = int(params["extra_hello_bits"])
        self.warn_tau_s = float(params.get("warn_tau_s", self.tau_th_s))
        self.xl = bool(params.get("xl", False))
        self.xl_beta = float(params.get("xl_beta", 0.2))
        self.retx_rate: dict[int, float] = {}  # neighbor id -> moving average of ACK timeouts (B1)
        self.range_m = self.kappa * maximum_communication_range()
        # replaced before the simulation starts, so Greedy's processes only ever see this table
        self.neighbor_table = LeapNeighborTable(self.simulator.env, my_drone)

    # ------------------------------------------------------------------ hello
    def broadcast_hello_packet(self, my_drone):
        """Greedy's hello procedure with a LEAP hello (same RNG draws, same timing)."""
        config.GL_ID_HELLO_PACKET += 1
        channel_id = self.my_drone.channel_assigner.channel_assign()
        hello_pkd = LeapHelloPacket(
            src_drone=my_drone,
            creation_time=self.simulator.env.now,
            id_hello_packet=config.GL_ID_HELLO_PACKET,
            hello_packet_length=config.HELLO_PACKET_LENGTH + self.extra_hello_bits,
            simulator=self.simulator,
            channel_id=channel_id,
        )
        hello_pkd.transmission_mode = 1
        logger.info(
            "At time: %s (us) ---- UAV: %s has a hello packet to broadcast",
            self.simulator.env.now,
            self.my_drone.identifier,
        )
        self.simulator.metrics.control_packet_num += 1
        self.my_drone.transmitting_queue.put(hello_pkd)

    # ------------------------------------------------------------- prediction
    def _is_valid(self, j: int) -> bool:
        entry = self.neighbor_table.table.get(j)
        return entry is not None and entry[-1] + self.neighbor_table.entry_life_time >= self.simulator.env.now

    def link_lifetime_s(self, j: int) -> float:
        """Predicted remaining lifetime (s) of the link to neighbor ``j``; 0 if ``j`` is not a valid neighbor.

        The neighbor's position is dead-reckoned from its last hello; this node uses its own current
        position and velocity (on-board GNSS/IMU).
        """
        if not self._is_valid(j):
            return 0.0
        pos, vel, t_hello_us, _ = self.neighbor_table.table[j]
        dt_s = (self.simulator.env.now - t_hello_us) / 1e6
        me = self.my_drone
        dp = [pos[k] + vel[k] * dt_s - me.coords[k] for k in range(3)]
        dv = [vel[k] - me.velocity[k] for k in range(3)]
        return let_3d(dp, dv, self.range_m)

    def progress_m(self, j: int, dst_drone) -> float:
        """Distance to the destination saved by forwarding to ``j``, from ``j``'s hello position (as Greedy)."""
        return euclidean_distance_3d(self.my_drone.coords, dst_drone.coords) - euclidean_distance_3d(
            self.neighbor_table.table[j][0], dst_drone.coords
        )

    def score(self, j: int, dst_drone) -> float:
        """Ranking score: progress (m), weighted by ``1 - f_j`` when the cross-layer bonus is on."""
        progress = self.progress_m(j, dst_drone)
        if self.xl and progress > 0:
            return progress * (1.0 - self.retx_rate.get(j, 0.0))
        return progress

    def best_alternative(self, dst_drone, exclude: set[int], require_safe: bool) -> int | None:
        """Neighbor with the best positive score, not in ``exclude``; if ``require_safe``, only among
        neighbors predicted to stay in range for at least ``tau_th_s``. Ties: first in table order (as Greedy).
        """
        best_id, best_progress = None, 0.0
        me = self.my_drone.identifier  # the table holds the node's own hello (phy/channel.py:40-42)
        for j in self.neighbor_table.table:
            if j == me or j in exclude or not self._is_valid(j):
                continue
            progress = self.score(j, dst_drone)
            if progress <= best_progress:
                continue
            if require_safe and self.link_lifetime_s(j) < self.tau_th_s:
                continue
            best_id, best_progress = j, progress
        return best_id

    def _log(self, kind: str, packet, j: int | None, tau_s: float | None = None) -> None:
        if hooks.REC is not None:
            hooks.REC.on_leap(kind, self.my_drone, packet, j, tau_s, self.warn_tau_s)

    # --------------------------------------------------------------- routing
    def next_hop_selection(self, packet):
        has_route, packet, enquire = super().next_hop_selection(packet)  # purge + Greedy's choice
        if has_route and self.xl:
            weighted_id = self.best_alternative(packet.dst_drone, set(), require_safe=False)
            if weighted_id is not None:
                packet.next_hop_id = weighted_id
        if not has_route or (self.tau_th_s <= 0 and self.warn_tau_s <= 0):
            return has_route, packet, enquire

        greedy_id = packet.next_hop_id
        tau_s = self.link_lifetime_s(greedy_id)
        if tau_s < self.warn_tau_s:
            self._log("WARNING", packet, greedy_id, tau_s)
        if self.tau_th_s <= 0 or tau_s >= self.tau_th_s:
            return has_route, packet, enquire  # normal case: identical to Greedy
        if greedy_id == packet.dst_drone.identifier and tau_s > 0:
            self._log("KEEP_DESTINATION", packet, greedy_id, tau_s)  # one hop to the destination: keep it
            return has_route, packet, enquire

        backup_id = self.best_alternative(packet.dst_drone, {greedy_id}, require_safe=True)
        if backup_id is None:
            self._log(
                "RISKY_FORWARD", packet, greedy_id, tau_s
            )  # no safe alternative: never worse than Greedy
        else:
            packet.next_hop_id = backup_id
            self._log("PROACTIVE_SWITCH", packet, backup_id, tau_s)
        return has_route, packet, enquire

    def packet_reception(self, packet, src_drone_id):
        if self.xl and isinstance(packet, AckPacket):
            self._update_retx_rate(src_drone_id, failed=False)
        yield from super().packet_reception(packet, src_drone_id)

    def _update_retx_rate(self, j: int, failed: bool) -> None:
        f = self.retx_rate.get(j, 0.0)
        self.retx_rate[j] = (1.0 - self.xl_beta) * f + self.xl_beta * (1.0 if failed else 0.0)

    def penalize(self, packet):
        """Called by the MAC on every ACK timeout, before it retries ``packet.next_hop_id``."""
        if self.xl:
            self._update_retx_rate(packet.next_hop_id, failed=True)
        if self.repair == "off":
            return
        next_hop_id = packet.next_hop_id
        if self.repair == "predictive":
            tau_s = self.link_lifetime_s(next_hop_id)
            if tau_s >= self.tau_th_s:
                return
            if next_hop_id == packet.dst_drone.identifier and tau_s > 0:
                return
            backup_id = self.best_alternative(packet.dst_drone, {next_hop_id}, require_safe=True)
        else:  # reactive control: switch after every timeout, no prediction
            tau_s = None
            backup_id = self.best_alternative(packet.dst_drone, {next_hop_id}, require_safe=False)
        if backup_id is not None:
            packet.next_hop_id = backup_id
            self._log("REPAIR", packet, backup_id, tau_s)
