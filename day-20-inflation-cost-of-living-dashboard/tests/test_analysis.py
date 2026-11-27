"""Tests for Day 20 analysis functions — formulas vs. hand-computed values.

All expectations are computed by hand from small synthetic series (never
from the functions under test), so a formula bug cannot hide behind the
function itself.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.analysis import (
    annualised_vol,
    basket_cost,
    cagr,
    cumulative_since,
    indexed,
    log_returns,
    mom,
    purchasing_power,
    real_earnings,
    summarise_series,
    yoy,
)


def _series(values: list[float], start: str = "2024-01-01") -> pd.Series:
    index = pd.date_range(start, periods=len(values), freq="MS")
    return pd.Series(values, index=index)


def test_yoy_uses_12_month_lag() -> None:
    # 13 months of 100, then 110: YoY at month 13 is +10%.
    s = _series([100.0] * 12 + [110.0])
    out = yoy(s)
    assert out.iloc[:12].isna().all()
    assert out.iloc[12] == pytest.approx(10.0)


def test_yoy_negative() -> None:
    s = _series([200.0] * 12 + [180.0])
    assert yoy(s).iloc[12] == pytest.approx(-10.0)


def test_mom_uses_1_month_lag() -> None:
    s = _series([100.0, 102.0, 102.0])
    out = mom(s)
    assert np.isnan(out.iloc[0])
    assert out.iloc[1] == pytest.approx(2.0)
    assert out.iloc[2] == pytest.approx(0.0)


def test_cumulative_since_base() -> None:
    s = _series([100.0, 110.0, 121.0])
    base = pd.Timestamp("2024-01-01")
    out = cumulative_since(s, base)
    assert out.iloc[0] == pytest.approx(0.0)
    assert out.iloc[1] == pytest.approx(10.0)
    assert out.iloc[2] == pytest.approx(21.0)


def test_cumulative_since_before_base_is_nan() -> None:
    s = _series([90.0, 100.0, 110.0])
    base = pd.Timestamp("2024-02-01")
    out = cumulative_since(s, base)
    assert np.isnan(out.iloc[0])
    assert out.iloc[1] == pytest.approx(0.0)
    assert out.iloc[2] == pytest.approx(10.0)


def test_real_earnings_deflates_by_cpi() -> None:
    # $20/hr against CPI 200 -> $10 in 1982-84 dollars.
    nominal = _series([20.0, 22.0])
    cpi = _series([200.0, 220.0])
    out = real_earnings(nominal, cpi)
    assert out.iloc[0] == pytest.approx(10.0)
    assert out.iloc[1] == pytest.approx(10.0)


def test_indexed_rebases_to_100() -> None:
    s = _series([50.0, 75.0, 100.0])
    out = indexed(s, pd.Timestamp("2024-01-01"))
    assert out.iloc[0] == pytest.approx(100.0)
    assert out.iloc[1] == pytest.approx(150.0)
    assert out.iloc[2] == pytest.approx(200.0)


def test_basket_cost_scales_with_cpi() -> None:
    cpi = _series([200.0, 300.0])
    out = basket_cost(cpi, pd.Timestamp("2024-01-01"), 100.0)
    assert out.iloc[0] == pytest.approx(100.0)
    assert out.iloc[1] == pytest.approx(150.0)


def test_purchasing_power_falls_as_cpi_rises() -> None:
    cpi = _series([100.0, 200.0, 400.0])
    out = purchasing_power(cpi)
    assert out.iloc[0] == pytest.approx(1.0)
    assert out.iloc[1] == pytest.approx(0.5)
    assert out.iloc[2] == pytest.approx(0.25)


def test_cagr_doubling_in_10_years() -> None:
    # Doubling in 10 years is 2**(1/10)-1 = 7.18%/yr.
    assert cagr(100.0, 200.0, 10.0) == pytest.approx(0.071773, abs=1e-6)


def test_cagr_rejects_non_positive() -> None:
    with pytest.raises(ValueError):
        cagr(0.0, 100.0, 5.0)
    with pytest.raises(ValueError):
        cagr(100.0, 100.0, 0.0)


def test_log_returns_and_vol() -> None:
    s = _series([100.0, 110.0, 121.0])
    lr = log_returns(s)
    assert np.isnan(lr.iloc[0])
    assert lr.iloc[1] == pytest.approx(np.log(1.1) * 100.0)
    # Constant 10%/mo log returns have zero volatility.
    assert annualised_vol(lr) == pytest.approx(0.0)


def test_summarise_series_uses_last_valid_yoy() -> None:
    # 14 months: YoY defined only at months 13-14; last valid is month 14.
    values = [100.0] * 12 + [104.0, 108.0]
    s = _series(values)
    row = summarise_series(s, pd.Timestamp("2024-01-01"), "Test")
    assert row["latest_value"] == pytest.approx(108.0)
    assert row["yoy_pct"] == pytest.approx(8.0)
    assert row["cumulative_since_base_pct"] == pytest.approx(8.0)
    assert row["n_months"] == 14.0


def test_summarise_series_skips_missing_yoy() -> None:
    # 14 months; month 2 is missing, so the YoY at the last month (which
    # needs month 2) is undefined — the summary must fall back to the
    # last valid YoY instead of reporting NaN.
    values = [100.0] * 12 + [104.0, 108.0]
    s = _series(values)
    s.iloc[1] = np.nan  # month 2 missing -> YoY at month 14 undefined
    row = summarise_series(s, pd.Timestamp("2024-01-01"), "Test")
    # Last valid YoY is at month 13: 104 / 100 - 1 = 4%.
    assert row["yoy_pct"] == pytest.approx(4.0)
    assert row["latest_value"] == pytest.approx(108.0)
