"""Generate the four static charts from data/processed/videos.csv.

Run: python3 -m src.make_charts  (from the project root, after the pipeline)
Exactly 4 PNGs, offline from the committed processed CSV only (no network,
no API). Every chart carries a "Source: YouTube Data API v3" footnote and,
when the data is synthetic, a SYNTHETIC DATA label.
Descriptive patterns only — never causal claims, never a guarantee of
future performance. Educational analysis only.
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
    from src.youtube_kpi import (
        BUCKET_LABELS,
        BUCKET_ORDER,
        TOPIC_LABELS,
        TOPIC_ORDER,
    )
except ImportError:  # run as a script: python src/make_charts.py
    from youtube_kpi import (  # type: ignore[no-redef]
        BUCKET_LABELS,
        BUCKET_ORDER,
        TOPIC_LABELS,
        TOPIC_ORDER,
    )

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHARTS_DIR = PROJECT_ROOT / "outputs" / "charts"

DOW_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
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
        "Source: YouTube Data API v3 | "
        "Descriptive pattern in this sample — not a causal finding",
        ha="left",
        fontsize=9,
        color="#555555",
    )
    if _synthetic():
        fig.text(
            0.99,
            y,
            "SYNTHETIC DATA — API unavailable on 2026-11-08",
            ha="right",
            color="red",
            fontweight="bold",
            fontsize=9,
        )


def _save(fig, name: str) -> None:
    fig.tight_layout(rect=[0, 0.04, 1, 0.96])
    fig.savefig(CHARTS_DIR / name, dpi=150)
    plt.close(fig)


def chart_01_views_by_topic(df: pd.DataFrame) -> None:
    grouped = (
        df.groupby("topic")["views_per_day"]
        .agg(["median", "count"])
        .reindex([t for t in TOPIC_ORDER if t in df["topic"].unique()])
    )
    overall = df["views_per_day"].median()
    fig, ax = plt.subplots(figsize=(10, 5.5))
    labels = [TOPIC_LABELS[t] for t in grouped.index]
    ax.barh(labels, grouped["median"], color="#2E86AB")
    ax.axvline(
        overall,
        color="#C0392B",
        linestyle="--",
        linewidth=1.5,
        label=f"Overall median: {overall:,.0f} views/day",
    )
    for i, (median, n) in enumerate(zip(grouped["median"], grouped["count"])):
        ax.text(
            median + overall * 0.03,
            i,
            f"{median:,.0f} views/day (n={int(n)})",
            va="center",
        )
    ax.set_xlabel("Median views per day")
    ax.set_title("Median views per day by topic")
    ax.legend()
    ax.set_xlim(0, max(grouped["median"].max() * 1.45, overall * 1.6))
    _source_note(fig)
    _save(fig, "01_views_by_topic.png")


def chart_02_duration_vs_performance(df: pd.DataFrame) -> None:
    grouped = (
        df.groupby("duration_bucket")
        .agg(
            med_vpd=("views_per_day", "median"),
            med_eng=("engagement_rate", "median"),
            n=("video_id", "count"),
        )
        .reindex([b for b in BUCKET_ORDER if b in df["duration_bucket"].unique()])
    )
    fig, ax = plt.subplots(figsize=(10, 5.5))
    labels = [BUCKET_LABELS[b] for b in grouped.index]
    x = np.arange(len(grouped))
    ax.bar(x, grouped["med_vpd"], color="#2E86AB", label="Median views/day")
    for i, (median, n) in enumerate(zip(grouped["med_vpd"], grouped["n"])):
        ax.text(
            i,
            median / 2,
            f"{median:,.0f}\n(n={int(n)})",
            ha="center",
            va="center",
            color="white",
            fontweight="bold",
            fontsize=9,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=12, ha="right")
    ax.set_ylabel("Median views per day")
    ax.set_ylim(0, grouped["med_vpd"].max() * 1.25)
    ax2 = ax.twinx()
    ax2.plot(
        x,
        grouped["med_eng"] * 100,
        color="#C0392B",
        marker="o",
        linewidth=2,
        label="Median engagement rate (%)",
    )
    for i, eng in enumerate(grouped["med_eng"]):
        ax2.text(
            i,
            eng * 100 + 0.45,
            f"{eng * 100:.2f}%",
            ha="center",
            color="#C0392B",
            fontsize=9,
        )
    ax2.set_ylabel("Median engagement rate (%)")
    ax2.set_ylim(0, max(grouped["med_eng"].max() * 100 * 1.4, 1.0))
    ax.set_title("Duration vs performance — median views/day and engagement")
    lines, labels_ = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels_ + labels2, loc="upper left")
    _source_note(fig)
    _save(fig, "02_duration_vs_performance.png")


def chart_03_publish_time_heatmap(df: pd.DataFrame) -> None:
    med = df.pivot_table(
        index="publish_dow",
        columns="publish_hour_utc",
        values="views_per_day",
        aggfunc="median",
    ).reindex(DOW_ORDER)
    counts = df.pivot_table(
        index="publish_dow",
        columns="publish_hour_utc",
        values="views_per_day",
        aggfunc="count",
    ).reindex(DOW_ORDER)
    hours = list(range(24))
    med = med.reindex(columns=hours)
    counts = counts.reindex(columns=hours)
    fig, ax = plt.subplots(figsize=(12, 5.5))
    data = med.values
    mesh = ax.pcolormesh(
        np.arange(25),
        np.arange(8),
        np.nan_to_num(data, nan=0.0),
        shading="flat",
        cmap="Blues",
        vmin=0,
        vmax=np.nanmax(data) if np.isfinite(np.nanmax(data)) else 1,
    )
    for r in range(7):
        for c in range(24):
            n = counts.values[r, c]
            value = data[r, c]
            if pd.isna(n) or n == 0:
                continue
            label = f"{value:,.0f}" if n >= 5 else f"{value:,.0f}\n(n={int(n)})"
            ax.text(
                c + 0.5,
                r + 0.5,
                label,
                ha="center",
                va="center",
                fontsize=7,
                color="white" if value > np.nanmax(data) * 0.6 else "black",
            )
    ax.set_xticks(np.arange(24) + 0.5)
    ax.set_xticklabels([str(h) for h in hours])
    ax.set_yticks(np.arange(7) + 0.5)
    ax.set_yticklabels(DOW_ORDER)
    ax.set_xlabel("Publish hour (UTC)")
    ax.set_ylabel("Publish day of week")
    ax.set_title("Median views per day by publish hour (UTC) and day of week")
    fig.colorbar(mesh, ax=ax, label="Median views per day")
    fig.text(
        0.01,
        0.055,
        "Cells with n < 5 are marked with their n. The channel audience "
        "timezone is unknown — this pattern is descriptive only, not a "
        "best time to post.",
        ha="left",
        fontsize=9,
        color="#555555",
    )
    _source_note(fig, y=0.01)
    _save(fig, "03_publish_time_heatmap.png")


def chart_04_engagement_scatter(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.5))
    high = df[df["high_performer"]]
    rest = df[~df["high_performer"]]
    ax.scatter(
        np.log10(rest["view_count"]),
        rest["engagement_rate"] * 100,
        s=28,
        alpha=0.6,
        color="#2E86AB",
        label=f"Rest (n={len(rest)})",
    )
    ax.scatter(
        np.log10(high["view_count"]),
        high["engagement_rate"] * 100,
        s=28,
        alpha=0.8,
        color="#C0392B",
        marker="D",
        label=f"Top quartile by views/day (n={len(high)})",
    )
    ax.set_xlabel("Views (log10 scale)")
    ax.set_ylabel("Engagement rate (%)")
    ax.set_title("Engagement vs reach — do high performers engage better?")
    ax.legend()
    _source_note(fig)
    _save(fig, "04_engagement_scatter.png")


def main() -> None:
    df = pd.read_csv(PROCESSED_DIR / "videos.csv")
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    # Remove any stale PNGs so the folder holds exactly the 4 charts.
    for stale in CHARTS_DIR.glob("*.png"):
        stale.unlink()
    chart_01_views_by_topic(df)
    chart_02_duration_vs_performance(df)
    chart_03_publish_time_heatmap(df)
    chart_04_engagement_scatter(df)
    print(f"Wrote 4 charts to {CHARTS_DIR}")


if __name__ == "__main__":
    main()
