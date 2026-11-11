"""Generate the four static charts from data/processed/*.csv.

Run: python3 -m src.make_charts  (from the project root, after the pipeline)
Exactly 4 PNGs, offline from the committed processed CSVs only (no network,
no API). Every chart carries a CDC source footnote and, when the data is
synthetic, a SYNTHETIC DATA label.

Honest-chart rules for this day: bars start at 0 unless the chart is a
distribution; year-over-year changes are computed on matched counties only
(Kentucky and Pennsylvania have no 2023 rows — see data/README.md), so
chart 03 says so; national bars are population-weighted, never county
means; the default measure is Diabetes and every chart names its measure.
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
    "Source: CDC PLACES County Data, 2025 release (2023) / 2024 release (2022) — "
    "model-based estimates, crude prevalence, adults 18+."
)
MEASURE_LABELS = {
    "DIABETES": "Diabetes",
    "COPD": "COPD",
    "CASTHMA": "Current asthma",
    "CHD": "Coronary heart disease",
    "STROKE": "Stroke",
    "OBESITY": "Obesity",
}
SLUGS = {
    "DIABETES": "diabetes",
    "COPD": "copd",
    "CASTHMA": "asthma",
    "CHD": "chd",
    "STROKE": "stroke",
    "OBESITY": "obesity",
}
COLOR = "#1b6ca8"
LIGHT = "#7fb3d5"
ACCENT = "#c0392b"
GREEN = "#1e8449"
GREY = "#5d6d7e"

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


def _is_synthetic() -> bool:
    record = json.loads((PROCESSED_DIR / "data_source.json").read_text())
    return bool(record.get("synthetic"))


def _footnote(fig: plt.Figure, extra: str = "") -> None:
    text = SOURCE_FOOTNOTE + (f" {extra}" if extra else "")
    if _is_synthetic():
        text = "SYNTHETIC DATA — labelled fallback, not CDC values. " + text
    # Wrapped to two lines: a single fig.text line overflows the right edge.
    wrapped = "\n".join(textwrap.wrap(text, 115))
    fig.text(0.01, 0.045, wrapped, fontsize=8, color=GREY, ha="left", va="top")


def _load(measure: str, year: str) -> pd.DataFrame:
    df = pd.read_csv(
        PROCESSED_DIR / f"prevalence_{SLUGS[measure]}.csv", dtype={"year": str}
    )
    return df[df["year"] == year].copy()


def chart_01_state_ranking() -> Path:
    """All states ranked by population-weighted diabetes prevalence, 2023."""
    state = pd.read_csv(PROCESSED_DIR / "state_prevalence.csv", dtype={"year": str})
    d = state[(state["measureid"] == "DIABETES") & (state["year"] == "2023")]
    d = d.sort_values("state_rate")
    record = json.loads((PROCESSED_DIR / "data_source.json").read_text())
    national = record["national_weighted_vs_us_row"]["DIABETES_2023"]["weighted"]
    fig, ax = plt.subplots(figsize=(10, 12))
    ax.barh(d["stateabbr"], d["state_rate"], color=COLOR)
    ax.axvline(
        national,
        color=ACCENT,
        linestyle="--",
        linewidth=1.5,
        label=f"National (weighted): {national:.2f}%",
    )
    ax.set_xlabel("Estimated diabetes prevalence, % of adults 18+ (2023)")
    ax.set_ylabel("State (population-weighted county estimates)")
    ax.set_title("Diabetes is highest in West Virginia, lowest in DC — 2023")
    ax.set_xlim(0, max(d["state_rate"]) * 1.08)
    ax.legend(loc="lower right")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    _footnote(
        fig,
        "Kentucky and Pennsylvania have no 2023 county rows in the "
        "source release and are absent here.",
    )
    out = CHARTS_DIR / "01_state_ranking.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def chart_02_county_distribution() -> Path:
    """(a) Diabetes county histogram, (b) box plots by measure, 2023."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    d = _load("DIABETES", "2023")["data_value"]
    ax1.hist(d, bins=30, color=COLOR, edgecolor="white")
    ax1.axvline(
        d.median(),
        color=ACCENT,
        linestyle="--",
        linewidth=1.5,
        label=f"Median: {d.median():.1f}%",
    )
    ax1.axvline(d.quantile(0.25), color=GREY, linestyle=":", linewidth=1.2)
    ax1.axvline(
        d.quantile(0.75),
        color=GREY,
        linestyle=":",
        linewidth=1.2,
        label=f"IQR: {d.quantile(0.25):.1f}–{d.quantile(0.75):.1f}%",
    )
    ax1.set_xlabel("Estimated diabetes prevalence, % of adults 18+")
    ax1.set_ylabel("Counties")
    ax1.set_title("(a) Counties: diabetes, 2023")
    ax1.legend()
    frames = [_load(m, "2023")["data_value"] for m in MEASURE_LABELS]
    ax2.boxplot(
        frames,
        tick_labels=[MEASURE_LABELS[m] for m in MEASURE_LABELS],
        orientation="horizontal",
        patch_artist=True,
        boxprops={"facecolor": LIGHT},
        medianprops={"color": ACCENT},
    )
    ax2.set_xlabel("Estimated prevalence, % of adults 18+ (2023)")
    ax2.set_title("(b) Spread differs by condition")
    for spine in ("top", "right"):
        ax1.spines[spine].set_visible(False)
        ax2.spines[spine].set_visible(False)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    _footnote(
        fig,
        "Each box is 2,956 counties. Obesity spans 16.7–52.9%; "
        "asthma spans only 7.8–15.3%.",
    )
    out = CHARTS_DIR / "02_county_distribution.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def chart_03_change() -> Path:
    """(a) Diabetes county pp-changes, (b) median pp-change by measure."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    ch = pd.read_csv(PROCESSED_DIR / "change_diabetes.csv")
    ax1.hist(ch["pp_change"], bins=30, color=COLOR, edgecolor="white")
    ax1.axvline(0, color="black", linewidth=1)
    ax1.axvline(
        ch["pp_change"].median(),
        color=ACCENT,
        linestyle="--",
        linewidth=1.5,
        label=f"Median: {ch['pp_change'].median():+.2f} pp",
    )
    ax1.set_xlabel("Change in diabetes prevalence, percentage points (2022→2023)")
    ax1.set_ylabel("Counties (matched in both years)")
    ax1.set_title("(a) Diabetes: most counties moved a little")
    ax1.legend()
    medians, ups, downs = [], [], []
    for m in MEASURE_LABELS:
        c = pd.read_csv(PROCESSED_DIR / f"change_{SLUGS[m]}.csv")
        medians.append(c["pp_change"].median())
        ups.append(float((c["pp_change"] > 0).mean() * 100))
        downs.append(float((c["pp_change"] < 0).mean() * 100))
    labels = [MEASURE_LABELS[m] for m in MEASURE_LABELS]
    order = np.argsort(medians)
    med = np.array(medians)[order]
    colors = [GREEN if v < 0 else ACCENT if v > 0 else GREY for v in med]
    ax2.barh(np.array(labels)[order], med, color=colors)
    ax2.axvline(0, color="black", linewidth=1)
    ax2.set_yticks(range(len(labels)))
    ax2.set_yticklabels(
        [
            f"{np.array(labels)[order[i]]} — {ups[order[i]]:.0f}% up / "
            f"{downs[order[i]]:.0f}% down"
            for i in range(len(labels))
        ],
        fontsize=9,
    )
    for i, value in enumerate(med):
        ax2.text(
            value + (0.02 if value >= 0 else -0.02),
            i,
            f"{value:+.2f} pp",
            va="center",
            ha="left" if value >= 0 else "right",
            fontsize=10,
        )
    ax2.set_xlim(-0.75, 0.35)
    ax2.set_xlabel("Median county change, percentage points (2022→2023)")
    ax2.set_title("(b) Five of six conditions fell on the median county")
    for spine in ("top", "right"):
        ax1.spines[spine].set_visible(False)
        ax2.spines[spine].set_visible(False)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    _footnote(
        fig,
        "Matched counties only (n=2,956). No 2023 rows for Kentucky/Pennsylvania.",
    )
    out = CHARTS_DIR / "03_change_2022_2023.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def chart_04_measure_comparison() -> Path:
    """National population-weighted prevalence by measure, 2022 vs 2023."""
    record = json.loads((PROCESSED_DIR / "data_source.json").read_text())
    nat = record["national_weighted_vs_us_row"]
    labels, v22, v23, pps = [], [], [], []
    for m, label in MEASURE_LABELS.items():
        labels.append(label)
        v22.append(nat[f"{m}_2022"]["weighted"])
        v23.append(nat[f"{m}_2023"]["weighted"])
        pps.append(nat[f"{m}_2023"]["weighted"] - nat[f"{m}_2022"]["weighted"])
    x = np.arange(len(labels))
    width = 0.38
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.bar(x - width / 2, v22, width, label="2022", color=LIGHT)
    ax.bar(x + width / 2, v23, width, label="2023", color=COLOR)
    for i, pp in enumerate(pps):
        ax.text(
            i,
            max(v22[i], v23[i]) + 1.0,
            f"{pp:+.2f} pp",
            ha="center",
            fontsize=10,
            color=GREEN if pp < 0 else ACCENT,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("National prevalence, % of adults 18+")
    ax.set_title("National rates: five of six conditions edged down in 2023")
    ax.set_ylim(0, max(v22 + v23) * 1.12)
    ax.legend()
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    _footnote(
        fig,
        "Population-weighted. 2023 excludes KY/PA, so the move is partly "
        "compositional.",
    )
    out = CHARTS_DIR / "04_measure_comparison.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def main() -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    for fn in (
        chart_01_state_ranking,
        chart_02_county_distribution,
        chart_03_change,
        chart_04_measure_comparison,
    ):
        out = fn()
        print(f"wrote {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
