#!/usr/bin/env bash
# Defense demo: Greedy and LEAP-GR on the same seed, run side by side, then their numbers.
# One short demo run, not a result: the article's numbers come from 3 paired seeds (experiments/sweep.py).
# Usage: experiments/demo.sh [output dir]   (record with: asciinema rec -i 1.5 demo.cast -c experiments/demo.sh)
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-/tmp/leap-demo}"
mkdir -p "$OUT"
RUN=(.venv/bin/python -W ignore experiments/run_one.py --n 20 --speed 20 --rate 2 --seed 1 --sim-time-s 15)
LEAP_PARAMS='{"tau_th_s": 0.25}'  # the threshold frozen for every experiment (docs/DECISIONS.md, D-016)

say() { printf '\n\033[1;34m# %s\033[0m\n' "$*"; sleep 1.2; }
cmd() { printf '\033[1m$ %s\033[0m\n' "$*"; sleep 0.8; "$@"; }

say "The code we run: our commit, and our protocol module in routing/"
cmd git --no-pager log -1 --format='%h  %s'
cmd ls routing/leap/*.py

say "Same swarm, same seed: 20 drones at 20 m/s, 15 s simulated, Greedy and LEAP-GR in parallel"
printf '\033[1m$ run_one.py --protocol greedy  &  run_one.py --protocol leap --params %s\033[0m\n' "$LEAP_PARAMS"
"${RUN[@]}" --protocol greedy --out "$OUT/greedy.json" &
"${RUN[@]}" --protocol leap --params "$LEAP_PARAMS" --out "$OUT/leap.json" &
wait
echo "done: $OUT/greedy.json  $OUT/leap.json"

say "What each run delivered, and why packets were lost"
cmd .venv/bin/python experiments/demo_summary.py "$OUT/greedy.json" "$OUT/leap.json"
sleep 4
