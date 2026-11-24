# Day 17 — Drought Impact Analyzer: Build Plan

**Status:** PLAN — planner sign-off complete (AGENTS.md, stage 2).
**Source of truth:** `research_brief.md` (2026-11-24) + this plan. **If brief
and plan disagree, the plan wins and the difference is noted in §11.** The
coder must reuse the brief + this plan. **No extra web searches.**
**Roadmap entry (verbatim):** "Relate drought severity and precipitation
anomalies to crop performance across counties or years. GitHub deliverable:
County map with trend and correlation insights."
**Core skills:** Regression, weather joins, time-series forecasting, GIS.
**Suggested data:** USDA Quick Stats; NOAA weather; US Drought Monitor.

| Item | Value |
|---|---|
| Fetch date | 2026-11-24 |
| Drought source | US Drought Monitor REST API, no key — `https://usdmdataservices.unl.edu/api/` (verified HTTP 200, 2026-11-24) |
| Yield source | OWID "Maize yields" CSV (FAO), USA 2000–2025, 26 rows — copied from Day 16's committed raw file (verified 2026-11-23) |
| Weather source | Open-Meteo ERA5 archive, Iowa + Illinois centroids — copied from Day 16's committed raw JSONs (verified 2026-11-23) |
| Crop / geography | Maize (corn); national yield vs Iowa + Illinois drought/weather; county drought for all 201 IA + IL counties |
| Window | 2000–2025 (26 years; USDM weekly maps start 2000-01-04) |
| Deliverable | County map with trend and correlation insights (README + `outputs/insights_summary.md` + Streamlit dashboard + 4 charts + notebook) |
| Scope | Annual drought–yield relationships + county drought ranking/map. No county yields (no USDA key — brief §1b). No 2026 yield prediction. The 2026 DSCI number is an AR(1) extrapolation, labelled as such. |

## 1. Problem statement + audience

**Problem.** A grower, buyer or planner who wants to know whether drought
actually moves the US corn harvest has three separate histories — the
weekly US Drought Monitor, daily Corn Belt weather, and annual national
yield — in three different shapes. This project joins them once, in the
open: 26 years of weekly drought severity (DSCI and % area in each D0–D4
class) for Iowa and Illinois, growing-season precipitation anomalies from
the same two states, and national maize yield, then asks how much of the
year-to-year yield variation drought explains once the long technology
trend is removed — and shows, on a county map, where drought hits hardest.

**Four hard limits, stated up front and labelled on every surface (README,
notebook, insights, dashboard, charts):**

1. **National yield, 2-state drought/weather.** The yield is the USA
   national figure; the drought and weather are Iowa + Illinois, the two
   largest corn states (~35% of US output). They are a proxy for the
   national crop, not a national average — say so wherever the series are
   described.
2. **No county yields.** USDA Quick Stats needs a key (HTTP 401 without
   one, brief §1b), so county-level crop performance is out of scope.
   The county analysis is drought severity by county; the yield
   relationship is by year at state/national level. The county map
   answers "where did drought hit hardest", not "where did yield fall".
3. **Association, not causation.** Drought moving with yield is a
   statistical association. Allowed language: "associated with",
   "moves with", "explains X% of the detrended variance". No "drought
   causes yield loss" claims.
4. **Small sample — 26 annual rows.** Correlations on 26 points carry
   wide uncertainty; report p-values and confidence language, and do
   not over-claim. The AR(1) 2026 DSCI forecast is a statistical
   extrapolation, not a weather forecast.

**Audience / decision-maker.** A farm planner or data reviewer who wants a
reproducible drought–yield analysis: the exact sources and URLs, the DSCI
definition, the detrend step, the correlations with p-values, the county
ranking, and every published number matching the committed CSVs.

## 2. Decisions (frozen)

### 2.1 Research questions (exactly 3)

1. How strongly is growing-season drought severity (DSCI) associated
   with US maize yield once the technology trend is removed — and how
   does that compare with the precipitation-anomaly association?
2. Which years and which counties were hit hardest by drought, and what
   happened to yield in the worst drought years (2012 first)?
3. Can a simple AR(1) on annual growing-season DSCI beat the naive
   last-year forecast — and what does it say for 2026?

### 2.2 Other frozen decisions

- **Units:** yield in t/ha primary, bu/acre alongside (1 t/ha = 15.93
  bu/acre, brief §1b). DSCI 0–500 (brief §1a). Precipitation in mm,
  anomalies in mm and % of the 2000–2025 mean.
- **Growing season:** April–September inclusive (corn growing season in
  the Corn Belt). A USDM week belongs to the growing season if its
  `ValidStart` falls in Apr–Sep. July is the silking month — July
  precipitation anomaly gets its own column.
- **Detrend (primary result):** yield residual = yield − OLS fit of
  yield on year (fit on all 26 years). All drought/yield correlations
  are computed on the residual as the primary result; the raw-yield
  correlation is reported alongside for transparency, never alone.
- **DSCI annual aggregates (per state, per year):** `gs_dsci_mean` =
  mean weekly DSCI over growing-season weeks; `gs_dsci_max` = max weekly
  DSCI in the year; `weeks_dsci_ge100` = count of weeks in the year with
  DSCI ≥ 100; `weeks_any_d2plus` = count of weeks with any D2+ area.
  The two-state value is the simple mean of Iowa and Illinois.
- **County annual aggregates (per county, per year):** from weekly %
  area: `gs_d1plus_pct`, `gs_d2plus_pct`, `gs_d3plus_pct` = mean % area in
  D1+/D2+/D3+ over growing-season weeks; `gs_dsci` = mean weekly county
  DSCI proxy (1×D0 + 2×D1 + 3×D2 + 4×D3 + 5×D4). County ranking is by
  mean `gs_d2plus_pct` over 2000–2025.
- **Correlations (exactly 3, frozen):** (a) gs DSCI mean vs yield
  residual, (b) gs precipitation anomaly (mm) vs yield residual,
  (c) July precipitation anomaly (mm) vs yield residual. Each: Pearson r,
  two-sided p-value (scipy), R², OLS slope with units. No other
  correlations are computed — do not go fishing.
- **AR(1) forecast:** fit AR(1) (OLS of DSCI_t on DSCI_{t−1} with
  intercept) on annual gs DSCI mean (IA+IL avg). Backtest: fit on
  2000–2024, forecast 2025, compare to actual 2025 and to the naive
  last-year forecast (2024 value) by absolute error. Then refit on all
  26 years and forecast 2026 with a ±1 residual-std interval. Labelled
  "statistical extrapolation, not a weather forecast" on every surface.
- **Charts:** exactly 4, matplotlib, to scale and legible (§7). Chart 04
  is the county choropleth, drawn from the plotly county GeoJSON
  polygons with matplotlib (no geopandas, no kaleido — kaleido 1.2.0
  fails against plotly 7.1.0 in this environment, Day 16 note).
- **Dependencies:** reuse the Day 16 verified pins (pandas 3.1.1, numpy
  2.5.4, matplotlib 3.11.2, streamlit 1.66.1, requests 2.34.2, pytest
  9.2.0, jupyter 1.1.1, nbformat 5.11.1, scikit-learn 1.9.1,
  scipy 1.18.1). No plotly, no geopandas, no statsmodels, no new
  dependency without a plan change.
- **No 2026 yield prediction.** The 2025 harvest is the latest actual.

## 3. Data — source, endpoints, fetch rules, provenance, licence

### 3.1 Source and download (verified, from the brief — copy, do not re-search)

- **Drought (live, 8 HTTP calls total):**
  - State DSCI: GET
    `https://usdmdataservices.unl.edu/api/StateStatistics/GetDSCI?aoi=19&startdate=1/1/2000&enddate=12/31/2025&statisticsType=1`
    (Iowa, FIPS 19) and the same with `aoi=17` (Illinois). Expect
    ~1,357 weekly rows each (2000-01-04 → 2025-12-30), columns
    `Name,MapDate,DSCI`. Commit as `data/raw/dsci_iowa.csv`,
    `data/raw/dsci_illinois.csv` (~25 KB each).
  - County % area: GET
    `https://usdmdataservices.unl.edu/api/CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent?aoi=IA&startdate=1/1/2000&enddate=12/31/2008&statisticsType=1`
    and the same for `2009–2017` and `2018–2025`, then the same three
    blocks for `aoi=IL`. Expect ~99 IA counties × ~470 weeks per block
    (~46k rows, ~4 MB per block). **Do NOT commit the county raw CSVs**
    (size rule §3.4): save to `data/raw/dsci_counties_ia_YYYY_YYYY.csv`
    locally, git-ignored, and aggregate immediately to the committed
    processed county files.
  - One retry after 10 s on a 5xx, then stop and fall back to the
    committed cache. No key, no account.
- **Yield (copy, not a fetch):** copy
  `../day-16-crop-yield-prediction/data/raw/maize_yields_owid.csv` to
  `data/raw/maize_yields_owid.csv`. Record `copied_from: day-16`,
  `fetch_date: 2026-11-23` in `data_source.json`. If the copy is missing,
  the pipeline may GET the OWID URL as a fallback (brief §1b).
- **Weather (copy, not a fetch):** copy Day 16's
  `weather_iowa.json` and `weather_illinois.json` to `data/raw/`.
  Record the same copy provenance. If missing, the pipeline may GET the
  Open-Meteo archive URL as a fallback (brief §1c).
- **County GeoJSON (fetch at chart time, not committed):** GET
  `https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json`
  (3,216,816 B, 3,221 features, verified 2026-11-24). Cache to
  `data/raw/counties_geo.json` locally (git-ignored). If the download
  fails, chart 04 falls back to a horizontal bar chart of the top 15
  counties by mean D2+ % — and the fallback is labelled on the chart.
- **Pipeline modes:** `--live` (default: fetch, then build),
  `--offline` (replay from committed raw files, no network),
  `--use-cache` (use raw files if present, else fetch). The offline run
  must reproduce the processed files byte-for-byte except
  `data_source.json` timestamps (tester checks this). In `--offline`
  mode the county aggregates rebuild from the committed processed
  `county_year.csv` (not from raw weekly county files, which are not
  committed); record `county_raw_available: false` in that case.

### 3.2 Cleaning rules (frozen — the tester tests these)

1. DSCI: parse `MapDate` as YYYYMMDD; assert DSCI integer 0–500, no NaN,
   weekly dates strictly increasing, first date 20000104. Weeks are
   USDM map weeks (Tuesday–Monday); `ValidStart`/`ValidEnd` come from
   the county files only.
2. County % area: assert `None + D0 + D1 + D2 + D3 + D4` sums to 100.0
   ± 0.05 per row (the USDM columns are cumulative: `None` = % with no
   drought, D0 = % in D0 or worse — so the exclusive shares are
   None, D0−D1, D1−D2, D2−D3, D3−D4, D4, and the DSCI proxy uses the
   cumulative columns as 1×D0 + 2×D1 + 3×D2 + 4×D3 + 5×D4, exactly as
   USDM defines it). Assert FIPS is a 5-digit string, county + state
   present, 99 IA + 102 IL counties (201 total).
3. Yield: same as Day 16 §3.2 rule 1 (26 rows, 2000–2025, no NaN).
4. Weather: same as Day 16 §3.2 rules 2–3 (daily → growing-season
   totals per state, then the two-state mean). Precipitation < 0 →
   error, never silently clipped.
5. Join: inner join on `year` (26 rows expected). Add
   `yield_bu_per_acre` = `yield_t_per_ha` × 15.932 and `yield_resid_t_per_ha`
   = yield − OLS(year) fit. Add `gs_precip_anomaly_mm` and
   `gs_precip_anomaly_pct` vs the 2000–2025 mean, and
   `jul_precip_anomaly_mm`.
6. No imputation anywhere. A failed assertion stops the pipeline with a
   clear message — it never writes partial processed files.

### 3.3 Cross-checks (frozen — run before the tester starts)

- Row counts: DSCI rows ~1,357/state; county rows 201 counties × 26
  years = 5,226 in `county_year.csv`; annual table 26 rows.
- 2012 is the worst drought year by gs DSCI mean (expect gs DSCI mean
  well above 200; the tester verifies the direction, not a number from
  memory).
- 2012 yield residual is negative (the 2012 harvest fell below trend).
- Hand-validation metric (§4.4): Iowa 2012 growing-season mean DSCI,
  computed independently from `data/raw/dsci_iowa.csv` with a one-liner
  and compared to `annual_drought_yield.csv` — exact match required.

### 3.4 Data-size and commit rule (READ CAREFULLY)

Small raw data IS committed: raw files under 1 MB each, under 5 MB per
day. Committed raw: `dsci_iowa.csv` (~25 KB), `dsci_illinois.csv`
(~25 KB), `maize_yields_owid.csv` (~369 KB),
`weather_iowa.json` (~210 KB), `weather_illinois.json` (~210 KB) —
total raw ~840 KB. **NOT committed** (git-ignored, documented in
`data/README.md`): `data/raw/dsci_counties_*.csv` (~4 MB each, ~24 MB
total) and `data/raw/counties_geo.json` (3.2 MB). `.gitignore` must NOT
exclude `data/` as a whole — only the two named large-file patterns.
Processed files are all < 1 MB. `data_source.json` records source URLs,
fetch date, row counts, `synthetic: false`, the Day 16 copy provenance,
and the manual-validation section (added by the tester, §4.4 — a `--live`
re-run drops it; do NOT re-run `--live` after the tester fills it).

### 3.5 Committed processed files (all < 1 MB; regenerable with one command)

- `data/processed/annual_drought_yield.csv` — 26 rows: year, yield_t_per_ha,
  yield_bu_per_acre, yield_resid_t_per_ha, gs_dsci_mean, gs_dsci_max,
  weeks_dsci_ge100, weeks_any_d2plus, gs_precip_total_mm,
  gs_precip_anomaly_mm, gs_precip_anomaly_pct, jul_precip_anomaly_mm.
- `data/processed/correlation_results.csv` — 3 rows (one per §2.2
  correlation): variable, pearson_r, p_value, r_squared, ols_slope,
  slope_units, n.
- `data/processed/county_year.csv` — 5,226 rows: fips, county, state,
  year, gs_d1plus_pct, gs_d2plus_pct, gs_d3plus_pct, gs_dsci.
- `data/processed/county_summary.csv` — 201 rows: fips, county, state,
  mean_d2plus_pct, worst_year, worst_year_d2plus_pct, mean_dsci.
- `data/processed/ar1_forecast.csv` — backtest row (2025: actual, AR(1)
  forecast, naive forecast, errors) + 2026 forecast row (point, lower,
  upper).
- `data/processed/data_source.json` — provenance + manual validation.

### 3.6 Fallback, licence, attribution

- No synthetic drought or yield data (brief §4). If USDM is unreachable
  and no committed raw exists, the pipeline fails loudly. County
  aggregates replay from the committed processed file in `--offline`.
- Attribution: "Drought: U.S. Drought Monitor (NDMC/USDA/NOAA).
  Yield: FAO via Our World in Data (CC BY 4.0). Weather: Open-Meteo
  ERA5 archive (CC BY 4.0). County boundaries: US Census Bureau via
  plotly datasets (public domain)." USDA Quick Stats / NOAA GHCN named
  in the README with the reason each was not used live (brief §1).

## 4. Analysis — definitions (from the brief, frozen)

### 4.1 Detrend

- OLS of `yield_t_per_ha` on `year` (all 26 years, sklearn
  LinearRegression). Residual = actual − fitted. Report the trend slope
  (t/ha/yr) in the insights and README.

### 4.2 Correlations

- Pearson r + two-sided p-value via `scipy.stats.pearsonr`; R² = r²;
  OLS slope via `sklearn.linear_model.LinearRegression` on the single
  predictor (residual as y). Slopes: (a) t/ha per DSCI point,
  (b)/(c) t/ha per mm. n = 26 for all three.

### 4.3 Drought-year case studies

- The 3 worst years by `gs_dsci_mean`: for each, yield residual,
  gs DSCI mean, gs precipitation anomaly, and the worst-hit county that
  year (max `gs_d2plus_pct` in `county_year.csv`).

### 4.4 AR(1) forecast

- Fit OLS of `gs_dsci_mean[t]` on `gs_dsci_mean[t−1]` + intercept.
  Backtest on 2025 (fit 2000–2024), then refit on all 26 years for the
  2026 forecast. Interval = forecast ± 1 residual std (in-sample
  residuals of the full fit). Naive baseline = last year's value.
  Report absolute errors for both on 2025.

### 4.5 Hand-validation (tester, §4.4 of the build — record in data_source.json)

- Metric: Iowa 2012 growing-season mean DSCI. Independent recomputation
  from `data/raw/dsci_iowa.csv` (filter MapDate weeks with ValidStart in
  Apr–Sep 2012 — for the state file use MapDate month 4–9 — mean of
  DSCI) vs `annual_drought_yield.csv` Iowa component. Exact match to
  2 decimals required. (Note: the annual table stores the IA+IL mean,
  so the tester validates the Iowa component from the pipeline's
  intermediate — the pipeline must write the per-state annual DSCI
  values to `annual_drought_yield.csv` as `gs_dsci_mean_ia` and
  `gs_dsci_mean_il` columns as well, so the check is against a
  committed number.)

## 5. File tree (exact)

```
day-17-drought-impact-analyzer/
├── README.md  requirements.txt  .gitignore  LICENSE  pyproject.toml
├── .pre-commit-config.yaml
├── research_brief.md  plan.md
├── coder_handoff.md  test_report.md  optimizer_handoff.md  publisher_handoff.md
├── data/
│   ├── README.md
│   ├── raw/            # dsci_iowa.csv, dsci_illinois.csv, maize_yields_owid.csv,
│   │                   # weather_iowa.json, weather_illinois.json (committed)
│   │                   # dsci_counties_*.csv, counties_geo.json (git-ignored)
│   └── processed/      # annual_drought_yield.csv, correlation_results.csv,
│                       # county_year.csv, county_summary.csv, ar1_forecast.csv,
│                       # data_source.json
├── notebooks/analysis.ipynb
├── src/
│   ├── __init__.py
│   ├── data_pipeline.py   # fetch (8 calls) + clean + aggregate + join; --live/--offline/--use-cache
│   ├── analysis.py        # detrend, correlations, case studies, AR(1), county ranking
│   ├── make_charts.py     # 4 charts (§7); GeoJSON fetch + matplotlib choropleth
│   └── app.py             # Streamlit dashboard
├── outputs/
│   ├── insights_summary.md
│   └── charts/            # 01_dsci_trend.png  02_drought_vs_yield.png
│                          # 03_precip_anomaly.png  04_county_map.png
├── screenshots/dashboard.png
└── tests/
    ├── test_pipeline.py
    ├── test_analysis.py
    └── test_smoke.py
```

## 6. Per-file responsibilities

- `src/data_pipeline.py` — only file that touches the network or the raw
  files; writes all 6 processed files; CLI flags `--live/--offline/--use-cache`;
  assertions per §3.2; never writes partial outputs.
- `src/analysis.py` — pure functions over the processed CSVs (detrend,
  correlations, case studies, AR(1), county ranking); no network, no raw
  reads; writes `correlation_results.csv`, `ar1_forecast.csv` (the
  pipeline calls it, or it runs standalone — coder decides, plan §11
  records the choice).
- `src/make_charts.py` — reads processed CSVs only (+ GeoJSON fetch for
  chart 04); writes the 4 PNGs to `outputs/charts/`; every chart has a
  title, labelled axes with units, source line, and a legible font size
  (≥ 9 pt at final size).
- `src/app.py` — Streamlit dashboard: KPI row (worst year, strongest r,
  2026 DSCI forecast), DSCI trend chart, drought-vs-yield scatter,
  county map (matplotlib figure), county ranking table, methods +
  limitations section. Must render without error on a fresh port.
- `notebooks/analysis.ipynb` — reproduces the annual table, the 3
  correlations, the county top-10 and the 4 charts from the processed
  CSVs; root resolved from the notebook file location (AGENTS.md
  lesson e); runs top-to-bottom with 0 error cells.
- `tests/test_pipeline.py` — cleaning/aggregation rules on small
  synthetic frames (DSCI parsing, % sum check, growing-season filter,
  precip aggregation, join row count).
- `tests/test_analysis.py` — detrend residual sums to ~0; Pearson r on a
  known synthetic series; AR(1) forecast on a known series; county
  ranking order on a small frame.
- `tests/test_smoke.py` — processed files exist with expected columns
  and row counts; no NaN in the annual table; charts exist and are
  non-empty PNGs; `data_source.json` has `synthetic: false`.
- `data/README.md` — per-file provenance, the size rule, the git-ignored
  county raw files, and how to regenerate everything with one command.
- `README.md` — problem, audience, the 4 limits (§1), setup, how to run,
  the 3 findings + recommendation, Visuals section with the 4 chart
  images **embedded at build time** (Day 9/16 lesson), Dashboard preview
  with `screenshots/dashboard.png` embedded, limitations, attribution.
- `outputs/insights_summary.md` — 3 findings + 1 actionable
  recommendation, every number matching the committed CSVs.

## 7. Charts (exactly 4, matplotlib, to scale, legible)

1. `01_dsci_trend.png` — line of annual gs DSCI mean (IA+IL avg)
   2000–2025, with the 2012 peak annotated and a horizontal line at
   DSCI = 100; y from 0.
2. `02_drought_vs_yield.png` — scatter of gs DSCI mean (x) vs yield
   residual t/ha (y), OLS fit line, r and p annotated; axes labelled
   with units.
3. `03_precip_anomaly.png` — bars of gs precipitation anomaly (mm) by
   year, blue for wet / brown for dry, with yield residual as a line on
   a secondary axis; 2012 annotated.
4. `04_county_map.png` — choropleth of mean % area in D2+ 2000–2025
   per county (IA + IL, 201 counties), matplotlib polygons from the
   county GeoJSON, colourbar "% of county area in severe+ drought
   (mean, growing season)"; top-3 counties labelled. Fallback (§3.1):
   top-15 county bar chart, labelled as the fallback.

## 8. Success criteria checklist (§8 — all must pass)

- [ ] Problem statement + audience written (README)
- [ ] Data provenance documented (data/README.md)
- [ ] 2+ labelled charts produced (4 produced, §7)
- [ ] 3 findings + 1 actionable recommendation (outputs/insights_summary.md)
- [ ] README with setup instructions, sample outputs, limitations
- [ ] No credentials in the repo; no huge files committed
- [ ] One metric manually validated and recorded (§4.5)
- [ ] Pipeline runs end-to-end from a clean checkout
- [ ] Notebook runs top-to-bottom without errors
- [ ] County map renders (chart 04) with all 201 counties joined by FIPS
- [ ] Detrended (primary) and raw correlations both reported, with p-values
- [ ] AR(1) 2026 forecast labelled as a statistical extrapolation
- [ ] 4 chart images embedded in the day README Visuals section at build time

## 9. Risks & mitigations

- **County raw files too large to commit** — mitigated by the size rule
  (§3.4): processed aggregates committed, raw git-ignored, offline
  replay from processed files.
- **GeoJSON fetch fails at chart time** — mitigated by the labelled
  top-15 bar fallback (§3.1, §7).
- **USDM API slow / 5xx** — one retry after 10 s, then committed cache;
  county calls split into 3 blocks per state so one failure loses a
  block, not the whole fetch.
- **DSCI columns are cumulative, not exclusive** — mitigated by the
  §3.2 rule 2 definition and a test asserting the % sum.
- **Weak correlation (small n)** — report it honestly with the p-value;
  a null result is a finding, not a failure. Do not add variables to
  chase significance.
- **kaleido/plotly static export broken** — no plotly in this day at all;
  all charts are matplotlib.

## 10. Build order

1. Coder: venv + pinned deps → `data_pipeline.py` (fetch + aggregate)
   → run `--live`, verify §3.3 cross-checks → `analysis.py` →
   `make_charts.py` → `app.py` → notebook → README/data README/insights
   → black/ruff/mypy/pytest → handoff.
2. Tester: re-run pytest + coverage, smoke test on a fresh port with a
   real screenshot, hand-validate §4.5, chart legibility check.
3. Optimizer: fix gaps only, re-run gates, update root README/docs.
4. Publisher: frozen-tree check (incl. `data/raw/`), push in 2 batches,
   verify live page renders, hand PNG list to the parent for the browser
   upload.

## 11. Plan-vs-brief differences

- None. The brief's 4 pipeline calls become 8 HTTP calls here (the
  county fetch is split into 3 blocks per state for resilience) — same
  endpoints, same columns.
- The brief said the county GeoJSON "chart code fetches it at chart
  build time with a state-level fallback"; the plan changes the fallback
  to a labelled top-15 county bar chart, because a 2-state choropleth
  carries almost no information and the bar chart preserves the county
  ranking the roadmap asks for.
- The annual table gains `gs_dsci_mean_ia` / `gs_dsci_mean_il` columns
  so the hand-validation metric (§4.5) checks a committed number.
- **DSCI proxy correction (coder, 2026-11-24):** the plan §2.2 wrote the
  county DSCI proxy as 1×D0 + 2×D1 + 3×D2 + 4×D3 + 5×D4, which is the
  USDM definition on *exclusive* shares. The API columns are
  *cumulative*, so the correct proxy is D0 + D1 + D2 + D3 + D4 (max 500).
  The first build used the 1..5 weights on cumulative columns and
  produced Woodbury County IA 2023 gs_dsci = 704 (> 500) — caught by the
  tester-style sanity check, fixed in `county_dsci_proxy`, with a
  regression test (`test_county_dsci_proxy_never_exceeds_500`). State
  DSCI values were never affected (they come from USDM's own GetDSCI).
- **Dropped column (coder, 2026-11-24):** `weeks_any_d2plus` was listed
  in plan §3.5 but has no clean definition from state DSCI alone; the
  county D2+ signal lives in `county_year.csv`. The annual table keeps
  `weeks_dsci_ge100` as its drought-weeks count.
