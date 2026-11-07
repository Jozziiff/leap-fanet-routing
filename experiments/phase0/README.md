# Phase 0 tooling (archived)

Scripts used on 2026-11-07 to benchmark UavNetSim-v1 v1.0.1 and to confirm UPSTREAM_FACTS M20, M22 and M26
before any upstream file was modified. They are kept so the numbers in `docs/LAB_NOTEBOOK.md` (Phase 0) and
`results/phase0/` stay reproducible. Later experiments use the patched simulator and `experiments/run_one.py`.

- `harness.py`: runs one simulation with runtime overrides (routing class, Poisson rate, mean speed, energy,
  logging level) and optional observe-only probes. Rationale: `docs/DECISIONS.md` D-002.
- `check_facts.py`: reads traced results and prints the M20 / M22 / M26 checks.
- `../../results/phase0/batch*.txt` and `run1.sh`: the exact batches that were run.

Example (run from a scratch directory, since upstream writes `running_log.log` to the working directory):

```
uv run python <repo>/experiments/phase0/harness.py --n 30 --routing greedy --speed 10 --rate 1 \
    --energy off --trace --out result.json
uv run python <repo>/experiments/phase0/check_facts.py --m20 result.json
```
Each run's args.out was normalised to its repo-relative path after the runs; no result field changed.
