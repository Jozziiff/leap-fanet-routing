# Changelog

All notable changes to this project. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2026-11-09

Version defended on 2026-11-09 (Projet 06, Futurs Réseaux Mobiles, RT5, INSAT).

### Added
- LEAP-GR in `routing/leap/`: Greedy forwarding with link-lifetime prediction from hello messages
  (position, velocity, timestamp), proactive next-hop switch below τ_th = 0.25 s, and predictive repair through
  the MAC's `penalize` hook. Variants for the ablation (LEAP-select, reactive control) and a cross-layer option
  weighted by the MAC retransmission rate (bonus B1).
- Observe-only recorder (`instrumentation/`) that gives every lost packet one final cause (link break,
  collision, no route, ...) and counts route recomputations, for the seven existing protocols.
- Experiment tooling: single-run runner, resumable parallel sweep driver with sharding across machines, YAML
  configs for Exp A to E, and the pre-registered τ_th freezing rule.
- Aggregated results (`results/*.csv`), paired statistics and the article's figures (`figures/`).
- The article (`paper/`, IEEEtran), the defense slides (`slides/`) and the defense demo (`experiments/demo.sh`).
- Documentation: architecture, methodology, reproduction guide, design spec, decision log, lab notebook and
  verified facts about the simulator (`docs/`).
- CI (lint, tests, smoke simulation, table reproduction), pre-commit hooks, Makefile, citation file.

### Changed
- `LICENSE` is the MIT license of our code; the upstream MIT notice moved to `LICENSE-UPSTREAM` unchanged.
- `tau_th_s` defaults to 0.25 s, the frozen value, instead of 1.0 s (experiments always passed it explicitly).

### Fixed
- LEAP-GR could select the node itself as next hop through its own hello (DECISIONS D-018). Every LEAP run
  was redone after the fix; the earlier runs are kept apart and not used.

## Upstream

The first commit is UavNetSim-v1 v1.0.1 (commit `a5622c5`) unmodified. Changes to upstream files are listed in
[`PATCHES.md`](PATCHES.md).

[1.0.0]: https://github.com/Jozziiff/leap-fanet-routing/releases/tag/v1.0.0
