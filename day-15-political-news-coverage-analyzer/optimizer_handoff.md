# Optimizer handoff — Day 15 Political News Coverage Analyzer

**Role:** optimizer (stage 5 of 6). **Date:** 2026-11-22. **Verdict:
RELEASE-READY** — all 3 tester defects fixed, every gate re-run green,
no other files touched. No live API fetch was re-run; the data is the
tester's verified corpus.

## 1. What was fixed (exact files/lines)

### D-1 — Dashboard methods text understated the WSJ/CNN window drops
- **File:** `src/app.py`, lines 293–295 (Methods and limitations panel).
- **Before:** "WSJ and CNN n=0 — their feeds served older items (WSJ
  January 2025, CNN April 2023) and one item each was dated outside
  the window."
- **After:** "WSJ and CNN n=0 — their feeds served older items (WSJ 20
  items dated January 2025, CNN 46 items dated April 2023 plus 4 with
  no parseable date), all dropped by the window filter."
- Counts verified against `data/processed/data_source.json`
  (`outlets.WSJ.dropped_outside_window` = 20,
  `outlets.CNN.dropped_outside_window` = 46,
  `dropped_missing_link_or_date` = 4; Fox News 1 item dated 2026-11-25
  is the single out-of-window item). No other code changed.

### D-2 — Notebook markdown stated the wrong Kruskal-Wallis p-value
- **File:** `notebooks/analysis.ipynb`, cell 8 markdown (Q3 section).
- **Before:** "Chi-square (permutation p = 0.221) and Kruskal-Wallis
  (p = 0.548) both say no: …"
- **After:** "… Kruskal-Wallis (p = 0.553) both say no: …"
- 0.553 confirmed in `data/processed/stats_results.json`
  (`sentiment_by_outlet.p_value` = 0.55336), README, insights summary,
  and the notebook's own executed output (cell 7 prints p=0.553).

### D-3 — Notebook markdown still said the sample review was pending
- **File:** `notebooks/analysis.ipynb`, cell 8 markdown (Sample review
  section) and cell 11 markdown (Limitations).
- **Before (cell 8):** "The `reviewer_topic` column is for the tester
  to complete; the agreement rate is reported next to every topic
  finding once the review is done."
- **After (cell 8):** "The review is complete: agreement rate 55.0%
  (11 of 20 reviewed articles) — BBC News 2/5, Fox News 2/5, NPR 4/5,
  NYT 3/5 — reported next to every topic finding."
- **Before (cell 11):** "the sample-review agreement rate (pending) is
  the honest measure of the dictionary's trustworthiness."
- **After (cell 11):** "the sample-review agreement rate 55.0% (11 of
  20; BBC News 2/5, Fox News 2/5, NPR 4/5, NYT 3/5) is the honest
  measure of the dictionary's trustworthiness."
- The notebook was re-executed via nbconvert after the edits (see §2);
  cell 9 output now prints "Agreement rate: 55.0% (11/20)".
- The one remaining "pending" string in the notebook is the code-cell
  else-branch (`print("Agreement rate: pending tester review")`,
  cell 9) — legitimate conditional code that only runs when no review
  rows exist. Left untouched, per "fix only the 3 defects".

### README coverage number corrected (optimizer's own update)
- **File:** `README.md`, Validation section ("Tests" bullet).
- **Before:** "coverage measured over `src/` (see `coder_handoff.md`
  for the exact number)" — that pointer gave the coder's pre-review
  55.99%, now stale.
- **After:** "coverage 56.35% measured over `src/` (threshold 30; the
  coder's 55.99% was measured before the sample review was filled —
  filling the review covers 3 more statements, see `test_report.md`
  §1)." No follow-up count-fix commit is needed: the README now states
  the final measured number (re-verified below, 38 passed / 56.35%
  from both the day folder and the repo root).

## 2. Verified numbers (commands + exit codes)

All run in the day folder's venv
`day-15-political-news-coverage-analyzer/.venv` unless noted.

| Check | Command | Result |
|---|---|---|
| black | `.venv/bin/python -m black --check src tests` | exit 0, 8 files unchanged |
| ruff | `.venv/bin/python -m ruff check src tests` | exit 0, all checks passed |
| mypy | `.venv/bin/python -m mypy src tests` (inside day folder) | exit 0, "Success: no issues found in 8 source files" |
| pytest, day folder | `.venv/bin/python -m pytest tests/ -q --cov=src --cov-fail-under=30` | **38 passed**, coverage **56.35%** (bar 30), exit 0 |
| pytest, repo root | `day-15-.../.venv/bin/python -m pytest day-15-political-news-coverage-analyzer/tests/ -q --cov=day-15-political-news-coverage-analyzer/src --cov-fail-under=30` (from `60-day-data-ai-portfolio/`) | **38 passed**, coverage **56.35%**, exit 0 |
| nbconvert | `.venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/analysis.ipynb` | exit 0, **12 cells, 0 error cells**; notebook 487,242 bytes |
| orchestrator validate | `python3 agents/orchestrator.py --day 15 validate` (from portfolio root) | **11/11 checks passed** (README 19,549 B; 4 charts; data/ 547 KB; screenshot 927,816 B; pytest 38 passed in 6.13 s), exit 0 |
| Streamlit smoke, fresh port 8504 | `.venv/bin/streamlit run src/app.py --server.port 8504 --server.fileWatcherType none --server.headless true` (system `python3` + Playwright for the capture) | HTTP 200 on `/`, HTTP 200 on `/_stcore/health` (body "ok"), server log clean (0 tracebacks/errors); page text verified to contain the corrected "WSJ 20 items dated January" / "CNN 46 items" sentence, "55.0%", and the guardrail sentence; server killed (returncode 0), **port 8504 verified free** afterwards |
| Screenshot | Playwright, viewport 1000×7232, full-page capture → `screenshots/dashboard.png` | **1000×7232, 927,816 bytes (< 1 MB)**, md5 `11e7b9bb5530a18a4141c13c689363d0` — a genuine re-capture, not the tester's file (1000×7232, 926,428 B, md5 `8c17dbc49274f8303fcd1acbdfab0f72`) |

Versions (venv, Python 3.12.3): pandas 3.1.1, numpy 2.5.4,
scipy 1.18.1, matplotlib 3.11.2, streamlit 1.66.1, feedparser 6.0.14,
vaderSentiment 3.3.2, pytest 9.2.0, pytest-cov 7.1.0, black 26.10.1,
ruff 0.17.4, mypy 2.4.1, jupyter 1.1.1, nbformat 5.11.1,
requests 2.34.2. `requirements.txt` pins 12 `==` versions.

Note on the repo-root pytest invocation: bare `python`/`python3` at
the portfolio root has no pytest installed (system python3: "No module
named pytest"); the equivalent run used the day venv's python from the
repo root, exactly as the tester did, and reproduced 38 passed /
56.35%.

## 3. Spot-check of published numbers against the committed CSVs

Re-checked with `csv` + `json` only (no pipeline re-run):

- Corpus: 75 articles — NYT 10, WSJ 0, Fox News 24, CNN 0, NPR 10,
  BBC News 31. Matches README, insights, dashboard.
- Corpus-wide topic shares: Other 42.7% (32/75), Technology & AI
  22.7% (17), Elections & campaigns 9.3% (7). Match.
- Largest cell BBC News × Other 61.2903% (19/31), Wilson 95% CI
  [43.8238, 76.2671]. Match (hand-validation diff 0.0000 pp, per
  test report §2).
- Sentiment means: NYT −0.046 [−0.483, 0.391], Fox News −0.127
  [−0.388, 0.135], NPR −0.240 [−0.682, 0.202], BBC News +0.048
  [−0.187, 0.283]; all four 95% CIs include 0. Match
  `sentiment_by_outlet.csv`.
- Tests: chi-square χ²=31.94, df=27, p=0.234; collapsed p=0.091;
  permutation p=0.2214; Kruskal-Wallis H=2.09, p=0.553. Match
  `stats_results.json` and every surface (notebook markdown now
  included).
- Sample review: 55.0% (11 of 20) — BBC News 2/5, Fox News 2/5,
  NPR 4/5, NYT 3/5. Match `sample_review.csv` and every surface
  (README, insights, notebook markdown + executed output, dashboard
  KPI).

## 4. Guardrail + size checks

- Guardrail sentence ("Sentiment measures the emotional tone of the
  words used; it is not a measure of factual accuracy, fairness, or
  political bias.") present in README, `outputs/insights_summary.md`,
  `src/app.py` (line 22, `GUARDRAIL_SENTENCE`), and the notebook
  (cell 0 markdown). PASS.
- No forbidden wording ("bias/leaning/left/right" about outlets)
  introduced by these edits: the only "bias"/"leaning" hits in the
  edited files are the mandated guardrail sentence itself and the
  pre-existing "no bias score, no leaning score" descriptive-only
  statements; the `ha="left"` / `left=` hits in `make_charts.py`
  are matplotlib alignment arguments, unchanged. PASS.
- `.gitignore` matches plan §3.4 (scaffold defaults +
  `data/raw/*_synthetic.json`); it does NOT exclude `data/` or any
  raw XML. Data-size rule: `data/` 547,011 bytes (< 5 MB), no file
  > 1 MB (largest: `screenshots/dashboard.png` 927,816 B). PASS.
- `data/processed/data_source.json` was NOT touched by this stage:
  still `source: "live"`, `fetch_date: 2026-11-22`, with the
  `manual_validation` section present (see §5). No `--live` /
  `--use-cache` run was done.

## 5. Known gaps (disclosed limitations, not defects)

- **Sample-review agreement 55.0% (11 of 20) is a disclosed
  limitation, not a defect to fix.** The frozen dictionary is NOT
  tuned: 9 disagreements are listed in `test_report.md` §5 (notably
  `ai` firing inside "said" and `drug` sending crime reporting to
  Healthcare). The rate is reported next to every topic finding on
  all surfaces.
- **WSJ and CNN n=0.** Both feeds served only items outside the
  2026-11-08–2026-11-22 window (WSJ 20 items, January 2025; CNN 46
  items, April 2023, plus 4 with no parseable date). Both outlets
  are kept with n=0 in every table/chart; the sample is 20 articles,
  not 30, because there was nothing to sample from them.
- **`data_source.json` `manual_validation` section is dropped by a
  `--live` (or `--use-cache`) re-run.** The section exists only in
  the committed file (added by hand after the live run); the
  pipeline's `run_pipeline` builds the record from scratch and never
  writes `manual_validation` (`src/data_pipeline.py`, record dict
  ~lines 780–845). `--offline` is safe (it skips writing
  `data_source.json` when a live record exists, tested). Do not
  re-run `--live` without re-adding the section afterwards.
- Minor notes carried from the tester (no action): N-1, the insights
  summary shows the BBC News × Other median as 0.219 vs CSV 0.2185
  (0.001 display-rounding difference); N-2, the dashboard KPI label
  truncates to "Sample-review agreem…" at a 1000 px viewport
  (value 55.0% displays fully).

## 6. Files changed by the optimizer

- `src/app.py` — D-1 wording fix only (lines 293–295).
- `notebooks/analysis.ipynb` — D-2 + D-3 markdown fixes, then
  re-executed via nbconvert (12 cells, 0 errors).
- `README.md` — coverage number updated 55.99% (stale pointer) →
  56.35% (final measured).
- `screenshots/dashboard.png` — genuine re-capture on fresh port
  8504 (1000×7232, 927,816 bytes).
- `optimizer_handoff.md` — this file.
- No changes to `src/` logic, `tests/`, `data/`, charts, insights
  summary, `data/README.md`, `coder_handoff.md`, or `test_report.md`.

## 7. Publisher's first step

**Frozen-tree check immediately before pushing:** re-verify every
file the READMEs reference exists on disk — 4 charts in
`outputs/charts/`, `screenshots/dashboard.png` (927,816 B, this
optimizer's re-capture), the 6 processed CSVs + `data_source.json`
(with `manual_validation` intact), `notebooks/analysis.ipynb`,
`data/raw/` XMLs — then push per the Day 14 lesson: **upload the 5
PNGs (4 charts + dashboard screenshot) BEFORE the code push so CI
never sees an incomplete tree.** Validate is 11/11 and pytest is
38 passed / 56.35% — nothing needs rebuilding.
