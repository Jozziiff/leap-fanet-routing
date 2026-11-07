# UavNetSim-v1 — Verified facts (read from source, not guessed)

> Verified on 2026-11-07 by reading the source code of
> `https://github.com/Zihao-Felix-Zhou/UavNetSim-v1` at tag **`v1.0.1`** (commit `a5622c5`, 2026-06-02).
> Line numbers refer to that tag. **Re-verify if you change the pinned version.**
> Phase-0 runs (2026-11-07) used `experiments/phase0/harness.py` (runtime overrides, upstream files untouched) under Python 3.12.15.
> Status legend: ✅ read in code · 🧮 computed by us from code constants · ⚠ to verify by running (Phase 0).

## 1. Which version and why

| Item | Fact | Status |
|---|---|---|
| Tags | `v1.0.0` (6fd4846, 2026-01-20), `v1.0.1` (a5622c5, 2026-06-02) | ✅ |
| `master` | On 2026-08-20 the repo was migrated to "v2" (`pyproject` version `2.0.0`): FastAPI web console, React frontend, **NVIDIA Sionna RT** (`sionna-rt==2.0.1`) ray-tracing channel, OSM scenes. Default `CHANNEL_MODE = "online"` needs a compiled Sionna scene. | ✅ |
| v1.0.1 deps | `matplotlib==3.10.1, numpy==2.2.4, openpyxl==3.1.5, Pillow==11.2.1, scikit_opt==0.6.6, simpy==4.1.1` — pure Python, laptop-friendly | ✅ |
| Python | Machine has Python **3.14**; numpy 2.2.4 / matplotlib 3.10.1 wheels target ≤3.13 → use **Python 3.12 via `uv`** | ✅ (uv present) / ⚠ install |
| License | MIT (Copyright 2025 Zihao Zhou) → we may vendor/modify, must keep LICENSE | ✅ |
| Paper | arXiv:2507.09852 (14 Jul 2025), Zhou, Dai, Huang, Yang, Xiang, Tang, Wong. README bibtex also lists IEEE/CIC ICCC 2025 (Shanghai) | ✅ arXiv / ⚠ ICCC on IEEE Xplore |

**Decision: pin `v1.0.1`.** It matches the PDF's description ("plateforme Python fondée sur SimPy… DSDV, Greedy, GRAd, OPAR, Q-Routing… PDR, délai, NRL, nombre de sauts… contrôle de topologie par force virtuelle") and avoids the Sionna/GPU stack. Ask the professor to confirm (see SPEC §16).

## 2. Protocol interface (what our module must implement)

| Method | Called from | Contract | Status |
|---|---|---|---|
| `__init__(self, simulator, my_drone)` | `entities/drone.py:106` (`self.routing_protocol = Dsdv(self.simulator, self)`) | hard-coded install → we add a registry | ✅ |
| `next_hop_selection(self, packet)` | `drone.py` `feed_packet()` | returns **`(has_route, final_packet, enquire)`**; sets `packet.next_hop_id`. If `has_route` is False the packet goes to `waiting_list`; if `enquire` is True, `final_packet` (a control packet) is sent | ✅ |
| `packet_reception(self, packet, src_drone_id)` | `drone.py` `receive()` via `env.process(...)` | **must be a generator** (SimPy process). Must handle hello, `DataPacket`, `AckPacket`, **`VfPacket`** (virtual force), reply ACK after `SIFS` | ✅ |
| `penalize(self, packet)` | `mac/csma_ca.py:167` on **every ACK timeout** | not mentioned in README but **required** (AttributeError otherwise). Hook for cross-layer bonus and predictive repair | ✅ |
| `check_waiting_list()` | own SimPy process (Greedy: every 0.6 s) | re-tries packets in `waiting_list` | ✅ |

## 3. Mechanics that matter for our study

| # | Fact | Where | Status |
|---|---|---|---|
| M1 | Drone speed is **hard-coded `speed = 10`** (heterogeneous: `random.randint(5,60)`) → must be parametrised for the 5–20 m/s sweep | `simulator/simulator.py:61-63` | ✅ |
| M2 | Poisson traffic **rate hard-coded `rate = 5`** pkt/s/drone; destination uniform among other drones | `entities/drone.py:142` | ✅ |
| M3 | `MAX_TTL = NUMBER_OF_DRONES + 1` computed **at import time** | `utils/config.py:45` | ✅ |
| M4 | `config` is mutable module state; global packet-ID counters `GL_ID_*` are **never reset** in v1.0.1 → **one simulation per fresh Python process** | `utils/config.py` | ✅ |
| M5 | Logging at `INFO` to `running_log.log` (verbose). **Phase-0 run:** pristine defaults (DSDV, N=10, seed 2025) give identical metrics at INFO and WARNING (754 generated, 707 delivered, delay 24.672 ms) and no measurable wall-time difference (110.6 vs 111.7 s, 3.3 MB log). Logging level is behaviour-neutral; WARNING is used to avoid the disk output | `simulator/log.py`, `phy/phy.py:5` | ✅ code + run |
| M6 | Blocking `plt.show()` calls: `scatter_plot` (start+end), `show_trajectory` in mobility models, energy model, VF → must be disabled for headless batch | `visualization/static_drawing.py:37,66`, `mobility/gauss_markov_3d.py:164`, … | ✅ |
| M7 | Gauss-Markov 3D: position update 0.1 s, direction update 0.5 s, α = 0.85; `speed` arg = **mean speed** (`velocity_mean`); wall rebound | `mobility/gauss_markov_3d.py` | ✅ |
| M8 | Mobility **reassigns** `drone.coords = next_position` (new list) → hello snapshots are true stale snapshots (no oracle leak) | `gauss_markov_3d.py:127` | ✅ |
| M9 | Greedy hello carries **position only** (`cur_position = src_drone.coords`, captured at hello *creation*, not transmission) | `routing/greedy/greedy_packet.py:15` | ✅ |
| M10 | Hello interval 0.5 s (+1–2 ms jitter); neighbor entry lifetime **2 s** (`BaseTable.entry_life_time`) → a departed neighbor can stay in the table up to 2 s | `greedy.py:40`, `routing/base/base_table.py:28` | ✅ |
| M11 | Greedy picks the neighbor **closest to destination** (max progress) → tends to pick neighbors at the **edge of range** (most likely to break) | `greedy_neighbor_table.py` `best_neighbor` | ✅ |
| M12 | On ACK timeout the MAC calls `penalize(pkd)` and **retransmits to the same `pkd.next_hop_id`** (no re-routing) up to `MAX_RETRANSMISSION_ATTEMPT = 5`, then drops silently | `mac/csma_ca.py:160-185` | ✅ |
| M13 | **GRAd disables MAC ACKs** (`enable_ack = False`) and sends everything as **broadcast** (`transmission_mode = 1`) → no retransmissions, no single next hop | `routing/grad/grad.py:52,84,105,151` | ✅ |
| M14 | **OPAR is centralised/oracle**: reads every drone's true `coords` and `velocity`, Dijkstra with a link-lifetime constraint; `link_lifetime_predictor` is the classic constant-velocity quadratic (no guard for `A=0` or negative discriminant) | `routing/opar/opar.py:50-210,347-370` | ✅ |
| M15 | PHY: free-space path loss α = 2, `P_t = 0.1 W`, `NOISE_POWER = 4e-11 W`, SNR threshold 6 dB (802.11b @ 2 Mbps, 2.4 GHz). Reception = packet with max SINR among simultaneously-completed ones, accepted if `SINR ≥ 6 dB` | `phy/large_scale_fading.py`, `utils/config.py`, `drone.py:366` | ✅ |
| M16 | `unicast_put` puts the frame **only in the next hop's inbox regardless of distance** → an out-of-range next hop simply fails the SINR test (silent loss) | `phy/channel.py` | ✅ |
| M17 | `metrics.collision_num` is incremented whenever a reception has **any** co-channel interferer, **even if decoded** → it is NOT a loss counter | `phy/large_scale_fading.py:59` | ✅ |
| M18 | Carrier sense is **channel-agnostic** with `SENSING_RANGE = 750 m` (≈ whole 600×600×100 m map) → effectively one collision domain; sub-channels 1/6/11 picked at random per packet only reduce collisions | `utils/util_function.py` `check_channel_availability`, `allocation/channel_assignment.py:66` | ✅ |
| M19 | **Every drop path is silent** (retry limit, expiry, SINR < threshold, queue full at relay → no ACK, TTL exceeded, waiting-list expiry) → we must instrument | `drone.py`, `csma_ca.py`, `greedy.py` | ✅ |
| M20 | `increase_ttl()` is called **on every transmission attempt** (incl. retransmissions) on the *same object*; the receiver copies it → the "hop count" metric (= TTL at destination) is likely **inflated by retransmissions**, and retries consume TTL budget | `csma_ca.py:117,137`, `metrics.calculate_metrics` | ✅ code / ✅ **run (Phase 0, 2026-11-07):** Greedy N=30, λ=5, seed 2025: 123/2644 delivered packets (4.7 %) have TTL > true hops (excess 1–4); mean upstream hop count 1.635 vs true 1.582 (+3.4 %); never TTL < hops. At N=10, λ=1: 0/220 (no retried delivery) |
| M21 | `copy.copy` is shallow → `number_retransmission_attempt` dict is shared across hops of the same packet | `greedy.py:119`, `entities/packet.py` | ✅ |
| M22 | Per-entity RNGs seeded from `seed + id + offset` (`rng_drone`, `rng_mac`, `rng_mobility`, `rng_routing`, `rng_channel_assignment`); start positions from `random.seed(seed+i)` → runs are deterministic. **Traffic (`rng_drone`: arrival times, destinations) and trajectories (`rng_mobility`) are identical across protocols for the same seed.** **But** `rng_channel_assignment` is drawn for every data *and* control packet (`drone.py:164`, `greedy.py:50`, `grad.py:67,92,136`) and `rng_mac` for every backoff (`csma_ca.py:71`) → **sub-channel choices and backoffs diverge between protocols** (different numbers of control packets). So CRN is partial: traffic + mobility paired, MAC randomness not | `drone.py`, `mobility/*`, `start_coords.py`, `allocation/channel_assignment.py:47` | ✅ code / ✅ **run (Phase 0):** N=10, λ=1, seed 2025, Greedy vs DSDV vs GRAd: identical (t, src, dst) sequences (281 packets) and bit-identical positions (300 samples × 10 drones, max diff 0.0 m); data-packet sub-channel differs for 57/281 (DSDV) and 184/281 (GRAd) packets |
| M23 | `metrics.print_metrics` divides by `len(datapacket_arrived)` → ZeroDivisionError if nothing is delivered | `simulator/metrics.py` | ✅ |
| M24 | `BaseTable.is_item` returns `None` (not `False`) for unknown ids — harmless but beware in `if` chains | `routing/base/base_table.py:34-39` | ✅ |
| M26 | **Energy depletion kills the run early.** `EnergyModel.energy_monitor` (started in `energy_model.py:50`) sets `drone.sleep = True` when `residual_energy ≤ ENERGY_THRESHOLD = 2 kJ`; `INITIAL_ENERGY = 20 kJ`; Gauss-Markov deducts `power_consumption(speed)·0.1 s` each step (`gauss_markov_3d.py:137`). With the config rotor constants, flight power ≈ **1283 W @5 m/s, 1104 W @10, 924 W @20** → drones go to sleep after ≈ **14 s @5 m/s, 16 s @10, 19 s @20**, i.e. before the upstream default `SIM_TIME = 30 s`. A sleeping drone stops generating, sending and receiving. This also **confounds the speed sweep** (slow drones die first). **Mitigation:** set `INITIAL_ENERGY` very high (e.g. 1e9 J) in all routing experiments, documented in PATCHES/Table I as "energy depletion disabled, out of scope" | `energy/energy_model.py:52-68`, `utils/config.py` | ✅ code / 🧮 power recomputed (1283.4 / 1104.0 / 977.0 / 923.8 W at 5/10/15/20 m/s) / ✅ **run (Phase 0):** N=10, Greedy, λ=1: all 10 drones asleep at 14.15 / 16.45 / 19.55 s for 5 / 10 / 20 m/s (sampled at 0.05 s offset; analytic 14.1 / 16.4 / 19.5 s). All drones die at the same instant because consumption uses the constant `drone.speed` (`gauss_markov_3d.py:136`) |
| M27 | All baselines (DSDV, Greedy, OPAR, Q-Routing, QGeo, Q-FANET) implement `next_hop_selection`, `packet_reception`, `penalize`. **GRAd has no `penalize()`**, which only works because GRAd disables ACKs, so `wait_ack` (the only caller) never runs. Never enable ACKs for GRAd | `routing/grad/grad.py`, `mac/csma_ca.py` | ✅ |
| M28 | **GRAd is ≈ 3.5× more expensive to simulate** than the other protocols (wall time 248 s vs 66–71 s for Greedy, DSDV, OPAR, Q-Routing, QGeo, Q-FANET; N=30, 3 s, λ=1, 2 concurrent runs). Cause: flooding. `M_REQUEST` is broadcast with `remaining_value=20` (`grad.py:101`), relays re-broadcast data/request messages (`grad.py:151-165,185,212`), and every broadcast is copied into every inbox (`phy/channel.py:40-42`), so each receiver evaluates many more frames. Simulation cost only, not a network metric | `routing/grad/grad.py`, `phy/channel.py` | ✅ code + run |
| M29 | **One "ghost" packet per drone after it falls asleep.** `generate_data_packet` checks `self.sleep` (`drone.py:132`) *before* the inter-arrival wait (`drone.py:143`), so a drone that sleeps during the wait still creates and counts one packet (`drone.py:175`) that can never be sent (`feed_packet` has exited). Observed: last generation at 17.6–21.7 s after sleep at 14.15–19.55 s. Moot with P7 | `entities/drone.py:131-188` | ✅ code + run |
| M30 | **Source-side queue overflow is silent and counted as generated.** `datapacket_generated_num` is incremented (`drone.py:175`) before the queue-size check (`drone.py:182-186`); a packet arriving at a full queue is discarded without any trace. The recorder must log it as `QUEUE_OVERFLOW` at the source, not only at relays (M19) | `entities/drone.py:175-186` | ✅ code |
| M31 | **Unicast passes the sender's packet object itself** to the receiver's inbox (`phy/channel.py:55`, no copy); only broadcast/multicast copy (`channel.py:41,69`). The receiver's `copy.copy` (e.g. `greedy.py:119`) is what separates hops. Instrumentation must not mutate a received data packet before that copy, or it also mutates the sender's (possibly retransmitted) object | `phy/channel.py`, `phy/phy.py:45-47` | ✅ code |
| M32 | **Run cost is dominated by polling and grows ~linearly with N.** `receive()` polls every 5 µs (`drone.py:384`), `feed_packet()` every 10 µs (`drone.py:227`), `listen()` every 1 µs during backoff (`csma_ca.py:227`). Measured (Greedy, 30 s, v=10, energy off, ~6 concurrent runs on 8 cores): see SPEC changelog v1.2 / G0 table; ≈ 35·N − 97 s at λ=1. Peak RSS 116–258 MB per run | `entities/drone.py`, `mac/csma_ca.py` | ✅ code + run |
| M33 | Upstream tag `v1.0.1` **ships IDE and bytecode files**: `.idea/` (6 files) and `routing/qmr/__pycache__/*.pyc` (cpython-39 and -312). Harmless (sources are newer, so Python recompiles), but they are clutter for our repo → decide at repo creation | `git ls-tree v1.0.1` | ✅ |
| M34 | **Observe-only probes are behaviour-neutral:** a run with probes (wrapped `Phy.unicast`, `Metrics.calculate_metrics`, `DataPacket` subclass, 0.1 s sampler) gave metrics identical to the same run without probes (Greedy N=30, λ=5: generated 4488, delivered 2644, delay 2206.587 ms, collision_num 2013, control 1800 in both) | Phase-0 harness | ✅ run |
| M25 | Virtual-force topology control: replace `mobility_model` by `VfMotionController(self)` in `drone.py`; VF packets are processed by the **routing** module's `packet_reception` | README, `greedy.py` VfPacket branch | ✅ |

## 4. Numbers derived from the constants (🧮 — recompute if config changes)

| Quantity | Value | How |
|---|---|---|
| Max range `R_max` (no interference) | **≈ 249.3 m** | `R = c/(4π f_c) · 10^((10log P_t − 10log N − γ_th)/(10α))` = `maximum_communication_range()` |
| Data frame size | 8656 bit (1024 B payload + IP 20 B + MAC 14 B + PHY 192 bit) | config |
| Data airtime @ 2 Mbps | **4.33 ms** | 8656 / 2e6 |
| ACK airtime / timeout | 120 µs / 180 µs | config |
| Per-frame service time (1st attempt) | ≈ DIFS 50 + mean backoff 300 + 4328 + SIFS 10 + ACK 120 ≈ **4.8 ms** | ⇒ ≈ **208 unicast frames/s** for the whole (single-domain) network |
| Saturation per-drone rate (h̄ ≈ 2 hops) | λ_sat ≈ 208 / (2N): N=10 → ~10, N=30 → ~3.5, **N=50 → ~2.1 pkt/s** | upstream default λ = 5 saturates N ≥ 30 |
| Hello frame / overhead | 720 bit (IP 160 + MAC 112 + PHY 192 + payload 256) → 0.36 ms airtime; 2 hellos/s/drone → ~7 % airtime at N = 50 (incl. DIFS + backoff) | config |
| Mean neighbor degree (rough) | ≈ 0.4·(N−1): N=10 → ~4, N=50 → ~20 (dense, few partitions) | disk πR² ≈ 0.54 of map area, edge effects |
| Mean src–dst distance | ≈ 315 m (uniform in 600×600×100) → ~2 hops on average | 0.5214·L |

**Implication:** with the upstream default λ = 5 pkt/s, MAC congestion and queueing would hide the link-break effect at large N. The load sweep must include **low loads (0.5–2 pkt/s)**. ⚠ Validate with the Phase-0 pilot.
