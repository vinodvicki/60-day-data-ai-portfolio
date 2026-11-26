"""Day 19 Credit Card Fraud Detection: Streamlit metrics panel.

Reads processed CSVs and charts only — never the raw file. Shows the
model comparison, the threshold tradeoff with a live slider, and the
operational cost curve, with the cost assumptions and limitations on
the page.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
CHARTS_DIR = ROOT / "outputs" / "charts"

st.set_page_config(page_title="Credit Card Fraud Detection — Day 19", layout="wide")
st.title("💳 Credit Card Fraud Detection — Imbalanced Classifiers")
st.markdown(
    "284,807 European card transactions (Sep 2013), 492 frauds (0.17%). "
    "Which classifier catches the most fraud, and what does each alert "
    "threshold cost? All metrics are on the held-out test set."
)

metrics = pd.read_csv(PROCESSED_DIR / "model_metrics.csv")
sweep = pd.read_csv(PROCESSED_DIR / "threshold_sweep.csv")
source = json.loads((PROCESSED_DIR / "data_source.json").read_text())
best_model = str(source["best_model"])

MODEL_LABELS = {
    "baseline_majority": "Majority baseline",
    "logistic_regression": "Logistic regression",
    "random_forest": "Random forest",
}
metrics["model"] = metrics["model"].map(MODEL_LABELS)

st.subheader("Model comparison (threshold 0.50, test set)")
display_cols = [
    "model",
    "precision",
    "recall",
    "f1",
    "pr_auc",
    "roc_auc",
    "tp",
    "fp",
    "fn",
    "cost_per_10k_txns_usd",
]
st.dataframe(metrics[display_cols], width="stretch")
st.markdown(
    "**Read this first:** accuracy is meaningless here — the majority "
    "baseline scores 99.83% accuracy by catching zero fraud. "
    "PR-AUC (average precision) is the headline ranking metric on a "
    "0.17% problem; ROC-AUC stays high even for a useless model."
)

st.subheader("Threshold tradeoff — pick a threshold, see the cost")
best_label = MODEL_LABELS[best_model]
model_choice = st.selectbox(
    "Model",
    options=["logistic_regression", "random_forest"],
    format_func=lambda name: MODEL_LABELS[name],
    index=0 if best_model == "logistic_regression" else 1,
)
sub = sweep[sweep["model"] == model_choice].sort_values("threshold")
threshold = st.slider(
    "Decision threshold (flag as fraud when score ≥ threshold)",
    min_value=0.05,
    max_value=0.95,
    value=float(source["best_threshold"]),
    step=0.05,
)
row = sub.iloc[(sub["threshold"] - threshold).abs().argmin()]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Precision", f"{row['precision']:.3f}")
col2.metric("Recall", f"{row['recall']:.3f}")
col3.metric("False alarms", f"{int(row['fp']):,}")
col4.metric("Cost / 10k txns", f"${row['cost_per_10k_txns_usd']:,.0f}")
st.markdown(
    f"At threshold {row['threshold']:.2f}: {int(row['tp'])} frauds caught, "
    f"{int(row['fn'])} missed (USD {row['missed_fraud_usd']:,.0f} lost), "
    f"{int(row['fp'])} false alarms (USD {row['review_cost_usd']:,.0f} review)."
)
st.markdown(
    f"Cost-optimal threshold for {best_label}: "
    f"**{source['best_threshold']:.2f}** "
    f"(${source['best_threshold_cost_per_10k_usd']:,.0f} per 10,000 "
    f"transactions; precision "
    f"{source['best_threshold_precision']:.2f}, recall "
    f"{source['best_threshold_recall']:.2f})."
)

st.subheader("Charts")
st.image(
    str(CHARTS_DIR / "01_class_imbalance.png"),
    caption="Class imbalance and Amount by class",
)
st.image(
    str(CHARTS_DIR / "02_pr_curves.png"), caption="Precision–recall curves (test set)"
)
st.image(
    str(CHARTS_DIR / "03_threshold_tradeoff.png"),
    caption="Threshold tradeoff, best model",
)
st.image(
    str(CHARTS_DIR / "04_cost_curve.png"), caption="Operational cost vs. threshold"
)

st.subheader("Cost assumptions (labelled, not measured)")
st.markdown(
    "- A missed fraud costs its transaction Amount (money lost).\n"
    "- A false alarm costs **$5.00** of manual review time — an "
    "assumption. The cost-optimal threshold moves if it changes.\n"
    "- True positives and true negatives cost $0 in this model."
)
st.subheader("Limitations")
st.markdown(
    "- Two days of 2013 European cardholder data — not current fraud "
    "patterns, not other regions or card products.\n"
    "- V1–V28 are anonymised PCA components: no feature-level "
    "explanation of *why* a transaction looks fraudulent is possible.\n"
    "- Thresholds are swept on the test set and are illustrative; a "
    "production system would tune them on a separate validation set.\n"
    "- The $5 review cost is an assumption (see above)."
)
st.caption(
    "Source: ULB / Worldline credit-card transactions via the Hugging "
    "Face mirror (see data/README.md). Real data — nothing synthetic."
)
