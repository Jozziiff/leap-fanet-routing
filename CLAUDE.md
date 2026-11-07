# CLAUDE.md — Projet 06 FANET predictive routing (RT5 INSAT, Futurs Réseaux Mobiles)

Team: **Youssef Hamdani** & **Rayen Hamza**. Supervisor: Dr Mériem Afif. Year 2026/2027.
Subject: *Routage prédictif basé sur la qualité de lien dans un essaim d'UAV* (Projet 06).

## Sources of truth (in priority order)
1. The subject PDF `Projets_TP_Futurs_Reseaux_Mobiles.pdf` (kept outside the repo, one folder up on Youssef's machine; ask the team for a copy): the subject (pp. 15–16), grading grid (p. 3), mandatory article plan (p. 4). **Never contradict it.** Its requirements are mirrored in SPEC §1.
2. `docs/SPEC.md`: the plan (requirements R1–R9, design of LEAP-GR, experiments, article, timeline).
3. `docs/UPSTREAM_FACTS.md`: verified facts about UavNetSim-v1 **v1.0.1** with file:line refs (M1–M38).
4. The upstream source code itself. If code and docs disagree, the code wins: fix the doc.

## Grounding rules (mandatory)
- Tag claims in docs as **[PDF] / [CODE] / [DECISION] / [EST] / [VERIFY]** (see SPEC header).
- Before stating a fact about the simulator, **read the code** and cite `file:line`. Don't assume the README is accurate.
- **Never invent numbers or results.** Any number in the article/slides must come from a result file in `results/` produced by a committed config. Estimates stay labelled [EST].
- **Never cite a reference that hasn't been verified** (publisher page / DBLP / IEEE Xplore). Update the status table in SPEC §11.1.
- If something is ambiguous in the PDF, list it in SPEC §16 (open questions) rather than guessing.

## Documentation discipline (team rule, 2026-11-07)
- **Every decision** (implementation, method, scope, fallback) gets an entry in `docs/DECISIONS.md`: context, decision, rejected alternatives, why, evidence with numbers, a one-line **defence** for Q&A, status. Write it when the decision is made, not later.
- **Every experiment or measurement** gets a dated entry in `docs/LAB_NOTEBOOK.md`: setup, exact numbers, source file in `results/`, and where it goes in the article/oral. Pilot numbers are labelled as such and never reported as results.
- Surprising facts still go to `UPSTREAM_FACTS.md` (file:line) + SPEC changelog.

## Hard constraints
- Repo: `git@github.com:Jozziiff/leap-fanet-routing.git` (private until the defense, DECISIONS D-008). Commit and push only as part of tasks the user asked for.
- **Commits: NEVER add a `Co-Authored-By` trailer**, and no assistant mention in commit messages, PR texts, README, docs or the article (team rule, 2026-11-07). Each teammate commits under their own git identity.
- This file is tracked (team decision, 2026-11-07) so both teammates share the same rules. Personal scratch notes (`notes/`) and local tool settings (`.claude/`) stay untracked.
- Two machines work on the repo: `git pull` before starting, small commits, push often; raw results (`results/raw/`) are never committed (zip and share them).
- Platform pinned to UavNetSim-v1 tag **`v1.0.1`** (commit `a5622c5`). Do not use `master` (v2, Sionna RT).
- **Python 3.12 via `uv`** (system Python 3.14 is incompatible with the pinned numpy/matplotlib).
- Our protocol lives in **`routing/leap/`** and implements `next_hop_selection(packet) -> (has_route, packet, enquire)`, generator `packet_reception(packet, src_drone_id)`, and `penalize(packet)` (called by the MAC on ACK timeout).
- **MAC identical in all comparisons** (CSMA/CA, same params). Never change MAC code to help LEAP; routing-layer hooks only.
- Upstream modifications must be minimal, behaviour-neutral by default, and listed in `PATCHES.md`. The regression test (hooks on == pristine upstream) must pass.
- **One simulation per fresh Python process** (`config` is mutable module state; `GL_ID_*` counters are never reset; `MAX_TTL` is computed at import).
- Never change the simulator polling intervals (5 µs inbox / 10 µs queue) to speed things up: it changes behaviour.
- Headless runs: logging at WARNING, all `plt.show()` disabled.

## Confirmed team decisions (2026-11-07, SPEC v0.2)
- Keep it **simple**: LEAP = `Leap(Greedy)` subclass; "Greedy unless its pick is predicted to break within τ_th"; repair via `penalize()`. No monitor process, no probe packets, no weighted scores.
- Traffic as in the PDF/platform (every drone is a Poisson source at λ per drone); the density/load coupling is discussed in the article.
- **Energy depletion disabled** (`INITIAL_ENERGY = 1e9`), otherwise drones sleep after ~14–19 s (M26).
- Seeds for the defense version: **3 everywhere** (test seeds 1–3, τ_th tuning on separate seeds 100–102), DECISIONS D-009; Exp B gets 5 seeds after the defense. Stats = 95 % CI + **paired t-test** (Wilcoxon can't reach p < 0.05 with ≤ 5 seeds).
- Article in **English**, no imposed template → **IEEEtran conference**. Oral = **10 min talk + 10 min Q&A**, demo = **pre-recorded MP4s embedded in the slides** (record after results are frozen, git hash on screen).
- Small documented upstream patches: accepted. GRAd keeps its broadcast-without-ACK mode: accepted. Change the SPEC only with a changelog entry (§17).
- Priority order for the defense (D-010): core R1–R9 → bonus B1 (cross-layer MAC retransmission rate) → τ̂-coloured animation for the oral (must) → B2 fixed-sink data collection (if time). **B3 (UavNetSim v2 city test) after the defense, in a separate venv/folder; it must never touch the core.**
- Diagnostic covers DSDV, Greedy, GRAd, OPAR, Q-Routing + QGeo, Q-FANET.
- References: only the verified entries in SPEC §11.1 (all 7 PDF refs must be cited). Article written in LaTeX/IEEEtran, figure-driven, humanizer pass per section (SPEC §11.0–11.0b).

## Current status (update when a phase changes)
- Defense: **Mon 2026-11-09, 09:00** (10 min talk + 10 min Q&A).
- Phase 0 and Phase 1 done (instrumentation validated, golden test T4 bit-identical). Exp A running since 2026-11-07 22:44: shard 0/2 on Youssef's laptop, shard 1/2 on Rayen's. Next: Phase 2 (LEAP-GR in `routing/leap/`, tests T1–T3, τ_th tuning).
- Where things are: decisions `docs/DECISIONS.md`, measurements `docs/LAB_NOTEBOOK.md`, simulator facts `docs/UPSTREAM_FACTS.md`, upstream changes `PATCHES.md`.

## Professional-repo standard (team goal: CV/LinkedIn-grade repo) — SPEC §18
- Our code: type hints, NumPy docstrings with units, `ruff` clean, no dead/commented-out code, no stray prints/TODOs. **Never reformat upstream files.**
- Conventional Commits, one logical change per commit, body says *why*. `main` always green; CI = lint + tests + smoke sim.
- No slop: every sentence in docs/comments/commits must be true, specific, checkable. No filler, no marketing adjectives, no emoji walls. Human-facing prose gets a `humanizer` pass.
- Never commit venvs, caches, raw logs, large binaries, secrets, or internal planning files.

## Drift-control protocol (mandatory) — SPEC §19
1. **Start of every session/task:** re-read SPEC §0, §1 and the current phase in §13. Name the requirement (R#/O#/X#) the task serves; if none, it's out of scope, so ask first.
2. **Before every commit:** tests + ruff pass, `PATCHES.md` updated if upstream changed, no unverified claims.
3. **At each gate G0–G3:** walk the SPEC §1 matrix row by row (done/partial/missing) against the PDF, and report it to the user.
4. **Before writing article/README text:** re-read SPEC §11.0 + PDF p. 4.
5. **Surprising fact:** verify in code → UPSTREAM_FACTS (file:line) → SPEC changelog. Never silently diverge from the spec.

## Conventions
- Configs in YAML under `experiments/configs/`; one result JSON per run with config, seed, our git hash, upstream commit, wall time.
- Same seed ⇒ same traffic and trajectories across protocols (but not the same MAC backoffs or sub-channel draws, M22) ⇒ use **paired** statistics.
- Tests with `pytest` (T1–T8 in SPEC §10.2). Run them before claiming anything works.
- Code, comments and article in English.
- Units: the simulator uses **microseconds** for time and metres for distance; convert explicitly and name variables with units (`t_us`, `tau_s`).

## Grading reminders (p. 3)
Core 30 % · Comparative rigour 25 % · Code 10 % (README!) · Article 20 % · Oral 15 % · Bonus up to +3/20.
The article must **explain why**, not just describe. Don't start the bonus before results gate G3.
