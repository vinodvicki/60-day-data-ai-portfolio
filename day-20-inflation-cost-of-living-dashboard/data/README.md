# Data provenance — Day 20 Inflation & Cost of Living Dashboard

## Source

- **Provider:** U.S. Bureau of Labor Statistics (BLS), via FRED (Federal
  Reserve Bank of St. Louis).
- **Endpoint:** `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES_ID>`
  — one GET per series, no API key, no account. Accessed 2026-11-27.
- **Series (10):** CPIAUCSL (headline CPI), CPILFESL (core), CPIFABSL (food
  at home), CPIENGSL (energy), CPIHOSSL (housing), CPITRNSL
  (transportation), CPIAPPSL (apparel), CPIMEDSL (medical care), CPIEDUSL
  (education), CES0500000003 (average hourly earnings, total private).
  All seasonally adjusted; CPI index base 1982–84 = 100.
- **Licence / attribution:** U.S. government statistics, free to use with
  attribution. Every doc and the dashboard footer carry: "Source: U.S.
  Bureau of Labor Statistics via FRED (Federal Reserve Bank of St. Louis)."

## Fetch outcome

- All 10 series returned HTTP 200 on 2026-11-27. Raw files are the
  verbatim FRED downloads, saved as `data/raw/<SERIES>.csv`
  (`DATE,VALUE` per FRED; the header is `observation_date,<SERIES>`).
- **Latest month: October 2026** (FRED lag ≈ 1 month; the November 2026
  CPI is scheduled for release 2026-12-10).
- **The October 2025 gap (read this first):** BLS published no headline
  or core CPI for October 2025 — it could not collect the survey data
  during the 2025 lapse in appropriations (federal shutdown) and cannot
  collect it retroactively. The raw files contain the 2025-10-01 row with
  an empty value; the pipeline keeps that row (it does not drop it) so
  every 12-month change stays aligned. Consequences, all handled in the
  code: the October 2026 year-on-year change is undefined for every CPI
  series (the latest reported YoY is September 2026), and the November
  2025 month-on-month change is undefined. Average hourly earnings do
  have an October 2025 value ($36.85), so the earnings series is complete.
- The live fetch was interrupted twice by service restarts after 1–2
  series; the pipeline's `--live` path had already been exercised for
  those series, and the build was completed from the verbatim downloads
  with `--offline` (same build code, no network). A clean-checkout
  `--live` re-run re-downloads all 10 series.

## Row counts and coverage

- Joint window: **2006-03 → 2026-10, 248 months (247 observed + the
  missing Oct 2025)**. Set by earnings availability (starts 2006-03).
- Headline CPI history (`data/processed/cpi_history.csv`): 1947-01 →
  2026-10, 958 months (same single missing month).
- Processed files (frozen list, plan.md §4): `monthly_panel.csv` (248
  rows × 11 cols), `cpi_history.csv` (958), `yoy_inflation.csv` (248),
  `category_cumulative.csv` (248), `real_earnings.csv` (248),
  `basket_cost.csv` (248), `summary_stats.csv` (10 rows), plus
  `data_source.json`.

## Commit rule for data files

- Small raw data IS committed: the 10 raw CSVs total ~150 KB (each under
  1 MB, day total under 5 MB) and are part of the deliverable —
  `.gitignore` does NOT exclude `data/`. Synthetic fallback output would
  go to `data/raw/*_synthetic.csv` (git-ignored, never overwriting real
  files); no synthetic data was used in this build (`synthetic: false`).

## Manual validation (one metric, by hand)

- Headline YoY, Sep 2026, from the raw values: 336.298 / 324.245 − 1 =
  3.717% — matches `yoy_inflation.csv` (3.717251%) to 6 decimals and
  BLS's published 3.7%. Full hand-validation record: `test_report.md`.

## Versions used for this build

- Python 3.12.3; pandas 3.1.1, numpy 2.5.4, matplotlib 3.11.2,
  streamlit 1.66.1, requests 2.34.2, pytest 9.2.0, pytest-cov 7.1.0,
  scipy 1.18.1 (see `requirements.txt`).
