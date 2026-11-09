# Shortcuts for the commands in docs/reproducing.md. Every target runs through uv (Python 3.12, pinned deps).
.PHONY: install lint test test-slow smoke figures paper demo slides

install:
	uv sync

lint:
	uv run ruff check .

test:
	uv run pytest

test-slow:
	uv run pytest -m slow

# One 3-s LEAP-GR run with 5 drones; the result goes to results/raw/ (not committed).
smoke:
	uv run python experiments/run_one.py --protocol leap --n 5 --sim-time-s 3 \
		--traffic-start-s 0.5 --traffic-end-s 2.5 --out results/raw/smoke.json

# Figures and paired-statistics tables from the committed aggregated results.
figures:
	uv run python -m analysis.plots --exp-a results/exp_a.csv --exp-b results/exp_b.csv \
		--exp-c results/exp_c.csv --exp-d results/exp_d.csv --out figures

paper:
	cd paper && latexmk

demo:
	experiments/demo.sh

slides:
	slides/serve.sh
