# Changelog

All notable changes to the 60-Day Data Analytics + AI Portfolio, newest
first. Days are published one at a time to `main`; there are no versioned
releases.

## Unreleased

### Added (best-practice retrofit, 2026-11-18)

- CI now runs `agents/orchestrator.py --day N validate` for every changed
  day (secret scan, pinned-deps check, data-size rule, screenshot check).
- Test-coverage gate: `pytest-cov` with `--cov=src --cov-report=term-missing`
  and a `--cov-fail-under` threshold set at the measured floor across the
  12 published days (see "Coverage" below).
- Type checking: `mypy` (gradual) in CI and in the per-day `pyproject.toml`;
  new days are strict-by-default.
- Dependabot: weekly pip updates for the root dev requirements and every
  day's `requirements.txt` (`.github/dependabot.yml`).
- Pre-commit hooks (ruff, black, secret scan) via `.pre-commit-config.yaml`.
- `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `.editorconfig`,
  `.python-version` (3.12), issue templates and a pull-request template.
- README badges (CI status, MIT licence, Python 3.12).

### Coverage

Measured 2026-11-18 across the 12 published days (pytest-cov, `--cov=src`,
run from inside each day folder):

| Day | Coverage |
| --- | --- |
| 01 — Crypto Market Intelligence Dashboard | 48% |
| 02 — Crypto Risk & Volatility Analyzer | 42% |
| 03 — Crypto Market Anomaly Detector | 53% |
| 04 — YouTube Video Performance Analyzer | 43% |
| 05 — Social Media Sentiment Analyzer | 39% |
| 06 — Viral Content Trend Explorer | 38% |
| 07 — Disease Prevalence Dashboard | 45% |
| 08 — Hospital Readmission Risk Model | 35% |
| 09 — Healthcare Resource Demand Forecast | 43% |
| 10 — Retail Sales Intelligence Dashboard | 41% |
| 11 — Inventory Demand Forecast | 63% |
| 12 — Customer Segmentation Engine | 69% |

The `--cov-fail-under` threshold is set at the measured floor (the lowest
day), rounded down to the nearest 5 — currently **30**, since the lowest
day (Day 08) measures 34.94% in a clean sequential run under the exact CI
invocation (42 passed; 35% would fail it). It rises as coverage improves; the
threshold is a floor, not a target. Streamlit `app.py` files are the
largest uncovered share (they are exercised by the smoke test, not by
pytest).

## 2026-11-18 — Day 12: Customer Segmentation Engine

- RFM + KMeans (k = 2, silhouette 0.4330) on UCI Online Retail: Champions
  1,661 (38.3%) drive 84.9% of attributed revenue (£7,436,335.44);
  Hibernating 2,673 (61.7%) hold 15.1%. pytest 28/28.

## 2026-11-15 — Day 11: Inventory Demand Forecast

- 4-week forecast for the top-20 SKUs (69,194 units) with reorder totals
  (97,314 units); moving average wins overall (WAPE 44.16%). pytest 28/28.

## 2026-11-14 — Day 10: Retail Sales Intelligence Dashboard

- UCI Online Retail, £10,283,243.98 revenue hand-validated; top 222
  customers (5.12%) drive 47.94% of identified revenue. pytest 31/31.

## 2026-11-13 — Day 9: Healthcare Resource Demand Forecast

- Holt-Winters 8-week forecast of respiratory ED visits, 3.03% → 13.87%
  (severe-season scenario at the top end); RMSE 0.4693 vs 0.8244 baseline.
  pytest 39/39.

## 2026-11-12 — Day 8: Hospital Readmission Risk Model

- UCI Diabetes 130-US Hospitals, 101,766 encounters; HistGradientBoosting
  ROC-AUC 0.6761 vs logistic 0.6612. Honest limit: ~1% sensitivity at the
  0.5 cutoff — a triage signal, not a decision-maker. pytest 42/42.

## 2026-11-11 — Day 7: Disease Prevalence Dashboard

- Real CDC PLACES county data; diabetes 12.05% (2023), West Virginia
  highest across the board. pytest 23/23.

## 2026-11-10 — Day 6: Viral Content Trend Explorer

- 472 videos / 406 channels, live YouTube Data API; AI & ML accelerating
  +6.36 pp, Python fading −8.05 pp. Truncation caveat documented (each
  query window returned exactly 50 videos). pytest 22/22.

## 2026-11-09 — Day 5: Social Media Sentiment Analyzer

- 1,462 comments classified with our own rule-based lexicon; validation
  accuracy 0.617, macro-F1 0.613 (disclosed as a limitation). pytest 15/15.

## 2026-11-08 — Day 4: YouTube Video Performance Analyzer

- 244 videos / 143 channels, live YouTube Data API v3; median 611
  views/day; AI & ML and 15–30 min videos strongest. pytest 15/15.

## 2026-11-07 — Day 3: Crypto Market Anomaly Detector

- 54 flagged days (baseline rules + Isolation Forest); union recall 1.000,
  precision 0.974. Forest misses volume surges — disclosed blind spot.
  pytest 25/25.

## 2026-11-06 — Day 2: Crypto Risk & Volatility Analyzer

- VaR/CVaR, Sharpe/Sortino, drawdowns for BTC/ETH/SOL; BTC–ETH
  correlation 0.908. pytest 21/21.

## 2026-11-05 — Day 1: Crypto Market Intelligence Dashboard

- First project: BTC/ETH/SOL daily returns, volatility, drawdown, volume,
  correlation over 366 days (1,098 rows, live CoinGecko). pytest 14/14
  (7 at first build, 14 after the Stage 2 audit fix). Repo created;
  single consolidated CI workflow; "Powered by CoinGecko" attribution;
  raw JSONs kept as the provenance record.
