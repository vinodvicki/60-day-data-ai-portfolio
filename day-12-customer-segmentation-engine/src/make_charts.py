"""Charts for Day 12 — exactly 4 PNGs (plan §7), matplotlib Agg,
offline from the processed CSVs + data_source.json only.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

FOOTNOTE = (
    "Source: UCI Online Retail (Chen 2015), DOI 10.24432/C5BW33, CC BY 4.0 — "
    "historical 2010–2011 data, scores relative to this customer base"
)
SEGMENT_COLOURS = {
    "Champions": "#b71c1c",
    "Loyal Customers": "#1565c0",
    "Big Spenders": "#6a1b9a",
    "Potential Loyalists": "#2e7d32",
    "New Customers": "#00838f",
    "At Risk": "#ef6c00",
    "Hibernating": "#795548",
    "Lost": "#9e9e9e",
}
QUADRANT_COLOURS = {
    "Smooth": "#2e7d32",
    "Erratic": "#1565c0",
    "Intermittent": "#ef6c00",
    "Lumpy": "#c62828",
}


def _colour(segment: str) -> str:
    return SEGMENT_COLOURS.get(segment, "#455a64")


def _footnote(fig: plt.Figure) -> None:
    fig.text(0.01, 0.005, FOOTNOTE, fontsize=7, color="#555555", ha="left")


def _load(day_dir: Path):
    proc = day_dir / "data" / "processed"
    record = json.loads((proc / "data_source.json").read_text(encoding="utf-8"))
    return {
        "rfm": pd.read_csv(proc / "rfm_table.csv"),
        "profile": pd.read_csv(proc / "segment_profile.csv"),
        "sbc": pd.read_csv(proc / "sbc_summary.csv"),
        "agreement": pd.read_csv(proc / "agreement.csv", index_col=0),
        "record": record,
    }


def chart_01(data: dict, out: Path) -> None:
    """RFM-score histogram + customers per segment."""
    rfm, profile = data["rfm"], data["profile"]
    segments = profile[profile["segment"] != "Unattributed (no CustomerID)"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(
        "What the RFM scores look like — relative to this customer base",
        fontsize=12,
        fontweight="bold",
    )
    ax = axes[0]
    ax.hist(
        rfm["rfm_score"],
        bins=np.arange(2.5, 16.5, 1),
        color="#1565c0",
        edgecolor="white",
    )
    ax.set_xlabel("RFM score (R + F + M, range 3–15)")
    ax.set_ylabel("Customers")
    ax.set_title("Distribution of RFM scores", fontsize=10)
    ax.set_xticks(range(3, 16))
    ax = axes[1]
    order = segments.sort_values("n_customers", ascending=True)
    ax.barh(
        order["segment"],
        order["n_customers"],
        color=[_colour(s) for s in order["segment"]],
    )
    for i, (_, row) in enumerate(order.iterrows()):
        ax.text(
            row["n_customers"] + 20,
            i,
            f"{int(row['n_customers']):,}",
            va="center",
            fontsize=9,
        )
    ax.set_xlabel("Customers")
    ax.set_title("Customers per segment (KMeans decides — see §2.0)", fontsize=10)
    ax.set_xlim(0, order["n_customers"].max() * 1.2)
    fig.tight_layout(rect=[0, 0.04, 1, 0.93])
    _footnote(fig)
    fig.savefig(out, dpi=100)
    plt.close(fig)


def chart_02(data: dict, out: Path) -> None:
    """Share of customers vs share of attributed revenue per segment."""
    profile = data["profile"]
    segments = profile[profile["segment"] != "Unattributed (no CustomerID)"].copy()
    segments = segments.sort_values("revenue_gbp", ascending=True)
    unattributed = profile[profile["segment"] == "Unattributed (no CustomerID)"].iloc[0]
    fig, ax = plt.subplots(figsize=(12, 6))
    y = np.arange(len(segments))
    height = 0.38
    ax.barh(
        y + height / 2,
        segments["share_customers"] * 100,
        height,
        color="#90a4ae",
        label="Share of customers (%)",
    )
    ax.barh(
        y - height / 2,
        segments["revenue_share_attributed"] * 100,
        height,
        # D-1 fix (optimizer): one neutral colour for all revenue bars, so
        # the legend swatch matches every bar. Per-segment colours here
        # made the single brown swatch misreadable (Champions is red).
        color="#455a64",
        label="Share of attributed revenue (%)",
    )
    for i, (_, row) in enumerate(segments.iterrows()):
        ax.text(
            max(row["share_customers"], row["revenue_share_attributed"]) * 100 + 1,
            i,
            f"mean £{row['mean_monetary_gbp']:,.0f} / customer",
            va="center",
            fontsize=8,
        )
    ax.set_yticks(y)
    ax.set_yticklabels(segments["segment"], fontsize=9)
    ax.set_xlabel("Share (%)")
    ax.set_title(
        "Who is worth what — share of customers vs share of attributed revenue",
        fontsize=11,
    )
    ax.legend(fontsize=8, loc="lower right")
    ax.set_xlim(0, 100)
    fig.text(
        0.01,
        0.035,
        f"Unattributed revenue (no CustomerID): "
        f"£{unattributed['revenue_gbp']:,.2f} "
        f"({unattributed['revenue_share_total']:.1%} of total cleaned revenue) "
        f"— not assigned to any segment.",
        fontsize=8,
        color="#333333",
    )
    fig.tight_layout(rect=[0, 0.06, 1, 0.96])
    _footnote(fig)
    fig.savefig(out, dpi=100)
    plt.close(fig)


def chart_03(data: dict, out: Path) -> None:
    """KMeans clusters: log10(Frequency) vs log10(Monetary £)."""
    rfm, profile = data["rfm"], data["profile"]
    segments = profile[profile["segment"] != "Unattributed (no CustomerID)"]
    fig, ax = plt.subplots(figsize=(10, 6))
    for segment, sub in rfm.groupby("segment"):
        ax.scatter(
            np.log10(sub["frequency"]),
            np.log10(sub["monetary_gbp"]),
            s=8,
            alpha=0.5,
            color=_colour(str(segment)),
            label=f"{segment} (n={len(sub):,})",
        )
    for _, row in segments.iterrows():
        ax.scatter(
            np.log10(row["median_frequency"]),
            np.log10(row["median_monetary_gbp"]),
            s=220,
            marker="X",
            facecolors="white",
            edgecolors="#111111",
            linewidths=1.4,
            zorder=5,
        )
        ax.annotate(
            f"{row['segment']}\nmed R {row['median_recency_days']:.0f}d",
            (
                np.log10(row["median_frequency"]),
                np.log10(row["median_monetary_gbp"]),
            ),
            fontsize=7,
            xytext=(8, 8),
            textcoords="offset points",
            bbox={
                "boxstyle": "round,pad=0.2",
                "facecolor": "white",
                "alpha": 0.85,
                "edgecolor": "none",
            },
        )
    ax.set_xlabel("log10(Frequency) — distinct orders per customer")
    ax.set_ylabel("log10(Monetary) — GBP per customer")
    ax.set_title(
        "KMeans clusters on log1p + scaled R/F/M — KMeans decides segment "
        "assignment (plan §2.0)",
        fontsize=11,
    )
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout(rect=[0, 0.04, 1, 0.96])
    _footnote(fig)
    fig.savefig(out, dpi=100)
    plt.close(fig)


def chart_04(data: dict, out: Path) -> None:
    """SBC quadrants: ADI (weeks) vs CV², multi-order customers only."""
    record = data["record"]
    per_customer = pd.DataFrame(record["sbc_per_customer"])
    multi = per_customer[per_customer["quadrant"] != "Single-order"]
    single_n = int((per_customer["quadrant"] == "Single-order").sum())
    agreement = float(record["agreement_rate"])
    fig, ax = plt.subplots(figsize=(10, 6))
    for quadrant in ["Smooth", "Erratic", "Intermittent", "Lumpy"]:
        sub = multi[multi["quadrant"] == quadrant]
        ax.scatter(
            sub["adi_weeks"],
            sub["cv2"],
            s=8,
            alpha=0.5,
            color=QUADRANT_COLOURS[quadrant],
            label=f"{quadrant} (n={len(sub):,})",
        )
    ax.axvline(1.32, color="#333333", ls="--", lw=1)
    ax.axhline(0.49, color="#333333", ls="--", lw=1)
    label_box = {
        "boxstyle": "round,pad=0.2",
        "facecolor": "white",
        "alpha": 0.75,
        "edgecolor": "none",
    }
    ax.text(
        0.02,
        0.02,
        "Smooth",
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
        bbox=label_box,
    )
    ax.text(
        0.02,
        0.97,
        "Erratic",
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
        va="top",
        bbox=label_box,
    )
    ax.text(
        0.98,
        0.02,
        "Intermittent",
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
        ha="right",
        bbox=label_box,
    )
    ax.text(
        0.98,
        0.97,
        "Lumpy",
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
        ha="right",
        va="top",
        bbox=label_box,
    )
    ax.set_xlabel("ADI — mean inter-order gap (weeks)")
    ax.set_ylabel("CV² — squared coefficient of variation of per-order £ totals")
    ax.set_title(
        "SBC cross-check — ADI vs CV² (multi-order customers only)\n"
        f"Agreement with KMeans segments: {agreement:.1%} "
        f"(SBC never overrides a KMeans assignment)",
        fontsize=11,
    )
    ax.set_xlim(0, max(2, multi["adi_weeks"].max() * 1.05))
    ax.set_ylim(0, max(1, multi["cv2"].max() * 1.05))
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=4)
    fig.text(
        0.01,
        0.035,
        f"Single-order customers (no ADI): {single_n:,} — excluded from "
        f"the agreement rate.",
        fontsize=8,
        color="#333333",
    )
    fig.tight_layout(rect=[0, 0.07, 1, 0.95])
    _footnote(fig)
    fig.savefig(out, dpi=100)
    plt.close(fig)


def build_charts(day_dir: Path) -> list[Path]:
    """Build all 4 charts; returns the written paths."""
    day_dir = Path(day_dir)
    charts_dir = day_dir / "outputs" / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    data = _load(day_dir)
    outputs = []
    for name, fn in [
        ("01_rfm_scores.png", chart_01),
        ("02_segment_value.png", chart_02),
        ("03_kmeans_clusters.png", chart_03),
        ("04_sbc_quadrants.png", chart_04),
    ]:
        out = charts_dir / name
        fn(data, out)
        outputs.append(out)
    return outputs


def main() -> int:
    day_dir = Path(__file__).resolve().parents[1]
    for path in build_charts(day_dir):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
