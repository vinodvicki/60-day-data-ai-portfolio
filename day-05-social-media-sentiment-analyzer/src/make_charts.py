"""Generate the four static charts from data/processed/comments.csv.

Run: python3 -m src.make_charts  (from the project root, after the pipeline)
Exactly 4 PNGs, offline from the committed processed CSVs only (no network,
no API). Every chart carries a "Source: YouTube Data API v3" footnote and,
when the data is synthetic, a SYNTHETIC DATA label.
Sentiment is a model output from our own rule-based lexicon — never
presented as ground truth. Descriptive patterns only — never causal
claims. Educational analysis only.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:  # run as a module: python -m src.make_charts
    from src.sentiment import evaluate_predictions
except ImportError:  # run as a script: python src/make_charts.py
    from sentiment import evaluate_predictions  # type: ignore[no-redef]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHARTS_DIR = PROJECT_ROOT / "outputs" / "charts"

SENTIMENT_ORDER = ["positive", "neutral", "negative"]
SENTIMENT_COLORS = {
    "positive": "#2e7d32",
    "neutral": "#78909c",
    "negative": "#c62828",
}
SENTIMENT_LABELS = {
    "positive": "Positive",
    "neutral": "Neutral",
    "negative": "Negative",
}
TOPIC_LABELS = {
    "python": "Python",
    "ai_ml": "AI & ML",
    "sql": "SQL",
    "career": "Career",
    "bi_viz": "BI & Visualisation",
}
TOPIC_ORDER = ["python", "ai_ml", "sql", "career", "bi_viz"]
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
plt.rcParams.update(
    {"font.size": 11, "axes.titlesize": 13, "axes.labelsize": 11, "legend.fontsize": 10}
)


def _synthetic() -> bool:
    p = PROCESSED_DIR / "data_source.json"
    return bool(p.exists() and json.loads(p.read_text()).get("synthetic"))


def _source_note(fig, y=0.01):
    fig.text(
        0.01,
        y,
        "Source: YouTube Data API v3 | Sentiment as classified by our "
        "rule-based model — not ground truth",
        ha="left",
        fontsize=9,
        color="#555555",
    )
    if _synthetic():
        fig.text(
            0.99,
            y,
            "SYNTHETIC DATA — API unavailable on 2026-11-09",
            ha="right",
            color="red",
            fontweight="bold",
            fontsize=9,
        )


def _save(fig, name: str) -> None:
    fig.tight_layout(rect=[0, 0.04, 1, 0.96])
    fig.savefig(CHARTS_DIR / name, dpi=150)
    plt.close(fig)


def _monthly_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly sentiment shares (%, one row per month) with n."""
    months = sorted(df["month"].unique())
    rows = []
    for month in months:
        sub = df[df["month"] == month]
        row = {"month": month, "n": len(sub)}
        for label in SENTIMENT_ORDER:
            row[label] = (sub["sentiment"] == label).mean() * 100
        rows.append(row)
    return pd.DataFrame(rows)


def chart_01_sentiment_trend(df: pd.DataFrame) -> None:
    monthly = _monthly_frame(df)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    x = np.arange(len(monthly))
    bottom = np.zeros(len(monthly))
    for label in SENTIMENT_ORDER:
        values = monthly[label].to_numpy()
        ax.bar(
            x,
            values,
            bottom=bottom,
            color=SENTIMENT_COLORS[label],
            label=f"{SENTIMENT_LABELS[label]}",
            width=0.7,
        )
        bottom += values
    for i, row in monthly.iterrows():
        idx = list(monthly.index).index(i)
        thin = " (thin)" if row["n"] < 30 else ""
        ax.text(
            idx,
            102,
            f"n={int(row['n'])}{thin}",
            ha="center",
            fontsize=9,
            color="#333333",
        )
    ax.set_xticks(x)
    ax.set_xticklabels(monthly["month"], rotation=30, ha="right")
    ax.set_ylim(0, 112)
    ax.set_ylabel("Share of comments (%)")
    ax.set_title(
        "Sentiment trend — monthly share of comments by class\n"
        "(as classified by our rule-based model)"
    )
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3, frameon=False)
    _source_note(fig)
    _save(fig, "01_sentiment_trend.png")


def chart_02_sentiment_by_topic(df: pd.DataFrame) -> None:
    topics = [t for t in TOPIC_ORDER if t in set(df["topic"])]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(topics))
    bottom = np.zeros(len(topics))
    for label in SENTIMENT_ORDER:
        values = []
        for topic in topics:
            sub = df[df["topic"] == topic]
            values.append((sub["sentiment"] == label).mean() * 100)
        ax.bar(
            x,
            values,
            bottom=bottom,
            color=SENTIMENT_COLORS[label],
            label=SENTIMENT_LABELS[label],
            width=0.6,
        )
        bottom += np.array(values)
    for i, topic in enumerate(topics):
        n = int((df["topic"] == topic).sum())
        ax.text(i, 102, f"n={n}", ha="center", fontsize=10, color="#333333")
    ax.set_xticks(x)
    ax.set_xticklabels([TOPIC_LABELS[t] for t in topics])
    ax.set_ylim(0, 112)
    ax.set_ylabel("Share of comments (%)")
    ax.set_title(
        "Sentiment by video topic — share of comments per class\n"
        "(as classified by our rule-based model)"
    )
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)
    _source_note(fig)
    _save(fig, "02_sentiment_by_topic.png")


def chart_03_top_themes(df: pd.DataFrame) -> None:
    exploded = df.assign(theme=df["themes"].str.split(";")).explode("theme")
    order = exploded["theme"].value_counts().index.tolist()
    order = [t for t in order if t in THEME_LABELS]
    fig, ax = plt.subplots(figsize=(10, 6.0))
    y = np.arange(len(order))[::-1]
    left = np.zeros(len(order))
    for label in SENTIMENT_ORDER:
        values = []
        for theme in order:
            sub = exploded[exploded["theme"] == theme]
            values.append(int((sub["sentiment"] == label).sum()))
        ax.barh(
            y,
            values,
            left=left,
            color=SENTIMENT_COLORS[label],
            label=SENTIMENT_LABELS[label],
            height=0.6,
        )
        left += np.array(values)
    for i, theme in enumerate(order):
        total = int((exploded["theme"] == theme).sum())
        share = total / len(df) * 100
        ax.text(
            left[i] + 8,
            y[i],
            f"{total} ({share:.1f}%)",
            va="center",
            fontsize=10,
            color="#333333",
        )
    ax.set_yticks(y)
    ax.set_yticklabels([THEME_LABELS[t] for t in order])
    ax.set_xlabel("Comments carrying the theme (a comment can carry 2 themes)")
    ax.set_title(
        "Top themes — comments per theme, split by sentiment class\n"
        "(themes are fixed keyword lists; shares sum to over 100%)"
    )
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False)
    _source_note(fig)
    _save(fig, "03_top_themes.png")


def chart_04_validation_confusion(df: pd.DataFrame) -> None:
    labels_path = PROCESSED_DIR / "validation_labels.csv"
    labels = pd.read_csv(labels_path, dtype=str).fillna("")
    merged = df.merge(labels, on="comment_id", how="inner")
    evaluation = evaluate_predictions(
        merged["sentiment"].tolist(), merged["human_label"].tolist()
    )
    confusion = evaluation["confusion"]
    matrix = np.array(
        [[confusion[t][p] for p in SENTIMENT_ORDER] for t in SENTIMENT_ORDER]
    )
    fig, ax = plt.subplots(figsize=(9.5, 7.0))
    fig.subplots_adjust(bottom=0.20, top=0.84)
    ax.imshow(matrix, cmap="Blues", vmin=0)
    ax.set_xticks(range(3))
    ax.set_yticks(range(3))
    ax.set_xticklabels([SENTIMENT_LABELS[s] for s in SENTIMENT_ORDER])
    ax.set_yticklabels([SENTIMENT_LABELS[s] for s in SENTIMENT_ORDER])
    ax.set_xlabel("Predicted by the rule-based model")
    ax.set_ylabel("Human label")
    ax.set_title(
        f"Human validation — predicted vs human labels (n={evaluation['n']})\n"
        f"Accuracy {evaluation['accuracy']:.3f} · "
        f"Macro-F1 {evaluation['macro_f1']:.3f}"
    )
    for i in range(3):
        for j in range(3):
            value = int(matrix[i, j])
            color = "white" if value > matrix.max() * 0.6 else "#1a1a1a"
            ax.text(
                j,
                i,
                str(value),
                ha="center",
                va="center",
                fontsize=16,
                color=color,
                fontweight="bold",
            )
    lines = []
    for label in SENTIMENT_ORDER:
        m = evaluation["per_class"][label]
        lines.append(
            f"{SENTIMENT_LABELS[label]}: P={m['precision']:.2f} "
            f"R={m['recall']:.2f} F1={m['f1']:.2f} (n={m['support']})"
        )
    fig.text(0.5, 0.09, "  ·  ".join(lines), ha="center", fontsize=9, color="#333333")
    _source_note(fig, y=0.01)
    fig.savefig(CHARTS_DIR / "04_validation_confusion.png", dpi=150)
    plt.close(fig)


def main() -> None:
    df = pd.read_csv(PROCESSED_DIR / "comments.csv")
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    chart_01_sentiment_trend(df)
    chart_02_sentiment_by_topic(df)
    chart_03_top_themes(df)
    chart_04_validation_confusion(df)
    print(f"wrote 4 charts to {CHARTS_DIR} (n={len(df)} comments)")


if __name__ == "__main__":
    main()
