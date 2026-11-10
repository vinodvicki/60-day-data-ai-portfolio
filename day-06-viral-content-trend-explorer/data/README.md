# Data provenance — Day 06 Viral Content Trend Explorer

## Source

- **Provider:** YouTube Data API v3 (`https://youtube.googleapis.com/youtube/v3`), via the
  `custom.youtube` connector helper (`~/workspace/custom-connectors/custom.youtube/bin/youtube.py`).
  Read-only API-key auth; the key is held by the connector and never appears in any file, env var,
  log, command argument, or the repo.
- **Endpoints used:** `search.list` (10 calls), `videos.list` (10 batched calls, ≤ 50 IDs each),
  `channels.list` (9 batched calls, ≤ 50 IDs each), `commentThreads.list` (0 calls — no video
  qualified for the sentiment snapshot, see below).
- **Access date (fetch date):** 2026-11-10. Snapshot dates: Day 4 frame 2026-11-08, fresh fetch
  2026-11-10.
- **Queries (5, the same five as Day 4):** `data analytics`, `machine learning tutorial`,
  `Python data analysis`, `artificial intelligence explained`, `SQL tutorial`. Each with
  `order=date`, `maxResults=50`, one page per query-window.
- **Windows:** prior 2026-09-11T00:00:00Z → 2026-10-11T00:00:00Z (Window B); recent
  2026-10-11T00:00:00Z → 2026-11-10T00:00:00Z (Window A). The boundary instant
  2026-10-11T00:00:00Z belongs to Window A.
- **Licence / attribution:** public YouTube video metadata and comment text under the YouTube API
  Services Terms of Service and Developer Policies. Attribution: "Data from the YouTube Data API
  v3" with a link to [YouTube's Terms of Service](https://www.youtube.com/t/terms). Code in this
  repo is MIT; YouTube data is under separate YouTube terms, not MIT.

## Fetch outcome

- **Quota used (this run): 1,019 units** — 10 searches × 100 = 1,000 + 10 `videos` calls × 1 = 10
  + 9 `channels` calls × 1 = 9 + 0 `commentThreads` calls. One unit over the plan's ≤ 1,018
  estimate, because 406 distinct channels needed 9 batched `channels` calls, not ≤ 3.
- **Quota used (whole day, all attempts): 2,238 units (~22% of the 10,000/day free tier)** —
  researcher's 200-unit probe + a first coder attempt (1,019 units: fetch succeeded, then the
  pipeline crashed on a division-by-zero for a 0-view video before saving; fixed, raw responses
  are now persisted immediately after fetching) + the successful run (1,019 units).
- **Truncation — all 10 query-windows returned exactly 50 items (`truncated: true` for every
  query-window in `data_source.json`).** Each window therefore holds only its newest videos:
  the recent window effectively covers 2026-11-08 → 11-09 and the prior window 2026-10-08 →
  10-10. Weekly buckets W1–W3 and W6–W8 are empty; W9 is partial (5 days). Volume numbers are
  lower bounds for their windows. No second page was fetched (the plan forbids it); the
  truncation is stated, not hidden.
- **Sentiment snapshot: 0 videos, 0 comments.** The snapshot needs the top video by
  `views_per_day` per topic in the recent window, aged ≥ 7 days — all 236 recent videos were
  published 2026-11-08/09, so no video qualifies in any of the 5 topics. No `commentThreads`
  calls were made. This is a consequence of the truncation, not a scoring failure.

## Row counts and coverage

| Step | Count |
|---|---|
| Search candidates (10 query-windows × 50) | 500 |
| Unique after dedupe by `videoId` | 474 |
| Dropped: live/upcoming or published outside the windows | 0 |
| Dropped: no `viewCount` (missing from `videos` response) | 2 |
| **Final videos in `data/processed/videos.csv`** | **472** (236 recent / 236 prior) |
| Distinct channels | 406 |
| Sentiment videos / comments analysed | 0 / 0 |

- **Per query-window:** every query-window returned 50 items, all truncated (see
  `data_source.json` → `per_query_window`).
- **Topics:** python 157, ai_ml 139, sql 95, other 47, general 17, bi_viz 10, career 7.
  `other` is 10.0% of the sample (target ≤ 30% — met, taxonomy not re-tuned).
- **Weekly coverage:** W4 20, W5 216, W9 236; W1–W3, W6–W8 empty. Only 2 of 8 full weeks
  have ≥ 5 videos (target ≥ 7 — **missed**, diagnosed as truncation, not tuned away).
- **Channel concentration:** recent window 202 distinct channels, largest single channel 3.4%;
  prior window 209 distinct channels, largest 2.5%. No channel exceeds 20% in either window.
- **Overlap with the Day 4 frame:** 0 videos.
- **Missing values:** 10 videos have 0 views (engagement rates NaN, never filled with 0);
  25 videos missing `likeCount`, 1 missing `commentCount`, 0 missing `subscriberCount`.
- **Shorts share:** recent 53.8%, prior 32.6%.
- **Median engagement rate:** 1.49% (Day 4 sanity range 0.5–8% — inside).

## Layer A / Layer B split

- **Layer A (context only):** Day 4 frame, 244 videos, fetched live 2026-11-08, relevance-ranked
  snapshot. Read from
  `../day-04-youtube-video-performance-analyzer/data/processed/videos.csv`. Never mixed into
  the momentum math (different snapshot date, different selection method). The Day 4 frame itself
  is never edited.
- **Layer B (the trend sample):** the 472 fresh videos above. All momentum, velocity and
  classification numbers come from this layer only.

## Commit rule for data files

- Small raw data IS committed: files under 1 MB each (under 5 MB per day folder) are part of the
  deliverable — `.gitignore` must NOT exclude `data/`. Anything larger must be `.gitignore`d and
  regenerated by the pipeline.
- **Known size exception:** `data/raw/videos_details.json` is 2,110,466 bytes (~2.0 MB) — it
  exceeds the 1 MB/file guideline because 474 video detail records are ~4.5 KB each. It is kept
  as the single file the plan's §5 tree requires (splitting it would deviate from the plan).
  Total `data/` is 3.9 MB, inside the 5 MB/day limit; every other raw file is < 1 MB.
  Synthetic fallback output goes only to `data/raw/*_synthetic.json` and is git-ignored; it must
  never overwrite the live cache.

## `data_source.json` source-field correction (§3.5)

An offline pipeline run (`--offline`, used to verify the cache reproduces the live outputs)
overwrote `data/processed/data_source.json`'s `source` field to `"cache"`. The live record was
restored by hand from the backed-up live file (generated 2026-11-10T14:20:41Z, quota 1,019,
source `"live"`), byte-for-byte. The offline run reproduced `videos.csv` exactly (472 rows,
identical trend table), so the restored file describes the live fetch truthfully.

**Fixed at the source (optimizer, 2026-11-10):** `src/data_pipeline.py::save_outputs` now skips
writing `data_source.json` on an offline/cache run when an existing live record is present, so
the overwrite cannot recur; `tests/test_pipeline.py::test_offline_run_reproduces_live_outputs`
asserts the file is byte-identical after an `--offline` run.

## Manual validation (one metric, by hand)

**Topic: Python — full momentum numbers recomputed by hand from `videos.csv`** (and checked by
`tests/test_pipeline.py::test_committed_csv_matches_trend_table`):

- n_A = 69, n_B = 88 (236 videos per window)
- topic share recent = 69 / 236 × 100 = 29.24%; prior = 88 / 236 × 100 = 37.29%
- share change = 29.24 − 37.29 = **−8.05 pp**
- volume growth = (69 − 88) / 88 = **−0.2159 (−21.6%)**
- median views/day prior (age ≥ 7 days, n=88, median age 30 days) = **5.5919**;
  recent-window median is undefined (0 age-eligible videos)
- classification: **fading** (share ≤ −3 pp and growth ≤ −20%, n ≥ 10 both windows)

All values match `data/processed/trend_table.csv` to the last digit. The tester re-verifies one
topic's full momentum numbers by hand per plan.md §4.6 item 3.

## Validation results

- **Holdout backtest: not computable.** Weeks W1–W3 hold no videos and W8 is empty, so there is
  no train growth to predict from and no test week. No hit/miss is claimed.
- **Age-guard sensitivity:** no topic's velocity direction flips between the 7-day and 14-day
  guards, because velocity change is undefined at both guards.
- **Sanity checks:** zero duplicate `videoId`s; 100% duration parse, all > 0 s; no `publishedAt`
  in the future or before 2005-04-23; no `publishedAt` outside the two windows; median
  engagement rate 1.49% (in range); median views/day (age ≥ 7 days) 5.1 > 0.

## Licence tensions, stated honestly (no legal certainty claimed)

1. **Snapshot vs historical trend** — the API gives no historical daily statistics, so "trend"
   is a comparison of two publish-date cohorts, resolved by design; no output presents a cohort
   comparison as a historical trend.
2. **Quota-cost documentation conflict** — official docs say 1 unit per `commentThreads.list`
   call; a generated client-library reference says 2 units. No comment calls were made in this
   build, so the conflict was not tested; the coder's actual fetch (1,019 units) is the ground
   truth. June 2026 quota buckets: the 10,000-unit framing is the connector doc's figure.
3. **Derived-metrics tension** — Developer Policies say API clients must only offer metrics
   available via YouTube's API services and must not offer independently calculated metrics that
   replace API data, but also state metrics displayed must be calculated exclusively from YouTube
   API data through basic arithmetic. Our KPIs (`views_per_day`, `engagement_rate`,
   `topic_share`, `volume_growth`) are basic arithmetic on returned statistics for an offline
   educational analysis, not a service offering metrics to users; the dashboard shows the
   underlying counts next to every derived rate.
4. **Committed raw JSON vs data-storage rules** — Developer Policies §III.E.4 allow storing video
   statistics for more than 30 days but require verifying every 30 days that the data is still
   authorised / the video still exists. Our raw JSONs are a dated one-time snapshot (2026-11-10)
   committed as the provenance record, following the Days 1–5 convention; they are not re-served
   by a live service. No YouTube page found states explicitly whether committing verbatim raw API
   JSON to a public GitHub repo counts as redistribution — unresolved.
5. **Comment text** — no comment JSONs were fetched in this build (0 sentiment videos), so no
   user-generated comment text is committed for Day 6.

## Versions used for this build

- Python 3.12.3; pandas 3.1.1, numpy 2.5.4, matplotlib 3.11.2, plotly 7.1.0,
  streamlit 1.66.1, requests 2.34.2, pytest 9.2.0, jupyter 1.1.1, nbformat 5.11.1
  (see `requirements.txt`).
- Dev tools (portfolio root `requirements-dev.txt`): ruff 0.17.4, black 26.10.1.
- `src/sentiment.py` is Day 5's lexicon scorer copied verbatim (scoring functions only, no
  themes); verified against Day 5's hand-computed cases before use: "I love this tutorial,
  amazing work" → 0.7184 positive; "This is terrible and boring" → −0.6124 negative;
  "not good" → −0.25 negative (negation); "very helpful" → 0.3612 positive (intensifier ×1.5).
