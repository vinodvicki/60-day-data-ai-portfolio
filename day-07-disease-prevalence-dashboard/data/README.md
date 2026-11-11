# Data provenance — Day 07 Disease Prevalence Dashboard

## Source

- **Provider:** CDC PLACES: Local Data for Better Health, County Data —
  **2025 release** (2023 estimates, Socrata dataset `swc5-untb`) and
  **2024 release** (2022 estimates, dataset `fu4u-a9bh`), via CDC Open
  Data (`https://data.cdc.gov/resource/<dataset>.json`).
- **Access:** 2026-11-11. No key, no app token, no account — all requests
  returned HTTP 200 unauthenticated. ~24 requests total (12 count checks
  + 12 fetches), sequential, 1 s apart, 1 retry on 429/5xx.
- **Exact queries (SoQL):**
  - Count: `?$select=count(*)&$where=measureid='<M>' AND
    datavaluetypeid='CrdPrv'`
  - Fetch: `?$select=year,stateabbr,statedesc,locationname,locationid,
    measureid,measure,short_question_text,data_value,
    data_value_footnote_symbol,data_value_footnote,low_confidence_limit,
    high_confidence_limit,totalpopulation,totalpop18plus,geolocation
    &$where=measureid='<M>' AND datavaluetypeid='CrdPrv'&$limit=5000
    &$offset=<N>`
  - Measures `<M>`: DIABETES, COPD, CASTHMA, CHD, STROKE, OBESITY.
    Value type: crude prevalence only (`CrdPrv`, % of adults 18+).
- **Licence / attribution:** US federal government work — public domain.
  "Source: CDC PLACES: Local Data for Better Health, County Data, 2025
  release (2023 estimates) and 2024 release (2022 estimates), via CDC
  Open Data (data.cdc.gov). Estimates are model-based, derived from the
  Behavioral Risk Factor Surveillance System (BRFSS)."

## Fetch outcome

- Every count check matched its fetch exactly (rows fetched == count for
  all 12 measure-releases) — no truncation, no retry needed beyond the
  normal flow. A `$limit=5000` page returned each full measure in one call.
- `data_source.json` (in `data/processed/`) records the per-measure-year
  counts, the US-row drops, the suppressed rows, unmatched counties,
  national weighted-vs-US-row gaps, and median CI widths.

## Row counts and coverage

| Measure | 2023 fetched | 2023 analysed | 2022 fetched | 2022 analysed | Matched |
|---|---|---|---|---|---|
| Each of the 6 | 2,958 | 2,956 | 3,145 | 3,144 | 2,956 |

- **Analysed = fetched − 1 US aggregate row − suppressed rows.** The 2025
  release has 1 row per measure with no published value (footnote `*`);
  the 2024 release has 0. The suppressed county is **Loving County, TX**
  (locationid 48301) — the least-populous county in the US.
- **Kentucky and Pennsylvania are entirely absent from the 2025 release**
  (verified against the live API: 0 rows for DIABETES in 2023 vs 120 and
  67 rows in 2022). 2023 therefore covers 49 states; 2022 covers 51
  (50 states + DC). The 188 counties present only in 2022 are KY (120)
  + PA (67) + Loving County, TX (1).
- **National cross-check (M5):** our population-weighted national rate vs
  CDC's published `US` row — diabetes 2023: 12.05% vs 12.0% (+0.05 pp);
  COPD 2023: 6.49% vs 6.2% (+0.29 pp); asthma 2023: 10.21% vs 9.8%
  (+0.41 pp); heart disease 2023: 6.28% vs 6.4% (−0.12 pp); stroke 2023:
  3.41% vs 3.4% (+0.01 pp); obesity 2023: 33.20% vs 32.8% (+0.40 pp).
  The gap is a coverage note (the US row covers suppressed counties too),
  not an error.
- **Precision (median county 95% CI width, pp):** diabetes 3.9, COPD 3.0,
  asthma 2.7, heart disease 2.1, stroke 1.1, obesity 15.3 (2023).

## Files

- `data/processed/prevalence_<measure>.csv` — county rows, both years:
  `year,stateabbr,locationname,locationid,measureid,data_value,
  totalpop18plus,est_cases,lon,lat` (~6,100 rows each, < 400 KB each).
- `data/processed/change_<measure>.csv` — matched counties only:
  `locationid,locationname,stateabbr,measureid,value_2022,value_2023,
  pp_change,pct_change` (2,956 rows each).
- `data/processed/state_prevalence.csv` — population-weighted state rates
  (600 rows: 51 jurisdictions × 6 measures × 2 years, minus KY/PA 2023).
- `data/processed/data_source.json` — counts, coverage, gaps, CI widths.
- `data/processed/us_states.geojson` — simplified US state boundaries
  (51 features, 60 KB) for the dashboard choropleth, derived from the
  public-domain US states GeoJSON published by PublicaMundi
  (`https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/
  data/geojson/us-states.json`, Puerto Rico removed, state abbreviations
  added, coordinates rounded to 2 decimals). Bundled because Plotly's
  CDN topojson returns 403 in this environment — the dashboard map must
  render offline.
- `data/raw/sample_rows.json` — 3 raw rows per measure-year (36 rows), the
  provenance sample.

## Commit rule for data files

- The full raw Socrata JSON for 12 measure-releases is ~23 MB — over the
  5 MB/day limit — so raw responses go to a temporary directory and are
  deleted after processing. Only the compact processed CSVs above and the
  36-row sample are committed. `data/` totals ~3.0 MB, no file over 1 MB.
- `.gitignore` does NOT exclude `data/` (only `data/raw/*_synthetic.json`).
- Full raw is regenerable with one command:
  `python -m src.data_pipeline --live` (same queries, same counts).
- Synthetic fallback output (`data/raw/*_synthetic.json`, seed 42) is
  git-ignored and never overwrites live files.

## Manual validation (one metric, by hand)

- **Claiborne parish, LA — diabetes 2023 (from the committed CSV):**
  published prevalence 22.8%, adult population 11,034 →
  22.8 / 100 × 11,034 = 2,515.752 → **2,516 estimated cases**, exactly the
  `est_cases` value in `prevalence_diabetes.csv` (diff 0.0).
- **Louisiana diabetes state rate 2023:** recomputed from the county CSV
  as 100 × Σ est_cases / Σ totalpop18plus = **15.23%**, matching
  `state_prevalence.csv` to the last digit; the naive mean of county
  percentages (16.50%) is different, confirming the weighted roll-up.
- Both checks are also asserted in `tests/test_pipeline.py`
  (`test_estimated_cases_claiborne_hand_check`,
  `test_state_rate_matches_hand_computation`).

## Versions used for this build

- Python 3.12.3; pandas 3.1.1, numpy 2.5.4, matplotlib 3.11.2,
  plotly 7.1.0, streamlit 1.66.1, requests 2.34.2, pytest 9.2.0,
  jupyter 1.1.1, nbformat 5.11.1 (all pinned in `requirements.txt`).
- Offline mode: `python -m src.data_pipeline --offline` regenerates the
  derived tables from the committed CSVs and leaves `data_source.json`
  byte-identical (verified by test).
