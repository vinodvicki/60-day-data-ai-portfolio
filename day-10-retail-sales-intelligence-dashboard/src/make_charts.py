"""Generate the four static charts from data/processed/*.csv.

Run: python -m src.make_charts  (from the project root, after the pipeline)
Exactly 4 PNGs, offline from the committed processed CSVs only (no network,
no API). Every chart carries the source footnote (UCI Online Retail, Chen
2015, DOI 10.24432/C5BW33, CC BY 4.0) and the disclaimer that this is
historical 2010–2011 data, not a current-market tool. When the data is
synthetic, every chart carries a SYNTHETIC DATA label.

Honest-chart rules for this day: revenue axes start at 0; the partial
Dec 2011 month is hatched and flagged, never silently plotted as a full
month; the forecast chart shows the 80% and 95% intervals as shaded
bands around the point forecast; no truncated axes.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHARTS_DIR = PROJECT_ROOT / "outputs" / "charts"

SOURCE_FOOTNOTE = (
    "Source: UCI Online Retail (Chen 2015), DOI 10.24432/C5BW33, CC BY 4.0 — "
    "historical 2010–2011 data, not a current-market tool."
)
BLUE = "#1b6ca8"
LIGHT = "#7fb3d5"
ORANGE = "#d35400"
GREEN = "#1e8449"
GREY = "#5d6d7e"
CLUSTER_COLOURS = ["#1b6ca8", "#d35400", "#1e8449", "#7d3c98"]

plt.rcParams.update(
    {
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
    }
)


def _record() -> dict:
    return dict(json.loads((PROCESSED_DIR / "data_source.json").read_text()))


def _is_synthetic() -> bool:
    return bool(_record().get("synthetic"))


def _save(fig, name: str, dpi: int = 120) -> Path:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    out = CHARTS_DIR / name
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return out


def _footnote(fig, text: str) -> None:
    fig.text(0.01, -0.01, text, fontsize=8, color=GREY, ha="left", va="top")


def _synthetic_banner(fig) -> None:
    if _is_synthetic():
        fig.text(
            0.5,
            0.96,
            "SYNTHETIC — NOT REAL DATA",
            fontsize=12,
            color="#922b21",
            ha="center",
            va="top",
            weight="bold",
        )


def chart_01_monthly_sales() -> Path:
    """Monthly revenue bars + orders/AOV lines (plan §7 chart 1)."""
    monthly = pd.read_csv(PROCESSED_DIR / "monthly_sales.csv")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    fig.suptitle(
        "Monthly sales — revenue peaks in November 2011", fontsize=14, weight="bold"
    )
    colours = [ORANGE if p else BLUE for p in monthly["is_partial"]]
    bars = ax1.bar(monthly["month"], monthly["revenue_gbp"] / 1000, color=colours)
    bars[-1].set_hatch("///")
    for bar, value in zip(bars, monthly["revenue_gbp"] / 1000):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 18,
            f"£{value:,.0f}k",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax1.set_ylabel("Revenue (£ thousands)")
    ax1.set_ylim(0, 1650)
    ax1.set_title("Monthly revenue (GBP) — Dec 2011 is partial (9 days), hatched")
    ax1.tick_params(axis="x", rotation=45)
    ax1.grid(axis="y", alpha=0.3)

    ax2.plot(
        monthly["month"], monthly["orders"], marker="o", color=BLUE, label="Orders"
    )
    ax2.set_ylabel("Orders", color=BLUE)
    ax2.tick_params(axis="y", labelcolor=BLUE)
    ax2b = ax2.twinx()
    ax2b.plot(
        monthly["month"],
        monthly["aov_gbp"],
        marker="s",
        color=ORANGE,
        label="Average order value",
    )
    ax2b.set_ylabel("Average order value (£)", color=ORANGE)
    ax2b.tick_params(axis="y", labelcolor=ORANGE)
    ax2.set_title("Orders and average order value by month")
    ax2.tick_params(axis="x", rotation=45)
    ax2.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    _footnote(fig, SOURCE_FOOTNOTE)
    _synthetic_banner(fig)
    return _save(fig, "01_monthly_sales.png")


def _short_label(text: str, width: int = 34) -> str:
    return textwrap.shorten(str(text), width=width, placeholder="…")


def chart_02_product_country() -> Path:
    """Top 10 SKUs by revenue + top 10 countries by revenue (plan §7 chart 2)."""
    top = pd.read_csv(PROCESSED_DIR / "top_products.csv").head(10)
    country = pd.read_csv(PROCESSED_DIR / "country_sales.csv").head(10)
    record = _record()
    uk_share = record["kpis"]["uk_revenue_share_pct"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6))
    fig.suptitle("Product mix and regional variation", fontsize=14, weight="bold")

    labels = [_short_label(d) for d in top["description"]]
    ax1.barh(labels[::-1], top["revenue_gbp"][::-1] / 1000, color=BLUE)
    for i, (value, share) in enumerate(
        zip(top["revenue_gbp"][::-1] / 1000, top["revenue_share"][::-1])
    ):
        ax1.text(
            value + 2, i, f"£{value:,.0f}k ({share:.2f}%)", va="center", fontsize=9
        )
    ax1.set_xlabel("Revenue (£ thousands)")
    ax1.set_title("Top 10 SKUs by revenue")
    ax1.set_xlim(0, 235)
    ax1.grid(axis="x", alpha=0.3)

    ax2.barh(
        country["country"][::-1],
        country["revenue_gbp"][::-1] / 1000,
        color=[
            ORANGE if c == "United Kingdom" else LIGHT for c in country["country"][::-1]
        ],
    )
    for i, (value, share) in enumerate(
        zip(country["revenue_gbp"][::-1] / 1000, country["revenue_share"][::-1])
    ):
        ax2.text(
            value + 180, i, f"£{value:,.0f}k ({share:.2f}%)", va="center", fontsize=9
        )
    ax2.set_xlabel("Revenue (£ thousands)")
    ax2.set_title("Top 10 countries by revenue")
    ax2.text(
        0.98,
        0.06,
        f"UK = {uk_share:.2f}% of revenue",
        transform=ax2.transAxes,
        ha="right",
        va="bottom",
        fontsize=10,
        weight="bold",
        color=ORANGE,
    )
    ax2.set_xlim(0, 12000)
    ax2.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    _footnote(fig, SOURCE_FOOTNOTE)
    _synthetic_banner(fig)
    return _save(fig, "02_product_country.png")


def chart_03_rfm_clusters() -> Path:
    """RFM cluster scatter + cluster profile bars (plan §7 chart 3)."""
    rfm = pd.read_csv(PROCESSED_DIR / "rfm_clusters.csv")
    summary = pd.read_csv(PROCESSED_DIR / "cluster_summary.csv")
    record = _record()
    silhouette = record["clustering"]["silhouette"]
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(13, 6), gridspec_kw={"width_ratios": [1.4, 1]}
    )
    fig.suptitle(
        f"Customer clusters (RFM + KMeans k=4, silhouette {silhouette:.3f})",
        fontsize=14,
        weight="bold",
    )
    for cluster, colour in zip(summary["cluster"], CLUSTER_COLOURS):
        sub = rfm[rfm["cluster"] == cluster]
        label = summary.loc[summary["cluster"] == cluster, "label"].iloc[0]
        ax1.scatter(
            sub["recency_days"],
            sub["monetary_gbp"],
            s=12,
            color=colour,
            alpha=0.6,
            label=f"{label} (n={len(sub):,})",
        )
    ax1.set_yscale("log")
    ax1.set_xlabel("Recency (days since last purchase)")
    ax1.set_ylabel("Monetary — total revenue per customer (£, log scale)")
    ax1.set_title("Recency vs monetary, coloured by cluster")
    ax1.legend(fontsize=9, loc="upper right")
    ax1.grid(alpha=0.3)

    order = summary.sort_values("mean_monetary", ascending=True)
    colours = [CLUSTER_COLOURS[int(c)] for c in order["cluster"]]
    ax2.barh(order["label"], order["mean_monetary"], color=colours)
    ax2.set_xscale("log")
    for i, (value, n, share) in enumerate(
        zip(order["mean_monetary"], order["n_customers"], order["share_revenue"])
    ):
        text = f"£{value:,.0f} · n={n:,} · {share:.1f}%"
        if value > 5000:
            # Inside the bar (white, right-aligned) — the full text is too
            # long to fit outside the axes on a log scale at this DPI.
            ax2.text(
                value * 0.92,
                i,
                text,
                va="center",
                ha="right",
                fontsize=9,
                color="white",
                weight="bold",
            )
        else:
            ax2.text(
                value * 1.15,
                i,
                text,
                va="center",
                fontsize=9,
            )
    ax2.set_xlabel("Mean revenue per customer (£, log scale)")
    ax2.set_title("Cluster profile — mean monetary (log scale)")
    ax2.set_xlim(100, 700000)
    ax2.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    _footnote(
        fig,
        SOURCE_FOOTNOTE + " Descriptive segmentation (RFM + KMeans), not a churn model."
        " Percentages are shares of identified-customer revenue.",
    )
    _synthetic_banner(fig)
    # dpi=100 (not 120): the 4,334-point scatter is the largest chart, and
    # the executed notebook embeds all four charts — at dpi=120 the
    # notebook exceeds the 1 MB per-file rule.
    return _save(fig, "03_rfm_clusters.png", dpi=100)


def chart_04_forecast() -> Path:
    """Weekly revenue + 8-week forecast with intervals; backtest RMSE (plan §7 chart 4)."""
    weekly = pd.read_csv(PROCESSED_DIR / "weekly_revenue.csv")
    forecast = pd.read_csv(PROCESSED_DIR / "forecast.csv")
    backtest = pd.read_csv(PROCESSED_DIR / "backtest.csv")
    record = _record()
    winner = record["forecast"]["published_method"]
    winner_label = "Holt-Winters (trend-only)" if winner == "holt_winters" else "Naïve"
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=False)
    fig.suptitle(
        f"Weekly revenue forecast — {winner_label} wins the backtest",
        fontsize=14,
        weight="bold",
    )
    weeks = pd.to_datetime(weekly["week_start"])
    ax1.plot(
        weeks, weekly["revenue_gbp"] / 1000, color=BLUE, label="Observed weekly revenue"
    )
    fweeks = pd.to_datetime(forecast["week_start"])
    ax1.plot(
        fweeks,
        forecast["forecast_gbp"] / 1000,
        color=ORANGE,
        marker="o",
        label=f"Forecast ({winner_label})",
    )
    ax1.fill_between(
        fweeks,
        forecast["lo_95"] / 1000,
        forecast["hi_95"] / 1000,
        color=ORANGE,
        alpha=0.15,
        label="95% interval",
    )
    ax1.fill_between(
        fweeks,
        forecast["lo_80"] / 1000,
        forecast["hi_80"] / 1000,
        color=ORANGE,
        alpha=0.3,
        label="80% interval",
    )
    ax1.set_ylabel("Revenue (£ thousands)")
    ax1.set_title(
        "Weekly revenue history (51 full weeks) + 8-week forecast with intervals"
    )
    ax1.legend(fontsize=9, loc="upper left")
    ax1.grid(alpha=0.3)
    ax1.tick_params(axis="x", rotation=30)

    origins = sorted(backtest["origin"].unique())
    width = 0.35
    x = np.arange(len(origins))
    hw = backtest[backtest["method"] == "holt_winters"].sort_values("origin")
    nv = backtest[backtest["method"] == "naive"].sort_values("origin")
    ax2.bar(x - width / 2, hw["rmse"] / 1000, width, color=BLUE, label="Holt-Winters")
    ax2.bar(x + width / 2, nv["rmse"] / 1000, width, color=GREY, label="Naïve")
    for xi, value in zip(x - width / 2, hw["rmse"] / 1000):
        ax2.text(xi, value + 1, f"£{value:,.0f}k", ha="center", fontsize=9)
    for xi, value in zip(x + width / 2, nv["rmse"] / 1000):
        ax2.text(xi, value + 1, f"£{value:,.0f}k", ha="center", fontsize=9)
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"train ends {o} weeks before end" for o in origins])
    ax2.set_ylabel("Backtest RMSE (£ thousands)")
    ax2.set_title("Backtest RMSE by origin — lower is better (8-week horizons)")
    ax2.legend(fontsize=9)
    ax2.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    _footnote(
        fig,
        SOURCE_FOOTNOTE
        + " Trend-only forecast: one year of data cannot support a seasonal fit.",
    )
    _synthetic_banner(fig)
    return _save(fig, "04_forecast.png")


def main() -> int:
    for fn in (
        chart_01_monthly_sales,
        chart_02_product_country,
        chart_03_rfm_clusters,
        chart_04_forecast,
    ):
        fn()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
