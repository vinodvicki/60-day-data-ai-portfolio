# Day 19 — Credit Card Fraud Detection: Research Brief

**Status:** VERIFIED — one lean pass, 2026-11-26.
**Business question:** With only 0.17% of transactions fraudulent, which
classifier catches the most fraud without drowning analysts in false
alarms — and what does each decision threshold cost in dollars?

Roadmap entry (Phase 2, Banking, Finance & Economics): *"Train imbalanced
classifiers and compare recall, precision, and the operational cost of
false alarms."* Deliverable: Fraud detection metrics panel with threshold
tradeoffs. Core skills (Phase 2 block): Classification, financial ratios,
SQL, macroeconomic visualization. Suggested data: FRED, SEC EDGAR, public
fraud benchmark datasets.

## 1. Data sources — verified 2026-11-26 (one pass, no re-search later)

### 1a. Classic credit-card fraud transactions — Hugging Face mirror (NEW, no key)

- **Canonical dataset:** the Kaggle "creditcard.csv" (ULB / Worldline,
  European cardholders, two days in September 2013): 284,807
  transactions, 492 frauds (0.172%), columns Time, V1–V28 (PCA),
  Amount, Class. Kaggle itself requires an account/API key to download —
  no key is available, so Kaggle is NOT the fetch route.
- **Verified no-key source:** Hugging Face dataset
  `RS2k03/creditcard-fraud-dataset`, file `creditcard.csv`, resolved at
  `https://huggingface.co/datasets/RS2k03/creditcard-fraud-dataset/resolve/main/creditcard.csv`
  — public, no key, no login (verified 2026-11-26, HTTP 200).
- **Fingerprint verified on the downloaded file (not just the listing):**
  150,828,752 bytes, md5 `e90efcb83d69faf99fcab8b0255024de`,
  284,807 data rows, 492 frauds (0.1727%), Time 0–172,792 s (2 days),
  Amount $0.00–$25,691.16. Every number matches the published Kaggle
  fingerprint exactly, so this mirror is the same dataset.
- **Attribution:** Dal Pozzolo et al., ULB Machine Learning Group /
  Worldline. The V1–V28 features are PCA components (confidentiality);
  Time is seconds since the first transaction; Amount is the transaction
  value; Class 1 = fraud.
- **Size rule:** the raw file is 144 MB — far over the 1 MB/file and
  5 MB/day commit limits. It is therefore NOT committed: it lives in
  `data/raw/creditcard.csv` (git-ignored, local-only cache) and is
  re-downloaded by `src/data_pipeline.py --live`. Committed data is
  processed aggregates only (see plan §5). Before validate/push the raw
  file is moved out of `data/` to `~/workspace/day-19-data/` (Day 18
  precedent for an oversize local cache) so the validator's data-size
  check passes.

### 1b. UCI — checked, NOT the same dataset

- UCI dataset 350 ("Default of Credit Card Clients") is a different,
  Taiwan credit-default dataset (30,000 rows, 23 demographic/billing
  features) — not the transaction-level fraud data. UCI "Credit Approval"
  (id 27) is credit-card applications, also different. Neither is used.
  No UCI copy of the ULB transaction dataset exists.

### 1c. Synthetic fallback — NOT needed

- Real data verified above, so no synthetic data is generated anywhere.
  Had the mirror failed, the fallback was: seeded generator (seed 42),
  same schema (Time, V1–V28, Amount, Class), ~0.17% fraud, written only
  to files marked synthetic with `data_source.json` recording
  `synthetic: true`. That path stays unused; nothing synthetic is in
  the tree.

## 2. Metric definitions (frozen, reused by every later role)

- **Precision** = TP / (TP + FP): of flagged transactions, how many are
  really fraud. **Recall** = TP / (TP + FN): of real frauds, how many
  are caught. **F1** = harmonic mean of the two.
- **ROC-AUC** is reported but NOT the headline: on a 0.17% problem it
  stays high even for a useless model. **PR-AUC (average precision)** is
  the headline ranking metric for an imbalanced problem.
- **Accuracy is never the headline** — predicting "never fraud" scores
  99.83% accuracy and catches nothing. The majority baseline exists only
  to demonstrate this.
- **Cost model (assumptions labelled everywhere):** a missed fraud costs
  its transaction Amount (money lost); a false alarm costs **$5.00** of
  manual review time (assumption, not a measured figure). Expected cost
  is reported per 10,000 transactions at each threshold, and the
  threshold that minimises it is named. True positives / true negatives
  cost $0 in this model.

## 3. Models (frozen — roadmap says "imbalanced classifiers", plural)

- **Baseline:** majority classifier — predict every transaction legit.
  Shows the accuracy paradox; recall 0, cost = all fraud amounts lost.
- **Logistic regression:** `class_weight="balanced"`, features V1–V28
  plus standardised Amount and Time, C = 1.0, max_iter = 1000.
- **Random forest:** 200 trees, `class_weight="balanced_subsample"`,
  seed 42. The tree/ensemble representative.
- **Split:** stratified 70/30 train/test, seed 42 — the split preserves
  the 0.1727% fraud rate in both halves. All metrics are computed on
  the held-out test set only; the threshold sweep is computed on the
  test set too (stated as a limitation: thresholds are illustrative,
  not tuned on a separate validation set).
- **Threshold sweep:** thresholds 0.05–0.95 in steps of 0.05 for the
  best model (by PR-AUC) and for logistic regression; at each threshold
  record precision, recall, F1, FP count, FN count, missed-fraud dollars
  and expected cost per 10,000 transactions.

## 4. Rate limits / fetch notes

- One file, one HTTP GET, no API key, no rate limit encountered
  (download took ~8 s). The pipeline verifies the fingerprint after
  download (284,807 rows, 492 frauds) and refuses to build on a
  mismatch. `--offline` replays from the local cached raw file with no
  network.

## 5. Known limitations (stated in README, dashboard and insights)

- Two days of 2013 European cardholder data — not current fraud
  patterns, not other regions or card products.
- V1–V28 are anonymised PCA components: no feature-level explanation
  of *why* a transaction looks fraudulent is possible.
- Thresholds are swept on the test set (illustrative); a production
  system would tune them on a separate validation set.
- The $5 false-alarm cost is an assumption; the cost-optimal threshold
  moves if it changes (the cost curve chart shows the sensitivity).

## 6. Handoff to planner

- Next role's first step: read this brief + the roadmap entry above and
  write `plan.md` with the exact file tree (§5), the 9 processed files,
  the 4 charts, and the §8 success checklist. No re-search: every
  endpoint, number and definition above is final.
