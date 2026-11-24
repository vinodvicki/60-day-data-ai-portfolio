"""Tests for the Day 17 analysis: detrend, correlations, AR(1), ranking.

All tests run on small synthetic frames — no processed files needed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import analysis as an


def _annual_frame() -> pd.DataFrame:
    years = list(range(2000, 2010))
    # Perfect linear trend: yield = 8 + 0.1 * (year - 2000), plus a known residual.
    resid = [0.5, -0.5, 0.3, -0.3, 0.0, 0.2, -0.2, 0.1, -0.1, 0.0]
    yields = [8.0 + 0.1 * (y - 2000) + r for y, r in zip(years, resid)]
    dsci = [50.0, 150.0, 60.0, 140.0, 55.0, 70.0, 130.0, 65.0, 120.0, 60.0]
    return pd.DataFrame(
        {
            "year": years,
            "yield_t_per_ha": yields,
            "gs_dsci_mean": dsci,
            "gs_precip_anomaly_mm": [-d for d in dsci],
            "gs_precip_anomaly_pct": [-d / 5 for d in dsci],
            "jul_precip_anomaly_mm": [-d / 2 for d in dsci],
        }
    )


def test_detrend_yield_residuals_sum_to_zero() -> None:
    frame = an.detrend_yield(_annual_frame())
    assert "yield_resid_t_per_ha" in frame.columns
    assert "yield_trend_fit_t_per_ha" in frame.columns
    assert float(frame["yield_resid_t_per_ha"].sum()) == pytest.approx(0.0, abs=1e-9)
    assert float(frame.attrs["trend_slope_t_per_ha_per_year"]) == pytest.approx(
        0.1, abs=0.02
    )


def test_compute_correlations_signs() -> None:
    frame = an.detrend_yield(_annual_frame())
    corr = an.compute_correlations(frame)
    assert len(corr) == 3
    assert set(corr["variable"]) == {
        "gs_dsci_mean",
        "gs_precip_anomaly_mm",
        "jul_precip_anomaly_mm",
    }
    dsci_row = corr.loc[corr["variable"] == "gs_dsci_mean"].iloc[0]
    # Residuals were built anti-correlated with DSCI: r must be negative.
    assert float(dsci_row["pearson_r"]) < -0.5
    assert 0.0 <= float(dsci_row["p_value"]) <= 1.0
    assert float(dsci_row["r_squared"]) == pytest.approx(
        float(dsci_row["pearson_r"]) ** 2
    )
    assert float(dsci_row["ols_slope"]) < 0
    precip_row = corr.loc[corr["variable"] == "gs_precip_anomaly_mm"].iloc[0]
    # Precipitation anomaly is the mirror of DSCI here: positive r.
    assert float(precip_row["pearson_r"]) > 0.5


def test_worst_drought_years_ordering() -> None:
    frame = an.detrend_yield(_annual_frame())
    worst = an.worst_drought_years(frame, 3)
    assert worst["year"].tolist() == [2001, 2003, 2006]
    assert worst["gs_dsci_mean"].is_monotonic_decreasing


def test_worst_county_in_year() -> None:
    county_year = pd.DataFrame(
        {
            "fips": ["19001", "19003", "17001"],
            "county": ["Adair County", "Adams County", "Adams County"],
            "state": ["IA", "IA", "IL"],
            "year": [2012, 2012, 2012],
            "gs_d2plus_pct": [80.0, 40.0, 60.0],
            "gs_dsci": [300.0, 150.0, 220.0],
        }
    )
    worst = an.worst_county_in_year(county_year, 2012)
    assert worst["county"] == "Adair County"
    assert worst["state"] == "IA"
    assert float(str(worst["gs_d2plus_pct"])) == pytest.approx(80.0)


def test_fit_ar1_on_known_series() -> None:
    # y_t = 10 + 0.5 * y_{t-1} exactly.
    values = [100.0]
    for _ in range(9):
        values.append(10 + 0.5 * values[-1])
    series = pd.Series(values)
    intercept, slope, resid_std = an.fit_ar1(series)
    assert intercept == pytest.approx(10.0, abs=1e-6)
    assert slope == pytest.approx(0.5, abs=1e-6)
    assert resid_std == pytest.approx(0.0, abs=1e-6)


def test_ar1_forecast_table_shape() -> None:
    frame = pd.DataFrame(
        {
            "year": list(range(2000, 2026)),
            "gs_dsci_mean": [50.0 + (i % 5) * 10.0 for i in range(26)],
        }
    )
    table = an.ar1_forecast_table(frame)
    assert len(table) == 2
    assert table["year"].tolist() == [2025, 2026]
    assert np.isnan(table.loc[table["year"] == 2026, "actual"].iloc[0])
    assert not np.isnan(table.loc[table["year"] == 2026, "lower"].iloc[0])
    assert not np.isnan(table.loc[table["year"] == 2025, "ar1_abs_error"].iloc[0])


def test_top_counties_ordering() -> None:
    summary = pd.DataFrame(
        {
            "fips": ["19001", "19003", "17001"],
            "county": ["A", "B", "C"],
            "state": ["IA", "IA", "IL"],
            "mean_d2plus_pct": [5.0, 25.0, 15.0],
            "worst_year": [2012, 2012, 2012],
            "worst_year_d2plus_pct": [50.0, 90.0, 70.0],
            "mean_dsci": [100.0, 200.0, 150.0],
        }
    )
    top = an.top_counties(summary, 2)
    assert top["fips"].tolist() == ["19003", "17001"]
