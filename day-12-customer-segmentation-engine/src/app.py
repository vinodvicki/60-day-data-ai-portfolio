"""Streamlit dashboard for Day 12 — Customer Segmentation Engine.

Loads processed CSVs + data_source.json only (offline). Every surface
labels the three hard limits: RFM scores are relative to this customer
base, the data is 2010–2011 (historical), and unattributed revenue
(no CustomerID) is shown as its own line. KMeans decides segment
assignment (plan §2.0); SBC is a cross-check with the agreement rate.
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
CHARTS = ROOT / "outputs" / "charts"

LIMITS_BANNER = (
    "Historical 2010–2011 data — the segments describe that year, not "
    "today. RFM scores are relative to this customer base, not absolute. "
    "KMeans on log1p + scaled R/F/M decides segment assignment (plan §2.0)."
)
ATTRIBUTION = (
    "Data: UCI Online Retail (Chen, D., 2015), DOI 10.24432/C5BW33, " "CC BY 4.0."
)


@st.cache_data
def load_data():
    record = json.loads((PROC / "data_source.json").read_text(encoding="utf-8"))
    return {
        "record": record,
        "rfm": pd.read_csv(PROC / "rfm_table.csv"),
        "profile": pd.read_csv(PROC / "segment_profile.csv"),
        "sbc": pd.read_csv(PROC / "sbc_summary.csv"),
        "agreement": pd.read_csv(PROC / "agreement.csv", index_col=0),
    }


def main():
    st.set_page_config(
        page_title="Day 12 — Customer Segmentation Engine", layout="wide"
    )
    data = load_data()
    record = data["record"]
    profile, rfm = data["profile"], data["rfm"]
    st.title("Customer Segmentation Engine — UCI Online Retail (2010–2011)")
    st.caption(LIMITS_BANNER)
    st.caption(ATTRIBUTION)

    segments = profile[profile["segment"] != "Unattributed (no CustomerID)"]
    top = segments.iloc[0]
    unattributed = profile[profile["segment"] == "Unattributed (no CustomerID)"].iloc[0]

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Identified customers", f"{len(rfm):,}")
    col2.metric("Total cleaned revenue", "£10.28m", "£10,283,243.98")
    col3.metric("Attributed revenue", "£8.76m", "£8,761,066.65")
    col4.metric(
        "Top segment",
        top["segment"],
        "£7.44m · 84.9% of attributed",
    )
    col5.metric(
        "SBC↔KMeans agreement",
        f"{record['agreement_rate']:.1%}",
        "2,829 multi-order",
    )

    st.subheader("Segment profile — one tailored action per segment")
    st.caption(
        "KMeans on log1p + scaled R/F/M decides every assignment; RFM "
        "scores name and explain the segments. £ at stake = the segment's "
        "revenue: to protect (Champions / Loyal / Big Spenders), at risk "
        "or already lapsed (At Risk / Hibernating / Lost), to grow "
        "(Potential Loyalists / New Customers)."
    )
    # D-2 fix (optimizer): the full profile has 18 columns, so the action
    # + £ at stake columns were cut off at 1200 px and only reachable by
    # horizontal scrolling. Surface them first in a compact 5-column
    # action table (no scrolling needed); the full table follows below.
    st.markdown("**What to do per segment — action + £ at stake**")
    actions = segments[
        ["segment", "n_customers", "revenue_gbp", "action", "gbp_at_stake"]
    ]
    st.dataframe(
        actions,
        width="stretch",
        column_config={
            "revenue_gbp": st.column_config.NumberColumn(
                "Revenue (£)", format="£%,.2f"
            ),
            "gbp_at_stake": st.column_config.NumberColumn(
                "£ at stake", format="£%,.2f"
            ),
        },
    )
    st.caption(
        "Full segment profile — all columns (scroll right for mean/median R/F/M)."
    )
    st.dataframe(profile, width="stretch")
    st.caption(
        f"Unattributed revenue (no CustomerID): "
        f"£{unattributed['revenue_gbp']:,.2f} "
        f"({unattributed['revenue_share_total']:.1%} of total cleaned "
        f"revenue) — it cannot be assigned to any segment."
    )

    st.subheader("Charts")
    st.image(
        str(CHARTS / "01_rfm_scores.png"),
        caption="RFM scores and customers per segment",
        width="stretch",
    )
    st.image(
        str(CHARTS / "02_segment_value.png"),
        caption="Share of customers vs share of attributed revenue",
        width="stretch",
    )
    st.image(
        str(CHARTS / "03_kmeans_clusters.png"),
        caption="KMeans clusters — KMeans decides segment assignment",
        width="stretch",
    )
    st.image(
        str(CHARTS / "04_sbc_quadrants.png"),
        caption="SBC cross-check — ADI vs CV²",
        width="stretch",
    )

    st.subheader("KMeans — the decider (plan §2.0)")
    k_rows = record["k_selection"]
    st.dataframe(pd.DataFrame(k_rows), width="stretch")
    st.caption(
        f"Chosen k = {record['chosen_k']} by the §4.3 rule (argmax "
        f"silhouette, 0.01 smaller-k tie-break). Cluster → name mapping: "
        + "; ".join(
            f"cluster {c}: {v['segment']} "
            f"(median scores R{v['median_r_score']:.0f} "
            f"F{v['median_f_score']:.0f} M{v['median_m_score']:.0f})"
            for c, v in record["segment_naming"].items()
        )
    )

    st.subheader("SBC cross-check")
    st.caption(
        "Syntetos–Boylan quadrants (ADI 1.32 weeks, CV² 0.49) on per-order "
        "£ totals; Single-order customers have no ADI and are excluded "
        "from the agreement rate. SBC never overrides a KMeans assignment."
    )
    st.dataframe(data["sbc"], width="stretch")
    st.subheader("Segment × SBC quadrant (customer counts)")
    st.dataframe(data["agreement"], width="stretch")

    st.subheader("Methods and limitations")
    st.markdown("""
- RFM per customer over the full cleaned window (2010-12-01 → 2011-12-09),
  snapshot date 2011-12-10 = max(InvoiceDate) + 1 day. Recency in days,
  Frequency = distinct invoices, Monetary = Σ(Quantity × UnitPrice) in GBP.
- Scores are percentile-rank 1–5 (ties share a score), R inverted;
  relative to this customer base — recompute if the base changes.
- KMeans (log1p + StandardScaler, random_state 42, n_init 10) decides
  segment assignment; clusters are named from their median RFM-score
  profile. SBC quadrants are an interpretive cross-check only.
- Cleaning (in order): cancellations, non-positive quantity, non-positive
  price, non-product adjustment lines, missing descriptions; rows with no
  CustomerID are excluded from RFM and counted as unattributed revenue.
- Limitations: single retailer, single year (2010–2011); prices may or may
  not include VAT (the dataset does not state it); no current-customer
  claims are made; SBC and KMeans disagree about a share of customers —
  the agreement rate above reports it, it is not averaged away.
""")
    st.caption(ATTRIBUTION)


if __name__ == "__main__":
    main()
