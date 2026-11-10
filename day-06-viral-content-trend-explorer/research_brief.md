# Research Brief — Day 6: Viral Content Trend Explorer

**Project:** Day 6 of the 60-day Data + AI portfolio
**Roadmap entry (exact):** "DAY 06 | Viral Content Trend Explorer — Problem / analysis: Track publicly accessible content/topic metrics over time to identify accelerating and fading trends. GitHub deliverable: Trend detection dashboard and weekly briefing." Section context (Days 4–6, Social Media & Digital Marketing): Core skills: API integration, NLP, sentiment analysis, text visualization. Suggested data: YouTube Data API; public, permissioned comment and metadata datasets.
**Date written:** 2026-11-10 (researcher role, role 1 of 6)
**Status:** Research only — two lean verification probes were run (see §1.3) plus a minimal helper extension (see §1.4). No live dataset was fetched. Fetching is the coder's job.

---

## 1. Verified source, endpoints, and parameters

### 1.1 Source

**YouTube Data API v3** — base URL `https://youtube.googleapis.com/youtube/v3` — via the `custom.youtube` connector (`~/workspace/custom-connectors/custom.youtube/`, helper `bin/youtube.py`). Read-only API-key auth: the key belongs to Victor's Google Cloud project `60-day-data-ai-portfolio` (project ID `day-data-ai-portfolio`), restricted to YouTube Data API v3 only, free tier, no payment method. **The key is held by the connector and is never put in any file, env var, log, command argument, or the repo.** The helper sends it as the `key` query parameter through the connector's surrogate exchange; redirects are refused by the helper.

This day reuses the Day 4 data source (YouTube) and adds a **new capability** (time-bounded search, §1.4) plus a **small new endpoint use** (comment threads on 5 videos, §2.3). Nothing from Days 1–3 carries over except the workflow conventions (provenance, synthetic fallback, `.gitignore` rule — see §5).

### 1.2 The snapshot limitation — read this first, it drives the whole design

The YouTube Data API returns a **current snapshot** of each video's statistics (`viewCount`, `likeCount`, `commentCount` as they stand at fetch time). **It does not return historical daily views, likes, or comments for a video.** There is no endpoint that gives "views on 2026-10-20" for a video published on 2026-10-01.

Therefore "trend over time" in this project is built from **two things the API does give**:

1. **Publish-date cohorts.** Every video has a `publishedAt`. Grouping videos by the week they were published gives a genuine time series of *publish volume per topic* (how many data/AI videos on each topic appeared each week) — and each video's *current* `views_per_day` (views / days since publish) is a velocity measure for its cohort.
2. **Repeated, time-bounded search snapshots.** `search.list` accepts `publishedAfter` / `publishedBefore` (§1.2 table), so the coder fetches two consecutive 30-day windows with `order=date` — the closest the API comes to an exhaustive recent sample — instead of relying on Day 4's relevance-ranked snapshot.

**What this design must never claim:** that any chart shows a video's views rising or falling day by day, or that a topic's views "grew" between two dates. The honest claims are: (a) *more/fewer videos on topic X were published recently than before* (volume momentum), and (b) *recently published videos on topic X are accumulating views faster/slower per day of life than the previous cohort did* (velocity momentum, with the age bias stated in §3.5). Every output states this.

### 1.3 Endpoints (verified from the official docs + live probes, 2026-11-10)

| Command | API endpoint | Parameters sent by the helper | Cost |
|---|---|---|---|
| `search --query "..." --max-results N --order date --published-after T --published-before T --page-token T` | `GET /search` | `part=snippet`, `q=<query>`, `type=video`, `maxResults=N`, `order=date`, `publishedAfter=<RFC 3339>` (only when given), `publishedBefore=<RFC 3339>` (only when given), `pageToken=<token>` (only when given) | **100 units** |
| `videos --ids ID[,ID...]` | `GET /videos` | `part=snippet,statistics,contentDetails`, `id=<comma-separated, up to 50>` | **1 unit** |
| `channels --ids ID[,ID...]` | `GET /channels` | `part=snippet,statistics`, `id=<comma-separated, up to 50>` | **1 unit** |
| `comment-threads --video-id ID --max-results N --order time --page-token T --text-format plainText` | `GET /commentThreads` | `part=snippet`, `videoId=<id>`, `maxResults=N` (1–100), `order=time`, `textFormat=plainText`, `pageToken=<token>` (only when given) | **1 unit** |

Full invocations (the new ones):

```text
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py search --query "data analytics" --max-results 50 --order date --published-after 2026-10-11T00:00:00Z --published-before 2026-11-10T00:00:00Z
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py search --query "data analytics" --max-results 50 --order date --published-after 2026-10-11T00:00:00Z --published-before 2026-11-10T00:00:00Z --page-token NEXT_PAGE_TOKEN
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py videos --ids ID[,ID...]
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py comment-threads --video-id VIDEO_ID --max-results 100 --order time --text-format plainText
```

**Docs verification (2026-11-10):** the official `search.list` reference (`https://developers.google.com/youtube/data/reference/rest/v3/search/list`) lists `publishedAfter` ("only contain resources created at or after the specified time", RFC 3339) and `publishedBefore` ("created before or at the specified time", RFC 3339) as query parameters, and `order=date` ("resources are sorted in reverse chronological order based on the date they were created"). The generated client-library reference confirms the same parameter set. The same docs page notes that to reliably retrieve a channel's most recent uploads, `playlistItems.list` should be used instead of `search.list` — this build does not need per-channel uploads, so that note is recorded here and not acted on.

### 1.4 Verification probes (the lean probes — run 2026-11-10, both exit 0)

**Helper extension made for this day (minimal, documented):** `bin/youtube.py` `search` subcommand gained three optional arguments — `--published-after`, `--published-before`, `--page-token` — passed through to the API only when given. No other command was changed; the Day 4/5 behaviour (`comment-threads`, `comments`, `videos`, `channels`, `playlist-items`) is untouched. The usage docstring was updated with one example line. `search --help` exits 0 and lists all three new flags.

**Probe 1 — time-bounded, date-ordered search:**

```text
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py search --query "data analytics" --max-results 2 --order date --published-after 2026-10-11T00:00:00Z --published-before 2026-11-10T00:00:00Z
```

- **Result:** exit 0, ~1.2 s. Response `kind: "youtube#searchListResponse"`, `regionCode: "US"`, `pageInfo: {totalResults: 455684, resultsPerPage: 2}`, `nextPageToken: "CAIQAA"` present.
- **Items:** (1) `IMgoI6yIm3Q` — "LET'S SOLVING VBA ERRORS ON MS. EXCEL TOGETHER! #dataanalytics #excel …", channel "Nugrah The Analyst", published `2026-11-09T23:04:15Z`; (2) a second video, also published 2026-11-09. **Both `publishedAt` values fall inside the requested window** — the date filter works as documented.
- **Finding — `pageInfo.totalResults` (455,684) is a capped estimate, not a real count** (Day 4's probe saw 1,000,000 for a similar query). Never report it as a finding; count rows from the fetched items.
- **Finding — date-ordered search returns Shorts and very recent uploads.** The probe's top items include Shorts-length content published hours before the call. Shorts are kept and bucketed by duration (Day 4 convention, §3.2); the dashboard must state the Shorts share of each window.
- **Cost: 100 units.**

**Probe 2 — pagination with the token from Probe 1:**

```text
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py search --query "data analytics" --max-results 2 --order date --published-after 2026-10-11T00:00:00Z --published-before 2026-11-10T00:00:00Z --page-token CAIQAA
```

- **Result:** exit 0, ~0.6 s. Response `kind: "youtube#searchListResponse"`, `nextPageToken: "CAQQAA"` present. Items: `fIv3G9sZJTU` (published `2026-11-09T22:09:31Z`) and `DAwERBXKaRI` (published `2026-11-09T21:27:29Z`) — **two different videos from Probe 1, still inside the window, still in reverse-chronological order**. `--page-token` works for search.
- **Cost: 100 units.**

**Probe total: 200 units.** No further probe calls were made — the coder does the live fetch.

### 1.5 Response fields the coder will use

**`search` → `snippet` (per video):** `videoId`, `title`, `channelId`, `channelTitle`, `publishedAt` (ISO 8601 UTC), `description`, `liveBroadcastContent` (`"none"` for ordinary videos). Search returns **no statistics** — views/likes/comments require the `videos` call. Filter out any item with `liveBroadcastContent != "none"`.
**`search` → top level:** `nextPageToken` (absent on the last page), `pageInfo.totalResults` (**unreliable estimate — never report it**, §1.4).
**`videos` → `snippet`:** `title`, `channelId`, `channelTitle`, `publishedAt`, `description`, `tags` (may be absent), `categoryId`, `defaultLanguage` (may be absent), `liveBroadcastContent`.
**`videos` → `statistics`:** `viewCount`, `likeCount`, `commentCount` — **all arrive as strings**; cast to int. `likeCount` and/or `commentCount` may be **absent** (likes/comments disabled) — record as missing (NaN), never silently fill with 0. `viewCount` absent means the video is unusable — drop the row and count it.
**`videos` → `contentDetails`:** `duration` (ISO 8601, e.g. `PT12M34S` — parse to seconds; Shorts are `PT60S` or less), `definition`, `dimension`, `licensedContent`.
**`channels` → `statistics`:** `subscriberCount` (hidden for some channels — record as missing, never 0), `viewCount`, `videoCount`.
**`commentThreads` → `snippet.topLevelComment.snippet` (per thread):** `id`, `textDisplay` (with `textFormat=plainText` this equals `textOriginal`; use `textDisplay`), `authorDisplayName`, `authorChannelId.value`, `likeCount` (int), `publishedAt`. Thread-level `snippet`: `channelId` (the video's channel), `videoId`, `totalReplyCount`. `pageInfo.totalResults` is unreliable here too (Day 5, §1.3) — never use it as a count.

### 1.6 What the API does NOT offer (verified — do not assume otherwise)

- **No historical statistics.** No endpoint returns a video's daily views/likes/comments over time (§1.2). All velocity metrics are computed from the single fetch-time snapshot divided by age.
- **No `publishedAfter` / `publishedBefore` on `commentThreads.list`** (Day 5, §1.5). The §2.3 comment fetch is newest-first with no date filter; it is a mood snapshot of the trending videos, not a time series.
- **Search returns at most 50 results per call** (API limit) and the API caps search at 500 results per query (connector doc). With `order=date` + a 30-day window, a query that returns exactly `maxResults` items may be **truncated** — the newest 50 only. The pipeline records a `truncated` flag per query-window (§2.4) and the README states it; it does not silently fetch more pages (see §2.2 for why only one page is authorised).
- **Search relevance/date ranking is a black box.** Findings are descriptive of the returned set. Two queries returning overlapping top results is itself a finding about topic overlap — report the dedupe counts.
- **Read-only, public data only.** No posting, no private data (API key, no OAuth scopes). Timeout 30 s per request (helper). Redirects refused.

### 1.7 Quota and rate limits (verified)

- **Daily quota: 10,000 units/day, free tier, resets at midnight Pacific Time.** Search = 100 units; videos/channels/commentThreads = 1 unit each (connector doc + official docs + probes).
- **Polite-use rule for the coder:** ≥ 2 s between calls; one retry after 30 s on HTTP 5xx only; **no retry on 403 `quotaExceeded`** — stop and fall back (§5). Never hammer the API.
- **Quota budget for the planned build (§2):** 10 searches × 100 = **1,000** + ≤ 10 batched `videos` calls × 1 = **≤ 10** + ≤ 3 batched `channels` calls × 1 = **≤ 3** + 5 `comment-threads` calls × 1 = **5** → **≤ 1,018 units (~10% of the daily quota)**. Including this brief's 200-unit probe, the day total is ≤ **1,218 units (~12%)**. There is ample headroom for one full re-run if a call fails; there is no headroom for exploratory extra searches, so the coder runs exactly the §2 design.
- **June 2026 quota change (open item, same as Days 4–5):** Google split the daily quota into separate buckets from 2026-06-01. The 10,000-unit framing above is the connector doc's figure and the probes succeeded within it, so the build proceeds on that basis — but the coder's actual fetch is the ground truth (see §5.4).

### 1.8 Error handling

| Error | Meaning | Coder action |
|---|---|---|
| `400 keyInvalid` | Stored key wrong or project misconfigured | Stop. Do not retry. Report as blocked; key is the connector's business, never to be pasted or hard-coded anywhere. |
| `403 quotaExceeded` | Daily quota hit | Stop immediately. No retry. Fall back to cache, then synthetic (§5). |
| `403 accessNotConfigured` | YouTube Data API v3 not enabled on the project | Stop. Report as blocked (it was enabled 2026-11-07 and the probes succeeded, so this is not expected). |
| `403` other (e.g. `forbidden`) | Request rejected for another reason | Check the request first (IDs well-formed, ≤ 50 per call, RFC 3339 dates well-formed); one careful retry only if the request was malformed. |
| HTTP 5xx / timeout | Transient server/network failure | One retry after 30 s, then fall back (§5). |
| Empty `items` on a `videos` call | IDs invalid, private, or deleted | Drop those IDs, count them, continue — this is not an error. |
| Empty `items` on a `search` call for a query-window | No matching videos in that window (possible for a narrow query) | Record 0 for that query-window, continue — this is a finding (a quiet window), not an error, unless ≥ 3 of the 10 query-windows return 0. |
| Empty `items` on a `comment-threads` call | Comments disabled on that video, or none returned | Record 0 fetched for that video, continue with the other 4 (§2.3). Do not treat as a build failure unless ≥ 3 of the 5 videos return 0. |

The helper exits non-zero with `HTTP {code} from {path}: {body[:500]}` — the pipeline must catch that, log the code/reason, and follow the table above. **Never log the API key** (the helper never prints it; keep it that way).

---

## 2. Sample strategy (what the coder fetches — bounded, reproducible)

### 2.1 The two data layers (fixed — do not add a third)

| Layer | What it is | Cost | Role in the analysis |
|---|---|---|---|
| **A. Day 4 frame (reused, not re-fetched)** | `day-04-youtube-video-performance-analyzer/data/processed/videos.csv` — 244 videos, fetched live 2026-11-08, stats snapshot as of that date | **0 units** (read the committed CSV) | Long-run context only: topic shares and weekly publish volume back to 2017, labelled "relevance sample, not exhaustive". Never mixed into the momentum windows (different snapshot date, different selection method). |
| **B. Fresh time-bounded searches (the trend sample)** | 5 queries × 2 windows (§2.2), `order=date`, `maxResults=50`, then batched `videos` + `channels` calls | **≤ 1,013 units** | The momentum analysis: weekly publish volume per topic, velocity per topic per window, trend classification (§3). All trend calls come from this layer only. |

**Day 4 frame facts (computed from the committed CSV, 2026-11-10):** 244 videos; topics **python 123 / ai_ml 68 / sql 39 / career 10 / bi_viz 3 / general 1**; publish range **2017-05-19 → 2026-11-07**; by year: 2026: 49, 2025: 56, 2024: 47, 2023: 31, 2021: 13, 2022: 13, 2018: 12, 2020: 11, 2019: 8, 2017: 4. **Only 18 videos were published in the last 90 days before the Day 4 fetch, 28 in the last 180 days, 59 in the last 365 days; 185 are over a year old.** This is why Layer A alone cannot support a trend call and Layer B exists: a relevance-ranked snapshot is old-heavy, and its weekly counts are not a publish-volume time series. Median `views_per_day` in the Day 4 frame (for context, not for momentum): python 488.7, ai_ml 913.6, sql 707.1, career 642.4, bi_viz 2,573.9 (n=3 — unreliable), general 108.2 (n=1 — meaningless).

### 2.2 Fresh searches — fixed design (primary)

**Fetch date: 2026-11-10.** Two consecutive 30-day windows:

- **Window B (prior):** `2026-09-11T00:00:00Z` → `2026-10-11T00:00:00Z`
- **Window A (recent):** `2026-10-11T00:00:00Z` → `2026-11-10T00:00:00Z`

Five queries — **the same five as Day 4** (so the topic mix is comparable to the Day 4 frame), one page each per window, `order=date`:

| # | Query | Per window | Why this topic |
|---|---|---|---|
| 1 | `data analytics` | 50 | Core topic — the portfolio's own field |
| 2 | `machine learning tutorial` | 50 | AI/ML tutorial demand |
| 3 | `Python data analysis` | 50 | Tool-specific (Python) demand |
| 4 | `artificial intelligence explained` | 50 | AI explainer demand |
| 5 | `SQL tutorial` | 50 | Tool-specific (SQL) demand |

- **Order:** `date` (newest first) — deliberate: within a bounded window this is the closest the API comes to an exhaustive recent sample. Do **not** use `order=relevance` here — it would return a relevance-ranked mix and destroy the publish-volume time series. Do **not** use `order=viewCount` — it would return only the most-viewed videos and destroy the variance the velocity comparison needs.
- **Pagination:** **one page only per query-window** (no `--page-token` follow-up in the build, even though the helper now supports it — the probe verified it works, the build does not need it). If a query-window returns exactly 50 items, record `truncated: true` for it in `data_source.json` and state it in the README; do not fetch page 2. Rationale: a second page per query-window would double the search quota to 2,000 units for the tail of the window, and the first page (newest 50) already covers the volume signal; the truncation is a stated limitation, not a hidden one.
- **Deduplicate** by `videoId` across the five queries within each window (overlap is expected — e.g. a Python tutorial can match queries 1, 3 and 5). Keep the first occurrence; record the query of origin for every video and how many duplicates were dropped per window. A video cannot appear in both windows (its publish date is unique); if one does (API quirk), keep the window whose bounds contain its `publishedAt` and record it.
- **Deduplicate against Layer A:** videos already in the Day 4 frame that reappear in the fresh searches are kept **once, as fresh rows** (their stats are the 2026-11-10 snapshot); the overlap count is recorded. The Day 4 frame itself is never edited.
- **Filter:** drop `liveBroadcastContent != "none"`; drop rows with no `viewCount` after the `videos` call.
- **Detail fetch:** collect all surviving IDs per window and fetch in **one batched `videos` call per ≤ 50 IDs** (expect ≤ 10 calls total). Then **one batched `channels` call per ≤ 50 distinct `channelId`s** (expect ≤ 3 calls) for subscriber counts.
- **Expected row counts (coder must verify the actuals and report them; do not assume these):** 10 searches × 50 = **500 candidates** → after dedupe **~300–400 unique videos** → after filtering/missing statistics **~280–380 final videos** (≈ 140–190 per window). If the final count lands below **200**, the coder reports it as a thin-sample caveat in the README; the analysis still runs, but momentum classifications for topics with n < 10 per window are reported as "insufficient data" (§3.4). If any query-window returns 0 items, that is recorded as a finding (a quiet window), not an error, unless ≥ 3 query-windows return 0 (§1.8).
- **Channel concentration check:** report how many distinct channels the sample covers and the largest single channel's share per window. If one channel is > 20% of a window, the dashboard must say so — a one-channel window is a channel study, not a topic study.
- **Polite use:** ≥ 2 s between calls; one retry after 30 s on HTTP 5xx / timeout only; no retry on 403 `quotaExceeded` (§1.8).
- **Raw size guard:** one raw file per query-window (`data/raw/search_<query-slug>_<window>.json`, verbatim API responses) plus `data/raw/videos_details.json` and `data/raw/channels_details.json`. Each search file is ≤ ~50 items × ~1 KB ≈ 50 KB; the raw total is ≤ ~1 MB — inside the 5 MB/day rule and the 1 MB/file guideline.

### 2.3 Sentiment angle — bounded, secondary (fixed scope)

The trend call itself does not need comment text. The sentiment angle is a **mood snapshot of the trending videos**, not a second trend series:

- **Exactly 5 videos:** the top video by `views_per_day` within each topic in Window A (age ≥ 7 days, comments enabled), one per topic. If a topic has no eligible video in Window A (e.g. `bi_viz` / `general` may have n < 10), that topic contributes no sentiment video and the count is recorded — do not substitute a video from another topic or window.
- **Exactly 5 `comment-threads` call sequences** (one per video), `maxResults=100`, `order=time` (newest first), `textFormat=plainText`, `part=snippet` (top-level comments only — **no replies, no `comments.list` calls**), **one page only** per video (no `--page-token` follow-up).
- **Scoring:** Day 5's lexicon scorer, verbatim rules (Day 5 brief §3.1 — word-polarity sum, negation window 3, intensifier ×1.5, normaliser `s / sqrt(s² + 15)`, thresholds ±0.05, small emoji map). The coder **copies** Day 5's `src/sentiment.py` scoring functions into this day's own `src/sentiment.py` (same file, same rules — Victor's own code, copied within his repo, not re-derived and not re-tuned). Day 5's theme lists are **not** reused — themes are Day 5's scope. Non-English handling reuses Day 5's §3.4 heuristic (non-Latin > 20% of letters → excluded from scoring, counted).
- **Filter (in this order, each step counted):** (1) drop threads whose top-level comment's `authorChannelId` equals the video's channel ID (channel-owner comments, incl. pinned promos — not audience sentiment); (2) drop empty/whitespace-only text; (3) drop non-Latin comments per the heuristic.
- **Expected rows:** 5 videos × up to 100 threads = **≤ 500 fetched threads** → after filtering **~300–450 analysed comments**. If the final analysed count lands below **150**, the sentiment panel is labelled thin-sample in the dashboard and the README.
- **Reporting:** per-video mean compound score, positive/negative share, and n analysed — shown next to that video's velocity numbers as "audience mood on the fastest-rising video in this topic". **No claim is made that this mood represents the topic** — it represents five videos, and the dashboard says so.

### 2.4 Why this design (and what was rejected)

- **Two 30-day windows × 5 queries with `order=date`** is the smallest design that yields a real time series: 8–9 weekly buckets (§3.2) plus a clean two-window momentum comparison, for 1,000 search units. The windows are equal length (30 days), so volume comparisons need no length correction.
- **Reusing the Day 4 frame as context (Layer A)** costs 0 units and gives the long-run topic shares, but it is never allowed into the momentum math: different snapshot date (2026-11-08 vs 2026-11-10), different selection method (relevance vs date), old-heavy (185/244 over a year old). Mixing the layers would manufacture a trend out of a selection-method change.
- **One page per query-window** caps search quota at 1,000 units and keeps the sample definition simple (newest 50 per query per window). The truncation flag (§1.6) is the honest record of what was not fetched.
- **Rejected — a single 60-day window with weekly bucketing from one search per query:** 5 searches × 50 results with `order=date` over 60 days would return only the newest 50 videos per query — i.e. almost entirely the last ~2 weeks — leaving the earlier weeks empty. The two-window design forces coverage of both halves.
- **Rejected — four weekly windows (20 searches, 2,000 units):** more granular, but doubles the search quota for buckets that the two-window design already yields by bucketing `publishedAt` after fetching. Weekly buckets are computed from dates, not from separate API calls.
- **Rejected — `order=relevance` for the fresh searches:** destroys the publish-volume time series (relevance ranking is undocumented and mixes old popular videos into recent windows).
- **Rejected — full comment sentiment per topic:** fetching comments for every video in the sample would need ~300+ `commentThreads` calls and a new sample design; the 5-video mood snapshot (§2.3) is the bounded version that fits this day's quota and scope.
- **Rejected — playlist-based top-up (Day 4 §2.3):** not needed — if a query-window under-delivers, that is a finding (a quiet window), not a gap to fill from one channel's uploads.

---

## 3. Method — trend detection (fixed definitions the coder must not redefine)

All metrics are computed on the cleaned video frame (one row per video, Layer B only, unless a metric says otherwise). **Use medians, not means, for every views/engagement comparison** — view counts are heavily right-skewed and a single viral video would dominate any mean. Log10(viewCount) is used for charts.

### 3.1 Topic taxonomy (reuse Day 4 — verbatim, do not invent a new classifier)

**Assignment rule (Day 4 brief §3.2, copied exactly):** deterministic keyword match on lower-cased `title + tags + description`, first match wins in this priority order:

1. `python` — "python", "pandas", "numpy"
2. `sql` — "sql", "mysql", "postgres"
3. `ai_ml` — "machine learning", "artificial intelligence", " ai ", "llm", "chatgpt", "deep learning", "neural"
4. `bi_viz` — "power bi", "tableau", "excel", "dashboard", "visualization", "visualisation"
5. `career` — "career", "job", "salary", "interview", "roadmap"
6. `general` — "data analytics", "data analyst", "data science"
7. `other` — no keyword match

Record the keyword list in the code, not in prose. **No new topic is added and no keyword is changed.** Justification: the taxonomy is the portfolio's settled topic language (Days 4–5); changing it would break comparability with the Day 4 frame, and the fresh searches use the same five queries that produced that frame, so no new topic is expected to emerge. If `other` exceeds 30% of the fresh sample, the grouping is too narrow — **report it, do not silently re-tune the keywords after seeing results**. Expected small groups: `career`, `bi_viz` and `general` had only 10, 3 and 1 videos in the Day 4 frame and will likely stay small in Layer B — they are reported for completeness but will usually fall under the §3.4 "insufficient data" rule for momentum classification.

### 3.2 Time buckets (fixed)

- **Momentum windows:** Window B (prior, 2026-09-11 → 2026-10-11) vs Window A (recent, 2026-10-11 → 2026-11-10). Each is exactly 30 days; a video belongs to the window containing its `publishedAt`. The boundary instant `2026-10-11T00:00:00Z` belongs to Window A (`publishedAfter` is "at or after", §1.3).
- **Weekly buckets:** 7-day blocks anchored at the start of Window B — W1 2026-09-11→09-17, W2 09-18→09-24, W3 09-25→10-01, W4 10-02→10-08, W5 10-09→10-15, W6 10-16→10-22, W7 10-23→10-29, W8 10-30→11-05, W9 11-06→11-10 (5 days, **partial — flagged on every chart and excluded from week-over-week growth**). Week labels show the start date (e.g. "w/c 2026-10-30").
- **Smoothing:** a **2-week rolling mean** of weekly publish volume per topic (mean of the current and previous week's counts), drawn as a line over the weekly bars. It smooths single-week spikes; it is a display aid, never a classification input.
- **Small-n rule:** a topic-week cell with n < 5 is flagged **thin** on the chart and in the table; a topic-week with n = 0 is shown as 0 with a "no videos" note, never interpolated.

### 3.3 Core metrics (definitions fixed — the planner/coder must not redefine them)

| Metric | Formula | Notes |
|---|---|---|
| `days_since_publish` | `(fetch_date − publishedAt).days`, minimum 1 | Fetch date = 2026-11-10. A video published today scores 1 day, never 0 (no division by zero). |
| `views_per_day` | `view_count / days_since_publish` | Age-normalised velocity — the primary "how fast is this video accumulating views" measure. **Only computed for videos aged ≥ 7 days** (§3.5 guard); younger videos get `views_per_day = NaN` and are excluded from velocity medians (they still count in publish volume). |
| `engagement_rate` | `(like_count + comment_count) / view_count` | Requires both counts present; NaN otherwise. Typical range ~0.5–8% (Day 4 sanity check). |
| `like_rate` / `comment_rate` | `like_count / view_count` · `comment_count / view_count` | Components of engagement; `comment_rate` is the audience-response proxy in the briefing. |
| `views_per_subscriber` | `view_count / subscriber_count` | NaN where subscriber count is hidden. |
| `duration_seconds` | Parsed from `contentDetails.duration` (ISO 8601) | `PT12M34S` → 754. All durations must parse; zero/negative is a data error. Duration buckets (Day 4): Short ≤ 60 s · Short-form 61–300 s · Medium 301–900 s · Long 901–1800 s · Deep-dive > 1800 s. |
| `weekly_volume(topic, week)` | Count of videos in the topic published in the week | The primary time-series quantity. |
| `topic_share(topic, window)` | `weekly_volume` summed over the window / total videos in the window | In percentage points (pp) for momentum. |
| `volume_growth(topic)` | `(n_A − n_B) / n_B`, where `n_A`, `n_B` are the topic's video counts in Windows A and B | Undefined if `n_B = 0` — then report "no prior-window baseline" instead of a number. |
| `share_change(topic)` | `topic_share(topic, A) − topic_share(topic, B)`, in percentage points | The primary momentum quantity. |
| `median_views_per_day(topic, window)` | Median `views_per_day` over the topic's videos in the window with age ≥ 7 days | The velocity quantity. Always reported with n and with the median age of the videos in the window (§3.5). |
| `velocity_change(topic)` | `(median_views_per_day(A) − median_views_per_day(B)) / median_views_per_day(B)` | Supporting signal only — never the classification input (§3.4). Undefined if the Window B median is missing/zero. |
| `mean_compound` (sentiment) | Mean Day 5 `score_comment` compound over the analysed comments on one video | §2.3 only. Always with n and the positive/negative shares. |
| `sentiment_share` (per video) | Share of analysed comments per class (positive / neutral / negative) | §2.3 only. |

### 3.4 Trend classification — accelerating / fading / stable (fixed thresholds)

Computed **per topic, from Layer B only**, using volume momentum as the primary signal:

| Classification | Rule (all conditions must hold) |
|---|---|
| **Accelerating** | `share_change ≥ +3 pp` **AND** `volume_growth ≥ +20%` **AND** `n_A ≥ 10` **AND** `n_B ≥ 10` |
| **Fading** | `share_change ≤ −3 pp` **AND** `volume_growth ≤ −20%` **AND** `n_A ≥ 10` **AND** `n_B ≥ 10` |
| **Stable** | Any topic meeting the n ≥ 10 rule in both windows that is neither accelerating nor fading |
| **Insufficient data** | `n_A < 10` or `n_B < 10` in either window — no classification is made; the briefing says so plainly |
| **No prior baseline** | `n_B = 0` — reported as such, never as infinite growth |

**Velocity cross-check (mandatory, reported alongside every classification):** if the volume classification is Accelerating but `velocity_change < −30%`, or Fading but `velocity_change > +30%`, the briefing flags the topic **"mixed signal"** and states both numbers — the volume and velocity stories disagree, and neither is hidden. The classification itself does not change (volume is primary), but the flag is part of the deliverable.

**What the thresholds mean:** +3 pp of share plus +20% volume growth is large enough that it cannot be produced by one or two extra videos in a 30-day window at the expected sample size (~150 per window), while small enough to catch a real shift. The thresholds were set before the fetch runs and must **not** be re-tuned after seeing the results — if no topic meets them, the honest finding is "no topic accelerated or faded in this window", not a reason to lower the bar.

### 3.5 The age bias in velocity — stated, guarded, sensitivity-checked

`views_per_day` is systematically higher for young videos (a video's views accumulate fastest just after publication, then slow). Window A videos are 0–30 days old (median age ~15 days); Window B videos are 30–60 days old (median age ~45 days). **A raw Window A vs Window B `views_per_day` comparison therefore favours Window A by construction.** Three fixed mitigations, all mandatory:

1. **Minimum-age guard (7 days):** videos younger than 7 days are excluded from all velocity medians (their `views_per_day` is unstable — a 1-day-old video with 10,000 views scores 10,000/day). They still count in publish volume.
2. **Report median age alongside every velocity number:** every `median_views_per_day` cell in the dashboard, notebook and briefing carries its window's median `days_since_publish` and n, so the reader can see the age gap.
3. **Age-guard sensitivity check:** recompute `velocity_change` per topic with a **14-day guard** as well as the 7-day guard. If any topic's velocity direction flips between the two guards, the briefing reports both numbers and marks that topic's velocity call "sensitive to age guard". The volume classification is unaffected (it uses counts, not views).

**No causal claims.** A classification is reported as *"in this sample, videos on topic X published in the last 30 days outnumbered those in the prior 30 days by …"* — never "topic X is going viral" or "creators should switch to X". The briefing's recommendation format follows Day 4 (§4): recommendation + evidence numbers + sample basis + caveat, on every claim.

### 3.6 What "good" looks like — targets table

| Metric | Target |
|---|---|
| Final videos in `videos.csv` (Layer B) | **≥ 200** (expected ~280–380; < 200 = thin-sample caveat, §2.2) |
| Videos per window | **≥ 100** in each of Windows A and B (else the momentum comparison is thin — report it) |
| Topics classifiable | **≥ 2 topics** with n ≥ 10 in both windows (expected: python, ai_ml, sql; career/bi_viz/general likely "insufficient data") |
| Weekly coverage | **≥ 7 of 8 full weeks** (W1–W8) with ≥ 5 videos total (else flag thin weeks on the chart) |
| `other` topic share | **≤ 30%** of the fresh sample (if above, report — do not re-tune, §3.1) |
| Sentiment videos | **≥ 3 of 5** topics with an analysed comment set (else the sentiment panel is thin-sample, §2.3) |
| Sentiment comments analysed | **≥ 150** (expected ~300–450) |
| Charts | Exactly 4 PNGs (§4), drawn to scale, legible, source-noted |
| Limitations | §1.2 snapshot limitation + §3.5 age bias + §5.4 tensions stated in README, dashboard, notebook and briefing — **zero** presentation of a snapshot comparison as a historical trend |

If a target is missed, the correct response is to report the miss and diagnose it — **not** to re-tune the keyword lists, buckets, thresholds, or age guard after seeing the results. The windows, thresholds and guard are fixed in this brief before the fetch runs.

**Conventions the coder must not re-decide:** the 5 queries + 2 windows + `order=date` + `maxResults=50` + one page per query-window per §2.2; the Day 4 keyword topic rule per §3.1; weekly buckets per §3.2; the §3.3 formulas; the §3.4 thresholds; the 7-day age guard (with the 14-day sensitivity check) per §3.5; the 5-video sentiment snapshot per §2.3 with Day 5's scorer verbatim. If any of these is unworkable, send it back to the planner with the exact point — do not silently substitute a different convention.

---

## 4. Deliverable shape (for the planner — the roadmap's two artefacts, plus the portfolio pattern)

- **Trend detection dashboard** (roadmap): Streamlit app showing (a) weekly publish volume per topic with the 2-week rolling mean, (b) velocity comparison per topic per window (median `views_per_day` with median age and n), (c) the classification table (accelerating / fading / stable / insufficient data, with share change, volume growth, and the mixed-signal flag), (d) the sentiment mood panel for the 5 videos, (e) the snapshot-limitation and age-bias caveats on the front page. The dashboard header carries the sentence: *"Trends here compare two 30-day cohorts of recently published videos. The API gives a current snapshot of each video's statistics, not daily history — so these are cohort comparisons, not a record of views rising or falling over time."*
- **Weekly briefing** (roadmap): `outputs/weekly_briefing.md` — generated from the same computed table, not hand-written from memory: one paragraph per classified topic (what changed, the numbers, the sample basis, the caveat), the top accelerating and top fading topic called out first, the mixed-signal flags, and the sentiment mood lines. The briefing is dated to the fetch date (2026-11-10) and states the two windows it covers.
- **Portfolio pattern (Days 1–5):** `src/data_pipeline.py`, `src/trend.py` (pure trend math — no I/O, no network), `src/sentiment.py` (Day 5 scorer copied verbatim, §2.3), `src/make_charts.py` (exactly 4 PNGs), `src/app.py` (Streamlit dashboard), `notebooks/analysis.ipynb`, `tests/test_pipeline.py`, `data/raw/search_*.json` + `videos_details.json` + `channels_details.json` + `comments_<video_id>.json` (5 files), `data/processed/videos.csv` + `data/processed/comments.csv` + `data_source.json`, `outputs/insights_summary.md` + `outputs/weekly_briefing.md`, `README.md`, `data/README.md`, `requirements.txt` (pinned), `pyproject.toml`, `.gitignore` (must NOT exclude `data/`).
- **Charts (exactly 4, for the planner to place):** 01 weekly publish volume per topic (stacked bars + 2-week rolling mean, thin weeks flagged, partial W9 marked); 02 topic share and volume growth, Window A vs Window B (grouped bars + the ±3 pp / ±20% threshold lines); 03 median `views_per_day` per topic per window with median age annotated (velocity comparison, age bias visible); 04 sentiment mood — mean compound + positive/negative share for the 5 videos (with n).

---

## 5. Validation, fallback, licence, and open conflicts

### 5.1 Validation — how the trend calls are checked (two checks + one mandatory hand-validation)

There is no ground-truth "trending topic" dataset, so validation is a holdout check plus hand recomputation:

1. **Holdout backtest (the credibility core of this day).** Compute the §3.4 volume classification using **only weeks W1–W7** (train = W1–W7, test = W8). Predict the topic with the highest `topic_share` growth from the first half of the train period (W1–W3) to the second half (W5–W7); then check whether that topic is in the **top 2 by `topic_share` in W8**. Report hit or miss in the notebook, dashboard and briefing, with the numbers. A miss does not invalidate the classifications — it is reported as evidence about how stable the calls are over one week. **The holdout uses Layer B data only** (the Day 4 frame is relevance-sampled and cannot backtest a date-ordered sample).
2. **Age-guard sensitivity (§3.5):** recompute `velocity_change` with the 14-day guard; report any direction flip per topic.
3. **Tester hand-validation (mandatory):** the tester recomputes **one topic's full momentum numbers by hand from `videos.csv`** — `n_A`, `n_B`, `topic_share` in both windows, `share_change`, `volume_growth`, and `median_views_per_day` in both windows — and matches the processed CSV / dashboard to the last digit; recorded in `data/README.md` with the topic name and the hand-computed numbers. (Same convention as Days 1–5: one metric, verified by hand, recorded.)
4. **Sanity checks (pipeline must assert or report):** zero duplicate `videoId`s in the final frame; 100% duration parse, all > 0 s; no `publishedAt` in the future and none before 2005-04-23 (YouTube's launch); no `publishedAt` outside the two windows in Layer B; sample median `engagement_rate` roughly 0.5–8% (Day 4 sanity range — outside it means a definition or parsing error, stop and check); median `views_per_day` > 0, no infinite/NaN values among age-eligible videos.

### 5.2 Synthetic fallback (same conventions as Days 1–5, new parameters for trends)

Only if the live fetch fails **and** no cache exists (`data/raw/search_*.json` in this day folder). Deterministic, **seed 42**:

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

Output goes **only** to `data/raw/*_synthetic.json` — it must never overwrite the live cache. `data/processed/data_source.json` records `synthetic: true` + `seed: 42`. All downstream outputs are labelled SYNTHETIC. Synthetic data follows the same schema as live data (same columns, §3.3) so the pipeline, notebook, and dashboard run unchanged. Note: synthetic trends are uniform/constructed by design, so on synthetic data the accelerating/fading calls have no interpretation — state this in the README, notebook, and briefing if the synthetic path is used.

### 5.3 Cache reuse note

There is no prior Day 6 cache. A cache fallback is only valid if a Day 6 fetch has previously succeeded and written `data/raw/` files in the Day 6 folder. **Layer A (the Day 4 frame) is not a cache for Layer B** — it is a different snapshot (2026-11-08) selected by a different method (relevance), and it must never be relabelled as the fresh fetch. Do **not** reuse any other day's data as Layer B — the source design differs entirely.

### 5.4 Data provenance (Days 1–5 conventions, carried over)

- `data/README.md` (coder writes it) records: provider, endpoints used, the 5 queries + 2 windows, access date (2026-11-10), quota units used, row counts (candidates → unique → final, per window, with each filter's count), truncation flags per query-window, the Layer A / Layer B split and why, the licence/attribution note (§5.6) + the tensions stated honestly (§5.5), and the hand-validated metric (§5.1 item 3). `data/processed/data_source.json` records `source` (`"live"`, `"cache"` or `"synthetic"`), `generated_at_utc`, `synthetic` (bool), `seed` (`null` for live data, `42` for synthetic), plus `fetch_date` (`"2026-11-10"`), `snapshot_dates` (`{"day04_frame": "2026-11-08", "fresh_fetch": "2026-11-10"}`), `windows` (`{"prior": ["2026-09-11T00:00:00Z", "2026-10-11T00:00:00Z"], "recent": ["2026-10-11T00:00:00Z", "2026-11-10T00:00:00Z"]}`), `queries` (the 5 query strings), `max_results_per_query` (50), `order` (`"date"`), `per_query_window` (counts + `truncated` flags), `video_count`, `channel_count`, `quota_units_used` (best estimate), `api` (`"youtube-data-api-v3"`), `age_guard_days` (7), `overlap_with_day04_frame` (count), and `counts` (candidates, unique_after_dedupe, dropped_live_or_upcoming, dropped_no_view_count, final_videos, sentiment_videos, sentiment_comments_analysed).
- **Data-source field rule (Day 2 day-log lesson — mandatory):** an offline pipeline run (`--offline` / `--use-cache`) overwrites `data_source.json`'s `source` field to `"cache"`. Before publishing, the coder/optimizer must either **re-run the pipeline live** (restoring `"live"`) or **restore the field by hand with the true value and record the correction** in `data/README.md`. A published `data_source.json` that says `"cache"` when the data was in fact fetched live is a defect.
- **Data-commit rule (from Day 1):** small raw data IS committed — files under 1 MB each, under 5 MB per day folder — because the raw files are the provenance record. **`.gitignore` must NOT exclude `data/`.** Synthetic fallback output goes to `data/raw/*_synthetic.json` and is git-ignored; it must never overwrite the live cache. `python3 src/data_pipeline.py --offline` / `--use-cache` runs from the committed cache with no network.
- **Key rule:** the API key comes only from the `custom.youtube` connector. No `.env` file, no key in code, no key in any committed file, no key in logs.

### 5.5 Open conflicts / gaps (for the planner — mandatory resolution order)

1. **Snapshot vs historical trend (resolve by design, not by redefining the metrics).** The API gives no historical daily statistics (§1.2), so this day's "trend" is a comparison of two publish-date cohorts, not a record of views over time. The design in §2/§3 is the resolution: volume momentum (genuinely a time series) is primary, velocity is a supporting cohort comparison with the age bias stated (§3.5), and the dashboard header carries the limitation sentence (§4). No output may present a cohort comparison as a historical trend.
2. **Quota cost discrepancy (same as Day 5, carried over).** Official docs page: 1 unit per `commentThreads.list` call; generated client-library reference: "snippet part has a quota cost of 2 units". Resolution order: (a) run the §2 design as written; (b) if `quotaExceeded` appears far earlier than the ~1,018-unit budget predicts, stop, check the Google Cloud Console quota page for the bucket breakdown, and report the actual bucket limits — do not retry or add calls. (Same June 2026 quota-bucket caveat as Days 4–5, §1.7.)
3. **Derived-metrics tension (same as Day 4, carried over).** The YouTube Developer Policies say API clients must only offer metrics available via YouTube's API services and must not offer independently calculated or derived metrics that replace API data — but the same policies also state that metrics displayed must be calculated exclusively from YouTube API data through basic arithmetic. Our KPIs (`views_per_day`, `engagement_rate`, `topic_share`, `volume_growth`) are basic arithmetic on returned statistics for an offline educational analysis, not a service offering metrics to users — that is the defensible reading. No legal certainty is claimed. The planner carries this into `data/README.md` as an honestly stated tension, and the dashboard shows the underlying counts next to every derived rate so nothing replaces the API data.
4. **Committed raw JSON vs data-storage rules (same as Days 4–5).** Developer Policies §III.E.4 allow storing video statistics for more than 30 days but require verifying every 30 days that the data is still authorised / the video still exists. Our raw JSONs are a dated one-time snapshot (2026-11-10) committed as the provenance record, following the Days 1–5 convention; they are not re-served by a live service. No YouTube page found states explicitly whether committing verbatim raw API JSON to a public GitHub repo counts as redistribution, so this is unresolved and no legal certainty is claimed. State the snapshot date and the tension in `data/README.md`.
5. **Comment text is user-generated content (same as Day 5, §5.4 item 2, smaller scope).** The 5 raw comment JSONs contain public comments verbatim, including display names. They are a dated one-time snapshot (2026-11-10) committed as the provenance record; they are not re-served by a live service and the dashboard shows only aggregates (mean compound, shares, n) plus at most 3 short excerpts per video (≤ 120 chars, no author names). No legal certainty is claimed.
6. **`pageInfo.totalResults` is unreliable** (§1.4) — never report it; count rows from the fetched items.
7. **Search truncation (§1.6, §2.2).** A query-window returning exactly 50 items may have cut off older videos in that window. The `truncated` flag is the record; the weekly volume for a truncated query-window is a lower bound, stated as such.
8. **Age bias in velocity (§3.5).** Window A videos are younger than Window B videos by construction, so velocity comparisons favour Window A. The 7-day guard, median-age reporting and 14-day sensitivity check are the mitigations; the volume classification does not depend on velocity.
9. **Sentiment is a model output, not ground truth** (Day 5 §3.1/§3.5, carried over). The lexicon is a weak baseline by design; the 5-video mood snapshot is descriptive of five videos only. No claim in any output may present a sentiment share as "how viewers feel" without the "as classified by our rule-based model" qualifier, and no sentiment number may be used in a trend classification.
10. **Dependency:** none new (§3 — stdlib + the Day 1–5 stack: pandas, NumPy, matplotlib, Plotly, Streamlit). If the planner adds one, it must be pinned and justified in the plan.

### 5.6 Licence / attribution

- Data is public YouTube video metadata and comment text fetched under the **YouTube API Services Terms of Service and Developer Policies** (checked 2026-11-10). Attribution is required: include on the dashboard and in the repo README, legible: **"Data from the YouTube Data API v3"** with a link to YouTube's Terms of Service (`https://www.youtube.com/t/terms`), per the Developer Policies requirement that API clients display a link to YouTube's Terms of Service.
- Do not redistribute raw bulk data or re-host the API. Cache the fetched responses locally for the project only (§5.4, §5.5 items 4–5).
- Only public metadata is used — no user data beyond public comment text/display names, no private data. The API key has no OAuth scopes.
- Code in this repo is MIT (see `LICENSE`); YouTube data is under separate YouTube terms, not MIT.
- **No copying code or tutorials from the web.** All code is Victor's own original work, written from this brief and the plan. The sentiment scorer is copied from Day 5 within Victor's own repo (§2.3); the normaliser shape and ±0.05 thresholds are standard published VADER conventions, documented as such, not copied code.

---

## Handoff (researcher → planner)

**What was produced:** exactly one file — `day-06-viral-content-trend-explorer/research_brief.md` (this file) — plus a small, scoped extension to the shared YouTube helper (`~/workspace/custom-connectors/custom.youtube/bin/youtube.py`: three new optional arguments on the `search` subcommand, `--published-after` / `--published-before` / `--page-token`, passed through only when given; usage text updated; no other command touched). Two verification probes were run; no live dataset was fetched; no other file was written.

**Verified numbers:**
- Probe 1 (2026-11-10): `search --query "data analytics" --max-results 2 --order date --published-after 2026-10-11T00:00:00Z --published-before 2026-11-10T00:00:00Z` → exit 0, ~1.2 s, `youtube#searchListResponse`, 2 items, both published 2026-11-09 (inside the window), `nextPageToken: "CAIQAA"` present, `pageInfo.totalResults: 455684` (capped estimate — never a finding). Cost **100 units**.
- Probe 2: same call with `--page-token CAIQAA` → exit 0, ~0.6 s, 2 different videos (`fIv3G9sZJTU` 2026-11-09T22:09:31Z, `DAwERBXKaRI` 2026-11-09T21:27:29Z), still inside the window, still reverse-chronological, `nextPageToken: "CAQQAA"` present. Search pagination works. Cost **100 units**.
- Probe total: **200 units**.
- Docs verified: official `search.list` reference lists `publishedAfter` / `publishedBefore` (RFC 3339) and `order=date`; the generated client-library reference confirms the same parameter set.
- Quota budget for the build: 10 searches (1,000) + ≤ 10 videos calls (≤ 10) + ≤ 3 channels calls (≤ 3) + 5 comment-threads calls (5) = **≤ 1,018 units (~10% of the 10,000/day quota)**; day total including probes ≤ **1,218 units (~12%)**.
- Expected rows: 500 candidates → **~300–400 unique → ~280–380 final videos** (≈ 140–190 per window); sentiment ≤ 500 threads → **~300–450 analysed comments** on 5 videos (coder verifies actuals).
- Day 4 frame (Layer A, reused at 0 units): 244 videos, topics python 123 / ai_ml 68 / sql 39 / career 10 / bi_viz 3 / general 1, publish range 2017-05-19 → 2026-11-07; only 18 videos in the last 90 days, 185 over a year old — the reason Layer B exists.
- Endpoints: `/search` (100 units, `order=date`, `publishedAfter`/`publishedBefore` RFC 3339, `pageToken`), `/videos`, `/channels`, `/commentThreads` (1 unit each); counts arrive as strings; duration is ISO 8601; **no historical daily statistics exist** — trend is built from publish-date cohorts + two time-bounded search snapshots.

**Key decisions:**
- Data design (hybrid, two layers): Layer A = Day 4 frame reused as long-run context only (0 units, never in the momentum math); Layer B = fresh time-bounded searches, 5 Day-4 queries × 2 consecutive 30-day windows (prior 2026-09-11 → 2026-10-11, recent 2026-10-11 → 2026-11-10), `order=date`, `maxResults=50`, one page per query-window, truncation flagged not silently paged.
- Snapshot limitation stated up front (§1.2): no historical daily views exist; "trend" = publish-volume momentum (primary, genuinely a time series) + velocity cohort comparison (supporting, with the age bias stated).
- Topics: Day 4 taxonomy + keyword assignment rule reused verbatim (§3.1); no new topic, no re-tuning; `other` > 30% is reported, not fixed silently.
- Trend method (fixed, §3): weekly 7-day buckets anchored 2026-09-11 (W1–W8 full, W9 partial and flagged), 2-week rolling mean for display; momentum = `share_change` + `volume_growth` between the two 30-day windows; accelerating = share ≥ +3 pp AND growth ≥ +20% AND n ≥ 10 both windows; fading = mirror image; else stable / insufficient data; velocity (`median views_per_day`, age ≥ 7 days) is a cross-check with a ±30% "mixed signal" flag, never the classification input; age bias handled by the 7-day guard + median-age reporting + 14-day sensitivity check.
- Sentiment angle (§2.3): bounded mood snapshot — top video by `views_per_day` per topic in Window A (5 videos, 1 page × 100 threads each), Day 5's lexicon scorer copied verbatim, themes not reused; sentiment never enters a trend classification.
- Validation (§5.1): holdout backtest (train W1–W7, predict top-share topic, check top-2 in W8) + 14-day age-guard sensitivity + mandatory tester hand-validation of one topic's full momentum numbers from the CSV.
- Synthetic fallback: seed 42, n=300, Day 4 topic proportions, built-in python-rising / sql-falling trend by construction, `data/raw/*_synthetic.json` only.
- Licence tensions recorded honestly: snapshot-vs-historical limitation, quota-cost documentation conflict (1 vs 2 units), derived-metrics tension, 30-day storage rule, comment text as user-generated content — none claimed as legally certain.

**Known gaps:** no historical daily statistics (the defining limitation — handled by the cohort design, not worked around); search truncation at 50/page is possible and only flagged, not fetched past; `career` / `bi_viz` / `general` will likely be "insufficient data" for momentum (n < 10 per window expected); `pageInfo.totalResults` unreliable; velocity comparisons carry an age bias even after the guard (mitigated, not eliminated); the holdout backtest is a one-week check, not a proof of stability; June 2026 quota-bucket split means the coder's actual fetch is the ground truth on quota.

**Planner's first step:** take this brief as the source of truth for data, sample design, trend method, sentiment scope, and validation targets, and write `plan.md` — starting with the exact file tree (including the per-query-window raw JSONs, `videos.csv`, `comments.csv`, the 4 charts, and `outputs/weekly_briefing.md`) and the per-file responsibilities for the coder.
