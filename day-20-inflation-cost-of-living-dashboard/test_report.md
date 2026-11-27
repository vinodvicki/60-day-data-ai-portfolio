# Test report — Day 20 Inflation & Cost of Living Dashboard

**Tester, 2026-11-27. Verified in the coder's venv; no dependencies were
installed by the tester and no code was edited to make a test pass.**

## Gates re-verified (independent re-runs)

| Gate | Command / check | Result |
|---|---|---|
| `py_compile` | `python -m py_compile src/*.py tests/*.py` | PASS |
| black | `black --check src tests` | PASS (10 files unchanged) |
| ruff | `ruff check src tests` | PASS |
| mypy | `mypy src tests` (from inside the day folder) | PASS, no issues in 10 files |
| pytest (day folder) | `pytest tests/ -q --cov=src --cov-fail-under=30` | **41 passed**, coverage **64.88%** |
| pytest (repo root) | same, run from the portfolio root | **41 passed**, coverage **64.88%** |
| Pipeline offline replay | `--offline` re-run; md5 of all 8 processed files | **Byte-identical** to the committed files |
| Notebook | nbconvert execute from a copy **without `data/raw/`** | 15 cells, **0 errors** |
| Streamlit smoke (port 8503) | HTTP 200 on `/` and `/_stcore/health` | PASS (both 200, health "ok") |
| Screenshot (tester) | `screenshots/dashboard.png` | 1280×4219, 472,846 bytes, md5 18b0e38d… (coder's was 472,856 bytes — same dimensions/content; 10-byte difference is render noise) |
| Port free after kill | `ss -ltn` check in the smoke script | Port 8503 free: True |
| Chart legibility | Viewed all 4 PNGs + the tester screenshot | PASS — see notes |

## Hand-validation (independent arithmetic on the raw CSVs)

Three metrics recomputed by hand from `data/raw/*.csv` with plain
`csv`-module arithmetic (not via `src` functions):

- Energy YoY Sep 2026: hand 20.354115% vs. file 20.354115% — **diff 0.00e+00**
- Real hourly earnings Oct 2026: hand $11.260060 vs. file $11.260060 — **diff 0.00e+00**
- Medical-care cumulative since Mar 2006: hand 79.096512% vs. file 79.096512% — **diff 0.00e+00**

Spot-checks against the published numbers in README.md /
outputs/insights_summary.md (all from the processed CSVs): headline
+69.0%, basket $168.99, $1 = $0.30, peak YoY 8.98% (Jun 2022), latest
YoY 3.72% (Sep 2026), housing +80.0%, food +79.4%, medical +79.1%,
apparel +15.0%, education +29.9%, energy +20.35% YoY, real pay +12.2%,
nominal pay +89.6%, real YoY −0.54% (Sep 2026) — all match.

## Chart legibility notes

- Chart 01 now shows the 2009/2015 deflation dips below zero (the
  coder's ylim fix is confirmed in the render).
- Chart 02 "+66%" label is readable over the dashed headline line
  (white backing).
- Chart 04 titles read correctly ("The 100-dollar basket…",
  "Purchasing power of one dollar…") — no mathtext mangling.
- Chart 03's real-earnings line has a visible one-month gap at Oct 2025
  (the missing CPI month) — honest, not a defect.
- Dashboard screenshot: KPIs (3.72% / 2.57% / +69.0% / +12.2%), category
  table, basket slider line ("A basket that cost $100 in Mar 2006 costs
  $168.99 in Oct 2026") and all 6 assumptions render correctly.

## Defects

**NONE.** No send-back to the coder. No code was changed in this stage.

## Next role's first step (Optimizer)

Verify the published numbers once more against the committed CSVs
(they all check out — see above), confirm the day README embeds match
the chart files, and run `orchestrator validate` from inside the day
folder.
