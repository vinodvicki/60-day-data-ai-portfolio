"""Clustering, segment naming, SBC cross-check and segment profile
for Day 12 — Customer Segmentation Engine.

DECIDER RULE (plan §2.0): KMeans on log1p-transformed,
StandardScaler-scaled R/F/M is the SOLE decider of segment assignment.
RFM quintile scores name and explain the segments; SBC quadrants are a
cross-check only, with the agreement rate reported. Pure functions
(except the thin profile builder), no network.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ADI_CUTOFF = 1.32
CV2_CUTOFF = 0.49

# Fixed prototype mapping (plan §4.2), in tie-break order.
PROTOTYPES = [
    ("Champions", (5, 5, 5)),
    ("Loyal Customers", (4, 4, 4)),
    ("Big Spenders", (3, 3, 5)),
    ("Potential Loyalists", (5, 2, 3)),
    ("New Customers", (5, 1, 1)),
    ("At Risk", (2, 4, 4)),
    ("Hibernating", (2, 2, 2)),
    ("Lost", (1, 1, 1)),
]

SBC_QUADRANTS = ["Smooth", "Erratic", "Intermittent", "Lumpy"]


def _scaled_features(rfm: pd.DataFrame) -> np.ndarray:
    """log1p-transform R/F/M, then StandardScaler. Never raw R/F/M."""
    x = np.log1p(
        rfm[["recency_days", "frequency", "monetary_gbp"]].to_numpy(dtype=float)
    )
    return np.asarray(StandardScaler().fit_transform(x), dtype=float)


def select_k(
    rfm: pd.DataFrame, k_range: range = range(2, 9), seed: int = 42
) -> pd.DataFrame:
    """Elbow SSE + silhouette per k in ``k_range`` (plan §4.3)."""
    x = _scaled_features(rfm)
    rows = []
    for k in k_range:
        model = KMeans(n_clusters=int(k), random_state=seed, n_init=10)
        labels = model.fit_predict(x)
        rows.append(
            {
                "k": int(k),
                "sse": float(model.inertia_),
                "silhouette": float(silhouette_score(x, labels)),
            }
        )
    return pd.DataFrame(rows)


def choose_k(selection: pd.DataFrame) -> int:
    """k = argmax silhouette; if two k values are within 0.01, the
    smaller k wins (plan §4.3)."""
    best = float(selection["silhouette"].max())
    candidates = selection[selection["silhouette"] >= best - 0.01]
    return int(candidates["k"].min())


def cluster_customers(rfm: pd.DataFrame, k: int, seed: int = 42) -> np.ndarray:
    """KMeans labels (0..k-1) on log1p + scaled R/F/M (the decider)."""
    x = _scaled_features(rfm)
    return np.asarray(
        KMeans(n_clusters=int(k), random_state=seed, n_init=10).fit_predict(x),
        dtype=int,
    )


def name_segments(median_scores: pd.DataFrame) -> dict:
    """Map each KMeans cluster label to a segment name (plan §4.2).

    ``median_scores`` is indexed by cluster label with columns
    ``median_r_score``, ``median_f_score``, ``median_m_score``. Each
    cluster takes the unused name whose prototype is closest in
    Euclidean distance to its median triple; greedy by smallest
    distance first, ties broken by the pool order in PROTOTYPES.
    Each name is used at most once.
    """
    pairs = []
    for label, row in median_scores.iterrows():
        triple = (
            float(row["median_r_score"]),
            float(row["median_f_score"]),
            float(row["median_m_score"]),
        )
        for order, (name, proto) in enumerate(PROTOTYPES):
            dist = float(np.sqrt(sum((a - b) ** 2 for a, b in zip(triple, proto))))
            pairs.append((dist, order, int(label), name))
    pairs.sort()
    used_names, used_labels, mapping = set(), set(), {}
    for _, _, label, name in pairs:
        if label in used_labels or name in used_names:
            continue
        mapping[label] = name
        used_labels.add(label)
        used_names.add(name)
    return mapping


def sbc_stats(orders: pd.DataFrame) -> pd.DataFrame:
    """Per-customer SBC statistics (plan §4.4).

    ``orders`` carries ``customer_id``, ``invoice_no``,
    ``invoice_date`` and ``line_revenue`` (cleaned rows). Per-order £
    totals are Σ line values per InvoiceNo. ADI (weeks) = mean gap
    between successive distinct order dates, in days ÷ 7. CV² =
    (std ÷ mean)² of the per-order £ totals. Single-order customers
    get NaN ADI/CV² (quadrant ``Single-order``).
    """
    per_order = (
        orders.groupby(["customer_id", "invoice_no"], as_index=False)
        .agg(
            order_date=("invoice_date", "min"),
            order_value=("line_revenue", "sum"),
        )
        .sort_values(["customer_id", "order_date"])
    )
    rows = []
    for customer_id, sub in per_order.groupby("customer_id"):
        values = sub["order_value"].to_numpy(dtype=float)
        dates = pd.to_datetime(sub["order_date"]).sort_values()
        if len(values) >= 2:
            gaps = dates.diff().dt.days.to_numpy(dtype=float)[1:] / 7.0
            adi = float(np.mean(gaps))
            mean_val = float(values.mean())
            std_val = float(values.std(ddof=1)) if len(values) >= 2 else 0.0
            cv2 = float((std_val / mean_val) ** 2) if mean_val else 0.0
        else:
            adi, cv2 = float("nan"), float("nan")
        rows.append(
            {
                "customer_id": int(customer_id),
                "frequency": len(values),
                "adi_weeks": adi,
                "cv2": cv2,
                "sbc_quadrant": classify_sbc(adi, cv2),
            }
        )
    return pd.DataFrame(rows).sort_values("customer_id").reset_index(drop=True)


def classify_sbc(adi: float, cv2: float) -> str:
    """SBC quadrant for one customer (cut-offs ADI 1.32, CV² 0.49).

    ADI undefined (NaN, i.e. a single-order customer) → "Single-order".
    Thresholds are inclusive (≤), per plan §4.4. The exact theoretical
    cut-offs are 4/3 and 0.5 (Kostenko & Hyndman); 1.32/0.49 is the
    SBC-published rounded convention used here.
    """
    if adi is None or (isinstance(adi, float) and np.isnan(adi)):
        return "Single-order"
    if adi <= ADI_CUTOFF and cv2 <= CV2_CUTOFF:
        return "Smooth"
    if adi <= ADI_CUTOFF:
        return "Erratic"
    if cv2 <= CV2_CUTOFF:
        return "Intermittent"
    return "Lumpy"


def agreement_rate(contingency: pd.DataFrame) -> float:
    """Agreement rate (plan §4.4): greedy best one-to-one
    segment↔quadrant mapping over multi-order customers only.

    ``contingency`` rows = segments, columns = the four SBC quadrants
    (Single-order excluded). Greedy by largest cell first; agreement =
    matched customers ÷ multi-order customers (the table total).
    """
    table = contingency.copy()
    for col in ("Single-order",):
        if col in table.columns:
            table = table.drop(columns=[col])
    cells = []
    for seg in table.index:
        for quad in table.columns:
            cells.append((int(table.loc[seg, quad]), str(seg), str(quad)))
    cells.sort(reverse=True)
    used_segs, used_quads, matched = set(), set(), 0
    for value, seg, quad in cells:
        if seg in used_segs or quad in used_quads:
            continue
        matched += value
        used_segs.add(seg)
        used_quads.add(quad)
    total = int(table.to_numpy().sum())
    return float(matched / total) if total else 0.0


def build_segment_profile(
    rfm_table: pd.DataFrame,
    total_cleaned_revenue: float | None = None,
    unattributed_revenue: float = 0.0,
    unattributed_rows: int = 0,
) -> pd.DataFrame:
    """One row per KMeans-named segment (+ Unattributed row), columns
    in plan §3.5 order. ``rfm_table`` carries the decider-assigned
    ``segment`` column. Revenue shares are reported against attributed
    revenue AND total cleaned revenue. ``action`` / ``gbp_at_stake``
    are filled later by ``src.actions.build_actions``.
    """
    attributed = float(rfm_table["monetary_gbp"].sum())
    total = float(total_cleaned_revenue) if total_cleaned_revenue else attributed
    n_customers = len(rfm_table)
    rows = []
    for segment, sub in rfm_table.groupby("segment", sort=False):
        revenue = float(sub["monetary_gbp"].sum())
        rows.append(
            {
                "segment": str(segment),
                "n_customers": len(sub),
                "share_customers": (
                    float(len(sub) / n_customers) if n_customers else 0.0
                ),
                "revenue_gbp": revenue,
                "revenue_share_attributed": revenue / attributed if attributed else 0.0,
                "revenue_share_total": revenue / total if total else 0.0,
                "mean_recency_days": float(sub["recency_days"].mean()),
                "median_recency_days": float(sub["recency_days"].median()),
                "mean_frequency": float(sub["frequency"].mean()),
                "median_frequency": float(sub["frequency"].median()),
                "mean_monetary_gbp": float(sub["monetary_gbp"].mean()),
                "median_monetary_gbp": float(sub["monetary_gbp"].median()),
                "mean_rfm_score": float(sub["rfm_score"].mean()),
                "median_r_score": float(sub["r_score"].median()),
                "median_f_score": float(sub["f_score"].median()),
                "median_m_score": float(sub["m_score"].median()),
                "action": "",
                "gbp_at_stake": revenue,
            }
        )
    profile = pd.DataFrame(rows).sort_values("revenue_gbp", ascending=False)
    unattributed = pd.DataFrame(
        [
            {
                "segment": "Unattributed (no CustomerID)",
                "n_customers": 0,
                "share_customers": 0.0,
                "revenue_gbp": float(unattributed_revenue),
                "revenue_share_attributed": 0.0,
                "revenue_share_total": (
                    float(unattributed_revenue) / total if total else 0.0
                ),
                "mean_recency_days": float("nan"),
                "median_recency_days": float("nan"),
                "mean_frequency": float("nan"),
                "median_frequency": float("nan"),
                "mean_monetary_gbp": float("nan"),
                "median_monetary_gbp": float("nan"),
                "mean_rfm_score": float("nan"),
                "median_r_score": float("nan"),
                "median_f_score": float("nan"),
                "median_m_score": float("nan"),
                "action": "—",
                "gbp_at_stake": float(unattributed_revenue),
            }
        ]
    )
    profile = pd.concat([profile, unattributed], ignore_index=True)
    return profile


def build_sbc_summary(rfm_table: pd.DataFrame) -> pd.DataFrame:
    """One row per SBC quadrant + Single-order (plan §3.5)."""
    attributed = float(rfm_table["monetary_gbp"].sum())
    rows = []
    for quadrant in SBC_QUADRANTS + ["Single-order"]:
        sub = rfm_table[rfm_table["sbc_quadrant"] == quadrant]
        rows.append(
            {
                "quadrant": quadrant,
                "n_customers": len(sub),
                "share_customers": (
                    float(len(sub) / len(rfm_table)) if len(rfm_table) else 0.0
                ),
                "revenue_gbp": float(sub["monetary_gbp"].sum()),
                "revenue_share_attributed": (
                    float(sub["monetary_gbp"].sum() / attributed) if attributed else 0.0
                ),
            }
        )
    return pd.DataFrame(rows)


def build_agreement_table(rfm_table: pd.DataFrame) -> pd.DataFrame:
    """Segment × SBC-quadrant contingency table (plan §3.5)."""
    cols = SBC_QUADRANTS + ["Single-order"]
    table = pd.crosstab(rfm_table["segment"], rfm_table["sbc_quadrant"])
    for col in cols:
        if col not in table.columns:
            table[col] = 0
    return table[cols]
