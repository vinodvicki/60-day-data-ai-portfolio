"""Day 18 Agricultural Commodity Price Analyzer: analysis.

Pure functions over the processed price / annual-join tables: seasonal
indices, drawdowns, shock detection, weather/drought correlations, the
maize OLS regression, the Holt-Winters maize forecast with a rolling
backtest, and cross-commodity log-return correlations. No network, no raw
reads — the pipeline calls build_derived() with the base tables.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.holtwinters import ExponentialSmoothing

COMMODITIES = ("maize", "wheat", "soybeans")
DRIVERS = ("gs_temp_mean_c", "gs_precip_total_mm", "gs_dsci_mean")

# Named shock windows (plan §2.2): start month, end month, label.
SHOCK_WINDOWS = [
    ("2007-01", "2008-06", "2007-08 food-price crisis"),
    ("2012-06", "2012-12", "2012 US drought"),
    ("2020-02", "2020-05", "2020 COVID trough"),
    ("2022-02", "2022-06", "2022 Russia-Ukraine war spike"),
]

BACKTEST_ORIGINS = ("2023-09", "2024-09", "2025-09")
FORECAST_MONTHS = 12


# --- Seasonality ------------------------------------------------------------


def seasonal_indices(monthly: pd.DataFrame) -> pd.DataFrame:
    """Seasonal index per commodity per calendar month, two windows.

    Index = mean price in that month / overall mean price. Windows:
    'full' (1992-2026) and 'last10y' (2016-2025 full years). The index
    sums to 12 per commodity per window (up to rounding).
    """
    rows: list[dict[str, Any]] = []
    for window, frame in (
        ("full", monthly),
        ("last10y", monthly[monthly["date"].dt.year.between(2016, 2025)]),
    ):
        overall = frame.groupby("commodity")["price_usd_per_t"].mean()
        for (commodity, month), group in frame.groupby(
            ["commodity", frame["date"].dt.month]
        ):
            rows.append(
                {
                    "commodity": commodity,
                    "month": int(month),
                    "window": window,
                    "month_mean_price": float(group["price_usd_per_t"].mean()),
                    "seasonal_index": float(
                        group["price_usd_per_t"].mean() / overall[commodity]
                    ),
                    "n_months": len(group),
                }
            )
    out = pd.DataFrame(rows).sort_values(["commodity", "window", "month"])
    return out.reset_index(drop=True)


def seasonal_peaks(seasonality: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Peak / trough month and amplitude per commodity (full window)."""
    result: dict[str, dict[str, Any]] = {}
    full = seasonality[seasonality["window"] == "full"]
    for commodity, group in full.groupby("commodity"):
        peak = group.loc[group["seasonal_index"].idxmax()]
        trough = group.loc[group["seasonal_index"].idxmin()]
        result[commodity] = {
            "peak_month": int(peak["month"]),
            "peak_index": float(peak["seasonal_index"]),
            "trough_month": int(trough["month"]),
            "trough_index": float(trough["seasonal_index"]),
            "amplitude": float(
                group["seasonal_index"].max() - group["seasonal_index"].min()
            ),
        }
    return result


# --- Variability and shocks -------------------------------------------------


def max_drawdown(prices: pd.Series) -> dict[str, Any]:
    """Worst peak-to-trough drawdown of a monthly price series."""
    running_peak = prices.cummax()
    drawdown = prices / running_peak - 1.0
    trough_label = drawdown.idxmin()
    peak_label = prices.loc[:trough_label].idxmax()
    return {
        "peak_date": str(peak_label.date()),
        "trough_date": str(trough_label.date()),
        "drawdown_pct": float(drawdown.loc[trough_label] * 100),
    }


def rolling_volatility(monthly: pd.DataFrame) -> pd.DataFrame:
    """12-month rolling volatility (annualised %) of monthly log returns."""
    frames: list[pd.DataFrame] = []
    for commodity, group in monthly.groupby("commodity"):
        group = group.sort_values("date").copy()
        group["rolling_vol_12m_pct"] = (
            group["log_return"].rolling(12).std() * np.sqrt(12) * 100
        )
        frames.append(group[["date", "commodity", "rolling_vol_12m_pct"]])
    return pd.concat(frames, ignore_index=True)


def detect_shocks(monthly: pd.DataFrame) -> pd.DataFrame:
    """Shock months: |log return| >= 2x the rolling 24-month return std.

    Returns one row per shock month with the top-10 flag (largest
    |log return| across all three commodities).
    """
    rows: list[pd.DataFrame] = []
    for commodity, group in monthly.groupby("commodity"):
        group = group.sort_values("date").copy()
        rolling_std = group["log_return"].rolling(24).std()
        group["rolling_24m_std"] = rolling_std
        group["shock_flag"] = (group["log_return"].abs() >= 2 * rolling_std).fillna(
            False
        )
        rows.append(group)
    shocks = pd.concat(rows, ignore_index=True)
    shocks = shocks[shocks["shock_flag"]].copy()
    shocks = shocks.sort_values("log_return", key=lambda s: s.abs(), ascending=False)
    shocks["top10"] = [i < 10 for i in range(len(shocks))]
    shocks = shocks.sort_values(["commodity", "date"])
    return shocks[
        [
            "date",
            "commodity",
            "price_usd_per_t",
            "log_return",
            "rolling_24m_std",
            "shock_flag",
            "top10",
        ]
    ].reset_index(drop=True)


def named_window_changes(monthly: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Maize price change (%) over each named shock window (plan §2.2)."""
    maize = monthly[monthly["commodity"] == "maize"].set_index("date")
    result: dict[str, dict[str, float]] = {}
    for start, end, label in SHOCK_WINDOWS:
        start_price = float(maize.loc[pd.Timestamp(start), "price_usd_per_t"])
        end_price = float(maize.loc[pd.Timestamp(end), "price_usd_per_t"])
        result[label] = {
            "start_price": start_price,
            "end_price": end_price,
            "pct_change": (end_price / start_price - 1) * 100,
        }
    return result


# --- Weather / drought join -------------------------------------------------


def join_correlations(annual_join: pd.DataFrame) -> pd.DataFrame:
    """Pearson r + p-value of YoY price change vs each driver, per commodity."""
    rows: list[dict[str, Any]] = []
    for commodity in COMMODITIES:
        y = annual_join[f"{commodity}_yoy_pct_change"]
        for driver in DRIVERS:
            x = annual_join[driver]
            mask = y.notna() & x.notna()
            r, p = stats.pearsonr(x[mask], y[mask])
            rows.append(
                {
                    "commodity": commodity,
                    "driver": driver,
                    "pearson_r": float(r),
                    "p_value": float(p),
                    "n": int(mask.sum()),
                }
            )
    return pd.DataFrame(rows)


def maize_regression(annual_join: pd.DataFrame) -> pd.DataFrame:
    """OLS of maize YoY % change on growing-season DSCI + precip anomaly.

    statsmodels OLS so the p-values come from the same fit as the
    coefficients (plan §4.3, coder's choice recorded here).
    """
    import statsmodels.api as sm

    frame = annual_join.dropna(subset=["maize_yoy_pct_change"])
    y = frame["maize_yoy_pct_change"]
    x = frame[["gs_dsci_mean", "gs_precip_anomaly_mm"]]
    x = sm.add_constant(x)
    model = sm.OLS(y, x).fit()
    return pd.DataFrame(
        [
            {
                "intercept": float(model.params["const"]),
                "coef_dsci": float(model.params["gs_dsci_mean"]),
                "coef_precip_anomaly": float(model.params["gs_precip_anomaly_mm"]),
                "r_squared": float(model.rsquared),
                "p_dsci": float(model.pvalues["gs_dsci_mean"]),
                "p_precip": float(model.pvalues["gs_precip_anomaly_mm"]),
                "n": int(model.nobs),
            }
        ]
    )


def cross_correlations(monthly: pd.DataFrame) -> pd.DataFrame:
    """Pairwise Pearson r of monthly log returns, full window + last 10y."""
    pivoted = monthly.pivot(index="date", columns="commodity", values="log_return")
    rows: list[dict[str, Any]] = []
    pairs = [("maize", "wheat"), ("maize", "soybeans"), ("wheat", "soybeans")]
    windows = {
        "full": pivoted,
        "last10y": pivoted[pivoted.index >= "2016-10-01"],
    }
    for window, frame in windows.items():
        for a, b in pairs:
            sub = frame[[a, b]].dropna()
            r, p = stats.pearsonr(sub[a], sub[b])
            rows.append(
                {
                    "pair": f"{a}-{b}",
                    "window": window,
                    "pearson_r": float(r),
                    "p_value": float(p),
                    "n": len(sub),
                }
            )
    return pd.DataFrame(rows)


# --- Forecast ----------------------------------------------------------------


def _holt_winters_forecast(
    series: pd.Series, horizon: int, damped: bool = False
) -> pd.Series:
    """Holt-Winters (additive trend + additive seasonality, 12) forecast."""
    model = ExponentialSmoothing(
        series,
        trend="add",
        damped_trend=damped,
        seasonal="add",
        seasonal_periods=12,
    ).fit(optimized=True)
    return model.forecast(horizon)


def _seasonal_naive_forecast(series: pd.Series, horizon: int) -> pd.Series:
    """Seasonal naïve: the same month last year."""
    last_year = series.iloc[-12:]
    values = list(last_year.values)
    while len(values) < horizon:
        values.extend(values[:12])
    index = pd.date_range(
        series.index[-1] + pd.offsets.MonthBegin(1), periods=horizon, freq="MS"
    )
    return pd.Series(values[:horizon], index=index)


def maize_forecast(monthly: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """3-origin backtest + 12-month Holt-Winters forecast for maize.

    Returns (forecast table, backtest summary dict). The 80% interval is
    forecast +/- 1.2816 x the backtest residual std (36 residuals).
    """
    maize = monthly[monthly["commodity"] == "maize"].copy()
    maize = maize.sort_values("date")
    series = maize.set_index("date")["price_usd_per_t"]
    series.index = pd.DatetimeIndex(series.index)

    origins_rmse_hw: list[float] = []
    origins_rmse_naive: list[float] = []
    residuals: list[float] = []
    for origin in BACKTEST_ORIGINS:
        train = series.loc[:origin]
        actual = series.loc[
            pd.date_range(
                pd.Timestamp(origin) + pd.offsets.MonthBegin(1),
                periods=FORECAST_MONTHS,
                freq="MS",
            )
        ]
        try:
            forecast = _holt_winters_forecast(train, FORECAST_MONTHS)
        except (ValueError, np.linalg.LinAlgError):
            forecast = _holt_winters_forecast(train, FORECAST_MONTHS, damped=True)
        naive = _seasonal_naive_forecast(train, FORECAST_MONTHS)
        residuals.extend((actual - forecast).tolist())
        origins_rmse_hw.append(float(np.sqrt(np.mean((actual - forecast) ** 2))))
        origins_rmse_naive.append(float(np.sqrt(np.mean((actual - naive) ** 2))))

    try:
        full_forecast = _holt_winters_forecast(series, FORECAST_MONTHS)
    except (ValueError, np.linalg.LinAlgError):
        full_forecast = _holt_winters_forecast(series, FORECAST_MONTHS, damped=True)
    residual_std = float(np.std(residuals))
    forecast_index = pd.date_range("2026-10-01", periods=FORECAST_MONTHS, freq="MS")
    table = pd.DataFrame(
        {
            "date": forecast_index,
            "forecast": full_forecast.values,
            "lo_80": full_forecast.values - 1.2816 * residual_std,
            "hi_80": full_forecast.values + 1.2816 * residual_std,
        }
    )
    backtest = {
        "method": "Holt-Winters additive trend + additive seasonality (12)",
        "origins": list(BACKTEST_ORIGINS),
        "horizon_months": FORECAST_MONTHS,
        "rmse_hw_mean": float(np.mean(origins_rmse_hw)),
        "rmse_hw_by_origin": origins_rmse_hw,
        "rmse_seasonal_naive_mean": float(np.mean(origins_rmse_naive)),
        "rmse_seasonal_naive_by_origin": origins_rmse_naive,
        "residual_std": residual_std,
        "forecast_window": "2026-10 to 2027-09",
        "note": "Statistical extrapolation, not a market prediction.",
    }
    return table, backtest


# --- Orchestration ------------------------------------------------------------


def build_derived(
    processed_dir: Path,
    monthly: pd.DataFrame,
    annual_summary: pd.DataFrame,
    annual_join: pd.DataFrame,
) -> dict[str, Any]:
    """Build the six derived tables; write them; return the backtest dict."""
    seasonality = seasonal_indices(monthly)
    shocks = detect_shocks(monthly)
    correlations = join_correlations(annual_join)
    regression = maize_regression(annual_join)
    forecast_table, backtest = maize_forecast(monthly)
    cross = cross_correlations(monthly)

    seasonality.to_csv(processed_dir / "seasonality.csv", index=False)
    shocks.to_csv(processed_dir / "shocks.csv", index=False)
    correlations.to_csv(processed_dir / "correlations.csv", index=False)
    regression.to_csv(processed_dir / "regression_maize.csv", index=False)
    forecast_table.to_csv(processed_dir / "forecast_maize.csv", index=False)
    cross.to_csv(processed_dir / "cross_correlations.csv", index=False)
    return {"backtest": backtest}
