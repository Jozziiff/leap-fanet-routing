"""Confidence intervals and paired comparisons over seeds (SPEC §8.3).

Same seed means same traffic and trajectories across protocols (UPSTREAM_FACTS M22), so protocols are
compared on per-seed differences (paired t-test), not on raw means. No "better" claim unless the paired
95 % CI excludes zero.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats

CONFIG_KEYS = ["n", "speed", "rate"]


def ci95(values: pd.Series | np.ndarray) -> tuple[float, float, int]:
    """Mean, half-width of the Student-t 95 % confidence interval, and sample size."""
    x = np.asarray(values, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n == 0:
        return math.nan, math.nan, 0
    if n == 1:
        return float(x[0]), math.nan, 1
    half = stats.t.ppf(0.975, n - 1) * x.std(ddof=1) / math.sqrt(n)
    return float(x.mean()), float(half), n


def summarize(df: pd.DataFrame, metric: str, by: list[str] | None = None) -> pd.DataFrame:
    """Mean and 95 % CI of ``metric`` per group (default: label x configuration)."""
    by = by or ["label", *CONFIG_KEYS]
    rows = []
    for key, g in df.groupby(by, sort=True):
        mean, half, n = ci95(g[metric])
        rows.append(
            {
                **dict(zip(by, key if isinstance(key, tuple) else (key,))),
                "mean": mean,
                "ci": half,
                "n_seeds": n,
            }
        )
    return pd.DataFrame(rows)


def paired(df: pd.DataFrame, metric: str, base: str, other: str) -> pd.DataFrame:
    """Per configuration: mean of ``other - base`` over common seeds, its 95 % CI and the paired t-test p."""
    rows = []
    for key, g in df[df["label"].isin([base, other])].groupby(CONFIG_KEYS, sort=True):
        wide = g.pivot_table(index="seed", columns="label", values=metric).dropna()
        if base not in wide or other not in wide or len(wide) < 2:
            continue
        diff = wide[other] - wide[base]
        mean, half, n = ci95(diff)
        p = float(stats.ttest_rel(wide[other], wide[base]).pvalue) if diff.std(ddof=1) > 0 else math.nan
        rows.append(
            {
                **dict(zip(CONFIG_KEYS, key)),
                "base": base,
                "other": other,
                "metric": metric,
                "base_mean": wide[base].mean(),
                "other_mean": wide[other].mean(),
                "diff": mean,
                "ci": half,
                "p": p,
                "n_seeds": n,
                "significant": bool(not math.isnan(half) and abs(mean) > half),
            }
        )
    return pd.DataFrame(rows)


def sweep_of(row: pd.Series, reference: tuple[float, float, float] = (30, 10, 1)) -> list[str]:
    """Which one-factor sweeps (S1 drones, S2 speed, S3 rate) a configuration belongs to."""
    n0, v0, r0 = reference
    out = []
    if row["speed"] == v0 and row["rate"] == r0:
        out.append("S1")
    if row["n"] == n0 and row["rate"] == r0:
        out.append("S2")
    if row["n"] == n0 and row["speed"] == v0:
        out.append("S3")
    return out
