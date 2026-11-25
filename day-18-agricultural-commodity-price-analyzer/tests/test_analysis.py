"""Tests for the Day 18 analysis: seasonality, drawdown, shocks, forecast.

All tests run on small synthetic frames — no processed files needed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import analysis as an


def _monthly_frame() -> pd.DataFrame:
    """Two full years of flat-then-rising prices for one commodity."""
    dates = pd.date_range("2020-01-01", periods=24, freq="MS")
    prices = [100.0 + i for i in range(24)]
    frame = pd.DataFrame(
        {"date": dates, "commodity": ["maize"] * 24, "price_usd_per_t": prices}
    )
    frame["log_return"] = np.log(
        frame["price_usd_per_t"] / frame["price_usd_per_t"].shift(1)
    )
    return frame


def test_seasonal_indices_sum_to_twelve() -> None:
    frame = _monthly_frame()
    seasonality = an.seasonal_indices(frame)
    full = seasonality[seasonality["window"] == "full"]
    assert len(full) == 12
    assert float(full["seasonal_index"].sum()) == pytest.approx(12.0, abs=1e-9)
    assert set(full["n_months"]) == {2}


def test_seasonal_peaks() -> None:
    frame = _monthly_frame()
    seasonality = an.seasonal_indices(frame)
    peaks = an.seasonal_peaks(seasonality)
    assert peaks["maize"]["peak_month"] == 12
    assert peaks["maize"]["trough_month"] == 1
    assert peaks["maize"]["amplitude"] == pytest.approx(
        peaks["maize"]["peak_index"] - peaks["maize"]["trough_index"]
    )


def test_max_drawdown_known_series() -> None:
    prices = pd.Series(
        [100.0, 120.0, 90.0, 110.0],
        index=pd.date_range("2020-01-01", periods=4, freq="MS"),
    )
    result = an.max_drawdown(prices)
    assert result["peak_date"] == "2020-02-01"
    assert result["trough_date"] == "2020-03-01"
    assert float(result["drawdown_pct"]) == pytest.approx(-25.0)


def test_max_drawdown_no_drawdown() -> None:
    prices = pd.Series(
        [100.0, 110.0, 120.0],
        index=pd.date_range("2020-01-01", periods=3, freq="MS"),
    )
    result = an.max_drawdown(prices)
    assert float(result["drawdown_pct"]) == pytest.approx(0.0)


def test_detect_shocks_flags_large_move() -> None:
    rng = np.random.default_rng(7)
    dates = pd.date_range("2020-01-01", periods=36, freq="MS")
    returns = rng.normal(0, 0.02, 35).tolist()
    returns.append(0.50)
    prices = [100.0]
    for r in returns[1:]:
        prices.append(prices[-1] * np.exp(float(r)))
    frame = pd.DataFrame(
        {"date": dates, "commodity": ["maize"] * 36, "price_usd_per_t": prices}
    )
    frame["log_return"] = np.log(
        frame["price_usd_per_t"] / frame["price_usd_per_t"].shift(1)
    )
    shocks = an.detect_shocks(frame)
    # The seeded noise trips the rule once more (2022-03); the planted
    # 0.50 move must be flagged and must be the largest shock.
    assert pd.Timestamp("2022-12-01") in set(shocks["date"])
    assert len(shocks) <= 3
    biggest = shocks.loc[shocks["log_return"].abs().idxmax()]
    assert biggest["date"] == pd.Timestamp("2022-12-01")
    assert bool(biggest["top10"])


def test_detect_shocks_ignores_small_moves() -> None:
    rng = np.random.default_rng(11)
    dates = pd.date_range("2020-01-01", periods=36, freq="MS")
    returns = rng.normal(0, 0.02, 36).tolist()
    prices = [100.0]
    for r in returns[1:]:
        prices.append(prices[-1] * np.exp(float(r)))
    frame = pd.DataFrame(
        {"date": dates, "commodity": ["maize"] * 36, "price_usd_per_t": prices}
    )
    frame["log_return"] = np.log(
        frame["price_usd_per_t"] / frame["price_usd_per_t"].shift(1)
    )
    shocks = an.detect_shocks(frame)
    # With no move above ~0.06 in the window, at most the odd tail month
    # can trip the 2-sigma rule — and every flagged month must satisfy it.
    assert len(shocks) <= 2
    for _, row in shocks.iterrows():
        assert abs(float(row["log_return"])) >= 2 * float(row["rolling_24m_std"])


def test_rolling_volatility_window() -> None:
    frame = _monthly_frame()
    vol = an.rolling_volatility(frame)
    assert len(vol) == 24
    # The first 12 rows are NaN: 11 need the 12-month window, and the
    # 12th still lacks a full window because log_return[0] is NaN.
    assert vol["rolling_vol_12m_pct"].iloc[:12].isna().all()
    assert not pd.isna(vol["rolling_vol_12m_pct"].iloc[12])


def test_join_correlations_perfect() -> None:
    years = list(range(2000, 2010))
    join = pd.DataFrame(
        {
            "year": years,
            "maize_yoy_pct_change": [float(y) for y in years],
            "wheat_yoy_pct_change": [float(-y) for y in years],
            "soybeans_yoy_pct_change": [0.0] * 10,
            "gs_temp_mean_c": [float(y) for y in years],
            "gs_precip_total_mm": [float(-y) for y in years],
            "gs_dsci_mean": [float(y) for y in years],
        }
    )
    corr = an.join_correlations(join)
    assert len(corr) == 9
    maize_temp = corr[
        (corr["commodity"] == "maize") & (corr["driver"] == "gs_temp_mean_c")
    ].iloc[0]
    assert float(maize_temp["pearson_r"]) == pytest.approx(1.0)
    assert float(maize_temp["p_value"]) == pytest.approx(0.0, abs=1e-9)
    maize_precip = corr[
        (corr["commodity"] == "maize") & (corr["driver"] == "gs_precip_total_mm")
    ].iloc[0]
    assert float(maize_precip["pearson_r"]) == pytest.approx(-1.0)


def test_maize_regression_recovers_coefficients() -> None:
    rng = np.random.default_rng(42)
    n = 40
    dsci = rng.uniform(0, 200, n)
    precip = rng.uniform(-200, 200, n)
    y = 5.0 + 0.05 * dsci - 0.02 * precip + rng.normal(0, 0.5, n)
    join = pd.DataFrame(
        {
            "year": range(2000, 2000 + n),
            "maize_yoy_pct_change": y,
            "gs_dsci_mean": dsci,
            "gs_precip_anomaly_mm": precip,
        }
    )
    reg = an.maize_regression(join)
    assert len(reg) == 1
    assert float(reg.iloc[0]["coef_dsci"]) == pytest.approx(0.05, abs=0.01)
    assert float(reg.iloc[0]["coef_precip_anomaly"]) == pytest.approx(-0.02, abs=0.01)
    assert float(reg.iloc[0]["r_squared"]) > 0.9
    assert int(reg.iloc[0]["n"]) == n


def test_cross_correlations_identical_series() -> None:
    dates = pd.date_range("2020-01-01", periods=30, freq="MS")
    returns = np.linspace(-0.05, 0.05, 30)
    rows: list[dict[str, object]] = []
    for commodity in ("maize", "wheat", "soybeans"):
        prices = [100.0]
        for r in returns[1:]:
            prices.append(prices[-1] * np.exp(float(r)))
        for date, price, ret in zip(dates, prices, [np.nan, *returns[1:]]):
            rows.append(
                {
                    "date": date,
                    "commodity": commodity,
                    "price_usd_per_t": price,
                    "log_return": ret,
                }
            )
    frame = pd.DataFrame(rows)
    cross = an.cross_correlations(frame)
    assert len(cross) == 6
    full = cross[cross["window"] == "full"]
    assert (full["pearson_r"] > 0.999).all()


def test_maize_forecast_shape_and_interval() -> None:
    dates = pd.date_range("2020-01-01", periods=84, freq="MS")
    t = np.arange(84)
    prices = 200.0 + 0.5 * t + 10.0 * np.sin(2 * np.pi * t / 12)
    frame = pd.DataFrame(
        {"date": dates, "commodity": ["maize"] * 84, "price_usd_per_t": prices}
    )
    frame["log_return"] = np.log(
        frame["price_usd_per_t"] / frame["price_usd_per_t"].shift(1)
    )
    table, backtest = an.maize_forecast(frame)
    assert len(table) == 12
    assert (table["lo_80"] <= table["forecast"]).all()
    assert (table["forecast"] <= table["hi_80"]).all()
    assert backtest["rmse_hw_mean"] > 0
    assert backtest["rmse_seasonal_naive_mean"] > 0
    assert len(backtest["origins"]) == 3


def test_seasonal_naive_repeats_last_year() -> None:
    series = pd.Series(
        [100.0 + i for i in range(24)],
        index=pd.date_range("2020-01-01", periods=24, freq="MS"),
    )
    naive = an._seasonal_naive_forecast(series, 12)
    assert len(naive) == 12
    assert float(naive.iloc[0]) == pytest.approx(112.0)
    assert float(naive.iloc[11]) == pytest.approx(123.0)
