"""Generate the four static README charts from data/processed/*.csv.

Run: python3 -m src.make_charts  (from the project root, after the pipeline)
Every chart carries a "Powered by CoinGecko" footnote and, when the data is
synthetic, a SYNTHETIC DATA label. Educational analysis only.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHARTS_DIR = PROJECT_ROOT / "outputs" / "charts"

PALETTE = {"bitcoin": "#F7931A", "ethereum": "#627EEA", "solana": "#9945FF"}
LABELS = {
    "bitcoin": "Bitcoin (BTC)",
    "ethereum": "Ethereum (ETH)",
    "solana": "Solana (SOL)",
}
plt.rcParams.update(
    {"font.size": 11, "axes.titlesize": 13, "axes.labelsize": 11, "legend.fontsize": 10}
)


def _synthetic() -> bool:
    p = PROCESSED_DIR / "data_source.json"
    return bool(p.exists() and json.loads(p.read_text()).get("synthetic"))


def _finish(fig, ax, title, ylabel, source_note=True):
    ax.set_title(title, fontweight="bold", loc="left")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend(frameon=False)
    if _synthetic():
        fig.text(
            0.99,
            0.01,
            "SYNTHETIC DATA — API unavailable",
            ha="right",
            color="red",
            fontweight="bold",
            fontsize=10,
        )
    if source_note:
        fig.text(
            0.01,
            0.01,
            "Powered by CoinGecko (coingecko.com) | "
            "Educational analysis only — not investment advice",
            ha="left",
            fontsize=10,
            color="#555555",
        )
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    return fig


def main() -> None:
    daily = pd.read_csv(PROCESSED_DIR / "crypto_daily.csv", parse_dates=["date"])
    metrics = pd.read_csv(PROCESSED_DIR / "crypto_metrics.csv", parse_dates=["date"])
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    window = f"{daily['date'].min():%Y-%m-%d} to {daily['date'].max():%Y-%m-%d}"

    # 1 — Price indexed to 100
    d = daily.copy()
    d["indexed"] = d.groupby("coin")["price"].transform(lambda s: s / s.iloc[0] * 100)
    fig, ax = plt.subplots(figsize=(10, 5))
    for coin, g in d.groupby("coin"):
        ax.plot(g["date"], g["indexed"], label=LABELS[coin], color=PALETTE[coin], lw=2)
    ax.set_xlabel(f"Date ({window})")
    _finish(
        fig,
        ax,
        "Price indexed to 100 — momentum comparison",
        "Price index (first day = 100)",
    )
    fig.savefig(CHARTS_DIR / "01_price_indexed.png", dpi=150)
    plt.close(fig)

    # 2 — Rolling volatility
    fig, ax = plt.subplots(figsize=(10, 5))
    for coin, g in metrics.groupby("coin"):
        ax.plot(
            g["date"],
            g["vol_30d_annualised"] * 100,
            label=LABELS[coin],
            color=PALETTE[coin],
            lw=2,
        )
    ax.set_xlabel(f"Date ({window})")
    _finish(fig, ax, "30-day rolling volatility (annualised, ×√365)", "Volatility (%)")
    fig.savefig(CHARTS_DIR / "02_rolling_volatility.png", dpi=150)
    plt.close(fig)

    # 3 — Drawdown
    fig, ax = plt.subplots(figsize=(10, 5))
    for coin, g in metrics.groupby("coin"):
        ax.fill_between(
            g["date"], g["drawdown"] * 100, 0, color=PALETTE[coin], alpha=0.15
        )
        ax.plot(
            g["date"],
            g["drawdown"] * 100,
            label=LABELS[coin],
            color=PALETTE[coin],
            lw=2,
        )
    ax.set_xlabel(f"Date ({window})")
    _finish(fig, ax, "Drawdown from peak — how far each coin fell", "Drawdown (%)")
    fig.savefig(CHARTS_DIR / "03_drawdown.png", dpi=150)
    plt.close(fig)

    # 4 — Relative volume
    fig, ax = plt.subplots(figsize=(10, 5))
    for coin, g in metrics.groupby("coin"):
        ax.plot(
            g["date"],
            g["relative_volume"],
            label=LABELS[coin],
            color=PALETTE[coin],
            lw=1.5,
        )
    ax.axhline(1.0, color="grey", ls="--", lw=1, label="30-day average (= 1.0)")
    ax.set_xlabel(f"Date ({window})")
    _finish(
        fig,
        ax,
        "Relative volume — trading volume vs its 30-day mean",
        "Relative volume (× 30-day mean)",
    )
    fig.savefig(CHARTS_DIR / "04_relative_volume.png", dpi=150)
    plt.close(fig)

    print(f"Charts written to {CHARTS_DIR} (synthetic={_synthetic()})")


if __name__ == "__main__":
    main()
