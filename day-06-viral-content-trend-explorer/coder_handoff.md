# Coder handoff — Day 06 Viral Content Trend Explorer

**Status:** Coder complete, all gates passed (see §2). Built exactly to `plan.md` §5/§6 — no extra
files, no extra dependencies, no GitHub touch (publisher only). No `test_report.md` written
(tester's file).

## 1. What was produced (exact paths)

All under `~/workspace/goals/60-day-data-ai-portfolio/day-06-viral-content-trend-explorer/`:

- `src/trends.py` — pure trend math (topics, windows/weeks, views/day, momentum, classification,
  backtest, sensitivity). No I/O, no network.
- `src/sentiment.py` — Day 5's lexicon scorer copied verbatim (scoring functions only, no themes).
  Black reformatted the copy; logic verified identical via the Day 5 hand-computed cases (§2).
- `src/data_pipeline.py` — live fetch → clean → metrics → sentiment snapshot → save; `--offline` /
  `--use-cache` from committed cache; synthetic fallback (seed 42, n=300).
- `src/make_charts.py` — regenerates exactly the 4 PNGs in `outputs/charts/`, offline.
- `src/app.py` — Streamlit dashboard (`width='stretch'` throughout, no `use_container_width`).
- `notebooks/analysis.ipynb` — 16 cells, offline, `_find_root()` from the notebook file's location.
- `tests/test_pipeline.py` — 22 tests; scaffold `tests/test_smoke.py` deleted.
- `data/raw/` — 10 `search_<slug>_<prior|recent>.json` + `videos_details.json` +
  `channels_details.json` (no comment JSONs — 0 sentiment videos, see §3). Total `data/` 3.9 MB.
- `data/processed/videos.csv` (472 rows), `comments.csv` (header only, 0 rows),
  `trend_table.csv` (7 rows), `data_source.json` (`source: "live"`).
- `outputs/charts/01_trend_momentum.png`, `02_weekly_volume.png`, `03_views_velocity.png`,
  `04_sentiment_mood.png` (each 1800×825).
- `outputs/insights_summary.md`, `outputs/weekly_briefing.md` (generated from `trend_table.csv`
  by a script, not hand-typed).
- `README.md`, `data/README.md` (provenance, tensions, hand-validated metric, source-field
  correction), `requirements.txt` (pinned from the venv that ran), `pyproject.toml` / `.gitignore`
  (scaffold as-is).
- `screenshots/dashboard.png` — real capture of the running app (1440×6500, 576,011 bytes).
- `.venv/` — Python 3.12.3 with the pinned deps installed; tester provisions nothing.

## 2. Verified numbers

- **Fetch (live, 2026-11-10):** 500 candidates → 474 unique → **472 final videos** (236 recent /
  236 prior). Dropped: 0 live/upcoming, 2 no `viewCount`. Distinct channels 406.
- **Quota:** 1,019 units this run (10 searches × 100 + 10 `videos` + 9 `channels` + 0 comment
  calls — 1 unit over the ≤ 1,018 estimate because 406 channels needed 9 batched calls, not ≤ 3).
  Day total 2,238 units (~22% of the 10,000/day quota): probe 200 + first attempt 1,019 + this
  run 1,019 (first attempt fetched fine, then crashed on a 0-view division-by-zero before saving;
  fixed and raw responses are now persisted immediately after fetching).
- **Findings (from `trend_table.csv`):** AI & Machine Learning **accelerating** (+6.36 pp,
  +24.2%, 77 vs 62); SQL **accelerating** (+3.81 pp, +20.9%, 52 vs 43); Python **fading**
  (−8.05 pp, −21.6%, 69 vs 88); Other stable; Career / BI & Visualisation / General Data
  Analytics **insufficient data**. No mixed-signal flags (velocity undefined). Median engagement
  1.49% (in the 0.5–8% sanity range). `other` share 10.0%.
- **Velocity:** recent-window median views/day undefined for every topic (0 age-eligible videos);
  prior-window medians: Python 5.6/day (age 30, n=88), AI & ML 4.1/day (31, n=62), SQL 3.6/day
  (30, n=43).
- **Backtest: not computable** (W1–W3 and W8 empty — no hit/miss claimed). Age-guard sensitivity:
  no flips (undefined at both guards).
- **Sentiment: 0 videos, 0 comments analysed** (no recent video aged ≥ 7 days).
- **Sentiment copy verified** before use: "I love this tutorial, amazing work" → 0.7184 positive;
  "This is terrible and boring" → −0.6124 negative; "not good" → −0.25 negative; "very helpful" →
  0.3612 positive.
- **Hand-validated metric (Python, from `videos.csv`):** n_A 69, n_B 88; shares 29.24% / 37.29%;
  share change −8.05 pp; volume growth −0.2159; median views/day prior 5.5919 — matches
  `trend_table.csv` to the last digit (also asserted in the test suite).
- **Gates:** `black --check src tests` clean; `ruff check src tests` clean; **pytest 22 passed**
  from inside the day folder **and** from the repo root; notebook executes via nbconvert with
  **0 error cells**; `python -m src.make_charts` regenerates exactly 4 PNGs; pipeline verified
  live **and** offline from committed cache (offline reproduced `videos.csv` exactly, 472 rows).
- **Streamlit smoke (port 8502, never 8501):** HTTP 200 on `/` and on `/_stcore/health`
  ("ok"), clean server log; real full-page screenshot to `screenshots/dashboard.png`
  (1440×6500, 576,011 bytes); server killed afterwards, port 8502 verified free
  (connection refused, 0 streamlit processes). The screenshot caught a real bug during the
  smoke test (`itertuples()` dict-style access → TypeError, fixed; metrics now show counts).

## 3. Known gaps / defects (all reported, none tuned away)

1. **Truncation dominates the sample (the big one).** All 10 query-windows returned exactly 50
   videos, so each window holds only its newest videos: recent = 2026-11-08 → 11-09, prior =
   2026-10-08 → 10-10. W1–W3 and W6–W8 are empty; only 2 of 8 full weeks have ≥ 5 videos
   (target ≥ 7 — missed). Volume numbers are lower bounds. Classifications compare two truncated
   slices, not two full 30-day windows. No second page was fetched (plan forbids it); this is a
   planner decision to revisit, not a coder fix.
2. **Velocity / backtest / sentiment are all empty by consequence:** recent-window velocity
   undefined, backtest not computable, sentiment snapshot 0 videos / 0 comments. The dashboard,
   briefing, notebook and charts state this explicitly rather than filling anything in.
3. **`data/raw/videos_details.json` is 2,110,466 bytes (~2.0 MB)** — over the 1 MB/file guideline
   (474 detail records). Kept as the single file the plan's §5 tree requires. Total `data/` is
   3.9 MB, inside the 5 MB/day limit. Recorded in `data/README.md`.
4. **`data_source.json` source-field correction:** an offline verification run overwrote `source`
   to `"cache"`; the live record was restored by hand from the backed-up live file
   (generated 2026-11-10T14:20:41Z, quota 1,019) and the correction is recorded in
   `data/README.md`. Current value is `"live"` — verify it again at the frozen-tree check.
5. **Chart 03 quirk:** the "Other" prior-window median (49.2/day) dwarfs the other topics'
   bars (0.3–6.7/day) — drawn to scale, so the small bars are short; the numbers are labelled
   on every bar. Not a defect, but the tester should confirm legibility.
6. **Screenshot note:** `screenshots/dashboard.png` was captured before a final whitespace-only
   `black` reformat of `src/app.py` (no logic change); the tester re-takes the screenshot at
   their smoke gate anyway.
7. **Quota-cost discrepancy (1 vs 2 units for `commentThreads`) untested** — no comment calls
   were made in this build.

## 4. Tester's first step

In the coder's venv (provision nothing): `cd` into the day folder and run
`.venv/bin/python -m pytest tests/ -q`, then re-run the Streamlit smoke gate on a fresh port
(8502+): HTTP 200 on `/` and `/_stcore/health`, real screenshot to `screenshots/dashboard.png`,
kill the server, verify the port is free. Then recompute one topic's full momentum numbers by
hand from `videos.csv` (plan.md §4.6 item 3 — Python's numbers are in `data/README.md` to check
against) and record the result there.
