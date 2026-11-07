# Lab notebook

Dated record of what we ran, the exact numbers, and where they come from. Written as we go, so the article,
README and slides can be filled from it later without re-deriving anything. Decisions and their reasons are in
[DECISIONS.md](DECISIONS.md); verified simulator facts in [UPSTREAM_FACTS.md](UPSTREAM_FACTS.md).

**Rules:** every number has a source file. Phase-0 numbers are **pilot numbers** (one seed, runtime harness,
no traffic window); they justify methodology choices and must **not** be reported as results in the article.
Article-ready results come only from the Phase-1+ pipeline (committed configs, `results/`).

---

## 2026-11-07 — Phase 0: setup, benchmark, fact checks (gate G0)

### Environment
| Item | Value |
|---|---|
| Upstream | UavNetSim-v1 tag `v1.0.1` = `a5622c5d0a9f7b62b4e1d5a7dcc8978f34f0c85f` (2026-06-02), verified with `git rev-parse` |
| Python | CPython 3.12.15 via uv 0.13.5, `.venv/` |
| Pinned deps | matplotlib 3.10.1, numpy 2.2.4, openpyxl 3.1.5, Pillow 11.2.1, scikit-opt 0.6.6, simpy 4.1.1 (+ unpinned transitive: scipy 1.18.1, …) |
| Machine | 8 cores, 14 GB RAM, Linux 7.0 |
| Tooling | `experiments/phase0/harness.py` (runtime overrides, D-002), `experiments/phase0/check_facts.py` |
| Raw outputs | `results/phase0/<group>/<run>/result.json` + `time.txt` (`/usr/bin/time`: wall s, peak RSS KB); batch files `results/phase0/batch*.txt` |

Reproduce one run (from a scratch working directory, since upstream writes `running_log.log` to the cwd):
```
.venv/bin/python -W ignore experiments/phase0/harness.py --n 30 --routing greedy --speed 10 --rate 1 \
    --energy off --out result.json      # add --trace for the M20/M22/M26 probes
```

### Benchmark (`results/phase0/bench/`)
Greedy, 30 s simulated, mean speed 10 m/s, energy off, seed 2025, ~6 concurrent runs (D-003).

| N | λ (pkt/s/drone) | Wall (s) | Peak RSS (MB) | Generated | Delivered | PDR (%) | E2E delay (ms) | Upstream hop count | `collision_num` |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 1 | 254 | 116 | 281 | 220 | 78.3 | 7.3 | 1.44 | 20 |
| 10 | 5 | 435 | 118 | 1447 | 1106 | 76.4 | 23.2 | 1.42 | 62 |
| 30 | 1 | 938 | 160 | 892 | 768 | 86.1 | 41.4 | 1.74 | 2460 |
| 30 | 5 | 1049 | 168 | 4488 | 2644 | 58.9 | 2206.6 | 1.63 | 2013 |
| 50 | 1 | 1658 | 244 | 1525 | 1332 | 87.3 | 19.0 | 1.73 | 17561 |
| 50 | 5 | 1711 | 258 | 7568 | 1547 | 20.4 | 3706.6 | 1.49 | 7678 |

Observations:
- Wall time grows ~linearly with N (≈ 35·N − 97 s at λ = 1) and little with λ: the simulator is polling-bound
  (5 µs / 10 µs / 1 µs loops, M32).
- λ = 5 saturates the channel at N ≥ 30 (multi-second delays); λ = 1 does not → D-005.
- N = 10, λ = 1 loses 21.7 % of packets with only 20 interference events: a first hint that low-load losses are
  not collisions (hypothesis H1). Unverified until the recorder exists; `collision_num` is not a loss counter (M17).

### Relative cost per protocol (`results/phase0/proto/`)
N = 30, 3 s simulated, λ = 1, 2 concurrent runs. Wall s: Greedy 70.1 · DSDV 70.8 · OPAR 67.4 · Q-Routing 70.1 ·
QGeo 71.3 · Q-FANET 65.9 · **GRAd 248.1 (≈ 3.5×, flooding, M28)**.

### Fact checks (`results/phase0/m20|m22|m26/`)
| Fact | Setup | Result |
|---|---|---|
| M20 hop count inflated by retries | Greedy N=30 λ=5 | 123/2644 delivered packets (4.7 %) have TTL > true hops (excess: +1 ×111, +2 ×10, +3 ×1, +4 ×1); mean 1.635 (upstream) vs 1.582 (true), +3.4 %; never TTL < hops |
| M20, low load | Greedy N=10 λ=1 | 0/220 inflated (no delivered packet was retried) |
| M22 pairing | N=10 λ=1, Greedy vs DSDV vs GRAd | identical (t, src, dst) for all 281 packets; positions bit-identical (300 samples × 10 drones, max diff 0.0 m); data sub-channel differs for 57/281 (DSDV), 184/281 (GRAd) |
| M26 energy | Greedy N=10 λ=1, energy on | all 10 drones asleep at 14.15 / 16.45 / 19.55 s for 5 / 10 / 20 m/s (analytic 14.1 / 16.4 / 19.5 s; sampler offset 0.05 s) |
| Logging neutral | pristine defaults (DSDV, N=10, λ=5, v=10, energy on) | INFO and WARNING identical: 754 gen, 707 deliv, PDR 93.77 %, delay 24.672 ms, hops 1.634, control 656; wall 110.6 vs 111.7 s |
| Probes neutral (M34) | Greedy N=30 λ=5 traced vs untraced | identical generated/delivered/delay/collision_num/control |

Derived constants (recomputed from `utils/config.py`): R_max = 249.27 m; flight power 1283.4 / 1104.0 / 977.0 /
923.8 W at 5 / 10 / 15 / 20 m/s.

### Compute estimate and seed decision
One protocol × one seed over the 11 configurations ≈ 10 529 s. Tiered plan ≈ 165 worker-h ≈ 13.8 h on 2 laptops ×
6 workers (Exp A ≈ 6.9 h, Exp B ≈ 5.8 h). Team chose the tiered plan → **D-004**.

### For the article (where these facts go)
- **§5 Environment / Table I:** Python 3.12, SimPy 4.1.1, UavNetSim-v1 v1.0.1 (commit hash); energy model
  disabled, with the reason (D-007, M26); R_max = 249.3 m derived from the PHY constants.
- **§5 Metrics:** we report the **true hop count** from the recorder, because upstream's hop count counts
  retransmissions (M20: +3.4 % at N=30, λ=5). `collision_num` is not a loss counter (M17).
- **§5 Methodology:** paired design justified by M22 (identical traffic and trajectories per seed); partial
  pairing (MAC/sub-channel draws differ) stated as a limitation. Seeds per D-004 with the CI-width argument.
- **§5 Threats to validity:** one fresh process per run (M4); λ = 1 reference chosen because λ = 5 saturates
  (D-005); 30-s runs.
- **Oral Q&A:** "Why disable energy?" → D-007 numbers. "Is λ = 1 realistic?" → D-005 numbers.

---

## 2026-11-07 (night) — Phase 1: instrumentation validated

### Golden test T4 (hooks and recorder on, upstream values) — passed
Recorder attached, `run_one.py`, N = 10, speed 10, λ = 5, seed 2025, traffic window [0, ∞):

| Run | Reference (upstream untouched) | Result |
|---|---|---|
| DSDV, energy on (upstream defaults) | `results/phase0/golden/dsdv_default_warning` | bit-identical: 754 gen, 707 deliv, delay 24.672039603960396 ms, hops 1.6336633663366336, control 656, collision_num 0 |
| Greedy, energy off | `results/phase0/bench/n10_l5` | bit-identical: 1447 gen, 1106 deliv, same delay, hops, control 600, collision_num 62 |

### First recorder outputs on those runs (pilot, one seed, no traffic window: not article results)
- DSDV defaults: 35 losses, all `LINK_BREAK`; 12 in flight (drones asleep from 16.45 s, energy on).
- Greedy N=10 λ=5: 339 losses = 125 `LINK_BREAK` + 214 `NO_ROUTE`, 0 `COLLISION`; RR = 0.10
  (107 waiting-list retries). True hop count 1.417 vs upstream 1.42 (M20).
- Reading (to confirm in Exp A): at N = 10, losses come from link breaks and missing neighbours, not from
  collisions, because MAC retries recover most collisions.

### Tests
`pytest`: 26 passed (T2 interface, T5 paired traffic, T6 conservation for 7 protocols, T7 classifier, T8 hop
count), 2 slow golden tests run separately (above).

---

## 2026-11-08 00:45 — Exp C first runs (tuning seeds; tau_th selection, not yet the main comparison)
Source: `leap-dev/results/raw/exp_c_tuning/` (commit `694c7ef`), N = 30, 20 m/s, λ = 1, seeds 100–102.

| Variant | PDR (s100 / s101 / s102) | Link-break losses | Collision / no-route losses | Proactive switches |
|---|---|---|---|---|
| Greedy | 0.817 / 0.801 / 0.793 | 136 / 147 / 151 | 0 / 0 | – |
| LEAP, tau_th = 0.25 s | 0.991 / 0.986 / 0.977 | 0 / 1 / 3 | 0 / 0 | 493 / 513 / 520 |

Sanity checks on seed 100 (event logs): both runs generate the same 742 packets (paired traffic, M22). Greedy
makes 680 transmission attempts to a receiver already out of range (`FAIL_RANGE`); LEAP makes 0.
**Mechanism:** 486 of LEAP's 493 switches (98.6 %) happen with a predicted lifetime of exactly 0, i.e. the
neighbor Greedy picked is, by dead reckoning from its last hello, already out of range. Greedy keeps a neighbor
for 2 s after its last hello (M10) and picks the one closest to the destination (M11), which at 20 m/s is often a
neighbor that has already left; the MAC then spends its 5 retries on it (M12). At small tau_th, LEAP's gain is
mostly this "stale neighbor" filtering. Whether a larger tau_th adds a gain on top (true anticipation) is what the
rest of the sweep (0.5–4 s) and the shadow runs will show. **For the article and Q&A:** say this explicitly; it is
the main "why". A natural reviewer question is whether simply shortening Greedy's 2-s neighbor lifetime would do
the same; answer from data (tau_th sweep), and list "Greedy with a shorter neighbor timeout" as a further control
if time allows.
