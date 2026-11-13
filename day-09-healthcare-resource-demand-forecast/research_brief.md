# Day 09 — Healthcare Resource Demand Forecast: Research Brief

**Status:** RESEARCH COMPLETE — verified live 2026-11-13 (one lean probe pass).
**Business question:** How many respiratory-illness ED visits should a hospital
system expect over the next 8 weeks, with what uncertainty, and what staffing
posture does each forecast band imply?

## 1. Data sources — verified live

### 1a. PRIMARY — CDC NSSP Emergency Department Visits (COVID-19, Flu, RSV)

- **Source:** CDC National Syndromic Surveillance Program (NSSP), published
  on CDC Open Data (Socrata), dataset
  **"2023 Respiratory Virus Response - NSSP Emergency Department Visits -
  COVID-19, Flu, RSV, Combined"**.
- **Dataset ID:** `vutn-jzwm` · Domain: `data.cdc.gov` (Socrata API, no key).
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
  or `United States`), `percent_visits` (string, % of **all** ED visits in
  that geography/week attributed to that pathogen, one decimal).
- **Verified quirks (coder must handle):**
  - **There is NO `Combined` pathogen value** in the data despite the
    dataset title. "Combined" is computed by the analyst as the sum of
    the three pathogen percentages (same denominator — total ED visits —
    so summing is valid; co-infection double-counting is negligible and
    is how CDC's own dashboard builds "Combined"). Document this.
  - **72 rows (0.29%) have NULL `percent_visits`** — treat as missing,
    never as 0. Report the count and which geography/weeks.
  - `percent_visits` arrives as a JSON string; cast to float.
  - National series = `geography = "United States"`: 483 rows
    (161 weeks × 3 pathogens). State series = 51 geographies × 161 weeks
    × 3 pathogens (minus NULLs).
- **Rate limits / polite use:** Socrata public endpoint, no key, no
  documented quota for unauthenticated reads. One full-table call
  (~25k rows, ~2 MB) + a handful of count probes is the whole fetch.
  No retry storm: on HTTP 429/5xx, wait 60 s, retry once, then stop and
  report. No app token needed.
- **Licence / attribution:** US federal government work — public domain.
  Cite: "CDC National Syndromic Surveillance Program (NSSP), Emergency
  Department Visits — COVID-19, Flu, RSV, via CDC Open Data
  (data.cdc.gov/resource/vutn-jzwm)". Companion guide:
  https://www.cdc.gov/ncird/surveillance/respiratory-illnesses/index.html#companion-guide

### 1b. SECONDARY — HHS hospital bed capacity (bed-demand series)

- **Source:** HHS / healthdata.gov (Socrata), dataset
  **"COVID-19 Reported Patient Impact and Hospital Capacity by State
  Timeseries (RAW)"**, ID `g62h-syeh`, no key.
- **Endpoints (verified 2026-11-13, HTTP 200):**
  `GET https://healthdata.gov/resource/g62h-syeh.json?$select=count(*)%20AS%20n,min(date)%20AS%20first,max(date)%20AS%20last`
  → **81,713 rows, 2020-01-01 → 2024-04-27**.
- **Coverage / caveat:** **Reporting ended 2024-04-27** (hospitals no
  longer required to report to HHS/NHSN after 2024-05-01). The series is
  a complete historical record, not current. State-level only — **no
  national aggregate row** (coder aggregates the 50 states + territories
  itself, or models one state + the national sum of states).
- **Fields to use:** `date`, `state`, `inpatient_beds`,
  `inpatient_beds_used`, `inpatient_beds_utilization` (ratio),
  `total_staffed_adult_icu_beds`, `staffed_adult_icu_bed_occupancy`,
  `previous_day_admission_adult_covid_confirmed`.
  Coverage columns (`*_coverage` = 0/1) flag whether a hospital
  reported that field that day — coder must weight/filter on coverage
  and report the share of days with full coverage.
- **Use:** the bed-demand forecast target (national weekly mean inpatient
  bed utilisation, 2020–2024) — a second, longer forecast series that
  exercises the same forecasting machinery on a different horizon and
  shows the capacity side of the roadmap entry. Its end-date is disclosed
  in every chart/notebook/README that uses it.
- **Licence / attribution:** HHS public data — public domain. Cite:
  "U.S. Department of Health and Human Services, COVID-19 Reported
  Patient Impact and Hospital Capacity by State Timeseries, via
  healthdata.gov (resource g62h-syeh)".

### 1c. Ruled out

- **CDC PLACES (Day 7 source):** prevalence estimates, no time series —
  cannot forecast.
- **NHAMCS public-use data (tqpr-vcrm):** annual survey microdata,
  1992–2022, no weekly operational series; ED-visit estimates dataset
  (`ycxr-emue`, 2016–2022) is annual — too coarse for an 8-week forecast.
- **NSSP trajectories dataset (`rdmq-nq56`):** sub-state trajectories,
  overlaps 1a; not needed.

## 2. Metrics to compute

- **Target series (primary):** national weekly Combined respiratory ED
  share = COVID-19% + Influenza% + RSV% for `geography = "United States"`,
  161 weeks, 2023-10-07 → 2026-10-31. Also per-pathogen series and the
  top-5-state series for the geographic panel.
- **Target series (secondary):** national weekly mean inpatient bed
  utilisation (state-sum numerator / state-sum denominator), weekly
  2020-01-01 → 2024-04-27 (~225 weeks); ICU occupancy as a companion series.
- **Forecast:** 8-week ahead point forecast + **80% and 95% prediction
  intervals** (quantify uncertainty — the roadmap's explicit requirement).
  Methods: (a) seasonal naïve (same week last year) as the baseline,
  (b) Holt-Winters exponential smoothing (additive trend + additive
  weekly seasonality, period 52), (c) SARIMA(1,1,1)(1,1,1,52) if it
  converges cleanly — planner/coder pick at most two, no tuning grid.
  Intervals from residual bootstrap (Holt-Winters) or analytic
  (SARIMA); document which.
- **Backtest (rolling origin):** last 12 weeks as 3 rolling origins
  (train ends 12 / 8 / 4 weeks before the end, forecast 4 weeks each);
  report RMSE, MAE, MAPE and **interval coverage** (share of actuals
  inside the 80% interval — target ≈ 80%) for each method; the method
  with the lowest backtest RMSE is the published forecast, the other is
  shown for comparison. Never tune on the backtest.
- **Demand-band classification (roadmap "classification" skill):**
  classify each forecast week into a demand band from the Combined %
  (thresholds set by the planner from the observed training
  distribution and documented — provisional: <2% Low, 2–4% Moderate,
  4–6% High, >6% Surge; coder must check the observed max first and
  the planner must confirm the bands are reachable, not decorative).
  Report the historical confusion-style table: how often each band
  occurred, and the band of each forecast week.
- **Staffing scenario (capacity visual):** a scenario table keyed to the
  forecast band — e.g. Moderate = baseline staffing, High = +10%
  rostered shifts, Surge = +25% + elective-deferral trigger. The app
  also takes a user-entered weekly ED volume (default = labelled
  planning assumption, not a measured number) and converts forecast %
  → expected respiratory visits → expected admissions under an
  explicit, user-adjustable admission-rate assumption (default 15%,
  labelled "planning assumption"). No invented precision: round to whole
  visits, show the assumption on the same panel.
- **SQL (roadmap skill):** an in-memory SQLite check in the notebook —
  weekly aggregation + 4-week lag features via SQL, asserted equal to
  the pandas result (as Day 8 did). No external database.
- **Power BI (roadmap skill):** no `.pbix` is produced (same decision as
  Day 8 — a `.pbix` cannot be built or verified in this environment);
  the capacity/staffing visual is delivered as the Streamlit dashboard
  + the 4 static charts. Recorded here so the planner does not
  re-litigate it.

## 3. Licence / attribution

Both sources are US federal public-domain data. Attribution lines are in
§1a/§1b and must appear in `data/README.md`, the notebook, and the day
README. No licence file changes needed (portfolio LICENSE already covers
the code).

## 4. Synthetic-fallback note

Only if the live fetch fails: build a clearly-labelled synthetic weekly
series from documented parameters — 161 weeks, base 1.5% + winter peak
+5 pp (Gaussian bump centred week 52, σ = 6 weeks), weekly noise σ = 0.4 pp,
seed 42 — stored as `data/raw/*_synthetic.json`, `data_source.json`
`synthetic: true`, and labelled "SYNTHETIC — NOT REAL DATA" in every
chart, the notebook, and the README. **The live fetch works (verified
above), so the fallback is contingency only; the coder must not use it
unless the live call fails.**

## 5. Verification status

- [x] Endpoints confirmed against the official sources (2026-11-13):
  `vutn-jzwm` count 25,116, range 2023-10-07 → 2026-10-31; `g62h-syeh`
  count 81,713, range 2020-01-01 → 2024-04-27. All HTTP 200, no key.
- [x] Conflicts recorded with resolution:
  - Dataset title promises a "Combined" pathogen — **not present** as a
    value; resolved by summing the three pathogen percentages (same
    denominator), documented in §1a.
  - Bed-capacity series **ends 2024-04-27** — resolved by using it as a
    historical bed-demand series with the end-date disclosed everywhere.
  - Socrata **default `$limit` is 1,000** — resolved by mandating
    `$limit=50000` (Day 6 truncation lesson).
- [ ] No live fetch performed by the researcher (that is the coder's job);
  counts above are from Socrata `$select=count(*)` probes only.

## 6. Open items for the planner

1. Confirm demand-band thresholds against the observed Combined %
   distribution (provisional bands in §2 — check the observed max; a
   Surge band nobody ever reaches is a defect).
2. Decide the exact backtest design (origins/horizons) and which two
   forecast methods ship.
3. Decide the secondary (bed) series scope: national weekly utilisation
   only, or one state as well. Keep it to one extra chart, not a second
   dashboard.
4. Data-size rule: raw NSSP JSON ~2 MB and raw bed JSON (~80k rows) may
   exceed the 1 MB/file guideline — planner must decide the commit
   exception (sample + processed CSVs committed; raw full JSONs
   git-ignored and re-downloaded at build time, as Day 8 did for the
   19 MB CSV) and record it in plan §3.4.
5. Staffing-scenario numbers (shift uplift per band) are planning
   assumptions — planner must label them as such, not as measured data.
