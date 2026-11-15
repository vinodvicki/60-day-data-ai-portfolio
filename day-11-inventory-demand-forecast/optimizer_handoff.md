# Day 11 — Optimizer handoff (Stage 5, 2026-11-15)

**Project:** Inventory Demand Forecast — UCI Online Retail (2010–2011).
**Tester verdict carried in:** PASS with 1 minor docs-only defect + cosmetic
observations (`test_report.md`). All tester defects/observations below are
closed except chart 03, which was deliberately left untouched per the task.

## 1. What was fixed (exact files / lines)

### D-1 — docs-only defect (tester §9.1)
- **`data/README.md:145`** — "forecast 156,877 each week (week 48)" →
  "forecast **158,805** each week (week 48)". Verified before editing against
  `data/processed/weekly_aggregate.csv`: week 48 (week starting 2011-10-31)
  = 158,805 units; 156,877 is week 52's actual. The quoted WAPE
  (0.08252144200709814) is unchanged — it is identical for either forecast,
  as the tester showed. No other number changed.

### NaN defect (tester observation §9.4 — real defect, fixed)
- **`src/data_pipeline.py`** — added `sanitise_json_value()` (after the
  imports, before `write_data_source`) which recursively replaces
  non-finite floats (NaN / ±inf) with `None`, and `write_data_source()`
  now dumps `sanitise_json_value(record)` instead of the raw record.
  Source of the NaNs: `_insample_wape_aggregate()` returns `float("nan")`
  for `holt` / `gradient_boosting` (no cheap one-step in-sample analogue);
  those values are still NaN in memory — only the serialisation changes,
  NaN → null. No value changed.
- **`data/processed/data_source.json`** — fixed the committed file with the
  pipeline's own sanitiser (one-off snippet importing `write_data_source`
  from `src.data_pipeline`; no live fetch, no hand-edit). `diff` against the
  pre-fix file is exactly 2 lines: `"holt": NaN` → `null`,
  `"gradient_boosting": NaN` → `null` (lines 27443–27444). File grew by
  2 bytes (607,391 → 607,393). New sha256:
  `8c97e82c48fb099993441aaaed190cb12b2771ce5aaa79841835382282ca7851`
  (was `3504356393cc51904390f13508b5d130313116258f11f2eb73353a2842afedca`).
  Strict-JSON parse verified (`json.loads` with `parse_constant` raising).
- **`tests/test_pipeline.py`** — added ONE regression test at the end,
  `test_data_source_json_is_strict_json`: asserts no `NaN` / `Infinity`
  literal in the file, parses it with `parse_constant` raising, and asserts
  `backtest.in_sample_wape_aggregate.holt` and `.gradient_boosting` are
  `None`.
- **`README.md`** — pytest count updated to the new total in both places
  (line 130: "28 tests"; validation section: "pytest 28/28"), and the
  notebook byte count updated to the true post-execution size (see §3).

### Chart legibility (tester observations §9.3 — fixed, low-risk)
- **`src/make_charts.py`, `chart_01`** — panel titles used
  `row['description'][:32]`, truncating "…T-LIGHT HOLD" (missing "ER").
  Now uses the full stripped description. Longest top-4 description is
  34 chars; verified at full size: "85123A — WHITE HANGING HEART T-LIGHT
  HOLDER" now reads in full.
- **`src/make_charts.py`, `chart_04`** — y-labels used `d[:22]`
  ("MEDIUM CERAMIC TOP STO", …). Now uses the full stripped description
  and the figure widened 11 → 12 in. Verified at full size: all 20 labels
  read in full (e.g. "23166 — MEDIUM CERAMIC TOP STORAGE JAR",
  "22086 — PAPER CHAIN KIT 50'S CHRISTMAS").
- Charts 01 + 04 regenerated via `python -m src.make_charts`; charts 02
  and 03 are byte-identical to the coder's (unchanged code paths).
- **Chart 03 NOT touched** — label overlap left as-is per the task; the
  tester passed it as cosmetic and the exact per-SKU ADI/CV² live in
  `sku_summary.csv` / `data_source.json`. The note stays in the
  README/insights.

## 2. Verified numbers after the fixes (spot-checked from committed CSVs)

- Cleaned: **527,795 rows / £10,283,243.98 / 5,577,139 units / 19,776 orders**;
  exclusions 9,288 (3,836 invoices) / 1,336 / 1,181 / 2,309 / 0; missing
  CustomerID 131,455 (24.91%); partial-week rows 27,349, full-week 500,446.
- Aggregate 5,241,272 units; week 48 = **158,805**, week 52 = 156,877;
  holdout actual 681,023.
- Top-20 forecast total **69,194** units; aggregate forecast 627,508;
  reorder total **97,314** (69,194 forecast + 28,120 safety stock; Σ
  `order_up_to_units` = 97,313.715…); lumpy S = 38,073; 2 review-manually.
- WAPE (primary, volume-weighted): moving average **44.16%**, naïve 44.33%,
  Holt 45.52%, gradient boosting 65.51%, Croston-SBA 80.30%; per-cluster
  winners smooth → moving average 34.03%, erratic → moving average 47.26%,
  intermittent → Holt 52.35%, lumpy → naïve 29.74%, aggregate → naïve 8.25%.
- Rechecked the insights Rec-2 figure independently: Croston-SBA lumpy
  WAPE is 169.34% on the primary holdout and 3,805.98% on the supplementary
  holdout — the insights text is correct, no edit needed.
- Row counts: weekly_demand 1,040; weekly_aggregate 52; sku_summary 20;
  cluster_summary 4; forecast 84; backtest 252; reorder_list 20.

## 3. Notebook

- Re-executed after the chart regeneration (notebook embeds the charts):
  `jupyter nbconvert --to notebook --execute --inplace --allow-errors`
  exit 0, **15 cells, 0 error cells**.
- Final size **657,984 bytes** (was 648,748 at coder handoff, 648,693 after
  the tester's run — the size moves on every re-execution because the
  embedded chart PNGs changed; the README now quotes the true 657,984).
- sha256: `1fb4d39fd17170da009dada90750a0b203bce317e29a62cc2ccbe5e94265265a`.

## 4. Frozen-tree check (plan §5)

- Every plan-listed file exists on disk. **No extra files** outside the plan
  tree (excluding `.venv/`, `.pytest_cache/`, `.ruff_cache/`,
  `__pycache__/`; the coder's `.venv` was not deleted).
- Every path referenced in `README.md`, `data/README.md` and
  `outputs/insights_summary.md` resolves from its correct base.
- `publisher_handoff.md` is the only plan file still absent — it is the
  publisher's to write.
- `.gitignore` matches plan §3.4 (three raw-data lines only; `data/` itself
  NOT excluded). `data/` total 933,477 bytes (< 5 MB); no file > 1 MB
  anywhere in the day folder (excluding `.venv`); no raw ZIP/XLSX on disk.

## 5. Gate results after the fixes

| Gate | Result |
|---|---|
| `black --check src tests` | clean — 8 files unchanged |
| `ruff check src tests` | All checks passed! |
| `pytest tests/ -q` (day folder, coder venv) | **28 passed, 1 warning in 23.89 s** (was 27; +1 new strict-JSON test; warning is the known Holt ETS ConvergenceWarning) |
| `pytest` (portfolio root, day venv) | **28 passed, 1 warning in 24.67 s** |
| Offline pipeline `python -m src.data_pipeline --offline` | exit 0; `data_source.json` byte-identical to the NEW sha256 `8c97e82c…` (verified before/after); all 7 CSVs + 4 charts byte-identical after the run |
| Notebook nbconvert | exit 0, 15 cells, 0 error cells, 657,984 bytes |
| Streamlit smoke, fresh port **8504** | HTTP 200 on `/`, HTTP 200 on `/_stcore/health`, clean server log (0 error/exception/traceback/warning lines) |
| Screenshot | **Re-captured** (charts changed, so the dashboard changed): tall-viewport single-shot method, stMain scrollHeight 5,900 px; `screenshots/dashboard.png` **1200×5900, 842,017 bytes**, sha256 `950f92f4fd4da84305646a78f8eed625b85dedc037f59fabcec79ffe46a835e0`; visually verified — title, KPIs (5,241,272 / 12.4% / 44.2% / 2), forecast + reorder tables, all 4 charts (incl. fixed 01/04), method + cluster tables, 3 recommendations, CC BY 4.0 footer; no error banner. Server killed with `fuser -k 8504/tcp`; port 8504 verified free |
| Orchestrator validate (`python3 agents/orchestrator.py --day 11 validate`, portfolio root) | **11/11 checks passed** (pytest 28 passed in 25.06 s) |

Chart hashes: 01 `a5dd6840…`, 02 `70788f97…` (unchanged), 03 `7f796b2d…`
(unchanged), 04 `24675e96…`.

## 6. Known gaps / not done

- Chart 03 top-20 label overlap remains (cosmetic, passed by tester,
  exact values in `sku_summary.csv`).
- Holt ETS ConvergenceWarning (1 pytest warning) remains — known, fits
  are deterministic and backtest values reproduce exactly.
- No live fetch was re-run; no finding or number changed except the
  documented D-1 correction (156,877 → 158,805) and the NaN → null
  serialisation (representation only).

## 7. Publisher's first step

Run the frozen-tree check immediately before pushing: re-verify every
file the READMEs reference exists on disk (4 charts, `screenshots/dashboard.png`,
7 processed CSVs + `data_source.json`, `data/raw/sample_rows.json`) — then
push the day folder to `vinodvicki/60-day-data-ai-portfolio` and verify the
live GitHub page renders. Do NOT include `.pytest_cache/` / `.ruff_cache/`
in any push manifest.
