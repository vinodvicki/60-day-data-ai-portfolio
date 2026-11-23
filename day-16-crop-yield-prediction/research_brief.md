# Day 16 — Crop Yield Prediction: Research Brief

**Status:** VERIFIED — one lean pass, 2026-11-23.
**Business question:** Can USA maize (corn) yield be estimated from historical
harvest, temperature and rainfall data — and how well does the model do on
years it has never seen?

Roadmap entry (Phase 2, Agriculture & Farming): *"Estimate yields using
historical harvest, temperature, and rainfall data, evaluating performance on
held-out years."* Deliverable: crop yield model and driver analysis. Core
skills: regression, weather joins, time-series forecasting, GIS. Suggested
data: USDA Quick Stats; NOAA weather; US Drought Monitor.

## 1. Data sources — verified 2026-11-23 (one pass, no re-search later)

### 1a. Harvest / yield — Our World in Data, "Maize yields" (FAO source data)

- **URL:** `https://ourworldindata.org/grapher/maize-yields.csv?country=USA`
- **Verified:** HTTP 200, 368,479 B, 2026-11-23. Columns
  `Entity,Code,Year,Maize yield`. USA rows 2000–2025: **26 rows, 0 missing**.
  Values in **tonnes per hectare (t/ha)**, FAO (Food and Agriculture
  Organization) via Our World in Data. Spot values: 2000 = 8.592192 t/ha,
  2004 = 10.060836, 2024 = 11.253324, 2025 = 11.705214.
- **Why this instead of USDA Quick Stats:** the roadmap's first suggested
  source, the USDA Quick Stats API
  (`https://quickstats.nass.usda.gov/api/get_counts/?...`), returns
  **HTTP 401 `{"error":["unauthorized"]}`** without an API key — a key needs a
  free USDA signup that cannot be completed from here. The FAO/OWID series is
  the same underlying concept (national maize yield, same units) and is
  keyless, so it is the primary yield source. Record this substitution in the
  README and insights as a disclosed limitation; a future run with a USDA key
  could swap in state-level NASS yields without changing the pipeline shape.
- **Unit conversion (for a familiar bu/acre column):** 1 t/ha = 15.93 bu/acre
  for corn (1 tonne = 39.368 bushels at 56 lb/bu; 1 ha = 2.47105 acres;
  39.368 / 2.47105 = 15.934). Present both units; model in t/ha.

### 1b. Weather — Open-Meteo ERA5 archive API (no key)

- **Base URL:** `https://archive-api.open-meteo.com/v1/archive`
- **Verified:** HTTP 200, no key, 2026-11-23. Two Corn Belt centroids:
  - Iowa: lat 41.8780, lon −93.0977 — 2000-01-01 → 2024-12-31:
    **9,132 days, 0 missing** temperature / precipitation.
  - Illinois: lat 40.6331, lon −89.3985 — 2025-01-01 → 2025-12-31:
    **365 days, 0 missing** (proves the 2025 full year is available).
- **Parameters:** `daily=temperature_2m_mean,temperature_2m_max,precipitation_sum`,
  `timezone=America%2FChicago`, `start_date` / `end_date` per year range.
  Units: °C, mm. Iowa + Illinois are the two largest corn states
  (~35% of US production combined), so their average is the documented
  weather proxy for the national yield series — state this explicitly;
  it is a proxy, not a national weather average.
- **Rate limits:** Open-Meteo archive is free without a key for reasonable
  use; the pipeline makes exactly 2 calls (one per state, 2000–2025) and
  caches the raw JSONs. Retry once after 10 s on a 5xx; stop after that and
  fall back to the committed cache (`--offline` / `--use-cache`).

### 1c. Cross-check / context only (NOT used as model inputs)

- **NOAA GHCN-daily** (`https://www.ncei.noaa.gov/pub/data/ghcn/daily/all/USW00014933.dly`,
  Des Moines station): HTTP 200, 5,106,240 B, 2026-11-23 — public, no key.
  Recorded as the roadmap's "NOAA weather" cross-check; not fetched by the
  pipeline (Open-Meteo already supplies the same daily fields, and a 5 MB
  station file is needless weight).
- **US Drought Monitor** comprehensive-statistics page
  (`https://droughtmonitor.unl.edu/DmData/DataDownload/ComprehensiveStatistics.aspx`):
  HTTP 200, 2026-11-23 — but its data download needs an interactive form, so
  no machine-readable drought series is used. The roadmap entry asks for
  temperature + rainfall only; drought severity is out of scope for this day
  (it is Day 17's subject) and is noted as a future feature, not built.
- **FAOSTAT API** (`https://fenixservices.fao.org/faostat/api/v1/...`):
  HTTP 521 (Cloudflare) on 2026-11-23 — unavailable; the OWID mirror of the
  same FAO data is used instead.

## 2. Metrics to compute

- **Held-out evaluation (required):** train on 2000–2019 (20 years), evaluate
  on held-out 2020–2025 (6 years). Never fit on the held-out years.
- **Metrics on the held-out years:** RMSE (t/ha and bu/acre), MAE, R²,
  mean bias (mean predicted − mean actual). Also report the same metrics
  in-sample (train) for contrast — a model that is great in-sample and poor
  held-out is overfit, and that must be said.
- **Baseline to beat:** naive "last-year yield" and "train-mean yield"
  forecasts on the held-out years (a model that cannot beat the mean is not
  a model).
- **Models:** ordinary least squares (interpretable baseline), Ridge
  (regularised linear), RandomForestRegressor (non-linear, seed 42).
  All three trained on the same features and split; the best held-out RMSE
  wins, ties go to the simpler model.
- **Driver analysis:** standardised OLS coefficients; Pearson correlation of
  each weather feature with yield; RandomForest permutation importance
  (seed 42). Report drivers in plain language with the sign of each effect.
- **Features (all from the verified sources above, growing season Apr–Sep
  unless noted):** `year` (technology trend), `gs_temp_mean` (°C),
  `gs_precip_total` (mm), `jul_temp_mean` (°C), `jul_precip_total` (mm),
  `jun_precip_total` (mm), `heat_days_gs` (days with daily max > 30 °C).
  7 features, 20 training rows — small-n is a disclosed limitation;
  do not add more features to "fill" the model.

## 3. Licence / attribution

- OWID maize yields: FAO data republished by Our World in Data, CC BY 4.0 —
  attribute "FAO via Our World in Data".
- Open-Meteo: ERA5 reanalysis via Open-Meteo, CC BY 4.0 — attribute
  "Open-Meteo (ERA5)". No key, no account.
- USDA Quick Stats / NOAA / US Drought Monitor: named as the roadmap's
  suggested sources in the README with the reason each was not used live
  (key required / cross-check only / form-only download).

## 4. Synthetic-fallback note

- **No synthetic yields.** If the OWID CSV is unreachable at build time,
  the pipeline stops with a clear error — fabricating a harvest series
  would make the whole day meaningless. The committed raw CSV is the
  provenance record; `--offline` replays from it.
- Weather fallback: if Open-Meteo fails, replay from the committed raw
  JSONs (`--offline`). Same rule as Days 1–15: raw data is committed
  (< 1 MB/file, < 5 MB/day) and `data_source.json` records
  `synthetic: false`.

## 5. Verification status

- [x] Endpoints confirmed with live HTTP probes, 2026-11-23 (OWID 200,
  Open-Meteo 200 × 2 states, NOAA GHCN 200, Drought Monitor page 200,
  USDA Quick Stats 401 without key, FAOSTAT 521).
- [x] Conflicts recorded: USDA Quick Stats needs a key (→ OWID/FAO
  substitution, disclosed); FAOSTAT API down (→ OWID mirror of the same
  FAO data); Drought Monitor not machine-readable (→ out of scope, Day 17).
- [x] No live fetch by the researcher — the coder fetches once, from the
  URLs and parameters above, and commits the raw files.

## Handoff to the planner

- **Next role's first step:** read §1–§2 above and the roadmap entry; the
  file tree follows the Day 15 pattern (src/data_pipeline.py,
  src/model.py, src/make_charts.py, src/app.py, tests, notebooks,
  data/raw + data/processed, outputs/charts, screenshots).
- **Files produced:** `research_brief.md` (this file).
- **Known gaps:** state-level yields unavailable without a USDA key
  (national series used instead); weather is a 2-state Corn Belt proxy,
  not a national average; 26 annual rows is a small sample — the plan
  must carry these as disclosed limitations, not hide them.
