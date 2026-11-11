# Day 07 — Disease Prevalence Dashboard: Research Brief

**Status:** RESEARCH COMPLETE (AGENTS.md, stage 1) — 2026-11-11.
**Business question:** How do reported disease rates differ across US places
and over time — once population denominators and data definitions are
accounted for?
**Roadmap entry (verbatim, p. 3):** "DAY 07 | Disease Prevalence Dashboard —
Problem / analysis: Compare reported disease rates across places and time,
accounting for population denominators and data definitions. GitHub
deliverable: Public health maps and geographic comparison dashboard."
Section context (Days 7–9, Healthcare & Medical Analytics). Core skills:
SQL, Python, classification, forecasting, Power BI. Suggested data (section
level, Days 7–9): CDC Open Data; de-identified or synthetic hospital
datasets. **No data source is listed for Day 7 itself** — this brief verifies
one from scratch.

## 1. Data source — verified (one lean pass, 2026-11-11)

### 1.1 Source chosen: CDC PLACES, County Data (Socrata / CDC Open Data)

- **Source:** CDC PLACES: Local Data for Better Health, County Data,
  **2025 release** — model-based county estimates from the Behavioral Risk
  Factor Surveillance System (BRFSS). Publisher: Centers for Disease
  Control and Prevention (CDC). Hosted on CDC Open Data (Socrata).
- **Dataset ID (2025 release):** `swc5-untb`
  — `https://data.cdc.gov/resource/swc5-untb.json`
- **Second release for the time comparison:** County Data **2024 release**,
  dataset ID `fu4u-a9bh` — `https://data.cdc.gov/resource/fu4u-a9bh.json`
- **Discovery path (verified, not assumed):** Socrata catalog API
  `https://api.us.socrata.com/api/catalog/v1?domains=data.cdc.gov&q=PLACES`
  returned 248 results; the 2025 County Data release (`swc5-untb`,
  updated 2026-09-22) and 2024 County Data release (`fu4u-a9bh`) were the
  newest county-level releases. Dataset metadata confirmed via
  `https://data.cdc.gov/api/views/swc5-untb` (name, columns, ~1.76B rows
  across all measures/years/geographies in the full table).
- **Auth:** none. No API key, no app token, no account. All probe calls
  below returned HTTP 200 unauthenticated.
- **Why this source (and not the alternatives):** CDC WONDER has no usable
  public API for this shape of query; NNDSS notifiable-disease counts are
  case counts without ready population denominators at county level; PLACES
  gives prevalence percentages **plus** the adult-population denominator
  (`totalpop18plus`), confidence limits, lat/lon per county, and a stable
  county identifier — exactly the roadmap's "population denominators and
  data definitions" requirement. County level (not census tract) keeps the
  fetch small and the maps legible.

### 1.2 Endpoints and exact queries (copy — do not re-derive)

Base: `https://data.cdc.gov/resource/<dataset>.json`. All queries are Socrata
SoQL `GET`s. No pagination tokens: Socrata uses `$limit` / `$offset`.

| # | Purpose | Exact query (URL-encoded form) |
|---|---|---|
| Q1 | Row-count check per measure/year (the anti-truncation check) | `?$select=count(*)&$where=measureid='<M>' AND datavaluetypeid='CrdPrv'` on `swc5-untb` (2023) and `fu4u-a9bh` (2022) |
| Q2 | Full fetch, one measure, one release | `?$select=year,stateabbr,statedesc,locationname,locationid,measureid,measure,short_question_text,data_value,low_confidence_limit,high_confidence_limit,totalpopulation,totalpop18plus,geolocation&$where=measureid='<M>' AND datavaluetypeid='CrdPrv'&$limit=50000&$offset=0` |
| Q3 | Distinct measures (already run — see §1.4) | `?$select=measureid,measure,short_question_text&$where=categoryid='HLTHOUT'&$group=measureid,measure,short_question_text&$order=measureid&$limit=50000` |

**Pagination rule (Day 6 lesson — no silent truncation):** fetch in
`$limit=5000` pages with `$offset` stepping by 5000; after each measure,
assert `rows fetched == Q1 count` for that measure/release. If they differ,
retry that page once, then stop and report — never proceed on a short fetch.
A `$limit=5000` probe on DIABETES returned all 2,958 rows in one call
(verified 2026-11-11), so one page per measure is expected; the loop and
the count assertion stay in the code regardless.

### 1.3 Rate limits and polite-use rule

- Socrata publishes no hard anonymous quota; the documented guidance is
  to use an app token for heavy use and to throttle. This build makes
  ~8 data requests total (6 measures × 2 releases, plus ~6 count checks),
  each ≤ 5,000 rows, sequential, with a 1-second sleep between requests and
  a single retry after 5 seconds on HTTP 429/5xx. If a 429 persists, stop
  and report — do not hammer the endpoint.
- No app token is created for this day: the probe traffic proves anonymous
  access works, and a token would add a secret to manage for ~14 requests.

### 1.4 Verified facts (probe results, 2026-11-11 — all HTTP 200)

- **12 health-outcome measures** in the 2025 release
  (`categoryid='HLTHOUT'`): ARTHRITIS, BPHIGH, CANCER, CASTHMA, CHD,
  COPD, DEPRESSION, DIABETES, HIGHCHOL, OBESITY, STROKE, TEETHLOST.
- **Six measures chosen for this day** (chronic conditions with the clearest
  public-health reading; TEETHLOST excluded — age-65+ denominator differs;
  BPHIGH/HIGHCHOL/ARTHRITIS/CANCER/DEPRESSION held for later days):
  DIABETES, COPD, CASTHMA (current asthma), CHD (coronary heart disease),
  STROKE, OBESITY.
- **2025 release = year 2023 only** for these measures (verified:
  `year × datavaluetypeid` counts for DIABETES are 2023/CrdPrv 2,958 and
  2023/AgeAdjPrv 2,958 — no 2022 rows for the chosen measures in this
  release, despite the dataset-level distinct-year list also showing 2022
  for other measures/types).
- **2024 release = year 2022** for DIABETES crude: 3,145 rows (verified).
  The coder MUST run the Q1 count check for the other five measures on
  `fu4u-a9bh` before fetching them — the 2022 per-measure counts are not
  yet verified.
- **Row counts (crude prevalence, `datavaluetypeid='CrdPrv'`, 2025
  release, year 2023): exactly 2,958 counties per measure** for all six
  chosen measures (CASTHMA, CHD, COPD, DIABETES, OBESITY, STROKE — each
  2,958). The US has ~3,143 counties: ~185 counties are missing per
  measure (small-population suppression / no estimate) — a disclosed
  coverage gap, not a fetch error.
- **Geography:** 50 states + DC covered (stateabbr list verified: AK…WY
  plus DC). **One extra row per measure has `stateabbr='US'`** — the
  national aggregate. It is NOT a county and MUST be excluded from all
  county-level analysis (it is kept in the raw file, flagged, and dropped
  by the pipeline with a logged count).
- **Sample row (verified, LA, DIABETES, crude, 2023):** Claiborne parish,
  `locationid=22027`, data_value 22.8%, CI 20.2–26.0,
  totalpopulation 13,670, totalpop18plus 11,034, geolocation
  (-92.9956, 32.8228). East Feliciana 16.1%. Tangipahoa age-adjusted 13.5%.
- **Suppression footnote:** 1 of 2,958 DIABETES crude rows carries
  `data_value_footnote_symbol='*'`; the rest have none. The pipeline keeps
  the footnote column and reports its count; flagged rows are retained
  (the value is still published) and noted.
- **Value type:** this day uses **crude prevalence only**
  (`datavaluetypeid='CrdPrv'`, `data_value_type='Crude prevalence'`,
  `data_value_unit='%'`). Age-adjusted values exist for the same rows and
  are deliberately NOT fetched — one definition per measure keeps the
  comparison clean, and the README states the choice and why (crude =
  the actual burden in the population; age-adjusted answers a different
  question). A reader comparing with age-adjusted figures will see
  different numbers; that is expected and documented.

### 1.5 Response fields and units (from the verified metadata)

| Field | Type | Meaning |
|---|---|---|
| `year` | text | Estimate year: "2023" (2025 release), "2022" (2024 release) |
| `stateabbr` / `statedesc` | text | State, e.g. LA / Louisiana |
| `locationname` | text | County/parish name, e.g. Claiborne |
| `locationid` | text | 5-digit county FIPS code (e.g. 22027) — join key |
| `measureid` / `measure` / `short_question_text` | text | e.g. DIABETES / "Diagnosed diabetes among adults" / Diabetes |
| `data_value` | number | Crude prevalence, **percent of adults aged 18+** |
| `low_confidence_limit` / `high_confidence_limit` | number | 95% confidence interval, same units |
| `totalpopulation` / `totalpop18plus` | number | County total population / adult (18+) population — the denominator |
| `geolocation` | point | `{type: Point, coordinates: [lon, lat]}` — county centroid |
| `data_value_footnote_symbol` / `data_value_footnote` | text | Suppression/quality flag (`*` on 1 row) |
| `datasource` | text | "BRFSS" for all six measures |

## 2. Metrics to compute (definitions — frozen before the coder starts)

All rates are **crude prevalence, % of adults 18+**. Never average county
percentages without weights — see M4.

- **M1 — County prevalence:** `data_value` as published (%, 1 decimal).
- **M2 — Estimated cases in a county:** `round(data_value / 100 ×
  totalpop18plus)`. Adults only — the denominator is `totalpop18plus`,
  never `totalpopulation`.
- **M3 — Year-over-year change (2022 → 2023):** for counties present in
  both releases, `pp_change = value_2023 − value_2022` (percentage
  points) and `pct_change = 100 × pp_change / value_2022`. Report pp as
  the headline; % change is secondary (a 1 pp move on a 5% base is +20%
  and must never be headlined alone).
- **M4 — State prevalence (population-weighted):** `100 × Σ cases /
  Σ totalpop18plus` over that state's counties. Simple mean of county
  percentages is WRONG (small counties would count as much as large ones)
  and is forbidden; a test asserts the weighted value differs from the
  naive mean and matches a hand-computed check.
- **M5 — National prevalence (population-weighted):** same formula over
  all counties (excludes the `US` aggregate row). Cross-check: it must be
  close to — but will not exactly equal — the published `US` row, because
  the US row is computed on the full county set including suppressed
  counties. Report both; the gap is a coverage note.
- **M6 — Spread / disparity:** per measure, range (max − min county),
  interquartile range, and the ratio of the highest to lowest state
  (population-weighted). Top-10 / bottom-10 counties per measure.
- **M7 — Data-quality flags:** counties present in 2023 but missing in
  2022 (and vice versa) per measure; footnote-`*` row count; CI width
  (high − low) as a precision indicator, reported as median CI width per
  measure.

**Scope guard:** these are **model-based estimates** from survey data
(BRFSS), not counted cases. The dashboard must say "estimated prevalence"
everywhere, never "cases" without the "estimated" qualifier, and never
present a county ranking as a league table of health — small counties have
wide CIs (M7) and the ranking is a starting point for questions, not a
verdict.

## 3. Licence / attribution

- CDC PLACES data are US federal government works — public domain, no
  licence fee, no key. Required attribution (used in README, data/README,
  dashboard footer, notebook): "Source: CDC PLACES: Local Data for Better
  Health, County Data, 2025 release (2023 estimates) and 2024 release
  (2022 estimates), via CDC Open Data (data.cdc.gov). Estimates are
  model-based, derived from the Behavioral Risk Factor Surveillance System
  (BRFSS)."
- Socrata terms: public API, no key required for this volume; cite the
  dataset IDs (`swc5-untb`, `fu4u-a9bh`).
- No personal data, no de-identification issues: all values are county
  aggregates.

## 4. Synthetic-fallback note

- **Fallback parameters (only if the live API is unreachable at build
  time):** generate `data/raw/*_synthetic.json` from the verified
  structure in §1.5 with seed 42: 6 measures × 200 synthetic counties,
  prevalence drawn from the verified 2023 ranges (DIABETES ~10–23% etc. —
  the coder takes the actual min/max from the live probe values in §1.4
  only if a live fetch partially succeeded; otherwise use plausible
  ranges and label the file synthetic). Synthetic files are git-ignored,
  `data_source.json` records `synthetic: true, seed: 42`, and the README
  states the dashboard ran on synthetic data. **The fallback is not
  expected to be needed — the live API returned HTTP 200 on every probe
  in this pass.**

## 5. Verification status

- ✅ Source, dataset IDs, endpoints, parameters verified live 2026-11-11
  (catalog API + metadata API + 6 probe queries, all HTTP 200, no auth).
- ✅ Row counts verified for all six measures, 2025 release (2,958 each).
- ✅ Sample rows inspected field-by-field (LA DIABETES, §1.4).
- ✅ Pagination behaviour verified (`$limit=5000` returns the full set).
- ⚠️ 2024-release (2022) per-measure counts verified for DIABETES only
  (3,145). Coder runs Q1 for COPD, CASTHMA, CHD, STROKE, OBESITY on
  `fu4u-a9bh` before fetching — 5 cheap count queries.
- ⚠️ The `US` national row and the ~185 missing counties per measure are
  known handling requirements, not surprises — see §1.4 and M5/M7.
- **No live fetch was performed by the researcher** (per AGENTS.md) —
  counts and samples above are probe queries only; the coder does the
  full fetch.

## 6. Handoff

1. **Produced:** this file
   (`day-07-disease-prevalence-dashboard/research_brief.md`).
2. **Verified numbers:** 12 health-outcome measures; 6 chosen; 2,958
   counties per measure (2023); DIABETES 2022 = 3,145 counties; 50 states
   + DC + 1 US row; LA Claiborne DIABETES 22.8% (CI 20.2–26.0).
3. **Known gaps:** 2022 counts for 5 of 6 measures unverified (coder Q1
   check); county coverage ~94% (2,958/3,143); cross-release comparison
   carries a methods/coverage caveat the planner must word.
4. **Next role's first step (planner):** decide the 3 research questions
   and the exact file tree, with the population-weighted state roll-up
   (M4) and the cross-release caveat as first-class plan items — and the
   map design (county choropleth needs a US-county geometry source; if no
   lightweight one is available, a state choropleth + county dot/scatter
   map from the verified `geolocation` centroids is the fallback — the
   planner decides, the coder does not re-search).
