"""Day 18 Agricultural Commodity Price Analyzer: Streamlit dashboard.

Reads processed CSVs only. Shows price levels, seasonality, volatility
and shocks, the weather/drought join, the Holt-Winters maize forecast
and the 2012 county drought map, with the four limitations stated on
the page.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
CHARTS_DIR = ROOT / "outputs" / "charts"

st.set_page_config(
    page_title="Agricultural Commodity Price Analyzer — Day 18", layout="wide"
)
st.title("🌾 Agricultural Commodity Price Analyzer — 1992–2026")
st.markdown(
    "Monthly IMF benchmark prices for maize, wheat and soybeans via FRED — "
    "seasonality, variability and past shocks, joined to Corn Belt "
    "growing-season weather and drought."
)

monthly = pd.read_csv(PROCESSED_DIR / "monthly_prices.csv", parse_dates=["date"])
annual = pd.read_csv(PROCESSED_DIR / "annual_summary.csv")
seasonality = pd.read_csv(PROCESSED_DIR / "seasonality.csv")
shocks = pd.read_csv(PROCESSED_DIR / "shocks.csv", parse_dates=["date"])
correlations = pd.read_csv(PROCESSED_DIR / "correlations.csv")
forecast = pd.read_csv(PROCESSED_DIR / "forecast_maize.csv", parse_dates=["date"])
county = pd.read_csv(PROCESSED_DIR / "county_shock_2012.csv")
provenance = json.loads((PROCESSED_DIR / "data_source.json").read_text())
backtest = provenance["backtest"]

maize = monthly[monthly["commodity"] == "maize"].sort_values("date")
latest = maize.iloc[-1]
maize_2025 = annual[(annual["commodity"] == "maize") & (annual["year"] == 2025)].iloc[0]
worst_shock = shocks.loc[shocks["log_return"].abs().idxmax()]

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Latest maize price (Sep 2026)",
    f"${float(latest['price_usd_per_t']):.2f}/t",
    "IMF benchmark, partial year",
)
col2.metric(
    "Maize 2025 mean price",
    f"${float(maize_2025['annual_mean_price']):.2f}/t",
    f"{float(maize_2025['yoy_pct_change']):+.1f}% YoY",
)
col3.metric(
    "Shock months flagged",
    str(len(shocks)),
    "3 commodities combined",
)
col4.metric(
    "Largest single-month move",
    f"{float(worst_shock['log_return']) * 100:+.1f}%",
    f"{worst_shock['date'].strftime('%Y-%m')} "
    f"{str(worst_shock['commodity']).title()}",
)

st.sidebar.header("Explore")
commodity_choice = st.sidebar.selectbox(
    "Commodity (annual table)", ["maize", "wheat", "soybeans"]
)
year_min, year_max = st.sidebar.slider(
    "Year range (annual table)",
    min_value=int(annual["year"].min()),
    max_value=int(annual["year"].max()),
    value=(int(annual["year"].min()), int(annual["year"].max())),
)
shown = annual[
    (annual["commodity"] == commodity_choice)
    & (annual["year"] >= year_min)
    & (annual["year"] <= year_max)
]

st.header("Price levels, 1992–2026")
st.image(str(CHARTS_DIR / "01_price_levels.png"), width="stretch")
st.dataframe(
    shown[
        [
            "year",
            "annual_mean_price",
            "annual_max_price",
            "annual_min_price",
            "yoy_pct_change",
        ]
    ],
    width="stretch",
)

st.header("Seasonality")
st.image(str(CHARTS_DIR / "02_seasonality.png"), width="stretch")
st.dataframe(
    seasonality[seasonality["window"] == "full"][
        ["commodity", "month", "month_mean_price", "seasonal_index"]
    ],
    width="stretch",
)

st.header("Volatility and shocks")
st.image(str(CHARTS_DIR / "03_volatility_shocks.png"), width="stretch")
st.dataframe(
    shocks.sort_values("log_return", key=lambda s: s.abs(), ascending=False).head(10)[
        ["date", "commodity", "price_usd_per_t", "log_return"]
    ],
    width="stretch",
)

st.header("Weather / drought join (annual, 2000–2025)")
st.dataframe(correlations, width="stretch")
st.markdown(
    "No annual association is significant: every p-value is above 0.46. "
    "Global benchmark prices move on global supply and demand, not on "
    "two-state Corn Belt weather in the same year — the 2012 drought "
    "spike shows in the *monthly* moves (maize +22% in July 2012), not "
    "in the annual year-on-year join."
)

st.header("Maize forecast — Holt-Winters, 12 months")
st.dataframe(forecast, width="stretch")
st.markdown(
    "Statistical extrapolation from the monthly benchmark series, not a "
    "market prediction. Backtest (3 origins): Holt-Winters mean RMSE "
    f"${float(backtest['rmse_hw_mean']):.2f}/t vs "
    f"${float(backtest['rmse_seasonal_naive_mean']):.2f}/t for the "
    "seasonal-naïve baseline."
)

st.header("Where the 2012 drought hit hardest")
st.image(str(CHARTS_DIR / "04_county_map.png"), width="stretch")
st.dataframe(
    county.head(10)[["rank", "county", "state", "gs_d2plus_pct_2012"]],
    width="stretch",
)

st.header("Methods and limitations")
st.markdown("""
- **Prices are IMF global benchmarks via FRED** (PMAIZMTUSDM, PWHEAMTUSDM,
  PSOYBUSDM), not USDA NASS farm-gate prices — the USDA Quick Stats API
  needs a key and none was available to this run.
- **Latest price month is 2026-09** (IMF source lags ~2 months); 2026 is a
  partial year and is excluded from annual means and the weather/drought
  join.
- **Weather and drought are Iowa + Illinois growing-season means** — a
  proxy for the Corn Belt crop, not a national average. Correlations use
  26 annual points; report p-values, never causal claims.
- **The forecast is a trend extrapolation**, not a market prediction.
- **Log returns** are ln(P_t / P_{t-1}) on monthly prices. A shock month
  is |log return| >= 2x the rolling 24-month return standard deviation.
- Sources: FRED (Federal Reserve Bank of St. Louis), IMF Primary
  Commodity Prices; weather: Open-Meteo ERA5 archive (CC BY 4.0);
  drought: U.S. Drought Monitor (NDMC/USDA/NOAA); county boundaries:
  US Census Bureau via plotly datasets (public domain).
""")
