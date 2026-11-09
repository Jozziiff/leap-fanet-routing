# Decision log

Implementation-time decisions, one entry each, newest last. Design decisions made during planning are in
[SPEC §6.6](SPEC.md) and SPEC §16; this file covers what we decided while building, with the evidence.

Each entry gives the context, the decision, the alternatives we rejected, why, and a short **defence**: the
answer we would give if Dr Afif questions it during Q&A. Numbers come from files in `results/` and are also in
[LAB_NOTEBOOK.md](LAB_NOTEBOOK.md).

Status values: **accepted** (in force), **superseded by D-xxx**, **revisit at <gate>**.

---

## D-001 — Import upstream with `git archive` of the tag
- **Date / phase:** 2026-11-07, P0. **Serves:** R1.
- **Context:** the project folder already held our `docs/` and planning notes. The SPEC wants the upstream tree at
  the root and a first commit that is pristine upstream (§10.1, §18.3).
- **Decision:** clone upstream to a scratch folder, check that `v1.0.1` resolves to
  `a5622c5d0a9f7b62b4e1d5a7dcc8978f34f0c85f`, then `git archive v1.0.1 | tar -x` into the project.
- **Alternatives rejected:** copying a working tree (could carry untracked or modified files); cloning into the
  project (brings upstream's `.git` history into our future repo).
- **Why:** `git archive` writes exactly the files of the tagged commit and nothing else. We checksummed `docs/*`
  and the planning notes before and after: unchanged. No upstream path collides with ours.
- **Defence:** "Our tree is byte-for-byte the tagged release; you can check it with `git diff` against the upstream
  tag."
- **Status:** accepted.

## D-002 — Phase 0 uses a runtime harness; upstream files stay untouched
- **Date / phase:** 2026-11-07, P0. **Serves:** R1, R4 (benchmark), SPEC §18.3.
- **Context:** the benchmark needs Greedy and λ = 1, but upstream hard-codes DSDV (`entities/drone.py:106`),
  `rate = 5` (`drone.py:142`) and `speed = 10` (`simulator/simulator.py:63`). The real patches (P1–P7) belong
  to Phase 1, and the first commit must be pristine upstream.
- **Decision:** `experiments/phase0/harness.py` overrides these at runtime: config set before import, routing
  class rebound in `entities.drone`, λ through a `random.Random` subclass, speed set after construction with
  upstream's own formulas.
- **Alternatives rejected:** editing upstream now (dirties the pristine tree before the repo exists; P1–P7 would
  be written twice); benchmarking at upstream's λ = 5 only (λ = 1 is our reference point, SPEC §8.1).
- **Why it is faithful:** in Python 3.12 `expovariate` makes exactly one `random()` call, so replacing the rate
  leaves the random stream intact; inter-arrival times scale by 5/λ and destinations are drawn as before.
  Observe-only probes were shown to change nothing (M34: traced and untraced runs give identical metrics).
- **Defence:** "Phase 0 did not modify the simulator. The permanent changes are listed one by one in
  `PATCHES.md`, and the golden test checks that they are neutral by default."
- **Status:** accepted for P0 only. Superseded by patches P1–P7 in Phase 1 (the harness is throwaway tooling;
  keep or delete it at repo creation).

## D-003 — Benchmark with ~6 concurrent runs, not one run alone
- **Date / phase:** 2026-11-07, P0. **Serves:** seed-plan decision (D-004).
- **Context:** the sweeps will run as parallel worker processes, one simulation per fresh process (M4).
- **Decision:** time the 6 benchmark configurations concurrently on the 8-core laptop.
- **Alternatives rejected:** timing each run alone (faster per run, so it would under-estimate a parallel sweep).
- **Why:** it measures the regime the experiments will actually run in.
- **Limits (stated honestly):** we did not measure single-run time; the concurrency level dropped from 6 as runs
  finished and the fact-check batch was started alongside (it kept ~6 processes busy). 7 workers would be slower
  per run than what we measured, so we plan for 6.
- **Defence:** "The timings are what one laptop delivers when it runs the sweep, not best-case numbers."
- **Status:** accepted.

## D-004 — Seed plan: tiered 3 / 5 seeds, kept after the G0 benchmark
- **Date / phase:** 2026-11-07, G0. Decided by the team (Youssef), on the recommendation below. **Serves:** R4,
  R8, R9 and the 25 % rigour criterion.
- **Context:** SPEC §8.2 set a tiered plan and a rule to revisit it after measuring run time.
- **Decision:** keep the tiered plan unchanged:

  | Experiment | Seeds | Worker-hours | Wall time on 2 laptops × 6 workers |
  |---|---|---|---|
  | A. Diagnostic, 7 protocols × 11 configs | 3 | 83.4 | 6.9 h |
  | B. Core comparison (3 new variants × 5 seeds; Greedy and GRAd +2 seeds over A) | 5 | 70.2 | 5.8 h |
  | C. τ_th tuning (seeds 100–102) | 3 | 3.9 | 0.3 h |
  | D. Bonus | 3 | ≈ 7.8 | ≈ 0.7 h |
  | **Total** | | **≈ 165** | **≈ 13.8 h** |

  The first 3 test seeds of Exp B are the 3 seeds of Exp A, so Greedy and GRAd runs from A are reused in B.
  Exact seed values are fixed in the Phase-1 runner config.
- **How the SPEC rule was applied:** the rule says "keep the tiered plan if it fits in one night (~10 h)". The
  total (≈ 13.8 h) does not fit one night, but each experiment does. They run in different phases anyway:
  A at the end of P1, B in P3, after τ_th is frozen by C. So we apply the rule per experiment.
- **Alternatives rejected:**
  - All experiments at 3 seeds (≈ 121 worker-h, ≈ 10.1 h): cheaper, but the 95 % CI of the main claim is twice
    as wide (half-width t·s/√n: 4.303/√3 = 2.48·s at n = 3 vs 2.776/√5 = 1.24·s at n = 5, s = per-seed standard deviation).
  - Tiered, but GRAd at 3 seeds in B (≈ 145 worker-h, ≈ 12.1 h): kept as the first fallback (below).
- **Why:** the comparison of LEAP with Greedy (and the ablation) is our main scientific claim and carries 25 % of
  the grade; it gets the tighter intervals. The diagnostic describes large differences between protocols, where
  3 seeds are enough.
- **Fallback, in order:** if a night overruns, (1) run GRAd at 3 seeds in B (saves ≈ 20 worker-h, ≈ 1.7 h of wall
  time); (2) all-3-seeds. Any fallback used is written here and stated in the article.
- **Assumptions behind the estimate [EST]:** speed and λ ∈ {0.5, 2} cost about the same as measured configs; the
  GRAd factor 3.5 comes from 3-s runs at N = 30; the second laptop is similar to this one; ≈ 0.25 GB per run.
  We re-check against the actual wall time of the first Exp-A night.
- **Defence:** "We measured run time before choosing seeds. The main claim has 5 paired seeds; its CI is half as
  wide as with 3, and we use paired t-tests because traffic and trajectories are identical across protocols for
  a given seed (M22)."
- **Status:** superseded by D-009 for the defense version (3 seeds everywhere); restored after the defense.

## D-005 — λ = 1 pkt/s per drone stays the reference load
- **Date / phase:** 2026-11-07, G0. **Serves:** R4, H1/H3.
- **Context:** SPEC §8.1 assumed [EST] that upstream's λ = 5 saturates the channel for N ≥ 30.
- **Decision:** keep λ = 1 as the reference for S1 and S2; λ = 5 appears only in the load sweep S3.
- **Evidence (Greedy, 30 s, seed 2025):** λ = 5 gives PDR 58.9 % / delay 2.2 s at N = 30 and 20.4 % / 3.7 s at
  N = 50; λ = 1 gives 86.1 % / 41 ms and 87.3 % / 19 ms.
- **Why:** with a saturated channel, queueing and collisions hide link-break losses, which is what we study.
- **Defence:** "At λ = 5 the network is congested, with multi-second delays, so most losses come from the MAC.
  λ = 1 isolates mobility effects; S3 still shows what happens under load."
- **Status:** accepted.

## D-006 — Headless runs log at WARNING
- **Date / phase:** 2026-11-07, P0. **Serves:** SPEC §4.3 (P1), reproducibility.
- **Decision:** set `config.LOGGING_LEVEL = WARNING` before import.
- **Evidence:** pristine defaults (DSDV, N = 10, seed 2025) give identical metrics at INFO and WARNING (754
  generated, 707 delivered, delay 24.672 ms); wall time 110.6 s vs 111.7 s; INFO writes 3.3 MB per run.
- **Why:** behaviour-neutral, and avoids hundreds of MB of logs across ≈ 500 runs. Speed was *not* the reason;
  we measured no speed-up (M5 corrected).
- **Defence:** "Logging only writes text; it does not touch random numbers, and the identical-metrics test shows it."
- **Status:** accepted.

## D-007 — Energy depletion disabled (patch P7) is required, not optional
- **Date / phase:** 2026-11-07, G0 (confirms the SPEC v0.2 decision). **Serves:** validity of S2.
- **Evidence:** with the default energy model, all drones sleep at 14.15 / 16.45 / 19.55 s for 5 / 10 / 20 m/s
  (N = 10, 30-s runs), i.e. the slowest drones die first and the second half of every run is dead.
- **Why:** with energy on, the speed sweep would measure battery life, not mobility.
- **Defence:** "Energy is out of the subject's scope. Left on, it would end every run before the halfway point
  and bias the speed sweep against slow drones. We say so in Table I."
- **Status:** accepted.

---

## D-008 — Repository setup
- **Date / phase:** 2026-11-07, before P1. Decided by the team (Youssef). **Serves:** code-quality criterion (10 %),
  SPEC §18.
- **Decisions:**
  1. **Owner:** Youssef's GitHub account (`Jozziiff`), repository `leap-fanet-routing`, Rayen as collaborator.
  2. **Visibility:** private until the defense (Mon 2026-11-09), then public with release `v1.0.0`.
  3. **What is tracked:** upstream code, our code, `docs/` (SPEC, UPSTREAM_FACTS, DECISIONS, LAB_NOTEBOOK),
     `PATCHES.md`, Phase-0 tooling and evidence. Not tracked: virtual environment, caches, raw results, personal
     notes (`notes/`) and local tool settings. The assistant rules file `CLAUDE.md` was first kept untracked,
     then tracked on 2026-11-07 at the team's request so both teammates work from the same rules.
  4. **Commit authorship:** commits carry the author's name only, no co-author trailers.
  5. **History layout:** commit 1 = upstream `v1.0.1` unmodified (tree hash checked against the tag); commit 2
     removes the IDE and bytecode files shipped upstream (M33); then our files in small Conventional Commits.
  6. **Dependencies:** `pyproject.toml` + `uv.lock` pin the full set (incl. transitive) with the same versions as
     the Phase-0 runs; upstream's `requirements.txt` is left as shipped.
  7. **Phase-0 tooling and results committed** (`experiments/phase0/`, `results/phase0/`, 2.1 MB), so every
     Phase-0 number in LAB_NOTEBOOK stays reproducible.
- **Alternatives rejected:** public from day one (other groups may work on the same subject before grading);
  rewriting history before release (loses the reviewable history SPEC §18.3 asks for); committing raw results
  (large, regenerable).
- **Defence:** "The first commit is the exact upstream release, every change to it is in PATCHES.md, and the
  environment is locked, so anyone can re-run our numbers."
- **Status:** accepted.

## D-009 — Defense version: 3 seeds everywhere; 5 seeds for Exp B after the defense
- **Date / phase:** 2026-11-07, before P1. Decided by the team (Youssef). **Serves:** R4, R8, R9.
- **Context:** the defense is on Mon 2026-11-09 at 09:00. The tiered plan (D-004) needs ≈ 165 worker-h, i.e.
  ≈ 13.8 h of wall time on our two laptops (6 workers each), and the runs can only start once the Phase-1
  instrumentation and LEAP are implemented and tested. The compute our two laptops can deliver before the
  defense does not cover it.
- **Decision:** apply D-004's second fallback: 3 seeds for every experiment (≈ 121 worker-h ≈ 10.1 h). Exp A's
  seeds are reused for Greedy and GRAd in Exp B. **After the defense**, run 2 more seeds for Exp B (the plan of
  D-004) and update the article's figures and statistics before the final release.
- **Alternatives rejected:** keeping 5 seeds for Exp B (does not fit before the defense); cutting configurations
  or protocols instead (the PDF requires the full testbed for every protocol, R2–R4).
- **Consequence:** 95 % CI half-width is 2.48·s instead of 1.24·s on the main claim. Paired differences (M22) keep
  real effects detectable; any non-significant difference is reported as such (SPEC §8.3).
- **Defence:** "With the compute available we used 3 paired seeds for every experiment, the same as the
  diagnostic; claims are only made where the paired 95 % CI excludes zero."
- **Status:** accepted for the defense version; revisit after 2026-11-09 (5-seed Exp B).

## D-010 — Scope and priority order for the defense
- **Date / phase:** 2026-11-07, before P1. Decided by the team (Youssef). **Serves:** bonus (+3/20), oral (15 %).
- **Decision:** order of work: (1) mandatory core R1–R9 (SPEC §1.2); (2) bonus B1, cross-layer MAC
  retransmission rate (named in the subject's description, PDF p. 15); (3) the τ̂-coloured animation for the
  oral (kept: it is the visual hook of the talk and Video 2 of the demo, SPEC §12.2); (4) bonus B2, fixed-sink
  data collection, only if (1)–(3) are finished. B3 (UavNetSim v2 city test) moves to after the defense.
- **Why this order:** the core is worth 55 % (30 % mastery + 25 % rigour); a bonus counts only when finished with
  its own measured result (PDF p. 3), so one finished bonus beats two half-done ones. B1 comes before B2 because
  the subject names it explicitly, and it reuses LEAP's `penalize()` hook (≈ 30 lines).
- **Defence:** "We finished the required core first, then the extension the subject suggests directly."
- **Status:** accepted.

## D-011 — How the recorder counts recomputations and attributes losses
- **Date / phase:** 2026-11-07, P1. **Serves:** R2, R3, O2 (the diagnostic's two headline metrics).
- **Decisions:**
  1. **Hooks in shared code only** (drone, MAC, PHY, metrics), none in the seven protocols. Every protocol is
     measured by the same code, and the patch stays small (PATCHES P6).
  2. **A route computation** is a `next_hop_selection` call at the shared call site in `Drone.feed_packet`,
     i.e. a decision that forwards or parks a packet. Protocols also poll their waiting list every 0.6 s
     (e.g. `dsdv.py:287`); those polls are not counted, otherwise the metric would measure the polling period.
  3. **A recomputation** is (a) a second or later decision for the same packet copy at the same node
     (`WAIT_RETRY`), (b) a route-discovery broadcast (`DISCOVERY`, GRAd), or (c) a different next hop on a
     transmission that follows an ACK timeout at that node (`RETRY_SWITCH`). Greedy's MAC retries go to the
     same next hop and are not recomputations (SPEC §5.2). Duplicate copies created by lost ACKs are not
     counted as recomputations.
  4. **A failed reception is a link break** if its SNR without interference is below the 6 dB threshold
     (distance > R_max = 249.3 m), else a collision; exact on this PHY (M15, M16). A decodable frame beaten by
     a stronger one (`NOT_SELECTED`) counts as a collision.
  5. **One final cause per lost packet**, from the last thing that happened to it (rules in the recorder's
     docstring). Copies created by lost ACKs: the cause is that of the latest terminal event. Packets still
     active at the end are `IN_FLIGHT` and excluded from loss shares; a packet in a waiting list at the end
     is `NO_ROUTE`.
  6. **GRAd** (broadcast, no ACK): attribution from receptions, with a protocol-specific `DISCARD` bucket for
     copies the gradient rule chose not to forward. Reported as an approximation.
  7. **Every Exp-A run saves its event log** (`*.events.jsonl.gz`), so attribution can be recomputed offline
     if a rule must change, without re-running the simulations.
- **Alternatives rejected:** wrapping each protocol (seven different code paths, larger patch); counting
  `collision_num` as losses (it counts any interference, even on decoded frames, M17); counting every
  waiting-list poll (depends on the polling period).
- **Validation:** unit tests T7 (`tests/test_recorder.py`: out-of-range → link break, in-range → collision,
  winner/not-selected, unacknowledged → queue overflow, lost ACK on a broken link → link break, waiting →
  no route, recomputation rules); T6 conservation (generated = delivered + lost + in flight) for all 7
  protocols; T4 golden test bit-identical. A bug found while validating: the shared retry counter (M21) made
  packets that loop back look like retries; `RETRY_SWITCH` now requires a preceding ACK timeout (Greedy:
  0 switches over 165 ACK timeouts, as expected).
- **Defence:** "A loss is a link break when the receiver could not have decoded the frame even without any
  interference, computed with the simulator's own path-loss formula, so the split is exact on this platform."
- **Status:** accepted.

## D-012 — LEAP-GR implementation details
- **Date / phase:** 2026-11-07, P2. **Serves:** R5, R6, R7, R9.
- **Decisions (beyond SPEC §6):**
  1. **One class for all variants.** `Leap(Greedy)` with parameters: A1 LEAP-select = `repair: off`;
     A2 LEAP = `repair: predictive`; control R (Greedy-reactive) = `tau_th_s: 0, repair: reactive`. R therefore
     uses LEAP's hello (same size, +128 bits), so A2 − R differs *only* by prediction.
  2. **Never switch away from the destination** when it is Greedy's pick and its predicted lifetime is > 0
     (logged `KEEP_DESTINATION`): a direct delivery takes one transmission, a detour takes at least two.
  3. **Neighbor validity is checked without purging** (`_is_valid`: last hello younger than Greedy's 2-s entry
     lifetime). `penalize()` must not mutate the table, otherwise Greedy's own waiting-list check, which runs
     without purging (`greedy.py:234`), would see a different table than in Greedy.
  4. **Hello velocity is copied** (M39) and the neighbor position is dead-reckoned from the hello's creation
     time, the moment its position was sampled (M9).
  5. **Shadow mode** (`tau_th_s: 0`, `warn_tau_s > 0`, no extra hello bits) behaves exactly as Greedy (T3) and only
     logs warnings, so prediction quality (SPEC §8.4) is measured on Greedy's real link breaks, not on breaks
     LEAP has already avoided. One open warning per link at a time, so bursts of packets on one link do not
     inflate the counts.
  6. **Recomputations for LEAP:** a proactive switch is part of the packet's first decision and is reported in
     `leap_events`, not as a recomputation; a predictive repair changes the next hop after an ACK timeout and
     is a recomputation (`RETRY_SWITCH`), as for any protocol (D-011).
- **Validation:** T1 (12 cases: static, separating, head-on, perpendicular, vertical, out of range, boundary,
  near-zero speed, equality with OPAR's predictor on 3 in-range cases, R_max); decision-rule unit tests
  (safe backup, no safe backup, expired neighbor, dead reckoning); T3: LEAP with prediction off and Greedy give
  bit-identical metrics; shadow mode identical to Greedy with warnings logged; T6 conservation for LEAP.
- **Defence:** "LEAP is Greedy's code plus one check; with the check switched off it reproduces Greedy exactly,
  and the reactive control uses the same hellos, so the ablation isolates the prediction."
- **Status:** accepted.

## D-013 — Experiments run from a working tree frozen at a commit
- **Date / phase:** 2026-11-07, P2. **Serves:** reproducibility (code criterion, rigour).
- **Context:** `sweep.py` starts a fresh process per run, which imports the code from disk at that moment. Twice
  tonight, code was edited in the tree an experiment was running from (recorder during Exp A, `leap.py` during
  Exp C). Both times no run had started since the edit (checked in the sweep logs), so no result mixes code
  versions, but later runs would have.
- **Decision:** every experiment runs from a dedicated git worktree at a fixed commit; development happens in
  another worktree. Exp A: `main` at `dd71430`; Exp C: `feat/leap` at `694c7ef`. Each result JSON records the
  commit and a `dirty` flag, and the aggregation keeps both columns, so a mixed-version experiment would be
  visible.
- **Defence:** "Each result file names the exact commit that produced it, and no experiment ran on uncommitted
  code."
- **Status:** accepted.

## D-014 — Bonus B1: cross-layer weighting by the recent MAC retransmission rate
- **Date / phase:** 2026-11-07, implemented ahead of P4 so its runs can start as soon as compute is free
  (evaluated only after the core results, D-010). **Serves:** X1 (PDF p. 15: "pondérer le choix du prochain saut
  par un indicateur issu de la couche MAC, taux de retransmission récent vers un voisin").
- **Decision:** per neighbor *j*, `f_j <- 0.8 f_j + 0.2 [ACK timeout]`, updated on every ACK timeout (via
  `penalize()`, failure) and every ACK received from *j* (success); `f_j = 0` for unknown neighbors. Candidates,
  Greedy's own pick included, are ranked by `progress_j (1 - f_j)`; LEAP's lifetime rule is then applied
  unchanged. Parameter `xl: true` on the LEAP class; the MAC is only read.
- **Why these choices:** β = 0.2 averages over roughly the last 5 attempts, short enough to follow mobility;
  weighting Greedy's pick too lets the bonus act when the lifetime check sees no risk (e.g. congestion, H3).
- **Known limit (for the article):** an ACK timeout can come from a broken link or from contention at the
  receiver; `f_j` cannot tell them apart (SPEC Q&A 15).
- **Validation:** unit test (a neighbor with f = 0.5 loses to a slightly worse reliable one); conservation test
  for `leap` with `xl: true`.
- **Status:** accepted; experiment D pending.

## D-015 — A third machine runs Exp B; the reactive control starts before tau_th is frozen
- **Date / phase:** 2026-11-07 23:40, P2/P3. Decided by the team (Youssef). **Serves:** R8, R9 (schedule).
- **Context:** both laptops run Exp A until about 06:00–07:00. A third PC is available.
- **Decision:** the third PC runs all of Exp B from a frozen commit of `feat/leap-next`: first the reactive control
  R (`exp_b_reactive.yaml`, 33 runs), which does not depend on tau_th; then LEAP-select and LEAP (66 runs) once
  Exp C has frozen tau_th. The laptops take the B1 runs after Exp A.
- **Consistency:** Exp B reuses Exp A's Greedy and GRAd runs (same configurations and seeds). Exp A ran at
  `dd71430`, Exp B at a later commit; the difference is additive (LEAP module, recorder fields for LEAP), and
  Greedy's behaviour is unchanged by construction (T3/T4: LEAP files are not imported by Greedy; the golden test
  holds). The commit of every run is in its result file.
- **Defence:** "All variants of a comparison use the same seeds and configurations; each result records the exact
  code version, and the shared code paths are covered by the regression tests."
- **Status:** accepted.

## D-016 — Pre-registered rule for freezing tau_th, applied automatically
- **Date / phase:** 2026-11-08 00:55, P2, written and committed while Exp C had finished only Greedy and
  tau_th = 0.25 s (no result yet for 0.5, 1, 2 or 4 s). **Serves:** R6 (configurable threshold), rigour.
- **Rule:** on Exp C (N = 30, 20 m/s, λ = 1, tuning seeds 100–102, never used for testing), compute each tau_th's
  mean PDR; among the thresholds within 0.5 percentage points of the best mean, choose the **smallest**. The
  smallest threshold is closest to Greedy (fewest proactive switches, least path deviation), so it wins ties.
  0.5 pp is below the seed-to-seed PDR spread seen so far (about 1.4 pp for both Greedy and LEAP at 0.25 s).
- **Automation:** `experiments/freeze_tau.py` applies the rule only if all 15 LEAP tuning runs exist, writes
  `experiments/configs/exp_b_leap.yaml` and `docs/tau_freeze.json` (per-threshold PDRs), and a watcher commits and
  pushes them; the third PC launches Exp B part 2 from that commit. This lets Exp B start overnight without
  anyone choosing the threshold by hand after seeing the data.
- **Defence:** "The threshold was chosen on separate tuning seeds by a rule committed before the sweep finished;
  the test seeds never influenced it."
- **Status:** accepted.

## D-017 — Exploratory Exp E: LEAP selection combined with reactive repair
- **Date / phase:** 2026-11-08 11:00, P3, after the Exp B paired results. **Serves:** R8/R9 (explain why),
  rigour.
- **Context:** in Exp B, LEAP beats the reactive control (no prediction, switch after every ACK timeout) by +0.9
  to +2.0 pp at 15–20 m/s and N = 40–50, and loses by 1.2–6.5 pp at 5 m/s and λ = 2–5
  (`figures/table_paired.csv`). LEAP's predictive repair never fires on top of its selection (LEAP − LEAP-select
  ≈ 0), so LEAP does not recover from ACK timeouts that prediction cannot see (collisions, congestion).
- **Decision:** run one more variant on the test configurations and seeds 1–3: `leap_reactive` = LEAP selection
  at the frozen tau_th = 0.25 s with `repair: reactive` (existing code path, no code change), 33 runs
  (`experiments/configs/exp_e_leap_reactive.yaml`). It is reported as **exploratory**: it was defined after
  looking at test-seed results, so it is not part of the pre-registered comparison and is not tuned.
- **Rejected:** retuning tau_th on the test seeds (would leak test data into the threshold); dropping the
  configurations where LEAP loses (selective reporting).
- **Defence:** "The main comparison was fixed in advance; this extra variant tests one explanation of a result
  we observed, and we label it as a post-hoc check."
- **Status:** accepted; laptop, from the frozen worktree `leap-dev`.

## D-018 — LEAP self-selection bug: fix and redo every LEAP-based run
- **Date / phase:** 2026-11-08 11:30, P3. **Serves:** correctness of R5–R9.
- **Finding:** LEAP left 15–27 packets per run undelivered and not dropped at N = 30, λ = 1 (Greedy: 0). Event logs
  (`exp_b_comparison/leap/n30_v5_r1_s1`) show `PROACTIVE_SWITCH` from node 9 to node 9: the packet is sent to the
  node itself and lost. Cause: a broadcast reaches the sender's own inbox (M40), so each node is in its own
  neighbor table with the position of its last hello; `Leap.best_alternative` did not skip the node's own id,
  and that stale entry can look like a safe neighbor with progress. Across Exp B: 586 self-decisions out of
  17 929 LEAP switches and repairs (34 444 packets generated); 129 of 5 097 repairs of the reactive control
  (same function). Greedy and GRAd do not use this code; Greedy's own choice is immune (M40).
- **Decision:** skip the node's own id in `best_alternative` (one line, regression test
  `test_never_picks_itself_from_its_own_hello`), then redo, from the fixed commit, every run that executes LEAP
  code: Exp C's 15 LEAP tuning runs (Greedy and the shadow runs make no switch and are kept), re-freeze tau_th
  with the **unchanged** rule D-016, then Exp B (reactive control, LEAP-select, LEAP), Exp D and Exp E. Old
  results are kept aside as superseded, not deleted, and never reported.
- **Rejected:** correcting the old results by removing the lost packets (not what the protocol does); keeping
  tau_th = 0.25 s without re-tuning (it was chosen with the buggy code).
- **Defence:** "We found the bug ourselves from the event logs (packets in flight at the end), traced it to a
  simulator behaviour we then documented, fixed it with a regression test and re-ran everything it touched."
- **Status:** accepted.

## D-019 — `tau_th_s` defaults to the frozen value
- **Date / phase:** 2026-11-09, release. **Serves:** R6 (configurable threshold), reproducibility.
- **Context:** `routing/leap/leap.py` kept `tau_th_s = 1.0` as its default, a placeholder from before tuning.
  Every config and the demo pass 0.25 explicitly, but a reader who runs `--protocol leap` without parameters
  would get a different protocol from the one in the article.
- **Decision:** default `tau_th_s = 0.25`, the value frozen by D-016 (`docs/tau_freeze.json`).
- **Rejected:** keeping 1.0 and documenting it (a trap for anyone reusing the module).
- **Evidence:** no committed config relies on the default (`grep tau_th_s experiments/configs/*.yaml`: every
  LEAP variant sets it), so no result changes.
- **Defence:** "The default is the value we froze and report; every experiment also sets it explicitly."
- **Status:** accepted.

## D-020 — Release v1.0.0 contents
- **Date / phase:** 2026-11-09, release. **Serves:** SPEC §18.1 (portfolio-grade repository), D-008.
- **Decision:** tag `results-v1` at `165c2d1` (last commit that changed results; later commits to `figures/`
  only re-wrote PDF timestamps) and `v1.0.0` at the defended version. The GitHub release attaches the article
  PDF, the raw results (`results-raw.zip`, every run JSON and event log, including the superseded runs of
  D-018) and the side-by-side demo video. Our code is MIT-licensed under both authors' names; the upstream
  notice is kept in `LICENSE-UPSTREAM`.
- **Deviation from SPEC §18.1:** the slides stay in HTML (`slides/`, run with `make slides`) instead of a PDF in
  the release; the team chose not to maintain an export.
- **Defence:** "Every number in the article can be rebuilt from the release's raw results with the commands in
  `docs/reproducing.md`, and the tables come out identical."
- **Status:** accepted.
