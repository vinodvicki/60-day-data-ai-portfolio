"""Day 19 Credit Card Fraud Detection: data pipeline.

Downloads the classic ULB/Worldline credit-card fraud transactions from
the verified no-key Hugging Face mirror (research_brief.md §1a),
fingerprints the file, trains three imbalanced classifiers on a
stratified 70/30 split (seed 42) and writes the processed tables the
dashboard, charts and notebook read.

Modes:
    --live       download from Hugging Face, then build (default)
    --offline    replay from the local cached raw file, no network
    --use-cache  use the raw file if present, else download

The raw file is 144 MB and is NOT committed (git-ignored, local-only
cache in data/raw/). Only the small processed tables are committed.
Real data only — no synthetic data is generated anywhere in this day.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_curve
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

try:
    from src.analysis import (
        REVIEW_COST_USD,
        confusion_at_threshold,
        metrics_at_threshold,
        ranking_metrics,
        summarise_amounts,
        summarise_classes,
        threshold_sweep,
    )
except ImportError:  # running as a script from inside src/
    from analysis import (  # type: ignore[no-redef]
        REVIEW_COST_USD,
        confusion_at_threshold,
        metrics_at_threshold,
        ranking_metrics,
        summarise_amounts,
        summarise_classes,
        threshold_sweep,
    )

# --- Frozen configuration (plan.md §3) -------------------------------------

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_PATH = RAW_DIR / "creditcard.csv"

HF_URL = (
    "https://huggingface.co/datasets/RS2k03/creditcard-fraud-dataset"
    "/resolve/main/creditcard.csv"
)
EXPECTED_ROWS = 284_807
EXPECTED_FRAUD = 492
EXPECTED_MD5 = "e90efcb83d69faf99fcab8b0255024de"
EXPECTED_BYTES = 150_828_752

SEED = 42
TEST_SIZE = 0.30
FEATURES = [f"V{i}" for i in range(1, 29)] + ["Amount_scaled", "Time_scaled"]
THRESHOLDS = [round(0.05 * i, 2) for i in range(1, 20)]  # 0.05 .. 0.95


def md5_of(path: Path) -> str:
    """MD5 hex digest of a file, streamed in 1 MB chunks."""
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1_048_576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_fingerprint(path: Path) -> dict[str, Any]:
    """Check the downloaded file against the published Kaggle fingerprint.

    Raises ValueError on any mismatch — the build refuses to run on data
    that is not the documented dataset.
    """
    size = path.stat().st_size
    if size != EXPECTED_BYTES:
        raise ValueError(f"raw size {size} != expected {EXPECTED_BYTES}")
    digest = md5_of(path)
    if digest != EXPECTED_MD5:
        raise ValueError(f"raw md5 {digest} != expected {EXPECTED_MD5}")
    df = pd.read_csv(path, usecols=["Class"])
    n_rows = len(df)
    n_fraud = int(np.sum(df["Class"].to_numpy(dtype=int) == 1))
    if n_rows != EXPECTED_ROWS or n_fraud != EXPECTED_FRAUD:
        raise ValueError(
            f"raw rows/fraud {n_rows}/{n_fraud} != "
            f"expected {EXPECTED_ROWS}/{EXPECTED_FRAUD}"
        )
    return {"rows": n_rows, "fraud": n_fraud, "md5": digest, "bytes": size}


def download_raw() -> Path:
    """Download the dataset from the Hugging Face mirror (one GET)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {HF_URL} ...")
    with requests.get(HF_URL, stream=True, timeout=300) as response:
        response.raise_for_status()
        with RAW_PATH.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1_048_576):
                if chunk:
                    handle.write(chunk)
    print(f"Downloaded {RAW_PATH} ({RAW_PATH.stat().st_size} bytes)")
    return RAW_PATH


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Scale Amount/Time (V1–V28 are already PCA-scaled) and split X/y."""
    features = df[[f"V{i}" for i in range(1, 29)]].copy()
    features["Amount_scaled"] = df["Amount"].to_numpy(dtype=float)
    features["Time_scaled"] = df["Time"].to_numpy(dtype=float)
    return features, df["Class"].astype(int)


def train_models(x_train: pd.DataFrame, y_train: pd.Series) -> dict[str, Any]:
    """Train the three frozen models (plan.md §3)."""
    models: dict[str, Any] = {}
    baseline = DummyClassifier(strategy="most_frequent")
    baseline.fit(x_train, y_train)
    models["baseline_majority"] = baseline
    logreg = LogisticRegression(
        class_weight="balanced", C=1.0, max_iter=1000, random_state=SEED
    )
    logreg.fit(x_train, y_train)
    models["logistic_regression"] = logreg
    forest = RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced_subsample",
        random_state=SEED,
        n_jobs=-1,
    )
    forest.fit(x_train, y_train)
    models["random_forest"] = forest
    return models


def run_pipeline(mode: str) -> dict[str, Any]:
    """Run the full pipeline in the requested mode; return run summary."""
    if mode == "live" or (mode == "use-cache" and not RAW_PATH.exists()):
        download_raw()
    elif mode == "offline" and not RAW_PATH.exists():
        raise FileNotFoundError(
            f"{RAW_PATH} not found — run with --live once to download it, "
            "or place the verified file there (see data/README.md)."
        )
    fingerprint = verify_fingerprint(RAW_PATH)
    print(
        f"Fingerprint OK: {fingerprint['rows']} rows, "
        f"{fingerprint['fraud']} frauds, md5 {fingerprint['md5'][:12]}..."
    )

    df = pd.read_csv(RAW_PATH)
    features, target = build_features(df)
    x_train, x_test, y_train, y_test = train_test_split(
        features, target, test_size=TEST_SIZE, random_state=SEED, stratify=target
    )
    scaler = StandardScaler()
    x_train_scaled = x_train.copy()
    x_test_scaled = x_test.copy()
    for col in ("Amount_scaled", "Time_scaled"):
        x_train_scaled[col] = scaler.fit_transform(x_train[[col]]).ravel()
        x_test_scaled[col] = scaler.transform(x_test[[col]]).ravel()

    models = train_models(x_train_scaled, y_train)
    y_test_np = y_test.to_numpy(dtype=int)
    amounts_test = df.loc[y_test.index, "Amount"].to_numpy(dtype=float)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    class_summary = summarise_classes(df)
    class_summary.to_csv(PROCESSED_DIR / "class_summary.csv", index=False)
    amount_summary = summarise_amounts(df)
    amount_summary.to_csv(PROCESSED_DIR / "amount_summary.csv", index=False)

    # Binned log10(Amount) histogram per class (chart 01) — stored so the
    # chart builder never needs the 144 MB raw file.
    positive = df.loc[df["Amount"] > 0, ["Amount", "Class"]]
    log_amount = np.log10(positive["Amount"].to_numpy(dtype=float))
    edges = np.linspace(-2.0, 4.0, 41)
    hist_rows: list[dict[str, float]] = []
    for cls in (0, 1):
        counts, _ = np.histogram(
            log_amount[positive["Class"].to_numpy() == cls], bins=edges
        )
        for i, count in enumerate(counts):
            hist_rows.append(
                {
                    "bin_left": float(edges[i]),
                    "bin_right": float(edges[i + 1]),
                    "bin_center": float((edges[i] + edges[i + 1]) / 2.0),
                    "Class": float(cls),
                    "count": float(count),
                }
            )
    pd.DataFrame(hist_rows).to_csv(PROCESSED_DIR / "amount_hist.csv", index=False)

    metric_rows: list[dict[str, Any]] = []
    confusion_rows: list[dict[str, Any]] = []
    scores: dict[str, np.ndarray] = {}
    for name, model in models.items():
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(x_test_scaled)
            score = np.asarray(proba)[:, 1].astype(float)
        else:
            score = model.predict(x_test_scaled).astype(float)
        scores[name] = score
        ranks = ranking_metrics(y_test_np, score)
        metrics = metrics_at_threshold(y_test_np, score, 0.5)
        conf = confusion_at_threshold(y_test_np, score, 0.5)
        missed = float(np.sum(amounts_test[(score < 0.5) & (y_test_np == 1)]))
        total_cost = conf["fp"] * REVIEW_COST_USD + missed
        metric_rows.append(
            {
                "model": name,
                "threshold": 0.5,
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "accuracy": metrics["accuracy"],
                "pr_auc": ranks["pr_auc"],
                "roc_auc": ranks["roc_auc"],
                "tp": conf["tp"],
                "fp": conf["fp"],
                "tn": conf["tn"],
                "fn": conf["fn"],
                "missed_fraud_usd": missed,
                "total_cost_usd": total_cost,
                "cost_per_10k_txns_usd": total_cost / len(y_test_np) * 10_000.0,
            }
        )
        confusion_rows.append({"model": name, **conf})
        print(
            f"{name}: PR-AUC {ranks['pr_auc']:.4f} ROC-AUC "
            f"{ranks['roc_auc']:.4f} P {metrics['precision']:.4f} "
            f"R {metrics['recall']:.4f}"
        )

    metrics_df = pd.DataFrame(metric_rows)
    metrics_df.to_csv(PROCESSED_DIR / "model_metrics.csv", index=False)
    pd.DataFrame(confusion_rows).to_csv(
        PROCESSED_DIR / "confusion_matrix.csv", index=False
    )

    # Threshold sweep on the best model (by PR-AUC) and logistic regression.
    best_model = str(metrics_df.loc[metrics_df["pr_auc"].idxmax(), "model"])
    sweep_frames: list[pd.DataFrame] = []
    for name in (best_model, "logistic_regression"):
        sweep = threshold_sweep(y_test_np, scores[name], amounts_test, THRESHOLDS)
        sweep["model"] = name
        sweep_frames.append(sweep)
    sweep_df = pd.concat(sweep_frames, ignore_index=True)
    sweep_df = sweep_df[
        [
            "model",
            "threshold",
            "tp",
            "fp",
            "tn",
            "fn",
            "precision",
            "recall",
            "f1",
            "missed_fraud_usd",
            "review_cost_usd",
            "total_cost_usd",
            "cost_per_10k_txns_usd",
        ]
    ]
    sweep_df.to_csv(PROCESSED_DIR / "threshold_sweep.csv", index=False)
    best_sweep = sweep_df[sweep_df["model"] == best_model].copy()
    best_sweep.to_csv(PROCESSED_DIR / "cost_curve.csv", index=False)

    # Exact PR-curve points for the two scoring models (chart 02),
    # downsampled to at most 200 points per model so the committed file
    # stays far under the 1 MB/file rule (the raw curve has ~85k points).
    curve_frames: list[pd.DataFrame] = []
    for name in ("logistic_regression", "random_forest"):
        precisions, recalls, _ = precision_recall_curve(y_test_np, scores[name])
        frame = pd.DataFrame(
            {"model": name, "precision": precisions, "recall": recalls}
        )
        if len(frame) > 200:
            keep = np.unique(np.linspace(0, len(frame) - 1, 200).astype(int))
            frame = frame.iloc[keep]
        curve_frames.append(frame)
    pd.concat(curve_frames, ignore_index=True).to_csv(
        PROCESSED_DIR / "pr_curves.csv", index=False
    )

    best_cost_row = best_sweep.loc[best_sweep["cost_per_10k_txns_usd"].idxmin()]
    data_source = {
        "dataset": "Credit Card Fraud Detection (ULB / Worldline, Kaggle)",
        "mirror": HF_URL,
        "synthetic": False,
        "seed": SEED,
        "rows": fingerprint["rows"],
        "fraud": fingerprint["fraud"],
        "fraud_rate_pct": round(fingerprint["fraud"] / fingerprint["rows"] * 100, 4),
        "md5": fingerprint["md5"],
        "bytes": fingerprint["bytes"],
        "train_rows": len(y_train),
        "test_rows": len(y_test_np),
        "test_fraud": int(np.sum(y_test_np == 1)),
        "best_model": best_model,
        "best_threshold": float(best_cost_row["threshold"]),
        "best_threshold_cost_per_10k_usd": float(
            best_cost_row["cost_per_10k_txns_usd"]
        ),
        "best_threshold_precision": float(best_cost_row["precision"]),
        "best_threshold_recall": float(best_cost_row["recall"]),
        "review_cost_usd_per_false_alarm": REVIEW_COST_USD,
        "review_cost_note": (
            "ASSUMPTION: $5.00 of manual review time per false alarm; "
            "not a measured figure. Missed fraud costs its Amount."
        ),
        "threshold_note": (
            "Thresholds are swept on the test set and are illustrative; "
            "a production system would tune them on a separate validation set."
        ),
    }
    (PROCESSED_DIR / "data_source.json").write_text(
        json.dumps(data_source, indent=2) + "\n"
    )
    print(
        f"Best model: {best_model}; cost-optimal threshold "
        f"{best_cost_row['threshold']:.2f}"
    )
    return data_source


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--live", action="store_true", help="download, then build")
    group.add_argument("--offline", action="store_true", help="use cached raw file")
    group.add_argument(
        "--use-cache", action="store_true", help="use cache if present, else fetch"
    )
    args = parser.parse_args(argv)
    if args.offline:
        mode = "offline"
    elif args.use_cache:
        mode = "use-cache"
    else:
        mode = "live"
    try:
        run_pipeline(mode)
    except (ValueError, FileNotFoundError, requests.RequestException) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
