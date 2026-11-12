# Tester report — Day 08 Hospital Readmission Risk Model

**Stage:** tester (role 4 of 6) → optimizer. **Date:** 2026-11-12.
**Verdict: PASS with 2 minor defects** (both in `src/make_charts.py`, chart 04(b) axis
and chart 03 footnote — see §7). All hard gates pass: pytest 40/40 (both locations),
black + ruff clean, notebook 16 cells / 0 errors (raw absent), offline pipeline leaves
`data_source.json` byte-identical, Streamlit smoke on fresh port 8503 with HTTP 200s
and a genuine fresh full-page screenshot. No code was edited; this report is the
tester's only write, plus the fresh `screenshots/dashboard.png` (a genuine capture
of the running app, which the smoke gate requires).

## 1. Commands run and results

All run in the coder's venv `.venv` (present, provisioned nothing). Day folder:
`~/workspace/goals/60-day-data-ai-portfolio/day-08-hospital-readmission-risk-model/`.

| # | Command | Result |
|---|---|---|
| 1 | `.venv/bin/python -m py_compile src/*.py tests/*.py` | exit 0, no errors |
| 2 | `.venv/bin/python -m pytest tests/ -q` (from day folder) | **40 passed in 2.93 s**, exit 0 |
| 3 | `day-08-.../.venv/bin/python -m pytest day-08-.../tests/ -q` (from portfolio root `~/workspace/goals/60-day-data-ai-portfolio/`) | **40 passed in 2.97 s**, exit 0 |
| 4 | `.venv/bin/python -m black --check src tests` | exit 0 — "7 files would be left unchanged" |
| 5 | `.venv/bin/python -m ruff check src tests` | exit 0 — "All checks passed!" |
| 6 | `.venv/bin/python -m src.data_pipeline --offline` | exit 0 — "offline: all committed processed files present; data_source.json untouched (source='live')"; sha256 of `data/processed/data_source.json` verified unchanged (`fadf3f4a…ebc3`) |
| 7 | `.venv/bin/jupyter nbconvert --to notebook --execute notebooks/analysis.ipynb --output /tmp/day08_nb_out.ipynb --allow-errors` (raw CSV absent — `data/raw/` holds only `IDS_mapping.csv` + `sample_rows.json`) | exit 0; **16 cells, 0 error cells** |
| 8 | Streamlit smoke (see §2) | port 8503, HTTP 200 on `/` and `/_stcore/health`, clean log, fresh screenshot, server killed, port free |

## 2. Streamlit smoke gate (mandatory)

- Command: `.venv/bin/streamlit run src/app.py --server.port 8503 --server.headless true`
  (fresh port 8503 — never 8501, not the coder's 8502).
- `GET /` → **HTTP 200**; `GET /_stcore/health` → **HTTP 200** (body `ok`).
- Server log `/tmp/day08_streamlit_8503.log`: no errors / tracebacks.
- Screenshot: `screenshots/dashboard.png`, **1440 × 6441 px, 890,909 bytes** —
  genuine fresh capture of the running app (Playwright/Chromium; the app renders
  inside Streamlit's internal scroll container, so the capture was taken at the
  measured `stMain` scroll height of 6,441 px after `full_page` returned only the
  900 px viewport). It overwrites the coder's capture (1440 × 8200, 902,149 bytes);
  the height difference is rendering variance (chart/image heights), not missing
  content — the capture shows the full page top to bottom (see §3).
- Dashboard renders with no errors: header + "NOT a clinical tool" banner, cohort
  metrics (101,766 / 11,357 (11.16%) / 100,114 / 20,024 rows, 14,022 patients),
  model-comparison table for both models, calibration-decile table, subgroup table
  (age [0-10) shown as ROC-AUC None), odds-ratio + permutation-importance tables,
  all 4 charts embedded, methods/limitations panel, CC BY 4.0 attribution footer.
  Values shown match the committed CSVs (e.g. logistic 0.6612 / 0.2071 / 0.0971,
  slope 0.9131, intercept −0.1609, TP 29 / TN 17,712 / FP 40 / FN 2,243).
- Server killed afterwards; `ss` confirms **port 8503 free**; no streamlit process
  remains. (Note: the first `pkill` also matched the tester's own shell command
  line and terminated that shell; the server was already dead and the port was
  re-verified free with a separate command.)

## 3. Hand validation (from the committed CSVs only)

**Validation 1 — prevalence-only Brier (exact match, diff 0.0000).**
Test-set confusion counts in `data/processed/model_metrics.csv` give positives
TP + FN = 29 + 2,243 = 2,272 (logistic) and 20 + 2,252 = 2,272 (HistGB), n = 20,024.
Test prevalence = 2,272 / 20,024 = **0.113464**. Prevalence Brier =
0.113464 × (1 − 0.113464) = **0.100590 → 0.1006** at 4 dp. Committed
`brier_baseline` = **0.1006** for both models. **Diff = 0.0000. PASS.**
(Raw-prevalence check: 0.1116 × 0.8884 = 0.0991, as recorded in `data/README.md`.)

**Validation 2 — HistGB ROC-AUC from `data/processed/roc_pr_curves.csv` (exact match).**
Trapezoid integration over the 400 committed ROC points per model:
logistic **0.6612** (committed 0.6612, diff 0.0000), HistGB **0.6761**
(committed 0.6761, diff 0.0000). **PASS.**
Trapezoid PR-AUC over the same 400 points gives logistic 0.2097 / HistGB 0.2312
vs committed average-precision values 0.2071 / 0.2293 (diffs +0.0026 / +0.0019).
This is expected, not a defect: the committed PR-AUC is sklearn average
precision (step interpolation), while the trapezoid over 400 sampled points is
an approximation that slightly overestimates. Not flagged.

**Spot-checks of coder-claimed numbers against committed files (all match):**
- `data_source.json`: n_raw 101,766; n_after_exclusions 100,114;
  target_distribution_raw {NO 54,864, >30 35,545, <30 11,357};
  target_distribution_clean {0: 88,757, 1: 11,357}; exclusions {11: 1,642 Expired;
  19: 8; 20: 2; 21: 0} = 1,652, deviation None; split train 80,090 rows /
  56,417 patients / 11.34%, test 20,024 rows / 14,022 patients / 11.35%,
  test_share 0.20, patient_overlap 0; weight_missing_rate 0.9686;
  zip_bytes 3,170,254; csv_bytes 19,159,383; mapping_bytes 2,547;
  n_medication_columns 23; source "live", synthetic false, fetch_date 2026-11-12.
- Missing rates: weight 0.9686, medical_specialty 0.4908, payer_code 0.3956,
  race 0.0223, max_glu_serum 0.0, A1Cresult 0.0 ("None" is a real category;
  pinned by a test, `tests/test_pipeline.py:51-66`).
- Subgroups (`subgroup_metrics.csv`, 36 rows): age [20-30) logistic ROC-AUC
  0.7531 / HistGB 0.7991; [90-100) 0.5079 / 0.5611; [0-10) n=33, 0 positives,
  ROC-AUC empty (undefined), small_n True.
- `feature_importance.csv`: swing-bed OR 5.317 → 5.32, Hematology 3.376 → 3.38,
  psychiatric hospital 3.004 → 3.00, hospice/home 0.247; `number_inpatient`
  permutation importance 0.0753 — all match `outputs/insights_summary.md`.
- `sample_rows.json` = 500 rows (668,078 bytes); `sample_encounters.csv` =
  1,000 rows, target rate 0.107, readmitted dist {NO 536, >30 357, <30 107}.

## 4. Chart legibility (all 4 viewed at full size)

- **01_readmission_overview.png** — PASS. To scale, legible; (a) 3-class bars with
  counts + % (11,357 / 35,545 / 54,864); (b) <30-day rate by prior inpatient
  visits 0/1/2/3+ with n labelled (675/186/64/75, sums to the 1,000-row sample;
  footnote states panel (b) is computed on the committed sample, not the full
  cohort). Source footnote present.
- **02_discrimination.png** — PASS. ROC (AUC 0.661 / 0.676 in legend) + PR
  (AP 0.207 / 0.229, prevalence baseline 0.1116) with chance diagonal; axes 0–1,
  no clipping.
- **03_calibration.png** — PASS except minor defect D-2 (footnote number, §7).
  Decile points for both models + perfect-calibration diagonal; Brier, slope and
  intercept annotated per model and matching the committed values (0.097/0.096,
  0.91/1.07, −0.16/+0.14). Axes 0–0.35, legible.
- **04_interpretation.png** — (a) PASS: all 10 odds-ratio bars visible with
  distinct short labels (the coder's label-collision fix holds), log scale with
  the 1.0 line. (b) DEFECT D-1 (§7): y-axis is truncated (0.50–0.85).
  The [0-10) omission IS explained in the footnote ("age [0-10) is omitted
  (33 patients, 0 readmissions — ROC-AUC undefined); other small-n bands are
  flagged in subgroup_metrics.csv") — that part passes.

## 5. `.gitignore`, file sizes, README references

- `.gitignore` matches plan §3.4 exactly: scaffold defaults (`__pycache__/`,
  `.venv/`, `venv/`, `.env`, `*.key`, `*.log`, `.streamlit/secrets.toml`,
  `.pytest_cache/`, `.ipynb_checkpoints/`) plus the three raw-data lines
  `data/raw/diabetic_data.csv`, `data/raw/*.zip`, `data/raw/*_synthetic.csv`;
  nothing else under `data/` is excluded. PASS.
- No committed file exceeds 1 MB: largest is `screenshots/dashboard.png`
  (890,909 bytes, fresh capture), then `notebooks/analysis.ipynb` (887,106),
  then `data/raw/sample_rows.json` (668,078). `data/` total **984,666 bytes**
  (< 1 MB, < 5 MB limit). PASS. Raw CSV + zip absent from disk at handoff.
- Every file the READMEs reference exists on disk (15 paths checked across
  `README.md`, `data/README.md`, `outputs/insights_summary.md`,
  `outputs/model_card.md`): all charts, `screenshots/dashboard.png`,
  `notebooks/analysis.ipynb`, `data/processed/*.csv`, `data_source.json`,
  `data/raw/sample_rows.json`, `data/raw/IDS_mapping.csv`, `outputs/model_card.md`,
  `outputs/insights_summary.md`, `data/README.md`. The one exception is
  `data/raw/diabetic_data.csv`, referenced in `data/README.md` only as the
  git-ignored, never-committed download (line 124) — expected per plan §3.4,
  not a defect. PASS.
- `requirements.txt` pins scikit-learn==1.9.1 and scipy==1.18.1 (plan §6).
  Extra processed file `roc_pr_curves.csv` (40,430 bytes, 400 points/curve × 4)
  is not in plan §3.5 but is required for chart 02 offline and is documented in
  `data/README.md` and the coder handoff — accepted as a documented deviation,
  not a defect. `sample_rows.json` at 500 rows (not 1,000) is likewise documented
  (1,000 rows = 1.33 MB, over the 1 MB rule) — accepted.

## 6. Plan §8 success-checklist spot-check (all items verified where testable)

Problem + audience, source/licence/fetch-date/counts/missing-rates/exclusions,
repeatable prep steps + metric definitions, model card delivered
(`outputs/model_card.md`), discrimination AND calibration for both models,
patient-grouped split (0 overlap, test-asserted), discharge exclusions {11, 19,
20, 21} with labels verified from `IDS_mapping.csv`, exactly 4 charts + working
dashboard, insights with one finding per question + recommendation, README with
setup/sample outputs/validation/limitations, data-size exception honoured,
one metric hand-validated and recorded (§3 above), pytest passing from day folder
and portfolio root, notebook 0 errors offline, pinned deps, lint clean, smoke
gate passed, charts legible (except D-1/D-2), frozen-tree references all exist.

## 7. Defects (for the optimizer, via the coder — no code edited by the tester)

**D-1 (minor) — Chart 04(b) y-axis is truncated, violating plan §7 "no truncated axes".**
`src/make_charts.py:350`: `ax2.set_ylim(0.5, 0.85)`. Every other chart in the
same file starts its axis at 0 (lines 174, 213, 233, 275). Effect: bar heights
are not proportional to ROC-AUC — e.g. logistic [90-100) ROC-AUC 0.5079 renders
as a ~2%-tall sliver while [20-30) 0.7531 renders ~72% tall, exaggerating the
age gap. The values themselves are correct (axis is labelled, exact numbers are
in `subgroup_metrics.csv`). Fix: set the y-limit to start at 0 (e.g.
`ax2.set_ylim(0, 0.9)`), regenerate `outputs/charts/04_interpretation.png`
(and re-capture the dashboard screenshot if the chart image changes size).

**D-2 (minor) — Chart 03 footnote quotes a different Brier baseline than the legend.**
`src/make_charts.py:282`: footnote text "Brier baseline is the prevalence-only
predictor (0.0991)." The legend (line 265) uses the committed
`brier_baseline` 0.1006 → rendered "(baseline 0.101)". 0.0991 is the baseline at
the raw prevalence 0.1116; 0.1006 is the baseline at the test-set prevalence
0.1135 — the value actually reported in `model_metrics.csv`. One chart should
not show both without labelling which is which. Fix: change the footnote to
0.1006 (test-set prevalence) or annotate it as "0.0991 at the raw prevalence",
regenerate `outputs/charts/03_calibration.png`.

No other defects found. Known gaps from the coder handoff (extra
`roc_pr_curves.csv`, 500-row sample, "None"-is-a-category fix, HistGB dense
input, chart 04(a) label fix, chart 04(b) [0-10) omission) were all verified as
documented and correct, except D-1/D-2 above.

## 8. Optimizer's first step

Fix D-1 and D-2 in `src/make_charts.py` (lines 350 and 282), regenerate charts
03 and 04 via the offline chart command, re-run `pytest tests/ -q` (expect 40
passed) and `black --check` + `ruff check`, then re-verify chart 04(b) starts at
0 and chart 03's footnote/legend agree. Nothing else needs changing; do not
re-run a live fetch (data already verified) and do not touch the models or CSVs.
