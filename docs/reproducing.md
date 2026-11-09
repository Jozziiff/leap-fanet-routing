# Reproducing the results

Everything below runs from the repository root after `uv sync`. The `make` targets wrap the same commands.

## 1. Check the installation (under a minute)

```bash
make lint     # ruff on our code
make smoke    # one 3-s LEAP-GR simulation with 5 drones
make test     # pytest, about 7 minutes; `make test-slow` adds the golden regression tests
```

## 2. Figures from the committed tables (seconds)

The aggregated results are committed in `results/*.csv`, so the figures can be rebuilt without running a
single simulation:

```bash
make figures  # writes figures/*.png, *.pdf and the paired-statistics tables
```

The PNG figures and the tables come out identical to the committed ones; the PDFs differ only in their
creation timestamp.

## 3. From raw results to tables

The raw per-run JSON files are not in git. Download `results-raw.zip` from the
[v1.0.0 release](https://github.com/Jozziiff/leap-fanet-routing/releases/tag/v1.0.0) and unzip it into
`results/raw/`, or produce them with step 4. Then:

```bash
uv run python -m analysis.aggregate results/raw/exp_a_diagnostic --out results/exp_a.csv
uv run python -m analysis.aggregate results/raw/exp_b_comparison --out results/exp_b.csv
uv run python -m analysis.aggregate results/raw/exp_c_tuning results/raw/exp_c_shadow --out results/exp_c.csv
uv run python -m analysis.aggregate results/raw/exp_d_crosslayer --out results/exp_d.csv
```

These four commands rebuild the committed CSVs row for row. `results/raw/_superseded_selfbug/` holds the LEAP
runs made before the fix of DECISIONS D-018; they are kept for the record and not used.

## 4. Running the simulations

Each experiment is a YAML file in [`experiments/configs/`](../experiments/configs/). The sweep driver runs
every simulation in its own Python process, skips runs whose result file exists (an interrupted sweep
resumes), and splits the work between machines with `--shard i/K`:

```bash
uv run python experiments/sweep.py experiments/configs/exp_a_diagnostic.yaml --workers 4 --dry-run
uv run python experiments/sweep.py experiments/configs/exp_a_diagnostic.yaml --workers 4 --shard 0/2
```

| Config | Runs | Output in `results/raw/` |
|---|---|---|
| `exp_a_diagnostic.yaml` | 231 | `exp_a_diagnostic/` |
| `exp_c_tuning.yaml`, `exp_c_shadow.yaml` | 18 + 5 | `exp_c_tuning/`, `exp_c_shadow/` |
| `exp_b_reactive.yaml`, `exp_b_leap.yaml` | 99 | `exp_b_comparison/` |
| `exp_d_crosslayer.yaml` | 15 | `exp_d_crosslayer/` |
| `exp_e_leap_reactive.yaml` | 33 | exploratory, not in the tables |

Order matters for one step: τ_th is frozen from Exp C before Exp B part 2, with
`experiments/freeze_tau.py` (rule in DECISIONS D-016), which writes `exp_b_leap.yaml` and
`docs/tau_freeze.json`.

**Run time.** A 30-s Greedy run at λ = 1 takes roughly 35·N − 97 seconds of wall time with about six runs in
parallel (about 28 minutes at N = 50); GRAd takes about 3.5 times longer.

**Determinism.** The same seed and code version give bit-identical results, including across machines. The
same seed gives every protocol the same traffic and trajectories, but not the same MAC backoffs.

## 5. Demo

```bash
make demo     # Greedy and LEAP-GR side by side on one seed (experiments/demo.sh)
make slides   # serves the defense slides at http://127.0.0.1:8766/
```
