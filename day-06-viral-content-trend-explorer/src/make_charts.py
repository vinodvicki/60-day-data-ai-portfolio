"""Generate the four static charts from data/processed/*.csv.

Run: python3 -m src.make_charts  (from the project root, after the pipeline)
Exactly 4 PNGs, offline from the committed processed CSVs only (no network,
no API). Every chart carries a "Source: YouTube Data API v3" footnote and,
when the data is synthetic, a SYNTHETIC DATA label.

Honest-chart rules for this day: Window A has no videos aged >= 7 days
(all 236 were published 2026-11-08/09), so chart 03 has no Window A
velocity bars — the gap is shown and labelled, never filled in. The
sentiment snapshot has 0 videos for the same reason, so chart 04 states
that plainly instead of drawing an empty plot. W9 is partial (5 days)
and is marked on chart 02.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHARTS_DIR = PROJECT_ROOT / "outputs" / "charts"

TOPIC_LABELS = {
    "python": "Python",
    "ai_ml": "AI & Machine Learning",
    "sql": "SQL",
    "career": "Career",
    "bi_viz": "BI & Visualisation",
    "general": "General Data Analytics",
    "other": "Other",
}
TOPIC_ORDER = ["python", "ai_ml", "sql", "career", "bi_viz", "general", "other"]
CLASS_COLORS = {
    "accelerating": "#2e7d32",
    "fading": "#c62828",
    "stable": "#78909c",
    "insufficient data": "#bdbdbd",
    "no prior baseline": "#ffb300",
}
WEEK_LABELS = {
    "W1": "w/c 2026-09-11",
    "W2": "w/c 2026-09-18",
    "W3": "w/c 2026-09-25",
    "W4": "w/c 2026-10-02",
    "W5": "w/c 2026-10-09",
    "W6": "w/c 2026-10-16",
    "W7": "w/c 2026-10-23",
    "W8": "w/c 2026-10-30",
    "W9": "w/c 2026-11-06*",
}
plt.rcParams.update(
    {"font.size": 11, "axes.titlesize": 13, "axes.labelsize": 11, "legend.fontsize": 10}
)


def _synthetic() -> bool:
    p = PROCESSED_DIR / "data_source.json"
    return bool(p.exists() and json.loads(p.read_text()).get("synthetic"))


def _source_note(fig, note: str, y=0.01):
    fig.text(
        0.01,
        y,
        f"Source: YouTube Data API v3 | {note}",
        ha="left",
        va="bottom",
        fontsize=9,
        color="#555555",
    )
    if _synthetic():
        fig.text(
            0.99,
            y,
            "SYNTHETIC DATA — API unavailable on 2026-11-10",
            ha="right",
            color="red",
            fontweight="bold",
            fontsize=9,
        )


def _save(fig, name: str) -> None:
    fig.tight_layout(rect=[0, 0.04, 1, 0.96])
    fig.savefig(CHARTS_DIR / name, dpi=150)
    plt.close(fig)


def chart_01_momentum(table: pd.DataFrame) -> None:
    """Per-topic share change (pp) and volume growth (%) with thresholds."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    labels = [
        f"{TOPIC_LABELS[t]}\nn {int(a)}/{int(b)}"
        for t, a, b in zip(table["topic"], table["n_A"], table["n_B"], strict=True)
    ]
    colors = [CLASS_COLORS[c] for c in table["classification"]]
    x = np.arange(len(table))
    ax = axes[0]
    ax.bar(x, table["share_change_pp"], color=colors)
    ax.axhline(3, color="#2e7d32", linestyle="--", linewidth=1)
    ax.axhline(-3, color="#c62828", linestyle="--", linewidth=1)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylim(-10.5, 8.5)
    ax.set_xticks(x, labels, rotation=30, ha="right")
    ax.set_ylabel("Share change (percentage points)")
    ax.set_title("Share change, recent vs prior window")
    for xi, value in zip(x, table["share_change_pp"], strict=True):
        ax.text(
            xi,
            value + (0.4 if value >= 0 else -1.1),
            f"{value:+.1f}",
            ha="center",
            fontsize=9,
        )
    ax = axes[1]
    growth_pct = table["volume_growth"] * 100
    ax.bar(x, growth_pct, color=colors)
    ax.axhline(20, color="#2e7d32", linestyle="--", linewidth=1)
    ax.axhline(-20, color="#c62828", linestyle="--", linewidth=1)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylim(-42, 62)
    ax.set_xticks(x, labels, rotation=30, ha="right")
    ax.set_ylabel("Volume growth (%)")
    ax.set_title("Publish-volume growth, recent vs prior window")
    for xi, value in zip(x, growth_pct, strict=True):
        ax.text(
            xi,
            value + (1.5 if value >= 0 else -4),
            f"{value:+.0f}%",
            ha="center",
            fontsize=9,
        )
    fig.suptitle("Trend momentum: which topics gained or lost share (in this sample)")
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=color) for color in CLASS_COLORS.values()
    ]
    axes[0].legend(handles, list(CLASS_COLORS), loc="lower right", fontsize=9)
    _source_note(
        fig,
        "Dashed lines: ±3 pp share / ±20% volume thresholds. "
        "n shown as recent/prior counts.",
    )
    _save(fig, "01_trend_momentum.png")


def chart_02_weekly_volume(videos: pd.DataFrame) -> None:
    """Weekly publish volume per topic (stacked bars) + 2-week rolling mean."""
    weeks = list(WEEK_LABELS)
    totals = videos.groupby("week").size().reindex(weeks, fill_value=0)
    topic_counts = {
        topic: videos[videos["topic"] == topic]
        .groupby("week")
        .size()
        .reindex(weeks, fill_value=0)
        for topic in TOPIC_ORDER
    }
    fig, ax = plt.subplots(figsize=(12, 5.5))
    x = np.arange(len(weeks))
    bottom = np.zeros(len(weeks))
    palette = plt.cm.tab10.colors
    for i, topic in enumerate(TOPIC_ORDER):
        values = topic_counts[topic].to_numpy(dtype=float)
        ax.bar(
            x,
            values,
            bottom=bottom,
            label=TOPIC_LABELS[topic],
            color=palette[i % len(palette)],
        )
        bottom += values
    rolling = [totals.iloc[0]]
    for i in range(1, len(totals)):
        rolling.append((totals.iloc[i - 1] + totals.iloc[i]) / 2)
    ax.plot(
        x,
        rolling,
        color="black",
        marker="o",
        linewidth=2,
        label="2-week rolling mean (all topics)",
    )
    ax.set_xticks(x, [WEEK_LABELS[w] for w in weeks], rotation=30, ha="right")
    ax.set_ylabel("Videos published per week")
    ax.set_title("Weekly publish volume per topic (in this sample)")
    ax.legend(ncol=2, loc="upper left")
    for xi, total in enumerate(totals):
        if total:
            ax.text(xi, total + 4, str(int(total)), ha="center", fontsize=9)
    _source_note(
        fig,
        "Weekly buckets anchored 2026-09-11. Thin weeks flagged.\n"
        "W1–W3, W6–W8 are empty: each query-window returned only "
        "its newest 50 videos (truncation — see data/README.md). "
        "*W9 is partial (5 days, 2026-11-06 → 11-10).",
    )
    _save(fig, "02_weekly_volume.png")


def chart_03_velocity(table: pd.DataFrame) -> None:
    """Median views/day per topic per window, with median age and n."""
    fig, ax = plt.subplots(figsize=(12, 5.5))
    labels = [TOPIC_LABELS[t] for t in table["topic"]]
    x = np.arange(len(table))
    width = 0.38
    med_a = table["median_views_per_day_A"].to_numpy(dtype=float)
    med_b = table["median_views_per_day_B"].to_numpy(dtype=float)
    has_a = ~np.isnan(med_a)
    has_b = ~np.isnan(med_b)
    ax.bar(
        x[has_b] - width / 2,
        med_b[has_b],
        width,
        label="Prior window (B)",
        color="#78909c",
    )
    if has_a.any():
        ax.bar(
            x[has_a] + width / 2,
            med_a[has_a],
            width,
            label="Recent window (A)",
            color="#1565c0",
        )
    else:
        ax.bar([], [], width, label="Recent window (A) — no data", color="#1565c0")
    ax.set_xticks(x, labels, rotation=30, ha="right")
    ax.set_ylabel("Median views per day")
    ax.set_title("Velocity: median views per day by topic and window")
    for xi in range(len(table)):
        row = table.iloc[xi]
        if has_b[xi]:
            ax.text(
                xi - width / 2,
                row["median_views_per_day_B"] + 1,
                f"{row['median_views_per_day_B']:.1f}\n"
                f"age {row['median_age_B']:.0f}d, n={int(row['velocity_n_B'])}",
                ha="center",
                fontsize=8,
            )
        if has_a[xi]:
            ax.text(
                xi + width / 2,
                row["median_views_per_day_A"] + 1,
                f"{row['median_views_per_day_A']:.1f}\n"
                f"age {row['median_age_A']:.0f}d, n={int(row['velocity_n_A'])}",
                ha="center",
                fontsize=8,
            )
    ax.legend()
    ax.text(
        0.01,
        0.96,
        "Recent-window velocity is not computable: all 236 recent videos "
        "were published\n2026-11-08/09, so none is aged ≥ 7 days. "
        "Velocity change is undefined for every topic.",
        transform=ax.transAxes,
        va="top",
        fontsize=9,
        color="#555555",
    )
    _source_note(fig, "Age ≥ 7 days only. Median age and n on every bar.")
    _save(fig, "03_views_velocity.png")


def chart_04_sentiment(comments: pd.DataFrame) -> None:
    """Mean compound + positive/negative share for the sentiment videos."""
    fig, ax = plt.subplots(figsize=(12, 5.5))
    if comments.empty:
        ax.text(
            0.5,
            0.5,
            "No sentiment snapshot: no eligible video.\n"
            "The mood snapshot needs the top video by views per day in "
            "each topic\nin the recent window, aged ≥ 7 days — but all "
            "236 recent videos were\npublished 2026-11-08/09, so none "
            "qualifies. 0 videos, 0 comments analysed.",
            ha="center",
            va="center",
            fontsize=12,
        )
        ax.set_title("Audience mood on the fastest-rising video per topic")
        ax.set_axis_off()
        _source_note(
            fig,
            "No videos qualified for the sentiment snapshot — "
            "0 videos, 0 comments analysed.",
        )
        _save(fig, "04_sentiment_mood.png")
        return
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
    labels = [
        f"{TOPIC_LABELS[t]}\n({vid[:8]}…)"
        for vid, t in zip(summary["video_id"], summary["topic"], strict=True)
    ]
    x = np.arange(len(summary))
    ax.bar(x, summary["mean_compound"], color="#1565c0")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x, labels, rotation=30, ha="right")
    ax.set_ylabel("Mean compound score")
    ax.set_title("Audience mood on the fastest-rising video per topic")
    for xi, row in zip(x, summary.itertuples(), strict=True):
        ax.text(
            xi,
            row.mean_compound + 0.02,
            f"{row.mean_compound:.2f} · +{row.positive:.0f}% / "
            f"−{row.negative:.0f}% · n={int(row.n)}",
            ha="center",
            fontsize=9,
        )
    _source_note(
        fig, "As classified by our rule-based model — " "five videos, not the topics."
    )
    _save(fig, "04_sentiment_mood.png")


def main() -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    videos = pd.read_csv(PROCESSED_DIR / "videos.csv")
    comments = pd.read_csv(PROCESSED_DIR / "comments.csv")
    table = pd.read_csv(PROCESSED_DIR / "trend_table.csv")
    chart_01_momentum(table)
    chart_02_weekly_volume(videos)
    chart_03_velocity(table)
    chart_04_sentiment(comments)
    print(f"wrote 4 charts to {CHARTS_DIR}")


if __name__ == "__main__":
    main()
