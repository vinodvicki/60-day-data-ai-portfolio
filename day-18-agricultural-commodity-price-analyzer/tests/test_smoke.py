"""Smoke tests for Day 18: processed files, row counts, charts, provenance.

These tests read the committed processed files — they verify the build
output, not synthetic frames.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
CHARTS = ROOT / "outputs" / "charts"


def test_processed_files_exist_with_expected_rows() -> None:
    expected = {
        "monthly_prices.csv": 1251,
        "annual_summary.csv": 102,
        "seasonality.csv": 72,
        "annual_join.csv": 26,
        "correlations.csv": 9,
        "regression_maize.csv": 1,
        "forecast_maize.csv": 12,
        "county_shock_2012.csv": 201,
        "cross_correlations.csv": 6,
    }
    for name, rows in expected.items():
        frame = pd.read_csv(PROCESSED / name)
        assert len(frame) == rows, f"{name}: {len(frame)} rows, expected {rows}"


def test_monthly_prices_complete() -> None:
    monthly = pd.read_csv(PROCESSED / "monthly_prices.csv", parse_dates=["date"])
    assert set(monthly["commodity"]) == {"maize", "wheat", "soybeans"}
    for commodity, group in monthly.groupby("commodity"):
        assert len(group) == 417
        assert group["price_usd_per_t"].min() > 0
        expected = pd.date_range("1992-01-01", "2026-09-01", freq="MS")
        assert (
            group.sort_values("date")["date"]
            .reset_index(drop=True)
            .equals(pd.Series(expected, name="date"))
        )


def test_annual_join_has_no_nan_and_no_2026() -> None:
    join = pd.read_csv(PROCESSED / "annual_join.csv")
    assert not join.isna().any().any()
    assert 2026 not in set(join["year"])
    assert set(join["year"]) == set(range(2000, 2026))


def test_annual_summary_excludes_2026() -> None:
    annual = pd.read_csv(PROCESSED / "annual_summary.csv")
    assert 2026 not in set(annual["year"])


def test_charts_exist_and_are_pngs() -> None:
    for name in (
        "01_price_levels.png",
        "02_seasonality.png",
        "03_volatility_shocks.png",
        "04_county_map.png",
    ):
        path = CHARTS / name
        assert path.exists(), f"missing chart {name}"
        assert path.stat().st_size > 10_000, f"{name} suspiciously small"
        assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_data_source_is_live_not_synthetic() -> None:
    record = json.loads((PROCESSED / "data_source.json").read_text())
    assert record["synthetic"] is False
    assert record["sources"]["prices"]["series"] == {
        "maize": "PMAIZMTUSDM",
        "wheat": "PWHEAMTUSDM",
        "soybeans": "PSOYBUSDM",
    }
    assert "backtest" in record
    assert (
        record["backtest"]["rmse_hw_mean"]
        < record["backtest"]["rmse_seasonal_naive_mean"]
    )


def test_forecast_interval_is_ordered() -> None:
    forecast = pd.read_csv(PROCESSED / "forecast_maize.csv", parse_dates=["date"])
    assert (forecast["lo_80"] <= forecast["forecast"]).all()
    assert (forecast["forecast"] <= forecast["hi_80"]).all()
    assert forecast["date"].min() == pd.Timestamp("2026-10-01")
    assert forecast["date"].max() == pd.Timestamp("2027-09-01")


def test_county_shock_2012_top_county() -> None:
    county = pd.read_csv(PROCESSED / "county_shock_2012.csv")
    top = county.sort_values("gs_d2plus_pct_2012", ascending=False).iloc[0]
    assert str(top["county"]).startswith("Massac")
    assert float(top["gs_d2plus_pct_2012"]) > 70.0


def test_seasonality_indices_sum_to_twelve() -> None:
    seasonality = pd.read_csv(PROCESSED / "seasonality.csv")
    for (commodity, window), group in seasonality.groupby(["commodity", "window"]):
        # Equal month counts would sum to exactly 12; the full window has
        # 35 Jan-Sep months vs 34 Oct-Dec months, so allow a small gap.
        assert abs(float(group["seasonal_index"].sum()) - 12.0) < 0.01, (
            commodity,
            window,
        )


def test_readmes_exist_and_are_not_placeholders() -> None:
    readme = (ROOT / "README.md").read_text()
    assert len(readme) > 2000
    assert "PLACEHOLDER" not in readme
    data_readme = (ROOT / "data" / "README.md").read_text()
    assert len(data_readme) > 500
    assert "PLACEHOLDER" not in data_readme
