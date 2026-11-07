"""Generate the four static README charts from data/processed/*.csv.

Run: python3 -m src.make_charts  (from the project root, after the pipeline)
Exactly 4 PNGs, offline from the committed processed CSVs only (no network,
no API). Every chart carries a "Powered by CoinGecko" footnote and, when
the data is synthetic, a SYNTHETIC DATA label.
Educational analysis only — not investment advice. Flagged days are
statistical outliers in price and volume — never presented as proven
manipulation.
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
    from src.anomaly import evaluate, run_detection
except ImportError:  # run as a script: python src/make_charts.py
    from anomaly import evaluate, run_detection  # type: ignore[no-redef]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHARTS_DIR = PROJECT_ROOT / "outputs" / "charts"

PALETTE = {"bitcoin": "#F7931A", "ethereum": "#627EEA", "solana": "#9945FF"}
LABELS = {
    "bitcoin": "Bitcoin (BTC)",
    "ethereum": "Ethereum (ETH)",
    "solana": "Solana (SOL)",
}
SEVERITY_COLORS = {"High": "#C0392B", "Medium": "#E67E22", "Low": "#2E86AB"}
FLAG_MARKERS = {"baseline": "o", "forest": "s", "both": "D"}
plt.rcParams.update(
    {"font.size": 11, "axes.titlesize": 13, "axes.labelsize": 11, "legend.fontsize": 10}
)


def _synthetic() -> bool:
    p = PROCESSED_DIR / "data_source.json"
    return bool(p.exists() and json.loads(p.read_text()).get("synthetic"))


def _synthetic_label(fig):
    if _synthetic():
        fig.text(
            0.99,
            0.01,
            "SYNTHETIC DATA — API unavailable on 2026-11-07",
            ha="right",
            color="red",
            fontweight="bold",
            fontsize=10,
        )


def _source_note(fig, y=0.01):
    fig.text(
        0.01,
        y,
        "Powered by CoinGecko (coingecko.com) | "
        "Educational analysis only — not investment advice",
        ha="left",
        fontsize=10,
        color="#555555",
    )


def main() -> None:
    daily = pd.read_csv(PROCESSED_DIR / "crypto_daily.csv", parse_dates=["date"])
    timeline = pd.read_csv(PROCESSED_DIR / "anomaly_timeline.csv", parse_dates=["date"])
    injected = pd.read_csv(
        PROCESSED_DIR / "crypto_daily_injected.csv", parse_dates=["date"]
    )
    labels = pd.read_csv(PROCESSED_DIR / "injected_anomalies.csv")
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    window = f"{daily['date'].min():%Y-%m-%d} to {daily['date'].max():%Y-%m-%d}"
    synth = _synthetic()

    # Evaluation is recomputed from the committed injected CSVs so the
    # charts regenerate offline (same deterministic pipeline as the
    # coder's run: random_state=42, contamination from the baseline rate).
    injected_detected, _cont = run_detection(injected)
    # Amended precision rule (§4.4, 2026-11-07): the committed timeline
    # is the clean-data flag set — a flag matching it is a true positive.
    evaluation = evaluate(
        injected_detected,
        labels,
        tolerance_days=1,
        clean_flags=timeline[["date", "coin"]],
    )
    real_detected, _real_cont = run_detection(daily)
    real_base = set(
        map(
            tuple,
            real_detected.loc[
                real_detected["baseline_flagged"], ["date", "coin"]
            ].values,
        )
    )
    real_forest = set(
        map(
            tuple,
            real_detected.loc[real_detected["is_anomaly"], ["date", "coin"]].values,
        )
    )
    jaccard_real = (
        len(real_base & real_forest) / len(real_base | real_forest)
        if (real_base | real_forest)
        else 0.0
    )

    # 1 — Anomaly timeline: price per coin, flagged days marked.
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    for ax, coin in zip(axes, ["bitcoin", "ethereum", "solana"]):
        g = daily[daily["coin"] == coin].sort_values("date")
        ax.plot(g["date"], g["price"], label=LABELS[coin], color=PALETTE[coin], lw=1.5)
        tg = timeline[timeline["coin"] == coin]
        for _sev, sg in tg.groupby("severity"):
            ax.scatter(
                sg["date"],
                sg["price"],
                s=70,
                marker="o",
                color=SEVERITY_COLORS[_sev],
                edgecolor="black",
                linewidths=0.5,
                label=f"{_sev} ({len(sg)})",
                zorder=5,
            )
        # Annotate the highest-severity flag per coin (largest |return_z|).
        top = tg.loc[tg["return_z"].abs().idxmax()]
        ax.annotate(
            f"Highest: {top['date'].strftime('%Y-%m-%d')} "
            f"{top['daily_return']:+.1%}, vol {top['volume_ratio']:.1f}x",
            xy=(top["date"], top["price"]),
            xytext=(-8, 12),
            textcoords="offset points",
            ha="right",
            fontsize=9,
            color="#333333",
            arrowprops={"arrowstyle": "->", "color": "#333333"},
        )
        ax.set_title(
            f"{LABELS[coin]} — price with flagged days", fontweight="bold", loc="left"
        )
        ax.set_ylabel("Price (USD)")
        ax.grid(True, alpha=0.3)
        ax.legend(frameon=False, fontsize=9, loc="upper left")
    axes[-1].set_xlabel(f"Date ({window})")
    fig.suptitle(
        "Anomaly timeline — flagged days are statistical outliers, "
        "not evidence of manipulation",
        fontweight="bold",
        fontsize=13,
    )
    _synthetic_label(fig)
    _source_note(fig)
    fig.tight_layout(rect=[0, 0.04, 1, 0.97])
    fig.savefig(CHARTS_DIR / "01_anomaly_timeline.png", dpi=150)
    plt.close(fig)

    # 2 — Return vs log volume ratio scatter, flagged by severity.
    fig, ax = plt.subplots(figsize=(10, 6))
    daily["ret_pct"] = daily["daily_return"] * 100
    flagged_keys = {
        (str(d.date()), c) for d, c in zip(timeline["date"], timeline["coin"])
    }
    daily["is_flagged"] = [
        (str(d.date()), c) in flagged_keys for d, c in zip(daily["date"], daily["coin"])
    ]
    sev_map = {
        (str(d.date()), c): s
        for d, c, s in zip(timeline["date"], timeline["coin"], timeline["severity"])
    }
    daily["severity"] = [
        sev_map.get((str(d.date()), c), "")
        for d, c in zip(daily["date"], daily["coin"])
    ]
    unflagged = daily[~daily["is_flagged"]]
    ax.scatter(
        unflagged["ret_pct"],
        unflagged["log_volume_ratio"],
        s=8,
        color="#BBBBBB",
        alpha=0.6,
        label=f"Unflagged ({len(unflagged)})",
    )
    for sev in ("Low", "Medium", "High"):
        sg = daily[daily["severity"] == sev]
        ax.scatter(
            sg["ret_pct"],
            sg["log_volume_ratio"],
            s=45,
            color=SEVERITY_COLORS[sev],
            edgecolor="black",
            linewidths=0.5,
            label=f"{sev} ({len(sg)})",
        )
    # Threshold guides: R1/R2 boundaries at the median trailing sigma
    # (exact z thresholds vary day to day — see caption).
    med_ret_std = (daily["daily_return"] / daily["return_z"]).abs().median()
    # Median trailing std of log volume ratio, from volume_z directly.
    lvr = daily["log_volume_ratio"]
    vol_std = (lvr / daily["volume_z"]).abs()
    med_vol_std = vol_std.replace([np.inf, -np.inf], np.nan).median()
    med_lvr = lvr.median()
    ax.axvline(
        3 * med_ret_std * 100,
        color="#C0392B",
        ls="--",
        lw=1.2,
        label="R1 guide: ±3σ return (median σ)",
    )
    ax.axvline(-3 * med_ret_std * 100, color="#C0392B", ls="--", lw=1.2)
    ax.axhline(
        med_lvr + 3 * med_vol_std,
        color="#E67E22",
        ls="--",
        lw=1.2,
        label="R2 guide: volume z = +3 (median σ)",
    )
    ax.axhline(
        np.log(2),
        color="#2E86AB",
        ls=":",
        lw=1.2,
        label="R2 floor: volume ratio = 2x (log 2)",
    )
    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("Daily return (%)")
    ax.set_ylabel("Log volume ratio (log of volume / 30-day mean volume)")
    ax.set_title(
        "Return vs volume — why a day was flagged",
        fontweight="bold",
        loc="left",
    )
    ax.grid(True, alpha=0.3)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.text(
        0.01,
        0.055,
        "Dashed guides use the median trailing 30-day σ; exact R1/R2/R3 "
        "thresholds are per-day z-scores (see README).",
        ha="left",
        fontsize=9,
        color="#333333",
    )
    _synthetic_label(fig)
    _source_note(fig)
    fig.tight_layout(rect=[0, 0.09, 1, 1])
    fig.savefig(CHARTS_DIR / "02_return_volume_scatter.png", dpi=150)
    plt.close(fig)

    # 3 — Per-coin flag counts / severity / method split.
    coins = ["bitcoin", "ethereum", "solana"]
    x = np.arange(len(coins))
    width = 0.25
    r1 = [
        int(timeline[timeline["coin"] == c]["rules_triggered"].str.contains("R1").sum())
        for c in coins
    ]
    r2 = [
        int(timeline[timeline["coin"] == c]["rules_triggered"].str.contains("R2").sum())
        for c in coins
    ]
    r3 = [
        int(timeline[timeline["coin"] == c]["rules_triggered"].str.contains("R3").sum())
        for c in coins
    ]
    high = [
        int(((timeline["coin"] == c) & (timeline["severity"] == "High")).sum())
        for c in coins
    ]
    med = [
        int(((timeline["coin"] == c) & (timeline["severity"] == "Medium")).sum())
        for c in coins
    ]
    low = [
        int(((timeline["coin"] == c) & (timeline["severity"] == "Low")).sum())
        for c in coins
    ]
    both = [
        int(((timeline["coin"] == c) & (timeline["flagged_by"] == "both")).sum())
        for c in coins
    ]
    base_only = [
        int(((timeline["coin"] == c) & (timeline["flagged_by"] == "baseline")).sum())
        for c in coins
    ]
    forest_only = [
        int(((timeline["coin"] == c) & (timeline["flagged_by"] == "forest")).sum())
        for c in coins
    ]
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(12, 4.5), sharey=True)
    for ax, vals, title, note in [
        (ax1, (r1, r2, r3), "Flags by rule", "a day can trigger several rules"),
        (
            ax2,
            (high, med, low),
            "Flags by severity",
            "High / Medium / Low (Section 4.2)",
        ),
        (
            ax3,
            (both, base_only, forest_only),
            "Baseline vs forest",
            "both / baseline-only / forest-only",
        ),
    ]:
        labels3 = [
            ["R1", "R2", "R3"],
            ["High", "Medium", "Low"],
            ["Both", "Baseline-only", "Forest-only"],
        ]
        idx_panel = [ax1, ax2, ax3].index(ax)
        names = labels3[idx_panel]
        colors = (
            ["#2E86AB", "#F6AE2D", "#6A994E"]
            if idx_panel != 1
            else ["#C0392B", "#E67E22", "#2E86AB"]
        )
        for i, (v, name) in enumerate(zip(vals, names)):
            bars = ax.bar(x + (i - 1) * width, v, width, label=name, color=colors[i])
            ax.bar_label(bars, padding=2, fontsize=9)
        ax.set_xticks(x)
        ax.set_xticklabels([LABELS[c] for c in coins], fontsize=9)
        ax.set_title(f"{title}\n({note})", fontweight="bold", loc="left", fontsize=11)
        ax.grid(True, alpha=0.3, axis="y")
        ax.legend(frameon=False, fontsize=9)
    ax1.set_ylabel("Flagged days")
    fig.suptitle(
        "Flag counts per coin — which coin, which pattern",
        fontweight="bold",
        fontsize=13,
    )
    _synthetic_label(fig)
    _source_note(fig)
    fig.tight_layout(rect=[0, 0.06, 1, 0.94])
    fig.savefig(CHARTS_DIR / "03_flag_counts_severity.png", dpi=150)
    plt.close(fig)

    # 4 — Evaluation: precision/recall/F1 per method + per-type recall.
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))
    methods = ["baseline", "forest", "union"]
    metrics = ["precision", "recall", "f1"]
    x = np.arange(len(methods))
    width = 0.22
    colors_m = {"precision": "#2E86AB", "recall": "#F6AE2D", "f1": "#6A994E"}
    for i, m in enumerate(metrics):
        vals = [evaluation[mth][m] for mth in methods]
        bars = ax1.bar(
            x + (i - 1) * width, vals, width, label=m.capitalize(), color=colors_m[m]
        )
        ax1.bar_label(bars, fmt="%.2f", padding=2, fontsize=9)
    ax1.axhline(0.80, color="#C0392B", ls="--", lw=1.2, label="Recall target 0.80")
    ax1.axhline(0.50, color="#2E86AB", ls=":", lw=1.2, label="Precision target 0.50")
    ax1.set_xticks(x)
    ax1.set_xticklabels([m.capitalize() for m in methods])
    ax1.set_ylim(0, 1.05)
    ax1.set_ylabel("Score (0–1)")
    ax1.set_title(
        "Injected anomalies: precision / recall / F1",
        fontweight="bold",
        loc="left",
        fontsize=11,
    )
    ax1.grid(True, alpha=0.3, axis="y")
    ax1.legend(frameon=False, fontsize=8)
    # Jaccard caption as the x-label, below the axis, so it can never sit
    # behind the legend (was an in-axes text at the bottom-left, overlapping
    # the legend box).
    ax1.set_xlabel(
        f"Baseline–forest Jaccard (real data): {jaccard_real:.2f} (target ≥ 0.30)",
        fontsize=9,
        color="#333333",
    )
    types = ["price_spike", "volume_surge", "joint_shock"]
    type_labels = ["Price spike", "Volume surge", "Joint shock"]
    per_type = [evaluation["per_type_recall"].get(t, 0.0) for t in types]
    bars = ax2.bar(type_labels, per_type, color="#2E86AB", width=0.55)
    ax2.bar_label(bars, fmt="%.2f", padding=2, fontsize=10)
    ax2.axhline(0.60, color="#C0392B", ls="--", lw=1.2, label="Per-type target 0.60")
    ax2.set_ylim(0, 1.05)
    ax2.set_ylabel("Recall (union method, 0–1)")
    ax2.set_title("Per-type recall (union)", fontweight="bold", loc="left", fontsize=11)
    ax2.grid(True, alpha=0.3, axis="y")
    ax2.legend(frameon=False, fontsize=9)
    fig.suptitle(
        "Evaluation — injected anomalies (±1-day tolerance, n=30)",
        fontweight="bold",
        fontsize=13,
    )
    _synthetic_label(fig)
    _source_note(fig)
    fig.tight_layout(rect=[0, 0.05, 1, 0.94])
    fig.savefig(CHARTS_DIR / "04_evaluation.png", dpi=150)
    plt.close(fig)

    print(f"Wrote 4 charts to {CHARTS_DIR} (synthetic={synth})")
    print(
        f"Evaluation (injected): union recall "
        f"{evaluation['union']['recall']:.3f}, precision "
        f"{evaluation['union']['precision']:.3f}, F1 "
        f"{evaluation['union']['f1']:.3f}; "
        f"Jaccard (real) {jaccard_real:.3f}"
    )


if __name__ == "__main__":
    main()
