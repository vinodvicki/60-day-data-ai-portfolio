"""Tests for the Day 18 pipeline: cleaning, aggregation, joins.

All tests run on small synthetic frames — no network, no raw files.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import data_pipeline as dp


def _prices_frame() -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=12, freq="MS")
    return pd.DataFrame(
        {
            "date": dates,
            "commodity": ["maize"] * 12,
            "price_usd_per_t": [
                100.0,
                110.0,
                105.0,
                120.0,
                115.0,
                130.0,
                125.0,
                140.0,
                135.0,
                150.0,
                145.0,
                160.0,
            ],
        }
    )


def test_log_returns_are_log_differences() -> None:
    frame = _prices_frame()
    frame["log_return"] = np.log(
        frame["price_usd_per_t"] / frame["price_usd_per_t"].shift(1)
    )
    assert pd.isna(frame["log_return"].iloc[0])
    assert float(frame["log_return"].iloc[1]) == pytest.approx(np.log(110.0 / 100.0))
    assert float(frame["log_return"].iloc[11]) == pytest.approx(np.log(160.0 / 145.0))


def test_annual_summary_excludes_partial_year() -> None:
    """2026 (Jan-Sep only) must not appear in annual_summary (plan §3.2)."""
    monthly = _prices_frame()
    monthly["log_return"] = np.log(
        monthly["price_usd_per_t"] / monthly["price_usd_per_t"].shift(1)
    )
    extra = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=9, freq="MS"),
            "commodity": ["maize"] * 9,
            "price_usd_per_t": [170.0] * 9,
            "log_return": [0.01] * 9,
        }
    )
    combined = pd.concat([monthly, extra], ignore_index=True)
    summary = dp.build_annual_summary(combined)
    assert 2026 not in set(summary["year"])
    assert set(summary["year"]) == {2020}
    assert len(summary) == 1
    assert float(summary.iloc[0]["annual_mean_price"]) == pytest.approx(1535 / 12)
    assert float(summary.iloc[0]["annual_max_price"]) == pytest.approx(160.0)
    assert float(summary.iloc[0]["annual_min_price"]) == pytest.approx(100.0)


def test_annual_summary_yoy() -> None:
    rows: list[dict[str, object]] = []
    for year, base in ((2020, 100.0), (2021, 110.0)):
        for m in range(1, 13):
            rows.append(
                {
                    "date": pd.Timestamp(year, m, 1),
                    "commodity": "maize",
                    "price_usd_per_t": base,
                    "log_return": 0.0,
                }
            )
    monthly = pd.DataFrame(rows)
    summary = dp.build_annual_summary(monthly)
    assert len(summary) == 2
    assert pd.isna(summary.iloc[0]["yoy_pct_change"])
    assert float(summary.iloc[1]["yoy_pct_change"]) == pytest.approx(10.0)


def test_weather_growing_season_filter() -> None:
    daily = {
        "daily": {
            "time": [
                "2020-01-15",
                "2020-04-15",
                "2020-07-15",
                "2020-10-15",
                "2021-06-15",
            ],
            "temperature_2m_mean": [0.0, 15.0, 25.0, 10.0, 20.0],
            "temperature_2m_max": [5.0, 20.0, 30.0, 15.0, 25.0],
            "precipitation_sum": [1.0, 2.0, 3.0, 4.0, 5.0],
        }
    }
    features = dp.build_weather_features(daily)
    assert set(features["year"]) == {2020, 2021}
    row_2020 = features[features["year"] == 2020].iloc[0]
    # Only Apr + Jul count (growing season Apr-Sep).
    assert float(row_2020["gs_temp_mean_c"]) == pytest.approx(20.0)
    assert float(row_2020["gs_precip_total_mm"]) == pytest.approx(5.0)


def test_weather_negative_precip_raises() -> None:
    daily = {
        "daily": {
            "time": ["2020-05-15"],
            "temperature_2m_mean": [20.0],
            "temperature_2m_max": [25.0],
            "precipitation_sum": [-1.0],
        }
    }
    with pytest.raises(ValueError, match="negative precipitation"):
        dp.build_weather_features(daily)


def test_dsci_aggregation_growing_season_only() -> None:
    frame = pd.DataFrame(
        {
            "Name": ["Iowa"] * 4,
            "MapDate": ["20200107", "20200407", "20200707", "20201229"],
            "DSCI": [10, 100, 200, 300],
        }
    )
    annual = dp.aggregate_state_annual(frame, "iowa")
    assert len(annual) == 1
    assert int(annual.iloc[0]["year"]) == 2020
    # Only Apr + Jul weeks count.
    assert float(annual.iloc[0]["gs_dsci_mean_ia"]) == pytest.approx(150.0)


def test_dsci_out_of_range_raises() -> None:
    frame = pd.DataFrame({"Name": ["Iowa"], "MapDate": ["20200407"], "DSCI": [501]})
    with pytest.raises(ValueError, match="DSCI outside 0-500"):
        dp.aggregate_state_annual(frame, "iowa")


def test_annual_join_row_count_and_no_nan() -> None:
    annual_summary = pd.DataFrame(
        [
            {
                "year": y,
                "commodity": c,
                "annual_mean_price": 100.0 + y,
                "annual_max_price": 110.0,
                "annual_min_price": 90.0,
                "annual_volatility": 0.05,
                "yoy_pct_change": 1.0,
            }
            for y in range(2000, 2026)
            for c in ("maize", "wheat", "soybeans")
        ]
    )
    weather = {
        state: pd.DataFrame(
            {
                "year": range(2000, 2026),
                "gs_temp_mean_c": [20.0] * 26,
                "gs_precip_total_mm": [600.0] * 26,
            }
        )
        for state in ("iowa", "illinois")
    }
    dsci = {
        state: pd.DataFrame(
            {
                "year": range(2000, 2026),
                f"gs_dsci_mean_{abbr}": [50.0] * 26,
            }
        )
        for state, abbr in (("iowa", "ia"), ("illinois", "il"))
    }
    join = dp.build_annual_join(annual_summary, weather, dsci)
    assert len(join) == 26
    assert not join.isna().any().any()
    assert float(join.iloc[0]["gs_precip_anomaly_mm"]) == pytest.approx(0.0)
    assert float(join.iloc[0]["gs_dsci_mean"]) == pytest.approx(50.0)


def test_fred_series_ids() -> None:
    assert dp.SERIES == {
        "maize": "PMAIZMTUSDM",
        "wheat": "PWHEAMTUSDM",
        "soybeans": "PSOYBUSDM",
    }
    assert "PCORNUSDM" not in dp.SERIES.values()
