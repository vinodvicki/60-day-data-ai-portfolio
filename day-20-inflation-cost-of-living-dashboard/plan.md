# Day 20 — Inflation & Cost of Living Dashboard: Build Plan

**Status:** FROZEN — planner, 2026-11-27. Source of truth for the build.
**Source:** roadmap entry (Banking, Finance & Economics) +
`research_brief.md`. No extra web searches. Describe only what the
roadmap lists: compare consumer prices, earnings, and category-level
price movements over time; deliverable is a purchasing-power dashboard
with clearly labeled assumptions.

## 1. Problem

Prices have risen unevenly since 2006 while pay has not kept pace in
every period. A single headline CPI number hides the story: medical care
has compounded far faster than apparel, energy whipsaws, and nominal
pay rises can be wiped out by inflation. The questions this day answers:

1. How fast have consumer prices risen overall — and in each spending
   category — since March 2006?
2. Has the average worker's pay actually kept up with prices, in real
   (inflation-adjusted) terms?
3. What does a fixed $100 basket from March 2006 cost today, and what
   is a dollar worth now?

## 2. Audience / decision-maker

A household budgeter / personal-finance reader deciding how to think
about pay rises, savings and spending — and any analyst who needs a
plain, sourced picture of what inflation has done to purchasing power
since 2006.

## 3. Data

- Source: FRED `fredgraph.csv`, no key, 10 series (brief §1a). One GET
  per series, sequential, ≥1 s spacing, one retry after 30 s on 5xx.
  Latest month 2026-10 (FRED lag ≈ 1 month — November CPI not yet
  released; dashboard and docs must say so).
- Common joint window: **2006-03 → 2026-10 (248 months, 247 observed)**.
  October 2025 has no headline/core CPI value — BLS did not publish one
  (2025 lapse in appropriations) — so the panel keeps that month as a
  missing row and Oct 2026 YoY is undefined (see data/README.md).
- Raw files are small CSVs (~5–15 KB each, ~100 KB total): COMMITTED in
  `data/raw/<SERIES>.csv` (data-commit rule: each < 1 MB, day total < 5 MB).
- Synthetic fallback (brief §4, seed 42) only to clearly-marked
  `*_synthetic.csv` files, never overwriting real raws; `--offline`
  replays from the committed cache with no network.
- Attribution everywhere: "Source: U.S. Bureau of Labor Statistics via
  FRED (Federal Reserve Bank of St. Louis)."

## 4. File tree (exact)

```
day-20-inflation-cost-of-living-dashboard/
├── README.md  requirements.txt  .gitignore  LICENSE  pyproject.toml
├── .pre-commit-config.yaml
├── research_brief.md  plan.md
├── checkpoint-stage1-researcher.md  checkpoint-stage2-planner.md
├── checkpoint-stage3-coder.md  checkpoint-stage4-tester.md
├── checkpoint-stage5-optimizer.md  checkpoint-stage6-publisher.md
├── coder_handoff.md  test_report.md  optimizer_handoff.md
├── publisher_handoff.md
├── data/
│   ├── README.md
│   ├── raw/
│   │   ├── CPIAUCSL.csv  CPILFESL.csv  CPIFABSL.csv  CPIENGSL.csv
│   │   ├── CPIHOSSL.csv  CPITRNSL.csv  CPIAPPSL.csv  CPIMEDSL.csv
│   │   ├── CPIEDUSL.csv  CES0500000003.csv
│   └── processed/
│       ├── data_source.json
│       ├── monthly_panel.csv
│       ├── cpi_history.csv
│       ├── yoy_inflation.csv
│       ├── category_cumulative.csv
│       ├── real_earnings.csv
│       ├── basket_cost.csv
│       └── summary_stats.csv
├── notebooks/analysis.ipynb
├── src/
│   ├── __init__.py
│   ├── data_pipeline.py
│   ├── analysis.py
│   ├── make_charts.py
│   └── app.py
├── outputs/
│   ├── insights_summary.md
│   └── charts/
│       ├── 01_headline_yoy.png
│       ├── 02_category_divergence.png
│       ├── 03_real_earnings.png
│       └── 04_basket_cost.png
├── screenshots/dashboard.png
└── tests/
    ├── conftest.py
    ├── test_pipeline.py
    ├── test_analysis.py
    ├── test_make_charts.py
    └── test_smoke.py
```

**FROZEN processed-file list (Day 19 lesson):** the 8 files above are the
complete processed set. No file is added after the first pipeline run —
if a chart or the app needs a number, it reads one of these 8. The
pipeline writes exactly these 8 (+ `data_source.json`) and nothing else.

## 5. Per-file responsibilities

- `src/data_pipeline.py` — fetch (live) / load (offline) the 10 raw
  CSVs, parse `DATE,VALUE` (`.` = missing), build the joint monthly
  panel 2006-03 → 2026-10, compute all derived tables, write the 8
  frozen processed files + `data_source.json`. CLI:
  `--live | --offline | --use-cache`. No network in `--offline`.
  Synthetic fallback writes `data/raw/*_synthetic.csv` only.
- `src/analysis.py` — pure functions reused by pipeline/tests:
  `yoy(series)`, `mom(series)`, `cumulative_since(series, base)`,
  `real_earnings(nominal, cpi)`, `basket_cost(cpi, base)`,
  `purchasing_power(cpi)`, `cagr(start, end, periods)`,
  `annualised_vol(log_returns)`, `summarise(series, ...)`. No I/O.
- `src/make_charts.py` — draws the 4 charts from processed CSVs only,
  to scale, legible, 1280 px wide.
- `src/app.py` — Streamlit purchasing-power dashboard: reads processed
  CSVs + charts only; KPI row (latest YoY, cumulative since 2006-03,
  real-wage change, basket cost); category table; the 6 labelled
  assumptions from brief §3 on the page; basket-cost slider
  (recomputes from `basket_cost.csv`); footer attribution.
- `notebooks/analysis.ipynb` — reads processed CSVs only; reproduces
  the headline numbers and the 4 charts inline; `_find_root()` from the
  notebook file location (Day 1 lesson).
- `tests/conftest.py` — sys.path bootstrap (Day 17 fix) + a small seeded
  synthetic fixture (test-only, clearly labelled; never written to
  `data/`).
- `tests/test_pipeline.py` — raw-file shape/constants, processed-file
  existence/shape, offline reproducibility.
- `tests/test_analysis.py` — metric formulas vs. hand-computed values
  (YoY, real earnings, basket cost, CAGR, volatility), edge cases.
- `tests/test_make_charts.py` — charts render from the processed CSVs
  (files exist, non-empty, PNG headers valid).
- `tests/test_smoke.py` — README embeds the 4 charts + dashboard
  preview, all referenced files exist, no secrets in tree.
- `requirements.txt` — pinned to the venv-verified versions (pandas
  3.1.1, numpy 2.5.4, matplotlib 3.11.2, streamlit 1.66.1, requests
  2.34.2, pytest 9.2.0, pytest-cov 7.1.0, jupyter 1.1.1, nbformat
  5.11.1, scipy 1.18.1; dev tools black 26.10.1, ruff 0.17.4, mypy
  2.4.1 in the portfolio-root requirements-dev.txt). No scikit-learn —
  this day is descriptive, no model.

## 6. Charts (4, all embedded in the day README Visuals section at build time)

1. `01_headline_yoy.png` — headline + core YoY inflation 2006-03 →
   2026-10, with a 2% reference line; peak YoY annotated.
2. `02_category_divergence.png` — cumulative price change since 2006-03
   by category (horizontal bars), headline marked as a reference line.
3. `03_real_earnings.png` — nominal vs. real hourly earnings indexed
   2006-03 = 100 (two lines), with the real-wage change annotated.
4. `04_basket_cost.png` — cost of the fixed $100 (2006-03) basket over
   time, with the purchasing power of $1 on a second panel.

## 7. Success criteria checklist (from the roadmap — all must pass)

- [ ] Problem statement + audience written (README)
- [ ] Data provenance documented (data/README.md)
- [ ] 2+ labelled charts produced (4 produced)
- [ ] 3 findings + 1 actionable recommendation (outputs/insights_summary.md)
- [ ] README with setup instructions, sample outputs, limitations
- [ ] No credentials in the repo; no huge files committed (raw ~100 KB total)
- [ ] One metric manually validated and recorded (tester hand-checks one
      number from the processed CSVs, e.g. Oct 2026 YoY or the basket cost)
- [ ] Pipeline runs end-to-end from a clean checkout (`--live` re-downloads)
- [ ] Notebook runs top-to-bottom without errors (reads processed CSVs only)

## 8. Risks & mitigations

- FRED lag: latest month is 2026-10, not November → labelled everywhere
  (dashboard, README, insights); never claim November data.
- Series start dates differ (earnings 2006-03, education 1993, headline
  1947) → joint window fixed at 2006-03; long history is a separate file.
- Energy volatility dominates YoY ranges → core series shown alongside
  headline so the reader can separate signal from noise.
- Validate counts `data/` on disk → raw CSVs are small and committed, so
  the on-disk tree equals the pushed tree (no Day 18/19 cache-move needed).
- Notebook must not read the raw CSVs (CI runs it without network, but
  raws ARE committed, so a raw read would pass locally and in CI — still,
  notebook reads processed CSVs only, per house rule).

## 9. Build order

researcher (done) → planner (this file) → coder (venv, pipeline,
analysis, charts, app, notebook, tests, gates) → tester (independent
re-verification + smoke + hand-validation) → optimizer (gaps only,
re-run gates) → publisher (stage PNGs first, then text push).
