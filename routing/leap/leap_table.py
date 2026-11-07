"""Neighbor table of LEAP-GR: Greedy's table plus each neighbor's velocity and hello time."""

from __future__ import annotations

from routing.greedy.greedy_neighbor_table import GreedyNeighborTable


class LeapNeighborTable(GreedyNeighborTable):
    """Entries are ``[position, velocity, t_hello_us, t_update_us]``.

    The position stays at index 0 and the update time at index -1, so Greedy's ``best_neighbor``,
    ``purge`` and expiry logic (``routing/base/base_table.py``) work unchanged.
    """

    def add_item(self, hello_packet, cur_time):
        drone_id = hello_packet.src_drone.identifier
        self.table[drone_id] = [
            hello_packet.cur_position,
            hello_packet.velocity,
            hello_packet.t_hello_us,
            cur_time,
        ]
