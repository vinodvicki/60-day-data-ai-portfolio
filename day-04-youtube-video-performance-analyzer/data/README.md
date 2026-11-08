# Data provenance — Day 04 YouTube Video Performance Analyzer

## Source

- **Provider:** YouTube Data API v3 (`https://youtube.googleapis.com/youtube/v3`),
  via the `custom.youtube` connector (helper
  `~/workspace/custom-connectors/custom.youtube/bin/youtube.py`).
  Read-only API-key auth; the key belongs to Victor's Google Cloud project
  `60-day-data-ai-portfolio` (project ID `day-data-ai-portfolio`), restricted
  to YouTube Data API v3 only, free tier, no payment method. The key is held
  by the connector and is never put in any file, env var, log, command
  argument, or the repo.
- **Endpoints used:** `GET /search` (`part=snippet`, `type=video`,
  `maxResults=50`, `order=relevance`), `GET /videos`
  (`part=snippet,statistics,contentDetails`, batched ≤ 50 IDs),
  `GET /channels` (`part=snippet,statistics`, batched ≤ 50 IDs).
  No `playlist-items` call was needed (no query under-delivered).
- **The 5 queries (fixed):** `data analytics`, `machine learning tutorial`,
  `Python data analysis`, `artificial intelligence explained`, `SQL tutorial`
  — one search each, `maxResults=50`, `order=relevance`.
- **Access date:** 2026-11-08. Relevance-ranked snapshot as of this date —
  not a date-bounded cohort (the helper sends no `publishedAfter` /
  `publishedBefore`).
- **Licence / attribution:** public YouTube video metadata fetched under the
  YouTube API Services Terms of Service and Developer Policies (checked
  2026-11-08). Attribution required and given: "Data from the YouTube Data
  API v3" with a link to YouTube's Terms of Service
  (`https://www.youtube.com/t/terms`) on the dashboard and in the repo
  README. Only public metadata is used — no user data, no comment text, no
  private data. Code in this repo is MIT (see `LICENSE`); YouTube data is
  under separate YouTube terms, not MIT.

## Fetch outcome

- **Live fetch succeeded** on the final pipeline run (`python -m
  src.data_pipeline`, exit 0, 2026-11-08). `data/processed/data_source.json`
  records `source: "live"`, `synthetic: false`, `seed: null`.
- **Quota used:** 508 units for this build's fetch (5 searches × 100 + 5
  videos calls × 1 + 3 channels calls × 1), ~5% of the 10,000/day free-tier
  quota (resets at midnight Pacific Time). The day's total YouTube usage was
  ~1,624 units: the researcher's 100-unit probe, one manual fetch of the
  same design (508 units, used to verify the helper before the pipeline
  ran), and two pipeline fetch runs (508 units each) — the first pipeline
  run hit a duration-parsing bug on a `P1DT4H41M8S` duration and crashed
  after fetching but before saving; the second run succeeded and produced
  the committed files. No `quotaExceeded` or other quota error appeared, so
  the June 2026 quota-bucket split did not bite on this build.
- **No top-up was used** (`top_up: null`): every query returned 50 results
  and the final count (244) is above the 180 target, so the §3.2
  playlist-based top-up was never triggered.
- **No cache or synthetic fallback was used.** `data/raw/` holds only the
  live responses.

## Row counts and coverage

| Step | Count |
|---|---|
| Candidates (5 × 50 search results) | 250 |
| Unique videos after dedupe by videoId | 244 (6 duplicates dropped) |
| Dropped: live/upcoming (`liveBroadcastContent != "none"`) | 0 |
| Dropped: no `viewCount` | 0 |
| Dropped: IDs missing from the `videos` response | 0 |
| **Final videos in `data/processed/videos.csv`** | **244** |
| Distinct channels | 143 |
| Largest single channel | Simplilearn (`UCsvqVGtbbyHaMoevxPAq9Fg`), 10 videos, 4.1% of the sample — below the 20% concentration limit |
| Videos with `like_count` present | 238 of 244 (97.5%; 6 videos have likes disabled — recorded as missing, never 0) |
| Videos with `comment_count` present | 243 of 244 (99.6%; 1 video has comments disabled — recorded as missing, never 0) |
| Videos with `subscriber_count` present | 244 of 244 (100%; no channel hid its count) |
| Duration parse | 244 of 244 (100%; one video is `P1DT4H41M8S` = 103,268 s, the Alex The Analyst bootcamp `cnjhHZNJEDk`; the ~30-hour SQL course `SSKVgrwhzus` is `P1DT5H48M28S` = 107,308 s) |
| Dates | No `publishedAt` in the future; none before 2005-04-23. Published range 2017-05-19 to 2026-11-07; median age 800.5 days |
| Duplicate `videoId`s in the final frame | 0 |
| `other` topic share | 0 of 244 (0.0%) — every video matched a keyword group |
| Median engagement rate | 2.20% (within the 0.5–8% sanity range) |
| Median views per day | 611 |

### File sizes (commit rule)

Small raw data IS committed: files under 1 MB each, under 5 MB per day
folder, are part of the deliverable — `.gitignore` must NOT exclude `data/`.
Five search JSONs are ~54 KB each and `channels_details.json` is ~306 KB.
**Exception, recorded here:** `data/raw/videos_details.json` is 1,466,881
bytes (~1.47 MB), over the 1 MB per-file guideline, because 244 full video
records (snippet + statistics + contentDetails) do not fit under 1 MB. It
is kept as a single file because plan §5 fixes that filename and it is the
provenance record for every number in `videos.csv`; total raw data is
~2.0 MB, inside the 5 MB per-day-folder limit. It can be regenerated at any
time with `python -m src.data_pipeline` (508 quota units) or rebuilt offline
from the committed cache with `python -m src.data_pipeline --offline`.
No synthetic files exist in `data/raw/` (none were generated — the live
fetch succeeded); `data/raw/*_synthetic.json` is git-ignored.

### `data_source.json` source-field note (§3.3)

The published `data_source.json` says `source: "live"`, which is correct:
the committed raw files and `videos.csv` were produced by the live pipeline
run on 2026-11-08. No offline run has overwritten the field since, so no
hand correction was needed. (An `--offline` run would flip it to `"cache"`;
any future offline run must be followed by a live re-run or a hand restore
with a note here.)

## Manual validation (one metric, by hand)

Video `yZvFH7B6gKI` — "What Is Data Analytics? - An Introduction (Full
Guide)", channel CareerFoundry, published 2021-03-25T13:13:45Z. From the raw
`videos_details.json`:

- `viewCount` = 2,354,250; `likeCount` = 53,644; `commentCount` = 970;
  `duration` = `PT9M4S` = 544 s.
- Days since publish: 2026-11-08 − 2021-03-25 = **2,053 days**. Days are full 24-hour periods from the publish timestamp to 2026-11-08 00:00 UTC, clipped at a minimum of 1.
- Engagement rate by hand: (53,644 + 970) / 2,354,250 = 54,614 / 2,354,250
  = **0.023198046086864182** (2.3198%). CSV value: 0.023198046086864182. **Match.**
- Views per day by hand: 2,354,250 / 2,053 = **1146.736483195324**. CSV
  value: 1146.736483195324. **Match.**
- Duration by hand: 9 × 60 + 4 = **544 s**. CSV value: 544. **Match.**

## Derived-metrics tension (stated honestly, no legal certainty claimed)

The YouTube Developer Policies say API clients must only offer metrics
available via YouTube's API services and must not offer independently
calculated or derived metrics that replace API data — but the same policies
also state that metrics displayed must be calculated exclusively from
YouTube API data through basic arithmetic. Our KPIs (`engagement_rate`,
`views_per_day`, `views_per_subscriber`) are basic arithmetic on returned
statistics for an offline educational analysis, not a service offering
metrics to users — that is the defensible reading, and the June 2026
"additional policies on derived metrics and data storage" apply to audited
developers with analytics use cases who explicitly apply for permission.
No legal certainty is claimed. The dashboard shows the underlying counts
next to every derived rate so nothing replaces the API data.

## Committed raw JSON vs data-storage rules (stated honestly)

Developer Policies §III.E.4 allow storing video statistics for more than 30
days but require verifying every 30 days that the data is still authorised /
the video still exists. Our raw JSONs are a dated one-time snapshot
(2026-11-08) committed as the provenance record, following the Days 1–3
convention; they are not re-served by a live service. No YouTube page found
states explicitly whether committing verbatim raw API JSON to a public
GitHub repo counts as redistribution, so this is unresolved and no legal
certainty is claimed.

## Versions used for this build

Python 3.12.3. Pinned in `requirements.txt` (verified in the build venv):
pandas 3.1.1, numpy 2.5.4, matplotlib 3.11.2, plotly 7.1.0, streamlit
1.66.1, requests 2.34.2, pytest 9.2.0, jupyter 1.1.1, nbformat 5.11.1.
Lint/format: ruff 0.17.4, black 26.10.1 (portfolio-root
`requirements-dev.txt`).
