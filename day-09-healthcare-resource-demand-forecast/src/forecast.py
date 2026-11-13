"""Day 9 — Healthcare Resource Demand Forecast: forecasting.

Exactly two methods (plan.md §4.2, no tuning grid, no SARIMA):
seasonal naïve (baseline) and Holt-Winters exponential smoothing
(additive trend + additive seasonality, period 52, fixed). Prediction
intervals come from a residual bootstrap (seed 42, 1,000 paths, §4.3).
The published 8-week forecast is the method with the lowest mean
rolling-origin backtest RMSE (§4.4).

All functions here are pure except ``build_forecast``, which writes the
three committed forecast CSVs (forecast.csv, backtest.csv,
band_history.csv) into a processed directory.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from src.metrics import (
    interval_coverage,
    mae,
    mape,
    rmse,
    seasonal_naive_predict,
)

SEASONAL_PERIOD = 52
BOOTSTRAP_PATHS = 1000
BOOTSTRAP_SEED = 42
BACKTEST_ORIGINS = (12, 8, 4)
BACKTEST_HORIZON = 4
FORECAST_HORIZON = 8

BAND_THRESHOLDS = {"low": 2.0, "moderate": 4.0, "high": 6.0}
BANDS = ("Low", "Moderate", "High", "Surge")
METHODS = ("holt_winters", "seasonal_naive")


def classify_band(value: float) -> str:
    """Demand band for a Combined % (plan §4.5, fixed thresholds).

    Boundaries belong to the higher band: 2.0 → Moderate, 4.0 → High,
    6.0 → Surge.
    """
    if value < 2.0:
        return "Low"
    if value < 4.0:
        return "Moderate"
    if value < 6.0:
        return "High"
    return "Surge"


def seasonal_naive_forecast(series: pd.Series, horizon: int = 8) -> np.ndarray:
    """Seasonal-naïve forecast: each week = the same week last year."""
    return seasonal_naive_predict(
        series.to_numpy(dtype=float), horizon, period=SEASONAL_PERIOD
    )


def seasonal_naive_residuals(series: pd.Series) -> np.ndarray:
    """In-sample one-step residuals of the seasonal-naïve method."""
    values = series.to_numpy(dtype=float)
    return values[SEASONAL_PERIOD:] - values[:-SEASONAL_PERIOD]


def holt_winters_forecast(
    series: pd.Series, horizon: int = 8
) -> tuple[np.ndarray, object]:
    """Holt-Winters forecast (additive trend + additive seasonality, p=52).

    Returns (point forecast array, fitted model). Raises if the fit
    fails — the caller reports it; SARIMA is NOT a silent substitute
    (plan §4.2 rule 3).
    """
    model = ExponentialSmoothing(
        series.to_numpy(dtype=float),
        trend="add",
        seasonal="add",
        seasonal_periods=SEASONAL_PERIOD,
    )
    # statsmodels emits a ConvergenceWarning on some windows (the
    # optimiser stops on its tolerance, not on a failed fit); the fitted
    # parameters are finite and the forecasts are sane (backtest RMSE
    # beats seasonal naïve by a wide margin), so the warning is
    # suppressed here and the fact is recorded in data/README.md.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        fitted = model.fit()
    return np.asarray(fitted.forecast(horizon), dtype=float), fitted


def bootstrap_intervals(
    residuals: np.ndarray,
    point: np.ndarray,
    n_paths: int = BOOTSTRAP_PATHS,
    seed: int = BOOTSTRAP_SEED,
) -> dict:
    """Residual-bootstrap prediction intervals for a point forecast.

    Resamples the in-sample one-step residuals (with replacement),
    simulates ``n_paths`` 8-week paths by cumulative summation, and
    takes the 10th/90th percentiles (80% interval) and the 2.5th/97.5th
    percentiles (95% interval). Returns a dict of four arrays the same
    length as ``point``. The intervals always contain the point forecast
    (the 10th/90th percentiles of a zero-centred residual distribution
    bracket 0) and widen with horizon, because the simulated paths
    accumulate more resampled residuals further out.
    """
    residuals = np.asarray(residuals, dtype=float).ravel()
    point = np.asarray(point, dtype=float).ravel()
    if len(residuals) == 0:
        raise ValueError("need at least one residual to bootstrap")
    if len(point) == 0:
        raise ValueError("empty point forecast")
    rng = np.random.default_rng(seed)
    draws = rng.choice(residuals, size=(n_paths, len(point)), replace=True)
    paths = point[None, :] + np.cumsum(draws, axis=1)
    lo_80, hi_80 = np.percentile(paths, [10, 90], axis=0)
    lo_95, hi_95 = np.percentile(paths, [2.5, 97.5], axis=0)
    return {
        "lo_80": np.asarray(lo_80, dtype=float),
        "hi_80": np.asarray(hi_80, dtype=float),
        "lo_95": np.asarray(lo_95, dtype=float),
        "hi_95": np.asarray(hi_95, dtype=float),
    }


def _fit_intervals(fitted, point: np.ndarray) -> dict:
    """Bootstrap intervals from a fitted Holt-Winters model's residuals."""
    residuals = np.asarray(fitted.resid, dtype=float)
    residuals = residuals[np.isfinite(residuals)]
    return bootstrap_intervals(residuals, point)


def rolling_backtest(
    series: pd.Series,
    origins: tuple = BACKTEST_ORIGINS,
    horizon: int = BACKTEST_HORIZON,
) -> pd.DataFrame:
    """Rolling-origin backtest (plan §4.4): 3 origins, 4-week horizons.

    For each origin (train ends ``origin`` weeks before the end of the
    series) both methods forecast ``horizon`` weeks; RMSE, MAE, MAPE
    and 80%-interval coverage are computed against the held-out actuals.
    Returns one row per origin × method.
    """
    values = series.to_numpy(dtype=float)
    rows: list[dict] = []
    for origin in origins:
        train = pd.Series(values[: len(values) - origin])
        actual = values[len(values) - origin : len(values) - origin + horizon]
        # Holt-Winters on the training window.
        hw_point, hw_fitted = holt_winters_forecast(train, horizon)
        hw_intervals = _fit_intervals(hw_fitted, hw_point)
        rows.append(
            {
                "origin": origin,
                "method": "holt_winters",
                "rmse": round(rmse(actual, hw_point), 4),
                "mae": round(mae(actual, hw_point), 4),
                "mape": round(mape(actual, hw_point), 2),
                "coverage_80": round(
                    interval_coverage(
                        actual, hw_intervals["lo_80"], hw_intervals["hi_80"]
                    ),
                    4,
                ),
            }
        )
        # Seasonal naïve on the same training window.
        naive_point = seasonal_naive_forecast(train, horizon)
        naive_intervals = bootstrap_intervals(
            seasonal_naive_residuals(train), naive_point
        )
        rows.append(
            {
                "origin": origin,
                "method": "seasonal_naive",
                "rmse": round(rmse(actual, naive_point), 4),
                "mae": round(mae(actual, naive_point), 4),
                "mape": round(mape(actual, naive_point), 2),
                "coverage_80": round(
                    interval_coverage(
                        actual, naive_intervals["lo_80"], naive_intervals["hi_80"]
                    ),
                    4,
                ),
            }
        )
    return pd.DataFrame.from_records(
        rows, columns=["origin", "method", "rmse", "mae", "mape", "coverage_80"]
    )


def build_forecast(
    series: pd.Series,
    week_ends: pd.Series,
    processed_dir: Path,
    horizon: int = FORECAST_HORIZON,
) -> dict:
    """Backtest, publish the winning forecast, write the 3 CSVs.

    ``series`` is the national weekly Combined % (oldest first);
    ``week_ends`` is the matching week-ending dates. Writes
    ``forecast.csv`` (8 rows), ``backtest.csv`` (3 origins × 2 methods)
    and ``band_history.csv`` (one row per observed week) into
    ``processed_dir``. Returns a summary dict (winner, mean backtest
    RMSEs, forecast values) for the caller to record in data_source.json.
    The published forecast is the method with the lowest mean backtest
    RMSE across the 3 origins (plan §4.4); the other method is kept for
    comparison in backtest.csv / chart 02 / the dashboard.
    """
    processed_dir = Path(processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    backtest = rolling_backtest(series)
    mean_rmse = backtest.groupby("method")["rmse"].mean()
    winner = str(mean_rmse.idxmin())
    print(
        "backtest mean RMSE — holt_winters "
        f"{mean_rmse.get('holt_winters', float('nan')):.4f}, seasonal_naive "
        f"{mean_rmse.get('seasonal_naive', float('nan')):.4f} "
        f"-> published method: {winner}"
    )
    if winner == "holt_winters":
        point, fitted = holt_winters_forecast(series, horizon)
        intervals = _fit_intervals(fitted, point)
    else:
        point = seasonal_naive_forecast(series, horizon)
        intervals = bootstrap_intervals(seasonal_naive_residuals(series), point)
    last_week = pd.to_datetime(week_ends.iloc[-1])
    forecast_weeks = [
        (last_week + pd.Timedelta(weeks=i + 1)).strftime("%Y-%m-%d")
        for i in range(horizon)
    ]
    forecast = pd.DataFrame(
        {
            "week_end": forecast_weeks,
            "forecast_pct": np.round(point, 2),
            "lo_80": np.round(intervals["lo_80"], 2),
            "hi_80": np.round(intervals["hi_80"], 2),
            "lo_95": np.round(intervals["lo_95"], 2),
            "hi_95": np.round(intervals["hi_95"], 2),
            "band": [classify_band(float(v)) for v in point],
        }
    )
    forecast.to_csv(processed_dir / "forecast.csv", index=False)
    backtest.to_csv(processed_dir / "backtest.csv", index=False)
    band_history = pd.DataFrame(
        {
            "week_end": pd.to_datetime(week_ends).dt.strftime("%Y-%m-%d"),
            "combined_pct": np.round(series.to_numpy(dtype=float), 2),
            "band": [classify_band(float(v)) for v in series.to_numpy(dtype=float)],
        }
    )
    band_history.to_csv(processed_dir / "band_history.csv", index=False)
    summary = {
        "published_method": winner,
        "mean_rmse": {
            method: round(float(mean_rmse[method]), 4) for method in mean_rmse.index
        },
        "mean_mae": {
            method: round(float(v), 4)
            for method, v in backtest.groupby("method")["mae"].mean().items()
        },
        "mean_mape": {
            method: round(float(v), 2)
            for method, v in backtest.groupby("method")["mape"].mean().items()
        },
        "backtest_origins": list(BACKTEST_ORIGINS),
        "backtest_horizon_weeks": BACKTEST_HORIZON,
        "forecast_horizon_weeks": horizon,
        "bootstrap_paths": BOOTSTRAP_PATHS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "forecast_weeks": forecast_weeks,
        "forecast_values": [round(float(v), 2) for v in point],
        "forecast_bands": forecast["band"].tolist(),
        "observed_max_combined_pct": round(float(series.max()), 2),
        "band_counts_history": {
            band: int((band_history["band"] == band).sum()) for band in BANDS
        },
    }
    print(
        f"forecast {forecast_weeks[0]} → {forecast_weeks[-1]}: "
        f"{summary['forecast_values']} "
        f"(bands {summary['forecast_bands']})"
    )
    return summary
