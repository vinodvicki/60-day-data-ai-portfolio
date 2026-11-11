"""Pure metric functions for Day 7 — Disease Prevalence Dashboard.

No I/O, no network. Every function here is unit-tested in
tests/test_pipeline.py. All rates are crude prevalence, percent of adults
aged 18+ (CDC PLACES, see research_brief.md).

Definitions (frozen in plan.md §4):
  M2  estimated cases = round(prevalence / 100 * adult population)
  M3  year-over-year change in percentage points and percent
  M4  state rate = population-weighted: 100 * sum(cases) / sum(adult pop)
  M6  spread statistics for a set of county prevalences
  M7  median confidence-interval width (precision indicator)
"""

from __future__ import annotations

import pandas as pd


def estimated_cases(prevalence_pct: float, adult_pop: float) -> int:
    """Estimated number of adults with the condition (M2).

    The denominator is the adult (18+) population, never the total
    population.
    """
    return round(prevalence_pct / 100.0 * adult_pop)


def weighted_rate(total_cases: float, total_adult_pop: float) -> float:
    """Population-weighted prevalence in percent (M4/M5).

    100 * sum(estimated cases) / sum(adult population). A simple mean of
    county percentages would weight a county of 1,000 adults the same as
    one of 1,000,000 — that is forbidden in this project.
    """
    if total_adult_pop <= 0:
        raise ValueError("adult population must be positive")
    return 100.0 * total_cases / total_adult_pop


def yoy_change(value_2022: float, value_2023: float) -> tuple[float, float]:
    """Year-over-year change (M3): (percentage points, percent).

    Percentage points are the headline; percent change is secondary
    (a 1 pp move on a 5% base is +20% and must never be headlined alone).
    """
    pp_change = value_2023 - value_2022
    pct_change = 100.0 * pp_change / value_2022 if value_2022 != 0 else float("nan")
    return pp_change, pct_change


def spread_stats(values: pd.Series) -> dict:
    """Spread / disparity statistics for county prevalences (M6)."""
    s = pd.to_numeric(values, errors="coerce").dropna()
    if s.empty:
        raise ValueError("no numeric values for spread statistics")
    q1 = float(s.quantile(0.25))
    q3 = float(s.quantile(0.75))
    return {
        "n": len(s),
        "min": float(s.min()),
        "max": float(s.max()),
        "range": float(s.max() - s.min()),
        "median": float(s.median()),
        "q1": q1,
        "q3": q3,
        "iqr": float(q3 - q1),
        "mean": float(s.mean()),
    }


def median_ci_width(low: pd.Series, high: pd.Series) -> float:
    """Median 95% confidence-interval width in percentage points (M7)."""
    lo = pd.to_numeric(low, errors="coerce")
    hi = pd.to_numeric(high, errors="coerce")
    widths = (hi - lo).dropna()
    if widths.empty:
        raise ValueError("no usable confidence intervals")
    return float(widths.median())


def top_bottom(
    df: pd.DataFrame, value_col: str, n: int = 10
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Top-n and bottom-n rows by value_col (M6). Ties broken by name."""
    ordered = df.sort_values([value_col, "locationname"], ascending=[False, True])
    bottom = df.sort_values([value_col, "locationname"], ascending=[True, True])
    return ordered.head(n).copy(), bottom.head(n).copy()
