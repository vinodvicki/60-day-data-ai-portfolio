"""Day 10 — Retail Sales Intelligence Dashboard: pure metric functions.

No I/O, no network. Every function here is unit-tested in
tests/test_pipeline.py. Definitions follow plan.md §4.1 (from
research_brief.md §2).

Conventions
-----------
- Money is in GBP; ``revenue`` is a sum of ``Quantity × UnitPrice``.
- ``month_over_month`` skips partial months: a ``None`` in the input
  marks a partial month, and the growth for that month (and for the
  month after it, whose base is partial) is ``None``.
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


def line_revenue(quantity, unit_price) -> float:
    """Revenue of one transaction line: Quantity × UnitPrice (GBP)."""
    return float(quantity) * float(unit_price)


def aov(revenue: float, orders: int) -> float:
    """Average order value = total revenue / orders."""
    if orders <= 0:
        raise ValueError("orders must be positive")
    return float(revenue) / float(orders)


def repeat_rate(frequencies) -> float:
    """Share of customers with ≥ 2 orders (0–1)."""
    freq = np.asarray(list(frequencies), dtype=float).ravel()
    if len(freq) == 0:
        raise ValueError("empty input")
    return float(np.mean(freq >= 2))


def revenue_share(part: float, total: float) -> float:
    """Revenue share of a part of the total, in percent (0–100)."""
    if total <= 0:
        raise ValueError("total must be positive")
    return float(part) / float(total) * 100.0


def rmse(y_true, y_pred) -> float:
    """Root mean squared error, in the same units as the input (GBP)."""
    y, p = _as_arrays(y_true, y_pred)
    return float(np.sqrt(np.mean((y - p) ** 2)))


def mae(y_true, y_pred) -> float:
    """Mean absolute error, in the same units as the input (GBP)."""
    y, p = _as_arrays(y_true, y_pred)
    return float(np.mean(np.abs(y - p)))


def month_over_month(values: list[float | None]) -> list[float | None]:
    """Month-over-month growth in percent, skipping partial months.

    ``values`` is monthly revenue oldest-first; a ``None`` entry marks
    a partial month (Dec 2011, plan §3.2 rule 9). The growth for a
    partial month is ``None``, and the growth for the month after a
    partial month is also ``None`` (its base is partial). The first
    month has no predecessor, so its growth is ``None``.
    """
    out: list[float | None] = []
    for i, value in enumerate(values):
        if value is None or i == 0:
            out.append(None)
            continue
        prev = values[i - 1]
        if prev is None or prev == 0:
            out.append(None)
            continue
        out.append(float(value) / float(prev) * 100.0 - 100.0)
    return out
