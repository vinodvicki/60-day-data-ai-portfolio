# Test report — Day 09 Healthcare Resource Demand Forecast

**Stage:** tester (role 4 of 6) → optimizer. **Date:** 2026-11-13.
**Day folder:** `~/workspace/goals/60-day-data-ai-portfolio/day-09-healthcare-resource-demand-forecast/`
**Venv:** `.venv` present, Python 3.12.3, pinned deps installed (no reinstall done).
**Verdict: PASS with 4 defects** — 1 substantive numeric error (D-1) + 3 minor
(D-2, D-3, D-4). No gate failed outright; all gates below passed with exact
numbers. The optimizer's first step is fixing D-1 (see bottom).

## Gate results (all verified independently, not trusted from the handoff)

### 1. py_compile — PASS
- Command: `.venv/bin/python -m py_compile src/__init__.py src/data_pipeline.py src/forecast.py src/metrics.py src/make_charts.py src/app.py`
- Exit code **0**, all 6 files compile.

### 2. pytest — PASS, 37 passed (both locations)
- Day folder: `.venv/bin/python -m pytest tests/ -q` → **37 passed in 18.01 s**, exit 0.
- Portfolio root: `day-09-.../.venv/bin/python -m pytest day-09-healthcare-resource-demand-forecast/tests/ -q` → **37 passed in 14.80 s**, exit 0.
- Only `tests/test_pipeline.py` exists; scaffold `test_smoke.py` is deleted.

### 3. black + ruff — PASS
- `.venv/bin/python -m black --check src tests` → "All done! 7 files would be left unchanged", exit 0.
- `.venv/bin/python -m ruff check src tests` → "All checks passed!", exit 0.

### 4. Pipeline `--offline` reproducibility — PASS
- Command: `.venv/bin/python -m src.data_pipeline --offline` → exit 0, printed
  "offline: derived forecast tables regenerated from committed CSVs; data_source.json untouched (source='live')" and
  "backtest mean RMSE — holt_winters 0.4693, seasonal_naive 0.8244 -> published method: holt_winters".
- sha256 of all 7 processed files verified identical before/after (via
  `sha256sum -c`, all OK), including `data_source.json`
  (`e4f65c55037c0ebfec164957c05e225e3c57230b8e9801f42827a1e02cb9fed1`).
- `data_source.json` still records `source: "live"`, `synthetic: false`,
  `nssp_rows: 25116`, `bed_rows: 81713`, `fetch_date: 2026-11-13`,
  `national_weeks: 161`, `bed_weeks: 226`, null audit 72 rows
  (Iowa 54 / Delaware 9 / Georgia 9, 0 national weeks affected).

### 5. Notebook — PASS, 0 error cells (raw-absent mode)
- Command: `.venv/bin/python -m jupyter nbconvert --to notebook --execute notebooks/analysis.ipynb --output-dir /tmp/day09_nb --output analysis_executed.ipynb` → exit 0.
- Executed copy: **16 cells, 0 error cells**. Raw JSONs are absent on disk, so
  this is the guarded no-raw path (forecast loaded from committed CSVs, not
  re-run). The committed notebook was NOT modified by this run (executed to
  `/tmp/day09_nb/`).

### 6. Streamlit smoke gate — PASS (fresh port 8502)
- Started `.venv/bin/python -m streamlit run src/app.py --server.port 8502 --server.headless true`.
- `GET /` → **HTTP 200**; `GET /_stcore/health` → **HTTP 200, body "ok"**.
- Server log (`/tmp/day09_streamlit.log`) clean — no errors, tracebacks or
  exceptions.
- Real full-page screenshot captured with system Playwright/Chromium
  (tall viewport 1200×6100, `stMain` scrollHeight 6082) and written over the
  coder's file: `screenshots/dashboard.png`, **1200×6100, 905,025 bytes**
  (coder's was 1200×5957, 974,008 bytes). Viewed in full: title, 4 metric
  cards, chart 01 + forecast table, backtest chart + table, bands chart +
  state comparison (Florida), bed chart + staffing table, volume converter,
  methods/limitations, attribution footer — all render, no blank sections,
  no errors.
- Server killed; port 8502 verified free afterwards (`curl` exit 7,
  connection refused; no streamlit process remains).

### 7. Hand validation (independent recomputation from committed CSVs) — PASS, diff 0.0
- Latest week (2026-10-31): 0.5 + 1.7 + 0.1 = **2.3%** Combined vs CSV
  `combined_pct` 2.3 → **diff 0.0**.
- Final bed week (2024-04-27): 3,604,488 / 4,808,901 = **0.7495** vs CSV
  `bed_utilisation` 0.7495 → **diff 0.0**; ICU 0.7165, diff 0.0.
- Also recomputed: observed max Combined **10.4%** (2023-12-30); national
  series 161 rows, 0 NULLs; band counts Low 89 / Moderate 35 / High 19 /
  Surge 18 (total 161); HW mean RMSE 0.4693 vs naïve 0.8244; HW mean
  80%-coverage 75.0% vs naïve 91.67%; bed mean utilisation 72.47% → 72.5%,
  max 78.88% → 78.9% (2022-12-10); top-5 latest-4-week means Hawaii 7.02,
  Florida 3.42, Louisiana 2.88, Washington 2.80, Texas 2.58 (→ 7.0/3.4/2.9/
  2.8/2.6% as published); state series 8,187 rows = 51×161 − 24 NULL
  state-weeks, consistent with the 72-row NULL audit.

### 8. Chart legibility — PASS with D-2, D-3 noted
- All 4 charts in `outputs/charts/` viewed at full size (1787 px wide):
  legible, to scale, no truncated axes, footnotes agree with the data except
  D-2/D-3 below.
- 01_forecast: history + 8-week forecast with shaded intervals, band labels
  per forecast week, "Latest: 2.3% (week ending 2026-10-31)" annotation
  readable. Forecast values 3.03 → 13.87 match `forecast.csv`; final-week
  intervals 12.76–14.91 (80%) / 12.08–15.38 (95%) match.
- 02_backtest: per-origin RMSE bars match `backtest.csv` (HW 0.49/0.59/0.32;
  naïve 0.98/0.39/1.11); coverage panel matches (HW 75/50/100%;
  naïve 100/100/75%); 80% target line present; title "Holt Winters wins on
  mean RMSE (0.47 pp)" correct.
- 03_demand_bands: threshold lines 2/4/6%, title states observed max 10.4%
  and Surge 18 of 161 weeks; top-5 bars match recomputed values above.
- 04_bed_capacity: bed + ICU lines, series-end annotation 2024-04-27,
  staffing table (Low baseline / Moderate baseline-monitor / High +10% /
  Surge +25% + elective deferral) with "PLANNING ASSUMPTIONS — not measured
  data" label. The ICU line's plunge to 0% in Jul 2020 is the real committed
  value (week 2020-07-11, `icu_occupancy` exactly 0.0, 7 states reporting),
  disclosed in `data/README.md` lines 82–83; the chart footnote covers thin
  2020 reporting generally.

### 9. .gitignore / sizes / references — PASS
- `.gitignore` matches plan §3.4 exactly: scaffold defaults
  (`__pycache__/`, `*.pyc`, `.pytest_cache/`, `.venv/`, `venv/`, `.env`,
  `*.key`, `*.log`, `.streamlit/secrets.toml`, `.ipynb_checkpoints/`) plus
  the three raw-data lines (`data/raw/nssp_ed_visits.json`,
  `data/raw/bed_capacity.json`, `data/raw/*_synthetic.json`).
- No committed file > 1 MB (largest is now the tester screenshot, 905,025
  bytes; notebook 870,427; sample 798,920). `data/` total **1,132,954 bytes**
  (< 5 MB).
- Every file the READMEs reference exists on disk (README.md 9 refs, 0
  missing; insights_summary.md 4 refs, 0 missing). The 3 "missing" refs in
  `data/README.md` (`data/raw/nssp_ed_visits.json`, `bed_capacity.json`,
  `*_synthetic.json`) are the git-ignored raw files, intentionally absent at
  handoff per plan §3.4/§5 and documented as such (lines 113–114, 130) — not
  a defect.
- `data/raw/sample_rows.json`: 1,000 NSSP + 100 bed rows as claimed.
  `LICENSE` present. No `.pbix`, no `weekly_briefing.md`, no `test_smoke.py`,
  no extra files beyond the plan §5 tree.

### 10. README / insights spot-check — PASS except D-1
- Forecast table, band counts, backtest RMSEs/MAEs/MAPEs/coverages, top-5
  states, bed mean/max/latest, NULL audit, and the >observed-max disclosure
  all match the committed CSVs / `data_source.json`.
- >observed-max disclosure verified as honest and prominent: README.md
  lines 36, 67; `outputs/insights_summary.md` lines 9, 27, 32; notebook
  cell 5; dashboard text under the forecast table and in Methods &
  limitations. Intervals are sane: 80% width grows 0.63 → 2.15 pp and 95%
  width 1.57 → 3.30 pp from week 1 to week 8. No retune needed (plan-fixed
  method).
- Bed coverage redefinition verified: `*_coverage` columns are hospital
  counts, full coverage = `inpatient_beds_coverage ==
  inpatient_beds_used_coverage` (both > 0), 86.36% of state-days, 11,145
  dropped — documented in `data/README.md`, `data_source.json`
  (`bed_coverage` block) and the pipeline docstring.
- ConvergenceWarning suppression verified: `src/forecast.py` lines 88–94,
  recorded in `data/README.md` lines 103–106.
- Notebook's interval-width claim (95% width 1.57 pp week 1 → 3.30 pp week
  8) recomputed and correct.
- Insights line 15 per-origin coverage figures check out (HW 0.75/0.50/1.00;
  naïve 1.00/1.00/0.75 in origin 12/8/4 order); insights line 19
  "North Carolina 19.1% (2023-12-30)" verified as the max state-week.
- One numeric error found: D-1.

## Defects (optimizer fixes these; tester fixed nothing in code/docs/data)

### D-1 — SUBSTANTIVE: wrong "eight weeks" rise claim in insights + notebook
- **Files:** `outputs/insights_summary.md` line 9; `notebooks/analysis.ipynb`
  cell 5 (markdown source, same sentence).
- **Wrong text:** "Last winter rose from 0.7% to 10.0% in eight weeks".
- **Evidence from committed `data/processed/national_combined.csv`:** the
  2024–25 winter peak is 10.0% on 2025-02-01; eight weeks earlier
  (2024-12-07) Combined was **2.4%**, not 0.7%. The last week at or below
  0.7% before that peak was 2024-05-25 — **36 weeks** earlier. The 0.7%
  figure is the Combined value on 2025-11-01 (same week last year), which
  the same sentence already cites — the two numbers were conflated.
- **Fix:** in both files replace with "Last winter rose from 2.4% to 10.0%
  in eight weeks" (2024-12-07 → 2025-02-01). Then re-execute the notebook
  via nbconvert and confirm 0 error cells (the notebook must be re-run
  after any text edit so its stored outputs stay in sync).

### D-2 — MINOR: chart 01 has no >observed-max disclosure in its footnote
- **File:** `src/make_charts.py` (chart-01 footnote text) →
  `outputs/charts/01_forecast.png`.
- **Evidence:** the forecast line runs to 13.87%, visibly above every
  historical peak (observed max 10.4%), but the chart-01 footnote only
  says forecast weeks are labelled with their demand band. A reader seeing
  only the chart gets no warning; the disclosure exists in README /
  insights / notebook / dashboard text but not on the chart itself.
- **Fix:** add one footnote line to chart 01, e.g. "Forecast weeks 7–8
  exceed the observed historical maximum (10.4%) — read them as a
  severe-season scenario." Regenerate the chart with
  `python -m src.make_charts` and re-view it.

### D-3 — MINOR: chart 04 footnote/docstring wrongly claim a zoomed y-axis
- **Files:** `src/make_charts.py` line 12 (module docstring) and line 421
  (chart-04 footnote: "y-axis zoomed to the data range").
- **Evidence:** no `set_ylim` exists in the chart-04 function (the only
  `set_ylim` calls are lines 175/218/226/273, for charts 01–03); the
  rendered chart-04(a) y-axis is matplotlib-auto, 0 to ~88, while the data
  range is 0.0–78.9% — i.e. the axis is NOT zoomed to the data range.
- **Fix:** either set the bed-chart y-axis to the data range in code
  (e.g. `ax1.set_ylim(0, 85)` or a data-derived limit) OR correct the
  wording in both places to match the actual axis (e.g. "y-axis starts at
  0"). Then regenerate chart 04 and re-view it.

### D-4 — COSMETIC: 4th dashboard metric delta is clipped
- **File:** `src/app.py` lines ~96–99 (`col4.metric` delta
  `f"{published} beats seasonal naïve ({...:.2f} pp)"`).
- **Evidence:** in the tester's full-page screenshot the delta renders as
  "↑ Holt Winters beats seasonal naïve …" — the text is cut off with an
  ellipsis because the string is too long for the metric card.
- **Fix:** shorten the delta, e.g. `"beats naïve (0.82 pp)"`, re-run the
  smoke gate and confirm the full text is visible.

## Known gaps / verified deviations (not defects)
- Forecast outer weeks exceed the observed max (13.87% vs 10.4%) — plan-fixed
  method, honestly disclosed on every surface (see gate 10). No action.
- Bed `*_coverage` columns are hospital counts, not 0/1 flags; redefined
  full-coverage share 86.36% — documented and consistent.
- Bed sample is 100 rows, not 1,000 (width/size rule) — documented.
- Holt-Winters ConvergenceWarning suppressed — recorded (see gate 10).
- Screenshot is 1200 px wide (1440-wide capture exceeded the 1 MB rule);
  tester's replacement is 1200×6100, 905,025 bytes, a genuine capture of the
  running app on port 8502.
- Early-2020 bed weeks are thinly reported (45 of 226 weeks < 50 states,
  as few as 3) — disclosed in chart 04 footnote, README, data/README and
  dashboard. One week (2020-07-11) has ICU occupancy exactly 0.0 and 23
  weeks have no ICU data (NaN) — recorded in `data/README.md` lines 82–83.
- No `.pbix`, no SARIMA (plan §11). Synthetic fallback implemented, not used;
  `data_source.json` records `synthetic: false`.

## Optimizer's first step
Fix **D-1** first: correct "rose from 0.7% to 10.0% in eight weeks" → "rose
from 2.4% to 10.0% in eight weeks" in `outputs/insights_summary.md` line 9
**and** `notebooks/analysis.ipynb` cell 5, then re-execute the notebook via
nbconvert (0 error cells) so its stored outputs stay in sync. Then D-2, D-3,
D-4 (chart regeneration + app re-check), re-run `pytest` (expect 37 passed)
and the Streamlit smoke gate on a fresh port 8502+ after any change.
