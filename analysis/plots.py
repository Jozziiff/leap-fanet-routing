"""Article figures (SPEC §8.6), regenerated from aggregated CSVs; never edited by hand.

One fixed colour, marker and line style per protocol across every figure (colour-blind-safe palette,
validated; markers and line styles keep series distinguishable in greyscale print). Error bars are
Student-t 95 % confidence intervals over seeds.

Usage::

    python -m analysis.plots --exp-a results/exp_a.csv --exp-b results/exp_b.csv --exp-c results/exp_c.csv \
        --out figures/
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from analysis.stats import paired, summarize

# label -> (display name, colour, marker, line style). Colours: validated 8-slot categorical palette.
STYLE = {
    "leap": ("LEAP-GR", "#2a78d6", "o", "-"),
    "greedy": ("Greedy", "#eb6834", "s", "--"),
    "grad": ("GRAd", "#1baf7a", "^", "-."),
    "dsdv": ("DSDV", "#eda100", "v", ":"),
    "opar": ("OPAR", "#e87ba4", "D", "-"),
    "q_routing": ("Q-Routing", "#008300", "P", "--"),
    "qgeo": ("QGeo", "#6250d6", "X", "-."),
    "qfanet": ("Q-FANET", "#e34948", "*", ":"),
    # Exp B controls: neutral ink, not a ninth hue (they are variants of LEAP, not new protocols)
    "greedy_reactive": ("Reactive repair (control)", "#52514e", ">", ":"),
    "leap_select": ("LEAP-select (A1)", "#2a78d6", "o", ":"),
}
DIAGNOSTIC_ORDER = ["dsdv", "greedy", "grad", "opar", "q_routing", "qgeo", "qfanet"]
CAUSE_GROUPS = [  # greyscale + hatching: causes never reuse protocol colours
    ("Link break", ["loss_LINK_BREAK"], "#1f1f1f", ""),
    ("Collision", ["loss_COLLISION"], "#6e6e6e", "//"),
    ("No route", ["loss_NO_ROUTE"], "#a8a8a8", ""),
    (
        "Other",
        ["loss_QUEUE_OVERFLOW", "loss_TTL", "loss_EXPIRED", "loss_DISCARD", "loss_OTHER"],
        "#dcdcdc",
        "..",
    ),
]
REF = {"n": 30, "speed": 10.0, "rate": 1.0}
SWEEPS = [
    ("n", "Number of UAVs $N$", {"speed": 10.0, "rate": 1.0}),
    ("speed", "Mean speed (m/s)", {"n": 30, "rate": 1.0}),
    ("rate", r"$\lambda$ (packets/s per UAV)", {"n": 30, "speed": 10.0}),
]
SINGLE, DOUBLE = 3.5, 7.16  # IEEE column widths (in)


def setup() -> None:
    plt.rcParams.update(
        {
            "font.size": 8,
            "axes.titlesize": 8,
            "axes.labelsize": 8,
            "legend.fontsize": 7,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "lines.linewidth": 1.2,
            "lines.markersize": 4,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": "#e6e6e3",
            "grid.linewidth": 0.6,
            "axes.edgecolor": "#52514e",
            "pdf.fonttype": 42,
            "savefig.bbox": "tight",
        }
    )


def save(fig, out: Path, name: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out / f"{name}.{ext}", dpi=300)
    plt.close(fig)


def subset(df: pd.DataFrame, fixed: dict) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    for k, v in fixed.items():
        mask &= df[k] == v
    return df[mask]


def line_panel(ax, df, labels, var, fixed, metric, scale=1.0):
    for label in labels:
        s = summarize(subset(df[df["label"] == label], fixed), metric, by=[var])
        if s.empty:
            continue
        s = s.sort_values(var)
        name, colour, marker, ls = STYLE.get(label, (label, "#52514e", "o", "-"))
        ax.errorbar(
            s[var],
            s["mean"] * scale,
            yerr=s["ci"].fillna(0) * scale,
            color=colour,
            marker=marker,
            linestyle=ls,
            capsize=2,
            label=name,
        )


def fig_loss_causes(a: pd.DataFrame, out: Path) -> None:
    """Fig. 2: (a) final causes of lost packets at the reference point; (b) link-break share vs speed."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(DOUBLE, 2.5), gridspec_kw={"width_ratios": [1.3, 1]})
    ref = subset(a, REF)
    labels = [p for p in DIAGNOSTIC_ORDER if p in set(ref["label"])]
    bottoms = [0.0] * len(labels)
    for name, cols, colour, hatch in CAUSE_GROUPS:
        vals = []
        for label in labels:
            g = ref[ref["label"] == label]
            vals.append(100 * (g[cols].sum(axis=1) / g["generated"]).mean())
        ax1.bar(
            range(len(labels)),
            vals,
            bottom=bottoms,
            color=colour,
            hatch=hatch,
            edgecolor="white",
            linewidth=0.8,
            width=0.6,
            label=name,
        )
        bottoms = [b + v for b, v in zip(bottoms, vals)]
    ax1.set_xticks(range(len(labels)), [STYLE[p][0] for p in labels], rotation=30, ha="right")
    ax1.set_ylabel("Lost packets (% of generated)")
    ax1.set_title(r"(a) Loss causes, $N$=30, 10 m/s, $\lambda$=1")
    ax1.set_ylim(0, 1.3 * max(bottoms))
    ax1.legend(frameon=False, ncol=2, loc="upper left")
    # GRAd forwards by broadcast without a chosen next hop, so it has no link-break losses by construction
    unicast = [p for p in labels if p != "grad"]
    line_panel(ax2, a, unicast, "speed", {"n": 30, "rate": 1.0}, "loss_link_break_per_generated", 100)
    ax2.set_ylim(bottom=0)
    ax2.set_xticks([5, 10, 15, 20])
    ax2.set_xlabel("Mean speed (m/s)")
    ax2.set_ylabel("Lost to link breaks (% of generated)")
    ax2.set_title(r"(b) Link-break losses vs speed, $N$=30, $\lambda$=1")
    ax2.legend(frameon=False, ncol=2)
    save(fig, out, "fig2_loss_causes")


def fig_recomputations(a: pd.DataFrame, out: Path) -> None:
    """Fig. 3: route recomputations per delivered packet vs N and vs speed."""
    labels = [p for p in DIAGNOSTIC_ORDER if p in set(a["label"])]
    fig, axes = plt.subplots(1, 2, figsize=(DOUBLE, 2.4), sharey=True)
    for ax, (var, xlabel, fixed) in zip(axes, SWEEPS[:2]):
        line_panel(ax, a, labels, var, fixed, "rr")
        ax.set_xlabel(xlabel)
    axes[1].set_xticks([5, 10, 15, 20])
    axes[0].set_ylabel("Recomputations / delivered")
    axes[1].legend(frameon=False, ncol=2)
    save(fig, out, "fig3_recomputations")


def fig_comparison(
    ab: pd.DataFrame,
    out: Path,
    labels=("greedy", "grad", "greedy_reactive", "leap"),
    metric="pdr",
    ylabel="Packet delivery ratio (%)",
    name="fig4_pdr",
    scale=100.0,
) -> None:
    """Fig. 4: PDR of LEAP vs Greedy vs GRAd over the three sweeps (same seeds, same MAC)."""
    fig, axes = plt.subplots(1, 3, figsize=(DOUBLE, 2.3), sharey=True)
    for ax, (var, xlabel, fixed) in zip(axes, SWEEPS):
        line_panel(ax, ab, list(labels), var, fixed, metric, scale)
        ax.set_xlabel(xlabel)
    if metric == "pdr":
        axes[0].set_ylim(0, 105)
    axes[0].set_ylabel(ylabel)
    handles, names = axes[0].get_legend_handles_labels()
    fig.legend(handles, names, frameon=False, ncol=len(names), loc="upper center", bbox_to_anchor=(0.5, 1.08))
    save(fig, out, name)


def fig_cost(ab: pd.DataFrame, out: Path, labels=("greedy", "grad", "greedy_reactive", "leap")) -> None:
    """Fig. 5: end-to-end delay and control overhead (bits per delivered packet) vs speed."""
    ab = ab.assign(ctrl_kbit_per_delivered=ab["control_tx_bits"] / ab["delivered"] / 1e3)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(DOUBLE, 2.3))
    line_panel(ax1, ab, list(labels), "speed", {"n": 30, "rate": 1.0}, "delay_mean_ms")
    ax1.set_ylabel("Mean delay, delivered (ms)")
    line_panel(ax2, ab, list(labels), "speed", {"n": 30, "rate": 1.0}, "ctrl_kbit_per_delivered")
    ax2.set_ylabel("Control kbit / delivered")
    for ax in (ax1, ax2):
        ax.set_xlabel("Mean speed (m/s)")
        ax.set_xticks([5, 10, 15, 20])
    ax1.set_yscale("log")  # GRAd's delay is an order of magnitude above the unicast protocols
    ax2.set_ylim(bottom=0)
    ax2.legend(frameon=False)
    save(fig, out, "fig5_cost")


def fig_ablation(ab: pd.DataFrame, out: Path, config: dict) -> pd.DataFrame:
    """Fig. 6: paired differences isolating the gain of prediction (one series: variants on the y-axis)."""
    pairs = [
        ("greedy", "leap_select", "A1 LEAP-select − Greedy"),
        ("greedy", "leap", "A2 LEAP − Greedy"),
        ("greedy", "greedy_reactive", "R reactive − Greedy"),
        ("greedy_reactive", "leap", "A2 LEAP − R reactive"),
    ]
    sel = subset(ab, config)
    rows = []
    for base, other, text in pairs:
        p = paired(sel, "pdr", base, other)
        if not p.empty:
            rows.append({**p.iloc[0].to_dict(), "text": text})
    res = pd.DataFrame(rows)
    if res.empty:
        return res
    fig, ax = plt.subplots(figsize=(SINGLE, 1.9))
    y = range(len(res))
    ax.barh(
        list(y), 100 * res["diff"], xerr=100 * res["ci"].fillna(0), color="#2a78d6", height=0.5, capsize=2
    )
    ax.axvline(0, color="#52514e", linewidth=0.8)
    ax.set_yticks(list(y), res["text"])
    ax.invert_yaxis()
    ax.set_xlabel("Paired PDR difference (percentage points)")
    ax.set_title(f"$N$={config['n']}, {config['speed']:g} m/s, $\\lambda$={config['rate']:g}")
    save(fig, out, "fig6_ablation")
    return res


def fig_tau(c: pd.DataFrame, out: Path) -> None:
    """Fig. 7: (a) PDR vs tau_th with Greedy's level; (b) proactive switches; (c) warning precision and recall."""
    leap = c[c["label"].str.startswith("leap_tau")].copy()
    leap["tau"] = leap["label"].str.replace("leap_tau", "").astype(float)
    shadow = c[c["label"].str.startswith("shadow_w")].copy()
    shadow["tau"] = shadow["label"].str.replace("shadow_w", "").astype(float)
    fig, axes = plt.subplots(1, 3, figsize=(DOUBLE, 2.3), gridspec_kw={"wspace": 0.45})
    s = summarize(leap, "pdr", by=["tau"]).sort_values("tau")
    axes[0].errorbar(
        s["tau"],
        100 * s["mean"],
        yerr=100 * s["ci"].fillna(0),
        color=STYLE["leap"][1],
        marker="o",
        capsize=2,
        label="LEAP-GR",
    )
    g = summarize(c[c["label"] == "greedy"], "pdr", by=["label"])
    if not g.empty:
        axes[0].axhline(100 * g["mean"].iloc[0], color=STYLE["greedy"][1], linestyle="--", label="Greedy")
    axes[0].set_ylabel("PDR (%)")
    axes[0].legend(frameon=False)
    if "leap_PROACTIVE_SWITCH" in leap:
        leap["switch_per_delivered"] = leap["leap_PROACTIVE_SWITCH"].fillna(0) / leap["delivered"]
        s = summarize(leap, "switch_per_delivered", by=["tau"]).sort_values("tau")
        axes[1].errorbar(
            s["tau"], s["mean"], yerr=s["ci"].fillna(0), color=STYLE["leap"][1], marker="o", capsize=2
        )
    axes[1].set_ylabel("Proactive switches / delivered")
    if not shadow.empty:
        sh = shadow.sort_values("tau")
        axes[2].plot(sh["tau"], 100 * sh["pred_precision"], color="#52514e", marker="o", label="Precision")
        axes[2].plot(
            sh["tau"], 100 * sh["pred_recall"], color="#52514e", marker="s", linestyle="--", label="Recall"
        )
        axes[2].legend(frameon=False)
        axes[2].set_ylim(0, 105)
    axes[2].set_ylabel("Shadow-mode warnings (%)")
    for ax in axes:
        ax.set_xscale("log", base=2)
        ax.set_xticks([0.25, 0.5, 1, 2, 4], ["0.25", "0.5", "1", "2", "4"])
        ax.minorticks_off()
        ax.set_xlabel(r"Threshold $\tau_{th}$ (s)")
    save(fig, out, "fig7_tau")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exp-a", type=Path)
    ap.add_argument("--exp-b", type=Path)
    ap.add_argument("--exp-c", type=Path)
    ap.add_argument("--out", type=Path, default=Path("figures"))
    a = ap.parse_args()
    setup()
    exp_a = pd.read_csv(a.exp_a) if a.exp_a else None
    if exp_a is not None:
        fig_loss_causes(exp_a, a.out)
        fig_recomputations(exp_a, a.out)
    if a.exp_b:
        exp_b = pd.read_csv(a.exp_b)
        ab = (
            pd.concat([exp_b, exp_a[exp_a["label"].isin(["greedy", "grad"])]]) if exp_a is not None else exp_b
        )
        fig_comparison(ab, a.out)
        fig_cost(ab, a.out)
        res = fig_ablation(ab, a.out, {"n": 30, "speed": 20.0, "rate": 1.0})
        if not res.empty:
            res.to_csv(a.out / "table_ablation.csv", index=False)
        table = [
            paired(ab, metric, base, other)
            for base, other in [
                ("greedy", "leap"),
                ("greedy", "greedy_reactive"),
                ("greedy_reactive", "leap"),
                ("leap_select", "leap"),
                ("grad", "leap"),
            ]
            for metric in ("pdr", "delay_mean_ms")
        ]
        pd.concat(table).to_csv(a.out / "table_paired.csv", index=False)
    if a.exp_c:
        fig_tau(pd.read_csv(a.exp_c), a.out)


if __name__ == "__main__":
    main()
