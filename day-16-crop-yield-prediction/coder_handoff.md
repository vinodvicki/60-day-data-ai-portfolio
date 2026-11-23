# Coder handoff — Day 16 Crop Yield Prediction

**Role:** coder (stage 3 of 6). **Date:** 2026-11-23.
**Verdict: READY FOR TESTER.** All coder gates pass.

## 1. What was produced

- `src/data_pipeline.py` — fetch (OWID + Open-Meteo ×2) → clean → 7
  growing-season features → join; modes `--live/--offline/--use-cache`.
- `src/model.py` — OLS / Ridge / RandomForest + 2 naive baselines, driver
  analysis (Pearson r, standardised OLS coefs, RF permutation importance).
- `src/make_charts.py` — 4 charts from processed CSVs only.
- `src/app.py` — Streamlit dashboard, processed CSVs only.
- `tests/test_pipeline.py` — 19 tests + scaffold `test_smoke.py` (2 tests).
- `notebooks/analysis.ipynb` — 14 cells, nbconvert exit 0, 0 error cells.
- `README.md`, `data/README.md`, `outputs/insights_summary.md` — all
  numbers from the committed CSVs.
- Data: `data/raw/` 3 files (952,064 B total), `data/processed/` 5 files.
- `requirements.txt` — pinned from the venv (see §3).

## 2. Verified numbers

- Pipeline `--live`: 3 HTTP calls, all 200 first try. Yields 26 rows
  (2000–2025, 0 missing); weather 9,497 days/state, 0 missing.
- Models, held-out RMSE (t/ha): **Ridge 0.540 (winner)**, RandomForest
  0.592, OLS 0.785, naive_last **0.287**, naive_mean 1.479. Headline:
  **no model beats the naive one-step baseline** — reported plainly in
  README/insights/notebook.
- Drivers: year r +0.83; heat_days_gs std coef −0.49; jul_temp_mean −0.37
  (r −0.39); jul/jun precip r +0.23 each.
- 2012 spot-check: Iowa gs rain 423.6 mm vs 1041.9 mm (2010); yield 7.73
  vs 9.58 t/ha.
- pytest: **21 passed** (day folder AND repo root), coverage **47.70%**
  (bar 30). black + ruff + mypy clean (strict, run from inside the day
  folder). Notebook nbconvert exit 0, 0 errors.
- Charts: 01 (118,911 B), 02 (58,602 B), 03 (72,999 B), 04 (77,799 B).
- `.gitignore` matches Day 15 exactly; does NOT exclude `data/`.

## 3. Known gaps / defects (all disclosed, none blocking)

1. **kaleido 1.2.0 broken with plotly 7.1.0** (`RuntimeError:
   Chromium.get_cli() received invalid args`) — chart 04 uses the plan's
   matplotlib fallback (schematic lon/lat map). Plotly dropped from
   `requirements.txt` (nothing imports it now). The venv still has
   kaleido installed but it is unused.
2. **Timezone double-encoding bug, fixed:** `America%2FChicago` was passed
   to requests and re-encoded to `%252F` → HTTP 400. Fixed to
   `America/Chicago`. The live fetch then succeeded.
3. **Unit factor corrected:** 1 t/ha = 15.932 bu/acre (39.368/2.47105), not
   15.934 — fixed in code, plan §4.4 and tests. 2024 yield = 179.28 bu/acre.
4. **naive_last definition fixed to the plan's literal text:** one-step
   persistence (previous year's actual), not the last train year for all
   six years. This is what makes the baseline beat the models.
5. **RandomForest `n_jobs=1`, not `-1`:** parallel prediction changed the
   held-out RMSE in the last ulp between runs; serial is bit-identical.
   Plan §4.1/§11 updated.
6. **Offline replay no longer clobbers `data_source.json`:** `run()` only
   writes provenance on a live fetch, so the tester's manual-validation
   section survives `--offline` re-runs. (Do NOT re-run `--live` after
   the tester fills it.)
7. `data_source.json` currently has NO `manual_validation` section yet —
   the tester adds it (§4.4).

## 4. Tester's first step

Run the smoke gate on a fresh port (8502+): Streamlit HTTP 200 on `/`
and `/_stcore/health`, capture the real `screenshots/dashboard.png`
with the tall-viewport Playwright method, kill the server, verify the
port is free — then hand-validate the 2024 yield (11.253324 t/ha) from
the raw CSV by hand and add `manual_validation` to `data_source.json`.
