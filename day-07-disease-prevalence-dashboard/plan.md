# Day 07 — Disease Prevalence Dashboard: Build Plan

**Status:** PLAN — planner sign-off complete (AGENTS.md, stage 2).
**Source of truth:** `research_brief.md` (2026-11-11) + this plan. **If brief
and plan disagree, the plan wins and the difference is noted in §11.** The
coder must reuse the brief + this plan. **No extra web searches.**
**Roadmap entry (verbatim):** "DAY 07 | Disease Prevalence Dashboard —
Problem / analysis: Compare reported disease rates across places and time,
accounting for population denominators and data definitions. GitHub
deliverable: Public health maps and geographic comparison dashboard."
Section context (Days 7–9, Healthcare & Medical Analytics). Core skills:
SQL, Python, classification, forecasting, Power BI. Suggested data (section
level): CDC Open Data; de-identified or synthetic hospital datasets.

| Item | Value |
|---|---|
| Fetch date | 2026-11-11 (estimates: 2022 from the 2024 release, 2023 from the 2025 release — §3) |
| Source | CDC PLACES County Data via CDC Open Data (Socrata), no key. 2025 release `swc5-untb` (2023 estimates); 2024 release `fu4u-a9bh` (2022 estimates) |
| Measures | 6 chronic conditions, crude prevalence, % of adults 18+: DIABETES, COPD, CASTHMA (current asthma), CHD (coronary heart disease), STROKE, OBESITY |
| Expected rows | **~35,500 county rows** (6 measures × ~2,958 counties in 2023 + ~3,145 in 2022 — the coder verifies the 2022 counts first, brief §5); 51 state rows × 6 measures × 2 years = 612 state rows; ~17,500 matched county year-over-year pairs |
| Requests | ~12 data requests + ~12 count checks, sequential, 1 s apart, 1 retry on 429/5xx |
| Scope | Descriptive comparison of **model-based estimates** of diagnosed chronic-disease prevalence across US counties and states, 2022→2023. **Not counted cases, not a causal analysis, not a health ranking.** Every number carries its definition (crude prevalence, adults 18+) and its coverage caveat. |

## 1. Problem statement + audience

**Problem.** A public-health reader (or a data analyst new to health data)
looking at disease numbers for US counties faces three traps: rates quoted
without denominators (a county with 40 cases in 1,000 people is not "worse"
than one with 400 cases in 100,000), county percentages averaged as if all
counties were the same size, and year-over-year changes quoted without
saying which definition or which counties are even in both years. Day 7
fetches CDC PLACES county estimates for six chronic conditions in 2022 and
2023, converts percentages into estimated adult cases using each county's
own adult population, rolls counties up to states **population-weighted**
(never a simple mean), and compares 2022→2023 only on counties present in
both years — with the missing counties, the confidence intervals, and the
cross-release caveat shown on the front page. The dashboard is the
roadmap's "public health maps and geographic comparison dashboard": an
interactive state choropleth + county bubble map, state and county rankings,
and the year-over-year change view.

**Audience / decision-maker.** A non-specialist reader who wants to know
*where* disease burden is highest, *how much* places differ, and *whether
things moved* last year — and a hiring reviewer who wants to see that the
analyst handled denominators, definitions and coverage honestly. Every
finding in the dashboard, notebook and notes must be plain-language, must
cite the numbers behind it, must say "estimated prevalence" (never bare
"cases"), and must never present a county ranking as a league table of
health. `outputs/insights_summary.md` is the plain-language findings note
(§4.4).

## 2. Research questions (exactly 3)

1. **Where is estimated prevalence highest and lowest — and how wide is
   the gap?** Per measure (2023): the population-weighted national rate,
   the highest/lowest states (population-weighted), the highest/lowest
   counties, and the spread (county range and IQR, state max/min ratio).
   Is the geographic pattern the same across conditions or
   condition-specific?
2. **Did prevalence move from 2022 to 2023 — and where?** Per measure, on
   counties present in both years: the median county change in percentage
   points, the share of counties up vs down, the biggest movers (up and
   down) with their CIs, and the national population-weighted change. Do
   the six conditions move together or independently?
3. **How much of what we see is definition and coverage, not disease?**
   What changes if the comparison used age-adjusted instead of crude
   rates (answered qualitatively from the definitions + one worked
   example, not by fetching a second dataset); how wide are the county
   confidence intervals (median CI width per measure); how many counties
   are missing from each year and from the matched comparison; and how far
   is our computed national rate from CDC's published `US` aggregate row
   (M5 cross-check)?

## 3. Data — source, endpoints, fetch rules, provenance, licence

### 3.1 Source and endpoints (verified, from the brief — copy, do not re-search)

- **Source:** CDC PLACES: Local Data for Better Health, County Data,
  2025 release (`swc5-untb`, 2023 estimates) and 2024 release
  (`fu4u-a9bh`, 2022 estimates), via CDC Open Data (Socrata,
  `https://data.cdc.gov/resource/<id>.json`). No key, no token, no
  account. All researcher probes returned HTTP 200 unauthenticated.
- **Endpoints (exactly the brief's Q1/Q2; parameters are what the brief
  verified — copy them, do not re-derive them):**

| Call | Query (SoQL) |
|---|---|
| Count check (per measure, per release) | `?$select=count(*)&$where=measureid='<M>' AND datavaluetypeid='CrdPrv'` |
| Full fetch (per measure, per release) | `?$select=year,stateabbr,statedesc,locationname,locationid,measureid,measure,short_question_text,data_value,low_confidence_limit,high_confidence_limit,totalpopulation,totalpop18plus,geolocation&$where=measureid='<M>' AND datavaluetypeid='CrdPrv'&$limit=5000&$offset=<N>` |

- **Measures:** DIABETES, COPD, CASTHMA, CHD, STROKE, OBESITY.
  **Value type:** crude prevalence only (`CrdPrv`, % of adults 18+).
  Age-adjusted values are NOT fetched (one definition per measure; the
  README states the choice and why — brief §1.4).
- **Fetch order (mandatory):** for each measure, run the count check on
  BOTH releases first, record the expected counts, then fetch in
  `$limit=5000` pages with `$offset` stepping by 5000, then assert
  `rows fetched == count` per measure/release. One page per measure is
  expected (2,958 / ~3,145 rows) — the loop and the assertion stay in the
  code regardless (Day 6 lesson: never trust a fetch that was not counted).
  Retry a failed page once after 5 s; on a second failure, stop and report
  — never proceed on a short fetch. 1-second sleep between requests.
- **Verified counts to expect (brief §1.4):** 2023, all six measures:
  exactly 2,958 rows each. 2022, DIABETES: 3,145. The other five 2022
  counts are UNVERIFIED — the coder records the actuals and reports them;
  do not assume 3,145.

### 3.2 Cleaning rules (frozen — the tester tests these)

1. Drop the `stateabbr='US'` national aggregate row from county tables
   (keep it in the raw sample file, flagged; log how many rows dropped —
   expect 1 per measure-year, 12 total). It must never enter a county or
   state computation; a test asserts no `US` row in any processed CSV.
2. `locationid` is the 5-digit county FIPS join key; keep as zero-padded
   string. `data_value`, CIs and populations are numeric; coerce errors to
   NaN and fail loudly if any `data_value` is NaN in the live fetch.
3. `geolocation.coordinates` → `lon`, `lat` (floats, 3 decimals in the
   committed CSVs). A county with missing coordinates is kept in tables
   but excluded from the bubble map, with the count logged.
4. `est_cases = round(data_value / 100 × totalpop18plus)` — adults only.
   `totalpopulation` is NOT a denominator for anything in this project.
5. Footnote `*` rows: retained, counted per measure-year in
   `data_source.json` (`footnote_star_rows`), and noted in data/README.md.
6. Year-over-year matching is on `(locationid, measureid)` present in
   BOTH years (inner join). Unmatched counties are counted per measure
   and reported (M7), never silently dropped without a count.
7. **State roll-up (M4, population-weighted):**
   `state_rate = 100 × Σ est_cases / Σ totalpop18plus` over that state's
   counties. A simple mean of county percentages is forbidden; a test
   asserts the weighted value matches a hand-computed check and differs
   from the naive mean.
8. **National roll-up (M5):** same formula over all counties. Compare
   with the published `US` row value (kept aside before dropping);
   record both numbers and the gap in `data_source.json` and
   data/README.md — the gap is a coverage note (suppressed counties),
   not an error to fix.

### 3.3 Data-size and commit rule (differs from Days 1–6 — read carefully)

- The full raw Socrata JSON for 12 measure-releases is ~23 MB — far over
  the 5 MB/day limit. Therefore: the pipeline fetches raw JSON to a
  **temporary directory (not `data/raw/`)**, parses it, writes the compact
  processed CSVs below, writes `data/raw/sample_rows.json` (3 rows per
  measure-year, 36 rows, the provenance sample), and **deletes the full
  raw JSONs**. Full raw is regenerable with one command
  (`python -m src.data_pipeline --live`, documented in data/README.md).
- **`.gitignore` does NOT exclude `data/` or `data/raw/*.json`** — the
  scaffold default (only `data/raw/*_synthetic.json`) stays, so the
  orchestrator's `.gitignore` check passes. No large file will exist on
  disk in `data/` at handoff, so the validator's data-size check
  (no file > 1 MB, `data/` < 5 MB total) passes on the real files.
- **Committed processed files (per-measure split keeps every file
  < 1 MB):** `data/processed/prevalence_<measure>.csv` (both years,
  ~6,100 rows, ~400 KB each), `data/processed/change_<measure>.csv`
  (matched counties, ~2,900 rows, ~150 KB each),
  `data/processed/state_prevalence.csv` (612 rows),
  `data/processed/data_source.json` (counts, coverage, M5 gap, fetch
  timestamps). Expected `data/` total ≈ 3.5 MB — inside the 5 MB limit.
- Processed CSV columns — `prevalence_<m>.csv`: `year,stateabbr,
  locationname,locationid,measureid,data_value,totalpop18plus,est_cases,
  lon,lat` (CI limits are NOT stored per row; median CI width per
  measure-year is computed by the pipeline and stored in
  `data_source.json`). `change_<m>.csv`: `locationid,locationname,
  stateabbr,measureid,value_2022,value_2023,pp_change,pct_change`.
  `state_prevalence.csv`: `year,stateabbr,statedesc,measureid,
  state_rate,totalpop18plus,est_cases,n_counties`.
- `--offline` mode runs from the committed processed CSVs only (no
  network, no raw needed) and regenerates `state_prevalence.csv`,
  `change_*.csv` and `data_source.json` derived fields byte-identically
  except `generated_at_utc` (the Day 5/6 source-field lesson: the offline
  path must NOT clobber `source: "live"` or the quota/count fields — it
  skips rewriting `data_source.json` when a live record exists, verified
  by a test, as in Day 6 D-2).

### 3.4 Fallback, licence, attribution

- **Synthetic fallback (only if the live API is unreachable):** generate
  `data/raw/*_synthetic.json` with seed 42, 6 measures × 200 synthetic
  counties, prevalence drawn from the verified 2023 ranges; git-ignored;
  `data_source.json` records `synthetic: true, seed: 42`; README and
  dashboard label the data synthetic. Not expected to be needed (all
  probes HTTP 200).
- **Licence/attribution:** CDC PLACES is a US federal work — public
  domain, no key, no fee. Attribution everywhere (README, data/README,
  dashboard footer, notebook): "Source: CDC PLACES: Local Data for Better
  Health, County Data, 2025 release (2023 estimates) and 2024 release
  (2022 estimates), via CDC Open Data (data.cdc.gov). Estimates are
  model-based, derived from the Behavioral Risk Factor Surveillance System
  (BRFSS)." Dataset IDs `swc5-untb` / `fu4u-a9bh`.

## 4. Analysis — definitions (from the brief, frozen)

- **M1** county prevalence = published `data_value` (%, 1 decimal).
- **M2** estimated cases = `round(data_value / 100 × totalpop18plus)`.
- **M3** YoY change on matched counties: `pp_change = v2023 − v2022`;
  `pct_change = 100 × pp_change / v2022`. Headline pp, % secondary.
- **M4** state rate = population-weighted (see §3.2 rule 7).
- **M5** national rate = population-weighted over all counties;
  cross-check vs the published `US` row.
- **M6** spread: per measure, county range, IQR, state max/min ratio;
  top-10 / bottom-10 counties per measure (2023).
- **M7** quality flags: unmatched-county counts per measure, footnote
  `*` counts, median CI width per measure-year.
- **Scope guard (must appear in README, dashboard, notebook, insights):**
  model-based estimates from survey data, not counted cases; say
  "estimated prevalence" everywhere; county rankings are a starting point
  for questions, not a verdict — small counties have wide CIs.

## 5. File tree (exact — build only this)

```
day-07-disease-prevalence-dashboard/
├── README.md  requirements.txt  .gitignore  LICENSE  pyproject.toml
├── research_brief.md  plan.md  coder_handoff.md  test_report.md
├── optimizer_handoff.md  publisher_handoff.md
├── data/
│   ├── README.md
│   ├── data_source.json            (in data/processed/ — see §3.3; keep
│   │                                the scaffold's data/README.md)
│   ├── raw/
│   │   └── sample_rows.json        (36 rows, provenance sample)
│   └── processed/
│       ├── prevalence_diabetes.csv  prevalence_copd.csv
│       ├── prevalence_asthma.csv    (CASTHMA — filename uses asthma)
│       ├── prevalence_chd.csv       prevalence_stroke.csv
│       ├── prevalence_obesity.csv
│       ├── change_diabetes.csv  change_copd.csv  change_asthma.csv
│       ├── change_chd.csv  change_stroke.csv  change_obesity.csv
│       ├── state_prevalence.csv
│       ├── data_source.json
│       └── us_states.geojson        (bundled state boundaries, §11)
├── notebooks/analysis.ipynb
├── src/
│   ├── __init__.py
│   ├── data_pipeline.py
│   ├── metrics.py
│   ├── make_charts.py
│   ├── state_map.py                 (matplotlib state map, §11)
│   └── app.py
├── outputs/
│   ├── insights_summary.md
│   └── charts/
│       ├── 01_state_ranking.png
│       ├── 02_county_distribution.png
│       ├── 03_change_2022_2023.png
│       └── 04_measure_comparison.png
├── screenshots/
│   └── dashboard.png
└── tests/
    └── test_pipeline.py
```

Notes: the scaffold's `tests/test_smoke.py` is REPLACED by
`tests/test_pipeline.py` (the smoke tests are the readme/data-readme
existence checks plus the pipeline tests — do not keep two test files).
`src/__init__.py` is new (Day 6 has none — the coder adds it only if the
`python -m src.…` invocation needs it; if imports work without it, leave
it out and note the difference here in §11). No `weekly_briefing.md`
(Day 6 only), no extra modules, no extra charts.

## 6. Per-file responsibilities

| File | Responsibility |
|---|---|
| `src/data_pipeline.py` | Live fetch (brief Q1/Q2, count-assert, 1 s sleep, 1 retry), parse + clean (§3.2 rules 1–6), write `prevalence_<m>.csv`, `change_<m>.csv`, `state_prevalence.csv`, `data_source.json`, `sample_rows.json`; `--live` / `--offline` / `--use-cache` modes; `--keep-raw` debug flag (default off — raw deleted after processing, §3.3); synthetic fallback (`--synthetic`, seed 42) |
| `src/metrics.py` | Pure functions: `estimated_cases`, `weighted_rate`, `yoy_change`, `spread_stats`, `median_ci_width`, `top_bottom` — no I/O, no network; all tested |
| `src/make_charts.py` | Exactly 4 PNGs (§7), matplotlib `Agg`, offline from processed CSVs only, every chart footnoted with the CDC source + "model-based estimates" + year; synthetic label if applicable |
| `src/app.py` | Streamlit dashboard: measure + year selectors; state map (matplotlib, `src/state_map.py`, from the bundled geojson — Plotly geo cannot render offline, §11) + county dot map (plotly lon/lat scatter); state/county ranking tables; YoY change view; methods + caveats panel; `width="stretch"` (Day 2 lesson — no deprecated `use_container_width`); footer with attribution |
| `notebooks/analysis.ipynb` | Offline analysis top-to-bottom: load processed CSVs, answer Q1–Q3 with tables + the 4 charts inline, `_find_root()` from the notebook file location (Day 1 lesson (e)), 16 cells max, 0 error cells via nbconvert |
| `tests/test_pipeline.py` | ≥15 tests: M2 hand-check, M4 weighted vs naive mean + hand value, M3 pp/% on a fixture, US-row exclusion, matched-join counts, no-NaN values, lon/lat ranges, per-file row counts vs `data_source.json`, offline reproducibility (derived tables byte-identical), synthetic files never overwrite live files |
| `data/README.md` | Provenance: endpoints, exact queries, fetch date, row counts per measure-year (actuals), coverage (missing counties, US row, unmatched), M5 gap, manual validation, versions |
| `outputs/insights_summary.md` | One finding per §2 question with exact numbers + one actionable recommendation + limitations |
| `README.md` | Problem, audience, setup, how to run (live/offline), sample outputs (state table + chart thumbnails), headline findings with numbers, validation, limitations, attribution |
| `requirements.txt` | Pinned `==` versions verified in the build venv (Python 3.12.3): same stack as Day 6 (pandas, numpy, matplotlib, plotly, streamlit, requests, pytest, jupyter, nbformat) — no new runtime dependency without a plan change |
| `pyproject.toml` / `.gitignore` | Scaffold defaults (ruff/black line-length 88; gitignore excludes only `data/raw/*_synthetic.json` for data) |

## 7. Charts (exactly 4, matplotlib, to scale and legible)

All charts: title, labelled axes with units (%), source footnote
("Source: CDC PLACES County Data, 2025 release (2023) / 2024 release
(2022) — model-based estimates, crude prevalence, adults 18+"), no
truncated axes (bars start at 0 unless the chart is a distribution), state
and county names legible at 100% zoom.

1. **01_state_ranking.png** — Horizontal bar, all 51 states (+DC) ranked
   by population-weighted prevalence for the default measure (Diabetes,
   2023), highest at top, national weighted rate as a vertical reference
   line. Answers Q1 at state level.
2. **02_county_distribution.png** — Two panels: (a) histogram of county
   prevalence for Diabetes 2023 with median/IQR marked; (b) box plots of
   county prevalence by measure (2023, all six) on a shared % axis so
   spreads are comparable. Answers Q1's spread half.
3. **03_change_2022_2023.png** — Two panels: (a) histogram of county
   pp-changes 2022→2023 for Diabetes (matched counties only, 0 line
   marked, median labelled); (b) horizontal bar of median county
   pp-change by measure (all six) with the share of counties up/down
   annotated. Answers Q2.
4. **04_measure_comparison.png** — Grouped bars: national
   population-weighted prevalence by measure, 2022 vs 2023 side by side,
   with the pp change labelled on each pair. Answers Q2 at national level
   and frames Q3's definition note.

The interactive maps (state choropleth + county bubble map) live in the
Streamlit dashboard only (plotly, renders in the browser) — the static
PNGs above are the committed chart deliverables. The dashboard also
embeds the 4 PNGs (as Day 6 does) so the README thumbnails and the app
agree.

## 8. Success checklist (roadmap minimum success criteria — all must pass)

- [ ] Problem statement + audience written (§1, in README and this plan)
- [ ] Data source documented: provider, endpoints, the Q1/Q2 queries, both
  releases, collection date (2026-11-11), licence/attribution (CDC PLACES
  + BRFSS, public domain, dataset IDs), row counts (actuals per
  measure-year), coverage flags — in `data/README.md` and
  `data/processed/data_source.json` (with the §3.3 source-field rule:
  offline runs never clobber `source: "live"`)
- [ ] Repeatable prep steps documented (fetch → clean → metrics → charts,
  with `--offline` mode) + metric definitions M1–M7 (§4) written down
- [ ] ≥2 well-labelled visualisations produced — Day 7 produces exactly 4
  (§7), **drawn to scale and legible**, plus a functional dashboard: the
  Streamlit dashboard runs and renders (smoke gate, §9)
- [ ] Public health maps + geographic comparison dashboard delivered
  (roadmap): state choropleth + county bubble map in the app, state and
  county rankings, YoY change view, caveats panel
- [ ] Interpretation written (`outputs/insights_summary.md`, one finding
  per §2 question with exact numbers) + one actionable recommendation
- [ ] README with setup instructions, sample outputs (state table + chart
  thumbnails), validation results, and limitations
- [ ] No credentials / private records in the repo; no huge files committed
  (`data/` < 5 MB total, no file > 1 MB); `.gitignore` does not exclude
  `data/` (only `data/raw/*_synthetic.json`)
- [ ] One metric manually validated by hand and recorded in
  `data/README.md` (the tester recomputes one state rate and one county's
  est. cases from the committed CSVs, matching to the last digit)
- [ ] Pipeline runs end-to-end from a clean checkout (`pip install -r
  requirements.txt`, `python -m src.data_pipeline --offline`,
  `python -m src.make_charts`, `pytest tests/ -q`) — **pytest passing
  both from the repo root and from inside the day folder**
- [ ] Notebook runs top-to-bottom without errors (offline, via nbconvert,
  with `_find_root()`)
- [ ] Pinned dependencies in `requirements.txt`; `black --check` +
  `ruff check` clean
- [ ] Streamlit smoke gate passed: fresh port 8502+, HTTP 200 on `/` and
  on `/_stcore/health`, real `screenshots/dashboard.png` captured, server
  killed and port verified free
- [ ] Charts to scale and legible; frozen-tree check passed immediately
  before push (every file the READMEs reference exists on disk — charts,
  screenshot, CSVs)
- [ ] **Denominators, definitions and coverage documented prominently**
  (roadmap requirement): crude-vs-age-adjusted choice, population-weighted
  roll-up, missing counties, cross-release caveat, model-based-estimate
  scope guard — in README, dashboard, notebook and insights summary;
  **zero** presentation of a county mean as a state rate; **zero** bare
  "cases" without "estimated"

## 9. Coder handoff checklist (reference — coder must satisfy all of these before the tester starts)

- [ ] venv exists with pinned deps installed; `black --check` + `ruff check` pass; `pytest` passes
- [ ] `.gitignore` matches §5/§6 (only `data/raw/*_synthetic.json` for data)
- [ ] `screenshots/dashboard.png` is a real capture of the running app on a fresh port (8502+)
- [ ] `data/` total < 5 MB, no file > 1 MB; no full raw JSONs left on disk
- [ ] `data_source.json` records live counts, coverage, M5 gap, footnote counts
- [ ] Build only what §5 lists; no extra web searches

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| 2022 per-measure counts differ from the 2023 pattern (only DIABETES verified) | Count-check-first fetch order (§3.1); coder reports actuals, plan's expected rows are explicitly approximate |
| Cross-release methods/coverage change (2,958 vs 3,145 counties) makes YoY moves partly compositional | Matched-county join only (M3); unmatched counts reported (M7); caveat in README/dashboard/notebook |
| State choropleth needs geometry | Plotly built-in `locationmode="USA-states"` — no external file; county map uses verified lon/lat centroids via `scatter_geo` |
| Raw JSON too big to commit | §3.3: temp-dir raw, compact per-measure CSVs, 36-row provenance sample; regenerable with one command |
| County ranking misread as a health league table | Scope guard (§4) in all four surfaces; CIs shown; top/bottom framed as "highest estimated prevalence" with CI widths |
| A tiny county's wide CI dominates a "biggest mover" claim | Biggest-movers tables carry CI width / note the CI-overlap check; insights text says whether the move exceeds the CI |

## 11. Differences from the brief (plan wins)

- **Raw-data handling (§3.3):** the brief (§1.2/§4) assumes the standard
  commit-small-raw pattern; the plan replaces it with temp-dir raw +
  per-measure compact CSVs + 36-row sample, because the full raw is
  ~23 MB and the validator counts on-disk files in `data/` (verified in
  `agents/orchestrator.py` — the size check uses `rglob`, not git status).
  The brief's Q1/Q2 queries, counts and definitions are unchanged.
- **Measure filename for CASTHMA:** files use `asthma`
  (`prevalence_asthma.csv`) for readability; `measureid` inside the files
  stays `CASTHMA`.
- **`src/__init__.py`:** may be added or omitted per §5 note — coder
  decides by whether `python -m src.…` works, and records the choice in
  the coder handoff.
- **Footnote `*` rows (§3.2 rule 5):** the brief (§1.4) assumed the
  `*` row keeps a published value. Verified 2026-11-11 during the coder's
  fetch: exactly 1 row per measure in the 2025 release has a NULL
  `data_value` (Socrata omits the field) — that IS the `*` row, a
  suppressed estimate with no value to analyse. The pipeline drops it
  and records the count in `data_source.json`
  (`rows_without_published_value`); analysed 2023 counties are 2,957
  per measure, not 2,958. The 2024 release has 0 such rows.
- **State map implementation (§7, plan):** the plan specified a Plotly
  state choropleth. Verified 2026-11-11 via CDP that plotly.js fetches a
  topojson base map from cdn.plot.ly for ANY geo subplot (usa_110m.json
  with scope='usa', world_110m.json without) and the whole geo subplot
  fails when that fetch fails (403 / tunnel failure here) — 0 geo paths
  drawn even with a bundled geojson and all base layers disabled. The
  dashboard state map is therefore rendered with matplotlib from the
  bundled `data/processed/us_states.geojson` (`src/state_map.py`,
  new file, not in the plan's §5 tree); the county dot map stays Plotly
  (plain lon/lat scatter — verified rendering). The roadmap deliverable
  ("public health maps") is unchanged; only the rendering library moved.
- **CI limits:** stored as a per-measure-year median in
  `data_source.json`, not per row in the committed CSVs (size saving,
  §3.3); the raw sample retains the per-row CIs.
