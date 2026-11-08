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

---

## 2026-11-08 02:47 — Exp C complete: tau_th frozen at 0.25 s (pre-registered rule D-016)
Source: `leap-dev/results/raw/exp_c_tuning/` (commit `694c7ef`, 18 runs, 0 failed), summary in
`docs/tau_freeze.json`, frozen config `experiments/configs/exp_b_leap.yaml` (commit `b550e44`, written and
pushed by `experiments/freeze_tau.py` without manual intervention). N = 30, 20 m/s, λ = 1, seeds 100–102.

| tau_th (s) | 0.25 | 0.5 | 1 | 2 | 4 | Greedy |
|---|---|---|---|---|---|---|
| mean PDR | 0.9846 | 0.9809 | 0.9719 | 0.9329 | 0.8569 | 0.8036 |

Per seed (s100 / s101 / s102): 0.25 s → 0.991 / 0.986 / 0.977; 0.5 s → 0.987 / 0.984 / 0.973; 1 s → 0.978 /
0.978 / 0.959; Greedy → 0.817 / 0.801 / 0.793. Rule: smallest tau_th within 0.5 pp of the best mean ⇒ 0.25 s
(it is also the best mean). **PDR decreases monotonically with tau_th**: a larger threshold rejects more links
that would still have carried the packet, so LEAP switches to neighbours with less progress or finds none. For
Q&A ("why not smaller than 0.25 s?"): the grid was fixed before the sweep; at 0.25 s the residual link-break
losses are already 0–3 per run, so a smaller value can only win on the remaining ~1.5 % of losses, which are not
link breaks. Also say plainly: at this threshold the gain is mostly stale-neighbour filtering (entry above).

## 2026-11-08 — Exp C shadow mode: prediction quality (seed 100, Greedy behaviour unchanged)
Source: `leap-dev/results/raw/exp_c_shadow/` (commit `694c7ef`, 5 runs). LEAP computes and logs warnings but
always forwards like Greedy. Sanity check: PDR 0.8167 in all 5 runs, identical to Greedy seed 100.

| Warning window (s) | 0.25 | 0.5 | 1 | 2 | 4 |
|---|---|---|---|---|---|
| precision (warned links that did break) | 0.398 | 0.441 | 0.492 | 0.548 | 0.562 |
| recall (out-of-range attempts warned) | 680/680 | 680/680 | 680/680 | 680/680 | 680/680 |
| mean lead time (s) | 0.013 | 0.052 | 0.150 | 0.351 | 0.770 |
| median lead time (s) | 0.0044 | 0.0045 | 0.0046 | 0.0047 | 0.0048 |

Reading: every transmission to an out-of-range receiver was predicted (recall 1.0 at every window), but the
median lead time is ~4.5 ms, i.e. at decision time the link is predicted to be already broken: the same
stale-neighbour effect. Long lead times exist (up to ~4 s at the 4-s window) but are a minority. About half the
warnings are false alarms (link survived); this is the cost side of a larger tau_th and matches the PDR drop
above. Goes in article §5 (prediction quality, R7) and in the Q&A defence of the mechanism.

## 2026-11-08 05:17 — Exp B complete on the Windows PC (99 runs)
Source: zip of `results/raw/exp_b_comparison/` from the Windows PC, extracted into
`leap-work/results/raw/exp_b_comparison/`. 33 runs each of `greedy_reactive` (commit `d845f8c`), `leap_select`
and `leap` (commit `b550e44`), all with clean trees, 11 configs × seeds 1–3. Python 3.12.16 on that machine
(3.12.15 on the laptop). Greedy and GRAd baselines come from Exp A.

## 2026-11-08 09:50 — Exp A: completing the Greedy baseline on the laptop
Exp A shard 0 (laptop) finished at 08:00 (116 runs, 0 failed, 9.2 h). Shard 1 (Rayen's PC) not yet collected;
it contains 18 of the 33 Greedy runs needed as the paired baseline of Exp B. These 18 runs are re-run on the
laptop from the same frozen commit `dd71430` (same `run_one.py` arguments; subset config with only the `greedy`
variant, kept in untracked `notes/`). When Rayen's shard arrives, the overlap is a cross-machine reproducibility
check: the simulator is deterministic for a given seed and commit (golden test T4), so the files must match.

## 2026-11-08 10:35 — Exp A complete (231 runs) and cross-machine reproducibility
Rayen's shard 1 arrived (115 runs, 0 failed, commit `dd71430`, clean tree, Python 3.12.12, 8.4 h). The laptop
re-run of the missing Greedy runs had finished 4 runs; all 4 are **identical in every metric** to Rayen's files
(`greedy/n40_v10_r1_s{1,3}`, `greedy/n50_v10_r1_s{1,3}`; e.g. PDR 0.91878 on both), across two machines and
Python 3.12.15 vs 3.12.12. The re-run was stopped and Rayen's files used; Exp A now has 33 runs for each of the
7 protocols. **For Q&A / README:** results are reproducible bit for bit from the seed and the commit.

## 2026-11-08 10:45 — Exp B results: paired comparison (seeds 1–3, 95 % CI, paired t-test)
Source: `results/exp_b.csv` + `results/exp_a.csv` (Greedy, GRAd), table `figures/table_paired.csv`, figures
`figures/fig4_pdr.pdf`, `fig5_cost.pdf`, `fig6_ablation.pdf`. PDR differences in percentage points.

| Config (N, v, λ) | LEAP − Greedy | Reactive − Greedy | LEAP − Reactive |
|---|---|---|---|
| 10, 10, 1 | −0.33 ± 4.51 (ns) | +2.26 ± 4.10 (ns) | −2.58 ± 3.00 (ns) |
| 20, 10, 1 | +2.94 ± 0.73 * | +2.81 ± 0.75 * | +0.14 ± 0.29 (ns) |
| 30, 5, 1 | −0.01 ± 2.27 (ns) | +3.19 ± 1.74 * | −3.20 ± 0.70 * |
| 30, 10, 0.5 | +7.50 ± 3.12 * | +7.68 ± 2.02 * | −0.17 ± 1.68 (ns) |
| 30, 10, 1 | +6.96 ± 1.74 * | +7.65 ± 1.22 * | −0.69 ± 2.17 (ns) |
| 30, 10, 2 | +5.27 ± 2.13 * | +6.50 ± 1.26 * | −1.23 ± 0.87 * |
| 30, 10, 5 | −0.56 ± 7.33 (ns) | +5.94 ± 2.82 * | −6.50 ± 4.75 * |
| 30, 15, 1 | +9.46 ± 0.33 * | +8.30 ± 0.16 * | +1.16 ± 0.43 * |
| 30, 20, 1 | +13.72 ± 2.05 * | +11.77 ± 3.02 * | +1.95 ± 0.97 * |
| 40, 10, 1 | +8.29 ± 2.39 * | +7.39 ± 1.53 * | +0.90 ± 0.87 * |
| 50, 10, 1 | +9.42 ± 2.31 * | +7.38 ± 1.32 * | +2.04 ± 1.20 * |

`*` = CI excludes 0 (all such cells have p < 0.05). Readings:
1. LEAP beats Greedy significantly in 8 of 11 configurations; the gain grows with speed (+9.5 pp at 15 m/s,
   +13.7 pp at 20 m/s) and density (+8.3 / +9.4 pp at N = 40 / 50). No gain at 5 m/s, at N = 10 or at λ = 5.
2. The reactive control (switch next hop after an ACK timeout, no prediction) recovers most of the same gain
   and beats Greedy in 10 of 11 configurations.
3. LEAP beats the reactive control exactly where links break fastest (15–20 m/s, N = 40–50: +0.9 to +2.0 pp)
   and loses where breaks are rare or load is high (5 m/s: −3.2 pp; λ = 2: −1.2 pp; λ = 5: −6.5 pp). Plausible
   cause, to check: LEAP rejects the best-progress neighbour on prediction alone and does not rescue packets
   after an ACK timeout caused by collisions, which dominate at high load; the reactive control does.
4. LEAP − LEAP-select is 0.00 in 6 configurations and |≤ 0.38| pp elsewhere (ns): predictive repair almost
   never fires on top of predictive selection (bit-identical runs where it never fires).
5. LEAP vs GRAd: +47 to +87 pp where significant (9 of 11). GRAd pays with delays above 2 s and 4–6× more
   control traffic per delivered packet (Fig. 5). Delay and control overhead of LEAP ≈ Greedy.
Goes to article §5 (results, "explain why") and is the core of the oral's results slide.

## 2026-11-08 11:30 — LEAP self-selection bug found; LEAP-based results superseded (D-018)
**All LEAP, LEAP-select, reactive-control, LEAP+XL and Exp C LEAP numbers above this entry are superseded** and
must not be reported; the paired table of the 10:45 entry is kept only as a record of what led to the bug.
How it was found: LEAP left packets neither delivered nor dropped at the end of every run (N = 30, λ = 1:
27.0 / 20.7 / 14.7 per run at 5 / 10 / 20 m/s; Greedy 0.0), although traffic stops 3 s before the end and the
mean delay is ~12 ms at 5 m/s. Event trace of packet 330 (`leap/n30_v5_r1_s1`): node 9 logs
`PROACTIVE_SWITCH` to node 9, transmits to itself, and the packet disappears. Count over Exp B: 586 self-decisions
in 17 929 LEAP switches and repairs; 129 in 5 097 repairs of the reactive control. Cause M40, fix `2327be4`.
Old files: `leap-work/results/raw/_superseded_selfbug/`, `leap-dev/results/raw/_superseded_selfbug/`.

Exp D (superseded run, commit `1016302`, 15 runs) is still informative about the mechanism, which the bug does
not touch: at λ = 1 LEAP+XL produced runs identical to LEAP in 3 of 4 speeds, because there are only 7–11 ACK
timeouts per run, so the moving average stays near 0 and never changes the ranking. Only λ = 5 (294 timeouts
per run) gives XL something to react to. To be confirmed on the re-run.

Re-run plan (11:35): Exp C LEAP runs on the laptop from `e1dbd01` (frozen worktree `leap-dev`), then tau_th
re-frozen by D-016; reactive control re-run on the Windows PC in parallel (does not depend on tau_th); then
Exp B LEAP-select + LEAP split between the Windows PC and Rayen's PC, Exp D and Exp E on the laptop.

## 2026-11-08 12:50 — Demo animation rendered (oral hook, Video 2)
`experiments/animate.py --tau-th-s 0.25` at commit `a15c769` (fixed code, frozen tau_th; hash shown on
screen). Two recorded runs on the same seed: N = 20, 20 m/s, λ = 2 packets/s per UAV, seed 1, 20 s
(traffic 1–19 s). Greedy: 89 packets lost to link breaks, PDR 0.858. LEAP-GR: 0 link-break losses, PDR 0.981,
350 proactive switches and repairs. Output `figures/leap_vs_greedy.mp4` (1920×1080, 20 s, 20 fps) and `.gif`,
not tracked in git (release assets). Top view only: altitude is not drawn. Demo numbers, one seed: never
quoted as results.

## 2026-11-08 12:15 — Exp C re-run (fixed code): tau_th re-frozen at 0.25 s
Source: `leap-dev/results/raw/exp_c_tuning/` (LEAP runs at `e1dbd01`, 15 runs, 0 failed; Greedy runs reused),
`docs/tau_freeze.json`, commit `a15c769`. Mean PDR (seeds 100–102, N = 30, 20 m/s, λ = 1):

| tau_th (s) | 0.25 | 0.5 | 1 | 2 | 4 | Greedy |
|---|---|---|---|---|---|---|
| mean PDR | 0.9919 | 0.9896 | 0.9855 | 0.9765 | 0.9502 | 0.8036 |

Per seed at 0.25 s: 0.9946 / 0.9892 / 0.9918 (buggy code: 0.9906 / 0.9865 / 0.9767); 0 packets left in flight
(buggy: 7 / 9 / 14). Same rule, same choice; the large thresholds gained most from the fix (4 s: 0.857 → 0.950).

## 2026-11-08 14:50 — Exp B complete with the fixed code (99 runs): paired results
Sources: Windows PC (reactive control, commit `e02ae22`, 33 runs; LEAP-select + LEAP shard 0/2, `6d2826a`,
33 runs) and Rayen's PC (shard 1/2, `6d2826a`, 33 runs); all clean trees; `6d2826a` = `a15c769` + one docs
commit. 0 packets in flight in every run with λ < 5. Tables `results/exp_b.csv`, `figures/table_paired.csv`;
figures `fig4_pdr`, `fig5_cost`, `fig6_ablation`. PDR differences in percentage points, 3 paired seeds:

| Config (N, v, λ) | LEAP − Greedy | Reactive − Greedy | LEAP − Reactive |
|---|---|---|---|
| 10, 10, 1 | +1.95 ± 4.27 (ns) | +2.26 ± 4.10 (ns) | −0.31 ± 0.66 (ns) |
| 20, 10, 1 | +3.01 ± 0.75 * | +2.81 ± 0.75 * | +0.21 ± 0.00 * (1 packet per seed) |
| 30, 5, 1 | +2.55 ± 1.85 * | +3.19 ± 1.74 * | −0.65 ± 0.52 * |
| 30, 10, 0.5 | +8.67 ± 2.87 * | +7.68 ± 2.02 * | +1.00 ± 1.08 (ns) |
| 30, 10, 1 | +8.67 ± 0.56 * | +7.84 ± 0.95 * | +0.83 ± 0.66 * |
| 30, 10, 2 | +6.90 ± 0.91 * | +6.61 ± 0.99 * | +0.29 ± 0.10 * |
| 30, 10, 5 | −0.14 ± 7.31 (ns) | +4.82 ± 4.67 * | −4.95 ± 2.65 * |
| 30, 15, 1 | +10.34 ± 0.43 * | +8.30 ± 0.75 * | +2.04 ± 1.05 * |
| 30, 20, 1 | +14.73 ± 2.81 * | +11.72 ± 3.15 * | +3.01 ± 0.43 * |
| 40, 10, 1 | +8.33 ± 2.37 * | +7.42 ± 1.65 * | +0.90 ± 0.72 * |
| 50, 10, 1 | +9.42 ± 2.31 * | +7.38 ± 1.32 * | +2.04 ± 1.20 * |

LEAP − LEAP-select: exactly 0 in 7 configurations, |≤ 0.37| pp (ns) in the others: predictive repair never
matters once selection is predictive. LEAP − GRAd: +47 to +87 pp, significant in 9 of 11.

Mechanism (means per run, `results/exp_b.csv`):
- 30/20/1: link-break losses Greedy 115.0, reactive 30.7, LEAP 8.7; ACK timeouts 575.7 / 242.3 / 44.7. The
  reactive control must fail once before switching; LEAP avoids the failed attempt. LEAP hops 2.00 vs 1.69.
- 50/10/1: link-break losses 117.0 / 25.3 / 0.0; ACK timeouts 589.3 / 226.3 / 4.3; only 4 risky forwards per
  run: in a dense swarm a safe alternative almost always exists.
- 30/5/1: link-break losses 29.7 / 6.7 / 9.7; LEAP makes 30 risky forwards per run (no safe neighbour with
  progress) and, unlike the reactive control, does not rescue a packet after an ACK timeout; hops 2.03 vs 1.81.
- 30/10/5: LEAP delivers 2617 vs 2805 for the reactive control; expired 370.7 vs 264.0; delay 2885 vs 2568 ms;
  hops 1.74 vs 1.67. At saturation the extra hops of the safer, shorter links add queueing, and packets expire.
Exp E (LEAP selection + reactive repair) tests whether adding the rescue closes the 5 m/s and λ = 5 gaps.

## 2026-11-08 13:20 — Exp D re-run (fixed code, bonus B1): no PDR gain
Source: `leap-dev/results/raw/exp_d_crosslayer/` (commit `a15c769`, 15 runs, 0 failed), paired with Exp B's
LEAP runs; figure `fig8_crosslayer`. LEAP+XL − LEAP, PDR: +0.19 ± 0.21 (5 m/s), +0.09 ± 0.20 (10), +0.05 ± 0.20
(15), +0.19 ± 0.54 (20), −1.99 ± 3.47 (λ = 5) pp, none significant. ACK timeouts at λ = 5: 273.7 → 239.3 per run
(−34.3 ± 13.7, p = 0.0085); elsewhere ns. Reading: XL lowers retransmissions where there are many, but the
neighbours it avoids were not where packets were lost (losses at λ = 5 are queue expiry and no route). Null
result, reported as such. λ = 5 runs end with 521–686 packets still queued, like Greedy (410–598): saturation.
