"""Day 7 — Disease Prevalence Dashboard (Streamlit).

Public-health maps and geographic comparison of CDC PLACES county
estimates for six chronic conditions (2022–2023). All rates are crude
prevalence, % of adults 18+, model-based estimates from BRFSS — not
counted cases. State rates are population-weighted; county means are
never presented as state rates.

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

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import streamlit as st

from src.state_map import state_map_figure

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHARTS_DIR = PROJECT_ROOT / "outputs" / "charts"

MEASURE_LABELS = {
    "DIABETES": "Diabetes",
    "COPD": "COPD",
    "CASTHMA": "Current asthma",
    "CHD": "Coronary heart disease",
    "STROKE": "Stroke",
    "OBESITY": "Obesity",
}
SLUGS = {
    "DIABETES": "diabetes",
    "COPD": "copd",
    "CASTHMA": "asthma",
    "CHD": "chd",
    "STROKE": "stroke",
    "OBESITY": "obesity",
}
ATTRIBUTION = (
    "Source: CDC PLACES: Local Data for Better Health, County Data, "
    "2025 release (2023 estimates) and 2024 release (2022 estimates), via "
    "CDC Open Data (data.cdc.gov). Model-based estimates from BRFSS."
)


@st.cache_data
def load_all() -> tuple[dict, pd.DataFrame, dict, dict]:
    prevalence = {}
    change = {}
    for measure, slug in SLUGS.items():
        prevalence[measure] = pd.read_csv(
            PROCESSED_DIR / f"prevalence_{slug}.csv", dtype={"year": str}
        )
        change[measure] = pd.read_csv(PROCESSED_DIR / f"change_{slug}.csv")
    state = pd.read_csv(PROCESSED_DIR / "state_prevalence.csv", dtype={"year": str})
    record = json.loads((PROCESSED_DIR / "data_source.json").read_text())
    us_states = json.loads((PROCESSED_DIR / "us_states.geojson").read_text())
    return prevalence, state, change, record, us_states


PREVALENCE, STATE, CHANGE, RECORD, US_STATES = load_all()

st.set_page_config(page_title="Disease Prevalence Dashboard", layout="wide")
st.title("Disease Prevalence Dashboard")
st.markdown(
    "Estimated prevalence of six chronic conditions across US counties and "
    "states, 2022–2023. Rates are **crude prevalence, % of adults aged 18+** "
    "— model-based estimates from survey data, not counted cases."
)
if RECORD.get("synthetic"):
    st.warning("SYNTHETIC DATA — labelled fallback, not CDC values.")

measure = st.sidebar.selectbox(
    "Condition", options=list(MEASURE_LABELS), format_func=lambda m: MEASURE_LABELS[m]
)
year = st.sidebar.selectbox("Year", options=["2023", "2022"])
label = MEASURE_LABELS[measure]
prev = PREVALENCE[measure]
this_year = prev[prev["year"] == year]
nat = RECORD["national_weighted_vs_us_row"][f"{measure}_{year}"]["weighted"]
us_row = RECORD["national_weighted_vs_us_row"][f"{measure}_{year}"]["us_row"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("National rate (weighted)", f"{nat:.2f}%")
col2.metric("Median county", f"{this_year['data_value'].median():.1f}%")
col3.metric("Counties with data", f"{len(this_year):,}")
col4.metric("CDC published US figure", f"{us_row:.1f}%")
st.caption(
    "The national rate is population-weighted over counties with published "
    "values. The CDC figure covers all counties including suppressed ones — "
    f"the gap here is {nat - us_row:+.2f} pp. County medians are higher than "
    "national rates because small rural counties tend to have higher "
    "prevalence and count equally in a median."
)

st.header(f"{label} — where is it highest?")
state_year = STATE[(STATE["measureid"] == measure) & (STATE["year"] == year)]
fig_map = state_map_figure(
    state_year, US_STATES, f"{label} by state, {year} (population-weighted)"
)
st.pyplot(fig_map, width="stretch")
plt.close(fig_map)
st.caption(
    "State colour is the population-weighted rate of its counties — not the "
    "average of county percentages. Grey states have no county rows in this "
    "release (Kentucky and Pennsylvania in 2023)."
)

geo = this_year.dropna(subset=["lon", "lat"])
fig_bubble = px.scatter(
    geo,
    x="lon",
    y="lat",
    size="est_cases",
    color="data_value",
    color_continuous_scale="Reds",
    size_max=22,
    labels={
        "lon": "Longitude",
        "lat": "Latitude",
        "data_value": "Prevalence (%)",
        "est_cases": "Est. cases",
    },
    title=f"{label} by county, {year} — dot size = estimated adult cases, "
    "colour = prevalence",
    hover_data={"locationname": True, "stateabbr": True, "data_value": ":.1f"},
)
fig_bubble.update_layout(
    xaxis={"range": [-126, -65], "showgrid": False, "zeroline": False},
    yaxis={"range": [24, 50], "showgrid": False, "zeroline": False},
    height=520,
)
st.plotly_chart(fig_bubble, width="stretch")
st.caption(
    "County centroids plotted by longitude/latitude. Alaska and Hawaii fall "
    "outside this longitude window and are not shown here (their counties "
    "are in the tables and charts)."
)

top = this_year.nlargest(10, "data_value")
bottom = this_year.nsmallest(10, "data_value")
c1, c2 = st.columns(2)
c1.subheader("Highest estimated prevalence")
c1.dataframe(
    top[["locationname", "stateabbr", "data_value", "est_cases"]].rename(
        columns={
            "locationname": "County",
            "stateabbr": "State",
            "data_value": "Prevalence (%)",
            "est_cases": "Est. cases",
        }
    ),
    width="stretch",
    hide_index=True,
)
c2.subheader("Lowest estimated prevalence")
c2.dataframe(
    bottom[["locationname", "stateabbr", "data_value", "est_cases"]].rename(
        columns={
            "locationname": "County",
            "stateabbr": "State",
            "data_value": "Prevalence (%)",
            "est_cases": "Est. cases",
        }
    ),
    width="stretch",
    hide_index=True,
)
st.caption(
    "County rankings are a starting point for questions, not a verdict: "
    "small counties have wide confidence intervals (median width "
    f"{RECORD['median_ci_width_pp'][f'{measure}_{year}']} pp for {label} "
    f"in {year})."
)

st.header("Did it move from 2022 to 2023?")
ch = CHANGE[measure]
median_pp = ch["pp_change"].median()
up = float((ch["pp_change"] > 0).mean() * 100)
down = float((ch["pp_change"] < 0).mean() * 100)
st.markdown(
    f"On the **{len(ch):,} counties present in both years**, the median "
    f"county moved **{median_pp:+.2f} percentage points** for {label.lower()}: "
    f"{up:.1f}% of counties rose, {down:.1f}% fell. Kentucky and "
    "Pennsylvania are excluded — they have no 2023 rows — so this change is "
    "computed on the same counties in both years, not on two different maps."
)
movers_up = ch.nlargest(5, "pp_change")
movers_down = ch.nsmallest(5, "pp_change")
m1, m2 = st.columns(2)
m1.subheader("Largest rises (pp)")
m1.dataframe(
    movers_up[
        ["locationname", "stateabbr", "value_2022", "value_2023", "pp_change"]
    ].rename(
        columns={
            "locationname": "County",
            "stateabbr": "State",
            "value_2022": "2022 (%)",
            "value_2023": "2023 (%)",
            "pp_change": "Change (pp)",
        }
    ),
    width="stretch",
    hide_index=True,
)
m2.subheader("Largest falls (pp)")
m2.dataframe(
    movers_down[
        ["locationname", "stateabbr", "value_2022", "value_2023", "pp_change"]
    ].rename(
        columns={
            "locationname": "County",
            "stateabbr": "State",
            "value_2022": "2022 (%)",
            "value_2023": "2023 (%)",
            "pp_change": "Change (pp)",
        }
    ),
    width="stretch",
    hide_index=True,
)

st.header("Charts")
st.image(str(CHARTS_DIR / "01_state_ranking.png"), width="stretch")
st.image(str(CHARTS_DIR / "02_county_distribution.png"), width="stretch")
st.image(str(CHARTS_DIR / "03_change_2022_2023.png"), width="stretch")
st.image(str(CHARTS_DIR / "04_measure_comparison.png"), width="stretch")

st.header("Methods, definitions & coverage — read this first")
st.markdown("""
- **What a rate means:** crude prevalence — the estimated % of adults aged
  18+ with the condition, as modelled by CDC PLACES from BRFSS survey data.
  It is an estimate with a confidence interval, not a count of diagnosed
  people.
- **Denominators:** estimated cases = prevalence × adult (18+) population
  of the county. State and national rates are population-weighted
  (Σ cases / Σ adults). A simple average of county percentages would give a
  county of 1,000 adults the same weight as one of 1,000,000 — that is never
  done here.
- **Crude, not age-adjusted:** crude rates describe the actual burden in
  each place's real population. Age-adjusted rates answer a different
  question (what if every place had the same age mix) and would give
  different numbers.
- **Coverage gaps:** the 2025 release (2023) has no rows at all for
  Kentucky (120 counties) or Pennsylvania (67 counties), and one county —
  Loving County, TX — has its 2023 value suppressed (too small to publish).
  So 2023 covers 2,956 counties vs 3,144 in 2022. Year-over-year changes
  use only the 2,956 matched counties; national 2022→2023 moves are partly
  compositional.
- **Precision:** the median county confidence-interval width for
  diabetes in 2023 is 3.9 pp — year-to-year moves smaller than that in a
  single small county should not be over-read.
""")
st.caption(ATTRIBUTION)
