"""Link Expiration Time (LET) in 3-D: how long two nodes stay within radio range (SPEC §6.2, R5).

Constant-velocity prediction of Su, Lee and Gerla (Int. J. Netw. Manag., 2001), written for 3-D relative
motion. With relative position ``dp`` and relative velocity ``dv``, the link lasts until
``|dp + dv * tau| = R``. Expanding gives ``a tau^2 + 2 b tau + c = 0`` with ``a = |dv|^2``,
``b = dp . dv`` and ``c = |dp|^2 - R^2``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

_A_EPS = 1e-9  # (m/s)^2: below this relative speed the pair is treated as static


def r_max_m(
    p_tx_w: float,
    noise_w: float,
    snr_threshold_db: float,
    carrier_hz: float,
    path_loss_exponent: float = 2.0,
    light_speed_m_s: float = 3e8,
) -> float:
    """Largest distance (m) at which a frame is decodable without interference.

    Inverts the platform's free-space model ``P_rx = P_tx (c / (4 pi f d))^alpha`` at
    ``P_rx / N = threshold``; same formula as ``phy.large_scale_fading.maximum_communication_range``.
    """
    margin_db = 10 * math.log10(p_tx_w) - 10 * math.log10(noise_w) - snr_threshold_db
    return light_speed_m_s * 10 ** (margin_db / (10 * path_loss_exponent)) / (4 * math.pi * carrier_hz)


def let_3d(dp_m: Sequence[float], dv_m_s: Sequence[float], range_m: float) -> float:
    """Predicted remaining lifetime (s) of a link under constant relative velocity.

    Parameters
    ----------
    dp_m : sequence of 3 floats
        Position of the neighbor relative to this node (m).
    dv_m_s : sequence of 3 floats
        Velocity of the neighbor relative to this node (m/s).
    range_m : float
        Communication range ``R`` (m).

    Returns
    -------
    float
        ``0.0`` if the neighbor is already predicted out of range, ``math.inf`` if there is no relative
        motion, otherwise the larger root of the quadratic (the exit time), always ``>= 0``.
    """
    a = dv_m_s[0] ** 2 + dv_m_s[1] ** 2 + dv_m_s[2] ** 2
    b = dp_m[0] * dv_m_s[0] + dp_m[1] * dv_m_s[1] + dp_m[2] * dv_m_s[2]
    c = dp_m[0] ** 2 + dp_m[1] ** 2 + dp_m[2] ** 2 - range_m**2
    if c > 0:
        return 0.0
    if a < _A_EPS:
        return math.inf
    # c <= 0 implies b^2 - a c >= 0, and the larger root is >= 0
    return (-b + math.sqrt(b * b - a * c)) / a
