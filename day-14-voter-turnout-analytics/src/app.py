"""Streamlit dashboard for Day 14 — Voter Turnout Analytics.

Loads processed CSVs + data_source.json only (offline). Every surface
states the coverage limits: descriptive only (no predictive model),
state level only (no county map), VEP is the primary denominator
(VAP reported alongside, registered-voter figures are a cross-check
only), comparisons within cycle type only, and no causal claims.
"""

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
CHARTS = ROOT / "outputs" / "charts"

LIMITS_BANNER = (
    "Descriptive only — no predictive model, no causal claims. State level only "
    "(no county map). VEP turnout is the primary metric; VAP turnout is reported "
    "alongside it, never as a substitute. Comparisons are within cycle type only. "
    "2024 figures are the lab's preliminary v0.4 release; pre-2010 national "
    "figures are estimated, and national VEP turnout is not reported in the file "
    "for 1980–1996."
)
ATTRIBUTION = (
    "Source: Michael McDonald, University of Florida Election Lab, General "
    "Election Turnout Rates 1980–2022 v1.2 and 2024 General Election Turnout "
    "Rates v0.4 (https://election.lab.ufl.edu/voter-turnout/), CC BY 4.0. "
    "Retrieved 2026-11-21."
)
UF_LINK = "https://election.lab.ufl.edu/voter-turnout/"
EAC_LINK = "https://www.eac.gov/research-and-data/studies-and-reports"
CENSUS_LINK = "https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html"


def fmt_rate(x: float) -> str:
    """Format a turnout rate as '64.30%' (or '—' when missing)."""
    if pd.isna(x):
        return "—"
    return f"{float(x):.2f}%"


def fmt_pp(x: float) -> str:
    """Format a percentage-point change with its sign (or '—' when missing)."""
    if pd.isna(x):
        return "—"
    return f"{float(x):+.2f} pp"


@st.cache_data
def load_data() -> dict[str, Any]:
    """Load the processed tables and the provenance record (offline)."""
    record = json.loads((PROC / "data_source.json").read_text(encoding="utf-8"))
    return {
        "record": record,
        "long": pd.read_csv(PROC / "turnout_long.csv"),
        "national": pd.read_csv(PROC / "national_series.csv"),
        "state_2024": pd.read_csv(PROC / "state_2024.csv"),
        "correlations": pd.read_csv(PROC / "correlations.csv"),
        "outliers": pd.read_csv(PROC / "outliers.csv"),
    }


def main() -> None:
    """Render the dashboard."""
    st.set_page_config(page_title="Voter Turnout Analytics", layout="wide")
    data = load_data()
    national = data["national"]
    state_2024 = data["state_2024"]
    states = state_2024[~state_2024["is_national"].astype(bool)].copy()
    us_row = state_2024[state_2024["is_national"].astype(bool)].iloc[0]
    row_2022 = national[national["year"] == 2022].iloc[0]

    st.title("Voter Turnout Analytics — US General Elections 1980–2024")
    st.caption(
        "How turnout differs across states and over time, and which demographic "
        "indicators move with it — described only, with every number traceable "
        "to its source."
    )
    st.warning(LIMITS_BANNER)

    st.subheader(
        "Headline figures (VEP turnout — ballots counted ÷ voting-eligible population)"
    )
    top_state = states.sort_values("vep_turnout_rate", ascending=False).iloc[0]
    bottom_state = states.sort_values("vep_turnout_rate").iloc[0]
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric(
        "2024 national VEP turnout",
        fmt_rate(float(us_row["vep_turnout_rate"])),
        delta="−1.69 pp vs 2020",
    )
    col2.metric(
        "2022 midterm VEP turnout",
        fmt_rate(float(row_2022["vep_turnout_rate"])),
        delta="−3.93 pp vs 2018",
    )
    col3.metric(
        "Highest 2024 state",
        fmt_rate(float(top_state["vep_turnout_rate"])),
        delta=str(top_state["state"]),
    )
    col4.metric(
        "Lowest 2024 state",
        fmt_rate(float(bottom_state["vep_turnout_rate"])),
        delta=str(bottom_state["state"]),
    )
    col5.metric("Jurisdictions", "51", delta="50 states + DC")

    st.subheader("2024 turnout map")
    st.image(str(CHARTS / "01_turnout_map_2024.png"), width="stretch")
    st.caption(
        "State choropleth, 2024 VEP turnout. Geometry: U.S. Census Bureau "
        f"cartographic boundary file. [Source: UF Election Lab]({UF_LINK})"
    )

    st.subheader("Turnout over time")
    st.image(str(CHARTS / "02_turnout_over_time.png"), width="stretch")
    st.caption(
        "National VEP turnout by election year, split by cycle type. Pre-2010 "
        "points are estimated; 1980–1996 national VEP turnout is not reported "
        "in the file."
    )

    st.subheader("State ranking — 2024 VEP turnout")
    st.image(str(CHARTS / "03_state_ranking_2024.png"), width="stretch")
    ranking = states.sort_values("rank_vep")[
        [
            "rank_vep",
            "state",
            "state_abv",
            "vep_turnout_rate",
            "vap_turnout_rate",
            "pp_change_vs_2020",
        ]
    ].copy()
    ranking.columns = [
        "Rank",
        "State",
        "Abbr",
        "VEP turnout (%)",
        "VAP turnout (%)",
        "pp change vs 2020",
    ]
    st.dataframe(ranking, width="stretch")
    st.caption(
        "Rank 1 = highest 2024 VEP turnout. pp change vs 2020 compares two "
        "presidential years (like with like). US total 64.30% is shown as a "
        "reference line in the chart, never ranked."
    )

    st.subheader("National series")
    series = national.copy()
    series.columns = [
        "Year",
        "Cycle type",
        "Ballots counted",
        "VAP",
        "VEP",
        "VEP turnout (%)",
        "VAP turnout (%)",
        "pp change vs last same-cycle year",
        "National figure estimated",
    ]
    st.dataframe(series, width="stretch")

    st.subheader("Demographic indicators — associations only")
    st.image(str(CHARTS / "04_demographic_scatter.png"), width="stretch")
    corr = data["correlations"].copy()
    corr.columns = [
        "Indicator",
        "Scope",
        "n",
        "Pearson r",
        "Pearson p",
        "Spearman ρ",
        "Spearman p",
    ]
    st.dataframe(corr, width="stretch")
    st.caption(
        "These associations do not show that any indicator caused turnout to "
        "change. Correlation is not causation. No model is fitted."
    )

    st.subheader("Outliers — flagged, never dropped")
    outliers = data["outliers"]
    if len(outliers):
        st.dataframe(outliers, width="stretch")
        st.caption(
            "Flagged by the 1.5×IQR fence or |z| > 3 within cycle type. Every "
            "flagged row stays in every chart and table."
        )
    else:
        st.write("No states were flagged by the outlier screen.")

    st.subheader("Methods and limitations")
    st.markdown(
        "- **Source:** UF Election Lab turnout files (1980–2022 v1.2, 2024 v0.4), "
        "CC BY 4.0. EAVS 2024 (V1) cross-checked the 2024 numerator for sampled "
        "states only — UF figures stand. Census cartographic boundary file for "
        "map geometry.\n"
        "- **Denominators:** VEP (primary), VAP (secondary, alongside only), "
        "registered voters (EAVS cross-check only). Never mixed, never averaged.\n"
        "- **Cycle types:** presidential years compared with presidential years, "
        "midterms with midterms. A presidential-to-midterm change is a "
        "cycle-type change, not a trend.\n"
        "- **Limits:** descriptive only; state level only; 2024 figures are the "
        "lab's preliminary v0.4 release; pre-2010 national figures estimated; "
        "national VEP turnout not reported in the file for 1980–1996; state-level "
        "overseas eligible voters are not apportioned by the lab, so no "
        "state-level overseas association is computable.\n"
        "- **Sources:** "
        f"[UF Election Lab]({UF_LINK}) · [EAC EAVS]({EAC_LINK}) · "
        f"[Census boundary files]({CENSUS_LINK})"
    )

    st.divider()
    st.caption(ATTRIBUTION)


if __name__ == "__main__":
    main()
