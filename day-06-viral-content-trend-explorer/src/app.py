"""Day 6 — Viral Content Trend Explorer: Streamlit dashboard.

Reads only the committed processed CSVs (no network, no API).
Trends here compare two 30-day cohorts of recently published videos.
The API gives a current snapshot of each video's statistics, not daily
history — so these are cohort comparisons, not a record of views rising
or falling over time. No causal claims anywhere; every finding is stated
about this sample only. Sentiment is a model output from our own
rule-based lexicon — never ground truth — and never enters a trend
classification. Educational analysis only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHARTS_DIR = PROJECT_ROOT / "outputs" / "charts"
DAY04_FRAME = (
    PROJECT_ROOT.parent
    / "day-04-youtube-video-performance-analyzer"
    / "data"
    / "processed"
    / "videos.csv"
)

TOPIC_LABELS = {
    "python": "Python",
    "ai_ml": "AI & Machine Learning",
    "sql": "SQL",
    "career": "Career",
    "bi_viz": "Business Intelligence & Visualisation",
    "general": "General Data Analytics",
    "other": "Other",
}
COHORT_SENTENCE = (
    "Trends here compare two 30-day cohorts of recently published videos. "
    "The API gives a current snapshot of each video's statistics, not daily "
    "history — so these are cohort comparisons, not a record of views rising "
    "or falling over time."
)

st.set_page_config(
    page_title="Viral Content Trend Explorer",
    page_icon="📈",
    layout="wide",
)
st.title("Viral Content Trend Explorer")
st.markdown(f"*{COHORT_SENTENCE}*")

videos = pd.read_csv(PROCESSED_DIR / "videos.csv")
comments = pd.read_csv(PROCESSED_DIR / "comments.csv")
table = pd.read_csv(PROCESSED_DIR / "trend_table.csv")
source = json.loads((PROCESSED_DIR / "data_source.json").read_text())

if source.get("synthetic"):
    st.error(
        "SYNTHETIC DATA — API unavailable on 2026-11-10. "
        "Findings on this data have no interpretation."
    )

n_a = int((videos["window"] == "A").sum())
n_b = int((videos["window"] == "B").sum())
st.caption(
    f"Two 30-day cohorts of recently published data/AI YouTube videos: "
    f"prior window 2026-09-11 → 2026-10-11 ({n_b} videos) vs recent window "
    f"2026-10-11 → 2026-11-10 ({n_a} videos) · Fetched live 2026-11-10 · "
    f"Quota used: {source['quota_units_used']} units (this run; see "
    f"data/README.md for the day total) · Data from the YouTube Data API v3."
)

# --- Truncation warning (all 10 query-windows returned exactly 50) ----------
truncated = [
    key for key, value in source["per_query_window"].items() if value["truncated"]
]
if truncated:
    st.warning(
        "All 10 query-windows returned exactly 50 videos (the one-page cap), "
        "so each window is truncated to its newest videos: the recent window "
        "effectively covers only 2026-11-08 → 11-09 and the prior window only "
        "2026-10-08 → 10-10. Weekly buckets W1–W3 and W6–W8 are empty, and "
        "the volume numbers below are lower bounds for their windows, not "
        "full 30-day counts."
    )

# --- Channel concentration ----------------------------------------------------
concentration = source.get("channel_concentration", {})
for window, info in concentration.items():
    share = info.get("top_channel_share")
    if share and share > 20:
        st.warning(
            f"One channel contributes {share:.1f}% of window {window} — "
            "that window is more a channel study than a topic study."
        )
st.caption(
    f"Distinct channels: recent window "
    f"{concentration.get('A', {}).get('distinct_channels', '—')} "
    f"(largest share "
    f"{concentration.get('A', {}).get('top_channel_share', '—')}%), prior window "
    f"{concentration.get('B', {}).get('distinct_channels', '—')} "
    f"(largest share "
    f"{concentration.get('B', {}).get('top_channel_share', '—')}%). "
    f"No single channel dominates either window."
)

# --- Sidebar filters -----------------------------------------------------------
topics = st.sidebar.multiselect(
    "Topic",
    options=sorted(table["topic"].unique()),
    default=sorted(table["topic"].unique()),
    format_func=lambda t: TOPIC_LABELS.get(t, t),
)
if not topics:
    st.warning("Select at least one topic.")
    st.stop()
filtered_table = table[table["topic"].isin(topics)].copy()
filtered_videos = videos[videos["topic"].isin(topics)]

# --- KPI summary ----------------------------------------------------------------
accelerating = filtered_table[filtered_table["classification"] == "accelerating"]
fading = filtered_table[filtered_table["classification"] == "fading"]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Videos in this sample", f"{len(filtered_videos):,}")
col2.metric("Accelerating topics", str(len(accelerating)))
col3.metric("Fading topics", str(len(fading)))
col4.metric(
    "Topics with insufficient data",
    str(int((filtered_table["classification"] == "insufficient data").sum())),
)


def _finding_text(row) -> str:
    label = TOPIC_LABELS[row.topic]
    return (
        f"{label} ({row.share_change_pp:+.1f} pp, " f"{row.volume_growth * 100:+.1f}%)"
    )


st.caption(
    "Classifications use the fixed thresholds (share change ±3 pp and volume "
    "growth ±20%, n ≥ 10 in both windows). In this sample, "
    + (
        "; ".join(_finding_text(r) for r in accelerating.itertuples())
        + " meet the accelerating rule"
        if not accelerating.empty
        else "no topic meets the accelerating rule"
    )
    + ", and "
    + (
        "; ".join(_finding_text(r) for r in fading.itertuples())
        + " meet the fading rule"
        if not fading.empty
        else "no topic meets the fading rule"
    )
    + ". These are statements about this truncated sample, not about YouTube "
    "as a whole."
)

# --- Classification table ---------------------------------------------------------
st.subheader("1 · Which topics are accelerating, fading, or stable?")
display = filtered_table.copy()
display["Topic"] = display["topic"].map(TOPIC_LABELS)
display["Share change (pp)"] = display["share_change_pp"].map("{:+.2f}".format)
display["Volume growth"] = display["volume_growth"].map(
    lambda v: f"{v * 100:+.1f}%" if pd.notna(v) else "no prior baseline"
)
display["Median views/day (recent)"] = display["median_views_per_day_A"].map(
    lambda v: f"{v:.1f}" if pd.notna(v) else "—"
)
display["Median views/day (prior)"] = display["median_views_per_day_B"].map(
    lambda v: f"{v:.1f}" if pd.notna(v) else "—"
)
display["Median age (recent / prior, days)"] = display.apply(
    lambda r: (
        f"{r['median_age_A']:.0f} / {r['median_age_B']:.0f}"
        if pd.notna(r["median_age_A"]) and pd.notna(r["median_age_B"])
        else f"— / {r['median_age_B']:.0f}" if pd.notna(r["median_age_B"]) else "—"
    ),
    axis=1,
)
display["Mixed signal"] = display["mixed_signal"].map(
    lambda v: "Yes — see briefing" if v else "No"
)
display["Classification"] = display["classification"]
st.dataframe(
    display[
        [
            "Topic",
            "n_A",
            "n_B",
            "Share change (pp)",
            "Volume growth",
            "Median views/day (recent)",
            "Median views/day (prior)",
            "Median age (recent / prior, days)",
            "Mixed signal",
            "Classification",
        ]
    ].rename(columns={"n_A": "n (recent)", "n_B": "n (prior)"}),
    width="stretch",
    hide_index=True,
)
st.caption(
    "n is the video count per window. Velocity change is undefined for every "
    "topic in this sample (no recent video is aged ≥ 7 days), so no "
    "mixed-signal flag can be raised — the volume classification stands on "
    "its own, with that caveat stated."
)
st.image(str(CHARTS_DIR / "01_trend_momentum.png"), width="stretch")
st.caption(
    "Share change and volume growth against the fixed ±3 pp / ±20% "
    "threshold lines. Career, BI & Visualisation and General Data Analytics "
    "have n < 10 in a window, so they are reported as insufficient data, "
    "not classified."
)

# --- Weekly volume ------------------------------------------------------------------
st.subheader("2 · Weekly publish volume per topic")
st.image(str(CHARTS_DIR / "02_weekly_volume.png"), width="stretch")
st.caption(
    "Weekly buckets anchored 2026-09-11. W1–W3 and W6–W8 are empty because "
    "each query-window returned only its newest 50 videos (truncation). "
    "W9 is partial (5 days, 2026-11-06 → 11-10) and is excluded from "
    "week-over-week growth. The 2-week rolling mean is a display aid, "
    "never a classification input."
)

# --- Velocity -------------------------------------------------------------------------
st.subheader("3 · Velocity: how fast are videos accumulating views?")
st.image(str(CHARTS_DIR / "03_views_velocity.png"), width="stretch")
st.caption(
    "Median views per day (age ≥ 7 days only), with median age and n on "
    "every bar. Recent-window velocity is not computable in this sample: "
    "all 236 recent videos were published 2026-11-08/09. Prior-window "
    "medians: Python 5.6/day (median age 30 days, n=88), AI & Machine "
    "Learning 4.1/day (31 days, n=62), SQL 3.6/day (30 days, n=43). "
    "Views per day is systematically higher for young videos, so any "
    "recent-vs-prior velocity comparison would favour the recent window "
    "by construction — that is why the 7-day guard and the median-age "
    "reporting exist."
)
st.subheader("Age-guard sensitivity")
st.markdown(
    "Recomputing velocity change with a 14-day guard instead of 7 days "
    "flips no topic's velocity direction — because velocity change is "
    "undefined at both guards (no recent video is age-eligible). The "
    "volume classification does not depend on velocity."
)

# --- Sentiment mood panel ----------------------------------------------------------------
st.subheader("4 · Audience mood on the fastest-rising video per topic")
if comments.empty:
    st.info(
        "No sentiment snapshot in this sample: the mood snapshot needs the "
        "top video by views per day in each topic in the recent window, aged "
        "≥ 7 days — but all 236 recent videos were published 2026-11-08/09, "
        "so no video qualifies. 0 videos, 0 comments analysed. This is a "
        "consequence of the same truncation that empties the weekly buckets, "
        "not a scoring failure."
    )
else:
    summary = (
        comments.groupby(["video_id", "topic"])
        .agg(
            mean_compound=("sentiment_score", "mean"),
            n=("sentiment_score", "size"),
            positive=("sentiment", lambda s: (s == "positive").mean() * 100),
            negative=("sentiment", lambda s: (s == "negative").mean() * 100),
        )
        .reset_index()
    )
    st.image(str(CHARTS_DIR / "04_sentiment_mood.png"), width="stretch")
    for row in summary.itertuples():
        st.markdown(
            f"- **{TOPIC_LABELS[row.topic]}** — “{comments.loc[comments['video_id'] == row.video_id, 'video_title'].iloc[0][:80]}”: "
            f"mean compound {row.mean_compound:.2f}, {row.positive:.1f}% "
            f"positive / {row.negative:.1f}% negative (n={int(row.n)}, as "
            f"classified by our rule-based model)."
        )
st.caption(
    "Sentiment is a model output, not ground truth, and it describes five "
    "videos at most — never the topics. No sentiment number is used in any "
    "trend classification."
)

# --- Backtest panel -----------------------------------------------------------------------
st.subheader("5 · Holdout backtest — how stable are the calls over one week?")
st.markdown(
    "The backtest trains on weeks W1–W7, predicts the topic with the highest "
    "share growth from W1–W3 to W5–W7, and checks whether it is in the top 2 "
    "by share in W8. **Not computable in this sample:** W1–W3 hold no videos "
    "at all and W8 is empty, so there is no train growth to predict from and "
    "no test week to check against. No hit/miss is claimed. A one-week "
    "backtest would be weak evidence even when computable."
)

# --- Layer A context ------------------------------------------------------------------------
st.subheader("6 · Long-run context (Day 4 frame — relevance sample, not exhaustive)")
if DAY04_FRAME.exists():
    day04 = pd.read_csv(DAY04_FRAME)
    shares = day04["topic"].value_counts(normalize=True) * 100
    context = pd.DataFrame(
        {
            "Topic": [TOPIC_LABELS.get(t, t) for t in shares.index],
            "Videos": day04["topic"].value_counts().values,
            "Share (%)": [f"{v:.1f}" for v in shares.values],
        }
    )
    st.dataframe(context, width="stretch", hide_index=True)
    st.caption(
        f"Day 4 frame: {len(day04)} videos fetched 2026-11-08, publish range "
        f"{day04['published_at'].min()[:10]} → {day04['published_at'].max()[:10]}. "
        f"It is a relevance-ranked snapshot, never mixed into the momentum "
        f"numbers above (different snapshot date, different selection method). "
        f"Overlap with this sample: {source['overlap_with_day04_frame']} videos."
    )
else:
    st.info("Day 4 frame not found in this checkout.")

st.divider()
st.markdown(
    "These findings describe this sample of recently published data/AI videos. "
    "They are descriptive, not causal, and are not a guarantee of anything "
    "about YouTube videos in general. Data from the YouTube Data API v3 — "
    "see [YouTube's Terms of Service](https://www.youtube.com/t/terms). "
    "Code is MIT; YouTube data is under separate YouTube terms."
)
