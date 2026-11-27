"""Day 20 Inflation & Cost of Living Dashboard: Streamlit app.

Reads the processed CSVs and chart PNGs only — never the raw FRED files
and never the network. All six labelled assumptions (research_brief.md §3)
are shown on the page.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
CHARTS_DIR = ROOT / "outputs" / "charts"

ASSUMPTIONS = [
    "All CPI series are seasonally adjusted BLS series via FRED; index base 1982–84 = 100.",
    "Analysis window Mar 2006 – Oct 2026 (set by earnings availability). Headline CPI history back to 1947 is context only.",
    "Latest data: October 2026 (FRED lag ≈ 1 month — November CPI is not yet released).",
    "Real earnings use headline CPI as the deflator; no tax, benefits, or hours-worked adjustment — hourly wage only, all private employees.",
    "The $100 basket is a fixed-basket illustration: no substitution and no BLS weight changes.",
    "No forecast is made — this dashboard is descriptive.",
]


def load_frames() -> dict[str, pd.DataFrame]:
    """Load every processed table the dashboard needs."""
    names = [
        "monthly_panel",
        "yoy_inflation",
        "category_cumulative",
        "real_earnings",
        "basket_cost",
        "summary_stats",
    ]
    return {n: pd.read_csv(PROCESSED_DIR / f"{n}.csv") for n in names}


def main() -> None:
    """Render the dashboard."""
    st.set_page_config(page_title="Inflation & Cost of Living", layout="wide")
    frames = load_frames()
    yoy_df = frames["yoy_inflation"]
    cum_df = frames["category_cumulative"]
    real_df = frames["real_earnings"]
    basket_df = frames["basket_cost"]
    summary = frames["summary_stats"]

    latest = str(yoy_df["date"].iloc[-1])
    st.title("Inflation & Cost of Living Dashboard")
    st.caption(
        f"U.S. consumer prices vs. pay, Mar 2006 – Oct 2026 · Latest data: {latest}"
    )

    # Latest YoY is the last non-missing value: the BLS series has no
    # October 2025 observation, so the Oct 2026 YoY is undefined.
    latest_yoy = float(yoy_df["headline_yoy_pct"].dropna().iloc[-1])
    latest_yoy_date = str(yoy_df["date"][yoy_df["headline_yoy_pct"].notna()].iloc[-1])
    latest_core = float(yoy_df["core_yoy_pct"].dropna().iloc[-1])
    latest_cum = float(cum_df["headline_cum_pct"].iloc[-1])
    real_change = float(real_df["real_indexed"].iloc[-1]) - 100.0
    basket_now = float(basket_df["basket_cost_usd"].iloc[-1])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Headline inflation (YoY)",
        f"{latest_yoy:.2f}%",
        help=f"Latest available YoY, {latest_yoy_date} (Oct 2026 YoY is undefined — no Oct 2025 CPI was published).",
    )
    col2.metric("Core inflation (YoY)", f"{latest_core:.2f}%")
    col3.metric("Prices since Mar 2006", f"+{latest_cum:.1f}%")
    col4.metric("Real hourly pay since Mar 2006", f"{real_change:+.1f}%")

    st.subheader("How fast are prices rising?")
    st.image(
        str(CHARTS_DIR / "01_headline_yoy.png"),
        caption="Headline vs. core YoY inflation. Source: BLS via FRED.",
    )

    st.subheader("Which categories rose most since Mar 2006?")
    st.image(
        str(CHARTS_DIR / "02_category_divergence.png"),
        caption="Cumulative price change by category. Source: BLS via FRED.",
    )
    cat_rows = []
    for _, row in summary.iterrows():
        label = str(row["series"])
        if (
            label.startswith("CPI-U")
            and "All Items" not in label
            and "Less Food" not in label
        ):
            cat_rows.append(
                {
                    "Category": label.replace("CPI-U ", "").replace(", SA", ""),
                    "Latest index": round(float(row["latest_value"]), 1),
                    "YoY %": round(float(row["yoy_pct"]), 2),
                    "Since Mar 2006 %": round(
                        float(row["cumulative_since_base_pct"]), 1
                    ),
                    "CAGR %/yr": round(float(row["cagr_pct"]), 2),
                }
            )
    st.dataframe(pd.DataFrame(cat_rows), use_container_width=True)

    st.subheader("Has pay kept up with prices?")
    st.image(
        str(CHARTS_DIR / "03_real_earnings.png"),
        caption="Nominal vs. real hourly earnings, Mar 2006 = 100. Source: BLS via FRED.",
    )

    st.subheader("What does the $100 basket cost now?")
    st.image(
        str(CHARTS_DIR / "04_basket_cost.png"),
        caption="Fixed-basket illustration (see assumptions). Source: BLS via FRED.",
    )
    basket_input = st.slider(
        "Your basket in Mar 2006 ($)",
        min_value=10,
        max_value=1000,
        value=100,
        step=10,
    )
    scaled = basket_input * basket_now / 100.0
    st.write(
        f"A basket that cost **\\${basket_input} in Mar 2006** costs "
        f"**\\${scaled:,.2f} in Oct 2026** "
        f"(+{latest_cum:.1f}%, fixed-basket illustration)."
    )

    st.subheader("Assumptions (please read)")
    for item in ASSUMPTIONS:
        st.write(f"- {item}")

    st.caption(
        "Source: U.S. Bureau of Labor Statistics via FRED "
        "(Federal Reserve Bank of St. Louis). "
        "This dashboard is descriptive, not investment advice."
    )


if __name__ == "__main__":
    main()
