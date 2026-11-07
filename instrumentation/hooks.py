"""Global hook point used by the patched upstream code (patch P6).

Upstream modules call ``if hooks.REC is not None: hooks.REC.<event>(...)``. When ``REC`` is ``None``
(the default) every hook is skipped, so the simulator behaves exactly as upstream. The runner sets
``REC`` to an :class:`instrumentation.recorder.Recorder` before building the simulator.
"""

from __future__ import annotations

from typing import Any

REC: Any = None
