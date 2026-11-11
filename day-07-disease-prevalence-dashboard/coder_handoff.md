# Day 07 — Disease Prevalence Dashboard: Coder Handoff

**Status:** CODER COMPLETE (AGENTS.md, stage 3) — 2026-11-11.
**Next role's first step (tester):** re-run every gate yourself in the
coder's venv — do not trust these numbers. Start with
`pytest tests/ -q` from the day folder AND from the portfolio root, then
the smoke gate on a fresh port (8503+ — the coder used 8502).

## 1. What was produced

```
day-07-disease-prevalence-dashboard/
├── README.md  requirements.txt  .gitignore  LICENSE  pyproject.toml
├── research_brief.md  plan.md  coder_handoff.md
├── data/
│   ├── README.md
│   ├── raw/sample_rows.json
│   └── processed/  (13 files: 6× prevalence_*.csv, 6× change_*.csv,
│       state_prevalence.csv, data_source.json, us_states.geojson)
├── notebooks/analysis.ipynb  (12 cells, executed, 0 error cells)
├── src/
│   ├── data_pipeline.py  metrics.py  make_charts.py  state_map.py
│   └── app.py
├── outputs/
│   ├── insights_summary.md
│   └── charts/  (4 PNGs)
├── screenshots/dashboard.png  (real capture, port 8502, 1440×6500)
└── tests/test_pipeline.py  (23 tests)
```

Files NOT in the plan's §5 tree (documented deviations, plan §11):
`src/state_map.py` and `data/processed/us_states.geojson` — the Plotly
geo choropleth cannot render offline (see §3 below); the state map is
matplotlib from the bundled geojson. `src/__init__.py` was NOT added
(namespace packages suffice; `python -m src.…` and pytest both work).

## 2. Verified numbers

- **Live fetch (2026-11-11, CDC Open Data, no key):** 12
  measure-releases; every count check matched its fetch exactly
  (2,958 rows per measure 2023; 3,145 per measure 2022). 36,600 county
  rows analysed (2,956 + 3,144 per measure); 2,956 matched counties per
  measure; 600 state rows.
- **pytest 23/23** passed from the day folder AND from the portfolio
  root (re-run after the last chart fix).
- **black --check + ruff check clean** (6 files).
- **Notebook:** nbconvert exit 0, 12 cells, 0 error cells.
- **Charts:** `make_charts` regenerates exactly 4 PNGs offline
  (01: 136,372 B; 02: 133,139 B; 03: 141,348 B; 04: 86,315 B).
- **Smoke (coder, port 8502):** HTTP 200 on `/` and on
  `/_stcore/health` ("ok"); server log 0 error lines; real screenshot
  1440×6500 (current file: 679,531 B — the pre-footnote-fix capture;
  the tester MUST re-capture it, the embedded charts changed since).
- **Hand validation:** Claiborne parish, LA, diabetes 2023 — 22.8% of
  11,034 adults = 2,516 est. cases (pipeline: 2,516, diff 0.0); Louisiana
  diabetes state rate 15.23% recomputed from the county CSV (naive mean
  16.50% — confirms the weighted roll-up).
- **data/ total:** 3,033,836 bytes; largest file 377,155 B (all < 1 MB).
- **Headline findings:** national diabetes 12.05% (2023) vs 11.97%
  (2022); WV top state for diabetes 15.88%; Greene County, AL top
  county 27.1%; heart disease median county change −0.50 pp (86.3% of
  counties down); diabetes +0.10 pp median. Full numbers in README /
  insights_summary / data_source.json.

## 3. Known gaps / defects fixed during coding (tester: verify the fixes)

1. **D-1 (fixed): Plotly geo maps rendered empty.** plotly.js fetches a
   topojson base map from cdn.plot.ly for ANY geo subplot
   (usa_110m.json with scope='usa', world_110m.json without); the fetch
   fails here (403 / tunnel failure, confirmed via CDP — the geo subplot
   throws, 0 paths drawn, even with a bundled geojson and all base
   layers off). Fix: state map is now matplotlib (`src/state_map.py`,
   bundled `us_states.geojson`); county map is a plain lon/lat Plotly
   scatter (no geo). Both verified rendering in the screenshot.
2. **D-2 (fixed): `src` not importable under Streamlit.** `streamlit run
   src/app.py` puts the script dir on sys.path, not the project root, so
   `from src.state_map import …` raised ModuleNotFoundError and the app
   showed an error page (caught by the screenshot). Fix: app.py inserts
   the project root into sys.path before the import. Verify the live app
   has no error banner.
3. **D-3 (fixed): chart 03 panel (b) label/bar mismatch.** The first
   fix attempt put up/down shares in the y-tick labels but indexed the
   measure names unordered while the bars were sorted — the bottom bar
   (CHD, −0.50 pp) was labelled "Diabetes". Fixed by indexing names with
   `order[i]`; re-verified visually: Diabetes +0.10 pp on top, CHD
   −0.50 pp at bottom.
4. **D-4 (fixed): chart footnotes truncated at the right edge.**
   Single-line fig.text overflowed (chart 01 cut at "have no 20").
   Fix: footnotes wrapped to 2 lines (textwrap, width 115) + bottom
   margin 0.06; chart 03/04 extra texts shortened. All 4 PNGs visually
   re-checked after the fix.
5. **D-5 (fixed): suppressed `*` row has no published value.** The
   brief assumed the footnote-`*` row keeps a value; verified live that
   Socrata omits null fields — exactly 1 row per measure in 2023 (Loving
   County, TX) has no `data_value`. The pipeline drops it and records
   `rows_without_published_value` (plan §11 updated).
6. **D-6 (fixed): US aggregate row omits `locationname`.** The raw US row
   has no locationname/geolocation; the parser now tolerates missing
   optional fields on that row and still fails loudly on bad county rows.
7. **D-7 (fixed): footnote columns missing from the fetch.** The first
   fetch's $select omitted `data_value_footnote_symbol`, so
   `footnote_star_rows` read 0. Added both footnote fields to the
   select; now 1 per measure in 2023, 0 in 2022.
8. **Open, not a defect:** the sidebar selectboxes look clipped at the
   left edge in the full-page (captureBeyondViewport) screenshot. This
   looks like a headless-capture artifact of the fixed-position sidebar,
   not an app defect — but the tester should confirm with a
   viewport-only screenshot.
9. **Known coverage facts (documented, not defects):** Kentucky and
   Pennsylvania have zero rows in the 2025 release (verified against the
   live API: 0 vs 120/67 in 2022); Loving County, TX suppressed in 2023;
   national 2022→2023 moves are partly compositional. All in README /
   data/README / insights / dashboard.

## 4. Handoff checklist (plan §9 — all satisfied)

- [x] venv exists with pinned deps installed (`.venv`, Python 3.12.3,
  exact versions from `requirements.txt` + `requirements-dev.txt`)
- [x] `black --check` + `ruff check` pass; `pytest` 23/23
- [x] `.gitignore` matches the plan (only `data/raw/*_synthetic.json`)
- [x] `screenshots/dashboard.png` is a real capture of the running app
  (port 8502) — **stale after the chart fixes; tester re-captures**
- [x] `data/` total < 5 MB, no file > 1 MB; no full raw JSONs on disk
- [x] `data_source.json` records live counts, coverage, M5 gap, footnote
  counts
- [x] Built only what §5 lists (+ the two documented files above); no
  extra web searches beyond the geojson source already cited in
  data/README.md

## 5. Commands to re-run

```bash
cd day-07-disease-prevalence-dashboard
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m src.data_pipeline --offline   # derived tables regen; data_source.json untouched
.venv/bin/python -m src.make_charts
.venv/bin/python -m jupyter nbconvert --to notebook --execute notebooks/analysis.ipynb --output /tmp/nb_check.ipynb --allow-errors
.venv/bin/python -m black --check src tests && .venv/bin/python -m ruff check src tests
.venv/bin/streamlit run src/app.py --server.port 8503 --server.address 127.0.0.1
```
