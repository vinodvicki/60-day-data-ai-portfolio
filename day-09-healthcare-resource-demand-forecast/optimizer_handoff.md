# Optimizer handoff — Day 09 Healthcare Resource Demand Forecast

**Stage:** optimizer (role 5 of 6) → publisher/reviewer. **Date:** 2026-11-13.
**Day folder:** `~/workspace/goals/60-day-data-ai-portfolio/day-09-healthcare-resource-demand-forecast/`
**Verdict: RELEASE-READY** — all 4 tester defects fixed, every gate re-run
after the fixes, orchestrator validate 11/11. Nothing is pushed (publisher's job).

## Files changed (optimizer only — no other files touched)

- `outputs/insights_summary.md` — D-1: "rose from 0.7% to 10.0% in eight
  weeks" → "rose from 2.4% to 10.0% in eight weeks" (line 9).
- `notebooks/analysis.ipynb` — D-1: same sentence corrected in cell 5
  (index 5, markdown), then re-executed via nbconvert `--inplace` so
  stored outputs stay in sync (16 cells, 0 error cells; now 884,327 bytes).
- `src/make_charts.py` — D-2: chart-01 footnote gains "Forecast weeks 7–8
  exceed the observed historical maximum (10.4%) — read them as a
  severe-season scenario." (value taken from `data_source.json`, not
  hard-coded); D-3: module docstring (line 12) and chart-04 footnote
  corrected from "y-axis zoomed to the data range" to "y-axis starts at 0"
  (wording fix — the axis is matplotlib-auto 0 to ~88; no `set_ylim`
  added, so nothing about the render could clip).
- `outputs/charts/01_forecast.png` — regenerated from the committed CSVs
  only (180,082 bytes); new disclosure line viewed, legible, no truncation.
- `outputs/charts/04_bed_capacity.png` — regenerated from the committed
  CSVs only (195,574 bytes); corrected footnote viewed, legible.
  Charts 02/03 were NOT regenerated (untouched, same bytes/hashes as the
  tester verified).
- `src/app.py` — D-4: 4th metric delta shortened from "Holt Winters beats
  seasonal naïve (0.82 pp)" to "beats naïve (0.82 pp)" (~line 97).
- `tests/test_pipeline.py` — 2 new regression tests pinning the fixes:
  `test_winter_rise_claim_is_2_4_pct_not_0_7` (grounds 2.4% / 10.0%
  against `national_combined.csv` and asserts the corrected sentence in
  insights + notebook cell 5, with the wrong sentence absent) and
  `test_chart_footnotes_are_honest` (asserts "zoomed to the data range"
  absent, "y-axis starts at 0" present, chart-01 disclosure present in
  `make_charts.py`). Module docstring updated to mention them.
- `screenshots/dashboard.png` — re-captured (real capture of the running
  app on port 8502, tall viewport 1200×6100): **1200×6100, 912,013 bytes**.
  Re-capture was required because the D-4 fix changed the visible metric
  card; viewed in full — the 4th delta now reads "↑ beats naïve (0.82 pp)"
  with no clipping, all sections render, no blank sections, no errors.

## Verified numbers (tester's figures reused verbatim — nothing recomputed
except the D-1 ground check and the 43-point spot-check below)

- Live fetch (unchanged): NSSP **25,116** rows / bed **81,713** rows;
  `data_source.json` source "live", `synthetic: false`, fetch 2026-11-13.
- Latest week (2026-10-31) Combined **2.3%** (0.5 + 1.7 + 0.1, diff 0.0);
  observed max **10.4%** (2023-12-30); 2024–25 peak 10.0% (2025-02-01).
- Forecast 8 weeks 2026-11-07 → 2026-12-26: **3.03 → 13.87%**; bands
  Moderate, Moderate, High, High, Surge, Surge, Surge, Surge; final-week
  80% interval 12.76–14.91%, 95% interval 12.08–15.38%.
- Bands over 161 weeks: Low **89** / Moderate **35** / High **19** /
  Surge **18**.
- Backtest: Holt-Winters mean RMSE **0.4693** vs seasonal naïve **0.8244**;
  coverage 75.0% vs 91.67%.
- Top-5 states (latest-4-week mean): HI **7.0** / FL **3.4** / LA **2.9** /
  WA **2.8** / TX **2.6**; max state-week NC 19.1% (2023-12-30).
- Bed: mean **72.5%**, max 78.9% (2022-12-10), latest **74.95%**
  (2024-04-27), ICU latest 71.65%.
- `data/` total **1,132,954 bytes**; no file > 1 MB anywhere in the day
  folder (largest is now the screenshot, 912,013 bytes).

## Gate results after the fixes

1. **pytest — PASS, 39 passed** (37 + 2 new regression tests), both
   locations: day folder `39 passed in 15.20s`; portfolio root
   `39 passed in 15.41s`. One failure on the first run (the D-2/D-3 test
   asserted a joined sentence that spans two adjacent string literals in
   the source) — fixed by asserting both halves; re-run green.
2. **black + ruff — PASS.** `black --check src tests`: 7 files unchanged.
   `ruff check src tests`: all checks passed.
3. **Pipeline `--offline` — PASS.** Exit 0, "data_source.json untouched
   (source='live')"; sha256 of all 7 processed files verified identical
   before/after (all OK), including `data_source.json`
   (`e4f65c55…`). No live fetch re-run.
4. **Notebook — PASS.** nbconvert `--inplace`, exit 0; **16 cells,
   0 error cells**; corrected sentence confirmed present in the executed
   notebook, wrong sentence absent. Raw-absent guarded path (forecast
   loaded from committed CSVs).
5. **Streamlit smoke gate — PASS (fresh port 8502).** `GET /` → HTTP 200;
   `GET /_stcore/health` → HTTP 200, body "ok". Server log clean (0
   error/traceback/exception lines). Real screenshot re-captured
   (1200×6100, 912,013 bytes) and viewed in full. Server killed; port
   8502 verified free afterwards (curl exit 7, no streamlit process
   remains).
6. **Published-number verification — PASS, 0 mismatches.** 43-point
   check of README.md / insights_summary.md / notebook numbers against
   the committed CSVs (latest split, observed max, 2024-12-07 = 2.4%,
   2025-11-01 = 0.7% / flu 0.3%, forecast endpoints + all four interval
   bounds + interval widths 1.57→3.30 pp (95%) and 0.63→2.15 pp (80%),
   band counts, backtest RMSE/MAE/MAPE/coverage for both methods, top-5
   states, NC max state-week, bed mean/max/latest/ICU, volume-converter
   139 visits / 21 admissions). No other number in any doc was wrong —
   no other doc was edited.
7. **requirements.txt — PASS.** All 12 pins match the venv exactly
   (`pip freeze` comparison, 0 mismatches).
8. **`.gitignore` — PASS.** Matches plan §3.4 exactly (scaffold defaults
   + the three raw-data lines).
9. **README references — PASS.** README.md 9 refs, insights 4 refs,
   data/README.md 6 refs — all exist on disk except the 4 git-ignored
   raw files in data/README.md (`data/raw/nssp_ed_visits.json`,
   `bed_capacity.json`, `*_synthetic.json`), intentionally absent per
   plan §3.4/§5 and documented as such — not a defect (same as the
   tester found). Plan §5 tree complete, nothing missing.
10. **Orchestrator validate — PASS, 11/11.** `python3
    agents/orchestrator.py --day 9 validate` from the portfolio root:
    all checks pass, including "pytest passes (day venv) — 39 passed
    in 15.64s". **Zero FAILs, nothing to explain.**

## Defects fixed (D-1…D-4)

- **D-1 (substantive) — FIXED.** Verified against
  `data/processed/national_combined.csv` before writing: 2024-12-07 =
  2.4%, 2025-02-01 = 10.0% (eight weeks apart); the last ≤0.7% week was
  2024-05-25, 36 weeks earlier. Corrected sentence in
  `outputs/insights_summary.md` and `notebooks/analysis.ipynb` cell 5;
  notebook re-executed (0 error cells). Pinned by
  `test_winter_rise_claim_is_2_4_pct_not_0_7`.
- **D-2 (minor) — FIXED.** Chart-01 footnote now carries the
  >observed-max disclosure ("Forecast weeks 7–8 exceed the observed
  historical maximum (10.4%) — read them as a severe-season scenario.");
  chart 01 regenerated from committed CSVs and viewed.
- **D-3 (minor) — FIXED by wording correction, not by code change.**
  The honest minimal fix: docstring + chart-04 footnote now say
  "y-axis starts at 0" (the actual matplotlib-auto axis, 0 to ~88, data
  range 0.0–78.9%). No `set_ylim` was added — setting one would have
  risked clipping the dashed Holt-Winters extension, and the wording
  fix is exact. Chart 04 regenerated and viewed.
- **D-4 (cosmetic) — FIXED.** 4th metric delta is now "beats naïve
  (0.82 pp)"; confirmed fully visible in the re-captured screenshot
  (no ellipsis, no clipping).

## Remaining known gaps (carried over from the tester — none are defects)

- Forecast outer weeks exceed the observed max (13.87% vs 10.4%) —
  plan-fixed method, now disclosed on every surface including chart 01.
- Bed `*_coverage` columns are hospital counts; full-coverage share
  86.36% — documented and consistent.
- Bed sample is 100 rows, not 1,000 (width/size rule) — documented.
- Holt-Winters ConvergenceWarning suppressed — recorded in
  `data/README.md` and the notebook.
- Early-2020 bed weeks thinly reported (45 of 226 weeks < 50 states,
  as few as 3); one week (2020-07-11) has ICU occupancy exactly 0.0 —
  disclosed in chart 04 footnote, README, data/README and dashboard.
- No `.pbix`, no SARIMA (plan §11). Synthetic fallback implemented,
  not used; `data_source.json` records `synthetic: false`.

## Publisher's first step

**Frozen-tree check immediately before pushing:** re-verify every file
the READMEs reference exists on disk (charts 01–04, `screenshots/
dashboard.png`, all 7 processed files, `notebooks/analysis.ipynb`) —
all verified present by the optimizer at 15:37 PST 2026-11-13 — then
push the day folder to `vinodvicki/60-day-data-ai-portfolio` (main) and
verify the live GitHub page renders. Note: the workspace copy is not a
git checkout, so `git check-ignore` could not be run here — confirm the
raw-data `.gitignore` lines with git before pushing (carried from the
coder handoff). Do not re-run a live fetch; no base64 anywhere in this
day's work.
