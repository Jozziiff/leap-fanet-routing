#!/bin/bash
# Run one Phase-0 simulation in a fresh process and its own working directory.
# usage: run1.sh <run-name> <harness args...>     (outputs go to $RUNS_DIR/<run-name>/)
# Batches were run as:  xargs -P 6 -L 1 ./run1.sh < batch1.txt
set -u
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
RUNS_DIR="${RUNS_DIR:-$PWD/runs}"
name=$1; shift
d="$RUNS_DIR/$name"; mkdir -p "$d"; cd "$d" || exit 1
/usr/bin/time -f "%e %M" -o "$d/time.txt" "$REPO/.venv/bin/python" -W ignore \
    "$REPO/experiments/phase0/harness.py" "$@" --out "$d/result.json" > "$d/stdout.txt" 2> "$d/stderr.txt"
echo "$name done rc=$? $(tail -1 "$d/time.txt")"
