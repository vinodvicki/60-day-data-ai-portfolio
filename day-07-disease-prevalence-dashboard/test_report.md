# Day 07 — Disease Prevalence Dashboard: Test Report

**Status:** TESTER COMPLETE (AGENTS.md, stage 4) — 2026-11-11.
**Verdict: PASS — no defects found.** All gates re-run independently in
the coder's venv; nothing was edited to make a test pass. The coder's
own fixes (D-1–D-7 in `coder_handoff.md`) were all re-verified rather
than trusted.

## Gate 1 — py_compile

```
.venv/bin/python -m py_compile src/*.py tests/*.py
```
**Result: PASS** — all 6 source files + 1 test file compile.

## Gate 2 — pytest (both locations)

```
.venv/bin/python -m pytest tests/ -q            # from the day folder
# from the portfolio root:
day-07-disease-prevalence-dashboard/.venv/bin/python -m pytest \
    day-07-disease-prevalence-dashboard/tests/ -q
```
**Result: PASS — 23/23 in both locations.** Includes the coder's new
`test_state_map_renders_all_states` and `test_state_geojson_covers_all_states`.

## Gate 3 — lint / format

`black --check src tests` — 6 files unchanged. `ruff check src tests` —
all checks passed. **Result: PASS.**

## Gate 4 — pipeline run (offline reproducibility)

```
md5sum data/processed/data_source.json state_prevalence.csv change_diabetes.csv
.venv/bin/python -m src.data_pipeline --offline
md5sum -c  # all three: OK
```
Output: "offline: derived tables regenerated; data_source.json untouched
(source='live')". **Result: PASS** — the Day 5/6 source-field lesson holds;
derived tables are byte-identical after an offline run.

## Gate 5 — notebook (independent run to /tmp)

`jupyter nbconvert --to notebook --execute notebooks/analysis.ipynb
--output /tmp/day07_nb_check.ipynb --allow-errors` — **Result: PASS —
12 cells, 0 error cells** (independent of the committed executed copy).

## Gate 6 — Streamlit smoke gate (mandatory, fresh port 8503)

```
.venv/bin/streamlit run src/app.py --server.port 8503 --server.address 127.0.0.1
curl http://127.0.0.1:8503/                 -> HTTP 200
curl http://127.0.0.1:8503/_stcore/health   -> HTTP 200, body "ok"
```
Server log: 0 error/traceback lines. Screenshot via CDP (navigate, wait
15 s real time, full-page capture at 1440×6500):
`screenshots/dashboard.png` — **686,480 bytes, 1440×6500** (replaces the
coder's stale 679,531-byte capture; the embedded charts changed since).

What the screenshot shows (read in full, not just the file size):
- Title, KPIs: national 12.05%, median county 13.3%, 2,956 counties,
  CDC figure 12.0% — all correct against `data_source.json`.
- **State map renders**: Alaska top-left, CONUS coloured blue (WV
  darkest), Kentucky and Pennsylvania grey, colour bar 8–15%, "Grey = no
  data in this release: KY, PA" note visible. This is the matplotlib
  map from the bundled geojson (coder D-1 fix) — verified drawn, not empty.
- **County dot map renders**: US-shaped cloud of dots, size = est.
  cases, colour = prevalence, colour bar 5–25%.
- Top-10/bottom-10 tables: Greene AL 27.1% / Madison ID 4.9% — match
  the CSVs. Movers tables: Kalawao HI +5.7 / Kenedy TX −7.5 — match.
- Charts 01–04 embedded and legible; **chart 03 panel (b) labels are
  now correct** (Diabetes +0.10 pp on top, CHD −0.50 pp at bottom —
  coder D-3 fix verified visually); all four footnotes complete, none
  truncated (coder D-4 fix verified).
- Methods section complete; **no error text anywhere** (coder D-2 fix
  verified — no ModuleNotFoundError banner).

Sidebar check (coder open item D-8): a second, viewport-only screenshot
(1440×900, no captureBeyondViewport) shows the sidebar rendering
correctly — "Condition: Diabetes" and "Year: 2023" dropdowns with labels.
The clipped sidebar in full-page captures is a headless-capture artifact
of the fixed-position sidebar, **not an app defect**. Closed: no action.

Teardown:
```
kill <8503 server pid>; kill <8502 coder server pid>; pkill chrome-headless-shell
curl http://127.0.0.1:8502/  -> connection refused (000)
curl http://127.0.0.1:8503/  -> connection refused (000)
ps: 0 streamlit servers, 0 headless-chrome processes
```
**Result: PASS — port 8503, HTTP 200 on `/` and `/_stcore/health`, real
screenshot 686,480 bytes / 1440×6500, servers killed, ports verified free.**

## Gate 7 — hand-validation of one metric (tester, different from coder's)

Recomputed independently from the committed CSVs:

| Quantity | My computation | Committed value | Match |
|---|---|---|---|
| WV diabetes state rate 2023 (100 × Σ cases / Σ adults, 55 counties) | 15.8813% | 15.88% in `state_prevalence.csv` | ✅ (diff 0.0013, rounding) |
| Greene County, AL est. cases (27.1% × 5,755 adults) | 1,559.6 → 1,560 | 1,560 in `prevalence_diabetes.csv` | ✅ exact |
| CHD median county pp change 2022→2023 | −0.50 pp, 86.3% down | chart 03 + README | ✅ |

**Result: PASS.**

## Gate 8 — chart legibility (all 4 PNGs read at full size)

- 01_state_ranking: 49 states, bars to scale from 0, national line
  12.05%, footnote complete on 2 lines. ✅
- 02_county_distribution: histogram median 13.3% / IQR 11.8–15.2% lines
  correct; box plots per measure, footnote complete. ✅
- 03_change_2022_2023: histogram median +0.10 pp; panel (b) labels now
  match their bars (verified after D-3); footnote complete. ✅
- 04_measure_comparison: 2022 vs 2023 bars, pp labels (+0.08 / −0.49 /
  −0.10 / −0.55 / −0.12 / −0.36) all match `data_source.json`; footnote
  complete. ✅

## Gate 9 — orchestrator validate

`python3 agents/orchestrator.py --day 7 validate` — **11/11 checks
passed** (README, data/README, 4 charts, insights, tests, pinned deps,
.gitignore, no credentials, data-size 3,034 KB, screenshot, pytest).

## Defects found by the tester

**None.** Zero new defects. The coder's D-1–D-7 fixes all verified; the
one open item (D-8, sidebar clip) is closed above as a capture artifact.

## Handoff

1. **Produced:** this file (`test_report.md`); fresh
   `screenshots/dashboard.png` (686,480 bytes, port 8503).
2. **Verified numbers:** pytest 23/23 (both locations); validate 11/11;
   smoke HTTP 200/200; WV hand-check diff 0.0013; Greene 1,560 exact.
3. **Known gaps:** none. All plan §8 success criteria are met on the
   evidence above.
4. **Next role's first step (optimizer):** run the release checklist —
   confirm the root README/docs need no further changes, re-verify the
   frozen tree (every file the READMEs reference exists), and do not
   re-run a live fetch: the data is already verified.
