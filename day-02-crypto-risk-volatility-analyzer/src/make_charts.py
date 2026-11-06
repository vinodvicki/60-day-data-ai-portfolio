"""Generate the four static README charts from data/processed/*.csv.

Run: python3 -m src.make_charts  (from the project root, after the pipeline)
Exactly 4 PNGs, offline from the committed processed CSVs only (no network,
no API). Every chart carries a "Powered by CoinGecko" footnote and, when
the data is synthetic, a SYNTHETIC DATA label.
Educational analysis only — not investment advice.
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
            "SYNTHETIC DATA — API unavailable on 2026-11-06",
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
    summary = pd.read_csv(PROCESSED_DIR / "crypto_risk_summary.csv")
    correlations = pd.read_csv(PROCESSED_DIR / "crypto_correlations.csv")
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    window = f"{daily['date'].min():%Y-%m-%d} to {daily['date'].max():%Y-%m-%d}"
    synth = _synthetic()

    # 1 — Drawdown over time, with each coin's max drawdown annotated.
    fig, ax = plt.subplots(figsize=(10, 5))
    for coin, g in daily.groupby("coin"):
        g = g.sort_values("date")
        ax.plot(
            g["date"],
            g["drawdown"] * 100,
            label=LABELS[coin],
            color=PALETTE[coin],
            lw=2,
        )
        row = summary[summary["coin"] == coin].iloc[0]
        trough = pd.Timestamp(row["trough_date"])
        ax.annotate(
            f"{LABELS[coin]}: {row['max_drawdown'] * 100:.1f}% "
            f"({row['trough_date']})",
            xy=(trough, row["max_drawdown"] * 100),
            xytext=(8, -18),
            textcoords="offset points",
            fontsize=9,
            color=PALETTE[coin],
            arrowprops={"arrowstyle": "->", "color": PALETTE[coin]},
        )
    ax.axhline(0, color="black", lw=1)
    ax.set_ylim(-70, 2)  # headroom so the Solana trough annotation is not clipped
    ax.set_xlabel(f"Date ({window})")
    _finish(fig, ax, "Drawdown from peak (%)", "Drawdown (%)")
    fig.savefig(CHARTS_DIR / "01_drawdown.png", dpi=150)
    plt.close(fig)

    # 2 — Rolling 30-day annualised volatility, with each max annotated.
    fig, ax = plt.subplots(figsize=(10, 5))
    for coin, g in daily.groupby("coin"):
        g = g.sort_values("date")
        ax.plot(
            g["date"],
            g["vol_30d_ann"] * 100,
            label=LABELS[coin],
            color=PALETTE[coin],
            lw=2,
        )
        row = summary[summary["coin"] == coin].iloc[0]
        vmax_date = pd.Timestamp(row["vol_30d_max_date"])
        ax.annotate(
            f"{LABELS[coin]}: {row['vol_30d_max'] * 100:.0f}% "
            f"({row['vol_30d_max_date']})",
            xy=(vmax_date, row["vol_30d_max"] * 100),
            xytext=(8, 6),
            textcoords="offset points",
            fontsize=9,
            color=PALETTE[coin],
            arrowprops={"arrowstyle": "->", "color": PALETTE[coin]},
        )
    ax.set_ylim(15, 118)  # headroom so the SOL/ETH max annotations are not clipped
    ax.set_xlabel(f"Date ({window})")
    _finish(
        fig,
        ax,
        "30-day rolling volatility, annualised (×√365)",
        "Volatility (% per year)",
    )
    fig.savefig(CHARTS_DIR / "02_rolling_volatility.png", dpi=150)
    plt.close(fig)

    # 3 — Correlation heatmap (full window), latest-90d values as text.
    piv = daily.pivot(index="date", columns="coin", values="daily_return")
    corr = piv.corr()
    order = ["bitcoin", "ethereum", "solana"]
    corr = corr.loc[order, order]
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(corr.to_numpy(), cmap="RdYlGn", vmin=-1, vmax=1)
    ax.set_xticks(range(3))
    ax.set_yticks(range(3))
    ax.set_xticklabels([LABELS[c] for c in order])
    ax.set_yticklabels([LABELS[c] for c in order])
    for i in range(3):
        for j in range(3):
            value = corr.iloc[i, j]
            ax.text(
                j,
                i,
                f"{value:.2f}",
                ha="center",
                va="center",
                fontsize=13,
                fontweight="bold",
                color="black" if abs(value) < 0.85 else "white",
            )
    fig.colorbar(im, ax=ax, label="Pearson correlation of daily returns")
    caption = "Latest 90 days: " + "; ".join(
        f"{r['pair'].replace('-', '–')}: {r['latest_90d']:.2f}"
        for _, r in correlations.iterrows()
    )
    fig.text(0.01, 0.01, caption, ha="left", fontsize=10, color="#333333")
    ax.set_title(
        "Correlation of daily returns — full window", fontweight="bold", loc="left"
    )
    if synth:
        fig.text(
            0.99,
            0.01,
            "SYNTHETIC DATA — API unavailable on 2026-11-06",
            ha="right",
            color="red",
            fontweight="bold",
            fontsize=10,
        )
    fig.text(
        0.01,
        0.055,
        "Powered by CoinGecko (coingecko.com) | "
        "Educational analysis only — not investment advice",
        ha="left",
        fontsize=10,
        color="#555555",
    )
    fig.tight_layout(rect=[0, 0.09, 1, 1])
    fig.savefig(CHARTS_DIR / "03_correlation_heatmap.png", dpi=150)
    plt.close(fig)

    # 4 — Risk-adjusted returns + VaR/CVaR, two clearly labelled panels.
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=False)
    coins = ["bitcoin", "ethereum", "solana"]
    x = np.arange(len(coins))
    width = 0.25
    total = summary.set_index("coin").loc[coins, "total_return"].to_numpy() * 100
    sharpe = summary.set_index("coin").loc[coins, "sharpe"].to_numpy()
    sortino = summary.set_index("coin").loc[coins, "sortino"].to_numpy()
    # Sharpe / Sortino are ratios (≈ −0.4 to −0.9), not percents — plotting
    # them on the total-return axis made them invisible slivers (D1). They
    # get their own twin axis on the right, plus a value label on every bar.
    ax1b = ax1.twinx()
    c_sharpe = ax1b.bar(x, sharpe, width, label="Sharpe (annualised)", color="#F6AE2D")
    c_sortino = ax1b.bar(
        x + width, sortino, width, label="Sortino (annualised)", color="#6A994E"
    )
    c_total = ax1.bar(
        x - width, total, width, label="Total return (%)", color="#2E86AB"
    )
    ax1.bar_label(c_total, fmt="%.1f%%", padding=3, fontsize=9)
    ax1b.bar_label(c_sharpe, fmt="%.2f", padding=3, fontsize=9)
    ax1b.bar_label(c_sortino, fmt="%.2f", padding=3, fontsize=9)
    ax1.set_ylim(-55, 5)  # headroom for the total-return value labels
    ax1b.set_ylim(-1.1, 0.1)  # headroom for the ratio value labels
    ax1.axhline(0, color="black", lw=1)
    ax1.set_xticks(x)
    ax1.set_xticklabels([LABELS[c] for c in coins])
    ax1.set_title(
        "Risk-adjusted returns — total return (%) with Sharpe / Sortino "
        "ratios (0% risk-free)",
        fontweight="bold",
        loc="left",
    )
    ax1.set_ylabel("Total return (%)")
    ax1b.set_ylabel("Sharpe / Sortino (ratio)")
    ax1.grid(True, alpha=0.3, axis="y")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax1b.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, frameon=False, fontsize=9)
    var = summary.set_index("coin").loc[coins, "var_95"].to_numpy() * 100
    cvar = summary.set_index("coin").loc[coins, "cvar_95"].to_numpy() * 100
    ax2.bar(x - width / 2, var, width, label="VaR 95% (daily loss %)", color="#E4572E")
    ax2.bar(
        x + width / 2,
        cvar,
        width,
        label="CVaR 95% (avg worst-5% loss %)",
        color="#7B2CBF",
    )
    ax2.axhline(0, color="black", lw=1)
    ax2.set_xticks(x)
    ax2.set_xticklabels([LABELS[c] for c in coins])
    ax2.set_title(
        "Tail risk — one-day historical VaR 95% and CVaR 95% (daily loss %)",
        fontweight="bold",
        loc="left",
    )
    ax2.set_ylabel("Daily loss (%)")
    ax2.grid(True, alpha=0.3, axis="y")
    ax2.legend(frameon=False, fontsize=9)
    if synth:
        fig.text(
            0.99,
            0.01,
            "SYNTHETIC DATA — API unavailable on 2026-11-06",
            ha="right",
            color="red",
            fontweight="bold",
            fontsize=10,
        )
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
    fig.savefig(CHARTS_DIR / "04_risk_adjusted_returns_var.png", dpi=150)
    plt.close(fig)

    print(f"Wrote 4 charts to {CHARTS_DIR} (synthetic={synth})")


if __name__ == "__main__":
    main()
