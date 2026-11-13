# Day 09 — Healthcare Resource Demand Forecast: Build Plan

**Status:** PLAN — planner sign-off complete (AGENTS.md, stage 2).
**Source of truth:** `research_brief.md` (2026-11-13) + this plan. **If brief
and plan disagree, the plan wins and the difference is noted in §11.** The
coder must reuse the brief + this plan. **No extra web searches.**
**Roadmap entry (verbatim):** "Forecast visits or bed demand from historical
or simulated operational trends and quantify forecast uncertainty. GitHub
deliverable: Capacity forecast and staffing scenario visual. Core skills:
SQL, Python, classification, forecasting, Power BI. Suggested data: CDC
Open Data; de-identified or synthetic hospital datasets."
Section context (Days 7–9, Healthcare & Medical Analytics).

| Item | Value |
|---|---|
| Fetch date | 2026-11-13 |
| Sources | CDC NSSP ED visits — COVID-19, Flu, RSV (`vutn-jzwm`, data.cdc.gov) + HHS hospital bed capacity by state timeseries (`g62h-syeh`, healthdata.gov) |
| Expected rows | **NSSP 25,116 rows** (verified probe count), 161 weeks, 52 geographies, 3 pathogens; **bed series 81,713 rows**, 2020-01-01 → 2024-04-27 |
| Target series (primary) | National weekly **Combined** respiratory ED share = COVID-19% + Influenza% + RSV% (`geography = "United States"`), 161 weeks, 2023-10-07 → 2026-10-31. Latest week (2026-10-31): **2.3%** combined (0.5% COVID-19 + 1.7% influenza + 0.1% RSV) |
| Target series (secondary) | National weekly mean inpatient bed utilisation (state-sum numerator / state-sum denominator), ~225 weeks, 2020-01-01 → 2024-04-27 |
| Forecast | **8-week ahead** point forecast + **80% and 95% prediction intervals** (residual bootstrap) |
| Methods | Exactly 2: seasonal naïve (baseline) + Holt-Winters (additive trend + additive seasonality, period 52). SARIMA is OUT unless Holt-Winters fails (§4.4) |
| Scope | Analytical exercise on public aggregate surveillance data. **Not a clinical or operational decision tool.** Bed series is historical (ends 2024-04-27); staffing uplifts are planning assumptions, not measured data (§4.6) |

## 1. Problem statement + audience

**Problem.** Respiratory illness drives a hospital's busiest weeks, and it
arrives in waves — but a capacity plan needs more than a single number. Day 9
asks three linked questions about the next 8 weeks: *how many respiratory ED
visits should a hospital system expect*, *how uncertain is that number*, and
*what staffing posture does each forecast level imply?* The second half
matters as much as the first: a point forecast with no interval hides the
range of staffing a system must actually be ready for, so the 8-week
forecast is published with 80% and 95% prediction intervals, backtested
honestly against a seasonal-naïve baseline, and translated into demand bands
(Low / Moderate / High / Surge) with a staffing scenario for each band.
A second, longer series — national inpatient bed utilisation, 2020–2024 —
exercises the same forecasting machinery on the capacity side and shows
how the method behaves over a full pandemic-era cycle. The analysis is
honest about its limits up front: the ED series is a *share* of all ED
visits, not a visit count (counts come only from a user-entered volume
assumption); the bed series ends 2024-04-27 and is a historical record,
not current capacity; and the staffing uplifts are labelled planning
assumptions, not measured effects.

**Audience / decision-maker.** A data analyst or hiring reviewer who wants
to see a forecast done properly on real public-health data: a baseline the
model must beat, rolling-origin backtesting with interval coverage (not
just point error), uncertainty quantified and reported, and a forecast
translated into an operational decision (staffing) without pretending the
translation is measured data. Every finding must carry its definition and
its denominator, and every assumption must be labelled as one.

## 2. Research questions (exactly 3)

1. **How many respiratory ED visits should a hospital system expect over
   the next 8 weeks, and with what uncertainty?** 8-week ahead point
   forecast of the national weekly Combined respiratory ED share, with
   80% and 95% prediction intervals from a residual bootstrap, from the
   method that wins the backtest; the per-pathogen split (COVID-19 /
   Influenza / RSV) and the top-5-state panel show where the demand is
   coming from.
2. **How good is the forecast, honestly?** Rolling-origin backtest over
   the last 12 weeks (3 origins, 4-week horizons): RMSE, MAE, MAPE and
   80%-interval coverage for Holt-Winters vs seasonal naïve, with the
   published forecast coming from the lower backtest RMSE — and the
   coverage reported against its ≈80% target, so a too-narrow interval
   is visible, not hidden.
3. **What staffing posture does each forecast level imply?** Each
   forecast week classified into a demand band (§4.5) with a historical
   band-occurrence table; a staffing-scenario table keyed to the band
   (baseline / +10% / +25% + elective-deferral trigger), all uplifts
   labelled **PLANNING ASSUMPTIONS**; plus the bed-utilisation series
   showing the capacity side — national weekly inpatient bed utilisation
   with its own forecast context — and the app's volume converter
   (forecast % → expected respiratory visits → expected admissions under
   a user-adjustable admission-rate assumption, default 15%, labelled
   "planning assumption").

## 3. Data — source, endpoints, fetch rules, provenance, licence

### 3.1 Source and endpoints (verified, from the brief — copy, do not re-search)

**Primary — CDC NSSP Emergency Department Visits (COVID-19, Flu, RSV):**

- **Source:** CDC National Syndromic Surveillance Program (NSSP), published
  on CDC Open Data (Socrata), dataset "2023 Respiratory Virus Response -
  NSSP Emergency Department Visits - COVID-19, Flu, RSV, Combined".
  Dataset ID `vutn-jzwm` · domain `data.cdc.gov` (Socrata API, no key).
- **Endpoints (verified 2026-11-13, all HTTP 200):**
  - Metadata: `GET https://data.cdc.gov/api/views/vutn-jzwm`
  - Rows: `GET https://data.cdc.gov/resource/vutn-jzwm.json?$limit=50000`
    (full table in one call; **Socrata default limit is 1,000 — the coder
    MUST pass `$limit=50000`, else the fetch is silently truncated** —
    the Day 6 truncation lesson).
  - Count check: `.../vutn-jzwm.json?$select=count(*)%20AS%20n` → **25,116**.
- **Coverage verified:** `week_end` 2023-10-07 → 2026-10-31 (161 weeks),
  52 geographies (50 states + DC + "United States"), 3 pathogens.
  Latest national week (2026-10-31): COVID-19 0.5%, Influenza 1.7%,
  RSV 0.1% (combined 2.3%).
- **Fields (only 4):** `week_end` (week-ending Saturday, ISO date),
  `pathogen` ∈ {`COVID-19`, `Influenza`, `RSV`}, `geography` (state name
  or `United States`), `percent_visits` (string, % of **all** ED visits
  in that geography/week attributed to that pathogen, one decimal).
- **Rate limits / polite use:** Socrata public endpoint, no key, no
  documented quota for unauthenticated reads. One full-table call
  (~25k rows, ~2 MB) + a handful of count probes is the whole fetch.
  No retry storm: on HTTP 429/5xx, wait 60 s, retry once, then stop and
  report. No app token needed.

**Secondary — HHS hospital bed capacity:**

- **Source:** HHS / healthdata.gov (Socrata), dataset "COVID-19 Reported
  Patient Impact and Hospital Capacity by State Timeseries (RAW)", ID
  `g62h-syeh`, no key.
- **Endpoint (verified 2026-11-13, HTTP 200):**
  `GET https://healthdata.gov/resource/g62h-syeh.json?$select=count(*)%20AS%20n,min(date)%20AS%20first,max(date)%20AS%20last`
  → **81,713 rows, 2020-01-01 → 2024-04-27**.
  Full fetch: `GET https://healthdata.gov/resource/g62h-syeh.json?$limit=50000`
  in two paged calls (`$offset=0` and `$offset=50000`) — same `$limit`
  rule as the NSSP call; never assume one call returns the whole table.
- **Coverage / caveat:** **Reporting ended 2024-04-27** (hospitals no
  longer required to report to HHS/NHSN after 2024-05-01). The series is
  a complete historical record, not current. State-level only — **no
  national aggregate row** (coder aggregates the 50 states + territories
  itself). Its end-date is disclosed in every chart / notebook / README
  that uses it.

### 3.2 Target construction (frozen — the tester tests these)

1. **There is NO `Combined` pathogen value** in the NSSP data despite the
   dataset title. "Combined" is computed by the analyst as the sum of
   the three pathogen percentages (same denominator — total ED visits —
   so summing is valid; co-infection double-counting is negligible and
   is how CDC's own dashboard builds "Combined"). Document this in
   `data/README.md`, the notebook and the README.
2. **`percent_visits` arrives as a JSON string; cast to float.**
3. **72 rows (0.29%) have NULL `percent_visits`** — treat as missing,
   never as 0. The pipeline reports the count and which
   geography/weeks, and records it in `data_source.json`. A week is
   Combined-missing if any of its three pathogen values is missing
   (report how many national weeks that affects; expected: 0–2).
4. **National series** = `geography = "United States"`: 483 rows
   (161 weeks × 3 pathogens) → 161 weekly Combined values.
   **State series** = 51 geographies × 161 weeks × 3 pathogens (minus
   NULLs); the top-5-state panel uses each state's latest-4-week mean
   Combined % (coder records the ranking rule).
5. **Bed series:** national weekly inpatient bed utilisation =
   (Σ `inpatient_beds_used` over states) / (Σ `inpatient_beds` over
   states) per week — state-sum numerator / state-sum denominator, NOT
   the mean of the per-state `inpatient_beds_utilization` ratios.
   Weekly aggregation by ISO week of `date`. ICU occupancy
   (`staffed_adult_icu_bed_occupancy`) is a companion series, computed
   the same way, shown in chart 04 only. Coverage columns
   (`*_coverage` = 0/1) flag whether a hospital reported that field that
   day — the pipeline filters to days with full coverage where the
   field exists and reports the share of days with full coverage in
   `data_source.json`.

### 3.3 Fetch rules

- One `GET` per dataset per build (plus the two paged bed calls);
  cache under `data/raw/` and re-use it (`--offline` / `--use-cache`
  per the Day 1 pattern). One retry after 60 s on HTTP 429/5xx, then
  stop and report — never hammer the host.
- Verify after fetch: NSSP row count = 25,116 and `week_end` range
  2023-10-07 → 2026-10-31; bed row count = 81,713 and date range
  2020-01-01 → 2024-04-27. Record the verified counts in
  `data_source.json`. If a count differs, report it — do not silently
  proceed.

### 3.4 Data-size exception and commit rule (READ CAREFULLY — Day 8 precedent)

- The raw NSSP JSON is **~2 MB** and the raw bed JSON is **~80k rows**
  — both over the portfolio rule (files < 1 MB each, < 5 MB per day
  folder). Therefore the **DATA-SIZE EXCEPTION** applies to this day
  only (same mechanism as Day 8's 19 MB CSV):
  - **`.gitignore` MUST exclude the raw data:** `data/raw/nssp_ed_visits.json`,
    `data/raw/bed_capacity.json`, `data/raw/*_synthetic.json`
    (synthetic fallback is always git-ignored). This is the one
    deliberate deviation from the "do NOT ignore `data/`" rule (Day 1
    lesson (d)) — the exception is forced by size and is recorded here,
    in `data/README.md`, and in the insights summary.
  - **The pipeline downloads the raw at build time** (`--live`),
    verifies the counts in §3.3, and caches it under `data/raw/` for
    re-use (`--use-cache`). `--offline` runs from the committed
    processed files only (no network, no raw needed) and regenerates
    charts + summaries from them.
  - **Committed provenance artefacts (small, the reproducibility
    record):** `data/raw/sample_rows.json` (≤ 1,000 rows NSSP +
    ≤ 1,000 rows bed, clearly labelled as a sample),
    and the compact processed files in §3.5. Expected `data/` total
    < 5 MB, no committed file > 1 MB.
- **`.gitignore` otherwise follows the scaffold default:**
  `__pycache__/`, `.venv/`, `venv/`, `.env`, `*.key`, `*.log`,
  `.streamlit/secrets.toml`, `.pytest_cache/`,
  `.ipynb_checkpoints/`, plus the three raw-data lines above. The
  tester diffs `.gitignore` against this list before sign-off.

### 3.5 Committed processed files (all < 1 MB; regenerable with one command)

| File | Contents |
|---|---|
| `data/processed/data_source.json` | Sources, URLs, dataset IDs, licence, fetch date, row counts (raw / national series weeks / bed weeks), NULL count (72) + geography/weeks affected, Combined construction note, bed end-date, split/backtest scheme + seed, method hyperparameters, backtest metric summary, band thresholds, staffing-assumption labels |
| `data/processed/national_combined.csv` | 161 rows: `week_end`, `covid_pct`, `flu_pct`, `rsv_pct`, `combined_pct` (national weekly series — the forecast target) |
| `data/processed/state_combined.csv` | State × week Combined % (51 geographies × 161 weeks, minus NULLs) — the geographic panel |
| `data/processed/bed_utilisation.csv` | ~225 rows: `week_end`, `bed_utilisation` (state-sum ratio), `icu_occupancy`, `beds_total`, `beds_used` |
| `data/processed/forecast.csv` | 8 rows: `week_end`, `forecast_pct`, `lo_80`, `hi_80`, `lo_95`, `hi_95`, `band` (published Holt-Winters forecast; method named in the file header comment / `data_source.json`) |
| `data/processed/backtest.csv` | One row per origin × method: `origin`, `method`, `rmse`, `mae`, `mape`, `coverage_80` |
| `data/processed/band_history.csv` | One row per national week: `week_end`, `combined_pct`, `band` — the historical band-occurrence table |

- The full raw JSONs are **not** committed (size). They are rebuilt by
  `python -m src.data_pipeline --live` from the live endpoints, and the
  notebook re-runs the forecast from them when present (§6, notebook
  rule). The committed processed CSVs are the offline-reproducible
  record: every number in the README, insights and dashboard must match
  them.
- **Offline rule (Day 5/6 lesson):** `--offline` must NOT clobber
  `data_source.json` fields recorded by a live run (`source: "live"`,
  counts, fetch date). It regenerates only the derived tables/charts
  from the committed CSVs; a test asserts this.

### 3.6 Fallback, licence, attribution

- **Synthetic fallback (only if a live fetch fails):** per brief §4 —
  161 weeks, base 1.5% + winter peak +5 pp (Gaussian bump centred
  week 52, σ = 6 weeks), weekly noise σ = 0.4 pp, seed 42. File
  `data/raw/nssp_ed_visits_synthetic.json` (git-ignored, NEVER
  overwrites real data); `data_source.json` records
  `synthetic: true, seed: 42`; README, dashboard, notebook, insights
  and every chart all carry a "SYNTHETIC — NOT REAL DATA" banner if it
  is used. Methods (§4) are unchanged. Not expected to be needed (all
  probes HTTP 200).
- **Licence: US federal public domain (both sources).** Attribution
  verbatim in README.md, data/README.md, the notebook and the
  dashboard footer:
  > CDC National Syndromic Surveillance Program (NSSP), Emergency
  > Department Visits — COVID-19, Flu, RSV, via CDC Open Data
  > (data.cdc.gov/resource/vutn-jzwm).
  > U.S. Department of Health and Human Services, COVID-19 Reported
  > Patient Impact and Hospital Capacity by State Timeseries, via
  > healthdata.gov (resource g62h-syeh).
  Companion guide: https://www.cdc.gov/ncird/surveillance/respiratory-illnesses/index.html#companion-guide

## 4. Analysis — definitions (from the brief, frozen; planner decisions in §11)

### 4.1 Forecast target and horizon

- **Primary target:** national weekly Combined respiratory ED share
  (`combined_pct`), 161 weeks, 2023-10-07 → 2026-10-31.
- **Horizon:** 8 weeks ahead from the last observed week (2026-10-31),
  i.e. forecast weeks ending 2026-11-07 → 2026-12-26.
- **Secondary target:** national weekly inpatient bed utilisation,
  ~225 weeks, 2020-01-01 → 2024-04-27. Forecasted with the same
  Holt-Winters machinery for the chart-04 context only (its forecast is
  shown as a historical-method illustration, NOT as a current capacity
  prediction — the series ends 2024-04-27 and the chart says so).

### 4.2 Methods (DECIDED — exactly two, no tuning grid)

1. **Seasonal naïve (baseline):** forecast for week *t* = the observed
   value 52 weeks earlier (same week last year). No parameters, no
   fitting. The forecast must beat this to be worth publishing.
2. **Holt-Winters exponential smoothing:** `statsmodels.tsa.holtwinters.ExponentialSmoothing`
   with **additive trend + additive seasonality, seasonal_periods=52**,
   fixed — no grid search, no parameter tuning. This is the candidate
   published forecast.
3. **SARIMA: OUT.** The brief offered SARIMA(1,1,1)(1,1,1,52) "if it
   converges cleanly"; the plan keeps it **out of scope** to avoid a
   tuning/convergence trap on a 161-week series with period-52
   seasonality. It is recorded as future work in the insights summary.
   (If Holt-Winters fails to fit — e.g. a convergence error — the coder
   reports it and the planner decides; the coder does not silently
   substitute SARIMA.)

### 4.3 Prediction intervals (roadmap: "quantify forecast uncertainty")

- **Residual bootstrap** for the Holt-Winters forecast: resample the
  in-sample one-step residuals (seed 42, 1,000 bootstrap paths),
  simulate 8-week paths, take the 10th/90th percentiles for the **80%
  interval** and the 2.5th/97.5th for the **95% interval**. Document the
  method, seed and path count in `data_source.json` and the notebook.
- **Seasonal naïve intervals:** same residual-bootstrap procedure
  applied to the naïve method's in-sample residuals, so the backtest
  interval coverage is comparable across methods.
- Intervals are reported as **percentage-point bands around the point
  forecast** and plotted as shaded bands (chart 01); the forecast CSV
  carries `lo_80` / `hi_80` / `lo_95` / `hi_95` per week.

### 4.4 Backtest (DECIDED — rolling origin, fixed)

- **Design:** last 12 weeks as **3 rolling origins** — train ends 12 /
  8 / 4 weeks before the end of the series, forecast **4 weeks** each.
  Both methods are backtested at every origin; no method is ever tuned
  on the backtest.
- **Metrics per origin × method:** RMSE, MAE, MAPE (report MAPE with
  the caveat that it inflates when the actual % is small — Combined %
  can sit near 1–2% in summer), and **80%-interval coverage** (share of
  the 4 actuals inside the 80% interval — target ≈ 80%).
- **Published forecast:** the method with the **lowest mean backtest
  RMSE** across the 3 origins is the published 8-week forecast; the
  other is shown for comparison in chart 02 and the dashboard. The
  choice and the numbers are recorded in `data_source.json` and the
  insights summary. (Expected: Holt-Winters wins; if seasonal naïve
  wins, publish naïve and say so — do not hide it.)

### 4.5 Demand-band classification (DECIDED — roadmap "classification" skill)

- **Bands (fixed by the plan, from the brief's provisional bands):**

  | Band | Combined % | Meaning |
  |---|---|---|
  | Low | < 2% | Baseline demand |
  | Moderate | 2–4% | Elevated, watch |
  | High | 4–6% | High demand, surge planning |
  | Surge | > 6% | Exceptional demand |

- **Reachability check (brief open item 1 — resolved here):** winter
  peaks in this series run roughly 5–9% Combined, so High is reachable
  in a normal winter and Surge is rare but reachable in a severe
  season. The coder **must** confirm against the actual observed max:
  compute the observed max Combined % and the historical count per band
  (in `band_history.csv`), and report in the notebook + insights whether
  Surge ever occurred historically. If Surge never occurred, the
  insights say so plainly ("Surge (>6%) has not occurred in the
  2023–2026 window; the band is retained as a planning threshold, not
  an observed level") — the band is not re-cut to force occurrences.
- **Each forecast week** is classified into a band from its point
  forecast; the band of each of the 8 forecast weeks is listed in
  `forecast.csv` and the dashboard.

### 4.6 Staffing scenario (DECIDED — planning assumptions, labelled)

- **Scenario table keyed to the forecast band (fixed uplifts):**

  | Band | Staffing posture |
  |---|---|
  | Low | Baseline roster |
  | Moderate | Baseline staffing (monitor) |
  | High | **+10% rostered shifts** |
  | Surge | **+25% rostered shifts + elective-deferral trigger** |

- **These uplifts are PLANNING ASSUMPTIONS, not measured data**
  (brief open item 5 — resolved here). The label "PLANNING ASSUMPTION"
  appears on the scenario table in the dashboard, in chart 04, in the
  notebook and in the insights summary. No source is cited for them
  because none exists; no precision is implied beyond the round numbers.
- **Volume converter (app only):** the dashboard takes a user-entered
  weekly ED volume (default 1,000 visits/week — labelled "planning
  assumption, not a measured number") and converts forecast % →
  expected respiratory visits → expected admissions under an explicit,
  user-adjustable **admission-rate assumption (default 15%, labelled
  "planning assumption")**. Round to whole visits; show the assumption
  on the same panel. No other invented inputs.

### 4.7 SQL check (roadmap core skill — small, honest)

The notebook answers one question twice — once in pandas, once in SQL —
on the committed `national_combined.csv` loaded into an in-memory
SQLite database (`sqlite3`, stdlib): the mean Combined % by season
(and the 4-week lagged Combined % as a lag feature), asserted equal to
the pandas result. A test asserts the SQL and pandas numbers agree.
This is the day's SQL element; no `.pbix` is built (see §11) and the
pipeline itself stays pandas.

## 5. File tree (exact — build only this)

```
day-09-healthcare-resource-demand-forecast/
├── README.md  requirements.txt  .gitignore  LICENSE  pyproject.toml
├── research_brief.md  plan.md  coder_handoff.md  test_report.md
├── optimizer_handoff.md  publisher_handoff.md
├── data/
│   ├── README.md
│   ├── raw/
│   │   └── sample_rows.json        (≤1,000 rows NSSP + ≤1,000 rows bed,
│   │                                provenance sample)
│   └── processed/
│       ├── data_source.json
│       ├── national_combined.csv   (161 rows)
│       ├── state_combined.csv
│       ├── bed_utilisation.csv     (~225 rows)
│       ├── forecast.csv            (8 rows)
│       ├── backtest.csv
│       └── band_history.csv
├── notebooks/analysis.ipynb
├── src/
│   ├── __init__.py
│   ├── data_pipeline.py
│   ├── forecast.py
│   ├── metrics.py
│   ├── make_charts.py
│   └── app.py
├── outputs/
│   ├── insights_summary.md
│   └── charts/
│       ├── 01_forecast.png
│       ├── 02_backtest.png
│       ├── 03_demand_bands.png
│       └── 04_bed_capacity.png
├── screenshots/
│   └── dashboard.png
└── tests/
    └── test_pipeline.py
```

Notes: the scaffold's `tests/test_smoke.py` is **DELETED** and replaced by
`tests/test_pipeline.py` (do not keep two test files). The scaffold's
placeholder `README.md`, `data/README.md`, `notebooks/analysis.ipynb`,
`outputs/insights_summary.md`, `requirements.txt` and `pyproject.toml`
are filled in by the coder — not new files. No `data/raw/*.json` full
raw files on disk at handoff (git-ignored, §3.4); the validator's
data-size check therefore passes on the real files. No extra modules, no
extra charts, no `.pbix`, no `weekly_briefing.md`, no model card (this
day's roadmap deliverable is the capacity forecast + staffing scenario
visual, not a model card).

## 6. Per-file responsibilities

| File | Responsibility |
|---|---|
| `src/data_pipeline.py` | Fetch NSSP (`$limit=50000`, §3.1) + bed series (2 paged calls, §3.1), 1 retry after 60 s on 429/5xx then stop; verify counts 25,116 / 81,713 and date ranges; cast `percent_visits` to float; count + locate the 72 NULLs; build Combined (sum of 3 pathogen %s); build the national series (161 weeks), state series, and bed utilisation (state-sum numerator/denominator, weekly, with coverage share); write `sample_rows.json`, the 4 processed series CSVs, `data_source.json`; modes `--live` / `--offline` / `--use-cache` / `--synthetic` (brief §4 generator, seed 42); `--keep-raw` debug flag (default off — raw is cached, not deleted, because re-downloading is the expensive part; the file is git-ignored either way) |
| `src/forecast.py` | `seasonal_naive_forecast(series, horizon)`; `holt_winters_forecast(series, horizon)` (additive trend + additive seasonality, period 52, fixed); `bootstrap_intervals(model_or_residuals, horizon, n_paths=1000, seed=42)` returning 80%/95% bands; `rolling_backtest(series, origins=(12, 8, 4), horizon=4)` returning per-origin × method metrics incl. coverage; `classify_band(value)` (§4.5 thresholds); `build_forecast(...)` writing `forecast.csv`, `backtest.csv`, `band_history.csv` |
| `src/metrics.py` | Pure functions, no I/O, no network — all tested: `rmse(y, p)`, `mae(y, p)`, `mape(y, p)`, `interval_coverage(y, lo, hi)`, `seasonal_naive_predict(train, horizon, period=52)`; thin wrappers where a library call is clearer |
| `src/make_charts.py` | Exactly 4 PNGs (§7), matplotlib `Agg`, offline from processed CSVs only, every chart footnoted with the source + "public aggregate surveillance data, not a clinical or operational decision tool" + bed end-date where relevant + synthetic label if applicable |
| `src/app.py` | Streamlit dashboard loading processed CSVs only (offline): forecast + intervals with band labels; backtest method comparison; demand-band history + state panel; bed utilisation + staffing-scenario table (uplifts labelled PLANNING ASSUMPTION); volume converter (user weekly ED volume, default 1,000, + admission-rate slider default 15%, both labelled planning assumptions); methods + limitations panel; `width="stretch"` (Day 2 lesson — no deprecated `use_container_width`); footer with public-domain attribution + bed-series end-date |
| `notebooks/analysis.ipynb` | Offline top-to-bottom, ≤ 16 cells, 0 error cells via nbconvert, `_find_root()` from the notebook file location (Day 1 lesson (e)): EDA on the committed series (seasonality, per-pathogen split, NULL audit); the 4 charts inline; Q1–Q3 answered with exact numbers; the SQL check (§4.7); the band-reachability check (§4.5 — observed max + historical band counts); **forecast section guarded by `RAW.exists()`** — if the raw JSONs are present it re-runs the forecast via `src.forecast` and asserts the metrics match the committed `backtest.csv` / `forecast.csv` within tolerance; if absent it loads the committed CSVs and prints a note that the forecast was skipped (still 0 errors). The notebook never downloads data itself. |
| `tests/test_pipeline.py` | ≥ 15 tests: Combined = sum of 3 pathogen %s on fixtures; 72 NULLs treated as missing (never 0); `$limit=50000` present in the fetch URL (no silent truncation); national series is 161 weeks with the latest week 2026-10-31 at 2.3% combined; bed utilisation = state-sum ratio (not mean of ratios) on fixtures; band thresholds incl. boundary values (2.0 → Moderate, 4.0 → High, 6.0 → Surge); seasonal-naïve = same week last year on fixtures; RMSE/MAE/MAPE/coverage hand-checks on fixtures; bootstrap intervals contain the point forecast and widen with horizon; backtest origins are (12, 8, 4) with horizon 4; offline run does not clobber `data_source.json` live fields; synthetic files never overwrite live files; no committed file > 1 MB, `data/` < 5 MB; SQL-vs-pandas agreement (§4.7) |
| `data/README.md` | Provenance: URLs, dataset IDs, public-domain licence, fetch date, row counts (25,116 / 81,713), NULL audit (72 + geography/weeks), Combined construction note, bed end-date disclosure, backtest scheme, band thresholds + reachability result, staffing-assumption labels, manual validation, versions |
| `outputs/insights_summary.md` | One finding per §2 question with exact numbers + one actionable recommendation + limitations (incl. Surge-occurrence finding and the bed-series end-date) |
| `README.md` | Problem, audience, setup, how to run (live/offline), sample outputs (forecast table + chart thumbnails), headline findings with numbers, validation, limitations, attribution |
| `requirements.txt` | Pinned `==` versions verified in the build venv (Python 3.12.3): Day 8 stack (pandas, numpy, matplotlib, plotly, streamlit, requests, pytest, jupyter, nbformat, scikit-learn, scipy) **plus statsmodels** (new runtime dep for this day — Holt-Winters). No other new runtime dependency without a plan change |
| `pyproject.toml` / `.gitignore` | Scaffold defaults (ruff/black line-length 88); `.gitignore` per §3.4 (raw-data lines are the only data exclusions) |

Key function signatures (coder follows these names):

```python
# src/data_pipeline.py
def fetch_nssp(limit: int = 50000) -> list[dict]
def fetch_bed_capacity(limit: int = 50000) -> list[dict]
def build_combined(df: pd.DataFrame) -> pd.DataFrame   # sums 3 pathogen %s
def build_national_series(df: pd.DataFrame) -> pd.DataFrame  # 161 weeks
def build_state_series(df: pd.DataFrame) -> pd.DataFrame
def build_bed_series(df: pd.DataFrame) -> pd.DataFrame  # state-sum ratio
def write_data_source(path: Path, record: dict) -> None

# src/forecast.py
def seasonal_naive_forecast(series: pd.Series, horizon: int = 8) -> np.ndarray
def holt_winters_forecast(series: pd.Series, horizon: int = 8) -> tuple[np.ndarray, object]
def bootstrap_intervals(residuals: np.ndarray, point: np.ndarray,
                        n_paths: int = 1000, seed: int = 42) -> dict
def rolling_backtest(series: pd.Series, origins: tuple = (12, 8, 4),
                     horizon: int = 4) -> pd.DataFrame
def classify_band(value: float) -> str   # Low / Moderate / High / Surge

# src/metrics.py
def rmse(y_true, y_pred) -> float
def mae(y_true, y_pred) -> float
def mape(y_true, y_pred) -> float
def interval_coverage(y_true, lo, hi) -> float
```

## 7. Charts (exactly 4, matplotlib, to scale and legible)

All charts: title, labelled axes with units (percentage points), source
footnote ("Source: CDC NSSP via CDC Open Data (vutn-jzwm) — public
aggregate surveillance data, not a clinical or operational decision
tool"; bed chart adds the HHS source + "series ends 2024-04-27"), no
truncated axes, legible at 100% zoom.

1. **01_forecast.png** — National weekly Combined % history (161 weeks)
   + 8-week Holt-Winters point forecast with shaded 80% and 95%
   prediction intervals; forecast weeks labelled with their demand band;
   the latest observed value (2.3%, week ending 2026-10-31) annotated.
   Answers Q1.
2. **02_backtest.png** — Two panels: (a) backtest RMSE by origin for
   Holt-Winters vs seasonal naïve (grouped bars, lower is better);
   (b) 80%-interval coverage by origin for both methods with the 80%
   target line. The winning method is named in the title. Answers Q2.
3. **03_demand_bands.png** — Two panels: (a) national Combined %
   history coloured by demand band with the 2 / 4 / 6% threshold lines;
   (b) top-5-state panel — latest-4-week mean Combined % by state,
   horizontal bars with values. Answers Q1's geographic half and Q3's
   band history.
4. **04_bed_capacity.png** — Two panels: (a) national weekly inpatient
   bed utilisation 2020–2024 (state-sum ratio) with the series end-date
   2024-04-27 annotated; (b) staffing-scenario table as a chart panel —
   band → posture with the +10% / +25% uplifts, footnoted
   "PLANNING ASSUMPTIONS — not measured data". Answers Q3's capacity
   half.

The Streamlit dashboard embeds the 4 PNGs (as Days 6–8 do) so the README
thumbnails and the app agree.

## 8. Success checklist (roadmap minimum success criteria — all must pass)

- [ ] Problem statement + audience written (§1, in README and this plan)
- [ ] Data source documented: provider, URLs, dataset IDs, licence
      (public domain, verbatim attribution), fetch date (2026-11-13),
      row counts (NSSP 25,116 / bed 81,713), NULL audit (72 rows +
      geography/weeks), Combined construction note, bed end-date
      (2024-04-27) — in `data/README.md` and
      `data/processed/data_source.json`
- [ ] Repeatable prep steps documented (fetch → build series → backtest →
      forecast → charts, with `--offline` mode) + metric definitions
      (§4.2–4.4) written down
- [ ] **Capacity forecast and staffing scenario visual delivered**
      (roadmap deliverable): 8-week forecast with 80%/95% intervals +
      demand bands + staffing-scenario table, in the dashboard and
      chart 04
- [ ] **Forecast uncertainty quantified**: 80% and 95% prediction
      intervals from a residual bootstrap (seed 42, 1,000 paths) on the
      published forecast, plotted and tabulated
- [ ] **Backtest reported** for both methods at 3 rolling origins
      (12 / 8 / 4 weeks, 4-week horizons): RMSE, MAE, MAPE,
      80%-interval coverage vs the ≈80% target; published forecast is
      the lower-mean-RMSE method
- [ ] **Demand bands applied** with the §4.5 thresholds; historical
      band-occurrence table + observed-max reachability check recorded;
      each forecast week banded in `forecast.csv`
- [ ] **Staffing uplifts labelled PLANNING ASSUMPTIONS** (dashboard,
      chart 04, notebook, insights) — never presented as measured data
- [ ] Exactly **4 charts** (§7), drawn to scale and legible, plus a
      functional dashboard: the Streamlit dashboard runs and renders
      (smoke gate, §9)
- [ ] Interpretation written (`outputs/insights_summary.md`, one finding
      per §2 question with exact numbers) + one actionable recommendation
- [ ] README with setup instructions, sample outputs (forecast table +
      chart thumbnails), validation results, and limitations
- [ ] No credentials / private records in the repo; **data-size exception
      honoured** (no file > 1 MB, `data/` < 5 MB; raw JSONs git-ignored
      per §3.4 and absent at handoff; `.gitignore` matches §5/§6)
- [ ] **One metric manually validated by hand** and recorded in
      `data/README.md` (the tester recomputes one metric — e.g. the
      latest-week Combined 2.3% from the three pathogen values, or one
      backtest RMSE — from the committed CSVs, matching to the last digit)
- [ ] Pipeline runs end-to-end from a clean checkout (`pip install -r
      requirements.txt`, `python -m src.data_pipeline --live`,
      `python -m src.make_charts`, `pytest tests/ -q`) — **pytest passing
      both from the repo root and from inside the day folder**
- [ ] **Notebook runs top-to-bottom without errors** (offline, via
      nbconvert, with `_find_root()` and the guarded forecast section, §6)
- [ ] Pinned dependencies in `requirements.txt` (incl. statsmodels);
      `black --check` + `ruff check` clean
- [ ] Streamlit smoke gate passed: fresh port 8502+, HTTP 200 on `/` and
      on `/_stcore/health`, **real `screenshots/dashboard.png`** captured,
      server killed and port verified free
- [ ] Charts to scale and legible; frozen-tree check passed immediately
      before push (every file the READMEs reference exists on disk —
      charts, screenshot, CSVs)

## 9. Coder handoff checklist (reference — coder must satisfy all of these before the tester starts)

- [ ] venv exists with pinned deps installed; `black --check` + `ruff check` pass; `pytest` passes (≥ 15 tests)
- [ ] `.gitignore` matches §3.4/§5 (raw JSONs + synthetic excluded; nothing else in `data/` excluded)
- [ ] `screenshots/dashboard.png` is a real capture of the running app on a fresh port (8502+)
- [ ] `data/` total < 5 MB, no file > 1 MB; no raw full JSONs on disk at handoff (git-ignored); `data_source.json` records live counts, NULL audit, backtest results, band thresholds
- [ ] Counts verified against §3.3 (NSSP 25,116 / bed 81,713); latest national week 2.3% combined confirmed; observed max + band reachability reported
- [ ] `tests/test_smoke.py` deleted — only `tests/test_pipeline.py` exists
- [ ] Build only what §5 lists; no extra web searches

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Socrata default `$limit=1000` silently truncates the fetch | `$limit=50000` mandated (§3.1); count check (25,116) asserted after fetch; test asserts the limit is in the URL (Day 6 lesson) |
| "Combined" pathogen value does not exist in the data | Sum the three pathogen %s (§3.2 rule 1); document the construction everywhere |
| 72 NULL `percent_visits` values misread as 0 | Treat as missing, never 0; audit + record geography/weeks (§3.2 rule 3) |
| Bed series mistaken for current capacity | End-date 2024-04-27 disclosed in every chart/notebook/README that uses it (§3.1, §4.1) |
| Holt-Winters fails to converge / fit | Report it; SARIMA is NOT a silent substitute (§4.2 rule 3) — planner decides |
| MAPE misread when Combined % is near 1–2% in summer | Report RMSE/MAE alongside MAPE; note the caveat in the notebook (§4.4) |
| Staffing uplifts mistaken for measured effects | Labelled PLANNING ASSUMPTION on every surface (§4.6) |
| Surge band never occurred historically | Report it plainly; do not re-cut the bands (§4.5) |
| Raw JSONs too big to commit | §3.4 exception: git-ignored, downloaded at build, small committed provenance artefacts |
| Notebook can't forecast offline (no raw data) | Guarded forecast section (§6); notebook fully executable from committed processed CSVs |
| Push-manifest / remote-head loss (Day 7 lesson) | Publisher keeps the push manifest under `~/workspace/` (never `/tmp`); re-check the remote head after any uncertain write |
| Base64 passed to `create_or_update_file` (Day 8 lesson) | Never pass base64 content to `create_or_update_file` — it stores the base64 text as the file. Use push-files from disk for file updates, or pass raw text |

## 11. Differences from the brief (plan wins)

- **Demand-band thresholds (§4.5):** the brief (§2, §6 item 1) left the
  thresholds provisional pending the observed distribution; the plan
  **fixes** <2 Low, 2–4 Moderate, 4–6 High, >6 Surge, with the
  reachability rationale (winter peaks ~5–9%) and the mandatory
  observed-max confirmation + plain reporting if Surge never occurred.
- **Backtest design (§4.4):** the brief (§2) sketched "last 12 weeks as
  3 rolling origins, 4-week horizons"; the plan **fixes** origins at
  train-ends 12 / 8 / 4 weeks before the end and the metric set (RMSE,
  MAE, MAPE, 80% coverage), and fixes the publication rule (lowest
  mean backtest RMSE wins).
- **Method set (§4.2):** the brief offered SARIMA(1,1,1)(1,1,1,52) "if
  it converges cleanly" as a third option; the plan keeps SARIMA
  **OUT** unless Holt-Winters fails, to avoid a tuning trap — exactly
  two methods ship.
- **Interval method (§4.3):** the brief left "residual bootstrap
  (Holt-Winters) or analytic (SARIMA)" open; the plan **fixes**
  residual bootstrap (seed 42, 1,000 paths) for both methods.
- **Bed series scope (§3.2 rule 5, §4.1):** the brief (§6 item 3) left
  open national-only vs one state as well; the plan fixes **national
  weekly inpatient-bed utilisation only** (state-sum
  numerator/denominator), one chart (04), no second dashboard.
- **Data-size exception (§3.4):** the brief (§6 item 4) asked the
  planner to decide; the plan **fixes** the exception — raw full JSONs
  git-ignored and re-downloaded at build (Day 8 precedent), committed
  provenance = `sample_rows.json` (≤1,000 rows per dataset) +
  processed CSVs + `data_source.json`, `data/` < 5 MB, no file > 1 MB.
- **Staffing-scenario numbers (§4.6):** the brief (§6 item 5) asked the
  planner to label them; the plan **fixes** the uplifts (High +10%,
  Surge +25% + elective-deferral trigger) and mandates the
  **PLANNING ASSUMPTION** label on every surface, plus the volume
  converter defaults (1,000 visits/week, 15% admission rate).
- **Power BI:** the roadmap's section-level core skills list Power BI,
  but the Day 9 deliverable is the "capacity forecast and staffing
  scenario visual". No `.pbix` is built (same decision as Day 8 — a
  `.pbix` cannot be built or verified in this environment); the
  Streamlit dashboard + 4 static charts are the deliverables. The SQL
  skill is covered by the §4.7 check.
- **Notebook forecast (§6):** the brief did not specify notebook
  mechanics; the plan adds the guarded forecast section (re-runs the
  forecast when the raw JSONs are present, otherwise loads committed
  CSVs — 0 errors either way).
- **Bed fetch paging (§3.1):** the brief verified the bed count via a
  `$select` probe only; the plan fixes the full fetch as **two paged
  calls** (`$offset=0` / `$offset=50000`, `$limit=50000` each).

## 12. Build order

1. `src/data_pipeline.py` — fetch (NSSP + bed, §3.1) → verify counts →
   Combined construction + NULL audit → national / state / bed series →
   `sample_rows.json` + processed CSVs + `data_source.json` (live run;
   cache raw).
2. `src/metrics.py` + `src/forecast.py` — pure metrics, seasonal naïve +
   Holt-Winters, residual-bootstrap intervals, rolling backtest (3
   origins × 4 weeks), band classification → `forecast.csv`,
   `backtest.csv`, `band_history.csv`.
3. `src/make_charts.py` — 4 charts from the processed CSVs.
4. `notebooks/analysis.ipynb` — EDA + Q1–Q3 + SQL check + band
   reachability check + guarded forecast section; run via nbconvert,
   0 errors.
5. `src/app.py` — Streamlit dashboard from processed CSVs only; smoke
   test on a fresh port (8502+) + real `screenshots/dashboard.png`.
6. `tests/test_pipeline.py` — ≥ 15 tests (§6); delete
   `tests/test_smoke.py`; `pytest`, `black`, `ruff`; coder handoff
   checklist (§9).
7. Docs — `README.md`, `data/README.md`, `outputs/insights_summary.md`;
   every number checked against the committed processed CSVs.
