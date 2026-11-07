"""Hello packet of LEAP-GR: Greedy's hello plus the sender's velocity and the hello's creation time."""

from __future__ import annotations

from routing.greedy.greedy_packet import GreedyHelloPacket


class LeapHelloPacket(GreedyHelloPacket):
    """Greedy hello carrying ``velocity`` (m/s) and ``t_hello_us`` in addition to the position.

    The velocity is copied: the mobility model mutates ``drone.velocity`` in place on wall rebound
    (UPSTREAM_FACTS M39), so a reference would change after the hello was created.
    """

    def __init__(self, src_drone, creation_time, id_hello_packet, hello_packet_length, simulator, channel_id):
        super().__init__(
            src_drone, creation_time, id_hello_packet, hello_packet_length, simulator, channel_id
        )
        self.velocity = list(src_drone.velocity)
        self.t_hello_us = creation_time
