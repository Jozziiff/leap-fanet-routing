"""Per-packet event recorder: loss attribution (R3), route recomputations (R2), true hop count.

The recorder only observes. It never draws random numbers, never yields to SimPy and never changes
simulator state, except for two bookkeeping attributes it adds to data packets (``hop_senders`` and
``_rec_node``), which no upstream code reads.

Loss attribution (SPEC §5.3)
----------------------------
Each failed reception is classified with the platform's own PHY: the signal-to-noise ratio *without
interference* is recomputed with ``phy.large_scale_fading.general_path_loss``. If it is below the
decoding threshold the receiver was out of range (``FAIL_RANGE``, a link break); otherwise the frame
was lost to interference (``FAIL_COLLISION``), or decodable but beaten by a stronger frame
(``NOT_SELECTED``, merged into collisions). Free-space path loss with fixed noise makes this test exact
(UPSTREAM_FACTS M15, M16).

Each lost packet then gets exactly one final cause, from the last thing that happened to it:

* ``LINK_BREAK`` / ``COLLISION``: dropped after the last MAC retry; the cause of the last attempt's
  failure (data frame, or its ACK);
* ``QUEUE_OVERFLOW``: source queue full, or the next hop decoded the frame but did not acknowledge it
  (its queue was full);
* ``TTL``: the last attempt was discarded by the receiver's TTL check;
* ``NO_ROUTE``: its last state is the waiting list (no next hop);
* ``EXPIRED``: lifetime exceeded in a queue;
* ``DISCARD``: GRAd only, copies were received but not forwarded by the gradient rule;
* ``OTHER``: anything else (safety net, expected ≈ 0);
* ``IN_FLIGHT``: still in the network at the end (excluded from loss shares).

GRAd broadcasts without ACK (M13), so its lost packets are attributed from receptions: ``COLLISION`` if
a node in range failed to decode a copy and never received one; ``LINK_BREAK`` if no node other than
the source ever decoded a copy; ``DISCARD`` otherwise. This is an approximation and is reported as such.

Route recomputations (SPEC §5.2)
--------------------------------
A route computation is one call of ``next_hop_selection`` for a data packet at the shared call site in
``Drone.feed_packet`` (decisions that forward or park the packet; periodic waiting-list polls inside
protocols are not counted). Recomputations are: a non-first computation for the same packet copy at the
same node (``WAIT_RETRY``), a route discovery broadcast (``DISCOVERY``, GRAd ``M_REQUEST``), and a change
of next hop between two MAC attempts of the same packet at the same node (``RETRY_SWITCH``).
"""

from __future__ import annotations

import gzip
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

OK = "OK"
FAIL_RANGE = "FAIL_RANGE"
FAIL_COLLISION = "FAIL_COLLISION"
NOT_SELECTED = "NOT_SELECTED"
TTL_DROP = "TTL_DROP"

LOSS_CAUSES = (
    "LINK_BREAK",
    "COLLISION",
    "NO_ROUTE",
    "QUEUE_OVERFLOW",
    "TTL",
    "EXPIRED",
    "DISCARD",
    "OTHER",
)

# a GRAd packet whose last activity is this close to the end of the run counts as in flight
_GRAD_IN_FLIGHT_WINDOW_US = 1e6


class Recorder:
    """Collects per-packet events during one run and summarises them with :meth:`summary`.

    Parameters
    ----------
    keep_events : bool
        Also keep the full event list (for debugging and the G1 check), written by :meth:`write_events`.
    """

    def __init__(self, keep_events: bool = False) -> None:
        self.sim: Any = None
        self.keep_events = keep_events
        self.events: list[tuple] = []

        self.gen: dict[int, tuple[float, int, int]] = {}  # pid -> (t_us, src, dst)
        self.last: dict[int, tuple[float, str, str | None]] = {}  # pid -> (t_us, kind, cause)
        self.delivered: dict[int, tuple[float, float, int | None]] = {}  # pid -> (t_us, latency_us, hops)

        self.last_attempt: dict[tuple[int, int], dict[str, Any]] = {}  # (pid, sender) -> attempt state
        self.grad_reached: dict[int, set[int]] = defaultdict(set)
        self.grad_inrange_fail: dict[int, set[int]] = defaultdict(set)
        self.grad_hops: dict[int, int] = {}
        self.grad_tx: set[int] = set()

        self.decisions = 0
        self.recomp: Counter[str] = Counter()
        self.frames: dict[str, Counter[str]] = defaultdict(Counter)  # frame type -> outcome counts
        self.drop_events: Counter[str] = Counter()
        self.tx_data_attempts = 0
        self.ack_timeouts = 0
        self.control_tx_frames = 0
        self.control_tx_bits = 0

    # ------------------------------------------------------------------ setup
    def attach(self, simulator: Any) -> None:
        """Bind to a simulator (called right after it is constructed)."""
        from phy.large_scale_fading import general_path_loss
        from utils import config

        self.sim = simulator
        self._path_loss = general_path_loss
        self._p_tx_w = config.TRANSMITTING_POWER
        self._noise_w = config.NOISE_POWER
        self._thr_db = config.SNR_THRESHOLD

    # ------------------------------------------------------------- utilities
    @property
    def _now(self) -> float:
        return self.sim.env.now

    def _ev(self, kind: str, pid: int, node: int | None, detail: Any = None) -> None:
        if self.keep_events:
            self.events.append((self._now, kind, pid, node, detail))

    def _set_last(self, pid: int, kind: str, cause: str | None = None) -> None:
        if pid in self.gen:
            self.last[pid] = (self._now, kind, cause)

    def _terminal(self, pid: int, cause: str, node: int | None) -> None:
        self.drop_events[cause] += 1
        self._set_last(pid, "DROP", cause)
        self._ev("DROP", pid, node, cause)

    def snr_noint_db(self, receiver: Any, sender_id: int) -> float:
        """SNR (dB) of the sender's signal at the receiver without any interference."""
        transmitter = self.sim.drones[sender_id]
        return 10 * math.log10(self._p_tx_w * self._path_loss(receiver, transmitter) / self._noise_w)

    @staticmethod
    def _is_data(packet: Any) -> bool:
        from entities.packet import DataPacket

        return isinstance(packet, DataPacket)

    @staticmethod
    def _grad_data_pid(packet: Any) -> int | None:
        if getattr(packet, "msg_type", None) == "M_DATA" and packet.attached_data_packet is not None:
            return packet.attached_data_packet.packet_id
        return None

    # ------------------------------------------------------------------ hooks
    def on_generated(self, pkd: Any, src: Any) -> None:
        pkd.hop_senders = ()
        self.gen[pkd.packet_id] = (self._now, src.identifier, pkd.dst_drone.identifier)
        self._set_last(pkd.packet_id, "GEN")
        self._ev("GEN", pkd.packet_id, src.identifier, pkd.dst_drone.identifier)

    def on_source_overflow(self, pkd: Any, src: Any) -> None:
        self._terminal(pkd.packet_id, "QUEUE_OVERFLOW", src.identifier)

    def on_decision(self, pkd: Any, node: Any, has_route: bool, enquire: bool) -> None:
        me = node.identifier
        self.decisions += 1
        if getattr(pkd, "_rec_node", None) == me:
            self.recomp["WAIT_RETRY"] += 1
        else:
            pkd._rec_node = me
        if not has_route and enquire:
            self.recomp["DISCOVERY"] += 1
        self._set_last(pkd.packet_id, "DECIDE" if has_route else "WAIT")
        self._ev("DECIDE" if has_route else "WAIT", pkd.packet_id, me, getattr(pkd, "next_hop_id", None))

    def on_expired(self, packet: Any, node: Any) -> None:
        if self._is_data(packet):
            self._terminal(packet.packet_id, "EXPIRED", node.identifier)

    def on_retry_budget(self, pkd: Any, node: Any) -> None:
        """Packet reached the queue again with its retry budget at this node already used (M21)."""
        self._terminal(pkd.packet_id, "OTHER", node.identifier)

    def on_tx(self, packet: Any, sender: Any, dst_id: int | None) -> None:
        me = sender.identifier
        if self._is_data(packet) and dst_id is not None:
            pid = packet.packet_id
            senders = getattr(packet, "hop_senders", ())
            if not senders or senders[-1] != me:
                packet.hop_senders = senders + (me,)
            attempt = packet.number_retransmission_attempt[me]
            prev = self.last_attempt.get((pid, me))
            # a MAC retry is a transmission that follows an ACK timeout at this node; the attempt counter
            # alone is not enough because it is shared between copies of a packet (UPSTREAM_FACTS M21)
            if prev is not None and prev["timed_out"] and prev["nh"] != dst_id:
                self.recomp["RETRY_SWITCH"] += 1
            self.last_attempt[(pid, me)] = {
                "nh": dst_id,
                "data": None,
                "ack_sent": False,
                "ack": None,
                "timed_out": False,
            }
            self.tx_data_attempts += 1
            self._set_last(pid, "TX")
            self._ev("TX", pid, me, (dst_id, attempt))
            return
        from entities.packet import AckPacket

        if isinstance(packet, AckPacket):
            pid = packet.ack_packet.packet_id
            state = self.last_attempt.get((pid, dst_id))
            if state is not None and state["nh"] == me:
                state["ack_sent"] = True
            self._ev("ACK_TX", pid, me, dst_id)
            return
        pid = self._grad_data_pid(packet)
        if pid is not None:
            self.grad_tx.add(pid)
            self.tx_data_attempts += 1
            self._set_last(pid, "TX")
            self._ev("TX", pid, me, None)
            return
        self.control_tx_frames += 1
        self.control_tx_bits += packet.packet_length

    def on_receptions(self, receiver: Any, senders: list, packets: list, sinr_list: list) -> None:
        """Classify every frame that finished at ``receiver`` in this polling step."""
        from entities.packet import AckPacket

        me = receiver.identifier
        max_sinr = max(sinr_list)
        winner = sinr_list.index(max_sinr) if max_sinr >= self._thr_db else None
        for k, (packet, pair) in enumerate(zip(packets, senders)):
            sid = pair[0]
            if sid == me:  # own broadcast copy (broadcast_put includes the sender's inbox)
                continue
            if k == winner:
                outcome = OK
            elif sinr_list[k] >= self._thr_db:
                outcome = NOT_SELECTED
            elif self.snr_noint_db(receiver, sid) < self._thr_db:
                outcome = FAIL_RANGE
            else:
                outcome = FAIL_COLLISION

            if self._is_data(packet):
                self.frames["data"][outcome] += 1
                pid = packet.packet_id
                state = self.last_attempt.get((pid, sid))
                if state is not None and state["nh"] == me:
                    state["data"] = outcome
                if outcome == OK:
                    self._set_last(pid, "RX")
                self._ev("RX", pid, me, (sid, outcome))
            elif isinstance(packet, AckPacket):
                self.frames["ack"][outcome] += 1
                pid = packet.ack_packet.packet_id
                state = self.last_attempt.get((pid, me))
                if state is not None and state["nh"] == sid:
                    state["ack"] = outcome
                self._ev("ACK_RX", pid, me, (sid, outcome))
            else:
                pid = self._grad_data_pid(packet)
                if pid is None:
                    self.frames["control"][outcome] += 1
                    continue
                self.frames["grad_data"][outcome] += 1
                if outcome == OK:
                    self.grad_reached[pid].add(me)
                    if packet.attached_data_packet.dst_drone.identifier == me and pid not in self.grad_hops:
                        self.grad_hops[pid] = packet.accrued_cost + 1
                    self._set_last(pid, "RX")
                elif outcome in (FAIL_COLLISION, NOT_SELECTED):
                    self.grad_inrange_fail[pid].add(me)
                self._ev("RX", pid, me, (sid, outcome))

    def on_ttl_drop(self, packet: Any, receiver: Any, sender_id: int) -> None:
        if self._is_data(packet):
            state = self.last_attempt.get((packet.packet_id, sender_id))
            if state is not None and state["nh"] == receiver.identifier:
                state["data"] = TTL_DROP
            self._ev("TTL_DROP", packet.packet_id, receiver.identifier, sender_id)

    def on_ack_timeout(self, pkd: Any, node: Any) -> None:
        if self._is_data(pkd):
            self.ack_timeouts += 1
            state = self.last_attempt.get((pkd.packet_id, node.identifier))
            if state is not None:
                state["timed_out"] = True
            self._set_last(pkd.packet_id, "ACK_TIMEOUT")
            self._ev("ACK_TIMEOUT", pkd.packet_id, node.identifier, None)

    def on_retry_drop(self, pkd: Any, node: Any) -> None:
        if self._is_data(pkd):
            state = self.last_attempt.get((pkd.packet_id, node.identifier))
            self._terminal(pkd.packet_id, self._attempt_cause(state), node.identifier)

    def on_delivered(self, pkd: Any) -> None:
        pid = pkd.packet_id
        if pid in self.delivered:
            return
        hops = len(pkd.hop_senders) if getattr(pkd, "hop_senders", ()) else self.grad_hops.get(pid)
        self.delivered[pid] = (self._now, self._now - pkd.creation_time, hops)
        self._set_last(pid, "DELIVERED")
        self._ev("DELIVERED", pid, pkd.dst_drone.identifier, hops)

    # ---------------------------------------------------------- attribution
    @staticmethod
    def _attempt_cause(state: dict[str, Any] | None) -> str:
        """Final cause of a packet dropped after its last MAC attempt."""
        if state is None:
            return "OTHER"
        data = state["data"]
        if data == FAIL_RANGE:
            return "LINK_BREAK"
        if data in (FAIL_COLLISION, NOT_SELECTED):
            return "COLLISION"
        if data == TTL_DROP:
            return "TTL"
        if data == OK:
            if not state["ack_sent"]:
                return "QUEUE_OVERFLOW"  # decoded but not acknowledged: relay queue full
            ack = state["ack"]
            if ack == FAIL_RANGE:
                return "LINK_BREAK"
            if ack in (FAIL_COLLISION, NOT_SELECTED):
                return "COLLISION"
        return "OTHER"

    def final_causes(self) -> dict[int, str]:
        """Final cause of every undelivered packet (``IN_FLIGHT`` included)."""
        end_us = self._now
        causes: dict[int, str] = {}
        for pid, (_t, src, _dst) in self.gen.items():
            if pid in self.delivered:
                continue
            t_last, kind, cause = self.last[pid]
            if kind == "DROP":
                causes[pid] = cause or "OTHER"
            elif kind == "WAIT":
                causes[pid] = "NO_ROUTE"
            elif pid in self.grad_tx:
                if end_us - t_last < _GRAD_IN_FLIGHT_WINDOW_US:
                    causes[pid] = "IN_FLIGHT"
                elif self.grad_inrange_fail[pid] - self.grad_reached[pid]:
                    causes[pid] = "COLLISION"
                elif not (self.grad_reached[pid] - {src}):
                    causes[pid] = "LINK_BREAK"
                else:
                    causes[pid] = "DISCARD"
            else:
                causes[pid] = "IN_FLIGHT"
        return causes

    # --------------------------------------------------------------- output
    def summary(self) -> dict[str, Any]:
        """Run-level metrics as a JSON-serialisable dict."""
        m = self.sim.metrics
        causes = self.final_causes()
        counts = Counter(causes.values())
        n_gen = len(self.gen)
        n_del = len(self.delivered)
        losses = {c: counts.get(c, 0) for c in LOSS_CAUSES}
        n_lost = sum(losses.values())
        lat_ms = sorted(v[1] / 1e3 for v in self.delivered.values())
        hops = [v[2] for v in self.delivered.values() if v[2] is not None]
        lb, coll = losses["LINK_BREAK"], losses["COLLISION"]
        n_recomp = sum(self.recomp.values())
        return {
            "generated": n_gen,
            "delivered": n_del,
            "in_flight": counts.get("IN_FLIGHT", 0),
            "pdr": n_del / n_gen if n_gen else None,
            "delay_mean_ms": sum(lat_ms) / n_del if n_del else None,
            "delay_p95_ms": lat_ms[min(n_del - 1, math.ceil(0.95 * n_del) - 1)] if n_del else None,
            "hops_true_mean": sum(hops) / len(hops) if hops else None,
            "hops_upstream_mean": (sum(m.hop_cnt_dict.values()) / len(m.hop_cnt_dict))
            if m.hop_cnt_dict
            else None,
            "losses": losses,
            "lost": n_lost,
            "lbr_all": lb / n_lost if n_lost else None,
            "lbr_vs_collision": lb / (lb + coll) if (lb + coll) else None,
            "loss_link_break_per_generated": lb / n_gen if n_gen else None,
            "route_computations": self.decisions,
            "recomputations": dict(self.recomp),
            "rr": n_recomp / n_del if n_del else None,
            "tx_data_attempts": self.tx_data_attempts,
            "ack_timeouts": self.ack_timeouts,
            "frame_outcomes": {k: dict(v) for k, v in self.frames.items()},
            "drop_events": dict(self.drop_events),
            "control_packets_upstream": m.control_packet_num,
            "nrl_upstream": m.control_packet_num / n_del if n_del else None,
            "control_tx_frames": self.control_tx_frames,
            "control_tx_bits": self.control_tx_bits,
            "collision_num_upstream": m.collision_num,
            "upstream_metrics": {
                "generated": m.datapacket_generated_num,
                "delivered": len(m.datapacket_arrived),
                "delay_mean_ms": (sum(m.deliver_time_dict.values()) / len(m.deliver_time_dict) / 1e3)
                if m.deliver_time_dict
                else None,
                "throughput_kbps": (sum(m.throughput_dict.values()) / len(m.throughput_dict) / 1e3)
                if m.throughput_dict
                else None,
            },
        }

    def write_events(self, path: Path) -> None:
        """Write the event list as JSON lines ``[t_us, kind, packet_id, node, detail]`` (gzip if ``.gz``)."""
        path = Path(path)
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "wt") as fh:
            for ev in self.events:
                fh.write(json.dumps(ev) + "\n")
