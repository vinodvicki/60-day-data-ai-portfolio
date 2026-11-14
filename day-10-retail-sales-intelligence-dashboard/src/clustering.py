"""Day 10 — Retail Sales Intelligence Dashboard: RFM + KMeans clustering.

Plan §4.3: RFM per identified customer (missing CustomerID excluded),
features standardised, KMeans k = 4, ``random_state=42``,
``n_init=10``. No tuning grid. Labels are assigned from the cluster
centroids *after* fitting — they describe the centroids, they are not
pre-assigned. This is descriptive segmentation, not a churn or
lifetime-value model.

All functions here are pure except ``build_forecast``-style writers;
``build_rfm`` / ``cluster_customers`` / ``summarise_clusters`` take and
return DataFrames / arrays only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

K_CLUSTERS = 4
CLUSTER_SEED = 42
RFM_COLUMNS = ["recency_days", "frequency", "monetary_gbp"]


def build_rfm(df: pd.DataFrame) -> pd.DataFrame:
    """RFM table for identified customers only (plan §4.3).

    ``df`` is the cleaned transaction set (one row per line, with
    ``line_revenue``, ``InvoiceNo``, ``InvoiceDate`` and ``CustomerID``).
    Rows with a missing ``CustomerID`` are excluded. Recency is days
    from the customer's last purchase to the dataset end (max
    ``InvoiceDate``); Frequency is distinct orders; Monetary is total
    revenue. Returns one row per customer, sorted by ``customer_id``.
    """
    identified = df[df["CustomerID"].notna()].copy()
    if identified.empty:
        raise ValueError("no identified customers in the cleaned set")
    end_date = pd.to_datetime(df["InvoiceDate"]).max()
    grouped = identified.groupby("CustomerID").agg(
        last_purchase=("InvoiceDate", "max"),
        frequency=("InvoiceNo", "nunique"),
        monetary_gbp=("line_revenue", "sum"),
    )
    rfm = (
        pd.DataFrame(
            {
                "customer_id": grouped.index.astype(int),
                "recency_days": (
                    end_date - pd.to_datetime(grouped["last_purchase"])
                ).dt.days.astype(int),
                "frequency": grouped["frequency"].astype(int),
                "monetary_gbp": grouped["monetary_gbp"].astype(float).round(2),
            }
        )
        .sort_values("customer_id")
        .reset_index(drop=True)
    )
    return rfm


def cluster_customers(
    rfm: pd.DataFrame, k: int = K_CLUSTERS, seed: int = CLUSTER_SEED
) -> tuple[np.ndarray, float]:
    """KMeans on standardised RFM (plan §4.3).

    Returns (labels, silhouette score). Deterministic for a fixed
    ``seed``. Raises if there are fewer customers than ``k``.
    """
    if len(rfm) < k:
        raise ValueError(f"need at least {k} customers to cluster, got {len(rfm)}")
    features = StandardScaler().fit_transform(rfm[RFM_COLUMNS].to_numpy(dtype=float))
    model = KMeans(n_clusters=k, random_state=seed, n_init=10)
    labels = model.fit_predict(features)
    score = float(silhouette_score(features, labels))
    return np.asarray(labels, dtype=int), score


def summarise_clusters(rfm: pd.DataFrame, labels: np.ndarray) -> pd.DataFrame:
    """One row per cluster: size, shares, mean R/F/M (plan §4.3).

    ``share_revenue`` is the cluster's share of total RFM monetary
    (identified-customer revenue). The ``label`` column is filled by
    :func:`assign_labels`.
    """
    frame = rfm.copy()
    frame["cluster"] = np.asarray(labels, dtype=int)
    total_customers = len(frame)
    total_revenue = float(frame["monetary_gbp"].sum())
    rows: list[dict] = []
    for cluster in sorted(frame["cluster"].unique()):
        sub = frame[frame["cluster"] == cluster]
        rows.append(
            {
                "cluster": int(cluster),
                "label": "",
                "n_customers": len(sub),
                "share_customers": round(len(sub) / total_customers * 100, 2),
                "share_revenue": round(
                    float(sub["monetary_gbp"].sum()) / total_revenue * 100, 2
                ),
                "mean_recency": round(float(sub["recency_days"].mean()), 1),
                "mean_frequency": round(float(sub["frequency"].mean()), 2),
                "mean_monetary": round(float(sub["monetary_gbp"].mean()), 2),
            }
        )
    summary = pd.DataFrame.from_records(
        rows,
        columns=[
            "cluster",
            "label",
            "n_customers",
            "share_customers",
            "share_revenue",
            "mean_recency",
            "mean_frequency",
            "mean_monetary",
        ],
    )
    summary["label"] = assign_labels(summary)
    return summary


def assign_labels(summary: pd.DataFrame) -> list[str]:
    """Plain-language labels from the cluster centroids (plan §4.3).

    Ranking rules, applied to the centroid means (not pre-assigned):
    the cluster with the lowest mean recency *and* the highest mean
    frequency is "Champions"; the cluster with the highest mean
    monetary is "Big spenders"; the cluster with the highest mean
    recency is "Lapsed"; the remaining cluster is "Occasional buyers".
    Ties are broken by mean monetary (higher first). Labels are
    descriptive of the fitted centroids.
    """
    ranked = summary.copy()
    n = len(ranked)
    if n == 0:
        return []
    # Champions: lowest recency, then highest frequency.
    champions = ranked.sort_values(
        ["mean_recency", "mean_frequency", "mean_monetary"],
        ascending=[True, False, False],
    ).iloc[0]["cluster"]
    remaining = [c for c in ranked["cluster"] if c != champions]
    labels: dict[int, str] = {int(champions): "Champions"}
    if remaining:
        # Big spenders: highest mean monetary among the rest.
        big = (
            ranked[ranked["cluster"].isin(remaining)]
            .sort_values("mean_monetary", ascending=False)
            .iloc[0]["cluster"]
        )
        labels[int(big)] = "Big spenders"
        remaining = [c for c in remaining if c != big]
    if remaining:
        # Lapsed: highest mean recency among the rest.
        lapsed = (
            ranked[ranked["cluster"].isin(remaining)]
            .sort_values("mean_recency", ascending=False)
            .iloc[0]["cluster"]
        )
        labels[int(lapsed)] = "Lapsed"
        remaining = [c for c in remaining if c != lapsed]
    for cluster in remaining:
        labels[int(cluster)] = "Occasional buyers"
    return [labels[int(c)] for c in summary["cluster"]]
