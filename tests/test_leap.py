"""T1 (link lifetime), T3 (prediction off == Greedy) and the LEAP decision rules."""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from phy.large_scale_fading import maximum_communication_range
from routing.leap.link_lifetime import let_3d, r_max_m
from routing.opar.opar import link_lifetime_predictor
from utils import config

REPO = Path(__file__).resolve().parents[1]
RUN_ONE = REPO / "experiments" / "run_one.py"
R = 200.0


# ----------------------------------------------------------------------- T1
def test_static_pair_lives_forever():
    assert let_3d([50, 0, 0], [0, 0, 0], R) == math.inf


def test_moving_apart_along_axis():
    # at 50 m, separating at 10 m/s: leaves the 200 m range after 15 s
    assert let_3d([50, 0, 0], [10, 0, 0], R) == pytest.approx(15.0)


def test_head_on_takes_the_later_exit():
    # neighbor 50 m ahead, approaching at 10 m/s: passes through and exits at -200 m after 25 s
    assert let_3d([50, 0, 0], [-10, 0, 0], R) == pytest.approx(25.0)


def test_perpendicular_motion():
    # |(100, 10 t, 0)| = 200  =>  t = sqrt(200^2 - 100^2) / 10
    assert let_3d([100, 0, 0], [0, 10, 0], R) == pytest.approx(math.sqrt(R**2 - 100**2) / 10)


def test_vertical_motion_counts():
    assert let_3d([0, 0, 10], [0, 0, 5], R) == pytest.approx((R - 10) / 5)


def test_out_of_range_is_zero():
    assert let_3d([R + 1, 0, 0], [-50, 0, 0], R) == 0.0


def test_on_the_boundary_moving_out_is_zero_and_moving_in_is_positive():
    assert let_3d([R, 0, 0], [1, 0, 0], R) == pytest.approx(0.0, abs=1e-9)
    assert let_3d([R, 0, 0], [-1, 0, 0], R) == pytest.approx(2 * R)


def test_near_zero_relative_speed_is_finite_and_large():
    tau = let_3d([10, 0, 0], [1e-3, 0, 0], R)
    assert math.isfinite(tau) and tau == pytest.approx((R - 10) / 1e-3)


@pytest.mark.parametrize(
    ("p1", "v1", "p2", "v2"),
    [
        ((0, 0, 50), (10, 0, 0), (120, 30, 60), (-5, 8, 1)),
        ((300, 300, 20), (0, -12, 0.5), (250, 180, 80), (7, 7, -1)),
        ((10, 500, 90), (3, 3, 0), (60, 420, 10), (-9, 1, 0.2)),
    ],
)
def test_matches_opar_predictor_when_in_range(p1, v1, p2, v2):
    a = SimpleNamespace(coords=list(p1), velocity=list(v1))
    b = SimpleNamespace(coords=list(p2), velocity=list(v2))
    dp = [b.coords[k] - a.coords[k] for k in range(3)]
    dv = [b.velocity[k] - a.velocity[k] for k in range(3)]
    assert let_3d(dp, dv, R) == pytest.approx(link_lifetime_predictor(a, b, R))


def test_r_max_matches_platform():
    expected = maximum_communication_range()
    got = r_max_m(
        config.TRANSMITTING_POWER, config.NOISE_POWER, config.SNR_THRESHOLD, config.CARRIER_FREQUENCY
    )
    assert got == pytest.approx(expected) and got == pytest.approx(249.27, abs=0.01)


# --------------------------------------------------------- decision rules
class FakeLeap:
    """Minimal stand-in exposing what Leap's decision helpers use."""

    def __init__(self, tau_th_s, neighbors, me_pos=(0.0, 0.0, 50.0), me_vel=(0.0, 0.0, 0.0)):
        from routing.leap.leap import Leap
        from routing.leap.leap_table import LeapNeighborTable

        env = SimpleNamespace(now=10e6)
        self.simulator = SimpleNamespace(env=env)
        self.my_drone = SimpleNamespace(identifier=0, coords=list(me_pos), velocity=list(me_vel))
        self.neighbor_table = LeapNeighborTable(env, self.my_drone)
        for j, (pos, vel) in neighbors.items():
            self.neighbor_table.table[j] = [list(pos), list(vel), env.now, env.now]
        self.tau_th_s = tau_th_s
        self.range_m = 0.9 * maximum_communication_range()
        for name in ("_is_valid", "link_lifetime_s", "progress_m", "best_alternative"):
            setattr(self, name, getattr(Leap, name).__get__(self))


DST = SimpleNamespace(identifier=99, coords=[500.0, 0.0, 50.0])


def test_backup_must_be_safe_and_make_progress():
    leap = FakeLeap(
        1.0,
        {
            1: ((200, 0, 50), (30, 0, 0)),  # most progress, leaves the 224 m range in 0.81 s: unsafe
            2: ((120, 0, 50), (0, 0, 0)),  # less progress, static: safe
            3: ((-50, 0, 50), (0, 0, 0)),  # safe but backwards: excluded
        },
    )
    assert leap.link_lifetime_s(1) < 1.0
    assert leap.best_alternative(DST, {1}, require_safe=True) == 2
    assert leap.best_alternative(DST, set(), require_safe=False) == 1


def test_no_safe_backup_returns_none():
    leap = FakeLeap(5.0, {1: ((200, 0, 50), (15, 0, 0)), 2: ((150, 0, 50), (20, 0, 0))})
    assert leap.best_alternative(DST, {1}, require_safe=True) is None


def test_expired_neighbor_has_zero_lifetime():
    leap = FakeLeap(1.0, {1: ((100, 0, 50), (0, 0, 0))})
    leap.neighbor_table.table[1][-1] = 0.0  # last hello long ago (> 2 s neighbor lifetime)
    assert leap.link_lifetime_s(1) == 0.0


def test_dead_reckoning_uses_hello_age():
    leap = FakeLeap(1.0, {1: ((100, 0, 50), (10, 0, 0))})
    leap.neighbor_table.table[1][2] = 10e6 - 2e6  # hello sent 2 s ago: neighbor now at x = 120
    expected = (leap.range_m - 120) / 10
    assert leap.link_lifetime_s(1) == pytest.approx(expected)


# ----------------------------------------------------------------------- T3
def _run(tmp_path, name, protocol, params):
    out = tmp_path / f"{name}.json"
    subprocess.run(
        [
            sys.executable,
            "-W",
            "ignore",
            str(RUN_ONE),
            "--protocol",
            protocol,
            "--params",
            params,
            "--n",
            "15",
            "--sim-time-s",
            "6",
            "--traffic-start-s",
            "0.5",
            "--traffic-end-s",
            "5",
            "--rate",
            "3",
            "--speed",
            "15",
            "--out",
            str(out),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return json.loads(out.read_text())


def test_prediction_off_is_identical_to_greedy(tmp_path):
    """T3: LEAP with tau_th = 0, repair off and no extra hello bits reproduces Greedy exactly."""
    greedy = _run(tmp_path, "greedy", "greedy", "{}")
    leap_off = _run(
        tmp_path, "leap_off", "leap", json.dumps({"tau_th_s": 0, "repair": "off", "extra_hello_bits": 0})
    )
    for key in (
        "generated",
        "delivered",
        "delay_mean_ms",
        "hop_count_mean",
        "control_packet_num",
        "collision_num",
    ):
        assert leap_off["upstream_metrics"][key] == greedy["upstream_metrics"][key], key
    assert leap_off["metrics"]["losses"] == greedy["metrics"]["losses"]


def test_shadow_mode_logs_warnings_but_changes_nothing(tmp_path):
    greedy = _run(tmp_path, "greedy", "greedy", "{}")
    shadow = _run(
        tmp_path,
        "shadow",
        "leap",
        json.dumps({"tau_th_s": 0, "repair": "off", "extra_hello_bits": 0, "warn_tau_s": 1.0}),
    )
    assert shadow["upstream_metrics"] == greedy["upstream_metrics"]
    assert shadow["metrics"]["leap_events"].get("WARNING", 0) > 0
    assert "PROACTIVE_SWITCH" not in shadow["metrics"]["leap_events"]
