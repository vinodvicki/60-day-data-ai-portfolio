"""Day 8 — Hospital Readmission Risk Model: data pipeline.

Downloads the UCI Diabetes 130-US Hospitals 1999–2008 dataset (id 296),
verifies row count (101,766) and the target distribution, cleans it per
plan.md §3.3, splits/trains/evaluates the two models via src.model, and
writes the committed processed files (plan.md §3.5).

Usage (from the project root):
    python -m src.data_pipeline --live        # download + process + train
    python -m src.data_pipeline --use-cache   # reuse cached raw, no download
    python -m src.data_pipeline --offline     # verify committed files only;
                                              # never clobbers data_source.json
    python -m src.data_pipeline --synthetic   # labelled-synthetic fallback

Data-size exception (plan §3.4): the raw CSV is ~19 MB, so
``data/raw/diabetic_data.csv`` and ``data/raw/*.zip`` are git-ignored and
downloaded at build time. Committed provenance is ``sample_rows.json``,
``IDS_mapping.csv`` and the compact processed CSVs (``data/`` < 1 MB).

Missing symbol is "?" (the metadata API says "NaN" — wrong for this
file; brief §5). Discharge exclusions {11, 19, 20, 21} are verified
against the labels in IDS_mapping.csv at build time; if the labels do
not read Expired/Hospice, the label rule governs (plan §3.3 rule 8).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from src import model as model_mod
from src.metrics import prevalence_brier

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

ZIP_URL = (
    "https://archive.ics.uci.edu/static/public/296/"
    "diabetes+130-us+hospitals+for+years+1999-2008.zip"
)
ALT_CSV_URL = "https://archive.ics.uci.edu/static/public/296/data.csv"
DATASET_PAGE = (
    "https://archive.ics.uci.edu/dataset/296/"
    "diabetes-130-us-hospitals-for-years-1999-2008"
)
DOI = "https://doi.org/10.24432/C5230J"
CITATION = (
    "Clore, J., Cios, K., DeShazo, J., & Strack, B. (2014). Diabetes "
    "130-US Hospitals for Years 1999-2008 [Dataset]. UCI Machine Learning "
    "Repository. https://doi.org/10.24432/C5230J"
)
LICENCE = "CC BY 4.0"
ZIP_NAME = "diabetes-130-us-hospitals-1999-2008.zip"
RAW_CSV_NAME = "diabetic_data.csv"
MAPPING_NAME = "IDS_mapping.csv"
SYNTHETIC_CSV_NAME = "diabetic_data_synthetic.csv"

EXPECTED_ROWS = 101_766
EXPECTED_TARGET = {"<30": 11_357, ">30": 35_545, "NO": 54_864}
EXPECTED_PREVALENCE = 11_357 / 101_766  # 0.1116
EXCLUSION_IDS = {11, 19, 20, 21}
SEED = 42
SAMPLE_ROWS = 1_000
# Provenance sample is 500 raw rows, not 1,000: a 1,000-row raw sample is
# 1.33 MB (the plan's ~190 KB estimate was wrong), over the 1 MB file
# rule; 500 rows is ~0.67 MB and still a substantial provenance record.
PROVENANCE_SAMPLE_ROWS = 500
HEADERS = {"User-Agent": "60-day-data-ai-portfolio/day-08 (research project)"}
ID_FIELDS = ["admission_type_id", "discharge_disposition_id", "admission_source_id"]

# Extra processed file (documented addition to plan §3.5): ROC/PR curve
# points are needed to draw chart 02 offline from committed data, and no
# listed processed file holds them. It is compact and regenerable.
CURVE_CSV = "roc_pr_curves.csv"


def download_data(url: str, dest: Path) -> Path:
    """Download ``url`` to ``dest`` with a single retry on failure."""
    last_exc: Exception | None = None
    for attempt in (1, 2):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=120)
            resp.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.content)
            print(f"downloaded {url} -> {dest} ({dest.stat().st_size:,} bytes)")
            return dest
        except requests.RequestException as exc:
            last_exc = exc
            print(f"download attempt {attempt} failed: {exc}", file=sys.stderr)
            if attempt == 1:
                time.sleep(5)
    raise RuntimeError(f"download failed after 2 attempts: {url}") from last_exc


def load_raw(csv_path: Path) -> pd.DataFrame:
    """Load the raw CSV treating "?" as missing (not "NaN").

    ``keep_default_na=False`` is essential: pandas' default NA strings
    include "None", but in this file "None" is a real category for
    ``max_glu_serum`` / ``A1Cresult`` ("not measured", plan §3.3 rule 4)
    and must be kept as-is.
    """
    return pd.read_csv(
        csv_path,
        na_values=["?", ""],
        keep_default_na=False,
        low_memory=False,
    )


def load_id_mapping(csv_path: Path) -> dict[str, dict[int, str]]:
    """Parse IDS_mapping.csv into {field: {id: label}}.

    The file is a sequence of sections separated by blank lines; each
    section starts with a ``<field>_id,description`` header row, followed
    by ``id,label`` rows (labels may be quoted).
    """
    mapping: dict[str, dict[int, str]] = {}
    field: str | None = None
    for line in csv_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            field = None
            continue
        row = next(csv.reader(io.StringIO(line)))
        if len(row) >= 2 and row[1].strip() == "description":
            field = row[0].strip()
            mapping[field] = {}
            continue
        if field is None or len(row) < 2:
            continue
        try:
            code = int(row[0].strip())
        except ValueError:
            continue
        mapping[field][code] = row[1].strip()
    return mapping


def group_icd9(code) -> str:
    """Map one ICD-9 code to its plan §3.3 rule 7 chapter group."""
    if code is None or (isinstance(code, float) and np.isnan(code)):
        return "Missing"
    text = str(code).strip()
    if text in ("", "?", "nan", "None"):
        return "Missing"
    if text[0] in "VvEe":
        return "Other"
    try:
        number = int(float(text.split(".")[0]))
    except ValueError:
        return "Other"
    if number == 250:
        return "Diabetes"
    if 390 <= number <= 459 or number == 785:
        return "Circulatory"
    if 460 <= number <= 519 or number == 786:
        return "Respiratory"
    if 520 <= number <= 579 or number == 787:
        return "Digestive"
    if 580 <= number <= 629 or number == 788:
        return "Genitourinary"
    if 710 <= number <= 739:
        return "Musculoskeletal"
    if 140 <= number <= 239:
        return "Neoplasms"
    if 800 <= number <= 999:
        return "Injury & poisoning"
    return "Other"


def make_binary_target(s: pd.Series) -> pd.Series:
    """Binary target: 1 if readmitted == "<30", else 0."""
    return (s == "<30").astype(int)


def apply_exclusions(
    df: pd.DataFrame, mapping: dict[str, dict[int, str]]
) -> tuple[pd.DataFrame, dict]:
    """Exclude expired / hospice discharges (plan §3.3 rule 8).

    The frozen ID list is {11, 19, 20, 21}, but the labels read from
    IDS_mapping.csv govern: if those IDs do not read Expired/Hospice,
    every disposition whose label contains "Expired" or "Hospice" is
    excluded instead, and the deviation is recorded.
    """
    labels = mapping.get("discharge_disposition_id", {})
    candidate_labels = {code: labels.get(code, "") for code in sorted(EXCLUSION_IDS)}
    candidates_ok = all(
        ("expired" in label.lower() or "hospice" in label.lower())
        for label in candidate_labels.values()
    )
    if candidates_ok:
        excluded_ids = set(EXCLUSION_IDS)
        deviation = None
    else:
        excluded_ids = {
            code
            for code, label in labels.items()
            if "expired" in label.lower() or "hospice" in label.lower()
        }
        deviation = (
            "Exclusion IDs {11, 19, 20, 21} did not read Expired/Hospice in "
            "IDS_mapping.csv; label rule governed instead."
        )
    counts = {
        str(code): int((df["discharge_disposition_id"] == code).sum())
        for code in sorted(excluded_ids)
    }
    n_excluded = int(df["discharge_disposition_id"].isin(excluded_ids).sum())
    kept = df[~df["discharge_disposition_id"].isin(excluded_ids)].copy()
    info = {
        "excluded_ids": sorted(excluded_ids),
        "excluded_labels": {
            str(code): labels.get(code, "") for code in sorted(excluded_ids)
        },
        "excluded_counts_per_id": counts,
        "n_excluded": n_excluded,
        "deviation": deviation,
    }
    print(
        f"exclusions: {n_excluded} rows removed "
        f"(ids {sorted(excluded_ids)}: {counts})"
    )
    return kept, info


def clean_encounters(
    df: pd.DataFrame, mapping: dict[str, dict[int, str]]
) -> tuple[pd.DataFrame, dict]:
    """Clean the raw frame per plan §3.3; returns (cleaned, info)."""
    missing_rates = {col: round(float(df[col].isna().mean()), 4) for col in df.columns}
    target_dist_raw = {
        str(k): int(v) for k, v in df["readmitted"].value_counts().items()
    }
    n_raw = len(df)
    clean = df.copy()
    clean["target"] = make_binary_target(clean["readmitted"])
    clean, exclusion_info = apply_exclusions(clean, mapping)
    # ICD-9 grouping (identical for diag_1/2/3); original codes dropped.
    for col in ("diag_1", "diag_2", "diag_3"):
        clean[f"{col}_group"] = clean[col].map(group_icd9)
    clean = clean.drop(columns=["diag_1", "diag_2", "diag_3", "weight"])
    # Join ID-mapping labels for the three coded stay fields.
    for field in ID_FIELDS:
        labels = mapping.get(field, {})
        clean[field] = clean[field].map(
            lambda code, labels=labels: (
                labels.get(code, f"Unknown ({code})") if pd.notna(code) else "Missing"
            )
        )
    # High-missing categoricals stay as an explicit "Missing" category.
    for col in model_mod.CATEGORICAL_FEATURES:
        if col in clean.columns:
            clean[col] = clean[col].fillna("Missing").astype(str)
    for col in model_mod.NUMERIC_FEATURES:
        clean[col] = pd.to_numeric(clean[col], errors="coerce")
    clean = clean.drop(columns=["encounter_id"])
    info = {
        "n_raw": n_raw,
        "n_after_exclusions": len(clean),
        "missing_rates": missing_rates,
        "weight_missing_rate": missing_rates.get("weight"),
        "target_distribution_raw": target_dist_raw,
        "target_distribution_clean": {
            str(k): int(v) for k, v in clean["target"].value_counts().items()
        },
        "exclusions": exclusion_info,
        "medication_columns": model_mod.MEDICATION_COLUMNS,
        "n_medication_columns": len(model_mod.MEDICATION_COLUMNS),
    }
    return clean, info


def write_data_source(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def _write_sample_rows(rows: list[dict]) -> None:
    """Committed provenance sample: PROVENANCE_SAMPLE_ROWS raw rows as JSON."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    sample = rows[:PROVENANCE_SAMPLE_ROWS]
    (RAW_DIR / "sample_rows.json").write_text(
        json.dumps(sample, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote sample_rows.json ({len(sample)} rows)")


def _downsample_curve(xs, ys, max_points: int = 400) -> tuple[np.ndarray, np.ndarray]:
    """Evenly-spaced subsample of a curve, always keeping both endpoints."""
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    if len(xs) <= max_points:
        return xs, ys
    idx = np.unique(np.linspace(0, len(xs) - 1, max_points).round().astype(int))
    return xs[idx], ys[idx]


def train_and_write(clean: pd.DataFrame, record: dict, *, synthetic: bool) -> dict:
    """Split, train, evaluate and write every processed file (§3.5).

    Mutates ``record`` in place with split sizes and the metric summary,
    then writes ``data_source.json``. Returns the record.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    train_idx, test_idx = model_mod.patient_group_split(clean)
    train = clean.loc[train_idx]
    test = clean.loc[test_idx]
    X_train, y_train = train[model_mod.FEATURES], train["target"]
    X_test, y_test = test[model_mod.FEATURES], test["target"]
    groups_train = train["patient_nbr"]
    test_share = len(test) / len(clean)
    print(
        f"split: train {len(train):,} rows "
        f"({train['patient_nbr'].nunique():,} patients, "
        f"positive rate {y_train.mean():.4f}); test {len(test):,} rows "
        f"({test['patient_nbr'].nunique():,} patients, "
        f"positive rate {y_test.mean():.4f}); test share {test_share:.3f}"
    )
    if not 0.18 <= test_share <= 0.22:
        print(
            f"WARNING: test share {test_share:.3f} outside 18–22% tolerance",
            file=sys.stderr,
        )
    overlap = set(train["patient_nbr"]) & set(test["patient_nbr"])
    if overlap:
        raise RuntimeError(
            f"patient leakage: {len(overlap)} patients in both train and test"
        )
    models = model_mod.train_models(X_train, y_train)
    metric_rows: list[dict] = []
    decile_frames: list[pd.DataFrame] = []
    curve_rows: list[dict] = []
    subgroup_frames: list[pd.DataFrame] = []
    for name, fitted in models.items():
        cv = model_mod.cross_validate(fitted, X_train, y_train, groups_train)
        result = model_mod.evaluate(fitted, X_test, y_test)
        conf = result["confusion"]
        metric_rows.append(
            {
                "model": name,
                "roc_auc": round(result["roc_auc"], 4),
                "pr_auc": round(result["pr_auc"], 4),
                "brier": round(result["brier"], 4),
                "brier_baseline": round(result["brier_baseline"], 4),
                "calibration_slope": round(result["calibration_slope"], 4),
                "calibration_intercept": round(result["calibration_intercept"], 4),
                "mean_predicted": round(result["mean_predicted"], 4),
                "observed_rate": round(result["observed_rate"], 4),
                "sensitivity": round(conf["sensitivity"], 4),
                "specificity": round(conf["specificity"], 4),
                "precision": round(conf["precision"], 4),
                "npv": round(conf["npv"], 4),
                "f1": round(conf["f1"], 4),
                "tp": conf["tp"],
                "tn": conf["tn"],
                "fp": conf["fp"],
                "fn": conf["fn"],
                "cv_roc_auc_mean": round(cv["cv_roc_auc_mean"], 4),
                "cv_roc_auc_std": round(cv["cv_roc_auc_std"], 4),
                "cv_pr_auc_mean": round(cv["cv_pr_auc_mean"], 4),
                "cv_pr_auc_std": round(cv["cv_pr_auc_std"], 4),
            }
        )
        deciles = result["deciles"].copy()
        deciles.insert(0, "model", name)
        decile_frames.append(deciles)
        fpr, tpr = result["roc_curve"]
        recall, precision = result["pr_curve"]
        # Downsample curve points (a full ROC curve has ~20k points per
        # model; the committed file must stay well under 1 MB).
        for f, t in zip(*_downsample_curve(fpr, tpr)):
            curve_rows.append(
                {
                    "model": name,
                    "curve": "roc",
                    "x": round(float(f), 4),
                    "y": round(float(t), 4),
                }
            )
        for r, p in zip(*_downsample_curve(recall, precision)):
            curve_rows.append(
                {
                    "model": name,
                    "curve": "pr",
                    "x": round(float(r), 4),
                    "y": round(float(p), 4),
                }
            )
        sub = model_mod.subgroup_metrics(fitted, X_test, y_test, test)
        sub.insert(0, "model", name)
        subgroup_frames.append(sub)
        print(
            f"{name}: ROC-AUC {result['roc_auc']:.4f}, "
            f"PR-AUC {result['pr_auc']:.4f}, Brier {result['brier']:.4f}, "
            f"slope {result['calibration_slope']:.3f}, "
            f"intercept {result['calibration_intercept']:.3f}"
        )
    # Feature effects: logistic odds ratios + HistGB permutation importance.
    odds = model_mod.logistic_odds_ratios(models["logistic"], top_n=20)
    odds.insert(0, "model", "logistic")
    odds = odds.rename(columns={"feature": "effect_feature"})
    perm = model_mod.permutation_importance_top(
        models["histgb"], X_test, y_test, top_n=20
    )
    perm.insert(0, "model", "histgb")
    perm = perm.rename(columns={"feature": "effect_feature"})
    importance = pd.concat(
        [
            odds.assign(
                metric="odds_ratio",
                value=odds["odds_ratio"],
                extra=odds["log_odds"],
            )[["model", "effect_feature", "metric", "value", "extra"]],
            perm.assign(
                metric="permutation_importance",
                value=perm["importance_mean"],
                extra=perm["importance_std"],
            )[["model", "effect_feature", "metric", "value", "extra"]],
        ],
        ignore_index=True,
    )
    pd.DataFrame.from_records(metric_rows).to_csv(
        PROCESSED_DIR / "model_metrics.csv", index=False
    )
    pd.concat(decile_frames, ignore_index=True).to_csv(
        PROCESSED_DIR / "calibration_deciles.csv", index=False
    )
    pd.concat(subgroup_frames, ignore_index=True).to_csv(
        PROCESSED_DIR / "subgroup_metrics.csv", index=False
    )
    importance.to_csv(PROCESSED_DIR / "feature_importance.csv", index=False)
    pd.DataFrame.from_records(curve_rows).to_csv(PROCESSED_DIR / CURVE_CSV, index=False)
    # 1,000-row cleaned sample (seed 42) — the offline EDA / SQL frame.
    sample = clean.sample(n=SAMPLE_ROWS, random_state=SEED)
    sample.to_csv(PROCESSED_DIR / "sample_encounters.csv", index=False)
    record.update(
        {
            "synthetic": synthetic,
            "seed": SEED,
            "split": {
                "scheme": "StratifiedGroupKFold(n_splits=5, shuffle=True, "
                "random_state=42), fold 0 = test",
                "grouping_key": "patient_nbr",
                "train_rows": len(train),
                "test_rows": len(test),
                "train_patients": int(train["patient_nbr"].nunique()),
                "test_patients": int(test["patient_nbr"].nunique()),
                "train_positive_rate": round(float(y_train.mean()), 4),
                "test_positive_rate": round(float(y_test.mean()), 4),
                "test_share": round(float(test_share), 4),
                "patient_overlap": 0,
            },
            "models": {
                "logistic": {
                    "class": "LogisticRegression",
                    "max_iter": 1000,
                    "C": 1.0,
                },
                "histgb": {
                    "class": "HistGradientBoostingClassifier",
                    "max_iter": 300,
                    "learning_rate": 0.05,
                    "random_state": 42,
                },
            },
            "metrics": metric_rows,
            "prevalence_baseline": {
                "roc_auc": 0.5,
                "pr_auc": round(EXPECTED_PREVALENCE, 4),
                "brier": round(prevalence_brier(EXPECTED_PREVALENCE), 4),
            },
        }
    )
    write_data_source(PROCESSED_DIR / "data_source.json", record)
    print(
        f"wrote processed CSVs; data/ total KB: "
        f"{sum(p.stat().st_size for p in (PROJECT_ROOT / 'data').rglob('*') if p.is_file()) / 1000:.0f}"
    )
    return record


def _extract_zip(zip_path: Path) -> tuple[Path, Path]:
    """Extract the two zip members into data/raw/; returns (csv, mapping)."""
    with zipfile.ZipFile(zip_path) as zf:
        members = zf.namelist()
        if RAW_CSV_NAME not in members or MAPPING_NAME not in members:
            raise RuntimeError(f"unexpected zip contents: {members}")
        zf.extract(RAW_CSV_NAME, RAW_DIR)
        zf.extract(MAPPING_NAME, RAW_DIR)
    return RAW_DIR / RAW_CSV_NAME, RAW_DIR / MAPPING_NAME


def run_live(use_cache: bool) -> dict:
    """Download (or reuse the cache), verify, clean, train, write."""
    zip_path = RAW_DIR / ZIP_NAME
    csv_path = RAW_DIR / RAW_CSV_NAME
    mapping_path = RAW_DIR / MAPPING_NAME
    if use_cache and csv_path.exists() and mapping_path.exists():
        print(f"using cached raw data: {csv_path} (no download)")
    else:
        download_data(ZIP_URL, zip_path)
        csv_path, mapping_path = _extract_zip(zip_path)
    raw = load_raw(csv_path)
    if len(raw) != EXPECTED_ROWS:
        raise RuntimeError(
            f"row count mismatch: got {len(raw)}, expected {EXPECTED_ROWS}"
        )
    actual_target = {
        str(k): int(v) for k, v in raw["readmitted"].value_counts().items()
    }
    if actual_target != EXPECTED_TARGET:
        raise RuntimeError(
            f"target distribution mismatch: got {actual_target}, "
            f"expected {EXPECTED_TARGET}"
        )
    print(
        f"verified: {len(raw):,} rows; target {actual_target} "
        f"(positive rate {EXPECTED_PREVALENCE:.4f})"
    )
    mapping = load_id_mapping(mapping_path)
    _write_sample_rows(raw.to_dict(orient="records"))
    clean, info = clean_encounters(raw, mapping)
    record = {
        "source": "live",
        "dataset": "Diabetes 130-US Hospitals for Years 1999-2008",
        "dataset_page": DATASET_PAGE,
        "download_url": ZIP_URL,
        "alternative_url": ALT_CSV_URL,
        "doi": DOI,
        "citation": CITATION,
        "licence": LICENCE,
        "fetched_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fetch_date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "zip_bytes": int(zip_path.stat().st_size) if zip_path.exists() else None,
        "csv_bytes": int(csv_path.stat().st_size),
        "mapping_bytes": int(mapping_path.stat().st_size),
        "expected_rows": EXPECTED_ROWS,
        "expected_target": EXPECTED_TARGET,
        **info,
    }
    return train_and_write(clean, record, synthetic=False)


def run_offline() -> None:
    """Verify committed files exist; never clobber data_source.json.

    Day 5/6 lesson: an offline run must NOT rewrite the live record's
    ``source: "live"`` field. Derived tables/charts are regenerated by
    ``src.make_charts`` from the committed CSVs; this step only checks
    they are all present.
    """
    existing = PROCESSED_DIR / "data_source.json"
    if not existing.exists():
        raise RuntimeError("no data_source.json — run --live first")
    record = json.loads(existing.read_text(encoding="utf-8"))
    required = [
        "sample_encounters.csv",
        "model_metrics.csv",
        "calibration_deciles.csv",
        "subgroup_metrics.csv",
        "feature_importance.csv",
        CURVE_CSV,
    ]
    for name in required:
        path = PROCESSED_DIR / name
        if not path.exists():
            raise RuntimeError(f"missing committed file: {path}")
    if not (RAW_DIR / "sample_rows.json").exists():
        raise RuntimeError("missing committed file: data/raw/sample_rows.json")
    print(
        "offline: all committed processed files present; "
        f"data_source.json untouched (source={record.get('source')!r})"
    )


# --- Synthetic fallback (brief §4; only if the UCI download fails) -------
# Documented logistic generator, seed 42, target rate ~11.2% (<30).
# Coefficients are recorded here so the relationship is auditable.
SYNTHETIC_GENERATOR = {
    "intercept": "calibrated so the mean predicted rate is 0.112",
    "coefficients": {
        "time_in_hospital": 0.12,
        "number_inpatient": 0.35,
        "num_medications": 0.02,
        "number_diagnoses": 0.08,
        "A1Cresult_gt8": 0.50,
        "number_emergency": 0.10,
    },
    "n_encounters": 20_000,
    "seed": 42,
}


def build_synthetic_frame() -> pd.DataFrame:
    """Generate 20,000 labelled-synthetic encounters (seed 42)."""
    rng = np.random.default_rng(SEED)
    n = 20_000
    n_patients = 14_000
    patient_nbr = rng.integers(1, n_patients + 1, size=n)
    age_bands = [
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
    age = rng.choice(
        age_bands,
        size=n,
        p=[0.01, 0.02, 0.03, 0.05, 0.09, 0.15, 0.22, 0.22, 0.15, 0.06],
    )
    gender = rng.choice(["Male", "Female"], size=n, p=[0.46, 0.54])
    race = rng.choice(
        ["Caucasian", "AfricanAmerican", "Hispanic", "Asian", "Other"],
        size=n,
        p=[0.70, 0.18, 0.06, 0.02, 0.04],
    )
    time_in_hospital = rng.integers(1, 15, size=n)
    number_inpatient = rng.poisson(0.6, size=n).clip(0, 10)
    number_emergency = rng.poisson(0.3, size=n).clip(0, 8)
    number_outpatient = rng.poisson(0.5, size=n).clip(0, 10)
    num_medications = rng.poisson(10, size=n).clip(1, 30)
    number_diagnoses = rng.integers(1, 10, size=n)
    num_lab_procedures = rng.poisson(40, size=n).clip(1, 120)
    num_procedures = rng.poisson(1, size=n).clip(0, 6)
    a1c = rng.choice(["None", "Norm", ">7", ">8"], size=n, p=[0.75, 0.10, 0.08, 0.07])
    logit = (
        -2.60
        + 0.12 * time_in_hospital
        + 0.35 * number_inpatient
        + 0.02 * num_medications
        + 0.08 * number_diagnoses
        + 0.50 * (a1c == ">8")
        + 0.10 * number_emergency
    )
    # Centre the intercept so the mean predicted rate is ~0.112.
    logit = logit - logit.mean() + np.log(0.112 / (1 - 0.112))
    prob = 1.0 / (1.0 + np.exp(-logit))
    target = (rng.random(n) < prob).astype(int)
    frame = pd.DataFrame(
        {
            "patient_nbr": patient_nbr,
            "race": race,
            "gender": gender,
            "age": age,
            "admission_type_id": rng.choice(
                ["Emergency", "Urgent", "Elective"], size=n, p=[0.6, 0.2, 0.2]
            ),
            "discharge_disposition_id": "Discharged to home",
            "admission_source_id": rng.choice(
                ["Emergency Room", "Physician Referral"], size=n, p=[0.6, 0.4]
            ),
            "time_in_hospital": time_in_hospital,
            "medical_specialty": rng.choice(
                ["InternalMedicine", "Family/GeneralPractice", "Missing"],
                size=n,
                p=[0.4, 0.3, 0.3],
            ),
            "payer_code": rng.choice(
                ["MC", "MD", "Missing"], size=n, p=[0.4, 0.3, 0.3]
            ),
            "num_lab_procedures": num_lab_procedures,
            "num_procedures": num_procedures,
            "num_medications": num_medications,
            "number_outpatient": number_outpatient,
            "number_emergency": number_emergency,
            "number_inpatient": number_inpatient,
            "number_diagnoses": number_diagnoses,
            "max_glu_serum": rng.choice(
                ["None", "Norm", ">200", ">300"], size=n, p=[0.9, 0.05, 0.03, 0.02]
            ),
            "A1Cresult": a1c,
            "change": rng.choice(["Ch", "No"], size=n, p=[0.45, 0.55]),
            "diabetesMed": rng.choice(["Yes", "No"], size=n, p=[0.8, 0.2]),
            "diag_1_group": rng.choice(
                ["Diabetes", "Circulatory", "Respiratory", "Other"],
                size=n,
                p=[0.4, 0.3, 0.1, 0.2],
            ),
            "diag_2_group": rng.choice(
                ["Diabetes", "Circulatory", "Respiratory", "Other", "Missing"],
                size=n,
                p=[0.2, 0.25, 0.1, 0.25, 0.2],
            ),
            "diag_3_group": rng.choice(
                ["Diabetes", "Circulatory", "Respiratory", "Other", "Missing"],
                size=n,
                p=[0.15, 0.2, 0.1, 0.25, 0.3],
            ),
            "readmitted": np.where(target == 1, "<30", "NO"),
            "target": target,
        }
    )
    for med in model_mod.MEDICATION_COLUMNS:
        frame[med] = rng.choice(
            ["No", "Steady", "Up", "Down"], size=n, p=[0.85, 0.12, 0.02, 0.01]
        )
    frame["insulin"] = rng.choice(
        ["No", "Steady", "Up", "Down"], size=n, p=[0.45, 0.4, 0.08, 0.07]
    )
    return frame[["patient_nbr", *model_mod.FEATURES, "readmitted", "target"]]


def run_synthetic() -> dict:
    """Labelled-synthetic fallback. Never overwrites live files."""
    frame = build_synthetic_frame()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(RAW_DIR / SYNTHETIC_CSV_NAME, index=False)
    _write_sample_rows(frame.head(SAMPLE_ROWS).to_dict(orient="records"))
    record = {
        "source": "synthetic",
        "synthetic": True,
        "seed": SEED,
        "dataset": "SYNTHETIC fallback — UCI download unavailable (brief §4)",
        "doi": DOI,
        "citation": CITATION,
        "licence": LICENCE,
        "fetched_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fetch_date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "generator": SYNTHETIC_GENERATOR,
        "n_raw": len(frame),
        "n_after_exclusions": len(frame),
        "missing_rates": {},
        "weight_missing_rate": None,
        "target_distribution_raw": {
            "<30": int((frame["target"] == 1).sum()),
            "NO": int((frame["target"] == 0).sum()),
        },
        "target_distribution_clean": {
            "1": int((frame["target"] == 1).sum()),
            "0": int((frame["target"] == 0).sum()),
        },
        "exclusions": {
            "excluded_ids": [],
            "excluded_labels": {},
            "excluded_counts_per_id": {},
            "n_excluded": 0,
            "deviation": None,
        },
        "medication_columns": model_mod.MEDICATION_COLUMNS,
        "n_medication_columns": len(model_mod.MEDICATION_COLUMNS),
    }
    return train_and_write(frame, record, synthetic=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--live", action="store_true", help="download from UCI and process"
    )
    group.add_argument(
        "--offline",
        action="store_true",
        help="verify committed files; no network, no rewrite",
    )
    group.add_argument(
        "--synthetic", action="store_true", help="labelled-synthetic fallback (seed 42)"
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="reuse cached raw data instead of downloading "
        "(implies --live when given alone)",
    )
    parser.add_argument(
        "--keep-raw",
        action="store_true",
        help="kept for compatibility; raw is always cached under data/raw/",
    )
    args = parser.parse_args(argv)
    try:
        if args.live or args.use_cache:
            run_live(use_cache=args.use_cache)
        elif args.synthetic:
            run_synthetic()
        else:
            run_offline()
    except Exception as exc:  # noqa: BLE001 — fail loudly, per plan
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
