"""Day 19 Credit Card Fraud Detection: chart builder.

Draws the 4 charts from the committed processed CSVs only — never from
the raw file, so the charts reproduce in CI without the 144 MB cache.
All charts are 1280 px wide, drawn to scale, with legible labels.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
CHARTS_DIR = ROOT / "outputs" / "charts"

MODEL_LABELS = {
    "baseline_majority": "Majority baseline",
    "logistic_regression": "Logistic regression",
    "random_forest": "Random forest",
}
MODEL_COLOURS = {
    "baseline_majority": "#9e9e9e",
    "logistic_regression": "#1f77b4",
    "random_forest": "#d62728",
}


def _save(fig: plt.Figure, name: str) -> Path:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    path = CHARTS_DIR / name
    fig.savefig(path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {path} ({path.stat().st_size} bytes)")
    return path


def chart_01_class_imbalance() -> Path:
    """Class counts (log scale) + Amount distribution by class.

    The histogram comes from the committed amount_hist.csv (binned
    log10 Amount counts per class), never from the raw file.
    """
    summary = pd.read_csv(PROCESSED_DIR / "class_summary.csv")
    amounts = pd.read_csv(PROCESSED_DIR / "amount_summary.csv")
    hist = pd.read_csv(PROCESSED_DIR / "amount_hist.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.2))
    fig.suptitle(
        "The imbalance: 492 frauds in 284,807 transactions (0.17%)", fontsize=13
    )
    counts = summary.set_index("Class")["n_transactions"]
    axes[0].bar(
        ["Legitimate", "Fraud"],
        [counts.loc[0], counts.loc[1]],
        color=["#1f77b4", "#d62728"],
    )
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Transactions (log scale)")
    axes[0].set_title("Transactions by class")
    for i, value in enumerate([counts.loc[0], counts.loc[1]]):
        if i == 0:
            # Label inside the tall bar (white) — a label above it would
            # collide with the subplot title on the log scale.
            axes[0].text(
                i,
                value * 0.6,
                f"{int(value):,}",
                ha="center",
                fontsize=11,
                color="white",
                fontweight="bold",
            )
        else:
            # The fraud bar is too short for an inside label; put it above.
            axes[0].text(
                i,
                value * 1.6,
                f"{int(value):,}",
                ha="center",
                fontsize=11,
                color="black",
                fontweight="bold",
            )
    for cls, colour, label in (
        (0, "#1f77b4", "Legitimate"),
        (1, "#d62728", "Fraud"),
    ):
        sub = hist[hist["Class"] == cls]
        widths = sub["bin_right"] - sub["bin_left"]
        densities = sub["count"] / (sub["count"].sum() * widths)
        axes[1].bar(
            sub["bin_center"],
            densities,
            width=widths,
            alpha=0.55,
            color=colour,
            label=label,
        )
    axes[1].set_xlabel("log10(Amount, USD)")
    axes[1].set_ylabel("Density (area = 1 per class)")
    axes[1].set_title("Amount distribution by class (log scale)")
    axes[1].legend()
    medians = amounts.set_index("Class")["median_usd"]
    axes[1].text(
        0.02,
        0.96,
        "Median amount: legit USD "
        f"{medians.loc[0]:.2f} vs fraud USD {medians.loc[1]:.2f}",
        transform=axes[1].transAxes,
        va="top",
        fontsize=10,
    )
    fig.tight_layout()
    return _save(fig, "01_class_imbalance.png")


def chart_02_pr_curves() -> Path:
    """Precision–recall curves per model (test set, from stored scores).

    Scores are recomputed here from the raw file + the fitted models is
    NOT possible without the models, so the pipeline stores the exact PR
    curve points (sklearn precision_recall_curve) in pr_curves.csv and
    this chart reads them.
    """
    metrics = pd.read_csv(PROCESSED_DIR / "model_metrics.csv")
    curves = pd.read_csv(PROCESSED_DIR / "pr_curves.csv")
    fig, ax = plt.subplots(figsize=(12.8, 6.4))
    # No-skill reference: a model that flags at random scores precision
    # equal to the fraud prevalence (0.17%) at every recall.
    ax.plot(
        [0, 1],
        [0.0017, 0.0017],
        color="#9e9e9e",
        linestyle="--",
        label="No-skill (prevalence 0.17%)",
    )
    for _, row in metrics.iterrows():
        model = str(row["model"])
        if model == "baseline_majority":
            continue  # the majority model outputs no scores; see the table
        sub = curves[curves["model"] == model].sort_values("recall")
        ax.plot(
            sub["recall"],
            sub["precision"],
            color=MODEL_COLOURS[model],
            label=f"{MODEL_LABELS[model]} (PR-AUC {row['pr_auc']:.3f})",
        )
    ax.set_xlim(0, 1.0)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Recall (share of fraud caught)")
    ax.set_ylabel("Precision (share of flags that are fraud)")
    ax.set_title(
        "Precision–recall curves, test set — PR-AUC is the headline metric "
        "(fraud rate 0.17%)"
    )
    ax.legend(loc="lower left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return _save(fig, "02_pr_curves.png")


def chart_03_threshold_tradeoff() -> Path:
    """Precision / recall / F1 vs. decision threshold for the best model."""
    source = json.loads((PROCESSED_DIR / "data_source.json").read_text())
    best = str(source["best_model"])
    sweep = pd.read_csv(PROCESSED_DIR / "threshold_sweep.csv")
    sub = sweep[sweep["model"] == best].sort_values("threshold")
    fig, ax = plt.subplots(figsize=(12.8, 6.4))
    ax.plot(
        sub["threshold"], sub["precision"], marker="o", markersize=3, label="Precision"
    )
    ax.plot(sub["threshold"], sub["recall"], marker="s", markersize=3, label="Recall")
    ax.plot(sub["threshold"], sub["f1"], marker="^", markersize=3, label="F1")
    best_row = sub.loc[sub["f1"].idxmax()]
    ax.axvline(float(best_row["threshold"]), color="grey", linestyle="--", alpha=0.6)
    ax.annotate(
        f"Best F1 {best_row['f1']:.3f} at threshold {best_row['threshold']:.2f}\n"
        f"(precision {best_row['precision']:.2f}, recall {best_row['recall']:.2f})",
        xy=(float(best_row["threshold"]), float(best_row["f1"])),
        xytext=(0.55, 0.75),
        textcoords="axes fraction",
        arrowprops={"arrowstyle": "->", "color": "grey"},
        fontsize=10,
    )
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Decision threshold")
    ax.set_ylabel("Score")
    ax.set_title(f"Threshold tradeoff — {MODEL_LABELS[best]} (test set)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return _save(fig, "03_threshold_tradeoff.png")


def chart_04_cost_curve() -> Path:
    """Expected cost per 10,000 transactions vs. threshold, with split."""
    source = json.loads((PROCESSED_DIR / "data_source.json").read_text())
    best = str(source["best_model"])
    cost = pd.read_csv(PROCESSED_DIR / "cost_curve.csv").sort_values("threshold")
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.6))
    fig.suptitle(
        f"Operational cost vs. threshold — {MODEL_LABELS[best]} "
        "(missed fraud = Amount lost; false alarm = $5 review)",
        fontsize=12,
    )
    axes[0].plot(
        cost["threshold"],
        cost["cost_per_10k_txns_usd"],
        marker="o",
        markersize=3,
        color="#d62728",
    )
    min_row = cost.loc[cost["cost_per_10k_txns_usd"].idxmin()]
    axes[0].axvline(
        float(min_row["threshold"]), color="grey", linestyle="--", alpha=0.6
    )
    axes[0].annotate(
        f"Minimum ${min_row['cost_per_10k_txns_usd']:,.0f} per 10k txns\n"
        f"at threshold {min_row['threshold']:.2f}",
        xy=(float(min_row["threshold"]), float(min_row["cost_per_10k_txns_usd"])),
        xytext=(0.22, 0.55),
        textcoords="axes fraction",
        arrowprops={"arrowstyle": "->", "color": "grey"},
        fontsize=10,
    )
    axes[0].set_xlabel("Decision threshold")
    axes[0].set_ylabel("Expected cost per 10,000 txns (USD)")
    axes[0].set_title("Total cost")
    axes[0].grid(alpha=0.3)
    test_n = float(
        cost["tp"].iloc[0]
        + cost["fp"].iloc[0]
        + cost["tn"].iloc[0]
        + cost["fn"].iloc[0]
    )
    per_10k = 10_000.0 / test_n
    missed = cost["missed_fraud_usd"] * per_10k
    review = cost["review_cost_usd"] * per_10k
    axes[1].plot(
        cost["threshold"], missed, marker="o", markersize=3, label="Missed-fraud $ lost"
    )
    axes[1].plot(
        cost["threshold"],
        review,
        marker="s",
        markersize=3,
        label="False-alarm review $",
    )
    axes[1].set_xlabel("Decision threshold")
    axes[1].set_ylabel("USD per 10,000 txns")
    axes[1].set_title("Cost split: losses vs. review time")
    axes[1].legend()
    axes[1].grid(alpha=0.3)
    fig.tight_layout()
    return _save(fig, "04_cost_curve.png")


def main(argv: list[str] | None = None) -> int:
    """Build all 4 charts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    chart_01_class_imbalance()
    chart_02_pr_curves()
    chart_03_threshold_tradeoff()
    chart_04_cost_curve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
