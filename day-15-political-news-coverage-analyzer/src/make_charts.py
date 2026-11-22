"""Charts for Day 15 — Political News Coverage Analyzer (exactly 4, matplotlib).

All charts are drawn from the committed processed CSVs only (offline).
Every chart is footnoted with the source (RSS feed URLs) + coverage
(outlets, window actually achieved per outlet, N per outlet,
title + description text only) + VADER version, states its N, and
uses one consistent outlet colour palette on every chart. Sentiment
charts use a single diverging scale centred at 0 with the VADER
thresholds (±0.05) marked. No chart title, axis label or caption
uses language about an outlet's fairness or accuracy: sentiment is
language tone only.
"""

from __future__ import annotations

import importlib.metadata
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from matplotlib.transforms import blended_transform_factory

try:
    from src.topics import TOPICS
except ImportError:  # pragma: no cover - running as a script from src/
    from topics import TOPICS  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
CHARTS = ROOT / "outputs" / "charts"

OUTLETS = ["NYT", "WSJ", "Fox News", "CNN", "NPR", "BBC News"]
PALETTE: dict[str, str] = {
    "NYT": "#1f77b4",
    "WSJ": "#ff7f0e",
    "Fox News": "#2ca02c",
    "CNN": "#d62728",
    "NPR": "#9467bd",
    "BBC News": "#8c564b",
}
GUARDRAIL_SHORT = "Sentiment is language tone, not factual bias."
WINDOW_LABEL = "2026-11-08–2026-11-22"


def _vader_version() -> str:
    """Pinned vaderSentiment version for footnotes."""
    try:
        return importlib.metadata.version("vaderSentiment")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _load() -> dict[str, pd.DataFrame]:
    """Load the processed tables the charts are drawn from."""
    return {
        "attention": pd.read_csv(PROC / "topic_attention.csv"),
        "by_outlet": pd.read_csv(PROC / "sentiment_by_outlet.csv"),
        "by_topic": pd.read_csv(PROC / "sentiment_by_topic.csv"),
    }


def _footnotes(fig: plt.Figure, data: dict[str, pd.DataFrame], extra: str = "") -> None:
    """Add the standard source + coverage footnotes to a figure.

    Long lines are wrapped so nothing runs off the figure edge.
    ``extra`` (if given) is printed as the first footnote line.
    """
    attention = data["attention"]
    totals = {
        outlet: int(
            attention.loc[
                (attention["outlet"] == outlet) & (attention["topic"] == TOPICS[0]),
                "outlet_total",
            ].iloc[0]
        )
        for outlet in OUTLETS
    }
    total = int(attention.loc[attention["outlet"] == "ALL", "n_articles"].sum())
    n_text = ", ".join(f"{o} {totals[o]}" for o in OUTLETS)
    lines = []
    if extra:
        lines.append(extra)
    lines.append(
        "Source: outlet RSS feeds — NYT, WSJ, Fox News, CNN, NPR, BBC News; "
        f"title + description text only; window {WINDOW_LABEL}; "
        f"VADER vaderSentiment {_vader_version()}."
    )
    lines.append(
        f"Corpus: {total} articles; N per outlet: {n_text}. "
        "Window actually achieved per outlet in data_source.json. "
        "WSJ and CNN returned no usable articles in the window (n=0)."
    )
    lines.append(GUARDRAIL_SHORT)
    wrapped = "\n".join("\n".join(textwrap.wrap(line, width=125)) for line in lines)
    fig.text(
        0.01,
        0.005,
        wrapped,
        fontsize=7,
        color="#555555",
        ha="left",
        va="bottom",
    )


def build_chart_01(root: Path = ROOT) -> Path:
    """Attention share by topic and outlet (plan §7 chart 01)."""
    proc = root / "data" / "processed"
    attention = pd.read_csv(proc / "topic_attention.csv")
    corpus = attention[attention["outlet"] == "ALL"].copy()
    corpus = corpus.sort_values("attention_share_pct", ascending=False)
    topic_order = list(corpus["topic"])
    fig, axes = plt.subplots(2, 3, figsize=(14, 10), sharex=True)
    for ax, outlet in zip(axes.flat, OUTLETS):
        sub = attention[attention["outlet"] == outlet].set_index("topic")
        shares = [float(sub.loc[t, "attention_share_pct"]) for t in topic_order]
        counts = [int(sub.loc[t, "n_articles"]) for t in topic_order]
        total = int(sub["outlet_total"].iloc[0])
        y = np.arange(len(topic_order))
        ax.barh(
            y,
            shares,
            color=PALETTE[outlet],
            height=0.7,
            edgecolor="white",
        )
        ax.set_yticks(y)
        ax.set_yticklabels(topic_order, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlim(0, 78)
        ax.set_xlabel("Share of outlet's corpus (%)", fontsize=8)
        ax.set_title(f"{outlet} (n={total})", fontsize=10)
        ax.grid(axis="x", alpha=0.3)
        for yi, share, count in zip(y, shares, counts):
            if share > 0:
                ax.text(
                    share + 1,
                    yi,
                    f"{share:.1f}% (n={count})",
                    va="center",
                    fontsize=7,
                )
    fig.suptitle(
        "Attention share by topic and outlet — share of each outlet's corpus, "
        f"{WINDOW_LABEL}",
        fontsize=13,
    )
    fig.tight_layout(rect=(0, 0.08, 1, 0.96))
    data = _load()
    _footnotes(fig, data)
    out = root / "outputs" / "charts" / "01_attention_share_by_topic.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def build_chart_02(root: Path = ROOT) -> Path:
    """Mean VADER compound by outlet with 95% CI (plan §7 chart 02)."""
    proc = root / "data" / "processed"
    by_outlet = pd.read_csv(proc / "sentiment_by_outlet.csv")
    has_data = by_outlet[by_outlet["n"] > 0].copy()
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(has_data))
    means = has_data["mean_compound"].to_numpy(dtype=float)
    low = has_data["ci_low"].to_numpy(dtype=float)
    high = has_data["ci_high"].to_numpy(dtype=float)
    colours = [PALETTE[o] for o in has_data["outlet"]]
    ax.errorbar(
        x,
        means,
        yerr=[means - low, high - means],
        fmt="none",
        capsize=6,
        color="#333333",
        ecolor="#333333",
    )
    ax.scatter(x, means, s=120, c=colours, zorder=3, edgecolor="white")
    ax.axhline(0.05, color="#888888", linestyle="--", linewidth=1)
    ax.axhline(-0.05, color="#888888", linestyle="--", linewidth=1)
    ax.axhline(0.0, color="#bbbbbb", linestyle="-", linewidth=0.8)
    label_transform = blended_transform_factory(ax.transAxes, ax.transData)
    ax.text(
        0.50,
        0.05,
        "VADER +0.05",
        fontsize=8,
        color="#555555",
        transform=label_transform,
        va="bottom",
        ha="center",
    )
    ax.text(
        0.50,
        -0.05,
        "VADER -0.05",
        fontsize=8,
        color="#555555",
        transform=label_transform,
        va="top",
        ha="center",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{row['outlet']}\n(n={int(row['n'])})" for _, row in has_data.iterrows()],
        fontsize=10,
    )
    ax.set_ylabel("Mean VADER compound", fontsize=10)
    ax.set_ylim(-1.0, 1.0)
    ax.set_title(
        "Mean language sentiment (VADER compound) by outlet\n"
        f"title + description text only, {WINDOW_LABEL}",
        fontsize=12,
    )
    ax.grid(axis="y", alpha=0.3)
    for xi, row in enumerate(has_data.itertuples()):
        ax.text(
            xi,
            float(row.mean_compound) + 0.14,
            f"{float(row.mean_compound):.3f}",
            ha="center",
            fontsize=9,
        )
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    data = _load()
    _footnotes(
        fig,
        data,
        extra="WSJ and CNN returned no usable articles in the window (n=0), "
        "so no mean is shown for them.",
    )
    out = root / "outputs" / "charts" / "02_mean_sentiment_by_outlet.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def build_chart_03(root: Path = ROOT) -> Path:
    """Mean VADER compound by topic x outlet heatmap (plan §7 chart 03)."""
    proc = root / "data" / "processed"
    by_topic = pd.read_csv(proc / "sentiment_by_topic.csv")
    corpus = pd.read_csv(proc / "topic_attention.csv")
    corpus = corpus[corpus["outlet"] == "ALL"].sort_values(
        "attention_share_pct", ascending=False
    )
    topic_order = list(corpus["topic"])
    values = np.full((len(OUTLETS), len(topic_order)), np.nan)
    counts = np.zeros((len(OUTLETS), len(topic_order)), dtype=int)
    for i, outlet in enumerate(OUTLETS):
        for j, topic in enumerate(topic_order):
            match = by_topic[
                (by_topic["outlet"] == outlet) & (by_topic["topic"] == topic)
            ]
            if not match.empty:
                values[i, j] = float(match["mean_compound"].iloc[0])
                counts[i, j] = int(match["n"].iloc[0])
    fig, ax = plt.subplots(figsize=(13, 6))
    masked = np.ma.masked_invalid(values)
    image = ax.imshow(masked, cmap="coolwarm", vmin=-1.0, vmax=1.0, aspect="auto")
    ax.set_xticks(np.arange(len(topic_order)))
    ax.set_xticklabels(topic_order, fontsize=8, rotation=35, ha="right")
    ax.set_yticks(np.arange(len(OUTLETS)))
    ax.set_yticklabels(OUTLETS, fontsize=10)
    for i in range(len(OUTLETS)):
        for j in range(len(topic_order)):
            n = counts[i, j]
            if n == 0:
                ax.text(
                    j,
                    i,
                    "no data",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="#555555",
                )
            elif n < 5:
                ax.add_patch(
                    Rectangle(
                        (j - 0.5, i - 0.5),
                        1,
                        1,
                        fill=False,
                        hatch="///",
                        edgecolor="#333333",
                        linewidth=0,
                    )
                )
                ax.text(
                    j,
                    i,
                    f"{values[i, j]:.2f}\nn={n}\nsmall n",
                    ha="center",
                    va="center",
                    fontsize=7,
                )
            else:
                ax.text(
                    j,
                    i,
                    f"{values[i, j]:.2f}\nn={n}",
                    ha="center",
                    va="center",
                    fontsize=8,
                )
    fig.colorbar(image, ax=ax, label="Mean VADER compound")
    ax.set_title(
        "Mean language sentiment (VADER compound) by topic and outlet, "
        f"{WINDOW_LABEL}",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    data = _load()
    _footnotes(
        fig,
        data,
        extra="Cells with n < 5 are hatched and labelled 'small n'. "
        "WSJ and CNN rows have no data (n=0 in the window).",
    )
    out = root / "outputs" / "charts" / "03_sentiment_by_topic_heatmap.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def build_chart_04(root: Path = ROOT) -> Path:
    """Sentiment-label mix by outlet, 100% stacked bars (plan §7 chart 04)."""
    proc = root / "data" / "processed"
    by_outlet = pd.read_csv(proc / "sentiment_by_outlet.csv")
    fig, ax = plt.subplots(figsize=(10, 6))
    y = np.arange(len(OUTLETS), dtype=float)
    colours = {"positive": "#2ca02c", "neutral": "#bbbbbb", "negative": "#d62728"}
    left = np.zeros(len(OUTLETS))
    for label, key in [
        ("positive", "pct_positive"),
        ("neutral", "pct_neutral"),
        ("negative", "pct_negative"),
    ]:
        widths = []
        for outlet in OUTLETS:
            row = by_outlet[by_outlet["outlet"] == outlet]
            widths.append(float(row[key].iloc[0]) if not row.empty else 0.0)
        widths_arr = np.array(widths)
        ax.barh(
            y,
            widths_arr,
            left=left,
            color=colours[label],
            height=0.6,
            edgecolor="white",
            label=label,
        )
        for yi, width, start in zip(y, widths_arr, left):
            if width >= 8:
                ax.text(
                    start + width / 2,
                    yi,
                    f"{width:.1f}%",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white",
                )
        left = left + widths_arr
    ax.set_yticks(y)
    ax.set_yticklabels(
        [
            f"{o} (n={int(by_outlet.loc[by_outlet['outlet'] == o, 'n'].iloc[0])})"
            for o in OUTLETS
        ],
        fontsize=10,
    )
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of outlet's articles (%)", fontsize=10)
    ax.set_title(
        "Share of articles by language-sentiment label and outlet "
        f"(VADER ±0.05), {WINDOW_LABEL}",
        fontsize=12,
    )
    ax.legend(
        title="Language-sentiment label",
        loc="upper center",
        bbox_to_anchor=(0.5, -0.28),
        ncol=3,
    )
    ax.grid(axis="x", alpha=0.3)
    for row_index, outlet in enumerate(OUTLETS):
        n = int(by_outlet.loc[by_outlet["outlet"] == outlet, "n"].iloc[0])
        if n == 0:
            ax.text(
                1,
                row_index,
                "no articles in window (n=0)",
                va="center",
                fontsize=8,
                color="#555555",
            )
    fig.tight_layout(rect=(0, 0.22, 1, 1))
    data = _load()
    _footnotes(fig, data)
    out = root / "outputs" / "charts" / "04_sentiment_distribution.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def main() -> None:
    """Build all four charts from the processed CSVs."""
    paths = [
        build_chart_01(),
        build_chart_02(),
        build_chart_03(),
        build_chart_04(),
    ]
    for path in paths:
        print(f"{path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
