# Modifications to upstream UavNetSim-v1

Upstream: <https://github.com/Zihao-Felix-Zhou/UavNetSim-v1>, tag `v1.0.1`, commit
`a5622c5d0a9f7b62b4e1d5a7dcc8978f34f0c85f`, MIT license. The first commit of this repository is that tree,
unmodified (its tree hash equals the upstream tag's tree hash). Every later change to an upstream file is listed
here: file, lines, why, and whether simulation behaviour can change.

Check the full diff at any time with `git diff <first-commit> -- <upstream paths>`.

## Non-code changes

| # | Change | Why | Behaviour change |
|---|---|---|---|
| N1 | Removed `.idea/` (6 files) and `routing/qmr/__pycache__/*.pyc` (12 files) shipped by the tag | IDE settings and stale bytecode do not belong in the repository (UPSTREAM_FACTS M33) | none (Python recompiles from source) |
| N2 | Appended a project section to `.gitignore` | ignore the virtual environment, tool caches, local notes and raw results | none |
| N3 | Renamed upstream `LICENSE` to `LICENSE-UPSTREAM` (content unchanged); `LICENSE` now holds the MIT license of our code | GitHub reads `LICENSE` for the repository's license; the upstream notice stays in the repository as MIT requires | none |

## Code patches (SPEC §4.3)

All defaults reproduce upstream v1.0.1. Test T4 (`tests/test_simulation.py`, `pytest -m slow`) checks that
with the recorder attached and upstream values, the metrics equal those of untouched upstream (Phase-0
reference runs) exactly; it passed on 2026-11-07 for DSDV defaults and for Greedy (N = 10, λ = 5).

| # | File (lines) | Change | Why | Behaviour change |
|---|---|---|---|---|
| P1 | none (runner) | `experiments/run_one.py` writes `utils.config` before importing the simulator | values read at import time (M3) | none |
| P2 | `utils/config.py` (end), `entities/drone.py:8-9,107` | `ROUTING_PROTOCOL` (default `'dsdv'`) and `ROUTING_PARAMS`; drone installs `routing.registry.get(config.ROUTING_PROTOCOL)` instead of `Dsdv` | select the protocol per run (R7) | none by default |
| P3 | `utils/config.py`, `simulator/simulator.py:63` | `DRONE_SPEED` (default 10) replaces the literal `10` | speed sweep (R4) | none by default |
| P4 | `utils/config.py`, `entities/drone.py:143-147` | `TRAFFIC_RATE` (default 5) replaces `rate = 5`; packets are generated only in `[TRAFFIC_START, TRAFFIC_END]` (default `[0, inf]`) | load sweep (R4); warm-up and drain window | none by default |
| P5 | none (runner) | `MPLBACKEND=Agg`, so upstream's `plt.show()` calls return immediately | headless batch runs (M6) | none |
| P6 | `entities/drone.py`, `mac/csma_ca.py`, `phy/phy.py`, `simulator/metrics.py` | `if hooks.REC is not None: hooks.REC.<event>(...)` at generation, source-queue overflow, route decision, expiry, retry budget, reception (SINR list), TTL drop, transmission, ACK timeout, retry drop, delivery | loss attribution and recomputations (R2, R3) | none: `REC` is `None` unless the runner attaches a recorder, and the recorder only observes (T4) |
| P7 | none (runner) | `INITIAL_ENERGY = 1e9` J | drones otherwise sleep after 14–20 s (M26, D-007) | intended: energy depletion disabled |
