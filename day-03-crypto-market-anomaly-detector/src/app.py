"""Day 3 — Crypto Market Anomaly Detector dashboard (Streamlit).

Reads ONLY data/processed/*.csv (never calls the API).
Flagged days are statistical outliers in price and volume — unusual
patterns requiring investigation, never presented as proven manipulation.
Educational analysis only — not investment advice.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHARTS_DIR = PROJECT_ROOT / "outputs" / "charts"
LABELS = {
    "bitcoin": "Bitcoin (BTC)",
    "ethereum": "Ethereum (ETH)",
    "solana": "Solana (SOL)",
}
ETHICS_SENTENCE = (
    "Anomalies flagged here are statistical outliers in price and volume. "
    "They are not evidence of manipulation, and no flagged pattern should "
    "be presented as such."
)

st.set_page_config(
    page_title="Crypto Market Anomaly Detector — BTC vs ETH vs SOL",
    layout="wide",
)
st.title("Crypto Market Anomaly Detector — BTC vs ETH vs SOL")
st.markdown(
    "**Powered by [CoinGecko](https://www.coingecko.com)** | "
    "Educational analysis only — not investment advice."
)
st.markdown(f"*{ETHICS_SENTENCE}*")

# --- Load processed data only -------------------------------------------------
daily = pd.read_csv(PROCESSED_DIR / "crypto_daily.csv", parse_dates=["date"])
timeline = pd.read_csv(PROCESSED_DIR / "anomaly_timeline.csv", parse_dates=["date"])
injected_labels = pd.read_csv(PROCESSED_DIR / "injected_anomalies.csv")

source_info = {}
source_path = PROCESSED_DIR / "data_source.json"
if source_path.exists():
    source_info = json.loads(source_path.read_text())
IS_SYNTHETIC = bool(source_info.get("synthetic", False))
if IS_SYNTHETIC:
    st.error(
        "⚠️ SYNTHETIC DATA — CoinGecko API was unavailable when this data "
        "was generated. Do not treat these values as real market data."
    )

window = f"{daily['date'].min():%Y-%m-%d} to {daily['date'].max():%Y-%m-%d}"
st.caption(f"Data window: {window} (daily, UTC)")

# --- Sidebar ------------------------------------------------------------------
coins = st.sidebar.multiselect(
    "Coins",
    options=["bitcoin", "ethereum", "solana"],
    default=["bitcoin", "ethereum", "solana"],
    format_func=lambda c: LABELS[c],
)
severities = st.sidebar.multiselect(
    "Severity",
    options=["High", "Medium", "Low"],
    default=["High", "Medium", "Low"],
)
if not coins:
    st.warning("Select at least one coin in the sidebar.")
    st.stop()

t = timeline[
    timeline["coin"].isin(coins) & timeline["severity"].isin(severities)
].copy()

# --- Summary ------------------------------------------------------------------
flaggable = int(daily["return_z"].notna().sum())
st.subheader("How many unusual days were there?")
n_flags = len(t)
both = int((t["flagged_by"] == "both").sum())
base_only = int((t["flagged_by"] == "baseline").sum())
forest_only = int((t["flagged_by"] == "forest").sum())
jaccard = both / n_flags if n_flags else 0.0
col1, col2, col3, col4 = st.columns(4)
col1.metric("Flagged days (selected)", n_flags)
col2.metric("Flagged by both methods", both)
col3.metric("Baseline-only / Forest-only", f"{base_only} / {forest_only}")
col4.metric("Baseline–forest overlap (Jaccard)", f"{jaccard:.2f}")
st.markdown(
    "A **flagged day** is an unusual pattern requiring investigation: a "
    "daily price or volume move far outside the coin's own trailing "
    "30-day behaviour, or a joint pattern the Isolation Forest found "
    "unusual. **Baseline** = the transparent z-score rules R1–R3; "
    "**forest** = the Isolation Forest on five engineered features. "
    f"Across all three coins, {len(timeline)} of {flaggable} flaggable "
    "days were flagged (the first 30 days per coin are a warm-up with no "
    "z-scores). A day flagged by both methods deserves more confidence "
    "than a day flagged by only one — but neither is evidence of "
    "manipulation."
)

# --- Overlap summary ----------------------------------------------------------
st.subheader("Baseline vs forest — do the two methods agree?")
overlap_rows = []
for coin in coins:
    tc = timeline[timeline["coin"] == coin]
    b = int(((tc["flagged_by"] == "baseline") | (tc["flagged_by"] == "both")).sum())
    f = int(((tc["flagged_by"] == "forest") | (tc["flagged_by"] == "both")).sum())
    both_c = int((tc["flagged_by"] == "both").sum())
    overlap_rows.append(
        {
            "Coin": LABELS[coin],
            "Baseline flags": b,
            "Forest flags": f,
            "Flagged by both": both_c,
            "Baseline-only": int((tc["flagged_by"] == "baseline").sum()),
            "Forest-only": int((tc["flagged_by"] == "forest").sum()),
            "Total flagged": len(tc),
        }
    )
st.dataframe(pd.DataFrame(overlap_rows), width="stretch", hide_index=True)
st.caption(
    "Jaccard overlap = days flagged by both ÷ days flagged by either. "
    f"Overall: {both}/{len(timeline)} = {both / len(timeline):.2f} "
    "(target ≥ 0.30). The methods substantially agree; the remaining "
    "difference is about *which* days, not how many — the forest's "
    "contamination was set equal to the baseline flag rate (3.7%)."
)

# --- Anomaly timeline table ----------------------------------------------------
st.subheader("Anomaly timeline — every flagged day, explained")
st.markdown(
    "Each row is one unusual pattern requiring investigation, with the "
    "numbers that triggered it and a one-sentence plain-language "
    "explanation. Sort or filter with the table controls."
)
if len(t) == 0:
    st.info("No flagged days match the current filters.")
else:
    show = t.sort_values(["date", "coin"]).reset_index(drop=True).copy()
    show["date"] = show["date"].dt.strftime("%Y-%m-%d")
    show["daily_return"] = (show["daily_return"] * 100).round(2)
    # Forest-only rows have no rule and early rows (before 2026-01-06)
    # have no volume_z yet (60-day warm-up): show an em dash, not "None".
    show["return_z"] = show["return_z"].map(
        lambda v: f"{v:.2f}" if pd.notna(v) else "—"
    )
    show["volume_z"] = show["volume_z"].map(
        lambda v: f"{v:.2f}" if pd.notna(v) else "—"
    )
    show["volume_ratio"] = show["volume_ratio"].round(2)
    show["vol_30d_ann"] = (show["vol_30d_ann"] * 100).round(1)
    show["isolation_forest_score"] = show["isolation_forest_score"].map(
        lambda v: f"{v:.2f}" if pd.notna(v) else "—"
    )
    # read_csv turns the empty rules_triggered field into NaN
    show["rules_triggered"] = show["rules_triggered"].fillna("— (forest only)")
    show = show[
        [
            "date",
            "coin",
            "daily_return",
            "volume_ratio",
            "return_z",
            "volume_z",
            "vol_30d_ann",
            "rules_triggered",
            "isolation_forest_score",
            "flagged_by",
            "severity",
            "explanation",
        ]
    ]
    show.columns = [
        "Date",
        "Coin",
        "Return (%)",
        "Volume ratio (x)",
        "Return z",
        "Volume z",
        "30d vol (%/yr)",
        "Rules",
        "Forest score",
        "Flagged by",
        "Severity",
        "Explanation",
    ]
    st.dataframe(show, width="stretch", hide_index=True)

# --- Highest-severity flag per coin --------------------------------------------
st.subheader("Most extreme flag per coin")
for coin in coins:
    tc = timeline[timeline["coin"] == coin].sort_values("date").reset_index(drop=True)
    if len(tc) == 0:
        continue
    top = tc.loc[tc["return_z"].abs().idxmax()]
    st.markdown(
        f"**{LABELS[coin]}:** {top['date'].strftime('%Y-%m-%d')} — "
        f"{top['daily_return']:+.1%} (return z = {top['return_z']:.1f}), "
        f"volume {top['volume_ratio']:.1f}x its 30-day average, "
        f"{top['severity']} severity, flagged by {top['flagged_by']}. "
        f"{top['explanation']}"
    )

# --- Charts ---------------------------------------------------------------------
st.subheader("1 · Anomaly timeline — price with flagged days")
st.image(str(CHARTS_DIR / "01_anomaly_timeline.png"), width="stretch")
st.caption(
    "Flagged days are statistical outliers, not evidence of manipulation. Powered by CoinGecko (coingecko.com)."
)

st.subheader("2 · Return vs volume — why a day was flagged")
st.image(str(CHARTS_DIR / "02_return_volume_scatter.png"), width="stretch")
st.caption(
    "Dashed guides use the median trailing 30-day σ; exact R1/R2/R3 thresholds are per-day z-scores. Powered by CoinGecko (coingecko.com)."
)

st.subheader("3 · Flag counts — which coin, which pattern")
st.image(str(CHARTS_DIR / "03_flag_counts_severity.png"), width="stretch")
st.caption(
    "A day can trigger several rules, so rule counts sum to more than the baseline flag count. Powered by CoinGecko (coingecko.com)."
)

st.subheader("4 · Evaluation — how good is the detector?")
st.image(str(CHARTS_DIR / "04_evaluation.png"), width="stretch")
st.markdown(
    "Evaluation is on **30 injected anomalies** of known type "
    f"({len(injected_labels)} labels in "
    "`data/processed/injected_anomalies.csv`), with a ±1-day tolerance. "
    "Union recall 1.00 (30 of 30 found, target ≥ 0.80) and precision "
    "0.974 (76 of 78 flags are injected anomalies or genuine unusual "
    "days also flagged on clean data, target ≥ 0.50). "
    "Per-type recall: price spikes 1.00, volume surges 1.00, joint "
    "shocks 1.00 (target ≥ 0.60 each). The forest alone finds 22 of 30 "
    "and misses only volume surges. "
    "Full report card: "
    "`outputs/anomaly_evaluation.md`."
)

st.divider()
st.markdown(
    "Powered by [CoinGecko](https://www.coingecko.com). "
    "Educational analysis only — not investment advice. "
    f"{ETHICS_SENTENCE} "
    "Close prices only (no OHLC); daily granularity; 366 daily "
    "observations per coin (2025-11-07 → 2026-11-07). Trailing 30-day "
    "z-scores exclude today, so no future information leaks into a "
    "flag. Isolation Forest: contamination 0.0368 (the baseline flag "
    "rate), random_state=42, n_estimators=200. There is no ground-truth "
    "manipulation label for real crypto data, so the detector is "
    "evaluated on injected anomalies only."
)
