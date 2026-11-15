"""Demand-pattern clustering for Day 11 — Inventory Demand Forecast.

Syntetos–Boylan (SBC) classification per SKU from ADI and CV², plus a
KMeans k = 4 cross-check on the top 200 SKUs by revenue. Pure functions,
no I/O, no network.
"""

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

ADI_CUTOFF = 1.32
CV2_CUTOFF = 0.49


def classify_sbc(adi: float, cv2: float) -> str:
    """SBC quadrant for one SKU (cut-offs ADI 1.32, CV² 0.49)."""
    if adi < ADI_CUTOFF and cv2 < CV2_CUTOFF:
        return "smooth"
    if adi < ADI_CUTOFF:
        return "erratic"
    if cv2 < CV2_CUTOFF:
        return "intermittent"
    return "lumpy"


def demand_pattern_stats(weekly: pd.DataFrame) -> pd.DataFrame:
    """Per-SKU demand-pattern statistics over the 52 full weeks.

    ``weekly`` is long format with ``week_start``, ``stock_code``,
    ``description`` and ``units``. Every SKU present in the frame gets one
    row; weeks with no row for a SKU count as zero demand. Returns one row
    per SKU with weeks_with_demand, total_units, mean_weekly_units, adi,
    cv2, cv, trend_slope and cluster.
    """
    pivot = weekly.pivot_table(
        index="stock_code", columns="week_start", values="units", aggfunc="sum"
    ).fillna(0)
    descriptions = (
        weekly.drop_duplicates("stock_code")
        .set_index("stock_code")["description"]
        .reindex(pivot.index)
    )
    n_weeks = pivot.shape[1]
    rows = []
    week_index = np.arange(n_weeks, dtype=float)
    for code, values in pivot.iterrows():
        vals = values.to_numpy(dtype=float)
        nonzero = vals[vals > 0]
        n_nonzero = len(nonzero)
        mean_nonzero = float(nonzero.mean()) if n_nonzero else 0.0
        if n_nonzero >= 2:
            std_nonzero = float(nonzero.std(ddof=1))
            cv = std_nonzero / mean_nonzero if mean_nonzero else 0.0
        else:
            cv = 0.0
        cv2 = float(cv**2)
        adi = float(n_weeks / n_nonzero) if n_nonzero else float(n_weeks)
        slope = float(np.polyfit(week_index, vals, 1)[0]) if n_weeks > 1 else 0.0
        rows.append(
            {
                "stock_code": code,
                "description": descriptions.get(code, ""),
                "total_units": float(vals.sum()),
                "weeks_with_demand": n_nonzero,
                "mean_weekly_units": float(vals.mean()),
                "adi": adi,
                "cv2": cv2,
                "cv": cv,
                "trend_slope": slope,
                "cluster": classify_sbc(adi, cv2),
            }
        )
    return pd.DataFrame(rows)


def summarise_clusters(stats: pd.DataFrame) -> pd.DataFrame:
    """One row per SBC quadrant: SKU counts and unit shares."""
    total_skus = len(stats)
    total_units = float(stats["total_units"].sum())
    rows = []
    for cluster in ["smooth", "erratic", "intermittent", "lumpy"]:
        sub = stats[stats["cluster"] == cluster]
        rows.append(
            {
                "cluster": cluster,
                "n_skus": len(sub),
                "share_skus": float(len(sub) / total_skus) if total_skus else 0.0,
                "share_units": (
                    float(sub["total_units"].sum() / total_units)
                    if total_units
                    else 0.0
                ),
                "mean_adi": float(sub["adi"].mean()) if len(sub) else 0.0,
                "mean_cv2": float(sub["cv2"].mean()) if len(sub) else 0.0,
            }
        )
    return pd.DataFrame(rows)


def kmeans_crosscheck(
    features: pd.DataFrame, k: int = 4, seed: int = 42
) -> tuple[np.ndarray, float]:
    """KMeans cross-check on standardised per-SKU features.

    ``features`` must carry ``mean_weekly_units``, ``cv``, ``adi``,
    ``trend_slope`` and ``cluster`` (SBC). Returns (labels, agreement
    rate): the share of SKUs whose KMeans group maps to their SBC
    quadrant under the best one-to-one mapping (Hungarian algorithm).
    """
    cols = ["mean_weekly_units", "cv", "adi", "trend_slope"]
    x = StandardScaler().fit_transform(features[cols].to_numpy(dtype=float))
    labels = KMeans(n_clusters=k, random_state=seed, n_init=10).fit_predict(x)
    quadrants = ["smooth", "erratic", "intermittent", "lumpy"]
    sbc = features["cluster"].tolist()
    contingency = np.zeros((k, len(quadrants)), dtype=int)
    for lab, q in zip(labels, sbc):
        contingency[int(lab), quadrants.index(q)] += 1
    row_ind, col_ind = linear_sum_assignment(-contingency)
    agreement = float(contingency[row_ind, col_ind].sum() / max(len(sbc), 1))
    return labels, agreement
