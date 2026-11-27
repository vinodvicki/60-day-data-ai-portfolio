"""Day 20 Inflation & Cost of Living Dashboard: pure analysis functions.

No I/O here — every function takes a pandas Series (monthly, DatetimeIndex)
or plain numbers and returns a Series or a float, so the tests can exercise
them on a small seeded fixture without touching the FRED downloads.

Metric definitions (research_brief.md §2, frozen):
- YoY inflation = CPI(t) / CPI(t-12) - 1, in %.
- MoM inflation = CPI(t) / CPI(t-1) - 1, in %.
- Cumulative change since a base date = CPI(t) / CPI(base) - 1.
- Real hourly earnings = nominal earnings / CPI * 100 (1982-84 dollars).
- Purchasing power of $1 = 100 / CPI.
- Basket cost: a fixed $100 basket at the base date costs
  100 * CPI(t) / CPI(base) in month t (fixed-basket illustration).
- CAGR = (end / start) ** (1 / years) - 1.
- Annualised volatility = std of monthly log changes * sqrt(12).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def yoy(series: pd.Series) -> pd.Series:
    """Year-on-year percentage change (12-month lag), in percent."""
    return (series / series.shift(12) - 1.0) * 100.0


def mom(series: pd.Series) -> pd.Series:
    """Month-on-month percentage change (1-month lag), in percent."""
    return (series / series.shift(1) - 1.0) * 100.0


def cumulative_since(series: pd.Series, base: pd.Timestamp) -> pd.Series:
    """Cumulative percentage change since the base month, in percent.

    The base month itself is 0.0. Months before the base are NaN.
    """
    base_value = float(series.loc[base])
    out = (series / base_value - 1.0) * 100.0
    out.loc[out.index < base] = np.nan
    return out


def real_earnings(nominal: pd.Series, cpi: pd.Series) -> pd.Series:
    """Inflation-adjusted hourly earnings in 1982-84 dollars."""
    return nominal / cpi * 100.0


def indexed(series: pd.Series, base: pd.Timestamp) -> pd.Series:
    """Rebase a series so the base month equals 100."""
    base_value = float(series.loc[base])
    return series / base_value * 100.0


def basket_cost(
    cpi: pd.Series, base: pd.Timestamp, base_cost: float = 100.0
) -> pd.Series:
    """Cost in each month of the fixed basket that cost `base_cost` at base."""
    base_value = float(cpi.loc[base])
    return cpi / base_value * base_cost


def purchasing_power(cpi: pd.Series) -> pd.Series:
    """What $1 (1982-84 dollars) is worth in each month, in dollars."""
    return 100.0 / cpi


def cagr(start_value: float, end_value: float, years: float) -> float:
    """Compound annual growth rate between two values `years` apart."""
    if start_value <= 0.0 or end_value <= 0.0 or years <= 0.0:
        raise ValueError("cagr needs positive values and a positive span")
    return float((end_value / start_value) ** (1.0 / years) - 1.0)


def annualised_vol(log_returns: pd.Series) -> float:
    """Annualised volatility of monthly log returns, in percent."""
    return float(log_returns.std(ddof=1)) * float(np.sqrt(12.0)) * 100.0


def log_returns(series: pd.Series) -> pd.Series:
    """Monthly log returns of a price/index series, in percent."""
    return np.log(series / series.shift(1)) * 100.0


def summarise_series(
    series: pd.Series, base: pd.Timestamp, label: str
) -> dict[str, float | str]:
    """One row of summary statistics for a series over the joint window.

    Window is the series from `base` to its last observation. Returns the
    latest value/date, YoY change, cumulative change since base, CAGR and
    annualised volatility of monthly log changes.
    """
    window = series.loc[base:]
    latest = float(window.iloc[-1])
    first = float(window.iloc[0])
    n_months = len(window)
    years = (n_months - 1) / 12.0
    # Latest YoY uses the last non-missing value: the BLS series has no
    # October 2025 observation, so the Oct 2026 YoY is undefined.
    yoy_values = yoy(window).dropna()
    yoy_latest = float(yoy_values.iloc[-1])
    cum = (latest / first - 1.0) * 100.0
    vol = annualised_vol(log_returns(window))
    return {
        "series": label,
        "latest_date": str(window.index[-1].date()),
        "latest_value": latest,
        "yoy_pct": yoy_latest,
        "cumulative_since_base_pct": float(cum),
        "cagr_pct": cagr(first, latest, years) * 100.0,
        "annualised_vol_pct": vol,
        "n_months": float(n_months),
    }
