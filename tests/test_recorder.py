"""T7: the reception classifier and the final-cause rules of the recorder (no simulation needed)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from entities.packet import AckPacket, DataPacket
from instrumentation.recorder import Recorder
from phy.large_scale_fading import maximum_communication_range

R_MAX_M = maximum_communication_range()


def make_world(positions: list[tuple[float, float, float]]):
    env = SimpleNamespace(now=1_000_000.0)
    sim = SimpleNamespace(env=env, drones=[], metrics=SimpleNamespace())
    sim.drones = [
        SimpleNamespace(identifier=i, coords=list(p), simulator=sim) for i, p in enumerate(positions)
    ]
    rec = Recorder(keep_events=True)
    rec.attach(sim)
    return sim, rec


def data_packet(sim, src: int, dst: int, pid: int) -> DataPacket:
    return DataPacket(
        sim.drones[src],
        sim.drones[dst],
        creation_time=0.0,
        data_packet_id=pid,
        data_packet_length=8656,
        simulator=sim,
        channel_id=1,
    )


def test_r_max_matches_platform_constant():
    assert R_MAX_M == pytest.approx(249.27, abs=0.01)


def test_out_of_range_failure_is_link_break():
    sim, rec = make_world([(0, 0, 0), (R_MAX_M + 20, 0, 0)])
    pkd = data_packet(sim, 1, 0, pid=1)
    rec.on_generated(pkd, sim.drones[1])
    pkd.number_retransmission_attempt[1] = 1
    rec.on_tx(pkd, sim.drones[1], 0)
    rec.on_receptions(sim.drones[0], [[1, 1]], [pkd], [3.0])  # SINR below 6 dB
    assert rec.frames["data"] == {"FAIL_RANGE": 1}
    rec.on_retry_drop(pkd, sim.drones[1])
    assert rec.final_causes() == {1: "LINK_BREAK"}


def test_in_range_failure_is_collision():
    sim, rec = make_world([(0, 0, 0), (100, 0, 0)])
    pkd = data_packet(sim, 1, 0, pid=2)
    rec.on_generated(pkd, sim.drones[1])
    pkd.number_retransmission_attempt[1] = 1
    rec.on_tx(pkd, sim.drones[1], 0)
    rec.on_receptions(sim.drones[0], [[1, 1]], [pkd], [2.0])  # in range, but interference
    assert rec.frames["data"] == {"FAIL_COLLISION": 1}
    rec.on_retry_drop(pkd, sim.drones[1])
    assert rec.final_causes() == {2: "COLLISION"}


def test_simultaneous_frames_winner_and_not_selected():
    sim, rec = make_world([(0, 0, 0), (50, 0, 0), (60, 0, 0)])
    a, b = data_packet(sim, 1, 0, pid=3), data_packet(sim, 2, 0, pid=4)
    rec.on_receptions(sim.drones[0], [[1, 1], [2, 1]], [a, b], [12.0, 8.0])
    assert rec.frames["data"] == {"OK": 1, "NOT_SELECTED": 1}


def test_decoded_but_not_acked_is_queue_overflow():
    sim, rec = make_world([(0, 0, 0), (100, 0, 0)])
    pkd = data_packet(sim, 1, 0, pid=5)
    rec.on_generated(pkd, sim.drones[1])
    pkd.number_retransmission_attempt[1] = 1
    rec.on_tx(pkd, sim.drones[1], 0)
    rec.on_receptions(sim.drones[0], [[1, 1]], [pkd], [20.0])
    rec.on_retry_drop(pkd, sim.drones[1])
    assert rec.final_causes() == {5: "QUEUE_OVERFLOW"}


def test_lost_ack_out_of_range_is_link_break():
    sim, rec = make_world([(0, 0, 0), (100, 0, 0)])
    pkd = data_packet(sim, 1, 0, pid=6)
    rec.on_generated(pkd, sim.drones[1])
    pkd.number_retransmission_attempt[1] = 1
    rec.on_tx(pkd, sim.drones[1], 0)
    rec.on_receptions(sim.drones[0], [[1, 1]], [pkd], [20.0])
    ack = AckPacket(
        sim.drones[0],
        sim.drones[1],
        ack_packet_id=20001,
        ack_packet_length=240,
        ack_packet=pkd,
        simulator=sim,
        channel_id=1,
    )
    rec.on_tx(ack, sim.drones[0], 1)
    sim.drones[0].coords = [-R_MAX_M, 0, 0]  # now R_MAX + 100 m from the sender: link broken
    rec.on_receptions(sim.drones[1], [[0, 1]], [ack], [1.0])
    rec.on_retry_drop(pkd, sim.drones[1])
    assert rec.final_causes() == {6: "LINK_BREAK"}


def test_waiting_list_is_no_route_and_unfinished_is_in_flight():
    sim, rec = make_world([(0, 0, 0), (100, 0, 0)])
    p_wait, p_fly = data_packet(sim, 1, 0, pid=7), data_packet(sim, 1, 0, pid=8)
    for p in (p_wait, p_fly):
        rec.on_generated(p, sim.drones[1])
    rec.on_decision(p_wait, sim.drones[1], has_route=False, enquire=False)
    rec.on_decision(p_fly, sim.drones[1], has_route=True, enquire=False)
    assert rec.final_causes() == {7: "NO_ROUTE", 8: "IN_FLIGHT"}


def test_recomputation_counts_only_repeated_decisions_and_switches():
    sim, rec = make_world([(0, 0, 0), (100, 0, 0), (120, 0, 0)])
    pkd = data_packet(sim, 1, 0, pid=9)
    rec.on_generated(pkd, sim.drones[1])
    rec.on_decision(pkd, sim.drones[1], has_route=False, enquire=False)  # first: not a recomputation
    rec.on_decision(pkd, sim.drones[1], has_route=True, enquire=False)  # waiting-list retry
    pkd.number_retransmission_attempt[1] = 1
    rec.on_tx(pkd, sim.drones[1], 0)
    rec.on_ack_timeout(pkd, sim.drones[1])
    pkd.number_retransmission_attempt[1] = 2
    rec.on_tx(pkd, sim.drones[1], 0)  # MAC retry to the same next hop: not a recomputation
    rec.on_ack_timeout(pkd, sim.drones[1])
    pkd.number_retransmission_attempt[1] = 3
    rec.on_tx(pkd, sim.drones[1], 2)  # next hop changed after an ACK timeout: recomputation
    pkd.number_retransmission_attempt[1] = 4
    rec.on_tx(pkd, sim.drones[1], 0)  # new hop without a preceding timeout (e.g. a loop, M21): not a retry
    assert dict(rec.recomp) == {"WAIT_RETRY": 1, "RETRY_SWITCH": 1}
    assert rec.decisions == 2
