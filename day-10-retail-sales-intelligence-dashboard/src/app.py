"""Day 10 — Retail Sales Intelligence Dashboard: Streamlit app.

Loads the committed processed CSVs only (offline, no network, no API).
Run: streamlit run src/app.py  (from the project root)
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHARTS_DIR = PROJECT_ROOT / "outputs" / "charts"
SOURCE_LINE = (
    "Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning "
    "Repository. https://doi.org/10.24432/C5BW33 — CC BY 4.0"
)


@st.cache_data
def load_all():
    record = json.loads((PROCESSED_DIR / "data_source.json").read_text())
    monthly = pd.read_csv(PROCESSED_DIR / "monthly_sales.csv")
    weekly = pd.read_csv(PROCESSED_DIR / "weekly_revenue.csv")
    country = pd.read_csv(PROCESSED_DIR / "country_sales.csv")
    top = pd.read_csv(PROCESSED_DIR / "top_products.csv")
    groups = pd.read_csv(PROCESSED_DIR / "product_groups.csv")
    clusters = pd.read_csv(PROCESSED_DIR / "rfm_clusters.csv")
    summary = pd.read_csv(PROCESSED_DIR / "cluster_summary.csv")
    forecast = pd.read_csv(PROCESSED_DIR / "forecast.csv")
    backtest = pd.read_csv(PROCESSED_DIR / "backtest.csv")
    return {
        "record": record,
        "monthly": monthly,
        "weekly": weekly,
        "country": country,
        "top": top,
        "groups": groups,
        "clusters": clusters,
        "summary": summary,
        "forecast": forecast,
        "backtest": backtest,
    }


DATA = load_all()
RECORD = DATA["record"]
KPIS = RECORD["kpis"]

st.set_page_config(page_title="Retail Sales Intelligence Dashboard", layout="wide")
st.title("Retail Sales Intelligence Dashboard")
st.markdown(
    "UCI Online Retail — one UK online retailer, Dec 2010 to Dec 2011. "
    "Revenue, units, product mix, regional variation and seasonality, "
    "plus customer clusters and an 8-week demand forecast."
)
if RECORD.get("synthetic"):
    st.warning("SYNTHETIC DATA — labelled fallback, not real UCI values.")

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Total revenue", "£10.28m")
col2.metric("Units sold", f"{KPIS['total_units']:,}")
col3.metric("Orders", f"{KPIS['orders']:,}")
col4.metric("Average order value", f"£{KPIS['aov_gbp']:,.2f}")
col5.metric("Unique customers", f"{KPIS['unique_customers']:,}")
col6.metric("Repeat-customer rate", f"{KPIS['repeat_customer_rate_pct']:.2f}%")
st.caption(
    f"Total revenue in full: £{KPIS['total_revenue_gbp']:,.2f}. "
    "Cleaned set: 527,795 transaction lines from 541,909 raw rows — "
    "9,288 cancelled lines, 1,336 non-positive quantities, 1,181 "
    "non-positive prices and 2,309 postage/adjustment lines excluded "
    "(see data/README.md). All revenue in GBP."
)

st.header("Seasonality — monthly sales")
st.image(str(CHARTS_DIR / "01_monthly_sales.png"), width="stretch")
st.dataframe(DATA["monthly"], width="stretch")
st.markdown(
    "November 2011 is the peak month at **£1,457,745.53** (2,751 orders) — "
    "**2.86×** February 2011 (£508,952.87) and 1.81× the average full month. "
    "September–November together are **£3,594,965.43 (34.96%)** of the "
    "year's revenue. December 2011 is partial (9 days) and is excluded "
    "from month-over-month comparisons."
)

st.header("Product mix and regional variation")
st.image(str(CHARTS_DIR / "02_product_country.png"), width="stretch")
st.dataframe(DATA["top"].head(10), width="stretch")
st.markdown(
    f"The top 10 SKUs are **{KPIS['top10_sku_revenue_share_pct']:.2f}%** of "
    "revenue — a long tail, not a winner-takes-all catalogue. The top SKU "
    "is the REGENCY CAKESTAND 3 TIER (£174,484.74 across 1,988 orders); "
    "the second, PAPER CRAFT LITTLE BIRDIE (£168,469.60), is a single "
    "wholesale order of 80,995 units. The largest derived product group "
    "is SET (7.35%), then JUMBO (5.70%); 'Other' is 65.46% — groups are "
    "derived from the first word of the product description, not source "
    "categories."
)
st.dataframe(DATA["country"].head(10), width="stretch")
st.markdown(
    f"The UK is **{KPIS['uk_revenue_share_pct']:.2f}%** of revenue "
    "(£8,759,372.58, 17,904 orders, AOV £489.24). Non-UK revenue is "
    "£1,523,871.40 with an AOV of £814.03 — overseas orders are fewer "
    "but bigger: the Netherlands averages £3,052.57 per order (93 orders) "
    "and Australia £2,467.34 (56 orders), a wholesale pattern."
)

st.header("Customer clusters — RFM + KMeans")
st.image(str(CHARTS_DIR / "03_rfm_clusters.png"), width="stretch")
st.dataframe(DATA["summary"], width="stretch")
st.markdown(
    "KMeans (k = 4) on standardised RFM, silhouette **0.616** — the "
    "clusters are well separated. **Champions (13 customers, 0.30%)** "
    "average £125,862.44 each and contribute 18.68% of identified-customer "
    "revenue; **Big spenders (209)** add 29.26%. Together the top 222 "
    "customers (5.12%) drive **47.94% (£4,200,055.35)** of identified "
    "revenue. **Lapsed (1,066 customers, 24.60%)** last bought 247.5 days "
    "ago on average and contribute only 5.79%. Descriptive segmentation, "
    "not a churn model. Rows with no CustomerID (14.80% of revenue) are "
    "excluded from this panel only."
)

st.header("Demand forecast — next 8 weeks")
st.image(str(CHARTS_DIR / "04_forecast.png"), width="stretch")
st.dataframe(DATA["forecast"], width="stretch")
forecast_total = float(DATA["forecast"]["forecast_gbp"].sum())
st.markdown(
    f"The published forecast is **Holt-Winters (additive trend, no "
    f"seasonality)** — it beat the naïve baseline in the backtest "
    f"(mean RMSE £55,504.52 vs £62,800.78). The 8 weeks from 2011-12-05 "
    f"are forecast at **£{forecast_total:,.2f} in total**, rising from "
    f"£346,552.30 to £418,710.57 per week, with 80% and 95% prediction "
    f"intervals from a residual bootstrap (seed 42, 1,000 paths). "
    f"One year of data cannot support a seasonal fit, so this is a trend "
    f"extrapolation — the December spike is visible in the history but "
    f"is not modelled."
)
st.dataframe(DATA["backtest"], width="stretch")

st.header("Three commercial recommendations")
st.markdown(
    "1. **Protect the 222 highest-value customers.** Champions (13) plus "
    "Big spenders (209) are 5.12% of identified customers and 47.94% of "
    "identified revenue (£4,200,055.35). Give them named-account service, "
    "priority allocation of the top-10 SKUs and early access to Q4 stock. "
    "Losing even 10% of that base costs ~£420,000 a year.\n\n"
    "2. **Build stock 6–8 weeks before the September ramp.** September–"
    "November are £3,594,965.43 (34.96%) of annual revenue, and November "
    "alone is £1,457,745.53 — 2.86× February — on 2,751 orders. Pre-build "
    "inventory of the top-10 SKUs (9.41% of revenue) and the SET/JUMBO "
    "groups before September. A 5% stock-out on November revenue alone "
    "is ~£73,000.\n\n"
    "3. **Win back the 1,066 lapsed customers.** They are 24.60% of "
    "customers but only 5.79% of revenue, last buying 247.5 days ago on "
    "average. A targeted re-engagement offer that brings back 10% of "
    "them at their mean spend (£475.91) is worth ~£50,732; if they return "
    "at the Occasional-buyer mean (£1,330.93), ~£141,877."
)

st.header("Methods and limitations")
st.markdown(
    "- Cleaning: cancellations (InvoiceNo starting 'C'), non-positive "
    "quantities/prices and postage/adjustment lines (POST, DOT, M, D, "
    "BANK CHARGES, CRUK, C2, AMAZONFEE, gift vouchers) excluded, every "
    "exclusion counted in data_source.json.\n"
    "- Product groups are derived from the first word of the product "
    "description — not source categories.\n"
    "- RFM + KMeans (k = 4, seed 42), silhouette 0.616; labels describe "
    "the fitted centroids.\n"
    "- Forecast: weekly revenue (51 full weeks), Holt-Winters additive "
    "trend, no seasonality — one year cannot support a seasonal fit; "
    "backtested at 2 rolling origins (8 / 16 weeks, 8-week horizons).\n"
    "- Single retailer, single year (2010–2011): historical data, not a "
    "current-market tool. Prices may or may not include VAT — the "
    "dataset does not state it.\n"
    "- SQL check (notebook): monthly revenue and top-5 countries "
    "recomputed in SQLite and asserted equal to pandas."
)
st.caption(f"Source: {SOURCE_LINE}")
