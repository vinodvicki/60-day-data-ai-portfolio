# Research Brief — Day 4: YouTube Video Performance Analyzer

**Project:** Day 4 of the 60-day Data + AI portfolio
**Roadmap entry (exact):** "DAY 04 | YouTube Video Performance Analyzer — Problem / analysis: Explore video topics, duration, publishing time, views, and engagement to find patterns linked with stronger performance. GitHub deliverable: Creator KPI dashboard with content recommendations." Section context (Days 4–6, Social Media & Digital Marketing): Core skills: API integration, NLP, sentiment analysis, text visualization. Suggested data: YouTube Data API; public, permissioned comment and metadata datasets.
**Date written:** 2026-11-08 (researcher role, role 1 of 6)
**Status:** Research only — one lean verification probe was run (see §1.3). No live dataset was fetched. Fetching is the coder's job.

---

## 1. Verified source, endpoints, and parameters

### 1.1 Source

**YouTube Data API v3** — base URL `https://youtube.googleapis.com/youtube/v3` — via the `custom.youtube` connector (`~/workspace/custom-connectors/custom.youtube/`, helper `bin/youtube.py`). Read-only API-key auth: the key belongs to Victor's Google Cloud project `60-day-data-ai-portfolio` (project ID `day-data-ai-portfolio`), restricted to YouTube Data API v3 only, free tier, no payment method. **The key is held by the connector and is never put in any file, env var, log, command argument, or the repo.** The helper sends it as the `key` query parameter through the connector's surrogate exchange; redirects are refused by the helper.

This is a NEW data source for the portfolio (Days 1–3 used CoinGecko). Nothing from Days 1–3 carries over except the workflow conventions (provenance, synthetic fallback, `.gitignore` rule — see §5).

### 1.2 Endpoints (verified from the connector doc + helper source, `bin/youtube.py`)

The helper exposes exactly four commands. Parameters below are what the helper actually sends — copy them, do not re-derive them.

| Command | API endpoint | Parameters sent by the helper | Cost |
|---|---|---|---|
| `search --query "..." --max-results N` | `GET /search` | `part=snippet`, `q=<query>`, `type=video`, `maxResults=N`, `order=relevance` (default; helper accepts `--order` but the plan uses the default) | **100 units** |
| `videos --ids ID[,ID...]` | `GET /videos` | `part=snippet,statistics,contentDetails`, `id=<comma-separated, up to 50>` | **1 unit** |
| `channels --ids ID[,ID...]` | `GET /channels` | `part=snippet,statistics`, `id=<comma-separated, up to 50>` | **1 unit** |
| `playlist-items --playlist-id PL --max-results N` | `GET /playlistItems` | `part=snippet,contentDetails`, `playlistId=<id>`, `maxResults=N` | **1 unit** |

Full invocations:

```text
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py search --query "data analytics" --max-results 50
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py videos --ids VIDEO_ID[,VIDEO_ID...]
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py channels --ids CHANNEL_ID[,CHANNEL_ID...]
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py playlist-items --playlist-id PL_ID --max-results 10
```

### 1.3 Verification probe (the one lean probe — run 2026-11-08, exit code 0)

```text
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py search --query "data analytics" --max-results 2
```

- **Result:** HTTP-equivalent success (exit 0, ~1.1 s). Response `kind: "youtube#searchListResponse"`, `regionCode: "US"`, `pageInfo: {totalResults: 1000000, resultsPerPage: 2}`, `nextPageToken: "CAIQAA"` present (but the helper cannot pass a page token — see §1.5).
- **Items returned (2):**
  - `ejKxJOnnAlI` — "Most People Learning Data Analytics Are Wasting Their Time (Here's Why)", channel "Esther Chinenye Anagu" (`UCyYQbC8QsuhfpU5ewU8AF6g`), published `2026-01-27T07:00:29Z`.
  - `yZvFH7B6gKI` — "What Is Data Analytics? - An Introduction (Full Guide)", channel "CareerFoundry" (`UCzAF54cHk1ZO82af-8E3qOQ`), published `2021-03-25T13:13:45Z`.
- **Response shape (search items):** each item carries `id.videoId`, `snippet.publishedAt`, `snippet.channelId`, `snippet.title`, `snippet.description`, `snippet.thumbnails` (default/medium/high/standard/maxres URLs), `snippet.channelTitle`, `snippet.liveBroadcastContent` (`"none"` for ordinary videos), `snippet.publishTime`.
- **Quota cost of the probe: 100 units.** No further search calls were made — the coder does the live fetch.
- **Note on `totalResults: 1000000`:** this is the API's capped estimate, not a real count of matching videos. Never report it as a finding.

### 1.4 Response fields the coder will use

**`search` → `snippet` (per video):** `videoId`, `title`, `channelId`, `channelTitle`, `publishedAt` (ISO 8601 UTC, e.g. `2026-01-27T07:00:29Z`), `description`, `liveBroadcastContent`. Search returns **no statistics** — views/likes/comments require the `videos` call. Filter out any item with `liveBroadcastContent != "none"` (live/upcoming streams have no comparable lifetime stats).

**`videos` → `snippet`:** `title`, `channelId`, `channelTitle`, `publishedAt`, `description`, `tags` (array of strings; may be absent), `categoryId` (string), `defaultLanguage` (may be absent), `liveBroadcastContent`.
**`videos` → `statistics`:** `viewCount`, `likeCount`, `commentCount` — **all arrive as strings**; cast to int. `likeCount` and/or `commentCount` may be **absent** (likes/comments disabled) — record as missing (NaN), never silently fill with 0. `viewCount` absent means the video is unusable — drop the row and count it.
**`videos` → `contentDetails`:** `duration` (ISO 8601, e.g. `PT12M34S`, `PT1H2M3S`, `PT45S` — parse to seconds; Shorts are `PT60S` or less), `definition` (`hd`/`sd`), `dimension` (`2d`/`3d`), `licensedContent` (bool).

**`channels` → `snippet`:** `title`, `publishedAt` (channel creation date).
**`channels` → `statistics`:** `subscriberCount`, `viewCount`, `videoCount` — strings; `subscriberCount` is **hidden for some channels** (absent) — record as missing, never 0. `hiddenSubscriberCount` (bool) tells you which.

**`playlistItems` → `contentDetails.videoId`, `snippet.publishedAt`, `snippet.title`, `snippet.channelId`.** Newest first by default. Used only as the §2.3 fallback.

**Category IDs** (record raw; map only the IDs actually observed, unknown → `other (<id>)`): 1 Film & Animation, 2 Autos & Vehicles, 10 Music, 15 Pets & Animals, 17 Sports, 19 Travel & Events, 20 Gaming, 22 People & Blogs, 23 Comedy, 24 Entertainment, 25 News & Politics, 26 Howto & Style, 27 Education, 28 Science & Technology, 29 Nonprofits & Activism.

### 1.5 Hard limits of the helper (design constraints, not bugs to fix in Day 4)

- **No `pageToken` support.** Search and playlist-items return the first page only. `maxResults` caps at 50 per search call (API limit). There is no way to page to results 51+ with this helper — the sample design in §2 works within that.
- **Search is capped at 500 results per query by the API** (connector doc) — irrelevant here, since the helper only ever sees the first 50.
- **No date bounding.** The helper sends no `publishedAfter` / `publishedBefore`, so the sample cannot be restricted to a date window. The sample is a relevance-ranked snapshot as of the fetch date (2026-11-08), not a time-bounded cohort. State this in the README.
- **Read-only, public data only.** No uploads, comments, or private data (API key, no OAuth scopes).
- **Timeout 30 s per request** (helper). Redirects refused.

### 1.6 Quota and rate limits (verified)

- **Daily quota: 10,000 units/day, free tier, resets at midnight Pacific Time.** Search = 100 units; videos/channels/playlist-items = 1 unit each (connector doc + Google's published quota costs).
- **Polite-use rule for the coder:** ≥ 2 s between calls; one retry after 30 s on HTTP 5xx only; **no retry on 403 `quotaExceeded`** — stop and fall back (§5). Never hammer the API.
- **Quota budget for the planned build (§2):** 5 searches × 100 = 500 units + ~5 videos calls × 1 = 5 + ~3 channels calls × 1 = 3 → **≈ 508 units, ~5% of the daily quota.** Including this brief's 100-unit probe, the day's total is ≈ 608 units — still ~6% of quota. There is ample headroom for one re-run if a call fails; there is no headroom for exploratory extra searches, so the coder runs exactly the §2 design.
- **June 2026 quota change (open item, see §5.4):** Google split the daily quota into separate buckets from 2026-06-01. The 10,000-unit framing above is the connector doc's figure and the probe succeeded within it, but the coder's actual fetch is the ground truth — if a `quotaExceeded` appears far earlier than the budget predicts, stop and check the Google Cloud Console quota page for the bucket breakdown instead of retrying.

### 1.7 Error handling

| Error | Meaning | Coder action |
|---|---|---|
| `400 keyInvalid` | Stored key wrong or project misconfigured | Stop. Do not retry. Report as blocked; key is the connector's business, never to be pasted or hard-coded anywhere. |
| `403 quotaExceeded` | Daily quota hit | Stop immediately. No retry. Fall back to cache, then synthetic (§5). |
| `403 accessNotConfigured` | YouTube Data API v3 not enabled on the project | Stop. Report as blocked (it was enabled 2026-11-07 and the probe succeeded, so this is not expected). |
| `403` other (e.g. `forbidden`) | Request rejected for another reason | Check the request first (IDs well-formed, ≤ 50 per call); one careful retry only if the request was malformed. |
| HTTP 5xx / timeout | Transient server/network failure | One retry after 30 s, then fall back (§5). |
| Empty `items` on a `videos` call | IDs invalid, private, or deleted | Drop those IDs, count them, continue — this is not an error. |

The helper exits non-zero with `HTTP {code} from {path}: {body[:500]}` — the pipeline must catch that, log the code/reason, and follow the table above. **Never log the API key** (the helper never prints it; keep it that way).

---

## 2. Sample strategy (what the coder fetches — bounded, reproducible)

### 2.1 Recommended design (primary)

**Five search queries, one page each, then batched detail calls. No pagination, no extra searches.**

| # | Query | `max-results` | Why this topic |
|---|---|---|---|
| 1 | `data analytics` | 50 | Core topic — the portfolio's own field |
| 2 | `machine learning tutorial` | 50 | AI/ML tutorial demand |
| 3 | `Python data analysis` | 50 | Tool-specific (Python) demand |
| 4 | `artificial intelligence explained` | 50 | AI explainer demand |
| 5 | `SQL tutorial` | 50 | Tool-specific (SQL) demand |

- **Order:** `relevance` (helper default — do not pass `--order`). This is a deliberate trade-off, stated plainly: relevance ranking gives a mix of popular and recent videos, but it is **not a random sample** of YouTube. All findings are descriptive of *this sampled set*, not estimates about all of YouTube. Do **not** use `order=viewCount` — it would return only the most-viewed videos and destroy the variance the analysis needs (you cannot find what links to stronger performance if every video in the sample is already a top performer).
- **Deduplicate** by `videoId` across the five queries (overlap is expected — e.g. a Python tutorial can match queries 1, 3 and 5). Keep the first occurrence; record how many duplicates were dropped.
- **Filter:** drop `liveBroadcastContent != "none"`; drop rows with no `viewCount` after the `videos` call.
- **Detail fetch:** collect all surviving IDs and fetch in **one batched `videos` call per ≤ 50 IDs** (expect 4–5 calls). Then **one batched `channels` call per ≤ 50 distinct `channelId`s** (expect 2–3 calls) for subscriber counts.
- **Expected row counts (coder must verify the actuals and report them; do not assume these):** 5 × 50 = **250 candidates** → after dedupe **~200–240 unique videos** → after filtering/missing statistics **~180–230 rows** in the final video frame. If the final count lands below 150, the coder reports it as a sample-size caveat in the README; the analysis still runs, but the recommendations are labelled thin-sample.
- **Channel concentration check:** report how many distinct channels the sample covers and the largest single channel's share. If one channel is > 20% of the sample, the dashboard must say so — a one-channel sample is a channel study, not a topic study.

### 2.2 Why this design (and what was rejected)

- **Five queries × first page** is the largest reproducible sample the helper allows without pagination (5 × 50 = 250). Each query is a distinct data/AI-adjacent topic, so topic comparison (§3) has real groups to compare instead of one homogeneous pile.
- **Batched `videos` calls (50 IDs for 1 unit)** are the quota-cheap step — the entire detail fetch costs ~5 units. The expensive step is search (100 units each), which is why the design is fixed at exactly 5 searches.
- **Rejected — channel-uploads playlists as the primary sample:** pulling named creators' uploads playlists would need channel IDs plus uploads-playlist IDs, costs extra calls, is capped at the first page anyway, and hand-picking creators injects selection bias (famous creators only). See §2.3 for its limited fallback role.
- **Rejected — more queries / bigger sample:** each extra search costs 100 units and adds mostly duplicate IDs across overlapping topics. Five queries is the sweet spot between topic coverage and quota.

### 2.3 Fallback if a query under-delivers

If any query returns < 25 usable videos after filtering, the coder may add **one** playlist-based top-up, and only then:

1. Take the most-subscribed channel already present in that query's results (from the `channels` call).
2. Its uploads playlist ID is `UU` + the channel ID minus its leading `UC` (the standard YouTube convention — e.g. channel `UCxxxx…` → playlist `UUxxxx…`). **The coder must verify this convention works with one `playlist-items --max-results 10` call before relying on it**; if it fails, abandon this route, do not debug it further.
3. Cap the top-up at 25 videos from that playlist's first page, dedupe against the existing sample, and record the top-up separately in `data_source.json` (`top_up` field) and `data/README.md`.

No other top-up route is authorised. Do not invent queries, do not re-run a failed search hoping for different results.

---

## 3. Metrics / KPIs to compute

All metrics are computed on the cleaned video frame (one row per video). Counts are integers; rates are decimals (present as % in the dashboard). **Use medians, not means, for every views/engagement comparison** — view counts are heavily right-skewed and a single viral video would dominate any mean. Log10(viewCount) is used for charts.

### 3.1 Core KPIs (definitions fixed — the planner/coder must not redefine them)

| Metric | Formula | Notes |
|---|---|---|
| `view_count` | `statistics.viewCount` (int) | Lifetime views at fetch time. |
| `like_count` | `statistics.likeCount` (int, NaN if absent) | Absent = disabled, not zero. |
| `comment_count` | `statistics.commentCount` (int, NaN if absent) | Absent = disabled, not zero. |
| `days_since_publish` | `(fetch_date − publishedAt).days`, minimum 1 | Fetch date = 2026-11-08. A video published today scores 1 day, never 0 (no division by zero). |
| `views_per_day` | `view_count / days_since_publish` | Age-normalised performance — the primary "how strong is this video" measure. A 2021 video with 2M views and a 2026 video with 200K views are not comparable on raw views. |
| `engagement_rate` | `(like_count + comment_count) / view_count` | Primary engagement KPI. Requires both counts present; NaN otherwise. Typical range ~0.5–8% — see §4 sanity checks. |
| `like_rate` | `like_count / view_count` | Component of engagement. |
| `comment_rate` | `comment_count / view_count` | Component of engagement; typically ~0.05–0.5% of views. |
| `views_per_subscriber` | `view_count / subscriber_count` | Reach relative to channel size. NaN where subscriber count is hidden. A small channel with high views/subscriber is outperforming its base. |
| `duration_seconds` | Parsed from `contentDetails.duration` (ISO 8601) | `PT12M34S` → 754. All durations must parse; zero/negative is a data error, not a short video. |
| `publish_hour_utc` | Hour of `publishedAt` (0–23, UTC) | Plus a US Pacific display hour (UTC−8 in November, PST). UTC is canonical; Pacific is display only. |
| `publish_dow` | Day of week of `publishedAt` (Mon–Sun) | |

### 3.2 Groupings for pattern-finding

| Grouping | Buckets | Rule |
|---|---|---|
| **Duration** | Short `≤ 60 s` (Shorts-length) · Short-form `61–300 s` · Medium `301–900 s` · Long `901–1800 s` · Deep-dive `> 1800 s` | Fixed boundaries, set before seeing the data. Report median `views_per_day` and `engagement_rate` per bucket. Do not drop Shorts — bucket them and report their share of the sample. |
| **Topic (subject)** | `python` · `sql` · `ai_ml` · `bi_viz` · `career` · `general` · `other` | Deterministic keyword match on lower-cased `title + tags + description`, first match wins in this priority order: `python` ("python", "pandas", "numpy") → `sql` ("sql", "mysql", "postgres") → `ai_ml` ("machine learning", "artificial intelligence", " ai ", "llm", "chatgpt", "deep learning", "neural") → `bi_viz` ("power bi", "tableau", "excel", "dashboard", "visualization", "visualisation") → `career` ("career", "job", "salary", "interview", "roadmap") → `general` ("data analytics", "data analyst", "data science") → `other`. Record the keyword list in the code, not in prose. If `other` exceeds 30% of the sample, the grouping is too narrow — report it, do not silently re-tune the keywords after seeing results. |
| **Format** | `tutorial` · `explainer` · `other` | `tutorial` if title/tags contain "tutorial", "how to", "learn", "course", "beginner", "step by step"; `explainer` if they contain "explained", "what is", "introduction", "guide", "why"; else `other`. A second axis, independent of subject. |
| **Publish time** | Hour (0–23 UTC) and day-of-week | Report median `views_per_day` by hour and by weekday. **Confound, stated up front:** creators publish for their own audience's timezone, which the API does not reveal — any hour pattern is descriptive of this sample, not a "best time to post" prescription. |
| **Channel size** | By `subscriber_count` terciles (small / mid / large, cut at the sample's own 33rd/66th percentiles) | Tests whether engagement patterns differ by channel size; also feeds `views_per_subscriber`. |
| **Category** | `categoryId` (raw value, mapped per §1.4) | Reported as a breakdown only; no hypothesis attached. |

### 3.3 "Stronger performance" — the comparison that drives the recommendations

- **High performers = top quartile of `views_per_day`** (within the whole sample). Compare their median `engagement_rate`, duration-bucket mix, topic mix, and publish-hour distribution against the remaining 75%. Report the numbers side by side; the recommendations (§4) are drawn only from differences that are visible in those medians, not from single videos.
- **No causal claims.** A pattern (e.g. "medium videos have higher median views/day") is reported as *"in this sample, medium-length videos had higher median views per day"* — never "medium videos get more views". Correlation in a relevance-ranked, cross-sectional sample cannot support a causal recommendation, and the dashboard must not imply otherwise.
- **No sentiment analysis in Day 4.** The roadmap lists NLP/sentiment as section skills, but the Day 4 deliverable is a Creator KPI dashboard with content recommendations, and comment *text* is not fetched by any helper command (there is no comments endpoint in `youtube.py`). Sentiment is **OUT of scope** unless the planner explicitly adds a comments fetch — which would need a new helper capability, a new quota budget, and a defined method. The defensible topic approach for Day 4 is the deterministic keyword grouping in §3.2 (transparent, reproducible, no model, no labels needed). If the planner wants NLP, the honest Day 4 version is the keyword grouping itself — it *is* a simple text-classification step, and it should be named as such.

### 3.4 Suggested dependency

No new runtime dependency. Pandas, NumPy, Plotly, Streamlit already in the Day 1–3 stack. Duration parsing is a few lines of stdlib (`re` on the ISO 8601 string) — do not add `isodate` or any other package for it.

---

## 4. Validation plan (no ground truth exists for "good" performance)

There is no labelled "good video" dataset, so validation is sanity checks + one manual recomputation, not precision/recall:

| Check | Expectation | If it fails |
|---|---|---|
| Row counts | 250 candidates → ~200–240 unique → ~180–230 final (§2.1) | Report the actuals; < 150 final rows = thin-sample caveat in README |
| Dedup | Zero duplicate `videoId`s in the final frame | Dedup logic is wrong — fix before proceeding |
| Duration parse | 100% parse, all > 0 s | A parse failure is a code bug, not a data quirk |
| Dates | No `publishedAt` in the future; none before 2005-04-23 (YouTube's launch) | Flag the row; do not silently drop it without recording why |
| Missing stats | Report % of rows missing `likeCount` / `commentCount` / `subscriberCount` | If > 25% missing likes, `engagement_rate` medians are thin — say so |
| Engagement sanity | Sample median `engagement_rate` roughly 0.5–8% | Median > 15% or < 0.1% means a definition or parsing error — stop and check before building charts |
| Views sanity | Median `views_per_day` > 0; no infinite/NaN values | Division or date bug — fix before proceeding |
| Manual validation (mandatory) | Recompute **one** video's `engagement_rate` and `views_per_day` by hand from the raw `videos` JSON and match the processed CSV to the last digit | Record the video ID, the hand-computed numbers, and the match in `data/README.md` (same convention as Days 1–3) |
| Top-quartile comparison | High performers' median `engagement_rate` and `views_per_day` reported vs the rest, with sample sizes | If the top quartile is dominated by one channel (> 50% of it), say so — the "pattern" may just be that channel |

### Recommendation format

Every recommendation in the dashboard / notebook / insights summary must be traceable to a number in the same output:

| Field | Meaning |
|---|---|
| `recommendation` | Plain-language advice, e.g. "Medium-length videos (5–15 min) had the highest median views per day in this sample." |
| `evidence` | The numbers behind it, e.g. "median 1,240 views/day (n=52) vs 610 for long videos (n=48)". |
| `sample_basis` | Which slice it comes from (topic, duration bucket, channel size) and its n. |
| `caveat` | Always present: "Descriptive pattern in a relevance-ranked sample of ~200 videos — not a causal finding." |

Rules: every claim in a recommendation must be a number in the processed CSV. No causal verbs ("will boost", "causes", "guarantees"). No advice about a specific creator or video by name beyond the aggregated evidence. The dashboard header carries the sentence: *"Performance patterns here describe this sampled set of public videos. They are descriptive, not causal, and are not a guarantee of future performance."*

---

## 5. Fallback parameters, licence, and open conflicts

### 5.1 Synthetic fallback (same conventions as Days 1–3, new parameters for YouTube)

Only if the live fetch fails **and** no cache exists (`data/raw/*_search.json` / `*_videos.json` in this day folder). Deterministic, **seed 42**:

| Field | Synthetic rule |
|---|---|
| `n` | **200 videos** across 20 synthetic channels ("Synthetic Creator 01" … "Synthetic Creator 20", 10 videos each) |
| `view_count` | Log-normal, median 50,000, σ_log 1.2, clipped to [100, 5,000,000] |
| `like_count` | `view_count × U(0.02, 0.06)` (rounded) |
| `comment_count` | `view_count × U(0.0005, 0.005)` (rounded) |
| `subscriber_count` | Log-normal, median 100,000, σ_log 1.0, clipped to [1,000, 10,000,000] |
| `duration_seconds` | Log-normal, median 600 s, σ_log 0.8, clipped to [60, 3600], rendered back to ISO 8601 |
| `published_at` | Uniform over the 365 days before 2026-11-08 |
| `title` / `tags` | Assembled from fixed template lists per §3.2 topic group (e.g. "Python Data Analysis Tutorial for Beginners"), so the keyword grouping classifies them |
| `category_id` | 27 (Education) or 28 (Science & Technology), alternating |

Output goes **only** to `data/raw/*_synthetic.json` — it must never overwrite the live cache. `data/processed/data_source.json` records `synthetic: true` + `seed: 42`. All downstream outputs are labelled SYNTHETIC. Synthetic data follows the same schema as live data (same columns, §3.1) so the pipeline, notebook, and dashboard run unchanged. Note: synthetic engagement rates are uniform by construction, so on synthetic data the topic/duration comparisons have no interpretation — state this in the README, notebook, and insights summary if the synthetic path is used.

### 5.2 Cache reuse note

There is no prior YouTube cache — Day 4 is the first YouTube day. A cache fallback is only valid if a Day 4 fetch has previously succeeded and written `data/raw/` files in the Day 4 folder. Do **not** reuse any other day's data — the source differs entirely.

### 5.3 Data provenance (Day 3 plan §3 conventions, carried over)

- `data/README.md` (coder writes it) records: provider, endpoints used, the 5 queries, access date (2026-11-08), quota units used, row counts (candidates → unique → final), and the licence/attribution note (§5.5). `data/processed/data_source.json` records `source` (`"live"`, `"cache"` or `"synthetic"`), `generated_at_utc`, `synthetic` (bool), `seed` (`null` for live data, `42` for synthetic), plus `queries` (the 5 query strings), `max_results_per_query` (50), `video_count`, `channel_count`, `quota_units_used` (best estimate), `api` (`"youtube-data-api-v3"`), and `top_up` (null, or the §2.3 details if used).
- **Data-source field rule (Day 2 day-log lesson — mandatory):** an offline pipeline run (`--offline` / `--use-cache`) overwrites `data_source.json`'s `source` field to `"cache"`. Before publishing, the coder/optimizer must either **re-run the pipeline live** (restoring `"live"`) or **restore the field by hand with the true value and record the correction** in `data/README.md`. A published `data_source.json` that says `"cache"` when the data was in fact fetched live is a defect.
- **Data-commit rule (from Day 1):** small raw data IS committed — files under 1 MB each, under 5 MB per day folder — because the raw files are the provenance record. **`.gitignore` must NOT exclude `data/`.** Synthetic fallback output goes to `data/raw/*_synthetic.json` and is git-ignored; it must never overwrite the live cache. `python3 src/data_pipeline.py --offline` / `--use-cache` runs from the committed cache with no network.
- **Key rule:** the API key comes only from the `custom.youtube` connector. No `.env` file, no key in code, no key in any committed file, no key in logs.

### 5.4 Open conflicts / gaps (for the planner — mandatory resolution order)

1. **June 2026 quota buckets (resolve first, at build time).** Google split the daily quota into separate buckets from 2026-06-01 (YouTube API Services Terms of Service revision history, checked 2026-11-08). The 10,000-unit budget in §1.6 is the connector doc's figure and the probe succeeded within it, so the build proceeds on that basis — but the coder's actual fetch is the ground truth. Resolution order: (a) run the §2 design as written; (b) if `quotaExceeded` appears far earlier than the ~508-unit budget predicts, stop, check the Google Cloud Console quota page for the bucket breakdown, and report the actual bucket limits — do not retry or add searches.
2. **Derived-metrics tension (record honestly, do not resolve by redefining the KPIs).** The YouTube Developer Policies (checked 2026-11-08) say API clients must only offer metrics available via YouTube's API services and must not offer independently calculated or derived metrics that replace API data — but the same policies also state that metrics displayed must be calculated exclusively from YouTube API data through basic arithmetic. Our KPIs (`engagement_rate`, `views_per_day`, `views_per_subscriber`) are basic arithmetic on returned statistics for an offline educational analysis, not a service offering metrics to users — that is the defensible reading, and the June 2026 "additional policies on derived metrics and data storage" apply to audited developers with analytics use cases who explicitly apply for permission. No legal certainty is claimed. The planner carries this into `data/README.md` as an honestly stated tension (same treatment as the Day 3 CoinGecko redistribution tension), and the dashboard shows the underlying counts next to every derived rate so nothing replaces the API data.
3. **Committed raw JSON vs data-storage rules (same treatment as (2)).** Developer Policies §III.E.4 (checked 2026-11-08) allow storing video statistics for more than 30 days but require verifying every 30 days that the data is still authorised / the video still exists. Our raw JSONs are a dated one-time snapshot (2026-11-08) committed as the provenance record, following the Days 1–3 convention; they are not re-served by a live service. No YouTube page found states explicitly whether committing verbatim raw API JSON to a public GitHub repo counts as redistribution, so this is unresolved and no legal certainty is claimed. State the snapshot date and the tension in `data/README.md`.
4. **No date-bounded sample.** The helper cannot pass `publishedAfter`/`publishedBefore`, so the sample mixes 2021 and 2026 videos. `views_per_day` corrects for age, but a relevance-ranked sample still skews toward videos YouTube currently surfaces. The planner should note this as a limitation, not try to work around it with extra calls.
5. **Search relevance is a black box.** The API does not document how `order=relevance` ranks results. Findings are descriptive of the returned set. If two queries return heavily overlapping top results, that is itself a finding about topic overlap — report the dedupe counts.
6. **No sentiment model in Day 4** (§3.3). If the planner wants comment sentiment, it must add a comments endpoint to the helper first (new capability, new quota budget, defined method) — it cannot be bolted onto this brief's design.
7. **Dependency:** none new (§3.4). If the planner adds one, it must be pinned and justified in the plan.

### 5.5 Licence / attribution

- Data is public YouTube video metadata fetched under the **YouTube API Services Terms of Service and Developer Policies** (checked 2026-11-08). Attribution is required: include on the dashboard and in the repo README, legible: **"Data from the YouTube Data API v3"** with a link to YouTube's Terms of Service (`https://www.youtube.com/t/terms`), per the Developer Policies requirement that API clients display a link to YouTube's Terms of Service.
- Do not redistribute raw bulk data or re-host the API. Cache the fetched responses locally for the project only (§5.3, §5.4 item 3).
- Only public metadata is used — no user data, no comments text, no private data. The API key has no OAuth scopes.
- Code in this repo is MIT (see `LICENSE`); YouTube data is under separate YouTube terms, not MIT.
- **No copying code or tutorials from the web.** All code is Victor's own original work, written from this brief and the plan.

---

## Handoff (researcher → planner)

**What was produced:** exactly one file — `day-04-youtube-video-performance-analyzer/research_brief.md` (this file). One verification probe was run; no live dataset was fetched; no other file was written.

**Verified numbers:**
- Probe (2026-11-08): `search --query "data analytics" --max-results 2` → exit 0, ~1.1 s, `youtube#searchListResponse`, 2 items (`ejKxJOnnAlI`, Esther Chinenye Anagu, 2026-01-27; `yZvFH7B6gKI`, CareerFoundry, 2021-03-25), `nextPageToken` present but unusable (helper has no pageToken support), cost **100 quota units**.
- Quota budget for the build: 5 searches (500) + ~5 videos calls (5) + ~3 channels calls (3) ≈ **508 units (~5% of the 10,000/day quota)**; day total including the probe ≈ 608 units.
- Expected rows: 250 candidates → ~200–240 unique → **~180–230 final videos** (coder verifies actuals).
- Endpoints: `/search` (100 units), `/videos`, `/channels`, `/playlistItems` (1 unit each); counts arrive as strings; duration is ISO 8601; no pagination; no date bounding via the helper.

**Key decisions:**
- Sample: 5 fixed queries × 50 results, `order=relevance` (deliberately not `viewCount`), dedupe, batched `videos` calls (≤50 IDs), batched `channels` calls for subscriber counts.
- KPIs: `views_per_day` (primary performance measure), `engagement_rate = (likes+comments)/views`, like/comment rates, `views_per_subscriber`, duration buckets, publish hour/day-of-week, deterministic keyword topic + format grouping. Medians everywhere, never means.
- High performers = top quartile of `views_per_day`; recommendations are descriptive, never causal.
- Comment sentiment OUT of scope for Day 4 (no comments endpoint in the helper); keyword grouping is the Day 4 text approach.
- Synthetic fallback: seed 42, n=200, log-normal views (median 50k), likes 2–6% of views, comments 0.05–0.5% of views, same schema as live, `data/raw/*_synthetic.json` only.
- Licence tensions recorded honestly: June 2026 derived-metrics/quota-bucket changes and the 30-day storage verification rule — both carried into `data/README.md`, neither claimed as legally certain.

**Known gaps:** no date-bounded sample possible (helper limitation); search relevance ranking is undocumented; the June 2026 quota-bucket split means the coder's actual fetch is the ground truth on quota; `other` topic bucket may exceed 30% (then report, don't re-tune); subscriber counts hidden for some channels.

**Planner's first step:** take this brief as the source of truth for data, sample design, metrics, and validation targets, and write `plan.md` — starting with the exact file tree (including the video frame CSV, the per-query raw JSONs, and the KPI/recommendation outputs) and the per-file responsibilities for the coder.
