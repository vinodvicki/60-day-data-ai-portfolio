# Test report — Day 19 Credit Card Fraud Detection

**Role:** Tester (independent re-verification in the coder's venv).
**Status:** ALL GATES PASS — no defects, no send-back. 2026-11-26.

## 1. Compile

- `python -m py_compile src/*.py tests/*.py` — PASS (no output, exit 0).

## 2. Pytest (with coverage)

- From inside the day folder: `pytest --cov=src --cov-fail-under=30` —
  **33 passed, coverage 64.50%** (analysis 100%, make_charts 99%,
  pipeline 46%, app 0% — app exercised by the smoke test).
- From the portfolio root (validate's cwd): `pytest
  day-19-credit-card-fraud-detection/tests/ --cov=...` — **33 passed,
  coverage 64.50%** (conftest sys.path bootstrap works).

## 3. Lint / format / types (re-run, not trusted from the coder)

- `black --check src tests` — clean (11 files unchanged).
- `ruff check src tests` — clean.
- `mypy src tests` — clean (11 source files, strict-by-default).

## 4. Pipeline run (offline reproduce)

- `python src/data_pipeline.py --offline` re-run by the tester:
  fingerprint OK (284,807 rows, 492 frauds); baseline PR-AUC 0.0017,
  logistic regression 0.7004, random forest 0.8239; cost-optimal
  threshold 0.10.
- md5 diff of all 9 processed files before vs after the re-run:
  **byte-identical** (no diff output).

## 5. Streamlit smoke (fresh port 8503, tester run)

- `GET /` → **200**; `GET /_stcore/health` → **200 ok**.
- Screenshot: 1280×3850, 421,702 B, md5
  `7ffbe4e25f912afe898c14d8c7a1e09b` — **byte-identical to the coder's
  screenshot** (same md5), so the dashboard renders deterministically.
- Server killed; port 8503 verified free afterwards.
- Dashboard viewed: model table (3 models), threshold slider at 0.10
  showing P 0.765 / R 0.838 / 38 false alarms / $786, all 4 charts,
  cost assumptions and limitations all render. No truncation, no
  broken images, no error banners.

## 6. Notebook

- nbconvert execute on the committed notebook: exit 0, **15 cells,
  0 error cells**. Re-executed from a copy without `data/raw/`:
  also 15 cells, 0 errors (CI-safe).

## 7. Manual validation (one metric, by hand — independent computation)

Hand-checked against the RAW file with a separate Python process
(day-18 venv, not the day-19 pipeline code):

| Metric | Independent value | File value | Diff |
| --- | --- | --- | --- |
| Fraud rate | 0.1727485631% (492/284,807) | class_summary 0.1727485631% | **0.00e+00** |
| RF @0.10 precision | 124/(124+38) = 0.7654320988 | threshold_sweep 0.7654320988 | **0.00e+00** |
| RF @0.10 recall | 124/(124+24) = 0.8378378378 | threshold_sweep 0.8378378378 | **0.00e+00** |
| RF @0.10 total cost | 38×$5 + $6,522.19 = $6,712.19 | threshold_sweep $6,712.19 | **0.00e+00** |
| RF @0.10 cost/10k | $785.5752 | threshold_sweep $785.5752 | **0.00e+00** |

## 8. Chart legibility (viewed)

- 01 class imbalance: both labels visible (284,315 inside bar, 492
  above bar); both density curves visible; median text clean.
- 02 PR curves: RF near the top, LR diagonal, no-skill dashed line at
  the bottom; legend legible.
- 03 threshold tradeoff: annotation readable, no collisions.
- 04 cost curve: minimum annotation short-arrow, legible; cost split
  panel legible.

## 9. Defects found

**None.** No send-back to the coder. (The coder fixed 5 defects
in-stage before handoff; the tester found no further issues.)

## Next role's first step (optimizer)

Re-run pytest + mypy after any change; verify every published number
against the committed CSVs (the tester's hand-validation table above
is the reference); run the smoke test once more on a fresh port
(8504+) if app.py changes; then hand the release-ready tree to the
publisher.
