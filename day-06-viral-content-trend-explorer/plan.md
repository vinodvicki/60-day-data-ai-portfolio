# Day 06 — Viral Content Trend Explorer: Build Plan

**Status:** PLAN — planner sign-off complete (AGENTS.md, stage 2).
**Source of truth:** `research_brief.md` (2026-11-10) + this plan. **If brief and
plan disagree, the plan wins and the difference is noted in §11.** The coder
must reuse the brief + this plan. **No extra web searches.**
**Roadmap entry (verbatim):** "DAY 06 | Viral Content Trend Explorer —
Problem / analysis: Track publicly accessible content/topic metrics over
time to identify accelerating and fading trends. GitHub deliverable: Trend
detection dashboard and weekly briefing." Section context (Days 4–6, Social
Media & Digital Marketing): Core skills: API integration, NLP, sentiment
analysis, text visualization. Suggested data: YouTube Data API; public,
permissioned comment and metadata datasets.

| Item | Value |
|---|---|
| Fetch date | 2026-11-10 (two consecutive 30-day windows: prior 2026-09-11 → 2026-10-11, recent 2026-10-11 → 2026-11-10 — §3) |
| Source | YouTube Data API v3 via the `custom.youtube` connector (helper `bin/youtube.py`, extended 2026-11-10 with `--published-after` / `--published-before` / `--page-token` on the `search` subcommand) |
| Sample | **Layer A** (context only): Day 4 frame, 244 videos, 0 units. **Layer B** (the trend sample): 5 Day-4 queries × 2 windows, `order=date`, 50/page, one page per query-window |
| Expected rows | **500 candidates → ~300–400 unique → ~280–380 final videos** (≈ 140–190 per window); sentiment ≤ 500 threads → **~300–450 analysed comments** on 5 videos (the coder must verify the actuals and report them; do not assume them) |
| Quota budget | **≤ 1,018 units (~10% of the 10,000/day free-tier quota)** — 10 searches (1,000) + ≤ 10 `videos` calls (≤ 10) + ≤ 3 `channels` calls (≤ 3) + 5 `comment-threads` calls (5); day total including the researcher's 200-unit probe ≤ 1,218 units (~12%) |
| Scope | Descriptive trend detection on two publish-date cohorts of recently published data/AI videos. **The API gives a current snapshot of each video's statistics, not daily history — so these are cohort comparisons, not a record of views rising or falling over time. No causal claims; no generalisation beyond this sample.** |

## 1. Problem statement + audience

**Problem.** A data/AI creator deciding what to make next can see what is
popular today, but cannot tell what is *accelerating* and what is *fading*:
are Python tutorials being published faster than a month ago while SQL
tutorials slow down, or is it just one viral video distorting the picture?
Day 6 fetches two consecutive 30-day cohorts of recently published data/AI
videos from YouTube, compares publish volume and view velocity per topic
between the two windows with fixed, pre-registered thresholds, and reports
which topics are accelerating, fading, or stable — with the velocity
cross-check, the age bias, and the snapshot limitation stated on the front
page. A bounded 5-video mood snapshot (Day 5's lexicon scorer, copied
verbatim) adds what viewers are saying on the fastest-rising video in each
topic. The weekly briefing (`outputs/weekly_briefing.md`) is the
roadmap's second deliverable: one paragraph per classified topic, generated
from the same computed table as the dashboard, never hand-written from
memory.

**Audience / decision-maker.** A data/AI creator (the portfolio's own field)
deciding what topic to cover next — which topics are gaining publish
momentum, which are losing it, and whether the velocity numbers agree with
the volume numbers. They are not a data analyst: every finding in the
dashboard, notebook, briefing and notes must be plain-language, must cite
the numbers behind it, must carry its caveat that a classification is a
statement about *this sample* ("in this sample, videos on topic X
published in the last 30 days outnumbered those in the prior 30 days
by …"), and must never present a cohort comparison as a historical trend
or as "topic X is going viral". The dashboard is the decision aid;
`outputs/insights_summary.md` is the plain-language findings note and
`outputs/weekly_briefing.md` is the dated weekly briefing (§4.4).

## 2. Research questions (exactly 3)

1. **Which topics are accelerating and which are fading — and by how
   much?** Per topic, what is the change in topic share (percentage
   points) and in publish volume (%) between the prior 30-day window
   (2026-09-11 → 2026-10-11) and the recent 30-day window (2026-10-11 →
   2026-11-10), and which topics meet the fixed accelerating / fading
   thresholds (§4.3) — and which fall under "insufficient data"?
2. **Does the velocity story agree with the volume story — and how stable
   are the calls?** Per topic per window, what is the median
   `views_per_day` (with median age and n), does the ±30% velocity
   cross-check flag any topic "mixed signal", does the 14-day age-guard
   sensitivity check flip any velocity direction, and does the holdout
   backtest (train W1–W7, check W8) predict the top-share topic?
3. **What is the audience mood on the fastest-rising video in each
   topic?** For the top video by `views_per_day` per topic in the recent
   window, what are the mean compound sentiment score and the
   positive/negative shares (as classified by the Day 5 rule-based model)
   — and what must a reader keep in mind, given this is five videos, not
   the topics?

## 3. Data — source, endpoints, fetch rules, provenance, licence

### 3.1 Source and endpoints (verified, from the brief — copy, do not re-search)

- **Source:** YouTube Data API v3, base URL
  `https://youtube.googleapis.com/youtube/v3`, via the `custom.youtube`
  connector (`~/workspace/custom-connectors/custom.youtube/`, helper
  `bin/youtube.py`). Read-only API-key auth: the key belongs to Victor's
  Google Cloud project `60-day-data-ai-portfolio` (project ID
  `day-data-ai-portfolio`), restricted to YouTube Data API v3 only, free
  tier, no payment method. **The key is held by the connector and is never
  put in any file, env var, log, command argument, or the repo.** The helper
  sends it as the `key` query parameter through the connector's surrogate
  exchange; redirects are refused by the helper. This day reuses the Day 4
  data source (YouTube) and adds a **new capability** (time-bounded search,
  §3.2) plus a **small new endpoint use** (comment threads on 5 videos,
  §3.3). Nothing from Days 1–3 carries over except the workflow
  conventions (provenance, synthetic fallback, `.gitignore` rule — §3.5).
- **Endpoints (exactly the four helper commands; parameters are what the
  helper actually sends — copy them, do not re-derive them):**

| Command | API endpoint | Parameters sent by the helper | Cost |
|---|---|---|---|
| `search --query "..." --max-results N --order date --published-after T --published-before T --page-token T` | `GET /search` | `part=snippet`, `q=<query>`, `type=video`, `maxResults=N`, `order=date`, `publishedAfter=<RFC 3339>` (only when given), `publishedBefore=<RFC 3339>` (only when given), `pageToken=<token>` (only when given) | **100 units** |
| `videos --ids ID[,ID...]` | `GET /videos` | `part=snippet,statistics,contentDetails`, `id=<comma-separated, up to 50>` | **1 unit** |
| `channels --ids ID[,ID...]` | `GET /channels` | `part=snippet,statistics`, `id=<comma-separated, up to 50>` | **1 unit** |
| `comment-threads --video-id ID --max-results N --order time --page-token T --text-format plainText` | `GET /commentThreads` | `part=snippet`, `videoId=<id>`, `maxResults=N` (1–100), `order=time`, `textFormat=plainText`, `pageToken=<token>` (only when given) | **1 unit** |

Full invocations:

```text
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py search --query "data analytics" --max-results 50 --order date --published-after 2026-10-11T00:00:00Z --published-before 2026-11-10T00:00:00Z
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py search --query "data analytics" --max-results 50 --order date --published-after 2026-10-11T00:00:00Z --published-before 2026-11-10T00:00:00Z --page-token NEXT_PAGE_TOKEN
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py videos --ids ID[,ID...]
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py comment-threads --video-id VIDEO_ID --max-results 100 --order time --text-format plainText
```

- **The snapshot limitation — read this first, it drives the whole design
  (brief §1.2, copied):** the YouTube Data API returns a **current
  snapshot** of each video's statistics (`viewCount`, `likeCount`,
  `commentCount` as they stand at fetch time). **It does not return
  historical daily views, likes, or comments for a video.** There is no
  endpoint that gives "views on 2026-10-20" for a video published on
  2026-10-01. Therefore "trend over time" in this project is built from
  **two things the API does give**: (1) **publish-date cohorts** — every
  video has a `publishedAt`; grouping videos by the week they were
  published gives a genuine time series of *publish volume per topic*, and
  each video's *current* `views_per_day` (views / days since publish) is a
  velocity measure for its cohort; (2) **repeated, time-bounded search
  snapshots** — `search.list` accepts `publishedAfter` /
  `publishedBefore`, so the coder fetches two consecutive 30-day windows
  with `order=date`. **What this design must never claim:** that any chart
  shows a video's views rising or falling day by day, or that a topic's
  views "grew" between two dates. The honest claims are: (a) *more/fewer
  videos on topic X were published recently than before* (volume momentum),
  and (b) *recently published videos on topic X are accumulating views
  faster/slower per day of life than the previous cohort did* (velocity
  momentum, with the age bias stated in §4.5). Every output states this.
- **Verification probes (already run by the researcher, 2026-11-10 — do not
  re-run them as separate probes):** Probe 1 — `search --query "data
  analytics" --max-results 2 --order date --published-after
  2026-10-11T00:00:00Z --published-before 2026-11-10T00:00:00Z` → exit 0,
  ~1.2 s, `youtube#searchListResponse`, 2 items, both published 2026-11-09
  (inside the window), `nextPageToken: "CAIQAA"` present,
  `pageInfo.totalResults: 455684` (capped estimate — never a finding),
  cost 100 units. Probe 2 — same call with `--page-token CAIQAA` → exit 0,
  ~0.6 s, 2 different videos (`fIv3G9sZJTU` 2026-11-09T22:09:31Z,
  `DAwERBXKaRI` 2026-11-09T21:27:29Z), still inside the window, still
  reverse-chronological, `nextPageToken: "CAQQAA"` present, cost 100 units.
  **Probe total: 200 units.** The helper extension (three new optional
  arguments on `search`: `--published-after`, `--published-before`,
  `--page-token`) is already in place; the coder uses it, does not modify
  it.
- **Response fields the coder will use.** `search` → `snippet` (per video):
  `videoId`, `title`, `channelId`, `channelTitle`, `publishedAt` (ISO 8601
  UTC), `description`, `liveBroadcastContent` (`"none"` for ordinary
  videos). Search returns **no statistics** — views/likes/comments require
  the `videos` call. Filter out any item with `liveBroadcastContent !=
  "none"`. `search` → top level: `nextPageToken` (absent on the last page),
  `pageInfo.totalResults` (**unreliable estimate — never report it**).
  `videos` → `snippet`: `title`, `channelId`, `channelTitle`,
  `publishedAt`, `description`, `tags` (may be absent), `categoryId`,
  `defaultLanguage` (may be absent), `liveBroadcastContent`. `videos` →
  `statistics`: `viewCount`, `likeCount`, `commentCount` — **all arrive as
  strings**; cast to int. `likeCount` and/or `commentCount` may be
  **absent** (likes/comments disabled) — record as missing (NaN), never
  silently fill with 0. `viewCount` absent means the video is unusable —
  drop the row and count it. `videos` → `contentDetails`: `duration`
  (ISO 8601, e.g. `PT12M34S` — parse to seconds; Shorts are `PT60S` or
  less), `definition`, `dimension`, `licensedContent`. `channels` →
  `statistics`: `subscriberCount` (hidden for some channels — record as
  missing, never 0), `viewCount`, `videoCount`. `commentThreads` →
  `snippet.topLevelComment.snippet` (per thread): `id`, `textDisplay`
  (with `textFormat=plainText` this equals `textOriginal`; use
  `textDisplay`), `authorDisplayName`, `authorChannelId.value`,
  `likeCount` (int), `publishedAt`. Thread-level `snippet`: `channelId`
  (the video's channel), `videoId`, `totalReplyCount`.
  `pageInfo.totalResults` is unreliable here too — never use it as a count.
- **Hard limits of the API (design constraints, not bugs to fix in Day 6):**
  **no historical statistics** (§3.1 above); **no `publishedAfter` /
  `publishedBefore` on `commentThreads.list`** — the §3.3 comment fetch is
  newest-first with no date filter; it is a mood snapshot of the trending
  videos, not a time series; **search returns at most 50 results per
  call** and the API caps search at 500 results per query — with
  `order=date` + a 30-day window, a query that returns exactly
  `maxResults` items may be **truncated** (the newest 50 only); the
  pipeline records a `truncated` flag per query-window (§3.4) and the
  README states it; it does not silently fetch more pages; **search
  relevance/date ranking is a black box** — findings are descriptive of
  the returned set; two queries returning overlapping top results is itself
  a finding about topic overlap — report the dedupe counts; **read-only,
  public data only**; timeout 30 s per request (helper); redirects refused.

### 3.2 The two data layers (fixed — do not add a third)

| Layer | What it is | Cost | Role in the analysis |
|---|---|---|---|
| **A. Day 4 frame (reused, not re-fetched)** | `day-04-youtube-video-performance-analyzer/data/processed/videos.csv` — 244 videos, fetched live 2026-11-08, stats snapshot as of that date | **0 units** (read the committed CSV) | Long-run context only: topic shares and weekly publish volume back to 2017, labelled "relevance sample, not exhaustive". Never mixed into the momentum windows (different snapshot date, different selection method). |
| **B. Fresh time-bounded searches (the trend sample)** | 5 queries × 2 windows (§3.4), `order=date`, `maxResults=50`, then batched `videos` + `channels` calls | **≤ 1,013 units** | The momentum analysis: weekly publish volume per topic, velocity per topic per window, trend classification (§4). All trend calls come from this layer only. |

**Day 4 frame facts (computed from the committed CSV, 2026-11-10):** 244
videos; topics **python 123 / ai_ml 68 / sql 39 / career 10 / bi_viz 3 /
general 1**; publish range **2017-05-19 → 2026-11-07**; by year: 2026: 49,
2025: 56, 2024: 47, 2023: 31, 2021: 13, 2022: 13, 2018: 12, 2020: 11,
2019: 8, 2017: 4. **Only 18 videos were published in the last 90 days
before the Day 4 fetch, 28 in the last 180 days, 59 in the last 365 days;
185 are over a year old.** This is why Layer A alone cannot support a
trend call and Layer B exists: a relevance-ranked snapshot is old-heavy,
and its weekly counts are not a publish-volume time series. Median
`views_per_day` in the Day 4 frame (for context, not for momentum): python
488.7, ai_ml 913.6, sql 707.1, career 642.4, bi_viz 2,573.9 (n=3 —
unreliable), general 108.2 (n=1 — meaningless). The Day 4 frame itself is
**never edited**; videos already in it that reappear in the fresh searches
are kept **once, as fresh rows** (their stats are the 2026-11-10 snapshot)
and the overlap count is recorded.

### 3.3 Sentiment angle — bounded, secondary (fixed scope)

The trend call itself does not need comment text. The sentiment angle is a
**mood snapshot of the trending videos**, not a second trend series:

- **Exactly 5 videos:** the top video by `views_per_day` within each topic
  in Window A (age ≥ 7 days, comments enabled), one per topic. If a topic
  has no eligible video in Window A (e.g. `bi_viz` / `general` may have
  n < 10), that topic contributes no sentiment video and the count is
  recorded — do not substitute a video from another topic or window.
- **Exactly 5 `comment-threads` call sequences** (one per video),
  `maxResults=100`, `order=time` (newest first), `textFormat=plainText`,
  `part=snippet` (top-level comments only — **no replies, no
  `comments.list` calls**), **one page only** per video (no `--page-token`
  follow-up).
- **Scoring:** Day 5's lexicon scorer, **copied verbatim** — the coder
  **copies** Day 5's `src/sentiment.py` scoring functions into this day's
  own `src/sentiment.py` (same file, same rules — Victor's own code, copied
  within his repo, not re-derived and not re-tuned). Day 5's theme lists
  are **not** reused — themes are Day 5's scope. Non-English handling
  reuses Day 5's §3.4 heuristic (non-Latin > 20% of letters → excluded
  from scoring, counted). See §4.2 for the verbatim rules.
- **Filter (in this order, each step counted):** (1) drop threads whose
  top-level comment's `authorChannelId` equals the video's channel ID
  (channel-owner comments, incl. pinned promos — not audience sentiment);
  (2) drop empty/whitespace-only text; (3) drop non-Latin comments per the
  heuristic.
- **Expected rows:** 5 videos × up to 100 threads = **≤ 500 fetched
  threads** → after filtering **~300–450 analysed comments**. If the final
  analysed count lands below **150**, the sentiment panel is labelled
  thin-sample in the dashboard and the README.
- **Reporting:** per-video mean compound score, positive/negative share,
  and n analysed — shown next to that video's velocity numbers as
  "audience mood on the fastest-rising video in this topic". **No claim is
  made that this mood represents the topic** — it represents five videos,
  and the dashboard says so.

### 3.4 Fetch rules (Layer B — fixed design)

- **Fetch date: 2026-11-10.** Two consecutive 30-day windows:
  **Window B (prior):** `2026-09-11T00:00:00Z` →
  `2026-10-11T00:00:00Z`; **Window A (recent):**
  `2026-10-11T00:00:00Z` → `2026-11-10T00:00:00Z`.
- **Five queries — the same five as Day 4** (so the topic mix is comparable
  to the Day 4 frame), one page each per window, `order=date`:

| # | Query | Per window | Why this topic |
|---|---|---|---|
| 1 | `data analytics` | 50 | Core topic — the portfolio's own field |
| 2 | `machine learning tutorial` | 50 | AI/ML tutorial demand |
| 3 | `Python data analysis` | 50 | Tool-specific (Python) demand |
| 4 | `artificial intelligence explained` | 50 | AI explainer demand |
| 5 | `SQL tutorial` | 50 | Tool-specific (SQL) demand |

- **Order:** `date` (newest first) — deliberate: within a bounded window
  this is the closest the API comes to an exhaustive recent sample. Do
  **not** use `order=relevance` — it would return a relevance-ranked mix
  and destroy the publish-volume time series. Do **not** use
  `order=viewCount` — it would return only the most-viewed videos and
  destroy the variance the velocity comparison needs.
- **Pagination:** **one page only per query-window** (no `--page-token`
  follow-up in the build, even though the helper now supports it — the
  probe verified it works, the build does not need it). If a query-window
  returns exactly 50 items, record `truncated: true` for it in
  `data_source.json` and state it in the README; do not fetch page 2.
  Rationale: a second page per query-window would double the search quota
  to 2,000 units for the tail of the window, and the first page (newest
  50) already covers the volume signal; the truncation is a stated
  limitation, not a hidden one.
- **Deduplicate** by `videoId` across the five queries within each window
  (overlap is expected — e.g. a Python tutorial can match queries 1, 3
  and 5). Keep the first occurrence; record the query of origin for every
  video and how many duplicates were dropped per window. A video cannot
  appear in both windows (its publish date is unique); if one does (API
  quirk), keep the window whose bounds contain its `publishedAt` and
  record it.
- **Filter:** drop `liveBroadcastContent != "none"`; drop rows with no
  `viewCount` after the `videos` call.
- **Detail fetch:** collect all surviving IDs per window and fetch in
  **one batched `videos` call per ≤ 50 IDs** (expect ≤ 10 calls total).
  Then **one batched `channels` call per ≤ 50 distinct `channelId`s**
  (expect ≤ 3 calls) for subscriber counts.
- **Expected row counts (coder must verify the actuals and report them; do
  not assume these):** 10 searches × 50 = **500 candidates** → after
  dedupe **~300–400 unique videos** → after filtering/missing statistics
  **~280–380 final videos** (≈ 140–190 per window). If the final count
  lands below **200**, the coder reports it as a thin-sample caveat in the
  README; the analysis still runs, but momentum classifications for topics
  with n < 10 per window are reported as "insufficient data" (§4.3). If
  any query-window returns 0 items, that is recorded as a finding (a quiet
  window), not an error, unless ≥ 3 query-windows return 0 (§3.6).
- **Channel concentration check:** report how many distinct channels the
  sample covers and the largest single channel's share per window. If one
  channel is > 20% of a window, the dashboard must say so — a one-channel
  window is a channel study, not a topic study.
- **Polite use:** ≥ 2 s between calls; one retry after 30 s on HTTP 5xx /
  timeout only; no retry on 403 `quotaExceeded` (§3.6).
- **Quota budget:** 10 searches × 100 = **1,000** + ≤ 10 batched `videos`
  calls × 1 = **≤ 10** + ≤ 3 batched `channels` calls × 1 = **≤ 3** + 5
  `comment-threads` calls × 1 = **5** → **≤ 1,018 units (~10% of the
  daily quota)**. Including this brief's 200-unit probe, the day total is
  ≤ **1,218 units (~12%)**. There is ample headroom for one full re-run if
  a call fails; there is no headroom for exploratory extra searches, so the
  coder runs exactly the §3.4 design.
- **Quota-cost discrepancy (open item, same as Days 4–5):** official docs
  page says 1 unit per `commentThreads.list` call; generated
  client-library reference says "snippet part has a quota cost of 2
  units". Resolution order: (a) run the §3.4 design as written; (b) if
  `quotaExceeded` appears far earlier than the ~1,018-unit budget
  predicts, stop, check the Google Cloud Console quota page for the bucket
  breakdown, and report the actual bucket limits — do not retry or add
  calls. (Same June 2026 quota-bucket caveat as Day 4: Google split the
  daily quota into separate buckets from 2026-06-01. The 10,000-unit
  framing above is the connector doc's figure and the probes succeeded
  within it, so the build proceeds on that basis — but the coder's actual
  fetch is the ground truth.)
- **Raw size guard:** one raw file per query-window
  (`data/raw/search_<query-slug>_<window>.json`, verbatim API responses)
  plus `data/raw/videos_details.json` and
  `data/raw/channels_details.json` plus 5 `data/raw/comments_<video_id>.json`
  files. Each search file is ≤ ~50 items × ~1 KB ≈ 50 KB; the raw total is
  ≤ ~1 MB — inside the 5 MB/day rule and the 1 MB/file guideline.

### 3.5 Data provenance

- `data/README.md` (coder writes it) records: provider, endpoints used,
  the 5 queries + 2 windows, access date (2026-11-10), quota units used,
  row counts (candidates → unique → final, per window, with each filter's
  count), truncation flags per query-window, the Layer A / Layer B split
  and why, the licence/attribution note (§3.7) + the tensions stated
  honestly (§3.7), and the hand-validated metric (§4.6 item 3).
  `data/processed/data_source.json` records `source` (`"live"`,
  `"cache"` or `"synthetic"`), `generated_at_utc`, `synthetic` (bool),
  `seed` (`null` for live data, `42` for synthetic), plus `fetch_date`
  (`"2026-11-10"`), `snapshot_dates` (`{"day04_frame": "2026-11-08",
  "fresh_fetch": "2026-11-10"}`), `windows` (`{"prior":
  ["2026-09-11T00:00:00Z", "2026-10-11T00:00:00Z"], "recent":
  ["2026-10-11T00:00:00Z", "2026-11-10T00:00:00Z"]}`), `queries` (the 5
  query strings), `max_results_per_query` (50), `order` (`"date"`),
  `per_query_window` (counts + `truncated` flags), `video_count`,
  `channel_count`, `quota_units_used` (best estimate), `api`
  (`"youtube-data-api-v3"`), `age_guard_days` (7),
  `overlap_with_day04_frame` (count), and `counts` (candidates,
  unique_after_dedupe, dropped_live_or_upcoming, dropped_no_view_count,
  final_videos, sentiment_videos, sentiment_comments_analysed).
- **Data-source field rule (Day 2 day-log lesson — mandatory):** an offline
  pipeline run (`--offline` / `--use-cache`) overwrites
  `data_source.json`'s `source` field to `"cache"`. Before publishing, the
  coder/optimizer must either **re-run the pipeline live** (restoring
  `"live"`) or **restore the field by hand with the true value and record
  the correction** in `data/README.md`. A published `data_source.json`
  that says `"cache"` when the data was in fact fetched live is a defect;
  the publisher's frozen-tree check (§8) includes verifying this field.
- **Data-commit rule (from Day 1):** small raw data IS committed — files
  under 1 MB each, under 5 MB per day folder — because the raw files are
  the provenance record. **`.gitignore` must NOT exclude `data/`.**
  Synthetic fallback output goes to `data/raw/*_synthetic.json` and is
  git-ignored; it must never overwrite the live cache.
  `python3 src/data_pipeline.py --offline` / `--use-cache` runs from the
  committed cache with no network.
- **Cache reuse note:** there is no prior Day 6 cache. A cache fallback is
  only valid if a Day 6 fetch has previously succeeded and written
  `data/raw/` files in the Day 6 folder. **Layer A (the Day 4 frame) is
  not a cache for Layer B** — it is a different snapshot (2026-11-08)
  selected by a different method (relevance), and it must never be
  relabelled as the fresh fetch. Do **not** reuse any other day's data as
  Layer B — the source design differs entirely.
- **Key rule:** the API key comes only from the `custom.youtube`
  connector. No `.env` file, no key in code, no key in any committed file,
  no key in logs.
- **`.gitignore` note (open item, already resolved at the shared-tool
  level):** the shared orchestrator (`agents/orchestrator.py`) already
  passes the `.gitignore` check for Days 4–5 (verified this run) — the
  coder/optimizer just use the scaffold `.gitignore` as-is; it already
  excludes only `data/raw/*_synthetic.json` and does NOT exclude `data/`.
  **Do NOT weaken the credentials scanner** and do not change the
  orchestrator for this day.

### 3.6 Error handling (from the brief — follow the table, do not improvise)

| Error | Meaning | Coder action |
|---|---|---|
| `400 keyInvalid` | Stored key wrong or project misconfigured | Stop. Do not retry. Report as blocked; key is the connector's business, never to be pasted or hard-coded anywhere. |
| `403 quotaExceeded` | Daily quota hit | Stop immediately. No retry. Fall back to cache, then synthetic (§3.8). |
| `403 accessNotConfigured` | YouTube Data API v3 not enabled on the project | Stop. Report as blocked (it was enabled 2026-11-07 and the probes succeeded, so this is not expected). |
| `403` other (e.g. `forbidden`) | Request rejected for another reason | Check the request first (IDs well-formed, ≤ 50 per call, RFC 3339 dates well-formed); one careful retry only if the request was malformed. |
| HTTP 5xx / timeout | Transient server/network failure | One retry after 30 s, then fall back (§3.8). |
| Empty `items` on a `videos` call | IDs invalid, private, or deleted | Drop those IDs, count them, continue — this is not an error. |
| Empty `items` on a `search` call for a query-window | No matching videos in that window (possible for a narrow query) | Record 0 for that query-window, continue — this is a finding (a quiet window), not an error, unless ≥ 3 of the 10 query-windows return 0. |
| Empty `items` on a `comment-threads` call | Comments disabled on that video, or none returned | Record 0 fetched for that video, continue with the other 4 (§3.3). Do not treat as a build failure unless ≥ 3 of the 5 videos return 0. |

The helper exits non-zero with `HTTP {code} from {path}: {body[:500]}` —
the pipeline must catch that, log the code/reason, and follow the table
above. **Never log the API key** (the helper never prints it; keep it that
way).

### 3.7 Licence / attribution

- Data is public YouTube video metadata and comment text fetched under the
  **YouTube API Services Terms of Service and Developer Policies** (checked
  2026-11-10). Attribution is required: include on the dashboard and in
  the repo README, legible: **"Data from the YouTube Data API v3"** with a
  link to YouTube's Terms of Service (`https://www.youtube.com/t/terms`),
  per the Developer Policies requirement that API clients display a link
  to YouTube's Terms of Service.
- Do not redistribute raw bulk data or re-host the API. Cache the fetched
  responses locally for the project only (§3.5).
- Only public metadata is used — no user data beyond public comment
  text/display names, no private data. The API key has no OAuth scopes.
- Code in this repo is MIT (see `LICENSE`); YouTube data is under separate
  YouTube terms, not MIT.
- **Tensions, stated honestly (brief §5.5, carried over — no legal
  certainty is claimed on any of them):** (1) snapshot vs historical trend
  — the API gives no historical daily statistics, so "trend" is a
  comparison of two publish-date cohorts, resolved by design (§3.1), and
  no output may present a cohort comparison as a historical trend;
  (2) quota-cost documentation conflict (1 vs 2 units — §3.4); (3)
  derived-metrics tension — the YouTube Developer Policies say API clients
  must only offer metrics available via YouTube's API services and must
  not offer independently calculated or derived metrics that replace API
  data, but the same policies also state that metrics displayed must be
  calculated exclusively from YouTube API data through basic arithmetic;
  our KPIs (`views_per_day`, `engagement_rate`, `topic_share`,
  `volume_growth`) are basic arithmetic on returned statistics for an
  offline educational analysis, not a service offering metrics to users —
  that is the defensible reading; the dashboard shows the underlying counts
  next to every derived rate so nothing replaces the API data; (4)
  committed raw JSON vs data-storage rules — Developer Policies §III.E.4
  allow storing video statistics for more than 30 days but require
  verifying every 30 days that the data is still authorised / the video
  still exists; our raw JSONs are a dated one-time snapshot (2026-11-10)
  committed as the provenance record, following the Days 1–5 convention;
  they are not re-served by a live service; no YouTube page found states
  explicitly whether committing verbatim raw API JSON to a public GitHub
  repo counts as redistribution, so this is unresolved; (5) comment text
  is user-generated content — the 5 raw comment JSONs contain public
  comments verbatim, including display names; they are a dated one-time
  snapshot (2026-11-10) committed as the provenance record, not re-served
  by a live service, and the dashboard shows only aggregates (mean
  compound, shares, n) plus at most 3 short excerpts per video (≤ 120
  chars, no author names). All five tensions are stated in `data/README.md`
  with the snapshot date.
- **No copying code or tutorials from the web.** All code is Victor's own
  original work, written from the brief and this plan. The sentiment scorer
  is copied from Day 5 within Victor's own repo (§4.2); the normaliser
  shape and ±0.05 thresholds are standard published VADER conventions,
  documented as such, not copied code.

### 3.8 Synthetic fallback rules (if the API is unreachable)

If all requests fail (quota, network block, or outage) after one polite retry:
1. Use a **cached copy** of a previous successful Day 6 fetch if one exists
   (`data/raw/` in this day folder only — see §3.5 cache note).
2. Otherwise generate a **clearly labelled synthetic dataset** for
   development only, deterministic, **seed 42**:

| Field | Synthetic rule |
|---|---|
| `n` | **300 videos** across the same 5 topics, in the Day 4 frame's proportions (python 150, ai_ml 85, sql 45, career 12, bi_viz 5, general 3) |
| `published_at` | Uniform over the 60-day window 2026-09-11 → 2026-11-10, **but with a built-in trend by construction** so the detector has something to detect: python volume rising across the weeks (30% of its videos in W1–W3, 70% in W6–W9), sql volume falling (70% in W1–W3, 30% in W6–W9), other topics uniform. Recorded in the code. |
| `view_count` | Log-normal, median 50,000, σ_log 1.2, clipped to [100, 5,000,000] |
| `like_count` | `view_count × U(0.02, 0.06)` (rounded) |
| `comment_count` | `view_count × U(0.0005, 0.005)` (rounded) |
| `subscriber_count` | Log-normal, median 100,000, σ_log 1.0, clipped to [1,000, 10,000,000] |
| `duration_seconds` | Log-normal, median 600 s, σ_log 0.8, clipped to [60, 3600], rendered back to ISO 8601 |
| `title` / `tags` | Assembled from fixed template lists per §3.1 topic group (e.g. "Python Data Analysis Tutorial for Beginners"), so the keyword grouping classifies them |
| `category_id` | 27 (Education) or 28 (Science & Technology), alternating |
| Sentiment comments | 5 videos × 100 template comments using Day 5's synthetic templates (45/35/20 positive/neutral/negative mix by construction) |

3. Synthetic output goes **only** to `data/raw/*_synthetic.json` — it must
   never overwrite the live cache. `data/processed/data_source.json`
   records `synthetic: true` + `seed: 42`. All downstream outputs are
   labelled SYNTHETIC. Synthetic data follows the same schema as live data
   (same columns, §4.4) so the pipeline, notebook, and dashboard run
   unchanged. Synthetic files are git-ignored
   (`data/raw/*_synthetic.json` in `.gitignore`); live `data/raw/*.json`
   are committed.
4. Never present synthetic data as real YouTube data. Mark every chart, the
   app and the README **"SYNTHETIC DATA — API unavailable on 2026-11-10"**
   and re-fetch real data before publishing.
   `python3 src/data_pipeline.py --offline` / `--use-cache` runs from the
   committed cache with no network and never generates synthetic data.
5. **Synthetic trends are uniform/constructed by design, so on synthetic
   data the accelerating/fading calls have no interpretation** — state this
   in the README, notebook and briefing if the synthetic path is used.

## 4. Method — trend detection, sentiment, metrics, validation, targets

All metrics are computed on the cleaned video frame (one row per video,
Layer B only, unless a metric says otherwise). **Use medians, not means,
for every views/engagement comparison** — view counts are heavily
right-skewed and a single viral video would dominate any mean.
Log10(viewCount) is used for charts.

### 4.1 Topic taxonomy (reuse Day 4 — verbatim, do not invent a new classifier)

**Assignment rule (Day 4 brief §3.2, copied exactly):** deterministic
keyword match on lower-cased `title + tags + description`, first match
wins in this priority order:

1. `python` — "python", "pandas", "numpy"
2. `sql` — "sql", "mysql", "postgres"
3. `ai_ml` — "machine learning", "artificial intelligence", " ai ",
   "llm", "chatgpt", "deep learning", "neural"
4. `bi_viz` — "power bi", "tableau", "excel", "dashboard",
   "visualization", "visualisation"
5. `career` — "career", "job", "salary", "interview", "roadmap"
6. `general` — "data analytics", "data analyst", "data science"
7. `other` — no keyword match

Record the keyword list in the code, not in prose. **No new topic is added
and no keyword is changed.** Justification: the taxonomy is the
portfolio's settled topic language (Days 4–5); changing it would break
comparability with the Day 4 frame, and the fresh searches use the same
five queries that produced that frame, so no new topic is expected to
emerge. If `other` exceeds 30% of the fresh sample, the grouping is too
narrow — **report it, do not silently re-tune the keywords after seeing
results**. Expected small groups: `career`, `bi_viz` and `general` had
only 10, 3 and 1 videos in the Day 4 frame and will likely stay small in
Layer B — they are reported for completeness but will usually fall under
the §4.3 "insufficient data" rule for momentum classification.

### 4.2 Sentiment model — Day 5 lexicon scorer, copied verbatim (do not rewrite)

`src/sentiment.py` in this day **copies** Day 5's
`src/sentiment.py` scoring functions verbatim (same file, same rules —
Victor's own code, copied within his repo, not re-derived and not
re-tuned). Day 5's theme lists are **not** reused — themes are Day 5's
scope and are not implemented here. The rules below are the Day 5 plan
§4.1 rules, copied so the coder can verify the copy without opening Day 5:

| Component | Rule (copy verbatim from Day 5 `src/sentiment.py`) |
|---|---|
| Lexicon | Two word lists authored in the code: **positive words** and **negative words**. Each word carries polarity **+1 / −1**; a small explicit set of strong words (**love, amazing, brilliant, excellent, fantastic, perfect, hate, terrible, awful, horrible, worst, useless**) carries **±2**. The lists must be written out in full in `src/sentiment.py` (target ~100–150 words per side). |
| Tokenisation | Lower-case, split on non-letters (keep apostrophes inside words, e.g. `don't` stays one token), strip URLs and @mentions before scoring (they carry no sentiment). |
| Negation | `not, no, never, n't, don't, doesn't, didn't, can't, won't, isn't, wasn't, aren't, couldn't, shouldn't` flip the polarity of the **next 3 scored words** (a token window of 3). Double negation is not handled — documented as a limitation. |
| Intensifiers | `very, extremely, so, really, absolutely, totally, super, incredibly, truly, quite, pretty` multiply the next scored word's polarity by **1.5**. |
| Emoji | A small explicit map in the code: positive `😍 😂 👍 ❤️ 🔥 🙌 👏 😊 🎉 💯` (+1 each, max +2 per comment); negative `😡 👎 😢 💩 🤮 😤 😠` (−1 each, max −2 per comment). Documented as a crude signal, not a full emoji model. |
| Exclamation | +0.25 per `!` in the text, capped at +0.5, applied to the raw sum **only if the sum is already positive** (excitement amplifies praise; it does not turn a complaint positive). |
| Normalisation | `compound = s / sqrt(s² + 15)` where `s` is the raw summed score (the same normaliser shape VADER publishes — a standard saturating function, documented in the code, not copied code). Result in (−1, +1). |
| Classification | `compound ≥ +0.05` → **positive**; `compound ≤ −0.05` → **negative**; otherwise **neutral** (the ±0.05 thresholds VADER publishes — standard, documented in the code). |
| Output columns | `sentiment_score` (compound, 4 dp), `sentiment` (positive / neutral / negative), plus `scored_words` (count of lexicon words matched — 0 means the comment carried no lexicon signal and is neutral by default, which is itself a finding). |

**Non-English heuristic (Day 5 §4.4, copied):** strip emoji/URLs/mentions,
take the alphabetic characters, and if **> 20% of letters are non-Latin**
(Unicode script check via `unicodedata`, stdlib only), mark the comment
`language_flag = "non_latin"` and exclude it from sentiment scoring (it is
counted in `data_source.json` and `data/README.md`). This is a crude
heuristic, not a language identifier: it will miss non-English comments
written in Latin script (e.g. Spanish, French) — those will mostly score
neutral (no lexicon match) and inflate the neutral share, which is a stated
limitation, not a hidden one. No new dependency (`langdetect` etc.) is
added for this.

**What the model cannot do (limitations to document prominently):** no
sarcasm/irony detection; no context beyond the negation window; no slang /
neologism coverage beyond the authored lists; short comments ("ok", "lol",
"first") usually score neutral by default, not by meaning; non-English is
excluded, not translated; emoji handling is a tiny explicit map; the
lexicon was authored before seeing the comments and must **not** be tuned
after seeing results. **Sentiment is a model output, not ground truth** —
no sentiment number may be used in a trend classification, and no sentiment
share may be presented as "how viewers feel" without the "as classified by
our rule-based model" qualifier.

### 4.3 Time buckets (fixed)

- **Momentum windows:** Window B (prior, 2026-09-11 → 2026-10-11) vs
  Window A (recent, 2026-10-11 → 2026-11-10). Each is exactly 30 days; a
  video belongs to the window containing its `publishedAt`. The boundary
  instant `2026-10-11T00:00:00Z` belongs to Window A (`publishedAfter` is
  "at or after", §3.1).
- **Weekly buckets:** 7-day blocks anchored at the start of Window B —
  W1 2026-09-11→09-17, W2 09-18→09-24, W3 09-25→10-01, W4 10-02→10-08,
  W5 10-09→10-15, W6 10-16→10-22, W7 10-23→10-29, W8 10-30→11-05,
  W9 11-06→11-10 (5 days, **partial — flagged on every chart and excluded
  from week-over-week growth**). Week labels show the start date (e.g.
  "w/c 2026-10-30").
- **Smoothing:** a **2-week rolling mean** of weekly publish volume per
  topic (mean of the current and previous week's counts), drawn as a line
  over the weekly bars. It smooths single-week spikes; it is a display aid,
  never a classification input.
- **Small-n rule:** a topic-week cell with n < 5 is flagged **thin** on the
  chart and in the table; a topic-week with n = 0 is shown as 0 with a "no
  videos" note, never interpolated.

### 4.4 Core metrics (definitions fixed — the planner/coder must not redefine them)

| Metric | Formula | Notes |
|---|---|---|
| `days_since_publish` | `(fetch_date − publishedAt).days`, minimum 1 | Fetch date = 2026-11-10. A video published today scores 1 day, never 0 (no division by zero). |
| `views_per_day` | `view_count / days_since_publish` | Age-normalised velocity — the primary "how fast is this video accumulating views" measure. **Only computed for videos aged ≥ 7 days** (§4.5 guard); younger videos get `views_per_day = NaN` and are excluded from velocity medians (they still count in publish volume). |
| `engagement_rate` | `(like_count + comment_count) / view_count` | Requires both counts present; NaN otherwise. Typical range ~0.5–8% (Day 4 sanity check). |
| `like_rate` / `comment_rate` | `like_count / view_count` · `comment_count / view_count` | Components of engagement; `comment_rate` is the audience-response proxy in the briefing. |
| `views_per_subscriber` | `view_count / subscriber_count` | NaN where subscriber count is hidden. |
| `duration_seconds` | Parsed from `contentDetails.duration` (ISO 8601) | `PT12M34S` → 754. All durations must parse; zero/negative is a data error. Duration buckets (Day 4): Short ≤ 60 s · Short-form 61–300 s · Medium 301–900 s · Long 901–1800 s · Deep-dive > 1800 s. |
| `weekly_volume(topic, week)` | Count of videos in the topic published in the week | The primary time-series quantity. |
| `topic_share(topic, window)` | `weekly_volume` summed over the window / total videos in the window | In percentage points (pp) for momentum. |
| `volume_growth(topic)` | `(n_A − n_B) / n_B`, where `n_A`, `n_B` are the topic's video counts in Windows A and B | Undefined if `n_B = 0` — then report "no prior-window baseline" instead of a number. |
| `share_change(topic)` | `topic_share(topic, A) − topic_share(topic, B)`, in percentage points | The primary momentum quantity. |
| `median_views_per_day(topic, window)` | Median `views_per_day` over the topic's videos in the window with age ≥ 7 days | The velocity quantity. Always reported with n and with the median age of the videos in the window (§4.5). |
| `velocity_change(topic)` | `(median_views_per_day(A) − median_views_per_day(B)) / median_views_per_day(B)` | Supporting signal only — never the classification input (§4.5). Undefined if the Window B median is missing/zero. |
| `mean_compound` (sentiment) | Mean Day 5 `score_comment` compound over the analysed comments on one video | §3.3 only. Always with n and the positive/negative shares. |
| `sentiment_share` (per video) | Share of analysed comments per class (positive / neutral / negative) | §3.3 only. |

### 4.5 Trend classification — accelerating / fading / stable (fixed thresholds)

Computed **per topic, from Layer B only**, using volume momentum as the
primary signal:

| Classification | Rule (all conditions must hold) |
|---|---|
| **Accelerating** | `share_change ≥ +3 pp` **AND** `volume_growth ≥ +20%` **AND** `n_A ≥ 10` **AND** `n_B ≥ 10` |
| **Fading** | `share_change ≤ −3 pp` **AND** `volume_growth ≤ −20%` **AND** `n_A ≥ 10` **AND** `n_B ≥ 10` |
| **Stable** | Any topic meeting the n ≥ 10 rule in both windows that is neither accelerating nor fading |
| **Insufficient data** | `n_A < 10` or `n_B < 10` in either window — no classification is made; the briefing says so plainly |
| **No prior baseline** | `n_B = 0` — reported as such, never as infinite growth |

**Velocity cross-check (mandatory, reported alongside every
classification):** if the volume classification is Accelerating but
`velocity_change < −30%`, or Fading but `velocity_change > +30%`, the
briefing flags the topic **"mixed signal"** and states both numbers — the
volume and velocity stories disagree, and neither is hidden. The
classification itself does not change (volume is primary), but the flag is
part of the deliverable.

**What the thresholds mean:** +3 pp of share plus +20% volume growth is
large enough that it cannot be produced by one or two extra videos in a
30-day window at the expected sample size (~150 per window), while small
enough to catch a real shift. The thresholds were set before the fetch runs
and must **not** be re-tuned after seeing the results — if no topic meets
them, the honest finding is "no topic accelerated or faded in this
window", not a reason to lower the bar.

**The age bias in velocity — stated, guarded, sensitivity-checked:**
`views_per_day` is systematically higher for young videos (a video's views
accumulate fastest just after publication, then slow). Window A videos are
0–30 days old (median age ~15 days); Window B videos are 30–60 days old
(median age ~45 days). **A raw Window A vs Window B `views_per_day`
comparison therefore favours Window A by construction.** Three fixed
mitigations, all mandatory:

1. **Minimum-age guard (7 days):** videos younger than 7 days are
   excluded from all velocity medians (their `views_per_day` is unstable
   — a 1-day-old video with 10,000 views scores 10,000/day). They still
   count in publish volume.
2. **Report median age alongside every velocity number:** every
   `median_views_per_day` cell in the dashboard, notebook and briefing
   carries its window's median `days_since_publish` and n, so the reader
   can see the age gap.
3. **Age-guard sensitivity check:** recompute `velocity_change` per topic
   with a **14-day guard** as well as the 7-day guard. If any topic's
   velocity direction flips between the two guards, the briefing reports
   both numbers and marks that topic's velocity call "sensitive to age
   guard". The volume classification is unaffected (it uses counts, not
   views).

**No causal claims.** A classification is reported as *"in this sample,
videos on topic X published in the last 30 days outnumbered those in the
prior 30 days by …"* — never "topic X is going viral" or "creators should
switch to X". The briefing's recommendation format follows Day 4:
recommendation + evidence numbers + sample basis + caveat, on every claim.

### 4.6 Validation — how the trend calls are checked (two checks + one mandatory hand-validation)

There is no ground-truth "trending topic" dataset, so validation is a
holdout check plus hand recomputation:

1. **Holdout backtest (the credibility core of this day).** Compute the
   §4.5 volume classification using **only weeks W1–W7** (train = W1–W7,
   test = W8). Predict the topic with the highest `topic_share` growth
   from the first half of the train period (W1–W3) to the second half
   (W5–W7); then check whether that topic is in the **top 2 by
   `topic_share` in W8**. Report hit or miss in the notebook, dashboard
   and briefing, with the numbers. A miss does not invalidate the
   classifications — it is reported as evidence about how stable the calls
   are over one week. **The holdout uses Layer B data only** (the Day 4
   frame is relevance-sampled and cannot backtest a date-ordered sample).
2. **Age-guard sensitivity (§4.5):** recompute `velocity_change` with the
   14-day guard; report any direction flip per topic.
3. **Tester hand-validation (mandatory):** the tester recomputes **one
   topic's full momentum numbers by hand from `videos.csv`** — `n_A`,
   `n_B`, `topic_share` in both windows, `share_change`,
   `volume_growth`, and `median_views_per_day` in both windows — and
   matches the processed CSV / dashboard to the last digit; recorded in
   `data/README.md` with the topic name and the hand-computed numbers.
   (Same convention as Days 1–5: one metric, verified by hand, recorded.)
4. **Sanity checks (pipeline must assert or report):** zero duplicate
   `videoId`s in the final frame; 100% duration parse, all > 0 s; no
   `publishedAt` in the future and none before 2005-04-23 (YouTube's
   launch); no `publishedAt` outside the two windows in Layer B; sample
   median `engagement_rate` roughly 0.5–8% (Day 4 sanity range — outside
   it means a definition or parsing error, stop and check); median
   `views_per_day` > 0, no infinite/NaN values among age-eligible videos.

### 4.7 What "good" looks like — targets table

| Metric | Target |
|---|---|
| Final videos in `videos.csv` (Layer B) | **≥ 200** (expected ~280–380; < 200 = thin-sample caveat, §3.4) |
| Videos per window | **≥ 100** in each of Windows A and B (else the momentum comparison is thin — report it) |
| Topics classifiable | **≥ 2 topics** with n ≥ 10 in both windows (expected: python, ai_ml, sql; career/bi_viz/general likely "insufficient data") |
| Weekly coverage | **≥ 7 of 8 full weeks** (W1–W8) with ≥ 5 videos total (else flag thin weeks on the chart) |
| `other` topic share | **≤ 30%** of the fresh sample (if above, report — do not re-tune, §4.1) |
| Sentiment videos | **≥ 3 of 5** topics with an analysed comment set (else the sentiment panel is thin-sample, §3.3) |
| Sentiment comments analysed | **≥ 150** (expected ~300–450) |
| Charts | Exactly 4 PNGs (§7), drawn to scale, legible, source-noted |
| Limitations | §3.1 snapshot limitation + §4.5 age bias + §3.7 tensions stated in README, dashboard, notebook and briefing — **zero** presentation of a snapshot comparison as a historical trend |

If a target is missed, the correct response is to report the miss and
diagnose it — **not** to re-tune the keyword lists, buckets, thresholds,
or age guard after seeing the results. The windows, thresholds and guard
are fixed in this brief before the fetch runs.

**Conventions the coder must not re-decide:** the 5 queries + 2 windows +
`order=date` + `maxResults=50` + one page per query-window per §3.4; the
Day 4 keyword topic rule per §4.1; weekly buckets per §4.3; the §4.4
formulas; the §4.5 thresholds; the 7-day age guard (with the 14-day
sensitivity check) per §4.5; the 5-video sentiment snapshot per §3.3 with
Day 5's scorer verbatim per §4.2. If any of these is unworkable, send it
back to the planner with the exact point — do not silently substitute a
different convention.

## 5. Exact file tree (mirror Days 4–5 shape)

```
day-06-viral-content-trend-explorer/
├── README.md
├── LICENSE                     # MIT (scaffolded; keep as-is)
├── requirements.txt
├── pyproject.toml
├── .gitignore                  # scaffold as-is (§3.5): must NOT exclude data/; only data/raw/*_synthetic.json
├── research_brief.md
├── plan.md                     # this file
├── data/
│   ├── README.md
│   ├── raw/
│   │   ├── search_data_analytics_prior.json
│   │   ├── search_data_analytics_recent.json
│   │   ├── search_machine_learning_tutorial_prior.json
│   │   ├── search_machine_learning_tutorial_recent.json
│   │   ├── search_python_data_analysis_prior.json
│   │   ├── search_python_data_analysis_recent.json
│   │   ├── search_artificial_intelligence_explained_prior.json
│   │   ├── search_artificial_intelligence_explained_recent.json
│   │   ├── search_sql_tutorial_prior.json
│   │   ├── search_sql_tutorial_recent.json
│   │   ├── videos_details.json
│   │   ├── channels_details.json
│   │   ├── comments_<video_id>.json   # one per sentiment video, ≤ 5 files
│   │   └── *_synthetic.json   # only if fallback used; git-ignored, never committed
│   └── processed/
│       ├── videos.csv          # ~280–380 rows expected: one row per Layer B video with all §4.4 fields + topic/window/week
│       ├── comments.csv        # ~300–450 rows expected: one row per analysed comment with §4.2 fields + video_id/topic
│       ├── trend_table.csv     # weekly-briefing input: one row per topic — n_A, n_B, shares, share_change, volume_growth, velocity medians + median ages (7- and 14-day guards), classification, mixed-signal flag
│       └── data_source.json    # source, generated_at_utc, synthetic, seed (null live / 42 synthetic), fetch_date, snapshot_dates, windows, queries, max_results_per_query, order, per_query_window, video_count, channel_count, quota_units_used, api, age_guard_days, overlap_with_day04_frame, counts
├── notebooks/
│   └── analysis.ipynb          # executes end-to-end offline via nbconvert
├── src/
│   ├── data_pipeline.py        # fetch, clean, metrics, sentiment snapshot, synthetic fallback, save outputs
│   ├── trends.py               # pure trend math — momentum, views_per_day, buckets, backtest — no I/O, no network
│   ├── sentiment.py            # Day 5 lexicon scorer COPIED VERBATIM (§4.2) — scoring + classification + non-Latin heuristic only; no themes
│   ├── make_charts.py          # regenerates exactly the 4 PNGs in §7, offline from committed CSVs
│   └── app.py                  # Streamlit trend detection dashboard (width='stretch', §6)
├── outputs/
│   ├── insights_summary.md     # plain-language findings (§2): one finding per question, each citing its number
│   ├── weekly_briefing.md      # the roadmap's weekly briefing (§4.4 of the brief): dated 2026-11-10, generated from trend_table.csv
│   └── charts/
│       ├── 01_trend_momentum.png
│       ├── 02_weekly_volume.png
│       ├── 03_views_velocity.png
│       └── 04_sentiment_mood.png
├── screenshots/
│   └── dashboard.png           # REAL capture of the running app (see §6)
└── tests/
    └── test_pipeline.py        # pytest, offline, ≥10 tests (see §6); replaces the scaffold tests/test_smoke.py — delete test_smoke.py, do not keep both test files
```

Build only what this tree lists. No extra files, no extra charts, no extra
dependencies. (Day 1's `publish_checklist.md` / `test_report.md` are produced
by later roles, not by the coder; the coder must not pre-create them.)

**Not in scope (deferred, do not add):** page 2 of any search (truncation
is flagged, not fetched, §3.4); `playlistItems`-based top-up (rejected,
brief §2.4); replies (`comments.list` — not fetched, §3.3); Day 5 theme
lists (not reused, §4.2); any new helper capability beyond the three
`search` flags already added; any extra query or window beyond §3.4; any
new runtime dependency (§3.7 of the brief — stdlib + the Day 1–5 stack;
sentiment scoring is hand-written, do not add `nltk`, `textblob`,
`vaderSentiment` or any other NLP package).

## 6. Per-file responsibilities

| File | Responsibility |
|---|---|
| `README.md` | Problem + audience (§1), dataset summary (source, endpoints, the 5 queries + 2 windows, Layer A / Layer B split, access date 2026-11-10, row counts, quota used, truncation flags, licence note), tools, method (topic rule §4.1, buckets §4.3, formulas §4.4, classification thresholds §4.5, age bias §4.5, sentiment scope §3.3), key insights (filled with real numbers after the run, each in the "in this sample …" form, never "going viral"), validation results (backtest hit/miss, sensitivity flips), visuals (the 4 charts embedded), how to run, limitations (§3.1 snapshot limitation, §4.5 age bias, §3.7 tensions), the cohort-comparison sentence in the header + "Data from the YouTube Data API v3" attribution with link to YouTube's Terms of Service. |
| `data/README.md` | Provenance (§3.5): provider, endpoints, the 5 queries + 2 windows, access date, quota units used, row counts (candidates → unique → final, per window, with each filter's count), truncation flags per query-window, channel concentration, the Layer A / Layer B split and why, licence/attribution note + tensions stated honestly, commit rule, one manually validated metric (by hand, with the numbers — the tester's hand-validation of one topic's full momentum numbers, §4.6 item 3), the backtest result, versions used for this build, and the `data_source.json` source-field correction if §3.5 applied. |
| `data/raw/*.json` | Verbatim YouTube API responses: one per query-window (`search_<query-slug>_<window>.json`, where `<window>` is `prior` or `recent` and slugs are `data_analytics`, `machine_learning_tutorial`, `python_data_analysis`, `artificial_intelligence_explained`, `sql_tutorial`), plus `videos_details.json`, `channels_details.json`, and one `comments_<video_id>.json` per sentiment video (≤ 5). Committed (small, <1 MB each). Never overwritten by synthetic data. |
| `data/processed/videos.csv` | One row per Layer B video, ~280–380 rows expected: `video_id, title, channel_id, channel_title, published_at, window, week, topic, query_origin, view_count, like_count, comment_count, subscriber_count, duration_seconds, duration_bucket, days_since_publish, views_per_day, engagement_rate, like_rate, comment_rate, views_per_subscriber, is_shorts`. `views_per_day` is NaN for videos aged < 7 days (§4.5 guard). |
| `data/processed/comments.csv` | One row per analysed comment, ~300–450 rows expected: `comment_id, video_id, video_title, topic, author_display_name, text, published_at, like_count, total_reply_count, sentiment_score, sentiment, scored_words, language_flag`. Text is stored verbatim (public comment text, dated snapshot — see §3.7). |
| `data/processed/trend_table.csv` | The weekly-briefing input, one row per topic (7 rows): `topic, n_A, n_B, share_A, share_B, share_change_pp, volume_growth, median_views_per_day_A, median_views_per_day_B, median_age_A, median_age_B, velocity_change_7d, velocity_change_14d, classification, mixed_signal, velocity_sensitive_to_guard`. Generated by `src/trends.py` from `videos.csv`; the briefing and dashboard read it, never hand-typed numbers. |
| `data/processed/data_source.json` | `source`, `generated_at_utc`, `synthetic` (bool), `seed` (`null` live / `42` synthetic), `fetch_date` (`"2026-11-10"`), `snapshot_dates` (`{"day04_frame": "2026-11-08", "fresh_fetch": "2026-11-10"}`), `windows`, `queries`, `max_results_per_query` (50), `order` (`"date"`), `per_query_window` (counts + `truncated` flags), `video_count`, `channel_count`, `quota_units_used`, `api` (`"youtube-data-api-v3"`), `age_guard_days` (7), `overlap_with_day04_frame`, `counts` (candidates, unique_after_dedupe, dropped_live_or_upcoming, dropped_no_view_count, final_videos, sentiment_videos, sentiment_comments_analysed). Subject to the §3.5 source-field rule (re-run live or restore before publishing). |
| `src/data_pipeline.py` | Fetch (10 `search` calls via the helper, ≥ 2 s spacing, one 30 s retry on 5xx only, then fallback; one page per query-window, §3.4; batched `videos` ≤ 50 IDs per call; batched `channels` ≤ 50 IDs per call; 5 `comment-threads` calls, §3.3; raw-size guard), load Layer A read-only from `../day-04-youtube-video-performance-analyzer/data/processed/videos.csv` for context only (never into the momentum frame), clean/dedupe/filter into the video frame (live/upcoming + no-`viewCount` steps, each counted), call `trends.py` for topics/buckets/metrics and `sentiment.py` for the 5-video mood snapshot, `generate_synthetic(seed=42)`, `--offline` / `--use-cache` mode (runs from committed cache, no network, never generates synthetic data), `save_outputs()` writing raw JSONs + `videos.csv` + `comments.csv` + `trend_table.csv` + `data_source.json`. Mirror Day 4/5's function shapes (`fetch_search_window`, `fetch_video_details`, `fetch_channel_details`, `fetch_sentiment_comments`, `clean_videos`, `load_day04_frame`, `save_outputs`, `generate_synthetic`, `_load_cache`, `main`) so the tester can reuse the Day 4/5 test patterns. **Never log the API key; never put the key in any file.** |
| `src/trends.py` | **Pure trend math. Pure, testable functions, no I/O, no network.** Signatures the coder must implement (names fixed so the pipeline, notebook, app and tests import them, never re-implement them): `assign_topic(title: str, tags: list[str], description: str) -> str` (Day 4 keyword rule, §4.1, first match wins in priority order); `parse_duration(iso: str) -> int` (ISO 8601 → seconds; Short ≤ 60 s etc. — `duration_bucket(seconds: int) -> str`); `assign_window(published_at) -> str` (`"A"` / `"B"`; boundary 2026-10-11T00:00:00Z belongs to A); `assign_week(published_at) -> str` (`"W1"`–`"W9"`, anchored 2026-09-11); `compute_views_per_day(view_count: int, days_since_publish: int, min_age_days: int = 7) -> float | None` (NaN/None below the guard); `topic_share(counts: dict, total: int) -> dict`; `volume_growth(n_a: int, n_b: int) -> float | None` (None when `n_b == 0`); `share_change(share_a: float, share_b: float) -> float`; `classify_topic(n_a: int, n_b: int, share_change_pp: float, volume_growth: float | None) -> str` (accelerating / fading / stable / insufficient data / no prior baseline, §4.5); `velocity_change(median_a: float, median_b: float) -> float | None`; `mixed_signal(classification: str, velocity_change: float | None) -> bool` (±30% rule, §4.5); `rolling_mean_2wk(weekly_counts: list[int]) -> list[float]`; `backtest_holdout(weekly: DataFrame) -> dict` (train W1–W7, predict top-share-growth topic W1–W3 → W5–W7, check top-2 in W8, §4.6); `sensitivity_check(...) -> dict` (7-day vs 14-day guard per topic). The keyword lists, window/bucket boundaries and thresholds live in this module as documented constants. |
| `src/sentiment.py` | **Day 5 lexicon scorer COPIED VERBATIM — the coder copies, not rewrites.** Copy Day 5's `src/sentiment.py` scoring functions into this day's own `src/sentiment.py` (same file, same rules, §4.2): `score_comment(text: str) -> tuple[float, str, int]` (compound score, class, scored-words count); `classify_sentiment(compound: float) -> str` (thresholds ±0.05); `is_non_latin(text: str) -> bool` (heuristic per §4.2). The lexicon word lists, strong-word set, negation/intensifier lists and emoji map live in this module as documented constants, copied from Day 5. **Do not copy Day 5's theme functions** (`classify_themes`, `top_words`, `top_bigrams`) — themes are Day 5's scope and are not implemented here. Do not re-tune any list, weight, window or threshold. Pure functions, no I/O, no network. |
| `src/make_charts.py` | `python -m src.make_charts` regenerates **exactly the 4 PNGs in §7** in `outputs/charts/`, offline from the committed processed CSVs only (no network, no API). Every chart: title, labelled axes with units, legend where needed, source note ("Source: YouTube Data API v3" or "SYNTHETIC DATA — API unavailable on 2026-11-10" when synthetic), readable at dashboard size, drawn **to scale** (no truncated or misleading axes). Must not create extra PNGs. |
| `src/app.py` | Streamlit trend detection dashboard: topic multi-select (default all), window comparison table (classification, share change, volume growth, mixed-signal flag, velocity medians with median age + n), weekly volume chart with 2-week rolling mean, velocity comparison, sentiment mood panel (per-video mean compound, shares, n — labelled "audience mood on the fastest-rising video in this topic", never "how viewers feel about the topic"), Layer A long-run context panel (clearly labelled "relevance sample, not exhaustive", never mixed into momentum numbers), channel-concentration note if §3.4 applies, truncation flags if any query-window was truncated, the snapshot-limitation sentence in the header (§4 of the brief — *"Trends here compare two 30-day cohorts of recently published videos. The API gives a current snapshot of each video's statistics, not daily history — so these are cohort comparisons, not a record of views rising or falling over time."*), backtest hit/miss panel, "Data from the YouTube Data API v3" attribution with link to YouTube's Terms of Service + synthetic banner if `data_source.json` says synthetic. **Layout must use `width='stretch'` (the current Streamlit API) — never the deprecated `use_container_width`** (Day 2 day-log lesson). **Human-readable labels everywhere** — no raw slugs (`ai_ml`, `bi_viz`) shown to the user; display "AI & Machine Learning", "Business Intelligence & Visualisation" etc. Must not crash on edge cases — Day 1 lesson (b): sort/reset indexes before any positional lookup. Must not display full comment text in bulk — aggregates + short excerpts only (§3.7). |
| `notebooks/analysis.ipynb` | Full analysis top-to-bottom, offline: load `videos.csv` (+ Layer A frame for the context panel only), recompute topics/buckets/metrics via `trends.py`, reproduce the 4 charts, answer each §2 question with numbers, show the backtest result and the age-guard sensitivity table, show the sentiment mood table. Resolve the project root from the notebook file's own location via `_find_root()` (check for `data/processed/videos.csv` from the notebook's directory upward); **never from `Path.cwd()` alone** — Day 1 lesson (e). A copy executed outside the project must fail with a clear `FileNotFoundError`. Must execute end-to-end offline via nbconvert (CI runs it). |
| `tests/test_pipeline.py` | pytest, offline, **≥10 tests** (target 12–14). Must cover at minimum: (1) topic assignment on hand-built cases (a "Python pandas tutorial" title → `python`; a title matching both `python` and `sql` keywords → `python`, because python is checked first in the §4.1 priority order; a title matching nothing → `other`); (2) window/week assignment at the boundaries (2026-10-11T00:00:00Z → Window A; 2026-10-10T23:59:59Z → Window B; 2026-11-06 → W9 partial); (3) `views_per_day` guard (age 3 days → excluded/NaN; age 7 days → computed; age 0 → minimum 1 day, never division by zero); (4) momentum math on a hand-computed frame (share change, volume growth, and the accelerating/fading/stable/insufficient-data thresholds at the boundaries: share +3 pp AND growth +20% with n ≥ 10 → accelerating; n = 9 → insufficient data; `n_B = 0` → no prior baseline, never infinite growth); (5) mixed-signal flag (accelerating + velocity −31% → True; accelerating + velocity −29% → False); (6) backtest on a constructed weekly frame (predicted topic in top-2 of W8 → hit; otherwise miss); (7) age-guard sensitivity (a constructed case where the 7-day and 14-day guards give opposite velocity directions → flagged sensitive); (8) sentiment copy (hand-computed cases from Day 5: "I love this tutorial, amazing work" → positive, exact compound to 4 dp; "This is terrible and boring" → negative; "not good" → negative via negation; "very helpful" → intensifier ×1.5 — verifying the copy matches Day 5's scorer, not a rewrite); (9) synthetic generation deterministic with seed 42 and n=300 with the Day 4 proportions (150/85/45/12/5/3) and the built-in python-rising / sql-falling trend (python share higher in W6–W9 than W1–W3, sql the reverse); (10) synthetic never overwrites the live cache and `*_synthetic.json` does not satisfy the cache check; (11) `--offline`/`--use-cache` runs without network; (12) committed CSV matches the published findings in README/insights/briefing (recompute one topic's momentum numbers from `videos.csv` and match `trend_table.csv`); (13) notebook `_find_root()` resolves correctly — **and the suite must pass both from the repo root and from inside the day folder** (Day 2 CI lesson: the test must exec the notebook namespace with `__file__` set to the notebook path, and the coder must run the full suite from both locations before handoff); (14) "Data from the YouTube Data API v3" attribution present in app + charts/README and the cohort-comparison sentence present in README + app + briefing. Replace the scaffold `tests/test_smoke.py` (delete it — do not keep both test files). |
| `outputs/insights_summary.md` | Plain-language findings (§2): one finding per §2 question (each citing its number from `videos.csv` / `comments.csv` and its chart), backtest + sensitivity results, limitations (§3.1, §4.5), cohort-comparison sentence. Does NOT carry the weekly briefing — that lives in `outputs/weekly_briefing.md` by this plan's choice (§5). |
| `outputs/weekly_briefing.md` | **Weekly briefing (the roadmap deliverable, this plan's choice of file — the brief fixes the artefact, not the generation rule):** dated 2026-11-10, states the two windows it covers, **generated from `data/processed/trend_table.csv`, not hand-written from memory**: the top accelerating and top fading topic called out first, one paragraph per classified topic (what changed, the numbers, the sample basis, the caveat — recommendation + evidence numbers + sample basis + caveat on every claim), the mixed-signal flags, the velocity-sensitivity notes, the sentiment mood lines (one per sentiment video, with n), and the backtest hit/miss. Topics with "insufficient data" are listed as such, never classified. No causal verbs anywhere. |
| `outputs/charts/*.png` | Exactly 4 PNGs (§7), regenerated by `src/make_charts.py`. No extra PNGs in this folder — CI asserts the count is exactly 4. |
| `screenshots/dashboard.png` | **REAL capture of the running Streamlit app** (full page), taken during the coder's smoke test — not a composite of the static charts. If a real capture is genuinely impossible, flag it explicitly as a composite in the handoff and in the README caption — do not silently pass a composite off as a screenshot. |
| `requirements.txt` | Pinned exact `==` versions, verified in the build venv (Python 3.12): `pandas`, `numpy`, `matplotlib`, `plotly`, `streamlit`, `requests`, `pytest`, **`jupyter==1.1.1` + `nbformat==5.11.1`** (required — CI executes the notebook via nbconvert). No new runtime dependency (brief §5.5 item 10); the exact pins are set at optimizer time from the venv that actually ran. The scaffold file currently carries Day 1's pins — the optimizer re-pins from this build's venv. |
| `pyproject.toml` | Ruff + black settings mirroring Day 5 exactly: `[tool.ruff] line-length = 88, target-version = "py312"`, `[tool.black] line-length = 88`, `[tool.pytest.ini_options] testpaths = ["tests"]`. Dev tools (ruff 0.17.4, black 26.10.1) are pinned once in the portfolio-root `requirements-dev.txt`, shared by all days. |
| `.gitignore` | Scaffold as-is, mirror Day 5 exactly: `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.venv/`, `venv/`, `.env`, `*.key`, `*.log`, `.streamlit/secrets.toml`, `.ipynb_checkpoints/`, plus `data/raw/*_synthetic.json` (synthetic fallback output is never committed; live `data/raw/*.json` IS committed). **Must NOT exclude `data/`** — diff `.gitignore` against this plan before sign-off (Day 1 lesson d). The orchestrator already passes this check for Days 4–5 (§3.5) — use the scaffold as-is. |
| `LICENSE` | MIT, keep as scaffolded. |

### Coder environment (Day 1/2/3/4/5 lessons applied)

- Create `.venv` with the pinned deps installed and hand it off working — the tester provisions nothing and must never install the project's own deps from scratch; if the venv is missing the tester reports "blocked: no venv".
- Run `black` + `ruff` **before** handoff (Day 1 lesson: lint left to the end cost a full fix cycle). `black --check` + `ruff check` must pass on `src/` and `tests/`.
- Capture the real `screenshots/dashboard.png` during the coder's own smoke test (fresh port 8502+, never assume 8501 is free; kill the server and verify the port is free afterwards — Day 1 lesson c).
- Run the full pytest suite **both from the repo root and from inside the day folder** before handoff (Day 2 CI lesson).
- One writer per file; build only what this plan lists; no extra web searches.
- **Verify the sentiment copy:** after copying Day 5's `src/sentiment.py` scoring functions, run the Day 5 hand-computed cases (§6 test 8) against the copy before any analysis code uses it — a copy that scores differently is a defect, not a rewrite opportunity.

## 7. Charts (exactly 4 — CI asserts the count)

`python -m src.make_charts` regenerates exactly these 4 PNGs, offline from
the committed processed CSVs. All 4 must be well-labelled (title, axes with
units, legend, source note), **drawn to scale** (no truncated or misleading
axes) and legible at dashboard size. Human-readable labels on every chart —
no raw slugs. Every velocity number carries its median age and n.

| # | Filename | Content |
|---|---|---|
| 1 | `01_trend_momentum.png` | **Trend momentum (the roadmap deliverable)** — per-topic share change (pp) and volume growth (%) between Windows B and A, as grouped bars with the **±3 pp / ±20% threshold lines** drawn, coloured by classification (accelerating / fading / stable / insufficient data), n per topic labelled, so which topics crossed the fixed thresholds — and on how much evidence — is visible at a glance. |
| 2 | `02_weekly_volume.png` | **Weekly publish volume per topic** — stacked bars of weekly volume per topic (W1–W9) with the **2-week rolling mean** line overlaid, thin topic-week cells (n < 5) flagged, **partial W9 marked** and excluded from week-over-week growth, so the time series the momentum call rests on is visible at a glance. |
| 3 | `03_views_velocity.png` | **Velocity comparison** — median `views_per_day` per topic per window (grouped bars, age ≥ 7 days only) with **median age and n annotated on every bar**, so the age bias is visible, not hidden — the reader can see Window A is younger than Window B. |
| 4 | `04_sentiment_mood.png` | **Sentiment mood** — mean compound score + positive/negative share for the 5 sentiment videos (one per topic, Window A top by `views_per_day`), with n per video, captioned "as classified by our rule-based model — five videos, not the topics". |

## 8. Success checklist (roadmap minimum success criteria — all must pass)

- [ ] Problem statement + audience written (§1, in README and this plan)
- [ ] Data source documented: provider, endpoints, the 5 queries + 2 windows, Layer A / Layer B split, collection date (2026-11-10), licence/attribution ("Data from the YouTube Data API v3" + link to YouTube's Terms of Service), quota used, row counts, truncation flags — in `data/README.md` and `data/processed/data_source.json` (with the §3.5 source-field rule satisfied: live re-run or restored field before publishing)
- [ ] Repeatable prep steps documented (fetch → clean → metrics → sentiment snapshot → charts, with `--offline` mode) + trend/sentiment definitions (§4) written down
- [ ] ≥2 well-labelled visualisations produced — Day 6 produces exactly 4 (§7), **drawn to scale and legible**, plus a functional dashboard: the Streamlit dashboard runs and renders (smoke gate, §9)
- [ ] Trend detection dashboard + weekly briefing delivered (roadmap): the dashboard shows weekly volume, velocity comparison, the classification table with mixed-signal flags, the sentiment mood panel and the caveats; `outputs/weekly_briefing.md` is generated from `trend_table.csv`, dated 2026-11-10, with the top accelerating/fading topics first — and all §4.7 targets pass (or each miss is reported and diagnosed, never tuned away)
- [ ] Interpretation written (`outputs/insights_summary.md`, one finding per §2 question) + **weekly briefing** (`outputs/weekly_briefing.md`, one paragraph per classified topic, generated from the computed table)
- [ ] README with setup instructions, sample outputs (momentum table + chart thumbnails), validation results (backtest hit/miss, sensitivity), and limitations
- [ ] No credentials / private records in the repo; no huge raw files committed (raw JSONs <1 MB each, <5 MB per day folder); `.gitignore` does not exclude `data/` (only `data/raw/*_synthetic.json`)
- [ ] One metric manually validated by hand and recorded in `data/README.md` (the tester recomputes one topic's full momentum numbers from `videos.csv`, matching to the last digit)
- [ ] Pipeline runs end-to-end from a clean checkout (`pip install -r requirements.txt`, `python -m src.data_pipeline --offline`, `python -m src.make_charts`, `pytest tests/ -q`) — **pytest passing both from the repo root and from inside the day folder**
- [ ] Notebook runs top-to-bottom without errors (offline, via nbconvert, with `_find_root()`)
- [ ] Pinned dependencies in `requirements.txt`; `black --check` + `ruff check` clean
- [ ] Streamlit smoke gate passed: fresh port 8502+, HTTP 200 on `/` and on `/_stcore/health`, real `screenshots/dashboard.png` captured, server killed and port verified free
- [ ] Charts to scale and legible; frozen-tree check passed immediately before push (every file the READMEs reference exists on disk — charts, screenshot, CSVs, briefing)
- [ ] **Snapshot limitation + age bias documented prominently** (roadmap requirement): §3.1 limitation + §4.5 age bias in README, dashboard, notebook, briefing and insights summary; **zero** presentation of a cohort comparison as a historical trend; **zero** sentiment numbers used in a trend classification

## 9. Coder handoff checklist (reference — coder must satisfy all of these before the tester starts)

Per AGENTS.md / Day 1 retrospective, the coder hands off only when **all**
of the following hold; the tester verifies in the coder's venv and provisions nothing:

1. `.venv` exists with pinned deps installed (requirements.txt matches the venv that actually ran).
2. `black --check src tests` and `ruff check src tests` pass (exit 0).
3. `pytest tests/ -q` passes (≥10 tests, offline) **from the repo root AND from inside the day folder**.
4. `.gitignore` matches §6 (in particular: does NOT exclude `data/`; excludes only `data/raw/*_synthetic.json`); scaffold used as-is (§3.5).
5. `screenshots/dashboard.png` is a REAL capture of the running app (or explicitly flagged as a composite in the handoff + README caption).
6. `python -m src.make_charts` regenerates exactly 4 PNGs in `outputs/charts/` (offline, from committed CSVs); notebook executes end-to-end offline via nbconvert.
7. Every number in README / dashboard / notebook / insights / briefing matches `data/processed/videos.csv`, `data/processed/comments.csv` and `data/processed/trend_table.csv`.
8. `data/processed/data_source.json` `source` field is correct for the published data (§3.5) — re-run live or restore before handoff.
9. `src/app.py` uses `width='stretch'` throughout — no `use_container_width` anywhere in the tree.
10. No causal verbs in any finding or briefing claim; the cohort-comparison sentence is in the README, app header, insights summary and briefing; no sentiment number is used in a trend classification; every sentiment share carries its "as classified by our rule-based model" qualifier.
11. `data/processed/trend_table.csv` exists with one row per topic and the briefing is generated from it, not hand-typed; the backtest hit/miss and sensitivity results in the README/insights/briefing are computed from `videos.csv`, not hand-typed.
12. `src/sentiment.py` is a verified copy of Day 5's scorer (§6 test 8 passes) — no re-derived or re-tuned lexicon, no theme functions.
13. `tests/test_smoke.py` is deleted; only `tests/test_pipeline.py` remains.

**Tester smoke gate (mandatory, for the tester's reference):** start
`streamlit run src/app.py` on a fresh port (8502 or higher, never 8501);
confirm HTTP 200 on `/` and on `/_stcore/health` with a clean server log;
capture a full-page screenshot to `screenshots/dashboard.png`; kill the server
and verify the port is free; record port, HTTP statuses and screenshot size in
`test_report.md`. The tester also recomputes one topic's full momentum numbers
by hand from `videos.csv` (§4.6 item 3) and records them in `data/README.md`.

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| YouTube 403 `quotaExceeded` / outage on fetch day | ≥ 2 s spacing, one 30 s retry on 5xx only, then cached → synthetic (§3.8); synthetic is labelled everywhere and re-fetched before publishing. Quota-cost discrepancy (1 vs 2 units): coder's actual fetch is ground truth (§3.4). |
| `order=relevance` or `order=viewCount` used by habit | Brief §2.2 forbids both; this plan repeats the ban (§3.4); tester checks the fetch code. |
| Thresholds / keywords / age guard re-tuned after seeing results | §4.5/§4.1 forbid it: a miss is diagnosed, not tuned away; thresholds, taxonomy and guard are fixed before the fetch and frozen at coder handoff. |
| Cohort comparison presented as a historical trend | §3.1 limitation sentence + checklist item 10: the sentence is in the README, app header, insights and briefing; tester greps the wording. |
| Velocity read without its age bias | §4.5 mitigations: 7-day guard, median-age annotation on every velocity number, 14-day sensitivity check; chart 03 annotates median age on every bar. |
| `pageInfo.totalResults` used as a count | Brief §1.4 proves it unreliable; this plan repeats the ban (§3.1); pipeline counts rows from fetched items only. |
| Layer A mixed into the momentum math | §3.2/§5: Layer A is read-only context, loaded by a separate function, never in the momentum frame; tester checks the pipeline never merges the layers. |
| Truncated query-window read as a full window | §3.4 `truncated` flag per query-window in `data_source.json` + README statement; weekly volume for a truncated query-window is a lower bound, stated as such. |
| Sentiment mood read as topic sentiment | §3.3/§4.2: sentiment is 5 videos only, never enters a classification; dashboard labels the panel "audience mood on the fastest-rising video in this topic"; checklist item 10. |
| One channel dominating a window | §3.4 concentration rule (> 20% → dashboard says so); §4.7 targets. |
| Sentiment scorer re-derived instead of copied | §4.2/§6: copy verbatim, verify with the Day 5 hand-computed cases (§6 test 8) before use; handoff checklist item 12. |
| `use_container_width` deprecation (Day 2 day-log lesson) | §6 mandates `width='stretch'` in `app.py`; handoff checklist item 9 greps for the deprecated call. |
| Offline run overwriting `data_source.json` source to `"cache"` (Day 2 day-log lesson) | §3.5 rule: re-run live or restore the field before publishing; handoff checklist item 8; publisher frozen-tree check includes it. |
| `.gitignore` silently dropping raw data (Day 1 lesson d) | §6 diff check at coder handoff; publisher frozen-tree check before push. The orchestrator check already passes for Days 4–5 (§3.5) — use the scaffold as-is. |
| Screenshot going missing before push (Day 1 lesson) | Treat `screenshots/dashboard.png` as a checked deliverable; verify it exists at every handoff; publisher re-verifies immediately before pushing. |
| Notebook cwd trap (Day 1 lesson e) + Day 2 CI failure (test passed inside the day folder, failed from the repo root) | `_find_root()` from the notebook file's own location; notebook test execs with `__file__` set to the notebook path; full suite run from both locations (§6, test 13). |
| Dashboard crash invisible to pytest (Day 1 lesson b) | Mandatory Streamlit smoke gate (§9) + real screenshot. |
| Chart count drift (extra PNG breaks CI) | `make_charts.py` writes exactly the 4 files in §7 and no others; CI asserts count == 4. |
| API key leaked into code/logs/repo | Key comes only from the connector (§3.5); pipeline never logs it; tester checks for secrets. |
| Thin sample read as a trend | §4.7 targets (≥ 200 videos, ≥ 100 per window, ≥ 2 classifiable topics, ≥ 7 of 8 full weeks); misses are reported, never tuned away. |
| Weekly W9 partial read as a full week | §4.3: W9 flagged on every chart and excluded from week-over-week growth; chart 02 marks it. |

## 11. Brief-vs-plan differences

**No contradictions on data, sample, method, sentiment or validation.** This
plan adopts the brief's endpoints and parameters (§3.1, verbatim), the
two-layer design (§3.2), the 5 queries × 2 windows + `order=date` +
`maxResults=50` + one page per query-window (§3.4), the quota budget
≤ 1,018 units (§3.4), the expected row counts 500 → ~300–400 → ~280–380
(§3.4), the 5-video sentiment snapshot (§3.3), the Day 4 topic taxonomy
(§4.1, verbatim), the weekly buckets (§4.3), the metric formulas (§4.4,
verbatim), the classification thresholds (§4.5, verbatim), the 7-day age
guard + 14-day sensitivity check (§4.5), the holdout backtest + hand
validation (§4.6), the synthetic parameters (seed 42, n=300, §3.8), the
licence tensions (§3.7) and the out-of-scope ruling on page 2 / top-ups /
replies (§5) without change. Additions and choices made by the plan (not
contradictions):

- **Trend module named `src/trends.py` (plural), not `src/trend.py`.** The
  brief's §4 deliverable shape names `src/trend.py`; the task for this plan
  and the Days 4–5 convention use the plural form. The plan wins: the file
  is `src/trends.py`, with the fixed function signatures in §6.
- **Chart filenames and order chosen by the plan:** `01_trend_momentum.png`
  (share change + volume growth with threshold lines),
  `02_weekly_volume.png` (weekly volume + rolling mean),
  `03_views_velocity.png` (median views/day with median age),
  `04_sentiment_mood.png`. The brief's §4 lists the same four chart
  contents but in a different order (weekly volume first, momentum
  second); the plan puts the momentum chart first because it is the
  roadmap deliverable, and names the files per the task. Contents are
  unchanged.
- **Processed-file names fixed** where the brief left them to the plan:
  `videos.csv` (one row per Layer B video, §6 column list),
  `comments.csv` (one row per analysed comment), `trend_table.csv` (the
  weekly-briefing input — one row per topic with all momentum numbers,
  §6), and `data_source.json` (with the brief's §5.4 field list).
- **Raw-file names fixed:** `search_<query-slug>_<window>.json` with
  `<window>` = `prior` / `recent` and the five slugs in §5;
  `videos_details.json`, `channels_details.json`,
  `comments_<video_id>.json` (≤ 5 files).
- **Weekly briefing generation rule chosen:** `outputs/weekly_briefing.md`
  is generated from `data/processed/trend_table.csv` (the brief fixes the
  artefact, not the generation rule); the plan fixes the rule so the
  briefing can never drift from the dashboard numbers.
- **New module `src/trends.py`** with fixed function signatures (§6) —
  the brief names the module but fixes no signatures; the pipeline module
  keeps the Day 4/5 shape.
- **Sentiment scope narrowed to the copy:** `src/sentiment.py` carries
  only `score_comment`, `classify_sentiment` and `is_non_latin`, copied
  verbatim from Day 5 — the brief says "Day 5's scorer copied verbatim"
  and the plan makes explicit that the theme functions are NOT copied
  (themes are Day 5's scope) and adds the verification step (§6 test 8,
  §9 item 12).
- **Exact 4 chart filenames** (§7) and the ≥10-test list (§6), including
  the Day 2 CI lesson (suite must pass from the repo root AND inside the
  day folder).
- **Targets table (§4.7) added by the plan:** ≥ 200 videos, ≥ 100 per
  window, ≥ 2 classifiable topics, ≥ 7 of 8 full weeks, `other` ≤ 30%,
  ≥ 3 of 5 sentiment videos, ≥ 150 analysed comments — the brief states
  the underlying expectations but fixes no pass/fail numbers; these are
  the plan's fixed targets.
- **Fetch spacing:** the plan states ≥ 2 s between calls (the brief's
  verified polite-use rule, §1.7); this is stricter than a 1 s minimum and
  therefore satisfies it.
- **`.gitignore` note (§3.5):** no orchestrator change is needed for this
  day — the shared orchestrator already passes the `.gitignore` check for
  Days 4–5 (verified this run), so the coder/optimizer use the scaffold
  `.gitignore` as-is; the credentials scanner is NOT weakened.
- **Day-log lessons applied:** `width='stretch'` (not `use_container_width`)
  in `app.py`; human-readable labels (no raw slugs) in the dashboard and
  charts; the `data_source.json` `"cache"` source-field rule (§3.5);
  `_find_root()` from the notebook's own location (Day 1 lesson e);
  `.gitignore` must NOT exclude `data/` (Day 1 lesson d); real screenshot
  at coder/tester handoff (not a composite); coder runs black+ruff before
  handoff; tester provisions nothing.
- **3 research questions** (§2) instead of Day 5's 3 sentiment questions,
  per this day's scope.

If the coder finds any of these unworkable, it goes back to the planner with
the exact point — the coder does not silently substitute a different
convention.

## 12. Build order (coder)

1. `.venv` + pinned deps → 2. `src/trends.py` (pure functions: topics →
   windows/weeks → views-per-day → momentum → classification → backtest →
   sensitivity, §6) → 3. `src/sentiment.py` (**copy** Day 5's scorer
   verbatim, §4.2, and verify it with the Day 5 hand-computed cases
   before any analysis code uses it) → 4. `src/data_pipeline.py` (fetch
   the 10 query-windows → dedupe/filter → detail calls → sentiment
   snapshot → save; verify ~280–380 rows, report quota units used, filter
   counts, truncation flags, and channel concentration) → 5. `pytest` on
   the trend tests as they land (from both the repo root and the day
   folder) → 6. `src/make_charts.py` (exactly 4 PNGs) → 7.
   `notebooks/analysis.ipynb` (offline, `_find_root()`) → 8. `src/app.py`
   + smoke test + real `screenshots/dashboard.png` → 9. `README.md`,
   `data/README.md`, `outputs/insights_summary.md`,
   `outputs/weekly_briefing.md` (numbers from the CSVs /
   `trend_table.csv` only) → 10. `black` + `ruff` + full `pytest` (both
   locations) + handoff checklist (§9). **No orchestrator change is needed
   for this day (§3.5) — there is no step 0 fix; the coder starts at step
   1.**

**Token note:** this plan reuses the brief's verified numbers (endpoints,
windows, quota budget, topic rule, buckets, formulas, thresholds, age
guard, sentiment rules, synthetic parameters) verbatim — no re-verification,
no extra searches. Later roles reuse the tester's verified figures
verbatim; nobody recomputes a finding from scratch (a spot-check from the
committed CSVs is the most that is ever needed).

## 13. Handoff (planner → coder)

**What was produced:** exactly one file —
`day-06-viral-content-trend-explorer/plan.md` (this file). No other file
was written or modified.

**Exact file tree the coder must build:** §5 — `README.md`, `LICENSE`,
`requirements.txt`, `pyproject.toml`, `.gitignore`, `data/README.md`,
`data/raw/` (10 `search_<query-slug>_<window>.json` files,
`videos_details.json`, `channels_details.json`, ≤ 5
`comments_<video_id>.json` files),
`data/processed/` (`videos.csv`, `comments.csv`, `trend_table.csv`,
`data_source.json`), `notebooks/analysis.ipynb`, `src/`
(`data_pipeline.py`, `trends.py`, `sentiment.py`, `make_charts.py`,
`app.py`), `outputs/` (`insights_summary.md`, `weekly_briefing.md`,
`charts/` with exactly 4 PNGs), `screenshots/dashboard.png`,
`tests/test_pipeline.py` (replacing `tests/test_smoke.py`, which is
deleted). Build only what §5 lists — no extra files.

**Known gaps:** no historical daily statistics (the defining limitation —
handled by the cohort design, not worked around, §3.1); search truncation
at 50/page is possible and only flagged, not fetched past (§3.4);
`career` / `bi_viz` / `general` will likely be "insufficient data" for
momentum (n < 10 per window expected); `pageInfo.totalResults`
unreliable (never use it); velocity comparisons carry an age bias even
after the guard (mitigated, not eliminated, §4.5); the holdout backtest is
a one-week check, not a proof of stability; June 2026 quota-bucket split
means the coder's actual fetch is the ground truth on quota (§3.4);
quota-cost documentation conflict (1 vs 2 units — coder's actual fetch is
ground truth, §3.4); no new dependency is added, so pins are set at
optimizer time from the venv that actually ran.

**Coder's first step:** create the `.venv` and write `src/trends.py` (the
pure trend math, §6) before any fetch code — then fetch the live data (the
10 query-windows in §3.4, `order=date`, `maxResults=50`, one page per
query-window) before writing any analysis code. Copy Day 5's sentiment
scorer verbatim (§4.2) and verify the copy with the Day 5 hand-computed
cases before the sentiment snapshot uses it.
