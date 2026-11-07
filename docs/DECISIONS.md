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
- **Status:** accepted. Revisit after the first Exp-A night if its wall time is > 20 % above the estimate.

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
     notes and local tool configuration.
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
