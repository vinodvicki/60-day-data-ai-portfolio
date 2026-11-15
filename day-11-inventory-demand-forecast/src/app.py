"""Streamlit dashboard for Day 11 — Inventory Demand Forecast.

Loads processed CSVs + data_source.json only (offline). Every surface
labels the two assumptions: the forecast is a 4-week trend extrapolation
from one retailer over one year (NOT a seasonal prediction), and the
reorder list assumes zero on-hand stock and a 1-week lead time.
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
CHARTS = ROOT / "outputs" / "charts"

ASSUMPTION_BANNER = (
    "Forecast: 4-week trend extrapolation from one retailer over one year "
    "(2010–2011) — NOT a seasonal prediction. Reorder list: assumes zero "
    "on-hand stock and a 1-week lead time."
)
ATTRIBUTION = (
    "Data: UCI Online Retail (Chen, D., 2015), DOI 10.24432/C5BW33, " "CC BY 4.0."
)


@st.cache_data
def load_data():
    record = json.loads((PROC / "data_source.json").read_text(encoding="utf-8"))
    return {
        "record": record,
        "weekly": pd.read_csv(PROC / "weekly_demand.csv"),
        "aggregate": pd.read_csv(PROC / "weekly_aggregate.csv"),
        "sku": pd.read_csv(PROC / "sku_summary.csv"),
        "backtest": pd.read_csv(PROC / "backtest.csv"),
        "forecast": pd.read_csv(PROC / "forecast.csv"),
        "reorder": pd.read_csv(PROC / "reorder_list.csv"),
        "clusters": pd.read_csv(PROC / "cluster_summary.csv"),
    }


def main():
    st.set_page_config(page_title="Day 11 — Inventory Demand Forecast", layout="wide")
    data = load_data()
    record = data["record"]
    st.title("Inventory Demand Forecast — UCI Online Retail (2010–2011)")
    st.caption(ASSUMPTION_BANNER)
    st.caption(ATTRIBUTION)

    sku, reorder, backtest = data["sku"], data["reorder"], data["backtest"]
    aggregate = data["aggregate"]
    total_units = int(aggregate["units"].sum())
    top20_share = float(sku["revenue_share"].sum())
    primary = backtest[backtest["origin"] == 48]
    overall = record["backtest"]["overall_volume_weighted_wape_primary"]
    headline_method = min(
        (m for m in overall if m != "seasonal_naive"),
        key=lambda m: overall[m],
    )
    headline_wape = overall[headline_method]
    n_review = int((reorder["stockout_risk_flag"] == "review-manually").sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total units (52 full weeks)", f"{total_units:,}")
    col2.metric("Top-20 revenue share", f"{top20_share:.1%}")
    col3.metric(
        "Headline WAPE (primary holdout)",
        f"{headline_wape:.1%}",
        f"best method: {headline_method.replace('_', ' ')}",
    )
    col4.metric("SKUs flagged review-manually", str(n_review))

    st.subheader("Forecast — next 4 weeks (weeks starting 2011-12-05)")
    st.caption(
        "Cluster-winner forecast per SKU. Trend extrapolation, not a "
        "seasonal prediction; horizon is 4 weeks only."
    )
    forecast = data["forecast"]
    st.dataframe(forecast, width="stretch")

    st.subheader("Proposed reorder list — top 20 SKUs")
    st.caption(
        "Assumptions: 1-week lead time; 95% service level (smooth/erratic) "
        "or 90% (intermittent/lumpy); safety stock = z × σ × √lead time; "
        "order-up-to level S is the deliverable and the implied order "
        "assumes zero on-hand stock."
    )
    st.dataframe(reorder, width="stretch")
    st.caption(
        f"Total order-up-to across the top 20: "
        f"{reorder['order_up_to_units'].sum():,.0f} units; total implied "
        f"order from zero on-hand: "
        f"{reorder['implied_order_zero_on_hand_units'].sum():,.0f} units."
    )

    st.subheader("Charts")
    st.image(
        str(CHARTS / "01_forecast_vs_actual.png"),
        caption="Forecast vs actual — primary holdout",
        width="stretch",
    )
    st.image(
        str(CHARTS / "02_method_wape.png"),
        caption="Method comparison by WAPE",
        width="stretch",
    )
    st.image(
        str(CHARTS / "03_demand_pattern_clusters.png"),
        caption="Demand-pattern clustering (ADI vs CV²)",
        width="stretch",
    )
    st.image(
        str(CHARTS / "04_reorder_list.png"),
        caption="Reorder list — order-up-to levels",
        width="stretch",
    )

    st.subheader("Method comparison (primary holdout, WAPE)")
    st.dataframe(
        primary.pivot_table(
            index="method", columns="stock_code", values="wape", dropna=False
        ),
        width="stretch",
    )

    st.subheader("Demand-pattern clusters")
    st.caption(
        "Syntetos–Boylan quadrants (ADI 1.32, CV² 0.49) over every SKU with "
        "any demand; KMeans k = 4 cross-check on the top 200 SKUs: agreement "
        f"{record['clustering']['kmeans_crosscheck']['agreement_rate']:.1%}."
    )
    st.dataframe(data["clusters"], width="stretch")
    st.dataframe(
        sku[
            ["stock_code", "description", "cluster", "adi", "cv2", "weeks_with_demand"]
        ],
        width="stretch",
    )

    st.subheader("Recommendations")
    st.markdown("""
1. **Order the biggest lines now** — start with the SKUs with the largest
   order-up-to levels in the reorder list above.
2. **Review the flagged lines manually** — lumpy SKUs and Croston-SBA
   forecasts are low-confidence; do not auto-order them on a point forecast.
3. **Hold the safety stock the error demands** — the headline WAPE shows how
   far the forecast can be off; the safety stock in the reorder list is the
   cover for that error. See `outputs/insights_summary.md` for the numbers.
""")

    st.subheader("Methods and limitations")
    st.markdown("""
- Weekly demand per SKU over 52 full weeks (2010-12-06 → 2011-12-04);
  partial first/last weeks excluded. Demand in units; revenue (GBP) only
  ranks SKUs.
- Six methods compared on two 4-week holdouts (primary: train weeks 1–48,
  forecast weeks 49–52, the Christmas ramp; supplementary: train weeks 1–29,
  forecast weeks 30–33). Winner chosen per demand-pattern cluster by
  volume-weighted primary-holdout WAPE, with a 0.5 pp simplicity tie-break.
  Seasonal naïve is unavailable on a 52-week series (its WAPE is n/a).
- Holt ETS uses an additive trend with **no seasonal component** — one year
  of data cannot support a seasonal fit.
- Limitations: single retailer, single year; no seasonality fitted; prices
  may or may not include VAT (dataset does not state it); no inventory or
  lead-time data exists, so the reorder list is assumption-based (see above).
""")
    st.caption(ATTRIBUTION)


if __name__ == "__main__":
    main()
