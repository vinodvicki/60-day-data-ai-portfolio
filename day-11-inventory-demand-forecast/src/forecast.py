"""Forecast methods, metrics and backtest for Day 11.

Exactly six methods (plan §4.3), all forecasts clipped at >= 0:
naïve, seasonal naïve (falls back to naïve where y(t-52) is unavailable
— on a 52-week series that is both backtest origins, so its WAPE is
reported as n/a and it never contends for winner selection), 4-week
moving average, Croston-SBA (alpha 0.1), Holt ETS (additive trend, no
seasonality) and HistGradientBoosting on lag features. Pure functions;
no I/O except the builders, no network.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from statsmodels.tsa.holtwinters import ExponentialSmoothing

METHODS = [
    "naive",
    "seasonal_naive",
    "moving_average",
    "croston_sba",
    "holt",
    "gradient_boosting",
]

# Simplicity order for the 0.5 pp tie-break (plan §4.3). Seasonal naïve
# never contends.
SIMPLICITY_ORDER = [
    "naive",
    "moving_average",
    "croston_sba",
    "holt",
    "gradient_boosting",
]

DISPLAY_NAMES = {
    "naive": "Naïve",
    "seasonal_naive": "Seasonal naïve",
    "moving_average": "4-wk moving avg",
    "croston_sba": "Croston-SBA",
    "holt": "Holt ETS",
    "gradient_boosting": "HistGradientBoosting",
}

PRIMARY_ORIGIN = 48
SUPPLEMENTARY_ORIGIN = 29


def wape(y_true, y_pred) -> float:
    """Weighted absolute percentage error: sum|actual-forecast|/sum actual."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = float(np.abs(y_true).sum())
    if denom == 0:
        return float("nan")
    return float(np.abs(y_true - y_pred).sum() / denom)


def mae(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def bias(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.mean(y_pred - y_true))


def _values(series: pd.Series) -> np.ndarray:
    return np.asarray(series.to_numpy(dtype=float), dtype=float).ravel()


def _week_starts(series: pd.Series) -> pd.DatetimeIndex:
    idx = series.index
    if isinstance(idx, pd.DatetimeIndex):
        return idx
    start = pd.Timestamp("2010-12-06")
    return pd.date_range(start, periods=len(series), freq="7D")


def naive_forecast(series: pd.Series, horizon: int = 4) -> np.ndarray:
    vals = _values(series)
    return np.full(horizon, vals[-1], dtype=float)


def seasonal_naive_available(series: pd.Series, horizon: int = 4) -> bool:
    """True only if y(t-52) exists for every horizon week."""
    return len(series) >= 52 + horizon - 1 and len(series) >= 52


def seasonal_naive_forecast(series: pd.Series, horizon: int = 4) -> np.ndarray:
    """y(t-52); falls back to naïve where the lag-52 value does not exist."""
    vals = _values(series)
    if seasonal_naive_available(series, horizon):
        start = len(vals) - 52
        return np.asarray(np.maximum(vals[start : start + horizon], 0.0), dtype=float)
    return naive_forecast(series, horizon=horizon)


def moving_average_forecast(
    series: pd.Series, horizon: int = 4, window: int = 4
) -> np.ndarray:
    vals = _values(series)
    return np.full(horizon, float(np.mean(vals[-window:])), dtype=float)


def croston_sba_forecast(
    series: pd.Series, horizon: int = 4, alpha: float = 0.1
) -> np.ndarray:
    """Croston with the Syntetos–Boylan bias correction (× (1 − α/2))."""
    vals = _values(series)
    nonzero_idx = np.flatnonzero(vals > 0)
    if len(nonzero_idx) == 0:
        return np.zeros(horizon, dtype=float)
    z = float(vals[nonzero_idx[0]])
    p = float(nonzero_idx[0] + 1)
    last_nonzero = int(nonzero_idx[0])
    for t in range(1, len(vals)):
        if vals[t] > 0:
            interval = t - last_nonzero
            z = alpha * float(vals[t]) + (1 - alpha) * z
            p = alpha * interval + (1 - alpha) * p
            last_nonzero = t
    rate = z / p if p > 0 else 0.0
    return np.full(horizon, max(rate * (1 - alpha / 2), 0.0), dtype=float)


def holt_forecast(series: pd.Series, horizon: int = 4) -> tuple[np.ndarray, object]:
    """Holt ETS: additive trend, no seasonal component (plan §4.3)."""
    vals = _values(series)
    try:
        model = ExponentialSmoothing(
            vals, trend="add", seasonal=None, initialization_method="estimated"
        ).fit(optimized=True)
        fc = np.asarray(model.forecast(horizon), dtype=float)
        return np.maximum(fc, 0.0), model
    except Exception:  # noqa: BLE001 - any Holt failure falls back to naive
        return naive_forecast(series, horizon=horizon), None


def _gb_features(values: np.ndarray, dates: pd.DatetimeIndex, t: int) -> list:
    """Features for week t: lags 1/2/4, rolling-4 mean, week-of-year,
    month, December indicator."""
    date = dates[t]
    return [
        float(values[t - 1]),
        float(values[t - 2]),
        float(values[t - 4]),
        float(np.mean(values[t - 4 : t])),
        float(date.isocalendar().week),
        float(date.month),
        1.0 if date.month == 12 else 0.0,
    ]


def gradient_boosting_forecast(series: pd.Series, horizon: int = 4) -> np.ndarray:
    """HistGradientBoosting on lag features; recursive multi-step forecast."""
    vals = _values(series)
    dates = _week_starts(series)
    if len(vals) < 8:
        return moving_average_forecast(series, horizon=horizon)
    rows, targets = [], []
    for t in range(4, len(vals)):
        rows.append(_gb_features(vals, dates, t))
        targets.append(float(vals[t]))
    model = HistGradientBoostingRegressor(random_state=42)
    model.fit(np.array(rows), np.array(targets))
    extended = list(vals)
    future_dates = pd.date_range(
        dates[-1] + pd.Timedelta(days=7), periods=horizon, freq="7D"
    )
    all_dates = list(dates) + list(future_dates)
    out = []
    for step in range(horizon):
        t = len(extended)
        feats = _gb_features(np.array(extended), pd.DatetimeIndex(all_dates), t)
        pred = float(model.predict([feats])[0])
        pred = max(pred, 0.0)
        out.append(pred)
        extended.append(pred)
    return np.array(out, dtype=float)


FORECASTERS = {
    "naive": naive_forecast,
    "seasonal_naive": seasonal_naive_forecast,
    "moving_average": moving_average_forecast,
    "croston_sba": croston_sba_forecast,
    "holt": lambda s, horizon=4: holt_forecast(s, horizon=horizon)[0],
    "gradient_boosting": gradient_boosting_forecast,
}


def backtest(series: pd.Series, origins: tuple = ((48, 4), (29, 4))) -> pd.DataFrame:
    """Per-origin × method metrics. ``origin`` is the training-week count.

    Seasonal naïve metrics are NaN where y(t-52) is unavailable.
    """
    rows = []
    vals = _values(series)
    for train_n, horizon in origins:
        train = series.iloc[:train_n]
        actual = vals[train_n : train_n + horizon]
        if len(actual) < horizon:
            continue
        for method in METHODS:
            if method == "seasonal_naive" and not seasonal_naive_available(
                train, horizon
            ):
                rows.append(
                    {
                        "origin": train_n,
                        "method": method,
                        "wape": float("nan"),
                        "mae": float("nan"),
                        "rmse": float("nan"),
                        "bias": float("nan"),
                    }
                )
                continue
            fc = FORECASTERS[method](train, horizon=horizon)
            rows.append(
                {
                    "origin": train_n,
                    "method": method,
                    "wape": wape(actual, fc),
                    "mae": mae(actual, fc),
                    "rmse": rmse(actual, fc),
                    "bias": bias(actual, fc),
                }
            )
    return pd.DataFrame(rows)


def _volume_weighted_wape(frame: pd.DataFrame) -> float:
    if "actual_total" in frame.columns:
        weights = frame["actual_total"].to_numpy(dtype=float)
        wapes = frame["wape"].to_numpy(dtype=float)
        mask = ~np.isnan(wapes) & (weights > 0)
        if mask.sum() == 0:
            return float("nan")
        return float(np.sum(wapes[mask] * weights[mask]) / np.sum(weights[mask]))
    return float(frame["wape"].mean())


def select_cluster_winner(backtest_df: pd.DataFrame, cluster: str) -> str:
    """Per-cluster winner (plan §4.3): lowest volume-weighted primary-
    holdout WAPE, with a 0.5 pp simplicity tie-break.

    ``backtest_df`` carries one row per origin × method × series with
    ``cluster`` and ``actual_total`` columns when available. Seasonal
    naïve never contends.
    """
    frame = backtest_df.copy()
    if "cluster" in frame.columns:
        frame = frame[frame["cluster"] == cluster]
    if len(frame) == 0:
        return "n/a"
    primary = (
        PRIMARY_ORIGIN
        if PRIMARY_ORIGIN in set(frame["origin"])
        else frame["origin"].max()
    )
    frame = frame[frame["origin"] == primary]
    frame = frame[frame["method"] != "seasonal_naive"]
    frame = frame[~frame["wape"].isna()]
    if len(frame) == 0:
        return "n/a"
    grouped = frame.groupby("method").apply(_volume_weighted_wape, include_groups=False)
    best = float(grouped.min())
    contenders = [m for m in grouped.index if grouped[m] <= best + 0.005]
    for method in SIMPLICITY_ORDER:
        if method in contenders:
            return method
    return str(grouped.idxmin())


def aggregate_winner(backtest_df: pd.DataFrame) -> str:
    """Winner for the aggregate series (same rule, no cluster)."""
    frame = backtest_df.copy()
    if "stock_code" in frame.columns:
        frame = frame[frame["stock_code"] == "AGGREGATE"]
    if len(frame) == 0:
        return "n/a"
    primary = (
        PRIMARY_ORIGIN
        if PRIMARY_ORIGIN in set(frame["origin"])
        else frame["origin"].max()
    )
    frame = frame[frame["origin"] == primary]
    frame = frame[frame["method"] != "seasonal_naive"]
    frame = frame[~frame["wape"].isna()]
    if len(frame) == 0:
        return "n/a"
    grouped = frame.groupby("method")["wape"].mean()
    best = float(grouped.min())
    contenders = [m for m in grouped.index if grouped[m] <= best + 0.005]
    for method in SIMPLICITY_ORDER:
        if method in contenders:
            return method
    return str(grouped.idxmin())


def build_forecast(
    weekly: pd.DataFrame,
    sku_summary: pd.DataFrame,
    winners: dict,
    agg_winner: str,
    aggregate: pd.Series | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Published 4-week forecast + full backtest table.

    ``weekly`` is long format (week_start, stock_code, units) for the
    top-20 SKUs; ``aggregate`` is the 52-week aggregate series (index
    week_start). Returns (forecast_df, backtest_df) where backtest_df
    has the committed columns plus ``stock_code``, ``cluster`` and
    ``actual_total`` for winner selection.
    """
    pivot = weekly.pivot_table(
        index="week_start", columns="stock_code", values="units", aggfunc="sum"
    ).fillna(0)
    pivot.index = pd.to_datetime(pivot.index)
    pivot = pivot.sort_index()
    cluster_of = dict(zip(sku_summary["stock_code"], sku_summary["cluster"]))
    forecast_weeks = pd.date_range(
        pivot.index[-1] + pd.Timedelta(days=7), periods=4, freq="7D"
    )
    forecast_rows, backtest_rows = [], []
    series_map = {code: pivot[code] for code in pivot.columns}
    if aggregate is not None:
        agg = aggregate.copy()
        agg.index = pd.to_datetime(agg.index)
        series_map["AGGREGATE"] = agg.sort_index()
    for code, series in series_map.items():
        cluster = cluster_of.get(code, "aggregate")
        winner = agg_winner if code == "AGGREGATE" else winners.get(cluster, "n/a")
        bt = backtest(series)
        bt["stock_code"] = code
        bt["cluster"] = cluster
        actual_primary = _values(series)[PRIMARY_ORIGIN : PRIMARY_ORIGIN + 4]
        bt["actual_total"] = float(np.sum(actual_primary))
        backtest_rows.append(bt)
        if winner in FORECASTERS:
            fc = FORECASTERS[winner](series, horizon=4)
        else:
            fc = naive_forecast(series, horizon=4)
        for week, value in zip(forecast_weeks, fc):
            forecast_rows.append(
                {
                    "week_start": week.strftime("%Y-%m-%d"),
                    "stock_code": code,
                    "description": (
                        "AGGREGATE — all cleaned SKUs"
                        if code == "AGGREGATE"
                        else str(
                            sku_summary.loc[
                                sku_summary["stock_code"] == code, "description"
                            ].iloc[0]
                        )
                    ),
                    "cluster": cluster,
                    "winning_method": winner,
                    "forecast_units": float(max(value, 0.0)),
                }
            )
    forecast_df = pd.DataFrame(forecast_rows)
    backtest_df = pd.concat(backtest_rows, ignore_index=True)
    return forecast_df, backtest_df
