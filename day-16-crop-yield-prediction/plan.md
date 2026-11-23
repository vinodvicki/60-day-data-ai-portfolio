# Day 16 — Crop Yield Prediction: Build Plan

**Status:** PLAN — planner sign-off complete (AGENTS.md, stage 2).
**Source of truth:** `research_brief.md` (2026-11-23) + this plan. **If brief
and plan disagree, the plan wins and the difference is noted in §11.** The
coder must reuse the brief + this plan. **No extra web searches.**
**Roadmap entry (verbatim):** "Estimate yields using historical harvest,
temperature, and rainfall data, evaluating performance on held-out years.
GitHub deliverable: Crop yield model and driver analysis."
**Core skills:** Regression, weather joins, time-series forecasting, GIS.
**Suggested data:** USDA Quick Stats; NOAA weather; US Drought Monitor.

| Item | Value |
|---|---|
| Fetch date | 2026-11-23 |
| Yield source | Our World in Data "Maize yields" CSV (FAO data), USA, 2000–2025, 26 rows, 0 missing, t/ha — `https://ourworldindata.org/grapher/maize-yields.csv?country=USA` |
| Weather source | Open-Meteo ERA5 archive API, no key — Iowa (41.8780, −93.0977) + Illinois (40.6331, −89.3985) centroids, daily `temperature_2m_mean`, `temperature_2m_max`, `precipitation_sum`, 2000–2025 |
| Crop / geography | Maize (corn), United States (national yield) with a 2-state Corn Belt weather proxy (Iowa + Illinois average) |
| Split | Train 2000–2019 (20 years); held-out 2020–2025 (6 years). Never fit on held-out years. |
| Models | OLS (baseline), Ridge, RandomForestRegressor (seed 42) — same features, same split; best held-out RMSE wins, ties go to the simpler model |
| Deliverable | Crop yield model and driver analysis (README + `outputs/insights_summary.md` + Streamlit dashboard + 4 charts + notebook) |
| Scope | Regression on annual data only. No county/state yield model (no USDA key — brief §1a), no drought model (Day 17), no price or forecast-beyond-2025 claims. The 2026 yield is NOT predicted — there is no 2026 harvest yet. |

## 1. Problem statement + audience

**Problem.** A grower, buyer or planner who wants to know what drives the US
corn harvest has the yield history and the weather history in two different
places, in different units and shapes. This project joins them once, in the
open: 26 years of national maize yield (FAO via Our World in Data) against
growing-season temperature and rainfall for the Corn Belt (Iowa + Illinois,
Open-Meteo ERA5), fits three regression models on 2000–2019, and scores them
on six years they never saw (2020–2025) — with the drivers (which weather
variables matter, and in which direction) shown alongside the errors, so the
reader can judge whether the model earns trust.

**Four hard limits, stated up front and labelled on every surface (README,
notebook, insights, dashboard, charts):**

1. **National yield, 2-state weather proxy.** The yield is the USA national
   figure; the weather is the average of two Corn Belt centroids, not a
   national weather average. Iowa + Illinois are ~35% of US corn output, so
   the proxy is reasonable, but it is a proxy — say so wherever the weather
   features are described.
2. **Small sample — 26 annual rows.** Seven features on 20 training years is
   a small-n regression. Report the uncertainty (held-out errors, confidence
   language) and do not add features to "fill" the model. No claim stronger
   than the held-out numbers support.
3. **Association, not causation.** A weather variable that moves with yield
   is a driver in the statistical sense only. No "rain causes yield" claims;
   allowed language: "associated with", "moves with", "explains X% of the
   held-out variance".
4. **No USDA state data in this build.** The roadmap's suggested USDA Quick
   Stats API needs a key (HTTP 401 without one, brief §1a), so state-level
   yields are out of scope. The README records the substitution and the
   exact step a future run would take with a key.

**Audience / decision-maker.** A farm planner or data reviewer who wants a
reproducible yield model: the exact sources and URLs, the feature
definitions, the train/held-out split, all three models scored the same way,
the baselines they must beat, and every published number matching the
committed CSVs.

## 2. Decisions (frozen)

### 2.1 Research questions (exactly 3)

1. How accurately can 2020–2025 US maize yields be estimated from
   growing-season temperature and rainfall (plus a time trend), and which
   of OLS / Ridge / Random Forest does best on those held-out years?
2. Which weather drivers matter most — growing-season heat, July heat,
   June/July rainfall, heat days — and in which direction?
3. Does any model beat the naive baselines (last-year yield, train-mean
   yield) on the held-out years, and by how much?

### 2.2 Other frozen decisions

- **Units:** model in t/ha; show bu/acre alongside (1 t/ha = 15.93 bu/acre,
  brief §1a). Every table/chart that shows yield gives both units at least
  once; the dashboard KPI shows t/ha primary, bu/acre secondary.
- **Growing season:** April–September inclusive (corn growing season in the
  Corn Belt). July is the silking month — July temperature/rainfall get
  their own features. June rainfall gets its own feature (early growth).
- **Features (exactly 7, frozen):** `year`, `gs_temp_mean`,
  `gs_precip_total`, `jul_temp_mean`, `jul_precip_total`,
  `jun_precip_total`, `heat_days_gs` (days Apr–Sep with daily max > 30 °C).
  Feature values are the Iowa/Illinois average. No other features.
- **Baselines (frozen):** `naive_last` (predict this year's yield = last
  year's actual) and `naive_mean` (predict = train-period mean yield),
  scored on the same 6 held-out years with the same metrics.
- **Winner rule:** lowest held-out RMSE; if two models are within 0.01 t/ha
  RMSE, the simpler one wins (OLS > Ridge > Random Forest).
- **Charts:** exactly 4, matplotlib, to scale and legible (§7). The GIS
  element is chart 04 (station map via plotly `scatter_geo`, built-in base
  map — no shapefile download).
- **No 2026 prediction.** The 2025 harvest is the latest actual; the model
  is evaluated, not used to forecast an unobserved year.
- **Dependencies:** reuse the Day 11 verified pins (pandas 3.1.1, numpy
  2.5.4, matplotlib 3.11.2, plotly 7.1.0, streamlit 1.66.1, requests
  2.34.2, pytest 9.2.0, jupyter 1.1.1, nbformat 5.11.1,
  scikit-learn 1.9.1, scipy 1.18.1). No statsmodels, no geopandas, no new
  dependency without a plan change.

## 3. Data — source, endpoints, fetch rules, provenance, licence

### 3.1 Source and download (verified, from the brief — copy, do not re-search)

- **Yields:** GET `https://ourworldindata.org/grapher/maize-yields.csv?country=USA`
  (HTTP 200, 368,479 B at probe time). Filter `Entity == "United States"`,
  keep `Year, Maize yield` for 2000–2025. Expect 26 rows, 0 missing.
  Raw file committed as `data/raw/maize_yields_owid.csv` (the full CSV as
  downloaded — it contains all countries; the pipeline filters to USA).
- **Weather:** GET `https://archive-api.open-meteo.com/v1/archive` twice
  (Iowa, Illinois), params `latitude`, `longitude`,
  `start_date=2000-01-01`, `end_date=2025-12-31`,
  `daily=temperature_2m_mean,temperature_2m_max,precipitation_sum`,
  `timezone=America%2FChicago`. Expect 9,497 days per state (2000–2025
  incl. leap years), 0 missing. Raw files committed as
  `data/raw/weather_iowa.json`, `data/raw/weather_illinois.json`.
  Exactly 3 HTTP calls total (1 yield + 2 weather). One retry after 10 s
  on a 5xx, then stop and fall back to the committed cache.
- **Pipeline modes:** `--live` (default: fetch, then build),
  `--offline` (replay from committed raw files, no network),
  `--use-cache` (use raw files if present, else fetch). The offline run
  must reproduce the processed files byte-for-byte except `data_source.json`
  timestamps (tester checks this).

### 3.2 Cleaning rules (frozen — the tester tests these)

1. Yield: drop rows outside 2000–2025; assert 26 rows, `yield_t_per_ha`
   float, no NaN, strictly positive, strictly increasing `year`.
2. Weather: parse `daily.time` to dates; assert each state covers
   2000-01-01–2025-12-31 with no missing days and no nulls in the three
   daily fields; precipitation < 0 → error (never silently clipped).
3. Aggregation per state per year: `gs_temp_mean` = mean of daily mean temp
   Apr–Sep; `gs_precip_total` = sum of daily precip Apr–Sep;
   `jul_temp_mean` = mean daily mean temp in July; `jul_precip_total` =
   sum daily precip in July; `jun_precip_total` = sum daily precip in June;
   `heat_days_gs` = count of Apr–Sep days with daily max > 30.0 °C.
   Then average the two states (simple mean) per feature per year.
4. Join: inner join on `year` (26 rows expected). Add `yield_bu_per_acre`
   = `yield_t_per_ha` × 15.932 (rounded in display only, never in the
   stored value). Add `split` column: `train` for 2000–2019,
   `heldout` for 2020–2025.
5. No imputation anywhere. A failed assertion stops the pipeline with a
   clear message — it never writes partial processed files.

### 3.3 Cross-checks (frozen — run before the tester starts)

- Row counts: yields 26, weather days 9,497/state, joined 26 (20 train +
  6 held-out).
- 2024 yield in the processed file equals the OWID value 11.253324 t/ha
  (the tester's hand-validation metric, §4.4).
- Feature spot-check: the pipeline's `gs_precip_total` for Iowa 2012
  (drought year) is lower than for Iowa 2010 — 2012 was the driest of the
  two in the Corn Belt; the tester verifies the direction, not a number
  from memory.

### 3.4 Data-size and commit rule (READ CAREFULLY)

Small raw data IS committed: raw files under 1 MB each, under 5 MB per day.
Expected: `maize_yields_owid.csv` ~369 KB, two weather JSONs ~210 KB each —
total raw ~790 KB. `.gitignore` must NOT exclude `data/`. Processed files
are all < 1 MB. `data_source.json` records source URLs, fetch date,
row counts, `synthetic: false`, and the manual-validation section (added
by the tester, §4.4 — a `--live` re-run drops it; do NOT re-run `--live`
after the tester fills it).

### 3.5 Committed processed files (all < 1 MB; regenerable with one command)

- `data/processed/yield_weather.csv` — 26 rows: year, yield_t_per_ha,
  yield_bu_per_acre, 7 features, split.
- `data/processed/model_results.csv` — one row per model (OLS, Ridge, RF)
  + 2 baselines: held-out RMSE/MAE/R²/bias in t/ha and bu/acre, train
  RMSE/R².
- `data/processed/heldout_predictions.csv` — 6 rows: year, actual,
  predicted per model + baselines.
- `data/processed/driver_importance.csv` — per feature: Pearson r with
  yield, standardised OLS coefficient, RF permutation importance (mean).
- `data/processed/data_source.json` — provenance + manual validation.

### 3.6 Fallback, licence, attribution

- No synthetic yields (brief §4). If OWID is unreachable and no committed
  raw exists, the pipeline fails loudly. Weather replays from cache.
- Attribution: "Yield: FAO via Our World in Data (CC BY 4.0). Weather:
  Open-Meteo ERA5 archive (CC BY 4.0)." USDA Quick Stats / NOAA / US
  Drought Monitor named in the README with the reason each was not used
  live (brief §1).

## 4. Analysis — definitions (from the brief, frozen; planner decisions in §11)

### 4.1 Models (DECIDED — exact)

- **OLS:** `sklearn.linear_model.LinearRegression` on the 7 features,
  fit on train only. Standardised coefficients computed by refitting on
  z-scored features (train mean/std) for the driver table.
- **Ridge:** `sklearn.linear_model.Ridge(alpha=1.0)`, features
  standardised with `StandardScaler` fit on train only.
- **Random Forest:** `sklearn.ensemble.RandomForestRegressor(
  n_estimators=300, random_state=42, n_jobs=1)` on raw features.
  (`n_jobs=1`, not `-1`: parallel tree prediction sums in a
  thread-dependent order and changes the held-out RMSE in the last ulp
  between runs; with 20 rows the serial fit costs nothing and the result
  is bit-identical every run. Coder change from the plan's `-1`, noted
  in §11.)
- **Baselines:** `naive_last`, `naive_mean` as defined in §2.2.
- All models output predictions for the 6 held-out years; metrics are
  computed from `heldout_predictions.csv`, never from in-memory values
  that differ from the file.

### 4.2 Metrics (DECIDED — exact)

- Held-out: RMSE = sqrt(mean((pred − actual)²)), MAE = mean(|pred − actual|),
  R² = 1 − SS_res/SS_tot (on the 6 held-out points), bias = mean(pred −
  actual). Report in t/ha and in bu/acre (× 15.932). Train: RMSE and R²
  on the 20 training years.
- Winner by §2.2 rule. The README/insights/dashboard all name the same
  winner with the same held-out RMSE to 3 decimals.

### 4.3 Driver analysis (DECIDED — exact)

- Pearson r between each feature and `yield_t_per_ha` over all 26 years
  (with the n=26 caveat stated).
- Standardised OLS coefficients (fit on z-scored features, train years).
- RF permutation importance: `sklearn.inspection.permutation_importance`
  on the held-out set, `n_repeats=30`, `random_state=42`, scoring
  `neg_root_mean_squared_error`; report mean importance per feature.
- Plain-language driver sentence per feature in the insights summary,
  with the sign of the effect and the caveat from §1 (association only).

### 4.4 Hand-validation metric (DECIDED — the tester checks exactly this)

- **2024 USA maize yield = 11.253324 t/ha** (= 179.28 bu/acre at
  15.932). The tester recomputes it by hand from the committed raw CSV
  (`csv` + `math` only, no pipeline code): filter `United States`, year
  2024, read the value, convert. Diff must be 0. Recorded in
  `data_source.json` under `manual_validation` (yield value, bu/acre,
  diff 0.0).

### 4.5 Insights structure (DECIDED)

`outputs/insights_summary.md` has exactly these sections: headline finding
(winner + held-out RMSE), the three research questions answered with
numbers, driver table in words, baselines beaten (or not), limitations
(§1 four limits), what to do next (USDA key → state-level yields;
drought features → Day 17). Every number verified against the committed
CSVs by the optimizer.

## 5. File tree (exact — build only this)

```text
day-16-crop-yield-prediction/
├── README.md                      # day README (template → filled)
├── research_brief.md              # stage 1 (done)
├── plan.md                        # this file (stage 2)
├── coder_handoff.md               # stage 3 handoff
├── test_report.md                 # stage 4 report
├── optimizer_handoff.md           # stage 5 handoff
├── publisher_handoff.md           # stage 6 handoff (local-only, never pushed)
├── LICENSE                        # scaffold
├── .gitignore                     # scaffold, checked vs §5 list below
├── .pre-commit-config.yaml        # scaffold
├── pyproject.toml                 # scaffold (strict mypy, coverage src)
├── requirements.txt               # pinned at optimizer time from the venv
├── data/
│   ├── README.md                  # provenance + size rule + attribution
│   ├── raw/
│   │   ├── maize_yields_owid.csv  # OWID download, all countries
│   │   ├── weather_iowa.json      # Open-Meteo raw, Iowa
│   │   └── weather_illinois.json  # Open-Meteo raw, Illinois
│   └── processed/
│       ├── yield_weather.csv
│       ├── model_results.csv
│       ├── heldout_predictions.csv
│       ├── driver_importance.csv
│       └── data_source.json
├── notebooks/
│   └── analysis.ipynb             # _find_root from notebook location; 0 errors
├── outputs/
│   ├── insights_summary.md
│   └── charts/
│       ├── 01_yield_history.png
│       ├── 02_actual_vs_predicted.png
│       ├── 03_feature_drivers.png
│       └── 04_weather_stations_map.png
├── screenshots/
│   └── dashboard.png              # REAL Streamlit capture (tall viewport)
├── src/
│   ├── __init__.py                # scaffold
│   ├── data_pipeline.py           # fetch → clean → features → join → save
│   ├── model.py                   # train/score 3 models + 2 baselines
│   ├── make_charts.py             # 4 charts from processed CSVs only
│   └── app.py                     # Streamlit dashboard, processed CSVs only
└── tests/
    ├── test_smoke.py              # scaffold smoke test (keep, extend if needed)
    └── test_pipeline.py           # pipeline/model/chart contract tests
```

`.gitignore` (exact list — must match): `__pycache__/`, `.venv/`, `venv/`,
`.env`, `*.key`, `*.log`, `.streamlit/secrets.toml`, `.pytest_cache/`,
`.mypy_cache/`, `.ipynb_checkpoints/`. Must NOT exclude `data/`.

## 6. Per-file responsibilities

- `src/data_pipeline.py` — `fetch_yields()`, `fetch_weather(state)`,
  `build_features(daily)`, `build_dataset()`, `main()` with
  `--live/--offline/--use-cache`; writes processed CSVs + data_source.json;
  asserts §3.2/§3.3; no model code.
- `src/model.py` — `train_models(df)`, `evaluate(...)`, `baselines(df)`,
  `driver_analysis(df, models)`; writes `model_results.csv`,
  `heldout_predictions.csv`, `driver_importance.csv`; `main()` runnable
  standalone after the pipeline. Deterministic (seed 42 everywhere).
- `src/make_charts.py` — reads processed CSVs only; `main()` writes the
  4 charts (§7); no network, no model code.
- `src/app.py` — Streamlit; reads processed CSVs only; sidebar year-range
  + model selector; KPIs (winner, held-out RMSE, 2024 yield); the 4 charts
  + held-out table + limitations box. Must render with no exceptions.
- `tests/test_pipeline.py` — offline pipeline reproduction; feature
  definitions on a fixed toy daily frame; split counts (20/6); metric
  formulas on toy arrays; model determinism (same seed → same RMSE);
  chart files exist + non-empty; forbidden-claim grep (no "causes",
  no "predicts 2026", no "USDA" as a used source); data-size rule.
- `notebooks/analysis.ipynb` — EDA + join + models + drivers + charts,
  `_find_root()` from the notebook file location, executed end-to-end
  with 0 errors.

## 7. Charts (exactly 4, matplotlib except 04, to scale and legible)

1. `01_yield_history.png` — line of `yield_t_per_ha` 2000–2025, train
   region vs held-out region shaded and labelled, OLS trend line
   (train years only), annotation of 2012 dip and 2025 value. Y-axis from
   0 is NOT required (values 8–12); axis must start ≤ 7 and be labelled
   in t/ha with bu/acre in the subtitle. No truncated bars (line chart).
2. `02_actual_vs_predicted.png` — held-out 2020–2025: grouped bars or
   lines, actual vs winner-model predicted vs naive-last, with RMSE
   annotated per model. Y-axis to scale, legend legible.
3. `03_feature_drivers.png` — horizontal bars: standardised OLS
   coefficient per feature (signed, zero line drawn) with Pearson r
   annotated beside each bar. Title states "association, not causation".
4. `04_weather_stations_map.png` — plotly `scatter_geo` (scope="usa"):
   Iowa + Illinois centroid markers, labelled with state + lat/lon,
   title "Corn Belt weather proxy — 2 stations". Saved as PNG via
   `plotly.io.write_image` (kaleido) or, if kaleido is unavailable,
   matplotlib lon/lat scatter with state labels — planner decision: try
   kaleido first; the coder records which route was used. No shapefile
   download either way.

## 8. Success checklist (roadmap minimum success criteria — all must pass)

1. [ ] Roadmap entry followed exactly: yields estimated from historical
   harvest + temperature + rainfall; performance evaluated on held-out
   years; deliverable is a crop yield model + driver analysis.
2. [ ] Data provenance: raw files committed (3 files, < 1 MB each);
   `data_source.json` records URLs, fetch date, row counts,
   `synthetic: false`, manual validation (§4.4).
3. [ ] Split respected: models fit on 2000–2019 only; held-out metrics
   computed on 2020–2025; no leakage (scaler/standardisation fit on
   train only — a test asserts this).
4. [ ] Three models + two baselines scored with RMSE/MAE/R²/bias on the
   held-out years; winner named by the §2.2 rule and consistent across
   README, insights, notebook, dashboard.
5. [ ] Driver analysis present: Pearson r + standardised coefficients +
   RF permutation importance, with association-not-causation language.
6. [ ] 4 charts, to scale, legible; GIS station map present.
7. [ ] Notebook executes with 0 errors (nbconvert exit 0).
8. [ ] Tests: pytest passes from repo root AND from inside the day
   folder; coverage ≥ 30 (`--cov=src --cov-fail-under=30`); black +
   ruff + mypy clean (strict-by-default, run from inside the day folder).
9. [ ] Streamlit smoke: fresh port (8502+), HTTP 200 on `/` and
   `/_stcore/health`, REAL `screenshots/dashboard.png` (tall viewport
   capture), server killed, port verified free.
10. [ ] Orchestrator validate 11/11; no secrets; `.gitignore` matches §5;
    README + insights numbers verified against the committed CSVs.
11. [ ] Publisher frozen-tree check + live GitHub page renders (stage 6).

## 9. Coder handoff checklist (reference — coder must satisfy all of these before the tester starts)

venv exists with pinned deps installed; black + ruff clean; mypy clean
(run from inside the day folder); pytest passes with coverage ≥ 30;
`.gitignore` matches the plan; `screenshots/dashboard.png` is a real
capture of the running app; notebook executes 0 errors; pipeline `--offline`
reproduces processed files; `data_source.json` not clobbered.

## 10. Risks & mitigations

- **OWID CSV unreachable at build time** → pipeline fails loudly; the
  committed raw from the researcher's probe (`/tmp/maize.csv`) is NOT
  reused silently — if the coder must seed from it, the handoff must say
  so explicitly and the file must be re-verified (row count 26, 2024 value
  11.253324) before use. Preferred: live fetch.
- **Open-Meteo 5xx** → one retry after 10 s, then cache/offline. The
  researcher already verified both endpoints return 200.
- **Random Forest overfits 20 rows** → expected; the held-out metrics will
  show it, and the winner rule + baselines make the verdict honest. Do
  not tune hyperparameters to chase the held-out score (that leaks the
  test set); hyperparameters are frozen in §4.1.
- **kaleido missing for chart 04** → matplotlib fallback (§7.4); either
  route is acceptable, the coder records which one ran.
- **Small-n R² on 6 points is noisy** → report RMSE/MAE as the primary
  metrics; R² is secondary and labelled as such.

## 11. Differences from the brief (plan wins)

- None material. The brief's feature list (§2) is adopted verbatim (§2.2).
  Two clarifications, not disagreements: (a) the growing season is fixed
  to April–September and July/June get their own features (§2.2) — the
  brief named the features but not the window; (b) the winner rule
  (§2.2) and the baselines are planner additions required to make "does
  the model beat naive?" answerable.
- Coder deviation (recorded, plan updated §4.1): Random Forest uses
  `n_jobs=1` instead of the planned `n_jobs=-1`, because parallel
  prediction changed the held-out RMSE in the last ulp between runs.
  Results are bit-identical across runs now; the fitted model is unchanged
  (same seed, same trees).
