"""Day 20 Inflation & Cost of Living Dashboard: charts.

Draws the 4 charts from the processed CSVs only (never from raw data).
All figures are 1280 px wide, labelled, drawn to scale.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

try:
    from src.data_pipeline import CATEGORIES
except ImportError:  # pragma: no cover - fallback for direct script runs
    from data_pipeline import CATEGORIES  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
CHARTS_DIR = ROOT / "outputs" / "charts"

FIGSIZE = (12.8, 7.2)
TITLE_SIZE = 15
LABEL_SIZE = 11

CATEGORY_LABELS = {
    "food_at_home": "Food at home",
    "energy": "Energy",
    "housing": "Housing",
    "transportation": "Transportation",
    "apparel": "Apparel",
    "medical_care": "Medical care",
    "education": "Education",
}


def _style(ax: plt.Axes, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=TITLE_SIZE, fontweight="bold", loc="left")
    ax.set_xlabel(xlabel, fontsize=LABEL_SIZE)
    ax.set_ylabel(ylabel, fontsize=LABEL_SIZE)
    ax.tick_params(labelsize=10)
    ax.grid(True, alpha=0.3)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)


def chart_headline_yoy(yoy_df: pd.DataFrame, out_path: Path) -> Path:
    """Headline + core YoY inflation with a 2% reference line."""
    dates = pd.to_datetime(yoy_df["date"])
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(dates, yoy_df["headline_yoy_pct"], label="Headline CPI (all items)", lw=2)
    ax.plot(dates, yoy_df["core_yoy_pct"], label="Core CPI (excl. food & energy)", lw=2)
    ax.axhline(2.0, color="grey", ls="--", lw=1.2, label="2% reference")
    peak_idx = yoy_df["headline_yoy_pct"].idxmax()
    peak_date = dates.iloc[int(peak_idx)]
    peak_val = float(yoy_df["headline_yoy_pct"].iloc[int(peak_idx)])
    ax.annotate(
        f"Peak {peak_val:.1f}% ({peak_date.strftime('%b %Y')})",
        xy=(peak_date, peak_val),
        xytext=(10, 18),
        textcoords="offset points",
        fontsize=11,
        arrowprops={"arrowstyle": "->", "color": "black"},
    )
    # The line dips below zero in deflation months (2009, 2015): the
    # axis must include the negative range or the line is clipped.
    low = min(0.0, float(yoy_df["headline_yoy_pct"].min()) - 0.5)
    ax.set_ylim(low, max(10.0, peak_val + 1.0))
    _style(
        ax,
        "Headline and core inflation, year on year (Mar 2006 – Oct 2026)",
        "Month",
        "Inflation, % per year",
    )
    ax.legend(fontsize=11, loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=100)
    plt.close(fig)
    return out_path


def chart_category_divergence(cum_df: pd.DataFrame, out_path: Path) -> Path:
    """Cumulative price change since Mar 2006 by category (latest month)."""
    latest = cum_df.iloc[-1]
    headline = float(latest["headline_cum_pct"])
    labels = [CATEGORY_LABELS[c] for c in CATEGORIES]
    values = [float(latest[f"{c}_cum_pct"]) for c in CATEGORIES]
    order = sorted(range(len(values)), key=lambda i: values[i])
    labels = [labels[i] for i in order]
    values = [values[i] for i in order]
    fig, ax = plt.subplots(figsize=FIGSIZE)
    colors = ["#c0392b" if v > headline else "#2e86ab" for v in values]
    ax.barh(labels, values, color=colors)
    ax.axvline(
        headline,
        color="black",
        ls="--",
        lw=1.5,
        label=f"Headline CPI: +{headline:.0f}%",
    )
    for i, v in enumerate(values):
        ax.text(
            v + 2,
            i,
            f"+{v:.0f}%",
            va="center",
            fontsize=11,
            # White backing so the label stays readable where it crosses
            # the dashed headline line (Transportation, +66%).
            bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none", "pad": 1.5},
        )
    ax.set_xlim(0, max(values) * 1.18)
    _style(
        ax,
        "What has risen most since Mar 2006? Cumulative price change to Oct 2026",
        "Cumulative price change since Mar 2006, %",
        "Category",
    )
    ax.legend(fontsize=11, loc="lower right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=100)
    plt.close(fig)
    return out_path


def chart_real_earnings(real_df: pd.DataFrame, out_path: Path) -> Path:
    """Nominal vs. real hourly earnings, indexed Mar 2006 = 100."""
    dates = pd.to_datetime(real_df["date"])
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(dates, real_df["nominal_indexed"], label="Nominal hourly earnings", lw=2)
    ax.plot(
        dates,
        real_df["real_indexed"],
        label="Real hourly earnings (Oct 2026 dollars)",
        lw=2,
    )
    ax.fill_between(
        dates,
        real_df["real_indexed"],
        real_df["nominal_indexed"],
        color="grey",
        alpha=0.15,
        label="Gap = inflation since Mar 2006",
    )
    last_real = float(real_df["real_indexed"].iloc[-1])
    last_nom = float(real_df["nominal_indexed"].iloc[-1])
    ax.annotate(
        f"Real pay +{last_real - 100:.1f}% since Mar 2006",
        xy=(dates.iloc[-1], last_real),
        xytext=(-180, -28),
        textcoords="offset points",
        fontsize=11,
        arrowprops={"arrowstyle": "->", "color": "black"},
    )
    ax.annotate(
        f"Nominal pay +{last_nom - 100:.0f}%",
        xy=(dates.iloc[-1], last_nom),
        xytext=(-150, 12),
        textcoords="offset points",
        fontsize=11,
        arrowprops={"arrowstyle": "->", "color": "black"},
    )
    _style(
        ax,
        "Has pay kept up with prices? Hourly earnings, indexed Mar 2006 = 100",
        "Month",
        "Index (Mar 2006 = 100)",
    )
    ax.legend(fontsize=11, loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=100)
    plt.close(fig)
    return out_path


def chart_basket_cost(basket_df: pd.DataFrame, out_path: Path) -> Path:
    """Fixed $100 (Mar 2006) basket cost + purchasing power of $1."""
    dates = pd.to_datetime(basket_df["date"])
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=FIGSIZE, sharex=True)
    ax1.plot(dates, basket_df["basket_cost_usd"], lw=2, color="#2e86ab")
    last_cost = float(basket_df["basket_cost_usd"].iloc[-1])
    ax1.annotate(
        f"${last_cost:.2f} in Oct 2026",
        xy=(dates.iloc[-1], last_cost),
        xytext=(-140, 10),
        textcoords="offset points",
        fontsize=11,
        arrowprops={"arrowstyle": "->", "color": "black"},
    )
    _style(
        ax1,
        "The 100-dollar basket: what 100 dollars of Mar 2006 shopping costs now",
        "",
        "Basket cost, USD",
    )
    ax2.plot(dates, basket_df["purchasing_power_usd"], lw=2, color="#c0392b")
    last_pp = float(basket_df["purchasing_power_usd"].iloc[-1])
    ax2.annotate(
        f"${last_pp:.2f} in Oct 2026",
        xy=(dates.iloc[-1], last_pp),
        xytext=(-160, 14),
        textcoords="offset points",
        fontsize=11,
        arrowprops={"arrowstyle": "->", "color": "black"},
    )
    _style(
        ax2,
        "Purchasing power of one dollar (1982–84 dollars)",
        "Month",
        "Value of one dollar, USD",
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=100)
    plt.close(fig)
    return out_path


def build_all() -> list[Path]:
    """Draw all 4 charts from the processed CSVs. Returns the file paths."""
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    yoy_df = pd.read_csv(PROCESSED_DIR / "yoy_inflation.csv")
    cum_df = pd.read_csv(PROCESSED_DIR / "category_cumulative.csv")
    real_df = pd.read_csv(PROCESSED_DIR / "real_earnings.csv")
    basket_df = pd.read_csv(PROCESSED_DIR / "basket_cost.csv")
    return [
        chart_headline_yoy(yoy_df, CHARTS_DIR / "01_headline_yoy.png"),
        chart_category_divergence(cum_df, CHARTS_DIR / "02_category_divergence.png"),
        chart_real_earnings(real_df, CHARTS_DIR / "03_real_earnings.png"),
        chart_basket_cost(basket_df, CHARTS_DIR / "04_basket_cost.png"),
    ]


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    del argv
    paths = build_all()
    for path in paths:
        print(f"wrote {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
