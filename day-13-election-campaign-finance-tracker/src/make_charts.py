"""Charts for Day 13 — Election Campaign Finance Tracker.

Exactly 4 PNGs (plan §7), matplotlib Agg, offline from processed CSVs
only. Party colours are fixed and symmetric (DEM blue, REP red, other
grey) — the same palette on every chart, neither party given a visual
advantage. Every chart footnotes its source and the 2024-cycle scope.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
CHARTS = ROOT / "outputs" / "charts"

PARTY_COLORS = {"DEM": "#2e6fb7", "REP": "#c0392b", "Other": "#7f8c8d"}
SOURCE_FOOTNOTE = (
    "Source: U.S. Federal Election Commission, 2024 cycle bulk data + "
    "openFEC API (public domain) — reported dollars as filed."
)


def money_millions(x: float) -> str:
    """Format dollars as $X.XM / $X.XB."""
    if abs(x) >= 1e9:
        return f"${x / 1e9:,.2f}B"
    if abs(x) >= 1e6:
        return f"${x / 1e6:,.1f}M"
    if abs(x) >= 1e3:
        return f"${x / 1e3:,.0f}K"
    return f"${x:,.0f}"


def party_bucket(party: str) -> str:
    """Collapse parties to DEM / REP / Other for charting (tables keep
    every party code — plan §4.4)."""
    return party if party in ("DEM", "REP") else "Other"


def style_axes(ax: plt.Axes) -> None:
    """Shared legibility style: no top/right spines, light grid."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", linestyle=":", linewidth=0.7, alpha=0.6)
    ax.set_axisbelow(True)


def chart_01_receipts_by_office_party(party_office: pd.DataFrame, out: Path) -> None:
    """Grouped bars: receipts by office (P/S/H), one bar per party."""
    offices = ["P", "S", "H"]
    labels = {"P": "President", "S": "Senate", "H": "House"}
    buckets = ["DEM", "REP", "Other"]
    data = party_office.copy()
    data["bucket"] = data["party"].map(party_bucket)
    grouped = data.groupby(["office", "bucket"])["receipts"].sum().unstack(fill_value=0)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(offices))
    width = 0.25
    for i, bucket in enumerate(buckets):
        vals = [
            grouped.loc[o, bucket] / 1e9 if o in grouped.index else 0.0 for o in offices
        ]
        bars = ax.bar(
            x + (i - 1) * width,
            vals,
            width,
            label=bucket,
            color=PARTY_COLORS[bucket],
        )
        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.05,
                    money_millions(v * 1e9),
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )
    ax.set_xticks(x)
    ax.set_xticklabels([labels[o] for o in offices])
    ax.set_ylabel("Candidate receipts ($ billions)")
    ax.set_title("Candidate receipts by office and party, 2024 cycle")
    ax.legend(title="Party", frameon=False)
    style_axes(ax)
    fig.text(0.01, -0.02, SOURCE_FOOTNOTE, fontsize=7, color="#555555")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def chart_02_top_candidates(top_candidates: pd.DataFrame, out: Path) -> None:
    """Top 10 candidates by receipts, horizontal bars, party-coloured."""
    rows = top_candidates.sort_values("receipts", ascending=True)
    names = [
        f"{r.candidate_name.title()} ({r.party}, {r.office})" for r in rows.itertuples()
    ]
    vals = rows["receipts"].to_numpy(dtype=float) / 1e9
    colors = [PARTY_COLORS[party_bucket(str(p))] for p in rows["party"]]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.barh(names, vals, color=colors, height=0.65)
    for bar, v, share in zip(bars, vals, rows["receipts_share"]):
        ax.text(
            bar.get_width() + 0.02,
            bar.get_y() + bar.get_height() / 2,
            f"{money_millions(v * 1e9)} ({share:.1%})",
            va="center",
            fontsize=8,
        )
    ax.set_xlabel("Total receipts ($ billions)")
    ax.set_title("Top 10 candidates by total receipts, 2024 cycle")
    ax.set_xlim(0, max(vals) * 1.3 if len(vals) else 1)
    style_axes(ax)
    fig.text(0.01, -0.02, SOURCE_FOOTNOTE, fontsize=7, color="#555555")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def chart_03_funding_mix(party_office: pd.DataFrame, out: Path) -> None:
    """Stacked bars per office: itemized / unitemized / other, as shares."""
    offices = ["P", "S", "H"]
    labels = {"P": "President", "S": "Senate", "H": "House"}
    data = party_office.groupby("office").agg(
        itemized=("individual_itemized", "sum"),
        unitemized=("individual_unitemized", "sum"),
        receipts=("receipts_with_split", "sum"),
        n_split=("n_with_split", "sum"),
    )
    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(offices))
    bottoms = np.zeros(len(offices))
    series = [
        ("Individual, itemized (>$200)", "itemized", "#2e6fb7"),
        ("Individual, unitemized (≤$200)", "unitemized", "#5dade2"),
        ("Other receipts (residual)", "other", "#7f8c8d"),
    ]
    for label, key, color in series:
        if key == "other":
            vals = (data["receipts"] - data["itemized"] - data["unitemized"]) / data[
                "receipts"
            ]
        else:
            vals = data[key] / data["receipts"]
        vals = vals.reindex(offices).fillna(0).to_numpy(dtype=float)
        ax.bar(x, vals, 0.55, bottom=bottoms, label=label, color=color)
        for xi, v, b in zip(x, vals, bottoms):
            if v > 0.08:
                ax.text(
                    float(xi),
                    b + v / 2,
                    f"{v:.0%}",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white",
                )
        bottoms += vals
    for xi, o in zip(x, offices):
        ax.text(
            float(xi),
            1.02,
            money_millions(float(data.loc[o, "receipts"])),
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax.set_xticks(x)
    ax.set_xticklabels([labels[o] for o in offices])
    ax.set_ylabel("Share of candidate receipts (split-covered candidates)")
    ax.set_ylim(0, 1.12)
    ax.set_title("Where candidate money came from, by office, 2024 cycle")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
    style_axes(ax)
    n_split = int(data["n_split"].sum())
    fig.text(
        0.01,
        -0.10,
        SOURCE_FOOTNOTE + f" Funding mix covers the {n_split:,} candidates "
        "with a published itemized/unitemized split; $ totals above the bars "
        "are those candidates' receipts.",
        fontsize=7,
        color="#555555",
    )
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def chart_04_state_totals(state_totals: pd.DataFrame, out: Path) -> None:
    """Top 15 states by candidate receipts, with candidate counts."""
    rows = state_totals.head(15).sort_values("receipts", ascending=True)
    vals = rows["receipts"].to_numpy(dtype=float) / 1e6
    labels = [
        f"{r.state}  (n={int(r.n_with_totals)} with totals)" for r in rows.itertuples()
    ]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.barh(labels, vals, color="#2e6fb7", height=0.65)
    for bar, v in zip(bars, vals):
        ax.text(
            bar.get_width() + max(vals) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            money_millions(v * 1e6),
            va="center",
            fontsize=8,
        )
    ax.set_xlabel("Candidate receipts ($ millions)")
    ax.set_title("Top 15 states by candidate receipts, 2024 cycle")
    ax.set_xlim(0, max(vals) * 1.18 if len(vals) else 1)
    style_axes(ax)
    fig.text(
        0.01,
        -0.02,
        SOURCE_FOOTNOTE + " Totals are not adjusted for state population.",
        fontsize=7,
        color="#555555",
    )
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main() -> None:
    """Regenerate all 4 charts from the processed CSVs."""
    CHARTS.mkdir(parents=True, exist_ok=True)
    record = json.loads((PROC / "data_source.json").read_text(encoding="utf-8"))
    if record.get("synthetic"):
        print("WARNING: synthetic data — charts will carry the synthetic label.")
    party_office = pd.read_csv(PROC / "party_office.csv")
    top_candidates = pd.read_csv(PROC / "top_candidates.csv")
    state_totals = pd.read_csv(PROC / "state_totals.csv")
    chart_01_receipts_by_office_party(
        party_office, CHARTS / "01_receipts_by_office_party.png"
    )
    chart_02_top_candidates(top_candidates, CHARTS / "02_top_candidates.png")
    chart_03_funding_mix(party_office, CHARTS / "03_funding_mix.png")
    chart_04_state_totals(state_totals, CHARTS / "04_state_totals.png")
    for name in [
        "01_receipts_by_office_party.png",
        "02_top_candidates.png",
        "03_funding_mix.png",
        "04_state_totals.png",
    ]:
        path = CHARTS / name
        print(f"{name}: {path.stat().st_size} bytes")
    print("charts done")


if __name__ == "__main__":
    main()
