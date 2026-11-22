# Test report — Day 15 Political News Coverage Analyzer

**Role:** tester (stage 4 of 6). **Date:** 2026-11-22. **Tester verdict:
PASS WITH 3 DEFECTS** — all quality gates pass (pytest, coverage,
black/ruff/mypy, nbconvert, smoke, validate 11/11); the defects below
are all in wording/numbers on surfaces, none in the pipeline or the
statistics. No code was edited to make a test pass; the only files
the tester changed are `data/processed/sample_review.csv` (the
assigned review), `README.md` + `outputs/insights_summary.md`
(stale "Pending" agreement-rate wording only), `screenshots/dashboard.png`
(genuine re-capture on a fresh port), and this report. The notebook
was re-executed via nbconvert (its computed outputs update from the
filled CSV; its markdown text does not — see D-2/D-3).

## 1. Commands run + results (exact)

All in the coder's venv
`day-15-political-news-coverage-analyzer/.venv` (present; nothing
installed from scratch).

| Check | Command | Result |
|---|---|---|
| py_compile | `.venv/bin/python -m py_compile src/*.py tests/*.py` | exit 0 |
| pytest, day folder | `.venv/bin/python -m pytest tests/ -q --cov=src --cov-fail-under=30` | **38 passed**, coverage **55.99%** (bar 30) — coder's number reproduced exactly |
| pytest, repo root | `python -m pytest day-15-political-news-coverage-analyzer/tests/ -q --cov=day-15-political-news-coverage-analyzer/src --cov-fail-under=30` (from `60-day-data-ai-portfolio/`) | **38 passed**, coverage **55.99%** — same |
| pytest, after review filled | same day-folder command, re-run after §5 | **38 passed**, coverage **56.35%** (see note below) |
| black | `.venv/bin/python -m black --check src tests` | exit 0, 8 files unchanged |
| ruff | `.venv/bin/python -m ruff check src tests` | exit 0, all checks passed |
| mypy | `.venv/bin/python -m mypy src tests` (from inside the day folder) | exit 0, "Success: no issues found in 8 source files" |
| offline pipeline | `.venv/bin/python -m src.data_pipeline --offline` | exit 0; all 7 processed files **byte-identical** (sha256 checked before/after); `data_source.json` untouched (`source: "live"` preserved); 75 articles |
| offline pipeline, after review filled | same command | exit 0; reviewer columns preserved by design (`build_sample_review` merges existing `reviewer_topic`/`agree` by link); parsed review content verified identical to the §5 judgements (20 reviewed, 11 agree); file hash changed only through CSV-writer formatting |
| nbconvert | `.venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/analysis.ipynb` | exit 0, **12 cells, 0 error cells**; sample-review cell now prints `Agreement rate: 55.0% (11/20)` |
| orchestrator validate | `python3 agents/orchestrator.py --day 15 validate` (from the portfolio root) | **11/11 checks passed** (README 19,426 B; 4 charts; data/ 547 KB; screenshot 926,428 B; pytest 38 passed in 5.31 s) |

Coverage note: the post-review 56.35% (vs the coder's 55.99%) is
not a discrepancy — filling `sample_review.csv` makes the offline
test execute `build_sample_review`'s existing-review merge branch
(3 more statements covered, 361 missed vs 364). The coder's 55.99%
was reproduced exactly before the review was filled.

## 2. Hand-validation (plan §4.4 — recomputed by hand, `csv` + `math` only, no pipeline code)

Largest attention-share cell, confirmed from `topic_attention.csv`
(excluding `ALL` rows): **BBC News × Other**.

- Hand count: **19 of 31** articles.
- Hand share: **61.2903%**; committed `attention_share_pct` 61.2903% —
  **diff 0.0000 pp** (tolerance 0.01 pp). PASS.
- Hand Wilson 95% CI (z = 1.96): **[43.8238%, 76.2671%]**; committed
  [43.8238, 76.2671] — **diff 0.0000 pp / 0.0000 pp**. PASS.

VADER recompute (5 hand-picked titles, direct `vaderSentiment` call
vs pipeline `vader_compound`, 3 decimals): Leeds/Chelsea 0.886 vs
0.886; Mexican drug lord −0.945 vs −0.945; Google AI-in-schools
−0.153 vs −0.153; Mexico capture 0.275 vs 0.275; U.N. climate talks
−0.844 vs −0.844. **Max diff 0.000.** PASS. (The coder's 5-title
cross-check in `data_source.json` also reads 0.000.)

## 3. Spot-check of published numbers against the committed CSVs

All headline numbers in README + insights summary match the CSVs:

- Corpus: 75 articles — NYT 10, WSJ 0, Fox News 24, CNN 0, NPR 10,
  BBC News 31 (`articles.csv` counts identical; `per_outlet_n` in
  `data_source.json` identical).
- Topic shares (corpus-wide): Other 42.7% (32/75), Technology & AI
  22.7% (17), Elections & campaigns 9.3% (7), Crime & justice 6.7%
  (5), Education 5.3% (4), Healthcare 4.0% (3), Climate/Energy 4.0%
  (3), Foreign policy 2.7% (2), Economy 1.3% (1), Immigration 1.3%
  (1). All match `topic_attention.csv` `ALL` rows.
- Largest cell BBC News × Other 61.3% (19/31, Wilson 43.8%–76.3%);
  Fox News Technology & AI 37.5% (9/24, 21.2%–57.3%); NYT Other
  50.0% (5/10, 23.7%–76.3%); NPR Other / Technology & AI 30.0%
  each (3/10, 10.8%–60.3%). All match.
- Sentiment means (95% CI): NYT −0.046 [−0.483, 0.391], Fox News
  −0.127 [−0.388, 0.135], NPR −0.240 [−0.682, 0.202], BBC News
  0.048 [−0.187, 0.283]; medians 0.077 / −0.084 / −0.350 / 0.000;
  % pos/neu/neg 50.0/10.0/40.0, 29.2/16.7/54.2, 30.0/0.0/70.0,
  45.2/9.7/45.2. All match `sentiment_by_outlet.csv`. All four CIs
  include 0, as stated.
- By-topic sentiment: Fox Other 0.501 [0.035, 0.968] n=5, Fox
  Technology & AI −0.004 [−0.364, 0.355] n=9, BBC Other 0.185
  [−0.090, 0.460] n=19, BBC Technology & AI 0.207 [−0.597, 1.000]
  n=5. All match `sentiment_by_topic.csv`.
- Tests: chi-square χ²=31.94, df=27, p=0.234, min expected 0.13;
  collapsed χ²=18.90, df=12, p=0.091; permutation p=0.2214;
  Kruskal-Wallis H=2.09, p=0.553 (BBC Shapiro-Wilk p=0.022);
  pairwise Mann-Whitney U + Bonferroni all 6 corrected p=1.000
  (mean diffs 0.1744, 0.2875, 0.0935, 0.1131, −0.0808, −0.194);
  Fox ANOVA F=4.26, p=0.061; BBC ANOVA F=0.01, p=0.941. All match
  `stats_results.json` (one exception: the notebook markdown — see
  D-2).
- WSJ/CNN disclosure is honest and complete everywhere checked:
  README lines 52–54, 63–66; insights lines 7–9; `data/README.md`
  line 51; `data_source.json` (WSJ fetched 20, dropped outside
  window 20, final 0; CNN fetched 50, dropped outside window 46,
  dropped missing link/date 4, final 0; Fox 1 item dated 2026-11-25
  dropped). Both outlets kept with n=0 in every table/chart. No
  re-fetch was done. One wording error on the dashboard — see D-1.

## 4. Guardrail checks (plan §2.0)

- Guardrail sentence ("Sentiment measures the emotional tone of the
  words used; it is not a measure of factual accuracy, fairness, or
  political bias.") present in README line 12, insights line 3,
  `src/app.py` line 22, notebook cell markdown. PASS.
- No forbidden word ("bias", "biased", "leaning", "left", "right")
  used about an outlet in any chart title/label/caption or dashboard
  heading — verified visually on all 4 charts and the dashboard
  screenshot; the only "bias" occurrences are the mandated guardrail
  sentence itself and its short form in chart footnotes ("Sentiment
  is language tone, not factual bias."). The "left"/"right" hits in
  `src/make_charts.py` are matplotlib alignment arguments
  (`ha="left"`, stacked-bar `left=`), not chart text. The test
  suite's forbidden-word test passes. PASS.
- Topic dictionary in code byte-identical to the README listing:
  the suite's `test_dictionary_byte_identical_to_readme` passes
  (38/38). PASS.
- Same columns for every outlet: `topic_attention.csv` 70 rows =
  6 outlets × 10 topics + 10 `ALL` rows, WSJ/CNN rows present with
  n=0; `sentiment_by_outlet.csv` 6 rows; `sentiment_by_topic.csv`
  27 rows with `small_n` flags. PASS.
- `.gitignore` matches plan §3.4 (scaffold defaults + the
  `data/raw/*_synthetic.json` line; does NOT exclude `data/` or any
  raw XML). Data-size rule: `data/` 546,692 bytes (< 5 MB), no file
  > 1 MB (largest: `screenshots/dashboard.png` 926,428 B). PASS.
- Descriptive only: no model, no bias/leaning score, no causal
  claims found in code, docs or charts. PASS.

## 5. Sample review — COMPLETE (coder gap #1 closed)

The tester read each title **+ description** in `articles.csv`
and recorded `reviewer_topic` / `agree` for all 20 rows in
`data/processed/sample_review.csv` (5 each from NYT, Fox News, NPR,
BBC News; WSJ/CNN had no articles, so 20 not 30 — no rows invented).

**Agreement rate: 55.0% (11 of 20).** Per outlet: BBC News 2/5
(40.0%), Fox News 2/5 (40.0%), NPR 4/5 (80.0%), NYT 3/5 (60.0%).

Disagreements (9) — assigned → reviewer:

1. BBC "'Move on!' Former PMs pile in with advice for Andy
   Burnham, but will he listen?" — Technology & AI → Elections &
   campaigns (the `ai` keyword fires inside "said").
2. BBC "Mexican drug lord on FBI's 10 most wanted list arrested in
   shoot-out" — Healthcare → Crime & justice (`drug` misfires).
3. BBC "Theresa May 'aghast' at Burnham's EU plans and says 'Brexit
   is done'" — Other → Foreign policy.
4. Fox News "$275M Obama-era solar fraud case could net taxpayers
   $1B, but Trump's DOJ backs Biden dismissal" — Climate/Energy →
   Crime & justice (a fraud lawsuit, not an energy story).
5. Fox News "American Culture Quiz: Test yourself on maritime
   mysteries and patriotic performers" — Technology & AI → Other.
6. Fox News "Indonesia candy factory fire leaves multiple dead,
   dozens missing" — Crime & justice → Other (industrial accident,
   not a crime).
7. NPR "NPR's Senior Podcast Challenge: Early entries we love" —
   Technology & AI → Other.
8. NYT "Drones, Texts and Diversions: How Mexico Captured a Most
   Wanted Man" — Healthcare → Crime & justice (`drug` misfires).
9. NYT "What Machines Love" — Other → Technology & AI (about AI
   and aesthetic judgement).

The dictionary was not tuned. The 55.0% rate is now reported in
README.md (Sample review section + Limitations), in
`outputs/insights_summary.md` (Finding 1, Sample review section with
the full disagreement list, Limitations), and in the dashboard,
which computes it live from the CSV — the KPI shows 55.0% and the
sample-review section reads "Agreement rate: 55.0% (11 of 20
reviewed articles)". No "Pending" agreement-rate wording remains in
README.md or `outputs/insights_summary.md` (grep: no hits).
`data/README.md` never carried a "Pending" line. The notebook's
computed output now prints 55.0%; its static markdown still says
pending — see D-3.

## 6. Streamlit smoke gate (fresh port 8503)

- Command: `.venv/bin/streamlit run src/app.py --server.port 8503
  --server.fileWatcherType none --server.headless true`
  (8502 was the coder's port; never reused).
- HTTP 200 on `/`, HTTP 200 on `/_stcore/health` (body "ok").
  Server log clean: 0 errors / tracebacks.
- Screenshot: real full-page capture with Playwright, tall
  viewport 1000×7232 (Playwright `full_page` and scroll-and-stitch
  fail on Streamlit's inner scroll container, per the Day 14
  lesson). File `screenshots/dashboard.png`: **1000×7232,
  926,428 bytes (< 1 MB)**, md5 `8c17dbc49274f8303fcd1acbdfab0f72`
  — a genuine re-capture, NOT byte-identical to the coder's
  (1000×7232, 929,920 bytes, md5 `b5006913ce3ecec8e17d34c5990e02ef`),
  and it now shows the completed review (KPI "Sample-review
  agreement 55.0%"). The coder's file was overwritten with this
  capture.
- Server killed after capture; port 8503 verified free afterwards
  (curl HTTP 000, nothing listening, no streamlit process).
- Dashboard renders fully: guardrail sentence, limits banners,
  KPI row (75 articles; 4 of 6 outlets; 10 topics; largest share
  61.3% BBC News — Other; agreement 55.0%), all 4 charts, tables,
  test results, sample-review table (20 rows), methods and feed
  URLs. Cosmetic note (coder gap #7, already disclosed, not a
  defect): the KPI label truncates to "Sample-review agreem…" at a
  1000 px viewport; the value 55.0% displays fully.

## 7. Chart legibility verdict — PASS (all 4)

Each chart was opened and read at full resolution; all are to
scale, legible, titled with metric + window, footnoted with source
(RSS feeds, title + description text only, window, VADER
vaderSentiment 3.3.2), coverage (corpus N and N per outlet) and
the short guardrail sentence where space allows; every chart
states its N; no bias/leaning/left/right wording about outlets.

- **01_attention_share_by_topic.png** (280,522 B): six outlet
  facets, all 6 outlets shown (WSJ/CNN empty panels labelled
  n=0), bars labelled with share + n; values match
  `topic_attention.csv` (BBC Other 61.3% n=19, Fox Tech & AI
  37.5% n=9, NYT Other 50.0% n=5, NPR Other/Tech 30.0% n=3).
- **02_mean_sentiment_by_outlet.png** (111,862 B): dot-and-whisker
  with 95% CIs, VADER ±0.05 threshold lines, means labelled
  (−0.046, −0.127, −0.240, 0.048), n annotated, WSJ/CNN noted as
  n=0 with no mean shown. The "VADER ±0.05" labels sit close to
  the BBC whisker but remain readable.
- **03_sentiment_by_topic_heatmap.png** (237,162 B): 6 × 10 cells,
  value + n annotated, n < 5 hatched and labelled "small n", WSJ/
  CNN rows "no data", single diverging scale centred at 0.
  Spot-checked 14 cell values against `sentiment_by_topic.csv`
  (e.g. NYT Elections −0.76 n=2, NYT Healthcare 0.27 n=1, BBC
  Climate 0.66 n=1, Fox Immigration −0.97 n=1) — all match to
  2 decimals, including signs (verified by zoomed crop where the
  minus sign was unclear at full-image scale). Hatching slightly
  strikes through some annotations at small zoom, but all values
  are readable at full resolution.
- **04_sentiment_distribution.png** (116,311 B): 100% stacked
  bars, % labelled per segment, legend (positive/neutral/
  negative), WSJ/CNN rows "no articles in window (n=0)".
  Percentages match `sentiment_by_outlet.csv` exactly.

## 8. Defect list

### D-1 — Dashboard methods text understates the WSJ/CNN window drops (wrong numbers)
- **File:** `src/app.py`, lines 293–294 (Methods and limitations
  panel, rendered in the dashboard screenshot).
- **Text as written:** "WSJ and CNN n=0 — their feeds served older
  items (WSJ January 2025, CNN April 2023) and one item each was
  dated outside the window."
- **Why it is wrong:** per `data/processed/data_source.json`,
  WSJ had **20** items dropped outside the window and CNN had
  **46** (plus 4 with no parseable date) — not "one item each".
  (The "one item dated outside the window" belongs to Fox News:
  1 item dated 2026-11-25.) The README (lines 63–66), insights
  summary and `data/README.md` state the 20/46 counts correctly;
  only the dashboard text is wrong.
- **Fix for optimizer:** rewrite the sentence to "WSJ and CNN n=0
  — their feeds served older items (WSJ 20 items dated January
  2025, CNN 46 items dated April 2023 plus 4 with no parseable
  date), all dropped by the window filter." Re-capture the
  screenshot after the fix.

### D-2 — Notebook markdown states the wrong Kruskal-Wallis p-value
- **File:** `notebooks/analysis.ipynb`, line 377 (Q3 markdown
  cell 8).
- **Text as written:** "Chi-square (permutation p = 0.221) and
  Kruskal-Wallis (p = 0.548) both say no…"
- **Correct value:** p = **0.553** (`stats_results.json`
  `sentiment_by_outlet.p_value` = 0.55336; README and insights
  both say 0.553; the notebook's own executed output at line 340
  says "p=0.553"). The markdown contradicts the notebook's own
  computed output and the committed JSON.
- **Fix for optimizer:** change 0.548 → 0.553 in that markdown
  cell and re-run nbconvert.

### D-3 — Notebook markdown still says the sample review is pending
- **File:** `notebooks/analysis.ipynb`, cell 8 markdown
  ("The `reviewer_topic` column is for the tester to complete;
  the agreement rate is reported … once the review is done") and
  cell 11 Limitations markdown ("the sample-review agreement rate
  (pending) is the honest measure…").
- **Why it is stale:** the review is complete — 55.0% (11 of 20).
  Re-running nbconvert updates only the computed output (cell 9
  now prints 55.0%); the static markdown is untouched.
- **Fix for optimizer:** update both markdown lines to the
  completed 55.0% figure (per-outlet: BBC 2/5, Fox 2/5, NPR 4/5,
  NYT 3/5) and re-run nbconvert.

### Minor notes (not defects)
- **N-1:** `outputs/insights_summary.md` line 66 shows the BBC
  News × Other median as 0.219; the CSV value is 0.2185 (0.219
  under half-up rounding to 3 dp; Python's `round` gives 0.218).
  A 0.001 display-rounding difference only; no action needed.
- **N-2:** KPI label truncation at 1000 px ("Sample-review
  agreem…") — coder gap #7, already disclosed, cosmetic only.

## 9. Files the tester changed

- `data/processed/sample_review.csv` — `reviewer_topic` + `agree`
  filled for all 20 rows (agreement 11/20 = 55.0%).
- `README.md` — Sample review section and two Limitations bullets
  updated from "pending" to the completed 55.0% figure with
  per-outlet counts and the disagreement list.
- `outputs/insights_summary.md` — same four spots updated
  (Finding 1 line, Sample review section, Limitations).
- `screenshots/dashboard.png` — replaced with the tester's genuine
  re-capture on port 8503 (1000×7232, 926,428 bytes).
- `notebooks/analysis.ipynb` — re-executed via nbconvert (computed
  outputs now reflect the completed review; file 487,108 bytes).
- `test_report.md` — this file.
- No changes to `src/` or `tests/` (per the tester rule). D-1 lives
  in `src/app.py` and is left for the optimizer.

## 10. Summary for the optimizer

Coder's numbers reproduced exactly (pytest 38 passed, coverage
55.99% from both the day folder and the repo root; hand-validation
diffs 0.0000 pp; VADER max diff 0.000; validate 11/11). Sample
review complete at **55.0% (11/20)** — the dictionary's crudeness
is quantified, not hidden. Three defects to fix, all small: (D-1)
dashboard methods sentence "one item each" → WSJ 20 / CNN 46
dropped; (D-2) notebook markdown Kruskal-Wallis p 0.548 → 0.553;
(D-3) notebook markdown "(pending)" agreement-rate lines → 55.0%.
After fixing, re-run pytest + mypy and re-capture the screenshot
(the dashboard text changes), then hand to the publisher.
