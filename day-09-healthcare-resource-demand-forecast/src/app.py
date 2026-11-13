"""Day 9 — Healthcare Resource Demand Forecast (Streamlit).

How many respiratory ED visits should a hospital system expect over the
next 8 weeks, with what uncertainty, and what staffing posture does each
forecast level imply? All numbers come from the committed processed
CSVs — the app never fetches live data and never fits a model.

Run: streamlit run src/app.py  (from the project root)
Data: data/processed/*.csv — offline, no network, no API.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Streamlit runs app.py as a script (script dir on sys.path, not the
# project root), so make the project root importable for `src.*`.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHARTS_DIR = PROJECT_ROOT / "outputs" / "charts"
ATTRIBUTION = (
    "CDC National Syndromic Surveillance Program (NSSP), Emergency "
    "Department Visits — COVID-19, Flu, RSV, via CDC Open Data "
    "(data.cdc.gov/resource/vutn-jzwm). U.S. Department of Health and "
    "Human Services, COVID-19 Reported Patient Impact and Hospital "
    "Capacity by State Timeseries, via healthdata.gov (resource "
    "g62h-syeh). Both sources are US federal public-domain data."
)
BED_END_DATE = "2024-04-27"
STAFFING = {
    "Low": ("Baseline roster", "—"),
    "Moderate": ("Baseline staffing (monitor)", "—"),
    "High": ("+10% rostered shifts", "+10%"),
    "Surge": ("+25% rostered shifts + elective-deferral trigger", "+25%"),
}


@st.cache_data
def load_all():
    record = json.loads((PROCESSED_DIR / "data_source.json").read_text())
    national = pd.read_csv(PROCESSED_DIR / "national_combined.csv")
    states = pd.read_csv(PROCESSED_DIR / "state_combined.csv")
    bed = pd.read_csv(PROCESSED_DIR / "bed_utilisation.csv")
    forecast = pd.read_csv(PROCESSED_DIR / "forecast.csv")
    backtest = pd.read_csv(PROCESSED_DIR / "backtest.csv")
    bands = pd.read_csv(PROCESSED_DIR / "band_history.csv")
    return record, national, states, bed, forecast, backtest, bands


RECORD, NATIONAL, STATES, BED, FORECAST, BACKTEST, BANDS = load_all()

st.set_page_config(page_title="Healthcare Resource Demand Forecast", layout="wide")
st.title("Healthcare Resource Demand Forecast")
st.markdown(
    "How many respiratory ED visits should a hospital system expect over "
    "the next 8 weeks, with what uncertainty — and what staffing posture "
    "does each forecast level imply? The forecast is published with 80% "
    "and 95% prediction intervals, backtested honestly against a "
    "seasonal-naïve baseline, and translated into demand bands with a "
    "staffing scenario for each band."
)
st.warning(
    "Analytical exercise on public aggregate surveillance data. **Not a "
    "clinical or operational decision tool** — never use it to make care "
    "or capacity decisions."
)
if RECORD.get("synthetic"):
    st.warning("SYNTHETIC DATA — labelled fallback, not real CDC/HHS values.")

latest = RECORD["latest_national_week"]
published = RECORD["forecast"]["published_method"].replace("_", " ").title()
col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Latest Combined %",
    f"{latest['combined_pct']:.1f}%",
    f"week ending {latest['week_end']}",
)
col2.metric(
    "8-week forecast (final week)",
    f"{FORECAST['forecast_pct'].iloc[-1]:.2f}%",
    f"week ending {FORECAST['week_end'].iloc[-1]}",
)
col3.metric(
    "Observed max (2023–2026)",
    f"{RECORD['forecast']['observed_max_combined_pct']:.1f}%",
    "Surge occurred 18 of 161 weeks",
)
col4.metric(
    "Backtest mean RMSE",
    f"{RECORD['forecast']['mean_rmse'][RECORD['forecast']['published_method']]:.2f} pp",
    f"beats naïve ({RECORD['forecast']['mean_rmse']['seasonal_naive']:.2f} pp)",
)
st.caption(
    f"Latest week split: COVID-19 {latest['covid_pct']:.1f}%, Influenza "
    f"{latest['flu_pct']:.1f}%, RSV {latest['rsv_pct']:.1f}% — Combined is "
    f"the sum of the three (same denominator: all ED visits). National "
    f"series: {RECORD['national_weeks']} weeks, "
    f"{RECORD['nssp_week_range'][0]} → {RECORD['nssp_week_range'][1]}."
)

st.header("8-week forecast with prediction intervals")
st.image(
    str(CHARTS_DIR / "01_forecast.png"),
    caption="National weekly Combined % + 8-week forecast (shaded 80% / 95% intervals).",
    width="stretch",
)
st.dataframe(FORECAST, width="stretch")
st.markdown(
    f"Published method: **{published}** (lowest mean backtest RMSE). "
    f"Intervals: residual bootstrap, seed 42, 1,000 paths. Forecast bands: "
    f"{', '.join(FORECAST['band'].tolist())}. The final forecast weeks "
    f"exceed the observed historical maximum "
    f"({RECORD['forecast']['observed_max_combined_pct']:.1f}%) — the "
    f"additive-trend Holt-Winters model extrapolates the steep autumn "
    f"rise, so treat the outer weeks with caution; the intervals widen "
    f"accordingly."
)

st.header("How good is the forecast? Rolling-origin backtest")
st.image(
    str(CHARTS_DIR / "02_backtest.png"),
    caption="Backtest RMSE and 80%-interval coverage by origin.",
    width="stretch",
)
st.dataframe(BACKTEST, width="stretch")
mean_cov = BACKTEST.groupby("method")["coverage_80"].mean()
st.markdown(
    f"Mean 80%-interval coverage: Holt-Winters **{mean_cov['holt_winters']:.0%}** "
    f"vs seasonal naïve **{mean_cov['seasonal_naive']:.0%}** (target ≈ 80%). "
    f"Holt-Winters wins 2 of the 3 origins on RMSE; seasonal naïve wins "
    f"the origin-8 window. MAPE is reported in backtest.csv alongside "
    f"RMSE/MAE — it inflates when Combined % sits near 1–2% in summer, "
    f"so judge the methods on RMSE."
)

st.header("Demand bands — history and geography")
st.image(
    str(CHARTS_DIR / "03_demand_bands.png"),
    caption="National history coloured by demand band + top-5 states.",
    width="stretch",
)
counts = RECORD["forecast"]["band_counts_history"]
st.markdown(
    f"Historical band occurrence (161 weeks): Low **{counts['Low']}**, "
    f"Moderate **{counts['Moderate']}**, High **{counts['High']}**, Surge "
    f"**{counts['Surge']}**. Surge (>6%) is a real historical level — it "
    f"occurred in {counts['Surge']} weeks, most recently in the "
    f"2025–26 winter peak."
)
state_choice = st.selectbox(
    "Compare a state with the national series",
    options=sorted(STATES["geography"].unique()),
    index=sorted(STATES["geography"].unique()).index("Florida"),
)
state_series = STATES[STATES["geography"] == state_choice].copy()
state_series["week_end"] = pd.to_datetime(state_series["week_end"])
national_series = NATIONAL.copy()
national_series["week_end"] = pd.to_datetime(national_series["week_end"])
compare = pd.DataFrame(
    {
        "week_end": national_series["week_end"],
        "National": national_series["combined_pct"],
        state_choice: state_series.set_index("week_end")["combined_pct"]
        .reindex(national_series["week_end"])
        .to_numpy(),
    }
).set_index("week_end")
st.line_chart(compare, width="stretch")
st.caption(
    "State Combined % uses the same construction (sum of the three "
    "pathogen percentages). Weeks where a state reported no value for a "
    "pathogen are missing, never 0 — Iowa has reported nothing since "
    "2026-07-04, Delaware and Georgia nothing since 2026-10-17."
)

st.header("Capacity side — bed utilisation and staffing scenario")
st.image(
    str(CHARTS_DIR / "04_bed_capacity.png"),
    caption="National bed utilisation (historical) + staffing scenario table.",
    width="stretch",
)
st.markdown(
    f"National weekly inpatient bed utilisation, "
    f"{BED['week_end'].iloc[0]} → {BED['week_end'].iloc[-1]} "
    f"(**series ends {BED_END_DATE}** — reporting ended; this is a "
    f"historical record, not current capacity). Latest week "
    f"({BED['week_end'].iloc[-1]}): "
    f"**{BED['bed_utilisation'].iloc[-1] * 100:.1f}%** of beds in use, "
    f"ICU occupancy **{BED['icu_occupancy'].iloc[-1] * 100:.1f}%**. "
    f"Early-2020 weeks reflect few reporting states (3–38); the 2020 "
    f"segment is thinly reported. The dashed 8-week extension in the "
    f"chart re-runs the same Holt-Winters machinery on the historical "
    f"series for illustration only."
)
staffing_rows = [
    {"Band": band, "Staffing posture": posture, "Uplift": uplift}
    for band, (posture, uplift) in STAFFING.items()
]
st.dataframe(pd.DataFrame(staffing_rows), width="stretch")
st.markdown(
    "**PLANNING ASSUMPTIONS — not measured data.** The +10% / +25% "
    "uplifts are round-number planning assumptions keyed to the demand "
    "band; no source is cited for them because none exists."
)

st.header("Volume converter — forecast % → expected visits")
st.markdown(
    "Convert the forecast share into expected respiratory visits for a "
    "hospital system of a given size. Both inputs are **planning "
    "assumptions, not measured numbers**."
)
volume = st.number_input(
    "Weekly ED volume (all visits/week) — planning assumption",
    min_value=100,
    max_value=100_000,
    value=1000,
    step=100,
)
admission_rate = st.slider(
    "Admission rate among respiratory ED visits (%) — planning assumption",
    min_value=0,
    max_value=50,
    value=15,
)
conv = FORECAST[["week_end", "forecast_pct", "band"]].copy()
conv["expected_respiratory_visits"] = (
    (conv["forecast_pct"] / 100 * volume).round(0).astype(int)
)
conv["expected_admissions"] = (
    (conv["expected_respiratory_visits"] * admission_rate / 100).round(0).astype(int)
)
st.dataframe(conv, width="stretch")
st.caption(
    f"At {volume:,} ED visits/week and a {admission_rate}% admission "
    f"rate, the peak forecast week ({conv.loc[conv['forecast_pct'].idxmax(), 'week_end']}, "
    f"{conv['forecast_pct'].max():.2f}%) implies "
    f"{conv['expected_respiratory_visits'].max():,} respiratory visits "
    f"and {conv['expected_admissions'].max():,} admissions that week. "
    f"Change the inputs above to re-run the conversion."
)

st.header("Methods and limitations")
st.markdown("""
- **Target:** national weekly Combined respiratory ED share = COVID-19% + Influenza% + RSV% (NSSP, `geography = "United States"`). There is no Combined value in the source data; the sum is valid because all three share the same denominator (all ED visits).
- **Methods:** seasonal naïve (same week last year) vs Holt-Winters, additive trend + additive seasonality, period 52, no tuning grid. Published forecast = lowest mean backtest RMSE. SARIMA was kept out of scope (plan §11).
- **Intervals:** residual bootstrap, seed 42, 1,000 paths; 80% = 10th/90th percentiles, 95% = 2.5th/97.5th.
- **Backtest:** 3 rolling origins (train ends 12 / 8 / 4 weeks before the end), 4-week horizons; RMSE, MAE, MAPE, 80%-interval coverage.
- **Beds:** national weekly inpatient bed utilisation = Σ beds used / Σ beds per week (state-sum ratio, not the mean of per-state ratios). Only state-days with full coverage enter the sums (86.36% of state-days; 11,145 dropped). Series ends 2024-04-27.
- **Limits:** the ED series is a *share* of visits, not a count — visit numbers come only from the user-entered volume assumption. The forecast's outer weeks exceed the observed historical maximum (10.4%), so treat them as a severe-season scenario, not a prediction to plan rosters on alone. MAPE inflates in low summer weeks. The bed series is historical, not current capacity.
""")
st.markdown("---")
st.caption(ATTRIBUTION)
st.caption(
    "Companion guide: "
    "https://www.cdc.gov/ncird/surveillance/respiratory-illnesses/"
    "index.html#companion-guide"
)
