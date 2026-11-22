# Coder handoff — Day 15 Political News Coverage Analyzer

**Status:** BUILT AND VERIFIED — all coder gates pass (see §2).
**Date:** 2026-11-22. **Role:** coder (stage 3 of 6).

## 1. What was produced

Day folder: `day-15-political-news-coverage-analyzer/`
(all paths relative to the portfolio root `60-day-data-ai-portfolio/`)

- `README.md` — problem, audience, dataset table, method, frozen topic
  dictionary verbatim, headline findings, chart thumbnails, validation,
  limitations, attribution.
- `requirements.txt` — pinned `==` versions verified in the build venv
  (Day 14 stack + feedparser 6.0.14 + vaderSentiment 3.3.2; no geopandas,
  no scikit-learn, no openpyxl).
- `.gitignore` — scaffold default + `data/raw/*_synthetic.json`; does
  NOT exclude `data/` or any raw XML.
- `pyproject.toml`, `.pre-commit-config.yaml`, `LICENSE` — scaffold files,
  kept as-is.
- `research_brief.md`, `plan.md` — not rewritten (per task).
- `data/README.md` — provenance, fetch outcome, metric definitions,
  dictionary, cross-checks, manual validation, sample-review method.
- `data/raw/nyt_rss.xml` (21,419 B), `wsj_rss.xml` (13,317 B),
  `fox_rss.xml` (258,357 B), `cnn_rss.xml` (130,144 B),
  `npr_rss.xml` (14,301 B), `bbc_rss.xml` (26,437 B) — live fetch,
  committed as the provenance record.
- `data/processed/data_source.json` (8,730 B), `articles.csv` (75 rows),
  `topic_attention.csv` (70 rows), `sentiment_by_outlet.csv` (6 rows),
  `sentiment_by_topic.csv` (27 rows), `sample_review.csv` (20 rows),
  `stats_results.json`.
- `notebooks/analysis.ipynb` — 12 cells, `_find_root()` from the notebook
  file's own location, runs offline via nbconvert, exit 0, 0 error cells.
- `src/__init__.py`, `src/data_pipeline.py`, `src/topics.py`
  (frozen dictionary verbatim from plan §4.1), `src/sentiment.py`,
  `src/stats.py`, `src/make_charts.py`, `src/app.py`
  (`width="stretch"` throughout; no deprecated `use_container_width`).
- `src/requirements.txt` — pre-existing Streamlit Cloud shim (as in Day 14).
- `outputs/insights_summary.md` — one finding per §2.1 question with exact
  numbers, tables, test results, sample-review status, limitations.
- `outputs/charts/01_attention_share_by_topic.png` (280,522 B),
  `02_mean_sentiment_by_outlet.png` (111,862 B),
  `03_sentiment_by_topic_heatmap.png` (237,162 B),
  `04_sentiment_distribution.png` (116,311 B) — exactly 4, all legible,
  footnoted with source + coverage + VADER version.
- `screenshots/dashboard.png` — real capture of the running app,
  1000×7232, 929,920 bytes (< 1 MB).
- `tests/test_pipeline.py` — 38 tests. Scaffold `tests/test_smoke.py`
  deleted (per plan §5).
- `.venv/` — build venv with pinned deps installed (provision nothing).

## 2. Verified numbers

**Corpus (live fetch 2026-11-22, all six feeds HTTP 200):**
75 articles — NYT 10, WSJ 0, Fox News 24, CNN 0, NPR 10, BBC News 31.
Fetched: NYT 10, WSJ 20, Fox 25, CNN 50, NPR 10, BBC 33 (147 items).
Dropped outside window: WSJ 20, CNN 46, Fox 1 (dated 2026-11-25, after
the fetch date), BBC 2. Dropped missing link/date: CNN 4. Duplicates: 0.
Window actually achieved: NYT 2026-11-20–2026-11-22; Fox 2026-11-22;
NPR 2026-11-21–2026-11-22; BBC 2026-11-11–2026-11-22; WSJ/CNN none.
Raw XML total 463,975 bytes; `data/` total 546,692 bytes (< 5 MB);
no file > 1 MB. GDELT: skipped (optional only; recorded in
`data_source.json`).

**Topics (corpus-wide):** Other 42.67% (32/75), Technology & AI 22.67%
(17), Elections & campaigns 9.33% (7), Crime & justice 6.67% (5),
Education 5.33% (4), Healthcare 4.0% (3), Climate/Energy 4.0% (3),
Foreign policy 2.67% (2), Economy 1.33% (1), Immigration 1.33% (1).
Largest cell: BBC News × Other 61.29% (19/31).

**Sentiment (mean VADER compound, 95% CI):** NYT −0.046 [−0.483, 0.391],
n=10; Fox News −0.127 [−0.388, 0.135], n=24; NPR −0.240 [−0.682, 0.202],
n=10; BBC News 0.048 [−0.187, 0.283], n=31; WSJ/CNN n=0.

**Tests:** chi-square topic × outlet χ²=31.94, df=27, p=0.234 (min
expected 0.13 → collapsed χ²=18.90, df=12, p=0.091 → permutation
p=0.2214, 10,000 shuffles, seed 42 — the conclusion rests on the
permutation p-value). Kruskal-Wallis H=2.09, p=0.553 (BBC News failed
Shapiro-Wilk, p=0.022); pairwise Mann-Whitney U + Bonferroni: all 6
corrected p=1.000. By-topic ANOVA: Fox F=4.26, p=0.061; BBC F=0.01,
p=0.941.

**Hand-validation (plan §4.4, independent `csv`+`math` recomputation,
no pipeline code):** BBC News × Other 19 ÷ 31 × 100 = 61.2903%
(committed 61.2903%, diff 0.0000 pp); Wilson 95% CI [43.8238%,
76.2671%] (committed [43.8238, 76.2671], diff 0.0000 pp). Tolerance
0.01 pp. VADER 5-title recompute: max diff 0.000 at 3 decimals
(pipeline cross-check of 5 further titles also 0.000). Recorded in
`data_source.json` under `manual_validation` and in `data/README.md`.

**Quality gates (all exit 0):**
- `.venv/bin/python -m black --check src tests` — clean.
- `.venv/bin/python -m ruff check src tests` — clean.
- `.venv/bin/python -m mypy src tests` (from inside the day folder) —
  clean, no issues in 8 source files.
- `.venv/bin/python -m pytest tests/ -q --cov=src --cov-fail-under=30` —
  **38 passed**, coverage **55.99%** (bar 30). Also passes from the
  portfolio root (38 passed, same coverage).
- `jupyter nbconvert --to notebook --execute --inplace
  notebooks/analysis.ipynb` — exit 0, 12 cells, 0 error cells;
  notebook 487,163 bytes.
- Streamlit smoke, fresh port **8502** (`--server.fileWatcherType none` —
  the default watcher hits the sandbox inotify limit, as on Day 14):
  HTTP **200** on `/` and on `/_stcore/health`, server log clean
  (0 errors); real full-page screenshot `screenshots/dashboard.png`
  (1000×7232, 929,920 bytes; tall-viewport capture — Playwright
  `full_page=True` does not capture Streamlit's inner scroll container);
  server killed, port 8502 verified free.
- `python3 agents/orchestrator.py --day 15 validate` (from the portfolio
  root) — **11/11 checks passed**.
- Offline check: `--offline` run leaves `data_source.json` byte-identical
  (sha256 verified before/after in the test suite); regenerated shares
  match within 0.01 pp.

**Versions (Python 3.12.3):** pandas 3.1.1, numpy 2.5.4, scipy 1.18.1,
matplotlib 3.11.2, plotly 7.1.0, streamlit 1.66.1, requests 2.34.2,
pytest 9.2.0, jupyter 1.1.1, nbformat 5.11.1, feedparser 6.0.14,
vaderSentiment 3.3.2; dev: ruff 0.17.4, black 26.10.1, mypy 2.4.1,
pytest-cov 7.1.0.

## 3. Known gaps / defects

1. **WSJ and CNN returned no usable articles in the window (n=0).**
   Their feeds served stale items (WSJ: 20 items dated January 2025;
   CNN: 46 items dated April 2023 + 4 with no parseable date). This is
   the data the feeds actually served on 2026-11-22, not a code defect.
   Both outlets are kept in every table/chart with n=0 and the fact is
   stated on every surface. Chi-square and sentiment tests exclude them
   (recorded in `stats_results.json`).
2. **Sample review is 20 articles, not 30.** The plan's 30-article
   design (5 per outlet across all six) cannot be supplied by the
   collected corpus — WSJ/CNN had no articles to sample. 5 each were
   drawn from NYT, Fox News, NPR, BBC News (seed 42, fixed once drawn).
   `reviewer_topic` / `agree` are blank, pending the tester (see §4);
   the agreement rate is shown as "Pending" in README / insights /
   dashboard until the review is done. The dictionary was not tuned.
3. **`data_source.json` `manual_validation` section is added by a
   post-pipeline step** (independent recomputation script). A `--live`
   re-run of the pipeline regenerates `data_source.json` and drops
   that section — re-run the hand-validation afterwards. This is noted
   in the JSON itself. `--offline` never touches the file.
4. **Rolling feeds shift between fetches.** The NPR feed changed by one
   article between the first and second live fetch (mean −0.245 →
   −0.240; Kruskal-Wallis H 2.12 → 2.09). All committed files and all
   numbers in the docs are from the final 14:24 run and were verified
   against those files; an earlier draft number was corrected before
   handoff (Kruskal-Wallis H/p and the NPR CI in README + insights).
5. **Dictionary crudeness is visible in the sample:** the frozen keyword
   `ai` matches as a substring inside ordinary words ("said"), and
   `drug` assigns crime reporting to Healthcare. Frozen per plan —
   do not tune; the sample-review agreement rate quantifies it.
6. **Sentiment CIs are clipped to [−1, +1]** (t-intervals for n=2
   otherwise exceed the compound range). Documented in
   `data_source.json` metric definitions.
7. **Dashboard cosmetics:** the KPI label "Sample-review agreement"
   truncates to "Sample-review agreem…" at a 1000 px viewport (value
   "Pending" displays fully); dataframes scroll horizontally (standard
   Streamlit behaviour, as on Day 14 — not a defect).
8. **Screenshot tooling:** the capture used the system Playwright +
   Chromium (as on Day 14); Playwright is NOT in `requirements.txt`
   (screenshot tooling only, not a runtime dependency).
9. **Notebook chart images are downscaled JPEG copies** (1100 px,
   quality 82) so the notebook stays under 1 MB (487,163 B); the
   standalone PNGs in `outputs/charts/` are full resolution.
10. **GDELT was skipped** (optional cross-check only; researcher
    verified it rate-limits). Recorded in `data_source.json`.

## 4. Tester's first step

From inside the day folder, in the coder's venv (`.venv/` exists with
pinned deps installed — provision nothing), run
`.venv/bin/python -m pytest tests/ -q --cov=src --cov-fail-under=30`
and confirm 38 passed, then re-run the Streamlit smoke on a fresh
port (8503+, `--server.fileWatcherType none`) and check the screenshot
against the app. Then complete the sample review: read the 20 titles
in `data/processed/sample_review.csv`, fill `reviewer_topic` (and
`agree`) for each row, and verify the hand-validation metric from
`data/processed/articles.csv` (suggested: BBC News × Other, 19/31 =
61.2903%, Wilson CI [43.8238, 76.2671]).
