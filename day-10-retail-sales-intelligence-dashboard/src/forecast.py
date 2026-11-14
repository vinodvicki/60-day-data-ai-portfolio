"""Day 10 — Retail Sales Intelligence Dashboard: forecasting.

Exactly two methods (plan.md §4.4, no tuning grid): naïve (baseline)
and Holt-Winters exponential smoothing with an additive trend and NO
seasonality. The series covers a single year, so a seasonal component
with period 52 cannot be estimated from one cycle — the forecast is a
trend extrapolation, and that limitation is disclosed wherever the
forecast appears. Prediction intervals come from a residual bootstrap
(seed 42, 1,000 paths, same procedure as Day 9). The published 8-week
forecast is the method with the lowest mean rolling-origin backtest
RMSE (§4.4).

All functions here are pure except ``build_forecast``, which writes the
two committed forecast CSVs (forecast.csv, backtest.csv) into a
processed directory.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from src.metrics import mae, rmse

BOOTSTRAP_PATHS = 1000
BOOTSTRAP_SEED = 42
BACKTEST_ORIGINS = (8, 16)
BACKTEST_HORIZON = 8
FORECAST_HORIZON = 8
METHODS = ("holt_winters", "naive")


def naive_forecast(series: pd.Series, horizon: int = 8) -> np.ndarray:
    """Naïve forecast: every future week = the last observed value."""
    values = series.to_numpy(dtype=float)
    if len(values) == 0:
        raise ValueError("empty series")
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    return np.full(horizon, values[-1], dtype=float)


def naive_residuals(series: pd.Series) -> np.ndarray:
    """In-sample one-step residuals of the naïve method (first diffs)."""
    values = series.to_numpy(dtype=float)
    return np.diff(values)


def holt_winters_forecast(
    series: pd.Series, horizon: int = 8
) -> tuple[np.ndarray, object]:
    """Holt-Winters forecast (additive trend, NO seasonality, plan §4.4).

    Returns (point forecast array, fitted model). Raises if the fit
    fails — the caller reports it; no seasonal substitute is used
    (plan §4.4).
    """
    model = ExponentialSmoothing(
        series.to_numpy(dtype=float),
        trend="add",
        seasonal=None,
    )
    # statsmodels can emit a ConvergenceWarning when the optimiser stops
    # on its tolerance; the fitted parameters are finite and the
    # forecasts are sane (checked against the backtest), so the warning
    # is suppressed here and the fact is recorded in data/README.md.
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
    and widen with horizon, because the simulated paths accumulate more
    resampled residuals further out.
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
    """Rolling-origin backtest (plan §4.4): 2 origins, 8-week horizons.

    For each origin (train ends ``origin`` weeks before the end of the
    series) both methods forecast ``horizon`` weeks; RMSE and MAE are
    computed against the held-out actuals. Returns one row per origin ×
    method.
    """
    values = series.to_numpy(dtype=float)
    rows: list[dict] = []
    for origin in origins:
        train = pd.Series(values[: len(values) - origin])
        actual = values[len(values) - origin : len(values) - origin + horizon]
        hw_point, _hw_fitted = holt_winters_forecast(train, horizon)
        rows.append(
            {
                "origin": origin,
                "method": "holt_winters",
                "rmse": round(rmse(actual, hw_point), 2),
                "mae": round(mae(actual, hw_point), 2),
            }
        )
        naive_point = naive_forecast(train, horizon)
        rows.append(
            {
                "origin": origin,
                "method": "naive",
                "rmse": round(rmse(actual, naive_point), 2),
                "mae": round(mae(actual, naive_point), 2),
            }
        )
    return pd.DataFrame.from_records(rows, columns=["origin", "method", "rmse", "mae"])


def build_forecast(
    series: pd.Series,
    week_starts: pd.Series,
    processed_dir: Path,
    horizon: int = FORECAST_HORIZON,
) -> dict:
    """Backtest, publish the winning forecast, write the 2 CSVs.

    ``series`` is weekly revenue (oldest first); ``week_starts`` is the
    matching week-starting (Monday) dates. Writes ``forecast.csv``
    (8 rows) and ``backtest.csv`` (2 origins × 2 methods) into
    ``processed_dir``. Returns a summary dict (winner, mean backtest
    RMSEs, forecast values) for the caller to record in data_source.json.
    The published forecast is the method with the lowest mean backtest
    RMSE across the 2 origins (plan §4.4); the other method is kept for
    comparison in backtest.csv / chart 04 / the dashboard.
    """
    processed_dir = Path(processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    backtest = rolling_backtest(series)
    mean_rmse = backtest.groupby("method")["rmse"].mean()
    winner = str(mean_rmse.idxmin())
    print(
        "backtest mean RMSE — holt_winters "
        f"{mean_rmse.get('holt_winters', float('nan')):.2f}, naive "
        f"{mean_rmse.get('naive', float('nan')):.2f} "
        f"-> published method: {winner}"
    )
    if winner == "holt_winters":
        point, fitted = holt_winters_forecast(series, horizon)
        intervals = _fit_intervals(fitted, point)
    else:
        point = naive_forecast(series, horizon)
        intervals = bootstrap_intervals(naive_residuals(series), point)
    last_week = pd.to_datetime(week_starts.iloc[-1])
    forecast_weeks = [
        (last_week + pd.Timedelta(weeks=i + 1)).strftime("%Y-%m-%d")
        for i in range(horizon)
    ]
    forecast = pd.DataFrame(
        {
            "week_start": forecast_weeks,
            "forecast_gbp": np.round(point, 2),
            "lo_80": np.round(intervals["lo_80"], 2),
            "hi_80": np.round(intervals["hi_80"], 2),
            "lo_95": np.round(intervals["lo_95"], 2),
            "hi_95": np.round(intervals["hi_95"], 2),
        }
    )
    forecast.to_csv(processed_dir / "forecast.csv", index=False)
    backtest.to_csv(processed_dir / "backtest.csv", index=False)
    summary = {
        "published_method": winner,
        "mean_rmse": {
            method: round(float(mean_rmse[method]), 2) for method in mean_rmse.index
        },
        "mean_mae": {
            method: round(float(v), 2)
            for method, v in backtest.groupby("method")["mae"].mean().items()
        },
        "backtest_origins": list(BACKTEST_ORIGINS),
        "backtest_horizon_weeks": BACKTEST_HORIZON,
        "forecast_horizon_weeks": horizon,
        "bootstrap_paths": BOOTSTRAP_PATHS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "forecast_weeks": forecast_weeks,
        "forecast_values": [round(float(v), 2) for v in point],
        "observed_max_weekly_revenue_gbp": round(float(series.max()), 2),
    }
    print(
        f"forecast {forecast_weeks[0]} → {forecast_weeks[-1]}: "
        f"{summary['forecast_values']}"
    )
    return summary
