"""Day 5 — Social Media Sentiment Analyzer: Streamlit dashboard.

Reads only the committed processed CSVs (no network, no API).
Sentiment is a model output from our own rule-based lexicon — never
presented as ground truth; the validation panel shows how far the model
can be trusted. Descriptive patterns only — never causal claims.
Educational analysis only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

try:  # run as a module: streamlit run src/app.py
    from src.sentiment import evaluate_predictions
except ImportError:  # run as a script
    from sentiment import evaluate_predictions  # type: ignore[no-redef]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHARTS_DIR = PROJECT_ROOT / "outputs" / "charts"

TOPIC_LABELS = {
    "python": "Python",
    "ai_ml": "AI & ML",
    "sql": "SQL",
    "career": "Career",
    "bi_viz": "BI & Visualisation",
}
THEME_LABELS = {
    "praise": "Praise",
    "tutorial_quality": "Tutorial quality",
    "requests": "Requests",
    "career": "Career",
    "criticism": "Criticism",
    "questions": "Questions",
    "audio_video": "Audio / video",
    "price_cost": "Price / cost",
    "humor": "Humour",
    "other": "Other (no theme matched)",
}
SENTIMENT_LABELS = {
    "positive": "Positive",
    "neutral": "Neutral",
    "negative": "Negative",
}
MODEL_SENTENCE = (
    "Sentiment below is as classified by our own rule-based model — "
    "it is not ground truth. The model scores 0.617 accuracy / 0.613 macro-F1 "
    "against 120 human-labelled comments (see Validation); treat every "
    "sentiment share as a model estimate, not a measurement of how viewers feel."
)

st.set_page_config(
    page_title="Social Media Sentiment Analyzer",
    page_icon="💬",
    layout="wide",
)
st.title("Social Media Sentiment Analyzer")
st.markdown(f"*{MODEL_SENTENCE}*")

comments = pd.read_csv(PROCESSED_DIR / "comments.csv")
source = json.loads((PROCESSED_DIR / "data_source.json").read_text())
labels = pd.read_csv(PROCESSED_DIR / "validation_labels.csv", dtype=str).fillna("")
evaluation = evaluate_predictions(
    comments.merge(labels, on="comment_id")["sentiment"].tolist(),
    comments.merge(labels, on="comment_id")["human_label"].tolist(),
)

if source.get("synthetic"):
    st.error(
        "SYNTHETIC DATA — API unavailable on 2026-11-09. "
        "Findings on this data have no interpretation."
    )

st.caption(
    f"Top-level public comments on 12 data/AI YouTube videos, "
    f"{source['window_start'][:10]} → {source['window_end'][:10]} · "
    f"Fetched live 2026-11-09 · {source['comment_count_fetched']:,} threads fetched, "
    f"{source['comment_count_analysed']:,} analysed · "
    f"Quota used: {source['quota_units_used']} units. "
    f"Data from the YouTube Data API v3."
)

# --- Sidebar filters -----------------------------------------------------------
topics = st.sidebar.multiselect(
    "Topic",
    options=sorted(comments["topic"].unique()),
    default=sorted(comments["topic"].unique()),
    format_func=lambda t: TOPIC_LABELS.get(t, t),
)
videos = st.sidebar.multiselect(
    "Video",
    options=sorted(comments["video_id"].unique()),
    default=sorted(comments["video_id"].unique()),
    format_func=lambda v: comments.loc[comments["video_id"] == v, "video_title"].iloc[
        0
    ][:48],
)
sentiments = st.sidebar.multiselect(
    "Sentiment (as classified by the model)",
    options=["positive", "neutral", "negative"],
    default=["positive", "neutral", "negative"],
    format_func=lambda s: SENTIMENT_LABELS[s],
)
if not topics or not videos or not sentiments:
    st.warning("Select at least one topic, one video and one sentiment class.")
    st.stop()

filtered = comments[
    comments["topic"].isin(topics)
    & comments["video_id"].isin(videos)
    & comments["sentiment"].isin(sentiments)
]
if filtered.empty:
    st.info("No comments match the current filters.")
    st.stop()

# --- Concentration note ---------------------------------------------------------
top_video = comments["video_id"].value_counts(normalize=True)
top_share = top_video.iloc[0] * 100
if top_share > 40:
    st.warning(
        f"One video ({top_video.index[0]}) contributes {top_share:.1f}% of the "
        "analysed comments — findings are dominated by that video's audience."
    )

# --- KPI summary ------------------------------------------------------------------
st.subheader("How do the comments break down? (as classified by the model)")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Analysed comments", f"{len(filtered):,}")
for col, label in zip(
    (col2, col3, col4), ("positive", "neutral", "negative"), strict=True
):
    share = (filtered["sentiment"] == label).mean() * 100
    col.metric(f"{SENTIMENT_LABELS[label]} (model)", f"{share:.1f}%")
col5.metric("Validation macro-F1", f"{evaluation['macro_f1']:.3f}")
st.caption(
    f"Across all {len(comments):,} analysed comments: "
    f"{(comments['sentiment'] == 'positive').mean() * 100:.1f}% positive, "
    f"{(comments['sentiment'] == 'neutral').mean() * 100:.1f}% neutral, "
    f"{(comments['sentiment'] == 'negative').mean() * 100:.1f}% negative "
    f"(as classified by the model). {(comments['scored_words'] == 0).mean() * 100:.1f}% "
    "of comments matched no lexicon word and are neutral by default, not by meaning."
)

# --- Charts ------------------------------------------------------------------------
st.subheader("1 · Sentiment trend by month")
st.image(str(CHARTS_DIR / "01_sentiment_trend.png"), width="stretch")
st.caption(
    "Monthly shares with n per month; November 2025 (n=14) is thin. The video mix "
    "changes month to month, so the trend partly reflects which videos were active."
)
st.subheader("2 · Sentiment by video topic")
st.image(str(CHARTS_DIR / "02_sentiment_by_topic.png"), width="stretch")
st.caption(
    "AI & ML draws the most negative-classified comments (13.3%) and the least "
    "positive (22.8%) — the 60 Minutes AI episode is the most "
    "negative-classified video in the topic (20.2%)."
)
st.subheader("3 · Top themes")
st.image(str(CHARTS_DIR / "03_top_themes.png"), width="stretch")
st.caption(
    "59.0% of comments matched no theme (`other`) — the fixed lists missed the "
    "large Google Data Analytics course-cohort check-in pattern. Reported, not re-tuned."
)

# --- Theme table ---------------------------------------------------------------------
st.subheader("Themes — counts, shares and sentiment split")
exploded = filtered.assign(theme=filtered["themes"].str.split(";")).explode("theme")
theme_rows = []
for theme, sub in exploded.groupby("theme"):
    theme_rows.append(
        {
            "Theme": THEME_LABELS.get(theme, theme),
            "Comments": len(sub),
            "Share": f"{len(sub) / len(filtered) * 100:.1f}%",
            "Positive": f"{(sub['sentiment'] == 'positive').mean() * 100:.1f}%",
            "Neutral": f"{(sub['sentiment'] == 'neutral').mean() * 100:.1f}%",
            "Negative": f"{(sub['sentiment'] == 'negative').mean() * 100:.1f}%",
        }
    )
theme_table = pd.DataFrame(theme_rows).sort_values("Comments", ascending=False)
st.dataframe(theme_table, width="stretch", hide_index=True)
st.caption("A comment can carry 2 themes, so theme shares sum to over 100%.")

# --- Example excerpts (short, no author names) ---------------------------------------
st.subheader("What the themes sound like — short excerpts")
for theme in theme_table["Theme"]:
    raw_theme = next(k for k, v in THEME_LABELS.items() if v == theme)
    examples = exploded[exploded["theme"] == raw_theme].head(12)
    shorts = [t for t in examples["text"].tolist() if 10 <= len(t) <= 120][:3]
    if not shorts:
        continue
    st.markdown(f"**{theme}**")
    for excerpt in shorts:
        st.markdown(f"> {excerpt}")

# --- Validation panel ------------------------------------------------------------------
st.subheader("4 · Human validation — how far can the model be trusted?")
st.image(str(CHARTS_DIR / "04_validation_confusion.png"), width="stretch")
st.markdown(
    f"**Accuracy {evaluation['accuracy']:.3f} · Macro-F1 {evaluation['macro_f1']:.3f} "
    f"(n={evaluation['n']} human-labelled comments, 40 per predicted class).** "
    "The model over-predicts negative (precision 0.48) and misses praise: "
    "12 of 52 truly positive comments were classified neutral and 10 negative. "
    "A lexicon baseline, not a trained model — do not use these sentiment "
    "shares for decisions."
)
confusion = evaluation["confusion"]
conf_df = pd.DataFrame(confusion).T.rename_axis("Human \\ Predicted")
st.dataframe(conf_df, width="stretch")
for label, metrics in evaluation["per_class"].items():
    st.markdown(
        f"- **{SENTIMENT_LABELS[label]}**: precision {metrics['precision']:.2f}, "
        f"recall {metrics['recall']:.2f}, F1 {metrics['f1']:.2f} "
        f"(support {metrics['support']})"
    )

st.divider()
st.markdown(
    "Sentiment patterns here describe the comments on these 12 videos. "
    "They are descriptive, not causal, and are not a guarantee of anything "
    "about YouTube comments in general. Data from the YouTube Data API v3 — "
    "see [YouTube's Terms of Service](https://www.youtube.com/t/terms). "
    "Code is MIT; YouTube data is under separate YouTube terms."
)
