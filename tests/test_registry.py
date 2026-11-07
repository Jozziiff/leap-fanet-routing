"""T2 (part): every registered protocol exposes the interface the simulator calls."""

from __future__ import annotations

import inspect

import pytest

from routing import registry


@pytest.mark.parametrize("name", sorted(registry.PROTOCOLS))
def test_protocol_interface(name):
    cls = registry.get(name)
    assert callable(cls.next_hop_selection)
    assert inspect.isgeneratorfunction(cls.packet_reception)
    if name != "grad":  # GRAd disables ACKs, so the MAC never calls penalize (UPSTREAM_FACTS M27)
        assert callable(cls.penalize)


def test_unknown_protocol_is_rejected():
    with pytest.raises(KeyError):
        registry.get("nope")
