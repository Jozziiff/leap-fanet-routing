# Methodology

How the experiments are set up, what each metric means, and how the results are compared. The full
reasoning behind each choice is in [`SPEC.md`](SPEC.md) §8 and [`DECISIONS.md`](DECISIONS.md).

## Testbed

Fixed for every run (upstream defaults): 600 × 600 × 100 m area, Gauss–Markov 3D mobility, 802.11b at
2 Mbps, CSMA/CA with 5 MAC retries, 1024-byte payloads, queue of 200 packets, packet lifetime 10 s. Energy
depletion is disabled (patch P7), otherwise drones stop after 14 to 20 s. A run lasts 30 s: traffic starts at
2 s and stops at 27 s, which leaves time for packets in flight to arrive.

Every drone is a Poisson source of rate λ to random destinations, as on the platform. The sweeps change one
factor at a time around a reference point (N = 30 drones, 10 m/s, λ = 1 packet/s per drone):

| Sweep | Values |
|---|---|
| Number of drones N | 10, 20, 30, 40, 50 |
| Mean speed | 5, 10, 15, 20 m/s |
| Traffic rate λ | 0.5, 1, 2, 5 packets/s per drone |

That gives 11 distinct configurations. In the N sweep the total offered load (N·λ) grows with N, so density
and load are coupled; the article reads that sweep together with the λ sweep.

## Metrics

Each run writes one JSON file with its configuration, our git hash, the upstream commit, the upstream metrics
and ours (`metrics`):

| Metric | Definition |
|---|---|
| `pdr` | packets delivered / packets generated (each packet counted once, duplicates removed) |
| `delay_mean_ms`, `delay_p95_ms` | end-to-end delay of delivered packets |
| `losses` | lost packets by final cause: `LINK_BREAK`, `COLLISION`, `NO_ROUTE`, `QUEUE_OVERFLOW`, `TTL`, `EXPIRED`, `DISCARD` (GRAd only), `OTHER` |
| `lbr_vs_collision` | link-break losses / (link-break + collision losses) |
| `loss_link_break_per_generated` | link-break losses / packets generated |
| `rr` | route recomputations per delivered packet |
| `leap_events` | LEAP-GR decisions: warnings, proactive switches, risky forwards, kept destinations |
| `prediction` | precision, recall and lead time of the lifetime warnings (shadow mode, see below) |

## Loss attribution

The recorder follows every packet and gives each lost packet one final cause, from the last thing that
happened to it. A failed reception is a **link break** when the frame could not have been decoded even
without interference (its SNR is below the 6 dB threshold, i.e. the receiver is farther than
R_max = 249.3 m), and a **collision** otherwise. The PHY's path loss is deterministic, so this split is
exact on this platform. A packet still moving at the end is `IN_FLIGHT` and left out of the loss shares.

A **route recomputation** is a second decision for the same packet at the same node, a route-discovery
broadcast, or a change of next hop after an ACK timeout. Greedy's MAC retries to the same neighbour are not
recomputations. The exact rules, and the alternatives we rejected, are in DECISIONS D-011.

## Isolating the prediction

LEAP-GR could beat Greedy simply because it switches neighbour at all. To separate the two effects, the
comparison includes a **reactive control**: the same code and the same hello messages as LEAP-GR, without
prediction, switching to another neighbour after every failed attempt. LEAP-GR minus the control is the gain
due to prediction alone. The MAC is identical in every run.

**Prediction quality** is measured in shadow mode: the protocol behaves exactly like Greedy and only logs a
warning when a used link's predicted lifetime drops below a horizon. Precision is the share of warnings
followed by a real break; recall is the share of real breaks that were warned; lead time is the time between
warning and break.

## Seeds and statistics

- Same seed means same traffic and same trajectories for every protocol (but not the same MAC backoffs), so
  protocols are compared on **paired** per-seed differences.
- 3 test seeds (1-3) per configuration. The threshold τ_th was tuned on separate seeds (100-102) and frozen
  by a rule committed before the tuning runs finished (D-016): the smallest τ_th whose mean PDR is within 0.5 points
  of the best. The result, 0.25 s, is in [`tau_freeze.json`](tau_freeze.json).
- Each point is a mean with a 95 % Student-t confidence interval. A difference is called significant only
  when the paired 95 % CI excludes zero (paired t-test). With 3 seeds a Wilcoxon test cannot reach p < 0.05,
  so it is not used.
