"""Generate the four static charts from data/processed/*.csv.

Run: python -m src.make_charts  (from the project root, after the pipeline)
Exactly 4 PNGs, offline from the committed processed CSVs only (no network,
no API). Every chart carries the UCI source footnote and, when the data is
synthetic, a SYNTHETIC DATA label.

Honest-chart rules for this day: bars start at 0; rates carry their
denominator (n); chart 01(b) is computed on the committed 1,000-row sample
and says so; chart 02 uses the stored ROC/PR curve points (no smoothed or
invented curves); chart 04(b) shows ROC-AUC by age band only — gender and
race live in subgroup_metrics.csv and the model card.
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
    "Source: UCI Diabetes 130-US Hospitals 1999–2008, "
    "DOI 10.24432/C5230J, CC BY 4.0 — de-identified example data, "
    "not a clinical tool."
)
BLUE = "#1b6ca8"
LIGHT = "#7fb3d5"
ORANGE = "#d35400"
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


def _record() -> dict:
    return json.loads((PROCESSED_DIR / "data_source.json").read_text())


def _is_synthetic() -> bool:
    return bool(_record().get("synthetic"))


def _footnote(fig: plt.Figure, extra: str = "") -> None:
    text = SOURCE_FOOTNOTE + (f" {extra}" if extra else "")
    if _is_synthetic():
        text = "SYNTHETIC DATA — labelled fallback, not UCI values. " + text
    wrapped = "\n".join(textwrap.wrap(text, 115))
    fig.text(0.01, 0.08, wrapped, fontsize=8, color=GREY, ha="left", va="top")


def _metrics() -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / "model_metrics.csv")


_OR_FIELD_LABELS = {
    "discharge_disposition_id_": "Discharge: ",
    "medical_specialty_": "Specialty: ",
    "diag_1_group_": "Diag 1: ",
    "diag_2_group_": "Diag 2: ",
    "diag_3_group_": "Diag 3: ",
    "admission_type_id_": "Admission: ",
    "admission_source_id_": "Source: ",
    "payer_code_": "Payer: ",
    "age_": "Age ",
    "race_": "Race: ",
    "gender_": "Gender: ",
    "max_glu_serum_": "Glucose: ",
    "A1Cresult_": "A1C: ",
    "change_": "Change: ",
    "diabetesMed_": "Diabetes med: ",
}
_DISCHARGE_SHORT = {
    "Discharged/transferred within this institution to Medicare approved swing bed": (
        "Swing bed (Medicare)"
    ),
    "Discharged/transferred to another rehab fac including rehab units of a hospital .": (
        "Rehab facility"
    ),
    "Discharged/transferred/referred to a psychiatric hospital of psychiatric distinct part unit of a hospital": (
        "Psychiatric hospital"
    ),
    "Discharged/transferred to a long term care hospital.": ("Long-term care hospital"),
    "Admitted as an inpatient to this hospital": "Admitted as inpatient",
    "Discharged/transferred to home with home health service": (
        "Home with home health"
    ),
}


def _or_label(feature: str) -> str:
    """Short, distinct display label for a one-hot logistic feature.

    The raw feature names (e.g. three discharge dispositions that all
    start "Discharged/transferred ...") collide when truncated, and
    matplotlib's categorical axis overplots bars that share a label —
    so labels must be distinct, not just short.
    """
    feature = feature.removeprefix("cat__").removeprefix("num__")
    for field, label in _OR_FIELD_LABELS.items():
        if feature.startswith(field):
            level = feature[len(field) :]
            if field == "discharge_disposition_id_":
                level = _DISCHARGE_SHORT.get(level, level)
            return (label + level)[:38]
    return feature[:38]


def chart_01_readmission_overview() -> Path:
    """(a) 3-class readmitted distribution; (b) <30-day rate by prior
    inpatient visits (from the committed 1,000-row sample)."""
    record = _record()
    dist = record["target_distribution_raw"]
    order = ["<30", ">30", "NO"]
    labels = {
        "<30": "Readmitted <30 days",
        ">30": "Readmitted >30 days",
        "NO": "Not readmitted",
    }
    counts = [dist[k] for k in order]
    total = sum(counts)
    sample = pd.read_csv(PROCESSED_DIR / "sample_encounters.csv")
    sample["inpatient_group"] = sample["number_inpatient"].clip(upper=3)
    grouped = (
        sample.groupby("inpatient_group")["target"]
        .agg(["mean", "size"])
        .reindex([0, 1, 2, 3])
    )
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    bars = ax1.barh(
        [labels[k] for k in order][::-1],
        counts[::-1],
        color=[ORANGE, LIGHT, BLUE][::-1],
    )
    ax1.set_xlabel("Encounters (n = 101,766)")
    ax1.set_title("(a) Most encounters are not readmitted within 30 days")
    for bar, count in zip(bars, counts[::-1]):
        ax1.text(
            bar.get_width() + 800,
            bar.get_y() + bar.get_height() / 2,
            f"{count:,} ({count / total * 100:.1f}%)",
            va="center",
            fontsize=10,
        )
    ax1.set_xlim(0, max(counts) * 1.22)
    x = np.arange(4)
    rates = grouped["mean"].to_numpy() * 100
    ns = grouped["size"].to_numpy()
    ax2.bar(x, rates, color=BLUE, width=0.62)
    ax2.set_xticks(x)
    ax2.set_xticklabels(["0", "1", "2", "3+"])
    ax2.set_xlabel("Prior inpatient visits in the previous year")
    ax2.set_ylabel("Readmitted within 30 days (%)")
    ax2.set_title("(b) More prior admissions → higher <30-day rate")
    ax2.set_ylim(0, max(rates) * 1.25)
    for xi, rate, n in zip(x, rates, ns):
        ax2.text(xi, rate + 0.4, f"{rate:.1f}%\n(n={n:,})", ha="center", fontsize=10)
    for spine in ("top", "right"):
        ax1.spines[spine].set_visible(False)
        ax2.spines[spine].set_visible(False)
    fig.tight_layout(rect=(0, 0.10, 1, 1))
    _footnote(
        fig,
        "Panel (b) is computed on the committed 1,000-row cleaned sample, "
        "not the full cohort.",
    )
    out = CHARTS_DIR / "01_readmission_overview.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def chart_02_discrimination() -> Path:
    """(a) ROC curves, both models + chance; (b) PR curves + baseline."""
    metrics = _metrics().set_index("model")
    curves = pd.read_csv(PROCESSED_DIR / "roc_pr_curves.csv")
    colors = {"logistic": BLUE, "histgb": ORANGE}
    names = {"logistic": "Logistic regression", "histgb": "HistGradientBoosting"}
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    ax1.plot([0, 1], [0, 1], color=GREY, linestyle="--", label="Chance (0.50)")
    for name in ("logistic", "histgb"):
        c = curves[(curves["model"] == name) & (curves["curve"] == "roc")]
        ax1.plot(
            c["x"],
            c["y"],
            color=colors[name],
            label=f"{names[name]} (AUC {metrics.loc[name, 'roc_auc']:.3f})",
        )
    ax1.set_xlabel("False positive rate")
    ax1.set_ylabel("True positive rate")
    ax1.set_title("(a) ROC curves — both models beat chance")
    ax1.legend(loc="lower right", fontsize=9)
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1.01)
    ax2.axhline(
        0.1116,
        color=GREY,
        linestyle="--",
        label="Prevalence baseline (0.1116)",
    )
    for name in ("logistic", "histgb"):
        c = curves[(curves["model"] == name) & (curves["curve"] == "pr")]
        ax2.plot(
            c["x"],
            c["y"],
            color=colors[name],
            label=f"{names[name]} (AP {metrics.loc[name, 'pr_auc']:.3f})",
        )
    ax2.set_xlabel("Recall")
    ax2.set_ylabel("Precision")
    ax2.set_title("(b) Precision–recall curves — the honest view at 11% prevalence")
    ax2.legend(loc="upper right", fontsize=9)
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1.01)
    for spine in ("top", "right"):
        ax1.spines[spine].set_visible(False)
        ax2.spines[spine].set_visible(False)
    fig.tight_layout(rect=(0, 0.10, 1, 1))
    _footnote(fig, "Curves are test-set curves (patient-grouped hold-out).")
    out = CHARTS_DIR / "02_discrimination.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def chart_03_calibration() -> Path:
    """Observed vs mean predicted rate per decile, both models + diagonal."""
    metrics = _metrics().set_index("model")
    deciles = pd.read_csv(PROCESSED_DIR / "calibration_deciles.csv")
    colors = {"logistic": BLUE, "histgb": ORANGE}
    names = {"logistic": "Logistic regression", "histgb": "HistGradientBoosting"}
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.plot(
        [0, 0.35], [0, 0.35], color=GREY, linestyle="--", label="Perfect calibration"
    )
    for name in ("logistic", "histgb"):
        d = deciles[deciles["model"] == name].sort_values("decile")
        m = metrics.loc[name]
        ax.plot(
            d["mean_predicted"],
            d["observed_rate"],
            marker="o",
            color=colors[name],
            label=(
                f"{names[name]} — Brier {m['brier']:.3f} "
                f"(baseline {m['brier_baseline']:.3f}), slope "
                f"{m['calibration_slope']:.2f}, intercept "
                f"{m['calibration_intercept']:+.2f}"
            ),
        )
    ax.set_xlabel("Mean predicted risk (decile)")
    ax.set_ylabel("Observed <30-day readmission rate (decile)")
    ax.set_title("Calibration: predicted risk vs observed rate, by decile")
    ax.legend(loc="upper left", fontsize=9)
    ax.set_xlim(0, 0.35)
    ax.set_ylim(0, 0.35)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout(rect=(0, 0.10, 1, 1))
    _footnote(
        fig,
        "Each point is one decile of the test set (n ≈ 2,002 per decile). "
        "Brier baseline is the prevalence-only predictor (0.1006 at the "
        "test-set prevalence 0.1135; 0.0991 at the raw prevalence 0.1116).",
    )
    out = CHARTS_DIR / "03_calibration.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def chart_04_interpretation() -> Path:
    """(a) Logistic odds ratios, top 10 by |log-OR|; (b) ROC-AUC by age band."""
    importance = pd.read_csv(PROCESSED_DIR / "feature_importance.csv")
    odds = importance[
        (importance["model"] == "logistic") & (importance["metric"] == "odds_ratio")
    ].copy()
    odds["abs_log"] = odds["extra"].abs()
    top = odds.sort_values("abs_log", ascending=True).tail(10)
    subgroups = pd.read_csv(PROCESSED_DIR / "subgroup_metrics.csv")
    age = subgroups[
        (subgroups["subgroup_type"] == "age_band") & (subgroups["model"] == "logistic")
    ].copy()
    age_h = subgroups[
        (subgroups["subgroup_type"] == "age_band") & (subgroups["model"] == "histgb")
    ].copy()
    order = [
        "[0-10)",
        "[10-20)",
        "[20-30)",
        "[30-40)",
        "[40-50)",
        "[50-60)",
        "[60-70)",
        "[70-80)",
        "[80-90)",
        "[90-100)",
    ]
    age = age.set_index("subgroup").reindex(order)
    age_h = age_h.set_index("subgroup").reindex(order)
    # [0-10) has 0 readmissions in the test set, so its ROC-AUC is
    # undefined (NaN) — omit it from the bars and say so in the footnote.
    valid = age["roc_auc"].notna() & age_h["roc_auc"].notna()
    order = [band for band, keep in zip(order, valid) if keep]
    age = age.loc[order]
    age_h = age_h.loc[order]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    colors = [ORANGE if v < 1 else BLUE for v in top["value"]]
    ax1.barh(
        [_or_label(f) for f in top["effect_feature"]],
        top["value"],
        color=colors,
    )
    ax1.axvline(1.0, color="black", linewidth=1)
    ax1.set_xscale("log")
    ax1.set_xticks([0.25, 0.5, 1, 2, 5])
    ax1.set_xticklabels(["0.25", "0.5", "1", "2", "5"])
    # Plain numbers, not scientific notation, and no minor-tick labels.
    ax1.xaxis.set_major_formatter(plt.ScalarFormatter())
    ax1.xaxis.set_minor_locator(plt.NullLocator())
    ax1.set_xlim(0.2, 6.5)
    ax1.set_xlabel("Odds ratio for <30-day readmission (log scale; 1.0 = no effect)")
    ax1.set_title("(a) Logistic odds ratios — top 10 by |log-OR|")
    x = np.arange(len(order))
    width = 0.38
    ax2.bar(x - width / 2, age["roc_auc"], width, label="Logistic", color=BLUE)
    ax2.bar(x + width / 2, age_h["roc_auc"], width, label="HistGB", color=ORANGE)
    ax2.set_xticks(x)
    ax2.set_xticklabels(order, rotation=45, ha="right", fontsize=9)
    ax2.set_ylabel("Test-set ROC-AUC")
    ax2.set_title("(b) ROC-AUC by age band — both models")
    ax2.set_ylim(0, 0.9)
    ax2.legend(fontsize=9)
    for spine in ("top", "right"):
        ax1.spines[spine].set_visible(False)
        ax2.spines[spine].set_visible(False)
    fig.tight_layout(rect=(0, 0.10, 1, 1))
    _footnote(
        fig,
        "Panel (a): odds ratios are unadjusted-for-collinearity "
        "coefficients from the one-hot logistic model — read as "
        "associations, not causes. Panel (b): age [0-10) is omitted "
        "(33 patients, 0 readmissions — ROC-AUC undefined); other "
        "small-n bands are flagged in subgroup_metrics.csv.",
    )
    out = CHARTS_DIR / "04_interpretation.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def main() -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    for fn in (
        chart_01_readmission_overview,
        chart_02_discrimination,
        chart_03_calibration,
        chart_04_interpretation,
    ):
        out = fn()
        print(f"wrote {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
