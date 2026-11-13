"""Day 9 — Healthcare Resource Demand Forecast: pure metric functions.

No I/O, no network. Every function here is unit-tested in
tests/test_pipeline.py. Definitions follow plan.md §4.3–4.4 (from
research_brief.md §2).

Conventions
-----------
- ``y_true`` / ``y_pred`` are weekly Combined respiratory ED shares in
  percentage points (e.g. 2.3 means 2.3% of all ED visits).
- ``mape`` is reported with the plan §4.4 caveat: it inflates when the
  actual % is small (Combined % can sit near 1–2% in summer), so RMSE
  and MAE are always reported alongside it.
- ``interval_coverage`` is the share of actuals inside the interval;
  the 80% interval's target is ≈ 0.80.
"""

from __future__ import annotations

import numpy as np


def _as_arrays(y_true, y_pred) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y_true, dtype=float).ravel()
    p = np.asarray(y_pred, dtype=float).ravel()
    if y.shape != p.shape:
        raise ValueError("y_true and y_pred must have the same length")
    if len(y) == 0:
        raise ValueError("empty input")
    return y, p


def rmse(y_true, y_pred) -> float:
    """Root mean squared error, in the same units as the input (pp)."""
    y, p = _as_arrays(y_true, y_pred)
    return float(np.sqrt(np.mean((y - p) ** 2)))


def mae(y_true, y_pred) -> float:
    """Mean absolute error, in the same units as the input (pp)."""
    y, p = _as_arrays(y_true, y_pred)
    return float(np.mean(np.abs(y - p)))


def mape(y_true, y_pred) -> float:
    """Mean absolute percentage error, in percent.

    Actual values of exactly 0 are excluded (a 0% week would make the
    percentage error undefined); if every actual is 0 the result is NaN.
    See the module docstring for why MAPE is never reported alone.
    """
    y, p = _as_arrays(y_true, y_pred)
    mask = y != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs(y[mask] - p[mask]) / np.abs(y[mask])) * 100.0)


def interval_coverage(y_true, lo, hi) -> float:
    """Share of actuals inside [lo, hi] (inclusive), 0–1."""
    y = np.asarray(y_true, dtype=float).ravel()
    lo = np.asarray(lo, dtype=float).ravel()
    hi = np.asarray(hi, dtype=float).ravel()
    if not (len(y) == len(lo) == len(hi)):
        raise ValueError("y_true, lo and hi must have the same length")
    if len(y) == 0:
        raise ValueError("empty input")
    return float(np.mean((y >= lo) & (y <= hi)))


def seasonal_naive_predict(train, horizon: int, period: int = 52) -> np.ndarray:
    """Seasonal-naïve forecast: week *t* = the value *period* weeks earlier.

    ``train`` is the training series (array-like, oldest first);
    ``horizon`` is the number of weeks to forecast. For horizons longer
    than one period the pattern cycles (not needed here: horizon ≤ 8).
    """
    values = np.asarray(train, dtype=float).ravel()
    if len(values) < period:
        raise ValueError(
            f"need at least {period} training weeks for seasonal naïve, "
            f"got {len(values)}"
        )
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    idx = [len(values) - period + (h % period) for h in range(horizon)]
    return values[idx]
