"""Day 17 Drought Impact Analyzer: Streamlit dashboard.

Reads processed CSVs only. Shows the drought trend, the drought-yield
relationship, the county map and ranking, and the AR(1) DSCI forecast,
with the four limitations stated on the page.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
CHARTS_DIR = ROOT / "outputs" / "charts"

st.set_page_config(page_title="Drought Impact Analyzer — Day 17", layout="wide")
st.title("🌵 Drought Impact Analyzer — Corn Belt, 2000–2025")
st.markdown(
    "Relating US Drought Monitor severity and precipitation anomalies to "
    "US maize yield — across years nationally and across counties in Iowa "
    "and Illinois."
)

annual = pd.read_csv(PROCESSED_DIR / "annual_drought_yield.csv")
correlations = pd.read_csv(PROCESSED_DIR / "correlation_results.csv")
county_summary = pd.read_csv(PROCESSED_DIR / "county_summary.csv")
county_year = pd.read_csv(PROCESSED_DIR / "county_year.csv")
forecast = pd.read_csv(PROCESSED_DIR / "ar1_forecast.csv")

worst = annual.loc[annual["gs_dsci_mean"].idxmax()]
dsci_row = correlations.loc[correlations["variable"] == "gs_dsci_mean"].iloc[0]
precip_row = correlations.loc[correlations["variable"] == "gs_precip_anomaly_mm"].iloc[
    0
]
forecast_2026 = forecast.loc[forecast["year"] == 2026].iloc[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Worst drought year",
    str(int(worst["year"])),
    f"GS DSCI {float(worst['gs_dsci_mean']):.0f}",
)
col2.metric(
    "DSCI vs detrended yield",
    f"r = {float(dsci_row['pearson_r']):.2f}",
    f"p = {float(dsci_row['p_value']):.3g}",
)
col3.metric(
    "Rain anomaly vs yield",
    f"r = {float(precip_row['pearson_r']):.2f}",
    f"p = {float(precip_row['p_value']):.3g}",
)
col4.metric(
    "2026 DSCI forecast (AR(1))",
    f"{float(forecast_2026['ar1_forecast']):.0f}",
    "statistical extrapolation",
)

st.sidebar.header("Explore")
year_min, year_max = st.sidebar.slider(
    "Year range (annual table)",
    min_value=int(annual["year"].min()),
    max_value=int(annual["year"].max()),
    value=(int(annual["year"].min()), int(annual["year"].max())),
)
shown = annual[(annual["year"] >= year_min) & (annual["year"] <= year_max)]
state_choice = st.sidebar.selectbox(
    "County ranking state", ["Both states", "Iowa", "Illinois"]
)

st.header("Drought severity trend")
st.image(str(CHARTS_DIR / "01_dsci_trend.png"), use_container_width=True)
st.dataframe(
    shown[
        [
            "year",
            "yield_t_per_ha",
            "yield_resid_t_per_ha",
            "gs_dsci_mean",
            "gs_precip_anomaly_mm",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

st.header("Drought vs yield")
st.image(str(CHARTS_DIR / "02_drought_vs_yield.png"), use_container_width=True)
st.dataframe(correlations, use_container_width=True, hide_index=True)
st.markdown(
    "Primary result: correlations are against the **detrended** yield "
    "residual (the technology trend removed). Raw-yield correlations are "
    "in the same table for transparency."
)

st.header("Precipitation anomalies")
st.image(str(CHARTS_DIR / "03_precip_anomaly.png"), use_container_width=True)

st.header("County map: where drought hit hardest")
st.image(str(CHARTS_DIR / "04_county_map.png"), use_container_width=True)
ranking = county_summary
if state_choice == "Iowa":
    ranking = county_summary[county_summary["state"] == "IA"]
elif state_choice == "Illinois":
    ranking = county_summary[county_summary["state"] == "IL"]
st.dataframe(
    ranking.head(15)[
        ["county", "state", "mean_d2plus_pct", "worst_year", "worst_year_d2plus_pct"]
    ],
    use_container_width=True,
    hide_index=True,
)

st.header("2026 DSCI forecast (AR(1))")
# Missing values (2026 actual, 2025 interval) display as "—", not "None".
forecast_display = forecast.fillna("—")
st.dataframe(forecast_display, use_container_width=True, hide_index=True)
st.markdown(
    "The 2026 number is a statistical extrapolation from the annual "
    "growing-season DSCI series — **not a weather forecast**."
)

st.header("Limitations — read before quoting any number")
st.markdown(
    "- **National yield, 2-state drought/weather.** Yield is the USA "
    "national figure; drought and weather are Iowa + Illinois (~35% of "
    "US corn output) — a proxy, not a national average.\n"
    "- **No county yields.** USDA Quick Stats needs an API key, so the "
    "county analysis is drought severity by county; the yield "
    "relationship is by year at state/national level.\n"
    "- **Association, not causation.** Drought moving with yield is a "
    "statistical association.\n"
    "- **Small sample — 26 annual rows.** Correlations carry wide "
    "uncertainty; p-values are reported alongside every r."
)
st.markdown(
    "Sources: U.S. Drought Monitor (NDMC/USDA/NOAA); yield: FAO via Our "
    "World in Data (CC BY 4.0); weather: Open-Meteo ERA5 archive "
    "(CC BY 4.0); county boundaries: US Census Bureau via plotly datasets."
)
