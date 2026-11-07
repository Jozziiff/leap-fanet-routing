"""Routing protocol registry (patch P2).

Maps a protocol name (``config.ROUTING_PROTOCOL``) to its class, imported lazily so that only the
selected protocol's module is loaded. Every class takes ``(simulator, my_drone)`` and implements
``next_hop_selection``, ``packet_reception`` and ``penalize`` (UPSTREAM_FACTS §2, M27).
"""

from __future__ import annotations

import importlib

PROTOCOLS: dict[str, tuple[str, str]] = {
    "dsdv": ("routing.dsdv.dsdv", "Dsdv"),
    "greedy": ("routing.greedy.greedy", "Greedy"),
    "grad": ("routing.grad.grad", "Grad"),
    "opar": ("routing.opar.opar", "Opar"),
    "q_routing": ("routing.q_routing.q_routing", "QRouting"),
    "qgeo": ("routing.qgeo.qgeo", "QGeo"),
    "qfanet": ("routing.qfanet.qfanet", "QFanet"),
    "qmr": ("routing.qmr.qmr", "QMR"),
    "leap": ("routing.leap.leap", "Leap"),
}


def get(name: str) -> type:
    """Return the routing class registered under ``name``.

    Raises
    ------
    KeyError
        If ``name`` is not registered.
    """
    try:
        module_name, class_name = PROTOCOLS[name]
    except KeyError:
        raise KeyError(f"unknown routing protocol {name!r}; known: {sorted(PROTOCOLS)}") from None
    return getattr(importlib.import_module(module_name), class_name)
