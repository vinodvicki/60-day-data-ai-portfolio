"""Pure RFM functions for Day 12 — Customer Segmentation Engine.

No I/O, no network. Definitions (plan §4.1): snapshot date =
max(InvoiceDate) + 1 day; Recency = snapshot − most recent InvoiceDate
(days); Frequency = distinct InvoiceNo per customer; Monetary =
Σ(Quantity × UnitPrice) in GBP. Scores are percentile-rank based
(1–5), R inverted, ties sharing a score; RFM code = R·100 + F·10 + M,
RFM score = R + F + M (range 3–15). Scores are relative to this
customer base, not absolute.
"""

import numpy as np
import pandas as pd


def line_revenue(quantity, unit_price) -> float:
    """Line value in GBP: Quantity × UnitPrice."""
    return float(quantity) * float(unit_price)


def compute_rfm(df: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    """Per-customer R/F/M from a cleaned transaction frame.

    ``df`` carries snake_case columns (``customer_id``, ``invoice_no``,
    ``invoice_date``, ``line_revenue``). Rows with a missing CustomerID
    are excluded — they cannot be attributed to a customer (plan §3.2
    rule 8). Returns one row per customer: ``customer_id``,
    ``recency_days``, ``frequency``, ``monetary_gbp``.
    """
    work = df[df["customer_id"].notna()].copy()
    work["customer_id"] = work["customer_id"].astype(int)
    grouped = work.groupby("customer_id")
    last = grouped["invoice_date"].max()
    # Calendar-date difference (plan §4.1: range 1–374 days on this
    # window — a customer last seen 2011-12-09 has Recency 1, not 0).
    # Using raw Timedelta.days would floor intraday times to 0.
    recency = (snapshot.normalize() - last.dt.normalize()).dt.days.astype(int)
    rfm = pd.DataFrame(
        {
            "customer_id": last.index,
            "recency_days": recency,
            "frequency": grouped["invoice_no"].nunique(),
            "monetary_gbp": grouped["line_revenue"].sum(),
        }
    ).reset_index(drop=True)
    return rfm.sort_values("customer_id").reset_index(drop=True)


def _score_series(values: pd.Series, invert: bool) -> pd.Series:
    """Percentile-rank 1–5 score; ties share a score; R inverted."""
    pct = values.rank(pct=True, method="average")
    raw = np.ceil(pct.to_numpy(dtype=float) * 5)
    if invert:
        raw = 6 - raw
    return pd.Series(np.clip(raw, 1, 5).astype(int), index=values.index)


def score_rfm(rfm: pd.DataFrame) -> pd.DataFrame:
    """Add R/F/M quintile scores, ``rfm_code`` and ``rfm_score``."""
    out = rfm.copy()
    out["r_score"] = _score_series(out["recency_days"], invert=True)
    out["f_score"] = _score_series(out["frequency"], invert=False)
    out["m_score"] = _score_series(out["monetary_gbp"], invert=False)
    out["rfm_code"] = (
        out["r_score"] * 100 + out["f_score"] * 10 + out["m_score"]
    ).astype(int)
    out["rfm_score"] = (out["r_score"] + out["f_score"] + out["m_score"]).astype(int)
    return out
