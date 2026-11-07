# SPEC — Projet 06 : Routage prédictif basé sur la qualité de lien dans un essaim d'UAV

**Course:** Futurs Réseaux Mobiles — RT5, INSAT (Université de Carthage), 2026/2027 · **Supervisor:** Dr Mériem Afif
**Team:** Youssef Hamdani · Rayen Hamza
**Spec version:** **v1.5** (2026-11-07). Defense Mon 2026-11-09 09:00. Phase 0 done, G0 passed, seed plan decided (§8.2). Decisions: [`DECISIONS.md`](DECISIONS.md); run records: [`LAB_NOTEBOOK.md`](LAB_NOTEBOOK.md). No GitHub repo until the team decides. Changelog in §17.

> **Tags.** **[PDF]** required by the subject (`Projets_TP_Futurs_Reseaux_Mobiles.pdf`, pp. 1, 3–4, 15–16), non-negotiable · **[CODE]** verified in UavNetSim-v1 `v1.0.1` (see [`UPSTREAM_FACTS.md`](UPSTREAM_FACTS.md), facts M1–M26) · **[DECISION]** our choice, justify it in the article · **[EST]** estimate, validate by a run · **[VERIFY]** check before citing.

> **Guiding principle (team decision):** *simple, correct, well-measured, well-explained.* The core (30 %) + rigour (25 %) are worth 55 % of the grade. Do them fully, then add a small, clean bonus.

---

## 0. TL;DR

1. **Platform:** UavNetSim-v1 **tag `v1.0.1`** (pure Python/SimPy), confirmed by the team. Python 3.12 via `uv`.
2. **Diagnostic [PDF]:** instrument the simulator. For **DSDV, Greedy, GRAd, OPAR, Q-Routing** (+ QGeo, Q-FANET, also cited by the PDF), measure **route recomputations per delivered packet** and the **share of losses due to link breaks vs MAC collisions** on the testbed **N = 10…50 (step 10) × mean speed 5…20 m/s × Poisson UDP rate**.
3. **Protocol [PDF]:** **LEAP-GR** (*Link-Expiration-Aware Predictive Greedy Routing*), new package `routing/leap/`. It **behaves exactly like Greedy unless Greedy's chosen neighbor is predicted to break within τ_th**, then it **switches early to a safe backup neighbor**. Link lifetime τ̂ = closed-form 3D Link Expiration Time from **distance, relative velocity and radio range**. Extra: when an ACK times out on a link predicted to be breaking, the remaining MAC retries go to the backup (routing-layer hook `penalize()`, MAC untouched).
4. **Fair comparison [PDF]:** vs **Greedy** and **GRAd**, **identical MAC**. A 4-variant ablation isolates the gain due to prediction alone.
5. **Bonus (+ up to 3/20) [PDF]:** B1 **cross-layer MAC retransmission-rate weighting** (explicitly suggested in the PDF, [EST] ~30 lines of code). B2 (if time) **UAV-assisted data collection with a fixed sink**. Plus an animated visualization for the oral. **B3 (last, only once everything else is finished):** port LEAP to UavNetSim **v2** and test it in a 3D city scene.
6. **Deliverables [PDF]:** functional code demo + README · **10 min talk + 10 min Q&A** · **English** IEEE-style article with the mandatory 7-section plan.

---

## 1. PDF compliance matrix (every requirement → where it's covered)

### 1.1 Objectives (p. 15) [PDF]
| ID | Objective (PDF) | Covered by |
|---|---|---|
| O1 | Take over a FANET simulation platform and evaluate the existing routing protocols on a standardized testbed | §4, §5, §8 (Exp. A) |
| O2 | Quantify the share of packet losses attributable to link breaks | §5.3 |
| O3 | Design a geographic routing protocol with link-break prediction and compare it to existing protocols | §6, §7, §8 (Exp. B) |

### 1.2 Mandatory core (p. 15) [PDF]
| ID | Requirement | Covered by | Evidence in article |
|---|---|---|---|
| R1 | Use **UavNetSim-v1** (Python/SimPy, network/MAC/PHY + 3D mobility; DSDV, Greedy, GRAd, OPAR, Q-Routing; PDR, delay, NRL, hops) | §4 | §5 "Environment" + Table I |
| R2 | Per existing protocol: **mean number of route recomputations per delivered packet** | §5.2 | Fig. 3 |
| R3 | Per existing protocol: **proportion of losses due to link break rather than MAC collision** | §5.3 | Fig. 2 |
| R4 | Testbed varying **N = 10→50 step 10**, **mean speed 5→20 m/s**, **Poisson UDP rate** | §8.1 | Table I, Figs 2–5 |
| R5 | **Lifetime per neighbor pair** from **current distance, relative velocity, radio range** | §6.2 | Eq. (LET), Fig. 1b |
| R6 | **Anticipated backup-route search** when the estimated lifetime **< configurable threshold** | §6.3–6.4 | Algorithm 1, Fig. 7 (τ_th) |
| R7 | **New module in `routing/`** respecting **`next_hop_selection` / `packet_reception`** | §6.5, §10 | §5 "Implementation" |
| R8 | **Compared to Greedy and GRAd** on the standardized testbed | §8 Exp. B | Figs 4–5 |
| R9 | **Isolate the gain due to prediction alone** with an **identical MAC** in all comparisons | §7 | Fig. 6 (ablation) |

### 1.3 Extension / bonus (pp. 3, 15–16) [PDF]
| ID | Suggested by the PDF | Our plan |
|---|---|---|
| X1 | Cross-layer: weight the next hop by the **recent MAC retransmission rate towards a neighbor** | **B1, yes** (§9.1) |
| X2 | Application scenario: **UAV-assisted data collection with fixed sink(s)** *or* air-ground network with ground relays | **B2, if time** (§9.2) |
| X3 | Combine with the **virtual-force topology control** (connectivity, route stability) | ❌ out of scope (state it in Future Work) |
| X4 | "proposer des idées innovantes" | prediction-quality study (§8.4) + animated visualization (§9.3) + **B3 urban check on UavNetSim v2 (§9.4, last, optional)** |
Bonus rules (p. 3): **evaluated separately**, added directly to the final grade, **up to +3/20**, total capped at 20/20. → A bonus counts only if it is **finished and has its own measured result**.

### 1.4 Deliverables & article rules (pp. 1, 3–4) [PDF]
| Rule | Our plan |
|---|---|
| 3 deliverables: **functional code demo**, **oral presentation**, **scientific article** | §12 (demo + talk), §11 (article) |
| **README** for reproducibility (hint for the 10 % code criterion) | §10.3 |
| Article: explain **why** the system behaves this way, not only describe it | rule for every figure (§11) |
| Title precise (not "Projet Futurs Réseaux Mobiles") | §11 |
| **Abstract: one paragraph, 150–250 words**: context, challenge, approach, **quantitative results** | §11 |
| **4–6 keywords** | §11 |
| Sections: Introduction (context, problem, positioning, **announce structure**), Related Work (critical synthesis, PDF refs + own), System Model (**block diagrams/flowcharts**, **formalisation**), Implementation & Evaluation (environment, **parameter table**, **commented figures** comparing core vs extensions or vs reference), Conclusion & Perspectives (limits + future work), References (**numbered, strict IEEE**) | §11 |

---

## 2. Grading grid → strategy (p. 3) [PDF]

| Criterion | Weight | What the PDF says it rewards | Our evidence |
|---|---|---|---|
| Understanding / mastery of the core | **30 %** | correctness, **completeness of imposed code**, clarity of technical choices | R1–R9 done; LET unit-tested; interface-compliant module; design-decision table (§6.6) |
| Comparative analysis & rigour | **25 %** | choice of comparisons, **relevance of metrics**, **finesse of analysis** | exact loss taxonomy; paired seeds; 95 % CI + paired t-test; ablation isolating prediction; threshold tuned on separate seeds; warning precision/lead time |
| Code quality | **10 %** | structure, **respect of imposed interfaces/tools**, **easy re-run** | pristine-upstream first commit + `PATCHES.md`; YAML configs; `make` targets; README; tests |
| Article | **20 %** | structure, **critical thinking**, **links to literature** | mandatory plan; related-work table; threats-to-validity paragraph; verified IEEE refs |
| Oral | **15 %** | dynamism, clarity, **mastery in Q&A** | 10-min story + demo clip; **10-min Q&A** prepared with a question bank (§12.3); both master everything |
| Extension | **+3/20 max** | going further, optional leads, innovative ideas | B1 (must) → B2 (if time) → B3 v2 urban check (last, optional), each with its own figure |

---

## 3. Problem framing (Introduction material)

- FANETs: fast, poorly predictable 3D mobility, no infrastructure, frequent link breaks. Most protocols react **after** a break (failed transmission, timer expiry), which causes a loss spike plus reconvergence delay [PDF].
- On this platform [CODE]: Greedy keeps a neighbor **up to 2 s** after its last hello (M10) and picks the neighbor **closest to the destination**, which is often the one at the **edge of range** (M11). On failure, the MAC **retries that same neighbor 5 times** before dropping (M12).
- **Hypotheses (to test, not assume):** **H1** at moderate load, link breaks are a major share of Greedy's losses, growing with speed. **H2** LEAP reduces link-break losses at a small overhead cost. **H3** the gain shrinks when the MAC saturates (collisions dominate) and when no safe alternative neighbor exists (sparse). **H4** too large a τ_th causes needless switches and longer paths.

---

## 4. Platform & environment

### 4.1 Version [CODE][DECISION — confirmed by team]
UavNetSim-v1, **tag `v1.0.1` = commit `a5622c5`** (2026-06-02, MIT). Not `master` (v2 since 2026-08-20, Sionna RT). Cite the arXiv paper + repo with tag and access date.

### 4.2 Toolchain
Python **3.12** via `uv` (system 3.14 is incompatible with the pinned numpy 2.2.4 / matplotlib 3.10.1). Pinned upstream deps + `pyyaml`, `pandas`, `scipy`, `pytest`. 8 cores / 14 GB → 7 parallel workers, **one fresh process per run** (M4). LaTeX available (IEEEtran).

### 4.3 Minimal upstream patches (each listed in `PATCHES.md`, behaviour-neutral by default)
| Patch | Why |
|---|---|
| P1 Config injection **before** importing the simulator: N, `MAX_TTL`, `SIM_TIME`, speed, λ, routing name, seed, logging=WARNING, headless | M1–M5 |
| P2 Routing **registry** (name → class) instead of hard-coded `Dsdv` | R7 |
| P3 Mean speed from config (replace hard-coded `10`) | R4, M1 |
| P4 Poisson rate from config (replace `rate = 5`) + traffic window `[2 s, T − 3 s]` | R4, M2 |
| P5 Disable blocking `plt.show()` | M6 |
| P6 **Instrumentation hooks** (observe only, never consume random numbers) | R2, R3 |
| **P7 Disable energy depletion** (`INITIAL_ENERGY = 1e9 J`). Otherwise drones go to sleep after **≈14–19 s**, earlier for slower drones, which would distort the speed sweep (M26). Stated in Table I as "energy model disabled (out of scope)" | validity |
**Golden test (T4):** hooks on, our features off, with upstream values (speed 10, λ = 5, default energy, no traffic window) → Greedy metrics **bit-identical** to pristine v1.0.1.

---

## 5. Step 1 — Diagnostic (O1, O2, R2, R3)

### 5.1 Recorder
`instrumentation/recorder.py` logs per-packet lifecycle events: generated, tx attempt (sender, next hop, attempt #), reception outcome (`OK / FAIL_RANGE / FAIL_COLLISION / NOT_SELECTED`, with distance, SNR without interference, SINR), ACK outcome, route computation (`kind`), drop (`cause`), delivered (true hops). Output: per-run JSON summary (+ optional event file for debugging).

### 5.2 R2 — Route recomputations per delivered packet
- **Route computation** = one routing decision for a data packet at a node (`next_hop_selection` call).
- **Recomputation** = a computation for packet *p* at node *i* that is **not the first** one for (*p*, *i*) (waiting-list retry, switch, repair), **plus explicit route discoveries** (GRAd `M_REQUEST`) **and next-hop changes between MAC retries** (`RETRY_SWITCH`, used by LEAP's repair). OPAR relays never re-plan (M36), so OPAR's recomputations are source-side waiting-list retries. Exact definitions: `instrumentation/recorder.py` docstring, DECISIONS D-011. DSDV table updates are reported separately as overhead.
- `RR = #recomputations / #delivered` (+ breakdown by kind). Note for the article [CODE M12]: Greedy's MAC retries are *not* recomputations, since they go to the same next hop. That is the weakness LEAP targets.

### 5.3 R3 — Loss attribution (exact on this platform)
**Per failed reception** of a unicast *s → r* (`SINR < 6 dB`), recompute `SNR_noint = P_t·PL(d)/N₀`:
- `SNR_noint < 6 dB` ⇔ `d > R_max ≈ 249.3 m` → **FAIL_RANGE (link break)**. The PHY is deterministic free-space with fixed noise (M15–M16), so this is exact, not an approximation.
- else → **FAIL_COLLISION** (interference); `NOT_SELECTED` (a stronger frame won) is merged into collision.

**Per lost packet (mutually exclusive final cause):** `LINK_BREAK` (dropped after 5 attempts, last failure FAIL_RANGE) · `COLLISION` (last failure collision, incl. lost ACK) · `NO_ROUTE` (expired in `waiting_list`) · `QUEUE_OVERFLOW` · `TTL` · `EXPIRED` · `OTHER` (safety net, expected ≈ 0; showing it's 0 is itself convincing) · `IN_FLIGHT` at the end (excluded from shares, count reported).
- **Conservation test (T6):** generated = delivered + Σ losses + in-flight.
- Headline: `LBR = LINK_BREAK / all losses` and `LINK_BREAK / (LINK_BREAK + COLLISION)` (literally the PDF's "plutôt qu'à une collision MAC"). Also report as a fraction of generated packets.
- Track **attempt-level** failures separately from **final** losses (a packet can collide, be retried, then be delivered).
- **GRAd** (broadcast, no ACK, M13): per-reception classification only, and a lost packet is attributed by its failed receptions. State it as an approximation.
- Upstream `collision_num` counts any interferer even when decoded (M17), so it is **not a loss counter**. Say so in the article.

### 5.4 Other metrics
PDR (de-duplicated), mean + p95 E2E delay, NRL (packets) + control bits, throughput (upstream definition), **true hop count** (recorder) vs upstream TTL-based value (inflated by retries, M20), wall time.

### 5.5 Protocols
DSDV, Greedy, GRAd, OPAR, Q-Routing (named in the PDF) **+ QGeo and Q-FANET**. Both are in v1.0.1 and both are **cited in the PDF's reference list**, and the PDF says "pour chaque protocole existant", so including them is the safe reading. Cost: +66 runs at 3 seeds. QMR (also present) is optional. Caveat: OPAR here is centralised and uses oracle positions/velocities (M14), so it's a "predictive reference with global knowledge", not a distributed competitor.

---

## 6. Step 2 — LEAP-GR (R5, R6, R7)

### 6.1 Implementation strategy: subclass Greedy [DECISION]
`class Leap(Greedy)` reuses Greedy's hello timing, ACK handling, VF handling and waiting-list logic **unchanged**, and overrides only: hello packet (adds velocity + timestamp), neighbor table (stores them), `next_hop_selection`, `penalize`. **Pro:** minimal code, and fairness by construction (everything except the prediction is literally Greedy's code).

### 6.2 Link lifetime (R5)
Hello carries `p_j, v_j, t_j` (+128 bit; the extra size is configurable so test T3 can set it to 0). At time *t*: `p̂_j = p_j + v_j (t − t_j)`, `Δp = p̂_j − p_i`, `Δv = v_j − v_i`.
Solve `‖Δp + Δv τ‖ = R` with `a = ‖Δv‖²`, `b = Δp·Δv`, `c = ‖Δp‖² − R²`:
```
if c > 0:        τ̂ = 0          # predicted already out of range
elif a < ε:      τ̂ = +∞         # no relative motion (capped)
else:            τ̂ = (−b + √(b² − a·c)) / a      # c ≤ 0 ⇒ b² − ac ≥ 0, τ̂ ≥ 0
```
- 3D form of the classic Link Expiration Time of Su, Lee & Gerla [ref 11, verified]. Uses exactly "distance courante, vitesse relative, portée radio" [PDF].
- `R = κ·R_max`, `R_max = 249.3 m` derived from the platform's PHY constants, **κ = 0.9 fixed** (margin for interference). Justify it in the article, no sweep.
- Our formula handles `c > 0` and `a ≈ 0`, unlike `opar.link_lifetime_predictor` (M14). On in-range cases it must equal OPAR's (test T1).
- **Progress uses the hello positions exactly like Greedy**. Dead reckoning is used **only inside τ̂**, so that LEAP with prediction off ≡ Greedy (test T3).

### 6.3 Next-hop selection = anticipated backup search (R6)
```
g ← Greedy's choice (max progress toward destination, same tie-breaking)
if g is None: return no route                       # → waiting_list, as Greedy
if τ̂(i,g) ≥ τ_th: return g                          # normal case: identical to Greedy
B ← { j ≠ g : progress_j > 0 and τ̂(i,j) ≥ τ_th }    # proactive backup search
if B ≠ ∅: return argmax_{j∈B} progress_j            # PROACTIVE_SWITCH (logged)
else:     return g                                   # RISKY_FORWARD (logged), never worse than Greedy
```
**Wording rule (article and oral):** the backup is a **local one-hop alternative next hop**, re-evaluated for **every packet at every hop**. Since geographic routing decides per packet, this check *is* the anticipated backup-route search. It is **not** an end-to-end backup path. Say it explicitly.

### 6.4 Predictive repair via `penalize()` (variant A2)
The MAC calls `penalize(pkd)` on every ACK timeout, then retries `pkd.next_hop_id` (M12). LEAP: if `τ̂(i, next_hop) < τ_th`, set `pkd.next_hop_id ←` best backup from *B* before the retry → `PREDICTIVE_REPAIR` (logged). Same number of MAC retries, same MAC code: **MAC identical** [PDF R9].

### 6.5 Interface compliance (R7) [CODE]
`__init__(simulator, my_drone)` · `next_hop_selection(packet) -> (has_route, packet, enquire=False)` · `packet_reception(packet, src_drone_id)` (generator, inherited) · `penalize(packet)` (**required by the MAC**, not mentioned in the README) · registered as `"LEAP"`.

### 6.6 Parameters & design decisions
| Parameter | Value | How chosen |
|---|---|---|
| `tau_th` | to be frozen ∈ {0.25, 0.5, 1, 2, 4} s | **tuned on separate tuning seeds** (§8.3), then frozen |
| `kappa` | 0.9 | fixed, justified (interference margin) |
| `repair` | on (A2) / off (A1) | ablation |
| hello period / neighbor lifetime | 0.5 s / 2 s | **= Greedy** (fairness: gain must not come from more hellos) |

| Decision | Alternative rejected | Why |
|---|---|---|
| Greedy core + LET switch | weighted score, ML/Kalman | simplest explainable design, one parameter |
| Velocity in hello | velocity estimated from 2 hellos | simpler; GNSS + IMU on board is a fair assumption |
| Repair via `penalize()` | change MAC retries | keeps the MAC identical |
| Destination location known (as Greedy) | location service | same assumption as the baseline; stated as a limitation |
| No full route discovery | RREQ/RREP flooding | complexity; one-hop backup matches geographic routing |

---

## 7. Isolating the gain due to prediction (R9)

Same CSMA/CA protocol and parameters, same PHY, same hello period, same seeds (paired traffic + trajectories, M22) for all.

| ID | Variant | Difference from previous | What it proves |
|---|---|---|---|
| A0 | **Greedy** | — | baseline |
| A1 | **LEAP-select** | lifetime-aware next-hop choice (§6.3) | gain of **prediction in the routing decision** |
| A2 | **LEAP (full, socle)** | + predictive repair (§6.4) | gain of **anticipating breaks on in-flight packets** |
| R | **Greedy-reactive** (control) | Greedy + switch to the next-best neighbor **after** an ACK timeout, no prediction | "Is predicting better than just reacting?" (answers the PDF context paragraph directly) |
| — | **GRAd** | — | 2nd mandatory baseline |

- **Gain due to prediction alone** = paired `A1 − A0` and `A2 − R` (same reaction mechanism, with vs without prediction). 95 % CI.
- **Sanity test T3:** LEAP with `tau_th = 0`, repair off, extra hello bits = 0 → **identical** to Greedy.
- **MAC fairness note** (article): GRAd's platform implementation uses broadcast without ACK (M13). We keep the same MAC protocol and parameters, and the access mode belongs to each routing protocol's design. Interpretation **accepted** (§16).

---

## 8. Experimental methodology

### 8.1 Testbed (R4)
Fixed (upstream defaults, Table I): 600 × 600 × 100 m, Gauss-Markov 3D, 802.11b 2 Mbps, CSMA/CA, 1024 B payload, 5 MAC retries, queue 200, lifetime 10 s, energy disabled (P7), `T = 30 s` (2 s warm-up, 3 s drain).
**One-factor-at-a-time sweeps around the reference (N = 30, v = 10 m/s, λ = 1 pkt/s/drone):**
| Sweep | Values |
|---|---|
| S1 drones | N ∈ {10, 20, 30, 40, 50} [PDF] |
| S2 mean speed | v ∈ {5, 10, 15, 20} m/s [PDF range] |
| S3 Poisson rate | λ ∈ {0.5, 1, 2, 5} pkt/s **per drone** (5 = upstream default) |
→ **11 distinct configurations.**
- **Traffic definition (team decision, follows the PDF):** every drone is a Poisson source at rate λ to a random destination, as on the platform. **Article note:** in S1 the total offered load grows with N (N·λ), so the density effect is coupled with load. We state it and interpret S1 with S3 in mind.
- [EST] λ = 5 probably saturates the channel for N ≥ 30 (≈208 frames/s capacity). λ = 1 is the non-saturated reference. **Check in the pilot.**

### 8.2 Seeds — tiered (**decided at G0, 2026-11-07: [DECISIONS.md D-004](DECISIONS.md)**)
| Experiment | Protocols | Seeds | Why |
|---|---|---|---|
| A. Diagnostic | DSDV, Greedy, GRAd, OPAR, Q-Routing, QGeo, Q-FANET | **3** | descriptive (loss shares, RR); differences between protocols are large |
| B. Core comparison | Greedy, GRAd, LEAP-select, LEAP, Greedy-reactive | **5** | our main claim; 5 seeds halve the CI width vs 3 (1.24σ vs 2.48σ) |
| C. τ_th tuning | LEAP | **3 separate tuning seeds** (100–102) | avoids tuning on the test seeds |
| D. Bonus | LEAP vs LEAP+XL (and sink scenario) | **3** | separate evaluation |
- **Run count:** A 7×11×3 = 231 · B 3 new variants×11×5 = 165 + 2 extra seeds for Greedy/GRAd 2×11×2 = 44 · C 5×1×3 = 15 · D ≈ 20–40 → **≈ 475–495 runs** (all-3-seeds alternative ≈ 355).
- **Decision rule after the benchmark:** `wall time ≈ runs × t_run / 7 workers`, split over **2 laptops**. If the tiered plan fits in **one night (~10 h)**, keep it. Otherwise use 3 seeds for B too and say so in the article.
- **G0 measurement (2026-11-07, see §17 v1.2):** Greedy 30 s runs take ≈ 35·N − 97 s wall at λ = 1 with ~6 concurrent runs; GRAd ≈ 3.5× (M28). Tiered plan ≈ 165 worker-h ≈ 13.8 h on 2 laptops × 6 workers (A ≈ 6.9 h, B ≈ 5.8 h, in different phases); all-3-seeds ≈ 121 worker-h ≈ 10.1 h. **Defense version (team, 2026-11-07, D-009): 3 seeds for every experiment**; the 5-seed Exp B below is run after the defense. Earlier decision: **keep the tiered plan**, with the one-night rule applied per experiment (A and B run in different phases). Fallbacks if a night overruns: GRAd at 3 seeds in B, then all-3-seeds. Exp A's 3 seeds = the first 3 of Exp B's 5, so Greedy/GRAd runs are reused. Full rationale: D-004.
- Because traffic + trajectories are paired across protocols (M22), **paired** differences have much lower variance than raw means, so 3–5 seeds are enough to detect real effects.

### 8.3 Statistics
- Mean ± **95 % CI (Student t)** per point; **paired t-test** on the per-seed differences vs Greedy for the headline claims. ⚠ **Wilcoxon is not usable** with ≤ 5 seeds: its minimum two-sided p is 0.25 (n = 3) and 0.0625 (n = 5).
- No "better" claim unless the paired CI excludes 0. Otherwise write "no significant difference", which is a valid finding.
- τ_th: sweep on tuning seeds at the **high-speed config (N = 30, v = 20, λ = 1)**, pick the best PDR/NRL compromise, **freeze**, then run Exp. B.

### 8.4 Prediction quality (cheap, high value: the "innovative" rigour touch)
From the recorder: a **warning** = a moment where τ̂ < τ_th for a used next hop. Then compute:
- **Precision** = warnings followed by a real break (true `d > R_max`) within τ_th / all warnings.
- **Recall** = breaks of used links that were warned before / all breaks.
- **Lead time** = actual break time − warning time (distribution).
This explains *why* a given τ_th works (Gauss-Markov changes direction every 0.5 s, so long horizons get imprecise).

### 8.5 Milestone sanity checks
- **G1 check:** explain one specific lost packet end-to-end from the recorder logs.
- **G2 check:** show one logged PROACTIVE_SWITCH **before** the real break of the old link.

### 8.6 Figures & tables (~8 figures)
| # | Content | Answers |
|---|---|---|
| Fig 1 | (a) architecture: UavNetSim stack + LEAP; (b) LET geometry | system model |
| Alg. 1 | LEAP next-hop selection + repair | R6 |
| Fig 2 | Loss causes, stacked bars per protocol (ref), + `LBR` vs speed | R3 / O2 |
| Fig 3 | Route recomputations per delivered packet vs N and v | R2 |
| Fig 4 | PDR vs N / v / λ: LEAP vs Greedy vs GRAd (CI) | R8 |
| Fig 5 | E2E delay + NRL vs speed (cost of prediction) | R8 |
| Fig 6 | **Ablation** A0 / A1 / A2 / R at high speed (paired Δ with CI) | R9 |
| Fig 7 | τ_th sensitivity (PDR & switches vs τ_th) + precision / lead time | R6, why |
| Fig 8 | Bonus: LEAP vs LEAP+XL (and sink scenario if done) | bonus |
| Table I | Simulation parameters | PDF |
| Table II | Related-work comparison | literature |
| Table III | Summary of gains (mean Δ, CI, p) | rigour |

---

## 9. Bonus (+3 max) — simple and finished

> Start only after Gate **G3** (core results frozen). A bonus counts only if it has **its own result**.

### 9.1 B1 — Cross-layer MAC retransmission rate (X1) ★★★ *(must)*
- Per neighbor *j*: `f_j ← (1−β)·f_j + β·1[ACK timeout]` on each attempt (failure via `penalize()`, success via ACK reception), β = 0.2, `f_j = 0` for new neighbors.
- In §6.3, the safe set *B* and Greedy's pick are ranked by `progress_j · (1 − f_j)` instead of `progress_j`.
- MAC unchanged: it only *reads* MAC outcomes. Evaluate **LEAP vs LEAP+XL** on S2 (speeds) + the λ = 5 high-load point, 3 seeds. Hypothesis: XL helps under congestion, where LET alone can't see the problem (H3).

### 9.2 B2 — UAV-assisted data collection, 1 fixed sink (X2) ★★ *(should, if time)*
- 1 static sink (speed 0, map centre) as a documented abstraction; all other UAVs send Poisson traffic **to the sink** (convergecast).
- Compare Greedy vs LEAP (vs LEAP+XL): PDR to sink, delay, loss causes. Interesting angle: does convergence near the sink shift losses from link breaks to collisions/queues?
- Cost: small patch (destination = sink, one zero-speed node).

### 9.3 Animated visualization ★ *(for the oral, low cost)*
Reuse `visualization/visualizer.py`: draw links coloured by τ̂ (green → red), flash PROACTIVE_SWITCH events. A 30–45 s clip for the talk.

### 9.4 B3 — "Does prediction survive a city?" on UavNetSim v2 ★ *(stretch, LAST: only after the whole project is finished: core, article, slides, demo)*
**Team decision:** the core stays on v1.0.1. B3 is attempted **only when everything else is done**, in a **separate environment and folder**, so it can never break the main project. If it fails, we lose nothing ("at least we tried"). If it works, it's a strong "innovative idea" bonus and a real limitations analysis.
- **Facts (verified in master `c2703f2`):** v2 keeps the **same routing interface** (`next_hop_selection` → `(has_route, packet, enquire)`, `packet_reception`, `penalize` called at `mac/csma_ca.py:166`) and registers all baselines incl. OPAR (`entities/drone.py:194-207`) → porting `routing/leap/` is mostly copying files. The building-aware **`a2a`** channel (`phy/channel.py:52`) is lighter than full ray tracing. Every run needs a compiled scene (`simulator/simulator.py:38`). The default scene has 5 buildings of 18–76 m on 600 × 600 m (`scenarios/default_scene.json`).
- **Feasibility gate (≤ 2 h):** separate venv → install v2 → `compile-scene` default scene → time one 30 s run in `a2a` mode. Fails or too slow → stop and mention in Future Work.
- **Experiment:** Greedy vs LEAP in the city scene, 1–2 speeds, 3 seeds. Split link breaks into **out of range** (predictable by LET) vs **blocked by a building** (not predictable), using the channel's line-of-sight flag.
- **Expected story (hypothesis):** LEAP's gain shrinks in the city because some breaks are blockages, which motivates obstacle-aware prediction as future work. Bonus visuals: v2's 3D web console for the oral.

Out of scope (Future Work): virtual-force topology control (X3), Kalman/ML predictors, GPS noise, full Sionna ray-tracing evaluation.

---

## 10. Software architecture & reproducibility (10 %)

### 10.1 Layout (repo not created yet)
```
leap-fanet-routing/                  # future repo
├── README.md · PATCHES.md · LICENSE (+ upstream MIT notice)
├── requirements.txt (pinned) · .python-version (3.12) · Makefile
├── <upstream v1.0.1 tree>      # first commit = pristine upstream (record hash)
├── routing/registry.py
├── routing/leap/
│   ├── __init__.py
│   ├── link_lifetime.py        # pure functions: r_max(), let_3d()  (unit-tested)
│   ├── leap_packet.py          # LeapHelloPacket(GreedyHelloPacket) + velocity, timestamp
│   ├── leap_table.py           # LeapNeighborTable(GreedyNeighborTable)
│   └── leap.py                 # Leap(Greedy); flags: tau_th, repair, xl ; GreedyReactive(Greedy)
├── instrumentation/recorder.py
├── experiments/{run_one.py, sweep.py, configs/*.yaml}
├── analysis/{aggregate.py, stats.py, plots.py}
├── results/ (raw gitignored, aggregated CSV committed) · figures/
├── tests/ · paper/ (IEEEtran + references.bib) · slides/ · docs/
```
`make setup | test | pilot | diagnostic | compare | tune | bonus | figures | paper | demo`

### 10.2 Tests (pytest)
| ID | Test |
|---|---|
| T1 | `let_3d`: static → ∞; moving apart (analytic); head-on (later exit root); perpendicular; out of range → 0; on boundary; near-zero speed; equals OPAR on in-range cases; µs↔s conversion |
| T2 | Interface: `Leap` has the methods, `packet_reception` is a generator, runs with N = 2 |
| T3 | **Prediction off ≡ Greedy** (decision function on the same table + full run with extra bits = 0) |
| T4 | **Golden regression:** hooks on == pristine upstream |
| T5 | Paired seeds: identical (t, src, dst) traffic and trajectories across protocols |
| T6 | Conservation: generated = delivered + losses + in-flight |
| T7 | Loss classifier: forced out-of-range → FAIL_RANGE; forced simultaneous tx → FAIL_COLLISION |
| T8 | Hop-count inflation by retries (M20) |

### 10.3 README
Purpose, method (1 paragraph), requirements, install (3 commands), **quickstart < 1 min**, reproduce each figure (`make …`), expected runtimes, outputs, parameters & seeds, tests, limitations, upstream version + license, citation, authors.

### 10.4 Git (when we create the repo)
`main` always runnable + short feature branches + PR reviewed by the other teammate. Tag `results-v1` at G3 and `final` at submission. No issue tracker/process overhead.

---

## 11. Article (English, LaTeX IEEEtran, mandatory structure [PDF p. 4])

**Working title:** *"LEAP-GR: Link-Expiration-Aware Predictive Geographic Routing for UAV Swarms"* (alt.: *"Anticipating Link Breaks in FANETs: Diagnosis and Predictive Greedy Forwarding on UavNetSim"*). Authors: Youssef Hamdani, Rayen Hamza, INSAT.
**Format:** no imposed template → **IEEEtran conference class** (`\documentclass[conference]{IEEEtran}`), the standard look of IEEE papers: clean and professional.
**Length:** no page limit. Aim for **~8–10 two-column pages incl. references**: dense and to the point, not padded.

### 11.0 What the professor explicitly wants to see (PDF p. 4 + p. 3 tip) — checklist
- [ ] **Title** precise, concise, representative of *our technical contribution* (never "Projet Futurs Réseaux Mobiles")
- [ ] **Abstract**: one paragraph, **150–250 words**, covering context/problem, technical challenge, our approach, **main quantitative results**
- [ ] **4–6 technical keywords**
- [ ] **Introduction**: general context + importance (technological stakes); **clear concrete problem**; quick positioning vs existing work (done / missing); **announce the paper structure at the end**
- [ ] **Related Work**: **critical synthesis**, based on **the PDF's references** (UavNetSim GitHub + arXiv, DSDV, OPAR, QGeo, Q-FANET, FANET routing survey) **plus our own research**
- [ ] **System Model / Proposed Approach**: detailed solution; **strong visuals** (block diagrams, architecture diagrams, flowcharts); **rigorous formalisation** (equations, cost functions, topologies defined here)
- [ ] **Implementation & Performance Evaluation**: environment (frameworks/simulator/datasets) **briefly**; **test scenarios with parameters in a table**; **clear graphs** (curves, histograms) comparing core vs extension *or* vs reference approach; **every figure analysed and commented in the text**
- [ ] **Conclusion & Perspectives**: main contributions and conclusions; **current limits** of our implementation; improvement leads / research perspectives
- [ ] **References**: numbered list, **strictly IEEE** format, everything cited in the text
- [ ] p. 3 tip: **explain *why* the system behaves this way**, not just describe results ("c'est cela qu'on attend en 3ᵉ année d'ingénieur")

### 11.0b Style & production rules [DECISION]
- **Figure-driven, not a blob of text.** Target: **≥ 1 visual per page** (≈ 3 diagrams + 6–7 plots + 3 tables + 1 algorithm). Each results subsection = **figure → what it shows (1 sentence) → why (mechanism, 2–4 sentences) → takeaway**.
- **Every figure/table is referenced in the text before it appears.** Captions are self-contained (what, config, n seeds, CI).
- **Diagrams in TikZ** (architecture, LET geometry, algorithm flowchart, loss-attribution decision tree). **Plots exported as vector PDF** from matplotlib with one shared style file: consistent colour per protocol across *all* figures, colour-blind-safe palette, also distinguishable in greyscale (markers/line styles), axis labels with units, 95 % CI error bars.
- Packages: `IEEEtran` (conference), `graphicx`, `booktabs` (tables), `siunitx` (units), `amsmath`, `algorithm`+`algpseudocode`, `cleveref`, `tikz`, `pgfplots` optional. Bibliography with `IEEEtran.bst` → strict IEEE automatically.
- Writing: short declarative sentences, active voice ("we measure…"), define every symbol once (notation table if > 8 symbols), numbers with units and CIs, no marketing adjectives ("novel", "robust", "significant" only when statistically significant).
- **Style pass:** after each section draft, edit out filler and stock phrasing (forced triads, "not X but Y", inflated claims), then a read-through by both of us. **Numbers and technical claims must not change during this pass.**
- Abstract and Conclusion are written **last**, from the frozen results only.
- Build: `make paper` (latexmk); figures regenerated from `results/` by `make figures`, never edited by hand.

| § | Content |
|---|---|
| 1 Title / Abstract / Keywords | **one paragraph, 150–250 words**: context → challenge → approach → **numbers** (written last, from results only). Keywords (4–6): *FANET, UAV swarm, geographic routing, link expiration time, link-break prediction, UavNetSim* |
| 2 Introduction | stakes; problem (reactive breaks); positioning (what's missing: distributed prediction + quantified loss attribution + isolated gain); contributions (3 bullets); **structure announcement** |
| 3 Related Work | critical synthesis by family: FANET surveys; topology-based (DSDV, GRAd); geographic (Greedy/GPSR); **prediction-based** (LET, OPAR, Kalman-based); RL (Q-Routing, QGeo, Q-FANET); simulators. **Table II** + the gap |
| 4 System Model & Approach | PHY (path loss, SINR, R_max derivation), MAC, mobility, traffic; LET derivation; Alg. 1; Fig 1 |
| 5 Implementation & Evaluation | environment (v1.0.1, SimPy, Py 3.12); patches & instrumentation; metric definitions; **Table I**; seeds/CI; diagnostic → comparison → ablation → τ_th/prediction quality → bonus. **Each figure: what + why.** **Threats to validity:** free-space PHY, oracle destination position, Gauss-Markov only, 30 s runs, 3–5 seeds, GRAd broadcast mode, OPAR oracle, density/load coupling in S1, energy disabled |
| 6 Conclusion & Future Work | contributions with numbers; where prediction helps and where it doesn't; limits; future: Kalman/learned predictors, VF topology control, realistic channel |
| 7 References | numbered by first citation, **strict IEEE**, only verified entries |

### 11.1 References: all verified 2026-11-07 against primary sources (Crossref DOI registry, arXiv API, NeurIPS proceedings, authors' pages)
**Rule:** the **7 references listed in the PDF (p. 16) must all be cited** (marked ★). Every entry below exists, with metadata checked. Put them in `references.bib` exactly as below; `IEEEtran.bst` produces the strict IEEE format.

| # | IEEE-style entry | Verified via |
|---|---|---|
| ★1 | Z. Zhou, Z. Dai, L. Huang, C. Yang, Y. Xiang, J. Tang, and K.-K. Wong, "UavNetSim-v1: A Python-based simulation platform for UAV communication networks," in *Proc. IEEE/CIC Int. Conf. Commun. China (ICCC)*, 2025, pp. 1–6, doi: 10.1109/ICCC65529.2025.11149314. (Preprint: arXiv:2507.09852, Jul. 2025.) | Crossref + arXiv |
| ★2 | Z. Zhou, "UavNetSim-v1," GitHub repository, tag v1.0.1 (commit a5622c5), 2026. [Online]. Available: https://github.com/Zihao-Felix-Zhou/UavNetSim-v1 (accessed: *date*) | git |
| ★3 | C. E. Perkins and P. Bhagwat, "Highly dynamic destination-sequenced distance-vector routing (DSDV) for mobile computers," in *Proc. ACM SIGCOMM*, 1994, pp. 234–244, doi: 10.1145/190314.190336. | Crossref |
| ★4 | M. Gharib, F. Afghah, and E. Bentley, "OPAR: Optimized predictive and adaptive routing for cooperative UAV networks," in *Proc. IEEE INFOCOM Workshops (INFOCOM WKSHPS)*, 2021, pp. 1–6, doi: 10.1109/INFOCOMWKSHPS51825.2021.9484489. | Crossref |
| ★5 | W.-S. Jung, J. Yim, and Y.-B. Ko, "QGeo: Q-learning-based geographic ad hoc routing protocol for unmanned robotic networks," *IEEE Commun. Lett.*, vol. 21, no. 10, pp. 2258–2261, Oct. 2017, doi: 10.1109/LCOMM.2017.2656879. | Crossref |
| ★6 | L. A. L. F. da Costa, R. Kunst, and E. P. de Freitas, "Q-FANET: Improved Q-learning based routing protocol for FANETs," *Comput. Netw.*, vol. 198, Art. no. 108379, Oct. 2021, doi: 10.1016/j.comnet.2021.108379. | Crossref |
| ★7 | M. F. Khan, K.-L. A. Yau, R. M. Noor, and M. A. Imran, "Routing schemes in FANETs: A survey," *Sensors*, vol. 20, no. 1, Art. no. 38, 2020, doi: 10.3390/s20010038. (Online Dec. 2019; PMC6983172) | Crossref |
| 8 | R. D. Poor, "Embedded networks: Pervasive, low-power, wireless connectivity," Ph.D. dissertation, Program in Media Arts and Sciences, MIT, Cambridge, MA, USA, 2001 (Ch. 4: GRAd). | CORE record (the 2000 GRAd note is cited by upstream but harder to verify, so cite the thesis) |
| 9 | J. A. Boyan and M. L. Littman, "Packet routing in dynamically changing networks: A reinforcement learning approach," in *Advances in Neural Information Processing Systems 6 (NIPS)*, 1993. | NeurIPS proceedings page |
| 10 | B. Karp and H. T. Kung, "GPSR: Greedy perimeter stateless routing for wireless networks," in *Proc. ACM MobiCom*, 2000, pp. 243–254, doi: 10.1145/345910.345953. | Crossref |
| 11 | W. Su, S.-J. Lee, and M. Gerla, "Mobility prediction and routing in ad hoc wireless networks," *Int. J. Netw. Manag.*, vol. 11, no. 1, pp. 3–30, 2001, doi: 10.1002/nem.386. **(The LET formula.)** | Crossref |
| 12 | I. Bekmezci, O. K. Sahingoz, and Ş. Temel, "Flying ad-hoc networks (FANETs): A survey," *Ad Hoc Netw.*, vol. 11, no. 3, pp. 1254–1270, May 2013, doi: 10.1016/j.adhoc.2012.12.004. | Crossref |
| 13 | D. Broyles, A. Jabbar, and J. P. G. Sterbenz, "Design and analysis of a 3-D Gauss-Markov mobility model for highly-dynamic airborne networks," in *Proc. Int. Telemetering Conf. (ITC)*, San Diego, CA, USA, Oct. 2010. | authors' group PDF (resilinets.org) + Arizona repository handle 10150/604297 |
| 14 | Y. Cui, Q. Zhang, Z. Feng, Z. Wei, C. Shi, and H. Yang, "Topology-aware resilient routing protocol for FANETs: An adaptive Q-learning approach," *IEEE Internet Things J.*, vol. 9, no. 19, pp. 18632–18649, Oct. 2022, doi: 10.1109/JIOT.2022.3162849. **(Kalman-based link-duration prediction, closest related work.)** | Crossref + arXiv:2306.17360 |
| (opt.) | M. Gharib, F. Afghah, and E. S. Bentley, "LB-OPAR: Load balanced optimized predictive and adaptive routing for cooperative UAV networks," *Ad Hoc Netw.*, vol. 132, Art. no. 102878, 2022, doi: 10.1016/j.adhoc.2022.102878. | Crossref |
Corrections made during verification: DSDV DOI is `10.1145/190314.190336` (not 190809); UavNetSim has a peer-reviewed ICCC 2025 version (cite it, not only arXiv); "TARRAQ" = Cui *et al.*, IEEE IoT J. 2022. Any new reference must be verified the same way before it goes into the .bib.

---

## 12. Oral: 10 min talk + 10 min Q&A, plus functional demo

### 12.1 Talk (10 min, ~10 slides, ~5 min each speaker)
| t | Slide | Speaker |
|---|---|---|
| 0:00 | Hook: **Video 2** (30 s animation), a link breaks and LEAP switches in time | Y |
| 0:40 | Problem & objectives (O1–O3) | Y |
| 1:30 | Platform + how we attribute losses (SNR-without-interference test) | Y |
| 2:30 | **Diagnostic result:** loss causes and RR (Figs 2–3) | Y |
| 3:45 | LEAP-GR: LET equation + "Greedy unless about to break" (Fig 1b, Alg. 1) | R |
| 5:00 | **Video 1:** functional demo, recorded run (40 s) | R |
| 5:45 | Fair comparison & ablation design | R |
| 6:30 | **Results + why** (Figs 4, 6) | R |
| 8:00 | Bonus (Fig 8) | R |
| 9:00 | Limits + conclusion (1 number to remember) | Y |
(Y = Youssef, R = Rayen; swap freely.)

### 12.2 Functional demo (deliverable [PDF]): **recorded, shown inside the talk**
Decision: the demo is part of the presentation and is **pre-recorded** (no live run).
- **Video 1, "it runs" (≈ 40 s, terminal screen recording):** `make demo` → 10 drones, 10 s, Greedy then LEAP. The output shows PDR, loss breakdown, route recomputations and the number of PROACTIVE_SWITCH events. Speed up the boring parts (×2–×4) and add a caption overlay naming each step.
- **Video 2, "what it does" (≈ 30 s, the animation from §9.3):** drones with links coloured by τ̂, a link turning red, LEAP switching neighbor *before* the break, Greedy losing packets on the same seed. Doubles as the opening hook.
- **Production:** record at 1920×1080, export **MP4 (H.264)**, **embed in the slides** (no streaming, no internet needed), and keep a copy of each video + the slides PDF on **two devices and a USB stick**. Each video has a still-image fallback slide.
- **Honesty rule:** the videos show real runs of the committed code (record the git hash on screen). The code also stays ready to run on a laptop in case she asks during Q&A.
- Recording happens **after G3** (results frozen), so the numbers in the videos match the article.

### 12.3 Q&A bank (10 min, so prepare ~15 answers, each member answers all)
1. Derive the LET equation. Why relative velocity?
2. What does τ̂ predict and what not? (geometry only, not interference)
3. Why is it exact to separate link break from collision on this platform?
4. Why constant velocity under Gauss-Markov? How wrong is it? (precision / lead time)
5. How was τ_th chosen? Why not tuned on the test seeds?
6. Your backup is one hop, not a route. Is that enough?
7. What if no safe neighbor exists?
8. How do you know the gain comes from prediction, not more hellos? (A0/A1, same hellos, T3)
9. Is the comparison with GRAd fair, since it has no ACK?
10. Why not just compare with OPAR? (oracle, centralised)
11. Why do higher loads reduce PDR even with stable links? (H3)
12. Only 3–5 seeds: are the results significant? (paired design, CI, paired t)
13. Overhead of LEAP? (+128 bit/hello, extra hops?)
14. Why did you disable the energy model?
15. What does the cross-layer bonus add, and why can the retry rate mislead? (contention vs bad link)

---

## 13. Work plan (phases & gates — team decision: tight deadline, but **no scope reduction for time**; we go phase by phase as fast as possible)

| Phase | Order | Content | Gate |
|---|---|---|---|
| P0 Setup | 1st | uv + Py 3.12; pristine headless run; **benchmark t_run vs N**; confirm M20, M22, M26 with small scripts; pilot λ ∈ {1, 5} | **G0:** runtime table → final seed plan |
| P1 Diagnostic | 2nd | patches P1–P7, recorder, tests T4–T8, runner; Exp. A | **G1:** Figs 2–3 + one lost packet explained |
| P2 LEAP | 3rd (can start in parallel with P1: LET + tests don't need the recorder) | `routing/leap/`, T1–T3; Exp. C (τ_th tuning) | **G2:** τ_th frozen + one proactive switch shown before a break |
| P3 Main results | 4th | Exp. B, stats, Figs 4–7 | **G3:** results frozen (tag) |
| P4 Bonus | 5th | B1 → B2 (if time) → animation | each bonus has its own figure |
| P6 Stretch bonus B3 | **last**, after P5 is complete | v2 feasibility gate (≤ 2 h) → city experiment → add one figure + paragraph to the article | never touches the main repo's results |
| P5 Write & defend | in parallel from P1 | LaTeX skeleton + TikZ diagrams + Related work during P1–P2; System model after P2; Evaluation after P3; style pass per section; slides + demo last; **2 timed rehearsals (10 + 10)** | article PDF, slides, demo |

**Split (adjustable, each must master everything):** Youssef: setup, patches, recorder/loss taxonomy, runner, stats/plots, article §5, B1. Rayen: LEAP + LET tests, τ_th tuning + prediction quality, article §3–4, B2 + animation. Together: Intro/Abstract/Conclusion, analysis, slides, rehearsals, cross-review of PRs.

## 14. Risks
| Risk | Mitigation |
|---|---|
| Runs too slow | benchmark first; tiered seeds → all-3 fallback; 2 laptops overnight; never change polling |
| Energy depletion silently ends runs | P7 + check in pilot (M26) |
| Instrumentation changes behaviour | golden test T4; recorder never draws random numbers |
| No gain at the reference point | valid result if explained; show where it helps (high v); ablation explains why |
| MAC saturation hides effects | λ = 1 reference + λ sweep |
| Bonus eats core time | gate G3 first; B1 only by default |
| Unverified citations | §11.1 status table; nothing unverified in the .bib |

## 15. Definition of Done
- [ ] R1–R9 each → code + figure + article paragraph (matrix §1.2)
- [ ] Tests T1–T8 pass; `make figures` regenerates every figure from raw results
- [ ] Every figure: CI bars, caption, *why* paragraph
- [ ] Abstract 150–250 words, one paragraph, with numbers; 4–6 keywords; Table I; IEEE refs verified
- [ ] README tested on the other teammate's laptop
- [ ] Videos 1 and 2 recorded from the frozen code (git hash visible), embedded in the slides, copies on 2 devices + USB
- [ ] 2 rehearsals of 10 min + 10 min Q&A

## 16. Resolved questions (all closed 2026-11-07)
| Question | Answer |
|---|---|
| Platform version | **UavNetSim-v1 tag `v1.0.1`** (includes the June 2026 fixes): confirmed |
| Article language / length / template | **English**, no page limit, **no imposed template** → **IEEEtran conference**, clean, professional, humanized (§11) |
| Upstream patches | **Small, documented patches are acceptable** (§4.3, `PATCHES.md`) |
| "Couche MAC identique" and GRAd | **Accepted:** same CSMA/CA protocol and parameters for all; GRAd keeps its native broadcast-without-ACK mode (§7) |
| Oral format | **10 min talk + 10 min Q&A** |
| Functional demo | **During the presentation, shown as pre-recorded videos** (live demos are prone to fail) (§12.2) |
No open questions remain. Anything new goes here with the date.

## 18. Repository quality standard (portfolio-grade)

**Goal (team, 2026-11-07):** after the defense, the repo goes on our CVs and LinkedIn. It must read like the work of careful engineers: clean, documented, reproducible, no slop. Two audiences: Dr Afif (grading) and a recruiter or engineer skimming for 2 minutes.

### 18.1 Repository content
| Item | Standard |
|---|---|
| `README.md` | 1-line pitch → badges (CI, Python 3.12, license) → **hero visual** (the τ̂ animation GIF) → **key result in one sentence with real numbers** → what's inside → quickstart (< 1 min) → reproduce every figure → method in brief (LET equation + Alg. 1 diagram) → results (3–4 figures) → limitations → paper (PDF link) → citation → authors (GitHub/LinkedIn) → acknowledgments (UavNetSim authors, Dr Afif, INSAT) → license. Gets the style pass. |
| `docs/` | `architecture.md` (diagram of the stack + where our code plugs in), `methodology.md` (metric definitions, loss taxonomy, seeds/stats), `reproducing.md` (exact commands + expected runtimes), `upstream-facts.md` (= UPSTREAM_FACTS, polished), `design-spec.md` (= this SPEC, cleaned of chat-specific notes at release) |
| `PATCHES.md` | every upstream modification: file, lines, why, behaviour-neutral? |
| `CHANGELOG.md` | Keep a Changelog format; versions `v0.x` → `v1.0.0` at submission |
| `CITATION.cff` | how to cite the repo (shows on GitHub's sidebar); cites UavNetSim upstream too |
| `LICENSE` | MIT (ours) + upstream MIT notice preserved (`LICENSE-UPSTREAM`) |
| `paper/` | LaTeX source + **compiled PDF attached to the GitHub Release** |
| `slides/` + videos | slides PDF in the release; videos as release assets (not in git history) |
| `results/` | aggregated CSVs + figures committed; **raw results zipped as a release asset** |
| `.github/` | `workflows/ci.yml`, `pull_request_template.md` |
| GitHub settings | description, topics (`fanet`, `uav`, `routing`, `simpy`, `wireless-networks`, `link-prediction`), social preview image, release `v1.0.0` |

### 18.2 Code standard
- **Our code** (`routing/leap/`, `instrumentation/`, `experiments/`, `analysis/`, `tests/`): type hints, docstrings (NumPy style, with units), `ruff` lint + format, no dead code, no commented-out blocks, no stray `print`, no leftover TODOs at release, explicit units in names (`t_us`, `tau_s`, `d_m`).
- **Upstream code is never reformatted**: patches stay minimal so `git diff <pristine-commit>` stays readable. Ruff excludes upstream paths.
- Config in YAML, no magic numbers in code; every parameter documented once.
- Tests T1–T8 in `pytest`; CI runs lint + unit tests + a **smoke simulation** (N = 5, 3 s) on every push/PR, < 3 min.
- `pre-commit` hooks (ruff, trailing whitespace, end-of-file, large-file guard).

### 18.3 Git history standard
- Commit 1 = pristine UavNetSim v1.0.1 (message records upstream URL + commit `a5622c5`). Then small logical commits.
- **Conventional Commits** (`feat(leap): …`, `fix(recorder): …`, `docs: …`, `test: …`, `exp: …`), imperative mood, one change per commit, body explains *why*.
- `main` protected and always green. Short-lived branches → PR (template: what / why / how tested / checklist) → review by the teammate → squash-merge.
- Never commit: venvs, caches, raw logs, large binaries, secrets, personal planning files.
- Tags: `results-v1` (frozen results), `v1.0.0` (submission) with a GitHub Release.

### 18.4 Anti-slop rules (docs, comments, commits, article)
- Every sentence must be **true, specific and checkable**. No filler ("This robust and innovative solution…"), no marketing adjectives, no emoji walls, no generic boilerplate sections.
- Numbers only from `results/` produced by committed configs. Claims about the simulator cite `file:line`.
- Comments explain *why*, not *what*. Docs are short and current; outdated docs are fixed or deleted.
- Human-facing prose (README, docs, article) gets the style pass (§11.0b), then a read-through by one of us.

### 18.5 Decisions at repo creation (ask the team then)
- Repo name (**chosen: `leap-fanet-routing`**) and owner account (Youssef's or Rayen's, both as collaborators).
- Internal files: personal scratch notes and earlier draft specs stay out of git; the shared working rules (`CLAUDE.md`) are tracked (D-008).
- Commit attribution: commits are authored by the team member who makes them; no co-author trailers (decided 2026-11-07, D-008).

## 19. Drift-control protocol (how we stay on track)

At each checkpoint, re-read the requirement → compare with what was built → fix or log the deviation.
| When | Check |
|---|---|
| **Start of every work session** | Re-read SPEC §0, §1 (compliance matrix), the current phase in §13. State the task and which requirement (R#/O#/X#) it serves. Anything that serves none is out of scope. |
| **Before every commit** | Tests pass; ruff clean; `PATCHES.md` updated if upstream changed; no unverified number or claim; commit message conventional. |
| **At every gate (G0–G3)** | Walk the §1 matrix row by row: done / partial / missing. Check facts against the PDF (pp. 3–4, 15–16). Update the Definition of Done (§15). |
| **Before writing any article/README text** | Re-read SPEC §11.0 (professor's checklist) + the PDF p. 4. |
| **When a fact surprises us** | Verify in code, record it in UPSTREAM_FACTS with `file:line`, and update the SPEC with a changelog entry. Never silently diverge from the spec. |
| **Before release** | Fresh clone on the other laptop → README quickstart → `make test` → `make figures` reproduces the figures. |

## 17. Changelog
- **v1.5 (2026-11-07):** Phase 1 instrumentation implemented (P1–P7, recorder, runner, sweep, tests T2 and T4–T8; T4 golden test passed). Corrected §5.2: OPAR has no relay re-planning (M36). New facts M35–M38. Recorder method in D-011.
- **v1.4 (2026-11-07):** defense version uses 3 seeds everywhere (D-009); 5-seed Exp B after the defense. Priority order core → B1 → animation → B2 (if time); B3 after the defense (D-010).
- **v1.3 (2026-11-07):** seed plan decided at G0: tiered 3/5 kept (D-004). Added `docs/DECISIONS.md` (decision log with alternatives, reasons and Q&A defence; D-001 to D-007) and `docs/LAB_NOTEBOOK.md` (dated run records with every number and its source file), to feed the article, README and oral.
- **v1.2 (2026-11-07), Phase 0 / G0:** UavNetSim-v1 `v1.0.1` (`a5622c5d0a9f7b62b4e1d5a7dcc8978f34f0c85f`, verified) exported into the project; Python 3.12.15 venv with pinned deps. Phase-0 runs use a runtime harness (`experiments/phase0/`), upstream files untouched. **Runtime table** (Greedy, 30 s, v = 10, energy off, seed 2025, ~6 concurrent runs on 8 cores; wall s / peak RSS MB / PDR %): N=10 λ=1 254/116/78.3 · N=10 λ=5 435/118/76.4 · N=30 λ=1 938/160/86.1 · N=30 λ=5 1049/168/58.9 · N=50 λ=1 1658/244/87.3 · N=50 λ=5 1711/258/20.4. Confirms [EST] that λ = 5 saturates N ≥ 30 (delay 2.2 s and 3.7 s) while λ = 1 does not (N = 50 delay 19 ms). **Confirmed by runs:** M20 (4.7 % of delivered packets inflated at N=30 λ=5, +3.4 % mean hop count), M22 (traffic and trajectories bit-identical across Greedy/DSDV/GRAd; sub-channel draws differ), M26 (sleep at 14.15/16.45/19.55 s for 5/10/20 m/s). **New facts** M28–M34 (GRAd 3.5× simulation cost; ghost packet after sleep; silent source-queue overflow counted as generated; unicast shares the packet object; polling-dominated linear-in-N cost; `.idea`/`.pyc` in upstream; observe-only probes behaviour-neutral). M5 corrected (logging level behaviour-neutral, no measurable slowdown). Compute estimate in §8.2.
- **v1.1 (2026-11-07):** added §18 **repository quality standard** (portfolio-grade: README structure, docs, CI, conventional commits, releases, anti-slop rules) and §19 **drift-control protocol**. Revised the v0.2 rejection of CITATION.cff/CHANGELOG/PR template: cheap and valuable for a public portfolio repo.
- **v1.0 FINAL (2026-11-07):** all open questions closed (§16): v1.0.1 confirmed, no template → IEEEtran conference, small documented patches accepted, GRAd broadcast interpretation accepted, demo = **pre-recorded videos inside the 10-min talk** (§12.2 production plan, talk timing updated with both videos).
- **v0.4 (2026-11-07):** **All 14 references verified** against primary sources and written in IEEE form with DOIs (§11.1). Corrected the DSDV DOI; added UavNetSim's ICCC 2025 version; identified "TARRAQ" = Cui *et al.* 2022; GRAd now cited via Poor's thesis. The 7 PDF references are marked as mandatory citations. **Added B3** (UavNetSim v2 city test, strictly last, separate environment, §9.4 + P6). **Diagnostic extended to QGeo and Q-FANET** (cited in the PDF + "pour chaque protocole existant"). Fixed the dangling "T9" reference. Full re-read against the PDF (§1 matrix re-checked).
- **v0.3 (2026-11-07):** article section expanded: PDF p. 4 checklist (§11.0), LaTeX/TikZ/vector-plot production rules, figure-driven layout, style pass (§11.0b), no page limit (target ~8–10 pages). Timeline expressed as phases and gates, without deadline-driven scope cuts.
- **v0.2 (2026-11-07):** team decisions: v1.0.1 confirmed, English article, oral 10 + 10 min, traffic per drone as in the PDF (density/load coupling discussed in the article), scope cut. **Merged from an external spec review:** "Greedy unless about to break" formulation, no separate monitor process or probe packet (per-packet check = backup search), prediction-off ≡ Greedy test, τ_th tuned on separate seeds, warning precision / lead time, "one-hop backup ≠ route" wording, milestone sanity checks, `OTHER` loss bucket. **New facts:** energy depletion after ≈14–19 s (M26 → patch P7); MAC/channel random numbers not paired across protocols (M22). **Stats fix:** Wilcoxon impossible with ≤ 5 seeds → paired t-test + CI. **Seeds:** tiered 3 / 5 (§8.2). Ablation reduced to 4 variants; bonus reduced to B1 (+B2 if time) + animation.
- **v0.1 (2026-11-07):** initial spec.
