# LEAP-GR: predicting link breaks in UAV swarms

Where do routing protocols for flying ad hoc networks (FANETs) lose their packets, and can a node that
predicts how long each radio link will last avoid those losses? This repository answers both questions on
the [UavNetSim-v1](https://github.com/Zihao-Felix-Zhou/UavNetSim-v1) simulator (tag `v1.0.1`).

- **Diagnosis.** An exact loss attribution for seven existing protocols (DSDV, Greedy, GRAd, OPAR,
  Q-Routing, QGeo, Q-FANET): each failed reception is classified as a link break (receiver out of range) or
  a collision (interference).
- **LEAP-GR** (Link-Expiration-Aware Predictive Greedy Routing), a new module in
  [`routing/leap/`](routing/leap/). It forwards exactly like Greedy unless Greedy's chosen neighbour is
  predicted to leave radio range within a threshold, in which case it switches to a neighbour predicted to
  stay.
- **A paired comparison** with Greedy, GRAd and a reactive control, using the same MAC, the same seeds and
  the same trajectories, which isolates the gain due to prediction.

Project 06 of the *Futurs Réseaux Mobiles* course, RT5, INSAT, 2026/2027.

## Key findings

At the reference point (30 UAVs, 10 m/s, 1 packet/s per UAV, 3 seeds):

- **Collisions are almost never the final cause of a loss** (at most 0.09 % of generated packets for the
  unicast protocols): the MAC's five attempts absorb them. Link breaks are 99–100 % of the losses that are
  either link breaks or collisions.
- Link breaks cost Greedy 9.8 % of its packets (83 % of its losses), rising from 4.1 % at 5 m/s to 16.0 % at
  20 m/s.
- LEAP-GR versus Greedy, GRAd and the reactive control: *pending the final runs*.

Figures: [`figures/`](figures/). Article: [`paper/`](paper/).

## Quickstart

Requires [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 and the pinned dependencies).

```bash
git clone git@github.com:Jozziiff/leap-fanet-routing.git
cd leap-fanet-routing
uv sync
uv run python experiments/run_one.py --protocol leap --params '{"tau_th_s": 0.25}' \
    --n 10 --speed 20 --sim-time-s 10 --traffic-start-s 1 --traffic-end-s 9 --out quick.json
```

This simulates 10 s of a 10-UAV swarm with LEAP-GR in about 1–2 minutes and writes `quick.json`: the
configuration, the code version, the upstream metrics and our metrics (PDR, delay, loss causes,
recomputations, LEAP events). Replace `leap` by any name in [`routing/registry.py`](routing/registry.py)
(`greedy`, `grad`, `dsdv`, `opar`, `q_routing`, `qgeo`, `qfanet`).

## Reproducing the experiments

Each experiment is a YAML file in [`experiments/configs/`](experiments/configs/). The sweep driver runs one
fresh Python process per simulation (the simulator keeps global state), skips runs whose result file exists,
and can split the work across machines with `--shard i/K`:

```bash
uv run python experiments/sweep.py experiments/configs/exp_a_diagnostic.yaml --workers 4 --dry-run
uv run python experiments/sweep.py experiments/configs/exp_a_diagnostic.yaml --workers 4 --shard 0/2
```

| Config | What it runs | Runs |
|---|---|---|
| `exp_a_diagnostic.yaml` | 7 existing protocols × 11 configurations × seeds 1–3 | 231 |
| `exp_c_tuning.yaml`, `exp_c_shadow.yaml` | threshold tuning on separate seeds 100–102; prediction quality without acting on it | 18 + 5 |
| `exp_b_reactive.yaml`, `exp_b_leap.yaml` | reactive control, LEAP-select, LEAP-GR × 11 configurations × seeds 1–3 | 99 |
| `exp_d_crosslayer.yaml` | LEAP-GR with cross-layer weighting by the MAC retransmission rate | 15 |
| `exp_e_leap_reactive.yaml` | exploratory: LEAP selection with reactive repair | 33 |

A 30-s run takes roughly 35·N − 97 s of wall time for Greedy at 1 packet/s with several runs in parallel
(GRAd about 3.5 times longer). Raw results go to `results/raw/` (not committed). Then:

```bash
uv run python -m analysis.aggregate results/raw/exp_b_comparison --out results/exp_b.csv
uv run python -m analysis.plots --exp-a results/exp_a.csv --exp-b results/exp_b.csv \
    --exp-c results/exp_c.csv --out figures
```

The threshold is frozen from the tuning runs by a rule fixed before the sweep finished:
[`experiments/freeze_tau.py`](experiments/freeze_tau.py).

The same seed and code version reproduce a run bit for bit: runs computed on two different machines gave
identical results.

## How LEAP-GR works

Hello messages carry each UAV's position, velocity and a timestamp. A node extrapolates each neighbour's
position and computes the remaining link lifetime τ̂ as the time until the distance exceeds 0.9 R_max
(R_max = 249.3 m, derived from the simulator's radio parameters): the larger root of
‖Δp + Δv τ‖ = R. Then, per packet and per hop:

1. take Greedy's choice (the neighbour closest to the destination);
2. if its τ̂ is at least τ_th, forward to it, exactly like Greedy;
3. otherwise forward to the neighbour with the most progress among those with τ̂ ≥ τ_th, or keep Greedy's
   choice if there is none.

On an ACK timeout, the MAC calls the routing layer's `penalize` hook; LEAP-GR can redirect the remaining
attempts there without any change to the MAC. Details, equations and Algorithm 1 are in the
[article](paper/).

## Repository layout

| Path | Content |
|---|---|
| `routing/leap/` | LEAP-GR: link lifetime, hello packet, neighbour table, protocol |
| `instrumentation/` | observe-only hooks and the recorder (loss attribution, recomputations) |
| `experiments/` | single-run runner, sweep driver, configs, threshold freezing, animation |
| `analysis/` | aggregation, paired statistics, figures |
| `tests/` | pytest suite (`uv run pytest`; the slow golden tests: `uv run pytest -m slow`) |
| `docs/` | specification, decisions, lab notebook, verified facts about the simulator |
| `paper/` | the article (LaTeX, IEEEtran) |
| everything else | UavNetSim-v1 v1.0.1; our changes to it are listed in [`PATCHES.md`](PATCHES.md) |

Our modifications to the simulator are behaviour-neutral by default: with our features off, a golden test
checks that the upstream metrics are bit-identical to the unmodified simulator.

## Limitations

Free-space channel without fading, Gauss–Markov mobility only, 30-s runs, three seeds per configuration,
energy depletion disabled, destination positions known to the source (as for Greedy). OPAR on this platform
uses the true positions of all UAVs, so it is a reference with global knowledge, not a distributed protocol.

## Credits

UavNetSim-v1 is by Zihao Zhou *et al.* ([paper](https://arxiv.org/abs/2507.09852),
[repository](https://github.com/Zihao-Felix-Zhou/UavNetSim-v1), MIT license); its README is kept as
[`README_UPSTREAM.md`](README_UPSTREAM.md). Supervision: Dr Mériem Afif, INSAT.

Authors: Youssef Hamdani and Rayen Hamza.
