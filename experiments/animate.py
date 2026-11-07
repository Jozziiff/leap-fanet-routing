"""Side-by-side animation of Greedy and LEAP-GR on the same seed (oral hook and demo Video 2, SPEC §9.3, §12.2).

Each link between two UAVs within radio range is coloured by its predicted lifetime (3-D link expiration
time from the current positions and velocities, range 0.9 R_max): red below the LEAP threshold, grey at
the threshold, blue when long-lived. Greedy's panel marks every packet lost to a link break; LEAP's panel
flashes every proactive switch. Frames come from two real recorded runs of the committed code.

Usage::

    python experiments/animate.py --out figures/leap_vs_greedy.mp4 [--gif figures/leap_vs_greedy.gif]
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------- recording
def record(args: argparse.Namespace) -> None:
    """Run one simulation (in this fresh process) and dump sampled frames and events as JSON."""
    sys.path.insert(0, str(REPO / "experiments"))
    import run_one

    run_args = run_one.parse_args(
        [
            "--protocol",
            args.protocol,
            "--params",
            args.params,
            "--n",
            str(args.n),
            "--speed",
            str(args.speed),
            "--rate",
            str(args.rate),
            "--seed",
            str(args.seed),
            "--sim-time-s",
            str(args.sim_time_s),
            "--traffic-start-s",
            "1",
            "--traffic-end-s",
            str(args.sim_time_s - 1),
            "--out",
            str(args.dump),
        ]
    )
    run_one.configure(run_args)
    import simpy

    from instrumentation import hooks
    from instrumentation.recorder import Recorder
    from simulator.simulator import Simulator
    from utils import config

    rec = Recorder(keep_events=True)
    hooks.REC = rec
    env = simpy.Environment()
    frames: list = []

    def sampler(sim):
        while True:
            frames.append(
                [env.now / 1e6, [list(d.coords) for d in sim.drones], [list(d.velocity) for d in sim.drones]]
            )
            yield env.timeout(args.frame_dt_s * 1e6)

    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()):
        sim = Simulator(
            seed=args.seed,
            env=env,
            channel_states={i: simpy.Resource(env, capacity=1) for i in range(args.n)},
            n_drones=args.n,
        )
        rec.attach(sim)
        env.process(sampler(sim))
        env.run(until=config.SIM_TIME)
    keep = {"PROACTIVE_SWITCH", "REPAIR", "DROP", "DELIVERED", "GEN"}
    events = [e for e in rec.events if e[1] in keep]
    commit = run_one.git_state()
    Path(args.dump).write_text(
        json.dumps(
            {
                "frames": frames,
                "events": events,
                "commit": commit,
                "summary": rec.summary(),
                "protocol": args.protocol,
            }
        )
    )


def record_in_subprocess(protocol: str, params: str, a: argparse.Namespace, dump: Path) -> dict:
    cmd = [
        sys.executable,
        "-W",
        "ignore",
        __file__,
        "record",
        "--protocol",
        protocol,
        "--params",
        params,
        "--n",
        str(a.n),
        "--speed",
        str(a.speed),
        "--rate",
        str(a.rate),
        "--seed",
        str(a.seed),
        "--sim-time-s",
        str(a.sim_time_s),
        "--frame-dt-s",
        str(a.frame_dt_s),
        "--dump",
        str(dump),
    ]
    subprocess.run(cmd, check=True, cwd=dump.parent)
    return json.loads(dump.read_text())


# --------------------------------------------------------------- rendering
def render(greedy: dict, leap: dict, a: argparse.Namespace) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import imageio_ffmpeg
    import matplotlib.pyplot as plt
    from matplotlib import animation
    from matplotlib.colors import LinearSegmentedColormap, Normalize

    sys.path.insert(0, str(REPO))
    from phy.large_scale_fading import maximum_communication_range
    from routing.leap.link_lifetime import let_3d

    r_max = maximum_communication_range()
    r_pred = 0.9 * r_max
    plt.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()
    cmap = LinearSegmentedColormap.from_list("lifetime", ["#e34948", "#c9c8c3", "#2a78d6"])
    norm = Normalize(vmin=0.0, vmax=2 * a.tau_th_s)

    fig, axes = plt.subplots(1, 2, figsize=(16, 9), dpi=120)
    fig.patch.set_facecolor("#fcfcfb")
    runs = [("Greedy forwarding", greedy), (rf"LEAP-GR ($\tau_{{th}}$ = {a.tau_th_s:g} s)", leap)]
    n_frames = min(len(greedy["frames"]), len(leap["frames"]))
    flash_s = 0.4

    def events_until(run, t, kind, cause=None):
        return [
            e for e in run["events"] if e[1] == kind and e[0] / 1e6 <= t and (cause is None or e[4] == cause)
        ]

    def draw(k):
        for ax, (title, run) in zip(axes, runs):
            ax.clear()
            t, coords, vels = run["frames"][k]
            ax.set_xlim(0, 600)
            ax.set_ylim(0, 600)
            ax.set_aspect("equal")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_facecolor("#fcfcfb")
            n = len(coords)
            for i in range(n):
                for j in range(i + 1, n):
                    d = math.dist(coords[i], coords[j])
                    if d > r_max:
                        continue
                    dp = [coords[j][q] - coords[i][q] for q in range(3)]
                    dv = [vels[j][q] - vels[i][q] for q in range(3)]
                    tau = min(let_3d(dp, dv, r_pred), 2 * a.tau_th_s)
                    ax.plot(
                        [coords[i][0], coords[j][0]],
                        [coords[i][1], coords[j][1]],
                        color=cmap(norm(tau)),
                        linewidth=1.6 if tau < a.tau_th_s else 1.0,
                        zorder=1,
                    )
            xs, ys = [c[0] for c in coords], [c[1] for c in coords]
            ax.scatter(xs, ys, s=70, color="#0b0b0b", edgecolor="#fcfcfb", linewidth=2, zorder=3)
            breaks = events_until(run, t, "DROP", "LINK_BREAK")
            for e in breaks:
                if t - e[0] / 1e6 <= flash_s:
                    ax.scatter(
                        [coords[e[3]][0]], [coords[e[3]][1]], marker="X", s=260, color="#e34948", zorder=4
                    )
            switches = events_until(run, t, "PROACTIVE_SWITCH") + events_until(run, t, "REPAIR")
            for e in switches:
                if t - e[0] / 1e6 <= flash_s and e[4] and e[4][0] is not None:
                    i, j = e[3], e[4][0]
                    ax.annotate(
                        "",
                        xy=(coords[j][0], coords[j][1]),
                        xytext=(coords[i][0], coords[i][1]),
                        arrowprops={"arrowstyle": "-|>", "color": "#0b0b0b", "lw": 2.5},
                        zorder=5,
                    )
            gen = len(events_until(run, t, "GEN"))
            dlv = len(events_until(run, t, "DELIVERED"))
            pdr = f"{100 * dlv / gen:.1f} %" if gen else "-"
            ax.set_title(title, fontsize=18, color="#0b0b0b")
            stats = f"lost to link breaks: {len(breaks)}\ndelivered so far: {pdr}"
            if run is leap:
                stats += f"\nproactive switches + repairs: {len(switches)}"
            ax.text(0.0, -0.02, stats, transform=ax.transAxes, fontsize=13, color="#52514e", va="top")
        fig.suptitle(
            f"Same seed: same UAVs, same traffic   ·   t = {greedy['frames'][k][0]:5.2f} s",
            fontsize=16,
            color="#0b0b0b",
        )

    fig.text(
        0.5,
        0.905,
        r"links coloured by predicted lifetime: red $<\tau_{th}<$ blue   ·   "
        "✕ packet lost to a link break   ·   arrow: LEAP switches next hop before the break",
        ha="center",
        fontsize=12,
        color="#52514e",
    )
    commit = (leap.get("commit") or {}).get("commit") or "unknown"
    fig.text(0.99, 0.01, f"UavNetSim-v1 v1.0.1 · code {commit[:7]}", ha="right", fontsize=10, color="#8a8984")

    anim = animation.FuncAnimation(fig, draw, frames=n_frames, interval=1000 / a.fps)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    anim.save(
        a.out, writer=animation.FFMpegWriter(fps=a.fps, codec="libx264", extra_args=["-pix_fmt", "yuv420p"])
    )
    if a.gif:
        anim.save(a.gif, writer=animation.PillowWriter(fps=min(a.fps, 10)), dpi=60)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", nargs="?", default="make", choices=["make", "record"])
    ap.add_argument("--protocol", default="greedy")
    ap.add_argument("--params", default="{}")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--speed", type=float, default=20.0)
    ap.add_argument("--rate", type=float, default=2.0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--sim-time-s", type=float, default=20.0)
    ap.add_argument("--frame-dt-s", type=float, default=0.05)
    ap.add_argument("--tau-th-s", type=float, default=1.0)
    ap.add_argument("--fps", type=int, default=20)
    ap.add_argument("--dump", type=Path)
    ap.add_argument("--out", type=Path, default=REPO / "figures" / "leap_vs_greedy.mp4")
    ap.add_argument("--gif", type=Path, default=None)
    a = ap.parse_args()
    if a.mode == "record":
        record(a)
        return
    with tempfile.TemporaryDirectory() as tmp:
        greedy = record_in_subprocess("greedy", "{}", a, Path(tmp) / "greedy.json")
        leap = record_in_subprocess(
            "leap", json.dumps({"tau_th_s": a.tau_th_s, "repair": "predictive"}), a, Path(tmp) / "leap.json"
        )
    render(greedy, leap, a)
    print(
        f"Greedy: {greedy['summary']['losses']['LINK_BREAK']} link-break losses, PDR {greedy['summary']['pdr']:.3f}"
    )
    print(
        f"LEAP:   {leap['summary']['losses']['LINK_BREAK']} link-break losses, PDR {leap['summary']['pdr']:.3f}"
    )
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
