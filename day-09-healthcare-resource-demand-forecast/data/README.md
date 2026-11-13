# Data provenance — Day 09 Healthcare Resource Demand Forecast

## Source

- **Primary — CDC NSSP Emergency Department Visits (COVID-19, Flu, RSV):**
  CDC National Syndromic Surveillance Program, published on CDC Open Data
  (Socrata), dataset "2023 Respiratory Virus Response - NSSP Emergency
  Department Visits - COVID-19, Flu, RSV, Combined", dataset ID `vutn-jzwm`.
  - Rows: `GET https://data.cdc.gov/resource/vutn-jzwm.json?$limit=50000`
    (full table in one call; **Socrata's default limit is 1,000 — the
    `$limit=50000` parameter is mandatory, else the fetch is silently
    truncated**).
  - Metadata: `GET https://data.cdc.gov/api/views/vutn-jzwm`.
  - Count check: `.../vutn-jzwm.json?$select=count(*)%20AS%20n` → 25,116.
  - No key, no documented quota for unauthenticated reads. One retry after
    60 s on HTTP 429/5xx, then stop.
- **Secondary — HHS hospital bed capacity:** "COVID-19 Reported Patient
  Impact and Hospital Capacity by State Timeseries (RAW)", ID `g62h-syeh`,
  healthdata.gov (Socrata, no key). Full fetch in two paged calls
  (`$limit=50000`, `$offset=0` and `$offset=50000`).
- **Licence:** both sources are US federal public-domain data.
  Attribution (verbatim, also in the README, notebook and dashboard footer):
  > CDC National Syndromic Surveillance Program (NSSP), Emergency
  > Department Visits — COVID-19, Flu, RSV, via CDC Open Data
  > (data.cdc.gov/resource/vutn-jzwm).
  > U.S. Department of Health and Human Services, COVID-19 Reported
  > Patient Impact and Hospital Capacity by State Timeseries, via
  > healthdata.gov (resource g62h-syeh).
  Companion guide: https://www.cdc.gov/ncird/surveillance/respiratory-illnesses/index.html#companion-guide

## Fetch outcome

- Fetch date: **2026-11-13** (live, `source: "live"`, `synthetic: false`).
- **NSSP: 25,116 rows** (verified against the expected count), `week_end`
  2023-10-07 → 2026-10-31, 52 geographies, 3 pathogens.
- **Bed series: 81,713 rows** (verified), `date` 2020-01-01 → 2024-04-27.
  **Reporting ended 2024-04-27** (hospitals no longer required to report
  after 2024-05-01) — the series is a complete historical record, not
  current capacity. The end-date is disclosed in every chart, the notebook,
  the README and the dashboard that uses it.

## Row counts and coverage

- National series (`geography = "United States"`): 483 rows
  (161 weeks × 3 pathogens) → **161 weekly Combined values**.
  Latest week (2026-10-31): COVID-19 0.5%, Influenza 1.7%, RSV 0.1%
  (Combined 2.3%).
- State series: 51 geographies × 161 weeks, **8,187 rows** (24 state-weeks
  Combined-missing because of NULLs — see below).
- Bed series: **226 weekly rows** (2020-01-04 → 2024-04-27).
- **Combined construction:** there is NO `Combined` pathogen value in the
  NSSP data despite the dataset title. Combined is computed as the sum of
  the three pathogen percentages (same denominator — total ED visits — so
  summing is valid; co-infection double-counting is negligible and is how
  CDC's own dashboard builds "Combined"). `percent_visits` arrives as a
  JSON string and is cast to float; values are stored to 1 decimal.
- **NULL audit (72 rows, 0.29%):** `percent_visits` is NULL — in the JSON
  the key is simply absent. Treated as missing, **never as 0**. All 72
  rows are recent reporting gaps: **Iowa** 54 rows (nothing reported since
  2026-07-04, 18 weeks × 3 pathogens), **Delaware** 9 rows and **Georgia**
  9 rows (nothing since 2026-10-17, 3 weeks × 3 pathogens). **National
  weeks affected: 0.** A week is Combined-missing if any of its three
  pathogen values is missing.
- **Bed utilisation method:** national weekly inpatient bed utilisation =
  (Σ `inpatient_beds_used` over states) / (Σ `inpatient_beds` over states)
  per ISO week ending Saturday — state-sum ratio, **not** the mean of the
  per-state ratios. ICU occupancy (`staffed_adult_icu_bed_occupancy` /
  `total_staffed_adult_icu_beds`) is computed the same way. Only state-days
  with full coverage enter the sums: 86.36% of state-days qualify, 11,145
  dropped.
- **Coverage definition (corrected from the brief):** the brief assumed the
  `*_coverage` columns are 0/1 flags. They are actually **counts of
  hospitals reporting that field** (e.g. 111). A state-day counts as fully
  covered when `inpatient_beds_coverage == inpatient_beds_used_coverage`
  (both > 0): the same hospitals reported the numerator and the
  denominator.
- **Thin early bed reporting:** 45 of the 226 bed weeks have <50 states
  reporting, all in 2020 (as few as 3 states; one week totals 1,205 beds).
  The 2020 segment's 48.9–59.8% readings reflect those few states, not the
  nation. Bed utilisation averaged 72.5% overall (max 78.9%, week ending
  2022-12-10); the final week (2024-04-27) is 74.95% with ICU occupancy
  71.65%. One week (2020-07-11) has ICU occupancy exactly 0.0 and 23 weeks
  have no ICU data at all (NaN).

## Backtest, bands and staffing assumptions

- **Backtest:** 3 rolling origins (train ends 12 / 8 / 4 weeks before the
  end), 4-week horizons, both methods. Holt-Winters mean RMSE **0.4693 pp**
  vs seasonal naïve **0.8244 pp** (MAE 0.4177 vs 0.7833; MAPE 42.19% vs
  80.63%). Mean 80%-interval coverage 75.0% (Holt-Winters) vs 91.67%
  (naïve) against the ≈80% target. Published forecast: Holt-Winters.
- **Prediction intervals:** residual bootstrap, seed 42, 1,000 paths.
- **Demand bands:** Low <2%, Moderate 2–4%, High 4–6%, Surge >6%.
  Historical occurrence (161 weeks): Low 89, Moderate 35, High 19,
  Surge 18. Observed max Combined: **10.4%** (2023-12-30) — Surge is a
  real historical level, not a decorative threshold.
- **Staffing uplifts are PLANNING ASSUMPTIONS, not measured data:** High
  +10% rostered shifts; Surge +25% rostered shifts + elective-deferral
  trigger. No source is cited for them because none exists.
- **Volume converter defaults** (dashboard only): 1,000 ED visits/week,
  15% admission rate — planning assumptions, not measured numbers.
- **Fitting note:** statsmodels' Holt-Winters optimiser emits a
  ConvergenceWarning on some windows (it stops on its optimisation
  tolerance, not on a failed fit). The fitted parameters are finite and
  the forecasts are sane (backtest RMSE beats seasonal naïve by a wide
  margin), so the warning is suppressed in `src/forecast.py`.

## Commit rule for data files

- **Data-size exception (plan §3.4, Day 8 precedent):** the raw NSSP JSON
  is ~2.9 MB and the raw bed JSON is ~585 MB on disk, both over the
  portfolio rule (files < 1 MB each, < 5 MB per day folder). Therefore the
  raw full JSONs are **git-ignored** (`data/raw/nssp_ed_visits.json`,
  `data/raw/bed_capacity.json`, `data/raw/*_synthetic.json`) and
  re-downloaded at build time by `python -m src.data_pipeline --live`.
  This is the one deliberate deviation from the "do NOT ignore `data/`"
  rule (Day 1 lesson (d)).
- **Committed provenance (small):** `data/raw/sample_rows.json` (1,000 NSSP
  rows + 100 bed rows, 798,920 bytes — bed rows are wide, ~129 fields, so
  the bed sample is capped at 100 rows to stay under 1 MB) and the compact
  processed CSVs. Committed `data/` total is 1,160,652 bytes (~1.16 MB); no committed file
  exceeds 1 MB.
- **Offline rule (Day 5/6 lesson):** `python -m src.data_pipeline --offline`
  regenerates only the derived forecast tables from the committed CSVs and
  never touches `data_source.json` (verified byte-identical, see the test
  suite). `--use-cache` reuses the cached raw JSONs without re-downloading.
- **Synthetic fallback** (brief §4, contingency only — not used; live fetch
  verified): 161 weeks, base 1.5% + winter peak +5 pp (Gaussian bump
  centred week 52, σ = 6 weeks), noise σ = 0.4 pp, seed 42, stored as
  `data/raw/nssp_ed_visits_synthetic.json`, never overwriting live files.

## Manual validation (one metric, by hand)

Two metrics were recomputed independently from the raw JSON files on disk
(plain `json.load`, not via the pipeline), both matching to the last digit:

1. **Latest-week Combined (2026-10-31):** the raw rows read COVID-19
   `0.5`, Influenza `1.7`, RSV `0.1`. Hand sum: 0.5 + 1.7 + 0.1 = **2.3%**;
   committed `national_combined.csv` value: 2.3%. **Diff: 0.0.**
2. **Final bed week (ending 2024-04-27):** the raw rows for 2024-04-21 →
   2024-04-27 with full coverage sum to 3,604,488 beds used /
   4,808,901 beds = **0.7495**; committed `bed_utilisation.csv` value:
   0.7495. **Diff: 0.0.** ICU occupancy the same way: 0.7165 vs committed
   0.7165. **Diff: 0.0.**

(The first attempt at check 2 used only the single day 2024-04-27 and gave
0.7333 — wrong window: a week ending Saturday covers 7 days. The corrected
7-day window matches exactly; the mistake is recorded here so the tester
does not repeat it.)

## Versions used for this build

Python 3.12.3. Pinned in `requirements.txt`: pandas 3.1.1, numpy 2.5.4,
matplotlib 3.11.2, plotly 7.1.0, streamlit 1.66.1, requests 2.34.2,
pytest 9.2.0, jupyter 1.1.1, nbformat 5.11.1, scikit-learn 1.9.1,
scipy 1.18.1, statsmodels 0.15.0. Dev: ruff 0.17.4, black 26.10.1.
