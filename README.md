<h1 align="center">LEAP-GR</h1>

<p align="center"><b>Predicting link breaks in UAV swarms</b><br>
Greedy geographic routing that changes next hop <i>before</i> the radio link fails.</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12-1d5bd8?style=flat-square" alt="Python 3.12">
  <img src="https://img.shields.io/badge/simulator-UavNetSim%20v1.0.1-111111?style=flat-square" alt="UavNetSim v1.0.1">
  <img src="https://img.shields.io/badge/tests-pytest-111111?style=flat-square" alt="tests: pytest">
  <img src="https://img.shields.io/badge/lint-ruff-111111?style=flat-square" alt="lint: ruff">
</p>

<p align="center">
  <img src="docs/media/replay.gif" width="100%" alt="Replay of one packet in the demo run. Greedy sends it to a drone that has already left range and loses it after five attempts; LEAP-GR, on the same seed, switches to another neighbour and delivers it.">
</p>

<p align="center"><i>One packet, two recorded runs, same seed. Greedy (left) sends it to drone 4, which has
already left range, and loses it. LEAP-GR (right) sees the dead link and switches to drone 5.</i></p>

## The idea

In a swarm of drones, neighbours fly out of range all the time. Greedy forwarding sends each packet to the
neighbour closest to the destination, and that neighbour is often the one about to leave. We first measured
exactly why seven existing FANET protocols lose packets, then built a protocol around what we found.

The diagnosis classifies every failed reception as a link break (receiver out of range) or a collision.
Since the MAC retries five times, collisions almost never cost a packet in the end, while link breaks cause
most of the losses.

LEAP-GR (Link-Expiration-Aware Predictive Greedy Routing) targets those breaks. Each node extrapolates its
neighbours' positions from their hello messages and estimates how long each link will last. If Greedy's pick
is about to break, it forwards to a neighbour that will stay in range.

All protocols run with the same MAC, seeds and trajectories. A reactive control, which switches neighbour
after a failed attempt, separates the gain from prediction from the gain from switching at all.

## Results

<img src="docs/media/results.png" alt="Packets delivered at 20 m/s: Greedy 84.0 %, reactive control 95.7 %, LEAP-GR 98.7 %." width="620">

- Link breaks cost Greedy 4.1 % of its packets at 5 m/s and 16.0 % at 20 m/s.
- LEAP-GR delivers more than Greedy in 9 of 11 configurations (paired, 95 % CI), by up to 14.7 points.
- Prediction beats the reactive control by 0.9 to 3.0 points at high speed and density. It loses at 5 m/s
  and when the network is saturated, and the [article](paper/) explains why.
- 98.4 % of LEAP-GR's switches avoid a neighbour that, by its last hello, had already left range but was still
  in Greedy's neighbour table. Most of the gain comes from not trusting stale neighbours.

Unless stated otherwise: 30 UAVs, 1 packet/s per UAV, mean of 3 paired seeds. All figures are in
[`figures/`](figures/).

## How it works

Hello messages carry each UAV's position, velocity and a timestamp. For each neighbour, a node computes the
remaining link lifetime τ̂: the time until their distance exceeds 0.9 R_max (R_max = 249.3 m, derived from
the simulator's radio parameters). Then, per packet and per hop:

1. Take Greedy's choice, the neighbour closest to the destination.
2. If its τ̂ ≥ τ_th (0.25 s), forward to it, exactly like Greedy.
3. Otherwise forward to the neighbour with the most progress among those with τ̂ ≥ τ_th, or keep Greedy's
   choice if there is none.

The MAC is not modified. On an ACK timeout it calls the routing layer's `penalize` hook, which lets
LEAP-GR redirect the remaining attempts. The protocol lives in [`routing/leap/`](routing/leap/).

## Quickstart

You need [uv](https://docs.astral.sh/uv/). It installs Python 3.12 and the pinned dependencies.

```bash
git clone https://github.com/Jozziiff/leap-fanet-routing.git
cd leap-fanet-routing
uv sync
uv run python experiments/run_one.py --protocol leap --params '{"tau_th_s": 0.25}' \
    --n 10 --speed 20 --sim-time-s 10 --traffic-start-s 1 --traffic-end-s 9 --out quick.json
```

This simulates 10 s of a 10-UAV swarm in one or two minutes. `quick.json` holds the configuration, the code
version and the metrics: delivery ratio, delay, loss causes, route recomputations, LEAP events. Swap `leap`
for `greedy`, `grad`, `dsdv`, `opar`, `q_routing`, `qgeo` or `qfanet` to run another protocol.

To run Greedy and LEAP-GR side by side on the same seed, as in the defense demo:

```bash
experiments/demo.sh
```

<details>
<summary>What the demo prints</summary>
<br>
<img src="docs/media/demo-terminal.png" alt="Terminal output of experiments/demo.sh: 403 packets generated; Greedy delivers 329 (81.6 %) and loses 32 to link breaks; LEAP-GR delivers 360 (89.3 %), loses none to link breaks and makes 162 proactive switches." width="100%">
<br>
One seed, for illustration. The results above come from the full sweeps.
</details>

## Reproducing the experiments

Each experiment is a YAML file in [`experiments/configs/`](experiments/configs/). The sweep driver runs every
simulation in a fresh Python process, skips runs whose result already exists, and can split the work across
machines with `--shard i/K`. The same seed and code version give bit-identical results on different machines.

```bash
uv run python experiments/sweep.py experiments/configs/exp_a_diagnostic.yaml --workers 4
uv run python -m analysis.aggregate results/raw/exp_b_comparison --out results/exp_b.csv
uv run python -m analysis.plots --exp-a results/exp_a.csv --exp-b results/exp_b.csv \
    --exp-c results/exp_c.csv --out figures
```

<details>
<summary>All experiments</summary>
<br>

| Config | What it runs | Runs |
|---|---|---|
| `exp_a_diagnostic.yaml` | 7 existing protocols × 11 configurations × seeds 1-3 | 231 |
| `exp_c_tuning.yaml`, `exp_c_shadow.yaml` | τ_th tuning on separate seeds 100-102; prediction quality without acting on it | 18 + 5 |
| `exp_b_reactive.yaml`, `exp_b_leap.yaml` | reactive control, LEAP-select, LEAP-GR × 11 configurations × seeds 1-3 | 99 |
| `exp_d_crosslayer.yaml` | LEAP-GR weighted by the MAC retransmission rate | 15 |
| `exp_e_leap_reactive.yaml` | exploratory: LEAP selection with reactive repair | 33 |

τ_th is frozen from the tuning runs by a rule fixed before the sweep finished
([`experiments/freeze_tau.py`](experiments/freeze_tau.py)). Raw results go to `results/raw/` and are not committed.
</details>

## Repository layout

| Path | Content |
|---|---|
| [`routing/leap/`](routing/leap/) | LEAP-GR: link lifetime, hello packet, neighbour table, protocol |
| [`instrumentation/`](instrumentation/) | observe-only hooks and the recorder behind the loss attribution |
| [`experiments/`](experiments/) | single-run runner, sweep driver, configs, demo |
| [`analysis/`](analysis/) | aggregation, paired statistics, figures |
| [`tests/`](tests/) | pytest suite (`uv run pytest`, slow golden tests with `-m slow`) |
| [`paper/`](paper/) | the article (LaTeX, IEEEtran) |
| [`slides/`](slides/) | the defense slides in HTML, with the recorded demo and its replay |
| [`docs/`](docs/) | specification, decision log, lab notebook, verified simulator facts |
| everything else | UavNetSim-v1 v1.0.1, with our changes listed in [`PATCHES.md`](PATCHES.md) |

Our changes to the simulator do nothing unless switched on: a golden test checks that, with them off, the
metrics are bit-identical to the unmodified simulator.

## Limitations

Free-space channel without fading, Gauss–Markov mobility only, 30-s runs, three seeds per configuration,
energy depletion disabled, and the destination's position is known to the source (as for Greedy). OPAR on
this platform uses the true positions of all UAVs, so it serves as a reference with global knowledge.

## Authors

Built by [Youssef Hamdani](https://github.com/Jozziiff) and Rayen Hamza as Projet 06 of the
*Futurs Réseaux Mobiles* course (RT5, INSAT, 2026/2027), supervised by Dr Mériem Afif.

The simulator is [UavNetSim-v1](https://github.com/Zihao-Felix-Zhou/UavNetSim-v1) by Zihao Zhou *et al.*
([paper](https://arxiv.org/abs/2507.09852), MIT license). Its original README is kept as
[`README_UPSTREAM.md`](README_UPSTREAM.md).
