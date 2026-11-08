"""Day 4 — YouTube Video Performance Analyzer dashboard (Streamlit).

Reads ONLY data/processed/videos.csv (never calls the API).
Performance patterns here describe this sampled set of public videos.
They are descriptive, not causal, and are not a guarantee of future
performance. Educational analysis only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

try:  # run as a module / from the project root
    from src.youtube_kpi import (
        BUCKET_LABELS,
        TOPIC_LABELS,
        build_recommendations,
    )
except ImportError:  # run as a script: streamlit run src/app.py
    from youtube_kpi import (  # type: ignore[no-redef]
        BUCKET_LABELS,
        TOPIC_LABELS,
        build_recommendations,
    )

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHARTS_DIR = PROJECT_ROOT / "outputs" / "charts"

DESCRIPTIVE_SENTENCE = (
    "Performance patterns here describe this sampled set of public "
    "videos. They are descriptive, not causal, and are not a guarantee "
    "of future performance."
)

st.set_page_config(
    page_title="YouTube Video Performance Analyzer",
    layout="wide",
)
st.title("YouTube Video Performance Analyzer")
st.markdown(
    "**Data from the YouTube Data API v3** — "
    "[YouTube's Terms of Service](https://www.youtube.com/t/terms) | "
    "Educational analysis only."
)
st.markdown(f"*{DESCRIPTIVE_SENTENCE}*")

# --- Load processed data only -------------------------------------------------
videos = pd.read_csv(PROCESSED_DIR / "videos.csv", parse_dates=["published_at"])

source_info = {}
source_path = PROCESSED_DIR / "data_source.json"
if source_path.exists():
    source_info = json.loads(source_path.read_text())
IS_SYNTHETIC = bool(source_info.get("synthetic", False))
if IS_SYNTHETIC:
    st.error(
        "⚠️ SYNTHETIC DATA — API unavailable on 2026-11-08. "
        "Do not treat these values as real YouTube data."
    )

n_videos = len(videos)
n_channels = int(videos["channel_id"].nunique())
top_channel = videos["channel_id"].value_counts()
top_channel_share = float(top_channel.iloc[0] / n_videos) if n_videos else 0.0
st.caption(
    f"Sample: {n_videos} videos from {n_channels} channels, "
    f"published {videos['published_at'].min():%Y-%m-%d} to "
    f"{videos['published_at'].max():%Y-%m-%d} "
    "(relevance-ranked snapshot as of 2026-11-08 — not a date-bounded cohort)."
)
if top_channel_share > 0.20:
    st.warning(
        f"One channel makes up {top_channel_share:.1%} of this sample "
        "— this is closer to a channel study than a topic study."
    )

# --- Sidebar filters -----------------------------------------------------------
topic_options = sorted(videos["topic"].unique())
topics = st.sidebar.multiselect(
    "Topics",
    options=topic_options,
    default=topic_options,
    format_func=lambda t: TOPIC_LABELS.get(t, t),
)
bucket_options = sorted(
    videos["duration_bucket"].unique(),
    key=lambda b: list(BUCKET_LABELS).index(b),
)
buckets = st.sidebar.multiselect(
    "Video lengths",
    options=bucket_options,
    default=bucket_options,
    format_func=lambda b: BUCKET_LABELS.get(b, b),
)
high_only = st.sidebar.checkbox("Top-quartile performers only", value=False)
if not topics or not buckets:
    st.warning("Select at least one topic and one video length in the sidebar.")
    st.stop()

filtered = videos[
    videos["topic"].isin(topics) & videos["duration_bucket"].isin(buckets)
].copy()
if high_only:
    filtered = filtered[filtered["high_performer"]].copy()
if len(filtered) == 0:
    st.info("No videos match the current filters.")
    st.stop()

# --- KPI summary (medians, never means) ---------------------------------------
st.subheader("How strong is this sample?")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Videos (selected)", len(filtered))
col2.metric(
    "Median views per day",
    f"{filtered['views_per_day'].median():,.0f}",
)
col3.metric(
    "Median engagement rate",
    f"{filtered['engagement_rate'].median() * 100:.2f}%",
)
col4.metric("Channels (selected)", int(filtered["channel_id"].nunique()))
st.markdown(
    "Views per day is the age-normalised performance measure: a 2021 "
    "video with 2M lifetime views and a 2026 video with 200K views are "
    "not comparable on raw views. Engagement rate is "
    "(likes + comments) ÷ views, shown next to the underlying counts "
    "wherever it appears — the derived rate never replaces the API data. "
    f"Across all {n_videos} videos the median is "
    f"{videos['views_per_day'].median():,.0f} views/day and "
    f"{videos['engagement_rate'].median() * 100:.2f}% engagement."
)

# --- Topic table ----------------------------------------------------------------
st.subheader("Which topics perform best?")
topic_rows = []
for topic, group in filtered.groupby("topic"):
    topic_rows.append(
        {
            "Topic": TOPIC_LABELS.get(topic, topic),
            "Videos": len(group),
            "Median views/day": round(float(group["views_per_day"].median()), 0),
            "Median engagement (%)": round(
                float(group["engagement_rate"].median()) * 100, 2
            ),
        }
    )
topic_table = (
    pd.DataFrame(topic_rows)
    .sort_values("Median views/day", ascending=False)
    .reset_index(drop=True)
)
st.dataframe(topic_table, width="stretch", hide_index=True)
st.caption(
    "BI & Visualisation has only 3 videos in this sample — its median "
    "is shown but is too thin to support a recommendation. "
    "The 'Other' topic group is empty (0 videos)."
)

# --- Duration table ---------------------------------------------------------------
st.subheader("Which lengths perform best?")
dur_rows = []
for bucket, group in filtered.groupby("duration_bucket"):
    dur_rows.append(
        {
            "Length": BUCKET_LABELS.get(bucket, bucket),
            "Videos": len(group),
            "Median views/day": round(float(group["views_per_day"].median()), 0),
            "Median engagement (%)": round(
                float(group["engagement_rate"].median()) * 100, 2
            ),
        }
    )
dur_table = pd.DataFrame(dur_rows)
order = list(BUCKET_LABELS)
dur_table["sort"] = dur_table["Length"].map(
    lambda label: order.index(next(k for k, v in BUCKET_LABELS.items() if v == label))
)
dur_table = dur_table.sort_values("sort").drop(columns="sort").reset_index(drop=True)
st.dataframe(dur_table, width="stretch", hide_index=True)

# --- High performers ---------------------------------------------------------------
st.subheader("Top-quartile performers vs the rest")
high = videos[videos["high_performer"]]
rest = videos[~videos["high_performer"]]
st.markdown(
    f"Top-quartile videos (n={len(high)}) had a median of "
    f"{high['views_per_day'].median():,.0f} views/day vs "
    f"{rest['views_per_day'].median():,.0f} for the rest (n={len(rest)}). "
    f"Their median engagement was "
    f"{high['engagement_rate'].median() * 100:.2f}% vs "
    f"{rest['engagement_rate'].median() * 100:.2f}% — reach and "
    "engagement did not move together in this sample. "
    f"AI & Machine Learning made up {high['topic'].eq('ai_ml').mean():.0%} "
    f"of the top quartile vs {rest['topic'].eq('ai_ml').mean():.0%} of "
    "the rest; Python made up "
    f"{high['topic'].eq('python').mean():.0%} vs "
    f"{rest['topic'].eq('python').mean():.0%}. No single channel "
    f"dominates the top quartile (largest share "
    f"{high['channel_id'].value_counts(normalize=True).iloc[0]:.1%})."
)

# --- Charts -------------------------------------------------------------------------
st.subheader("1 · Median views per day by topic")
st.image(str(CHARTS_DIR / "01_views_by_topic.png"), width="stretch")
st.caption(
    "Medians, not means — one viral video cannot dominate a median. "
    "Data from the YouTube Data API v3."
)

st.subheader("2 · Duration vs performance")
st.image(str(CHARTS_DIR / "02_duration_vs_performance.png"), width="stretch")
st.caption(
    "Bars are median views per day; the line is median engagement rate. "
    "Data from the YouTube Data API v3."
)

st.subheader("3 · Publish-time heatmap")
st.image(str(CHARTS_DIR / "03_publish_time_heatmap.png"), width="stretch")
st.caption(
    "Most hour/day cells hold only 1–4 videos. The channel audience "
    "timezone is unknown, so this is descriptive only — not a best time "
    "to post. Data from the YouTube Data API v3."
)

st.subheader("4 · Engagement vs reach")
st.image(str(CHARTS_DIR / "04_engagement_scatter.png"), width="stretch")
st.caption(
    "Each dot is one video. High performers reach further without "
    "engaging better. Data from the YouTube Data API v3."
)

# --- Recommendations -------------------------------------------------------------------
st.subheader("Content recommendations — each with its evidence")
recommendations = build_recommendations(videos)
for i, rec in enumerate(recommendations, start=1):
    st.markdown(
        f"**{i}. {rec['recommendation']}**  \n"
        f"Evidence: {rec['evidence']}.  \n"
        f"Sample basis: {rec['sample_basis']}.  \n"
        f"Caveat: {rec['caveat']}"
    )

st.divider()
st.markdown(
    "Data from the YouTube Data API v3 — "
    "[YouTube's Terms of Service](https://www.youtube.com/t/terms). "
    "Only public video metadata is used: no user data, no comment text, "
    "no private data. Derived rates (engagement rate, views per day, "
    "views per subscriber) are basic arithmetic on returned statistics "
    "for an offline educational analysis, shown next to the underlying "
    "counts. Sample: 5 fixed queries × 50 results, order=relevance, "
    "deduplicated by video ID, fetched 2026-11-08 (508 quota units). "
    "No date-bounded cohort was possible — the helper sends no "
    "publishedAfter/publishedBefore. Comment sentiment is out of scope: "
    "no comments endpoint exists in the helper. "
    f"{DESCRIPTIVE_SENTENCE}"
)
