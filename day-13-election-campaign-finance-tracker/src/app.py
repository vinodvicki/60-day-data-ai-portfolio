"""Streamlit dashboard for Day 13 — Election Campaign Finance Tracker.

Loads processed CSVs + data_source.json only (offline). Every surface
states the coverage limits: 2024 cycle only, state totals not
population-adjusted, no donor names, no outcome claims, candidate money
is the FEC candidate totals (plan §2.0, amended).
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
    "2024 cycle only — reported dollars as filed with the FEC. State totals "
    "are NOT adjusted for population. No individual-donor names are in this "
    "build (itemized vs unitemized aggregates only). Nothing here says money "
    "caused an election outcome — the data has no outcome variable."
)
ATTRIBUTION = (
    "Data: U.S. Federal Election Commission, 2024 cycle bulk data "
    "(fec.gov/data/browse-data) and openFEC API (api.open.fec.gov/v1). "
    "Public domain. Retrieved 2026-11-19."
)
BULK_LINK = "https://www.fec.gov/data/browse-data/?tab=bulk-data"
API_LINK = "https://api.open.fec.gov/v1"


def money(x: float) -> str:
    """Format dollars as $X.XB / $X.XM / $X.XK."""
    if pd.isna(x):
        return "—"
    if abs(x) >= 1e9:
        return f"${x / 1e9:,.2f}B"
    if abs(x) >= 1e6:
        return f"${x / 1e6:,.1f}M"
    if abs(x) >= 1e3:
        return f"${x / 1e3:,.0f}K"
    return f"${x:,.0f}"


@st.cache_data
def load_data() -> dict[str, Any]:
    record = json.loads((PROC / "data_source.json").read_text(encoding="utf-8"))
    return {
        "record": record,
        "candidates": pd.read_csv(PROC / "candidates.csv"),
        "committees": pd.read_csv(PROC / "committees.csv"),
        "party_office": pd.read_csv(PROC / "party_office.csv"),
        "state_totals": pd.read_csv(PROC / "state_totals.csv"),
        "top_candidates": pd.read_csv(PROC / "top_candidates.csv"),
        "top_committees": pd.read_csv(PROC / "top_committees.csv"),
    }


def main() -> None:
    st.set_page_config(
        page_title="Election Campaign Finance Tracker — 2024 cycle",
        layout="wide",
    )
    st.title("Election Campaign Finance Tracker")
    st.subheader(
        "Where the money in the 2024 US federal election cycle came from — and how it was spent"
    )
    st.info(LIMITS_BANNER)
    data = load_data()
    record = data["record"]
    candidates = data["candidates"]
    party_office = data["party_office"]
    state_totals = data["state_totals"]
    top_candidates = data["top_candidates"]
    top_committees = data["top_committees"]
    totals = record["cycle_totals"]

    if record.get("synthetic"):
        st.warning("SYNTHETIC — NOT REAL DATA. Live sources were unreachable.")
    st.markdown(
        f"Sources: [FEC bulk data]({BULK_LINK}) · "
        f"[openFEC API]({API_LINK}) · {ATTRIBUTION}"
    )

    # KPI row.
    with_totals = candidates[candidates["has_totals"]]
    top1 = top_candidates.iloc[0]
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Candidate receipts", money(float(totals["candidate_receipts_usd"])))
    col2.metric(
        "Candidate disbursements", money(float(totals["candidate_disbursements_usd"]))
    )
    col3.metric(
        "Candidates with totals",
        f"{int(totals['n_candidates_with_totals']):,} of " f"{len(candidates):,} filed",
    )
    col4.metric(
        "Committees in bulk file", f"{int(totals['n_committees_with_summary']):,}"
    )
    col5.metric(
        "Top candidate",
        f"{top1['candidate_name'].title()}",
        f"{money(float(top1['receipts']))} ({float(top1['receipts_share']):.1%})",
    )

    st.markdown(
        "Candidate receipts are the FEC candidate totals (principal campaign "
        "committee plus other authorized committees, per the FEC's own "
        "definition). Committee receipts are the sum of the committee-summary "
        "bulk file. The two universes are never added together without noting "
        "that transfers between committees would be double-counted."
    )
    st.caption(
        "Harris and Biden tie at $1,175.2M each — they share principal "
        "committee C00703975 (Harris Victory Fund), so the $6,503.1M "
        "candidate-receipts total counts their shared ~$1.18B twice."
    )

    st.header("Receipts by office and party")
    st.image(str(CHARTS / "01_receipts_by_office_party.png"))
    st.dataframe(
        party_office[
            [
                "party",
                "office",
                "n_candidates",
                "n_with_totals",
                "n_with_split",
                "receipts",
                "receipts_with_split",
                "receipts_share",
                "small_dollar_share",
                "median_receipts",
            ]
        ],
        width="stretch",
    )
    st.caption(
        "Same columns for every party. Small-dollar share = unitemized "
        "individual contributions ÷ all individual contributions, computed "
        "over the split-covered candidates only (n_with_split, "
        "receipts_with_split) — it is a funding-mix descriptor, not a "
        "donor headcount."
    )

    st.header("Top 10 candidates by receipts")
    st.image(str(CHARTS / "02_top_candidates.png"))
    st.dataframe(
        top_candidates,
        width="stretch",
    )
    st.caption("Top means top by total receipts in the 2024 cycle, as filed.")

    st.header("Where the money came from")
    st.image(str(CHARTS / "03_funding_mix.png"))
    st.caption(
        "Itemized = donors who gave more than $200 in the cycle and are named "
        "in filings. Unitemized = small-dollar, $200 or less, reported only "
        "in aggregate. Other receipts is the residual (PAC money, party "
        "transfers, candidate loans, other). The mix covers the 2,259 "
        "candidates with a published itemized/unitemized split "
        "($6,286.0M of receipts); the other 2,117 candidates with totals "
        "have no split on record."
    )

    st.header("Top 10 non-candidate committees by receipts")
    st.dataframe(
        top_committees,
        width="stretch",
    )
    st.caption(
        "Non-candidate committees from the 2024 committee-summary bulk file "
        "(PACs, super PACs, party committees, independent-expenditure "
        "groups). Principal campaign committees are excluded — their money "
        "is already in the candidate totals. Candidate committees are "
        "largely absent from this bulk file (only 179 of 12,379 rows), so "
        "candidate money is analysed from the candidate totals, not here."
    )

    st.header("States")
    st.image(str(CHARTS / "04_state_totals.png"))
    st.dataframe(
        state_totals,
        width="stretch",
    )
    st.caption(
        "Totals are not adjusted for state population — no per-capita "
        "figures. State is the candidate's mailing-address state as filed, "
        "so presidential campaigns appear under their HQ state (Biden and "
        "Harris: PA, Philadelphia — 38.8% of candidate receipts). 39 "
        "candidates with no usable state on file are excluded from this table."
    )

    st.header("Spending patterns")
    burn = with_totals.copy()
    burn = burn[burn["receipts"] > 0]
    burn_by_office = (
        burn.groupby("office")["burn_rate"]
        .agg(["median", "mean", "count"])
        .reset_index()
        .sort_values("median", ascending=False)
    )
    st.dataframe(burn_by_office, width="stretch")
    st.caption(
        "Burn rate = disbursements ÷ receipts. Above 1 is possible and "
        "normal for candidates spending down prior-cycle cash; it is not "
        "flagged as overspending."
    )
    cash_top = with_totals.nlargest(10, "cash_on_hand")[
        ["candidate_name", "party", "office", "cash_on_hand", "debts_owed"]
    ]
    st.subheader("Top 10 candidates by cash on hand (end of period)")
    st.dataframe(cash_top, width="stretch")
    st.caption(
        "Read the top row with care: Norris (P40010415) reports $775.8M "
        "cash on hand — 56.5% of all candidate cash — on $35.4M of "
        "receipts, and the filing fails the cash-identity check. The "
        "figure is reported as filed; excluding it, candidate cash on hand "
        "is $597.7M."
    )

    st.header("Methods & limitations")
    st.markdown(
        "- **Cycle:** 2024 two-year cycle only (2023-01-01 → 2024-12-31). "
        "No 2026 rows.\n"
        "- **Candidate money:** FEC candidate totals via the openFEC API "
        "(`/candidates/totals/` list endpoint, 5,321 rows for 4,294 unique "
        "candidates after dedup), joined to the FEC candidate master for "
        "party, office, state and district. Receipts, disbursements and "
        "individual contributions are taken from the candidate-summary "
        "bulk file (`webl24.zip`) where the candidate is present (2,378 "
        "candidates), because the list endpoint overstates multi-committee "
        "candidates; the remaining 1,998 use the list values. "
        "Cross-checked against the bulk file (max receipt difference "
        "$12.1M, all from the list endpoint's overstatement).\n"
        "- **Committee money:** FEC committee-summary bulk file "
        "(`webk24.zip`, 12,379 committees, 10,114 with a financial "
        "summary). Candidate committees are largely absent from this file, "
        "so it is not used for candidate money.\n"
        "- **Donors:** itemized vs unitemized aggregates only. No donor "
        "names are in this build.\n"
        "- **States:** totals and shares only — not population-adjusted "
        "(the Census API requires a key that is not available).\n"
        "- **Outcomes:** no election-result variable is included and none "
        "is added. No claim is made that money caused any outcome.\n"
        "- **Cash identity:** COH_BOP + receipts − disbursements equals "
        "cash on hand for 91.8% of committee summaries and 83.8% of "
        "candidate summaries; the rest reflect amended filings and are "
        "recorded in `data_source.json`.\n"
        "- **Bulk files are headerless:** column names were assigned from "
        "the FEC file descriptions and verified against the live API to "
        "the cent for five candidates, plus the cash identity."
    )
    st.caption(ATTRIBUTION)


if __name__ == "__main__":
    main()
