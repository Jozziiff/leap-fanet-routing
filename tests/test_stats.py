"""Statistics helpers: group keys must survive aggregation (regression: the seed count once overwrote N)."""

import pandas as pd

from analysis.stats import paired, summarize


def _runs() -> pd.DataFrame:
    rows = []
    for n in (10, 30):
        for seed in (1, 2, 3):
            rows.append(
                {"label": "a", "n": n, "speed": 10.0, "rate": 1.0, "seed": seed, "pdr": 0.5 + 0.01 * seed}
            )
            rows.append(
                {"label": "b", "n": n, "speed": 10.0, "rate": 1.0, "seed": seed, "pdr": 0.6 + 0.01 * seed}
            )
    return pd.DataFrame(rows)


def test_summarize_keeps_group_column_n() -> None:
    s = summarize(_runs()[lambda d: d["label"] == "a"], "pdr", by=["n"])
    assert sorted(s["n"]) == [10, 30]
    assert set(s["n_seeds"]) == {3}


def test_paired_keeps_configuration_n() -> None:
    p = paired(_runs(), "pdr", "a", "b")
    assert sorted(p["n"]) == [10, 30]
    assert set(p["n_seeds"]) == {3}
    assert p["diff"].round(9).eq(0.1).all()
