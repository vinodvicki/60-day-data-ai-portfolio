# Day 04 — YouTube Video Performance Analyzer: Build Plan

**Status:** PLAN — planner sign-off complete (AGENTS.md, stage 2).
**Source of truth:** `research_brief.md` (2026-11-08) + this plan. **If brief and
plan disagree, the plan wins and the difference is noted in §11.** The coder
must reuse the brief + this plan. **No extra web searches.**
**Roadmap entry (verbatim):** "DAY 04 | YouTube Video Performance Analyzer —
Problem / analysis: Explore video topics, duration, publishing time, views,
and engagement to find patterns linked with stronger performance. GitHub
deliverable: Creator KPI dashboard with content recommendations." Section
context (Days 4–6, Social Media & Digital Marketing): Core skills: API
integration, NLP, sentiment analysis, text visualization. Suggested data:
YouTube Data API; public, permissioned comment and metadata datasets.

| Item | Value |
|---|---|
| Fetch date | 2026-11-08 (relevance-ranked snapshot as of this date — not a date-bounded cohort, §3) |
| Source | YouTube Data API v3 via the `custom.youtube` connector (helper `bin/youtube.py`) |
| Sample | 5 fixed queries × 50 results, `order=relevance`, deduped by `videoId` |
| Expected rows | **250 candidates → ~200–240 unique videos → ~180–230 final videos** in the processed video frame (the coder must verify the actuals and report them; do not assume them) |
| Quota budget | **≈ 508 units (~5% of the 10,000/day free-tier quota)** — 5 searches × 100 + ~5 videos calls × 1 + ~3 channels calls × 1; day total including the researcher's 100-unit probe ≈ 608 units |
| Scope | Descriptive, historical performance analysis only. **No causal claims, no "best time to post" prescription, no guarantee of future performance.** Comment sentiment is OUT of scope (§4). |

## 1. Problem statement + audience

**Problem.** A data/AI creator deciding what to publish next can see views,
likes and comments on individual videos, but cannot tell which topics,
formats, lengths and publishing times are actually linked with stronger
performance: a 2021 video with 2M lifetime views is not comparable to a 2026
video with 200K views, a viral outlier distorts any average, and a
high-view video with almost no likes is a different kind of success from a
smaller video whose audience engages heavily. Day 4 fetches a bounded,
reproducible sample of public data/AI-adjacent YouTube videos, normalises
performance by video age (`views_per_day`), compares topics, durations,
formats and publish times on medians — never means — and turns only the
differences visible in those medians into concrete, evidence-cited content
recommendations.

**Audience / decision-maker.** A data/AI creator (the portfolio's own field)
deciding what to publish next — which topic to cover, how long to make the
video, what format to use, and roughly when to publish. They are not a data
analyst: every recommendation in the dashboard, notebook and notes must be
plain-language, must cite the numbers behind it, and must carry its caveat
that the pattern is descriptive of this sampled set, not a causal finding.
The dashboard is the decision aid; `outputs/insights_summary.md` is the
plain-language findings note and `outputs/recommendations.md` is the
evidence-cited recommendation list (§4.4).

## 2. Research questions (exactly 3)

1. **Which topics, formats and durations perform best?** For each topic
   group (§4.2), format (§4.2) and duration bucket (§4.2), what are the
   median `views_per_day` and median `engagement_rate`, with what sample
   size (n) — and how do the top-quartile performers (§4.3) differ from the
   rest in their topic, format and duration mix?
2. **When should a creator publish?** What are the median `views_per_day`
   by publish hour (UTC, with a US Pacific display hour) and by day of week
   — and, given that the channel's audience timezone is unknown and the
   sample is relevance-ranked, how much (or how little) can honestly be
   concluded from any hour/day pattern in this sample?
3. **What concrete recommendations follow — and what is the evidence for
   each?** Which specific, actionable content recommendations (topic,
   format, duration, publish-time) are supported by the medians in this
   sample, each citing its numbers and its caveat (§4.4) — and which
   tempting claims (causal, single-video, or thin-sample) must *not* be
   made?

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
  exchange; redirects are refused by the helper. This is a NEW data source
  for the portfolio (Days 1–3 used CoinGecko); nothing carries over except
  the workflow conventions (provenance, synthetic fallback, `.gitignore`
  rule — §3.3).
- **Endpoints (exactly the four helper commands; parameters are what the
  helper actually sends — copy them, do not re-derive them):**

| Command | API endpoint | Parameters sent by the helper | Cost |
|---|---|---|---|
| `search --query "..." --max-results N` | `GET /search` | `part=snippet`, `q=<query>`, `type=video`, `maxResults=N`, `order=relevance` (default; do not pass `--order`) | **100 units** |
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

- **The 5 queries (fixed — do not invent, add, or re-word any query):**

| # | Query | `max-results` | Why this topic |
|---|---|---|---|
| 1 | `data analytics` | 50 | Core topic — the portfolio's own field |
| 2 | `machine learning tutorial` | 50 | AI/ML tutorial demand |
| 3 | `Python data analysis` | 50 | Tool-specific (Python) demand |
| 4 | `artificial intelligence explained` | 50 | AI explainer demand |
| 5 | `SQL tutorial` | 50 | Tool-specific (SQL) demand |

- **Response fields the coder will use.** `search` → `snippet` per video:
  `videoId`, `title`, `channelId`, `channelTitle`, `publishedAt` (ISO 8601
  UTC), `description`, `liveBroadcastContent`. Search returns **no
  statistics** — views/likes/comments require the `videos` call. `videos` →
  `snippet`: `title`, `channelId`, `channelTitle`, `publishedAt`,
  `description`, `tags` (may be absent), `categoryId`, `defaultLanguage`
  (may be absent), `liveBroadcastContent`. `videos` → `statistics`:
  `viewCount`, `likeCount`, `commentCount` — **all arrive as strings; cast
  to int**. `likeCount` and/or `commentCount` may be **absent** (likes/
  comments disabled) — record as missing (NaN), never silently fill with
  0. `viewCount` absent means the video is unusable — drop the row and count
  it. `videos` → `contentDetails`: `duration` (ISO 8601, e.g. `PT12M34S`,
  `PT1H2M3S`, `PT45S` — parse to seconds; Shorts are `PT60S` or less),
  `definition`, `dimension`, `licensedContent`. `channels` → `snippet`:
  `title`, `publishedAt` (channel creation date). `channels` →
  `statistics`: `subscriberCount`, `viewCount`, `videoCount` — strings;
  `subscriberCount` is **hidden for some channels** (absent) — record as
  missing, never 0; `hiddenSubscriberCount` (bool) tells you which.
  `playlistItems` → `contentDetails.videoId`, `snippet.publishedAt`,
  `snippet.title`, `snippet.channelId` (newest first by default; fallback
  only, §3.2).
- **Category IDs** (record raw; map only the IDs actually observed, unknown
  → `other (<id>)`): 1 Film & Animation, 2 Autos & Vehicles, 10 Music,
  15 Pets & Animals, 17 Sports, 19 Travel & Events, 20 Gaming, 22 People &
  Blogs, 23 Comedy, 24 Entertainment, 25 News & Politics, 26 Howto &
  Style, 27 Education, 28 Science & Technology, 29 Nonprofits & Activism.
- **Verification probe (already run by the researcher, 2026-11-08 — do not
  re-run it as a separate probe):** `search --query "data analytics"
  --max-results 2` → exit 0, ~1.1 s, `youtube#searchListResponse`,
  `regionCode: "US"`, `pageInfo: {totalResults: 1000000, resultsPerPage:
  2}`, `nextPageToken: "CAIQAA"` present (but the helper cannot pass a page
  token — see below). Items: `ejKxJOnnAlI` — "Most People Learning Data
  Analytics Are Wasting Their Time (Here's Why)", channel "Esther Chinenye
  Anagu" (`UCyYQbC8QsuhfpU5ewU8AF6g`), published `2026-01-27T07:00:29Z`;
  `yZvFH7B6gKI` — "What Is Data Analytics? - An Introduction (Full
  Guide)", channel "CareerFoundry" (`UCzAF54cHk1ZO82af-8E3qOQ`),
  published `2021-03-25T13:13:45Z`. Cost: **100 quota units.** Note:
  `totalResults: 1000000` is the API's capped estimate, not a real count
  of matching videos — never report it as a finding.
- **Hard limits of the helper (design constraints, not bugs to fix in Day
  4):** no `pageToken` support — search and playlist-items return the first
  page only; `maxResults` caps at 50 per search call; search is capped at
  500 results per query by the API (irrelevant here, the helper only ever
  sees the first 50). **No date bounding** — the helper sends no
  `publishedAfter` / `publishedBefore`, so the sample cannot be restricted
  to a date window; it is a relevance-ranked snapshot as of the fetch date
  (2026-11-08), not a time-bounded cohort — state this in the README.
  Read-only, public data only; no uploads, comments, or private data (API
  key, no OAuth scopes). Timeout 30 s per request; redirects refused.

### 3.2 Fetch rules

- **Exactly 5 search calls** (one per query in §3.1, `maxResults=50`,
  `order=relevance` — the helper default; do not pass `--order`). Do **not**
  use `order=viewCount` — it would return only the most-viewed videos and
  destroy the variance the analysis needs.
- **Deduplicate** by `videoId` across the five queries (overlap is expected
  — e.g. a Python tutorial can match queries 1, 3 and 5). Keep the first
  occurrence; record how many duplicates were dropped.
- **Filter:** drop `liveBroadcastContent != "none"` (live/upcoming streams
  have no comparable lifetime stats); drop rows with no `viewCount` after
  the `videos` call (count them).
- **Detail fetch:** collect all surviving IDs and fetch in **one batched
  `videos` call per ≤ 50 IDs** (expect 4–5 calls). Then **one batched
  `channels` call per ≤ 50 distinct `channelId`s** (expect 2–3 calls) for
  subscriber counts.
- **Polite use:** ≥ 2 s between calls (the brief's verified rule — this is
  stricter than, and therefore satisfies, a 1 s minimum); **one retry after
  30 s on HTTP 5xx / timeout only**; **no retry on 403 `quotaExceeded`** —
  stop and fall back (§3.5). Never hammer the API.
- **Quota budget:** 5 searches × 100 = 500 + ~5 videos calls × 1 = 5 + ~3
  channels calls × 1 = 3 → **≈ 508 units, ~5% of the 10,000/day quota**
  (resets at midnight Pacific Time). Including the researcher's 100-unit
  probe, the day's total is ≈ 608 units — still ~6% of quota. There is ample
  headroom for one re-run if a call fails; there is no headroom for
  exploratory extra searches, so the coder runs exactly this design.
- **June 2026 quota change (open item):** Google split the daily quota into
  separate buckets from 2026-06-01. The 10,000-unit framing above is the
  connector doc's figure and the probe succeeded within it, so the build
  proceeds on that basis — but the coder's actual fetch is the ground truth.
  If a `quotaExceeded` appears far earlier than the ~508-unit budget
  predicts, stop, check the Google Cloud Console quota page for the bucket
  breakdown, and report the actual bucket limits — do not retry or add
  searches.
- **Error handling (from the brief — follow the table, do not improvise):**

| Error | Meaning | Coder action |
|---|---|---|
| `400 keyInvalid` | Stored key wrong or project misconfigured | Stop. Do not retry. Report as blocked; key is the connector's business, never to be pasted or hard-coded anywhere. |
| `403 quotaExceeded` | Daily quota hit | Stop immediately. No retry. Fall back to cache, then synthetic (§3.5). |
| `403 accessNotConfigured` | YouTube Data API v3 not enabled on the project | Stop. Report as blocked (it was enabled 2026-11-07 and the probe succeeded, so this is not expected). |
| `403` other (e.g. `forbidden`) | Request rejected for another reason | Check the request first (IDs well-formed, ≤ 50 per call); one careful retry only if the request was malformed. |
| HTTP 5xx / timeout | Transient server/network failure | One retry after 30 s, then fall back (§3.5). |
| Empty `items` on a `videos` call | IDs invalid, private, or deleted | Drop those IDs, count them, continue — this is not an error. |

  The helper exits non-zero with `HTTP {code} from {path}: {body[:500]}` —
  the pipeline must catch that, log the code/reason, and follow the table
  above. **Never log the API key** (the helper never prints it; keep it
  that way).
- **Fallback if a query under-delivers:** if any query returns < 25 usable
  videos after filtering, the coder may add **one** playlist-based top-up,
  and only then: (1) take the most-subscribed channel already present in
  that query's results (from the `channels` call); (2) its uploads playlist
  ID is `UU` + the channel ID minus its leading `UC` (e.g. channel
  `UCxxxx…` → playlist `UUxxxx…`) — **the coder must verify this convention
  works with one `playlist-items --max-results 10` call before relying on
  it**; if it fails, abandon this route, do not debug it further; (3) cap
  the top-up at 25 videos from that playlist's first page, dedupe against
  the existing sample, and record the top-up separately in
  `data_source.json` (`top_up` field) and `data/README.md`. No other top-up
  route is authorised. Do not invent queries, do not re-run a failed search
  hoping for different results.
- **Expected row counts (coder must verify the actuals and report them; do
  not assume these):** 5 × 50 = **250 candidates** → after dedupe
  **~200–240 unique videos** → after filtering/missing statistics
  **~180–230 rows** in the final video frame. If the final count lands
  below 150, the coder reports it as a sample-size caveat in the README;
  the analysis still runs, but the recommendations are labelled
  thin-sample.
- **Channel concentration check:** report how many distinct channels the
  sample covers and the largest single channel's share. If one channel is
  > 20% of the sample, the dashboard must say so — a one-channel sample is
  a channel study, not a topic study.

### 3.3 Data provenance

- `data/README.md` (coder writes it) records: provider, endpoints used, the
  5 queries, access date (2026-11-08), quota units used, row counts
  (candidates → unique → final, with dedupe/filter counts), channel
  concentration, and the licence/attribution note (§3.4) + the
  derived-metrics and storage tensions stated honestly (§3.4).
  `data/processed/data_source.json` records `source` (`"live"`, `"cache"`
  or `"synthetic"`), `generated_at_utc`, `synthetic` (bool), `seed` (`null`
  for live data, `42` for synthetic), plus `queries` (the 5 query strings),
  `max_results_per_query` (50), `video_count`, `channel_count`,
  `quota_units_used` (best estimate), `api` (`"youtube-data-api-v3"`), and
  `top_up` (null, or the §3.2 details if used).
- **Data-source field rule (Day 2 day-log lesson — mandatory):** an offline
  pipeline run (`--offline` / `--use-cache`) overwrites `data_source.json`'s
  `source` field to `"cache"`. Before publishing, the coder/optimizer must
  either **re-run the pipeline live** (restoring `"live"`) or **restore the
  field by hand with the true value and record the correction** in
  `data/README.md`. A published `data_source.json` that says `"cache"` when
  the data was in fact fetched live is a defect; the publisher's frozen-tree
  check (§8) includes verifying this field.
- **Data-commit rule (from Day 1):** small raw data IS committed — files
  under 1 MB each, under 5 MB per day folder — because the raw files are the
  provenance record. **`.gitignore` must NOT exclude `data/`.** Anything
  larger must be `.gitignore`d and regenerated by the pipeline. Synthetic
  fallback output goes to `data/raw/*_synthetic.json` and is git-ignored; it
  must never overwrite the live cache.
  `python3 src/data_pipeline.py --offline` / `--use-cache` runs from the
  committed cache with no network.
- **Cache reuse note:** there is no prior YouTube cache — Day 4 is the first
  YouTube day. A cache fallback is only valid if a Day 4 fetch has previously
  succeeded and written `data/raw/` files in the Day 4 folder. Do **not**
  reuse any other day's data — the source differs entirely.
- **Key rule:** the API key comes only from the `custom.youtube` connector.
  No `.env` file, no key in code, no key in any committed file, no key in
  logs.

### 3.4 Licence / attribution

- Data is public YouTube video metadata fetched under the **YouTube API
  Services Terms of Service and Developer Policies** (checked 2026-11-08).
  Attribution is required: include on the dashboard and in the repo README,
  legible: **"Data from the YouTube Data API v3"** with a link to YouTube's
  Terms of Service (`https://www.youtube.com/t/terms`), per the Developer
  Policies requirement that API clients display a link to YouTube's Terms of
  Service.
- Do not redistribute raw bulk data or re-host the API. Cache the fetched
  responses locally for the project only (§3.3).
- Only public metadata is used — no user data, no comments text, no private
  data. The API key has no OAuth scopes.
- Code in this repo is MIT (see `LICENSE`); YouTube data is under separate
  YouTube terms, not MIT.
- **Derived-metrics tension (record honestly, do not resolve by redefining
  the KPIs — same treatment as Day 3's CoinGecko tension):** the YouTube
  Developer Policies (checked 2026-11-08) say API clients must only offer
  metrics available via YouTube's API services and must not offer
  independently calculated or derived metrics that replace API data — but
  the same policies also state that metrics displayed must be calculated
  exclusively from YouTube API data through basic arithmetic. Our KPIs
  (`engagement_rate`, `views_per_day`, `views_per_subscriber`) are basic
  arithmetic on returned statistics for an offline educational analysis,
  not a service offering metrics to users — that is the defensible reading,
  and the June 2026 "additional policies on derived metrics and data
  storage" apply to audited developers with analytics use cases who
  explicitly apply for permission. **No legal certainty is claimed.** The
  dashboard shows the underlying counts next to every derived rate so
  nothing replaces the API data, and `data/README.md` states this tension
  honestly.
- **Committed raw JSON vs data-storage rules (same treatment):**
  Developer Policies §III.E.4 (checked 2026-11-08) allow storing video
  statistics for more than 30 days but require verifying every 30 days that
  the data is still authorised / the video still exists. Our raw JSONs are a
  dated one-time snapshot (2026-11-08) committed as the provenance record,
  following the Days 1–3 convention; they are not re-served by a live
  service. **No YouTube page found states explicitly whether committing
  verbatim raw API JSON to a public GitHub repo counts as redistribution,
  so this is unresolved and no legal certainty is claimed.** State the
  snapshot date and the tension in `data/README.md`.
- **No copying code or tutorials from the web.** All code is Victor's own
  original work, written from the brief and this plan.

### 3.5 Synthetic fallback rules (if the API is unreachable)

If all requests fail (quota, network block, or outage) after one polite retry:
1. Use a **cached copy** of a previous successful Day 4 fetch if one exists
   (`data/raw/` in this day folder only — see §3.3 cache note).
2. Otherwise generate a **clearly labelled synthetic dataset** for
   development only, deterministic, **seed 42**:

| Field | Synthetic rule |
|---|---|
| `n` | **200 videos** across 20 synthetic channels ("Synthetic Creator 01" … "Synthetic Creator 20", 10 videos each) |
| `view_count` | Log-normal, median 50,000, σ_log 1.2, clipped to [100, 5,000,000] |
| `like_count` | `view_count × U(0.02, 0.06)` (rounded) |
| `comment_count` | `view_count × U(0.0005, 0.005)` (rounded) |
| `subscriber_count` | Log-normal, median 100,000, σ_log 1.0, clipped to [1,000, 10,000,000] |
| `duration_seconds` | Log-normal, median 600 s, σ_log 0.8, clipped to [60, 3600], rendered back to ISO 8601 |
| `published_at` | Uniform over the 365 days before 2026-11-08 |
| `title` / `tags` | Assembled from fixed template lists per §4.2 topic group (e.g. "Python Data Analysis Tutorial for Beginners"), so the keyword grouping classifies them |
| `category_id` | 27 (Education) or 28 (Science & Technology), alternating |

3. Synthetic output goes **only** to `data/raw/*_synthetic.json` — it must
   never overwrite the live cache. `data/processed/data_source.json`
   records `synthetic: true` + `seed: 42`. All downstream outputs are
   labelled SYNTHETIC. Synthetic data follows the same schema as live data
   (same columns, §4.1) so the pipeline, notebook, and dashboard run
   unchanged. Synthetic files are git-ignored
   (`data/raw/*_synthetic.json` in `.gitignore`); live `data/raw/*.json`
   are committed.
4. Never present synthetic data as real YouTube data. Mark every chart, the
   app and the README **"SYNTHETIC DATA — API unavailable on 2026-11-08"**
   and re-fetch real data before publishing.
   `python3 src/data_pipeline.py --offline` / `--use-cache` runs from the
   committed cache with no network and never generates synthetic data.
5. **Synthetic engagement rates are uniform by construction, so on synthetic
   data the topic/duration comparisons have no interpretation** — state this
   in the README, notebook and insights summary if the synthetic path is
   used.

## 4. Method — KPI definitions, groupings, recommendations, validation, targets

All metrics are computed on the cleaned video frame (one row per video).
Counts are integers; rates are decimals (present as % in the dashboard).
**Use medians, not means, for every views/engagement comparison** — view
counts are heavily right-skewed and a single viral video would dominate any
mean. Log10(viewCount) is used for charts where stated (§7). **No
log-transformed views are used in any KPI or recommendation** — only in
chart 04's axis scale.

### 4.1 Core KPIs (definitions fixed — the planner/coder must not redefine them)

| Metric | Formula | Notes |
|---|---|---|
| `view_count` | `statistics.viewCount` (int) | Lifetime views at fetch time. |
| `like_count` | `statistics.likeCount` (int, NaN if absent) | Absent = disabled, not zero. |
| `comment_count` | `statistics.commentCount` (int, NaN if absent) | Absent = disabled, not zero. |
| `subscriber_count` | `channels.statistics.subscriberCount` (int, NaN if hidden/absent) | Absent = hidden, never 0. |
| `days_since_publish` | `(fetch_date − publishedAt).days`, minimum 1 | Fetch date = 2026-11-08. A video published today scores 1 day, never 0 (no division by zero). |
| `views_per_day` | `view_count / days_since_publish` | Age-normalised performance — the **primary** "how strong is this video" measure. |
| `engagement_rate` | `(like_count + comment_count) / view_count` | Primary engagement KPI. Requires both counts present; NaN otherwise. Typical range ~0.5–8% — see §4.5 sanity checks. |
| `like_rate` | `like_count / view_count` | Component of engagement. |
| `comment_rate` | `comment_count / view_count` | Component of engagement; typically ~0.05–0.5% of views. |
| `views_per_subscriber` | `view_count / subscriber_count` | Reach relative to channel size. NaN where subscriber count is hidden. A small channel with high views/subscriber is outperforming its base. |
| `duration_seconds` | Parsed from `contentDetails.duration` (ISO 8601) | `PT12M34S` → 754. All durations must parse; zero/negative is a data error, not a short video. |
| `publish_hour_utc` | Hour of `publishedAt` (0–23, UTC) | Plus a US Pacific display hour (UTC−8 in November, PST). **UTC is canonical; Pacific is display only.** |
| `publish_dow` | Day of week of `publishedAt` (Mon–Sun) | |

### 4.2 Groupings for pattern-finding (fixed before seeing the data — do not re-tune after seeing results)

| Grouping | Buckets | Rule |
|---|---|---|
| **Duration** | Short `≤ 60 s` (Shorts-length) · Short-form `61–300 s` · Medium `301–900 s` · Long `901–1800 s` · Deep-dive `> 1800 s` | Fixed boundaries, set before seeing the data. Report median `views_per_day` and `engagement_rate` per bucket. Do not drop Shorts — bucket them and report their share of the sample. |
| **Topic (subject)** | `python` · `sql` · `ai_ml` · `bi_viz` · `career` · `general` · `other` | Deterministic keyword match on lower-cased `title + tags + description`, **first match wins in this priority order** (implement verbatim in `classify_topic`, §6): `python` ("python", "pandas", "numpy") → `sql` ("sql", "mysql", "postgres") → `ai_ml` ("machine learning", "artificial intelligence", " ai ", "llm", "chatgpt", "deep learning", "neural") → `bi_viz` ("power bi", "tableau", "excel", "dashboard", "visualization", "visualisation") → `career` ("career", "job", "salary", "interview", "roadmap") → `general` ("data analytics", "data analyst", "data science") → `other`. This keyword grouping **is** the Day 4 text-classification step (a simple, transparent, reproducible NLP approach — no model, no labels needed). If `other` exceeds 30% of the sample, the grouping is too narrow — **report it, do not silently re-tune the keywords after seeing results**. |
| **Format** | `tutorial` · `explainer` · `other` | `tutorial` if title/tags contain "tutorial", "how to", "learn", "course", "beginner", "step by step"; `explainer` if they contain "explained", "what is", "introduction", "guide", "why"; else `other`. First match wins (`tutorial` before `explainer`). A second axis, independent of subject. Implement verbatim in `classify_format` (§6). |
| **Publish time** | Hour (0–23 UTC) and day-of-week | Report median `views_per_day` by hour and by weekday. **Confound, stated up front:** creators publish for their own audience's timezone, which the API does not reveal — any hour pattern is descriptive of this sample, not a "best time to post" prescription. `publishedAt` is UTC and the channel timezone is unknown; the Pacific hour is display only (§4.1). |
| **Channel size** | By `subscriber_count` terciles (small / mid / large, cut at the sample's own 33rd/66th percentiles) | Tests whether engagement patterns differ by channel size; also feeds `views_per_subscriber`. |
| **Category** | `categoryId` (raw value, mapped per §3.1) | Reported as a breakdown only; no hypothesis attached. |

**Comment sentiment is OUT of scope for Day 4.** The roadmap lists
NLP/sentiment as section skills, but the Day 4 deliverable is a Creator KPI
dashboard with content recommendations, and comment *text* is not fetched by
any helper command (there is no comments endpoint in `youtube.py`). Sentiment
would need a new helper capability, a new quota budget, and a defined method
— it cannot be bolted onto this design.

### 4.3 "Stronger performance" — the comparison that drives the recommendations

- **High performers = top quartile of `views_per_day`** (within the whole
  sample, 75th-percentile cut). Compare their median `engagement_rate`,
  duration-bucket mix, topic mix, and publish-hour distribution against the
  remaining 75%. Report the numbers side by side; the recommendations (§4.4)
  are drawn only from differences that are visible in those medians, not
  from single videos.
- **No causal claims.** A pattern (e.g. "medium videos have higher median
  views/day") is reported as *"in this sample, medium-length videos had
  higher median views per day"* — never "medium videos get more views".
  Correlation in a relevance-ranked, cross-sectional sample cannot support a
  causal recommendation, and the dashboard must not imply otherwise.
- The dashboard header carries the sentence: *"Performance patterns here
  describe this sampled set of public videos. They are descriptive, not
  causal, and are not a guarantee of future performance."*

### 4.4 Recommendation format

Every recommendation in the dashboard / notebook / insights summary /
`outputs/recommendations.md` must be traceable to a number in the same
output:

| Field | Meaning |
|---|---|
| `recommendation` | Plain-language advice, e.g. "Medium-length videos (5–15 min) had the highest median views per day in this sample." |
| `evidence` | The numbers behind it, e.g. "median 1,240 views/day (n=52) vs 610 for long videos (n=48)". |
| `sample_basis` | Which slice it comes from (topic, duration bucket, channel size) and its n. |
| `caveat` | Always present: "Descriptive pattern in a relevance-ranked sample of ~200 videos — not a causal finding." |

Rules: every claim in a recommendation must be a number in the processed
CSV. **No causal verbs** ("will boost", "causes", "guarantees"). No advice
about a specific creator or video by name beyond the aggregated evidence.
Each recommendation must cite the numbers behind it in the exact form
"videos 301–900s have median X views/day vs Y overall" (with the real X, Y
and n from `videos.csv`). Recommendations are generated from the group
medians by one function (`build_recommendations`, §6), not hand-written per
video. If a group has n < 10, its recommendation is labelled thin-sample or
omitted — never presented as a firm finding.

### 4.5 Validation (no ground truth exists for "good" performance)

There is no labelled "good video" dataset, so validation is sanity checks +
one manual recomputation, not precision/recall:

| Check | Expectation | If it fails |
|---|---|---|
| Row counts | 250 candidates → ~200–240 unique → ~180–230 final (§3.2) | Report the actuals; < 150 final rows = thin-sample caveat in README |
| Dedup | Zero duplicate `videoId`s in the final frame | Dedup logic is wrong — fix before proceeding |
| Duration parse | 100% parse, all > 0 s | A parse failure is a code bug, not a data quirk |
| Dates | No `publishedAt` in the future; none before 2005-04-23 (YouTube's launch) | Flag the row; do not silently drop it without recording why |
| Missing stats | Report % of rows missing `likeCount` / `commentCount` / `subscriberCount` | If > 25% missing likes, `engagement_rate` medians are thin — say so |
| Engagement sanity | Sample median `engagement_rate` roughly 0.5–8% | Median > 15% or < 0.1% means a definition or parsing error — stop and check before building charts |
| Views sanity | Median `views_per_day` > 0; no infinite/NaN values | Division or date bug — fix before proceeding |
| Manual validation (mandatory) | Recompute **one** video's `engagement_rate` and `views_per_day` by hand from the raw `videos` JSON and match the processed CSV to the last digit | Record the video ID, the hand-computed numbers, and the match in `data/README.md` (same convention as Days 1–3) |
| Top-quartile comparison | High performers' median `engagement_rate` and `views_per_day` reported vs the rest, with sample sizes | If the top quartile is dominated by one channel (> 50% of it), say so — the "pattern" may just be that channel |
| Topic coverage | `other` topic share reported | If `other` > 30%, report it; do not re-tune keywords (§4.2) |

### 4.6 What "good" looks like — targets table

| Metric | Target |
|---|---|
| Final videos in `videos.csv` | **≥ 180** (expected ~180–230; < 150 = thin-sample caveat, §3.2) |
| Videos with `like_count` present | **≥ 90%** of final rows (else `engagement_rate` medians are thin — say so) |
| Videos with `subscriber_count` present | **≥ 80%** of final rows (hidden counts are expected for some channels) |
| Dedupe | **Zero** duplicate `videoId`s in the final frame; dedupe count reported (candidates − unique) |
| Duration parse | **100%** parse, all > 0 s |
| Engagement sanity | Sample median `engagement_rate` within **0.5–8%** |
| Topic coverage | `other` topic share **≤ 30%** (if above, report — do not re-tune) |
| Channel concentration | Largest single channel **≤ 20%** of the sample (if above, dashboard says so) |
| High-performer comparison | Top-quartile vs rest medians reported with n for both groups |
| Recommendations | Every recommendation cites its numbers + caveat (§4.4); **zero** causal verbs |
| Charts | Exactly 4 PNGs (§7), drawn to scale, legible, source-noted |

If a target is missed, the correct response is to report the miss and
diagnose it — **not** to re-tune keyword lists, buckets, or thresholds after
seeing the results. Groupings and KPI definitions are fixed in this plan
before the fetch runs.

**Conventions the coder must not re-decide:** medians not means for every
views/engagement comparison; `engagement_rate = (likes + comments) / views`
(the simple formula — no weighted or log variant); `days_since_publish`
minimum 1; duration buckets per §4.2; topic/format keyword lists and
priority order per §4.2 (verbatim); high performers = top quartile of
`views_per_day`; publish hour canonical in UTC, Pacific display only; no
log-transformed views in any KPI or recommendation (log10 only on chart
04's axis); missing like/comment/subscriber counts stay NaN, never 0. If any
of these is unworkable, send it back to the planner with the exact point —
do not silently substitute a different convention.

## 5. Exact file tree (mirror Day 3's shape)

```
day-04-youtube-video-performance-analyzer/
├── README.md
├── LICENSE                     # MIT (scaffolded; keep as-is)
├── requirements.txt
├── pyproject.toml
├── .gitignore
├── research_brief.md
├── plan.md                     # this file
├── data/
│   ├── README.md
│   ├── raw/
│   │   ├── search_data-analytics.json
│   │   ├── search_machine-learning-tutorial.json
│   │   ├── search_python-data-analysis.json
│   │   ├── search_artificial-intelligence-explained.json
│   │   ├── search_sql-tutorial.json
│   │   ├── videos_details.json
│   │   ├── channels_details.json
│   │   └── *_synthetic.json   # only if fallback used; git-ignored, never committed
│   └── processed/
│       ├── videos.csv          # ~180–230 rows expected: one row per video with all §4.1 KPIs + topic, format, duration bucket, publish hour/dow, channel size tercile, high_performer flag
│       └── data_source.json    # source, generated_at_utc, synthetic, seed (null live / 42 synthetic), queries, max_results_per_query, video_count, channel_count, quota_units_used, api, top_up
├── notebooks/
│   └── analysis.ipynb          # executes end-to-end offline via nbconvert
├── src/
│   ├── data_pipeline.py        # fetch, clean, KPIs, grouping, recommendations, synthetic fallback, save outputs
│   ├── youtube_kpi.py          # pure KPI/topic functions, fixed signatures (see §6) — no I/O, no network
│   ├── make_charts.py          # regenerates exactly the 4 PNGs in §7, offline from committed CSVs
│   └── app.py                  # Streamlit creator KPI dashboard (width='stretch', §6)
├── outputs/
│   ├── insights_summary.md     # plain-language findings (§2): one finding per question, each citing its number
│   ├── recommendations.md      # evidence-cited content recommendations (§4.4) — CHOSEN as a separate file so the findings note stays readable and the recommendation list stands alone
│   └── charts/
│       ├── 01_views_by_topic.png
│       ├── 02_duration_vs_performance.png
│       ├── 03_publish_time_heatmap.png
│       └── 04_engagement_scatter.png
├── screenshots/
│   └── dashboard.png           # REAL capture of the running app (see §6)
└── tests/
    └── test_pipeline.py        # pytest, offline, ≥7 tests (see §6)
```

Build only what this tree lists. No extra files, no extra charts, no extra
dependencies. (Day 1's `publish_checklist.md` / `test_report.md` are produced
by later roles, not by the coder; the coder must not pre-create them.)

**Not in scope (deferred, do not add):** comment sentiment analysis (no
comments endpoint — §4.2); any new helper capability; any extra search query
or top-up route beyond §3.2; any new runtime dependency (§3.4 of the brief —
pandas, NumPy, Plotly, Streamlit already in the Day 1–3 stack; duration
parsing is stdlib `re`, do not add `isodate` or any other package).

## 6. Per-file responsibilities

| File | Responsibility |
|---|---|
| `README.md` | Problem + audience (§1), dataset summary (source, endpoints, the 5 queries, access date 2026-11-08, row counts, quota used, licence note), tools, method (KPI list, duration buckets, topic/format keyword grouping, high-performer definition, recommendation format), key insights (filled with real numbers after the run), visuals (the 4 charts embedded), how to run, limitations (§3.1 no date bounding, relevance black box, no causal claims, no sentiment), descriptive-not-causal sentence (§4.3) + "Data from the YouTube Data API v3" attribution with link to YouTube's Terms of Service. |
| `data/README.md` | Provenance (§3.3): provider, endpoints, the 5 queries, access date, quota units used, row counts (candidates → unique → final, dedupe/filter counts), channel concentration, licence/attribution note + derived-metrics and 30-day storage tensions stated honestly, commit rule, one manually validated metric (by hand, with the numbers — e.g. recompute one video's `engagement_rate` and `views_per_day` from the raw `videos` JSON), versions used for this build, and the `data_source.json` source-field correction if §3.3 applied. |
| `data/raw/*.json` | Verbatim YouTube API responses, one per query (`search_<query-slug>.json`) plus `videos_details.json` and `channels_details.json`. Committed (small, <1 MB each). Never overwritten by synthetic data. |
| `data/processed/videos.csv` | One row per video, ~180–230 rows expected: `video_id, title, channel_id, channel_title, published_at, days_since_publish, view_count, like_count, comment_count, subscriber_count, duration_seconds, duration_bucket, topic, format, category_id, publish_hour_utc, publish_hour_pacific, publish_dow, channel_size, views_per_day, engagement_rate, like_rate, comment_rate, views_per_subscriber, high_performer`. Missing like/comment/subscriber counts are empty (NaN), never 0. |
| `data/processed/data_source.json` | `source`, `generated_at_utc`, `synthetic` (bool), `seed` (`null` live / `42` synthetic), `queries`, `max_results_per_query` (50), `video_count`, `channel_count`, `quota_units_used`, `api` (`"youtube-data-api-v3"`), `top_up` (null or §3.2 details). Subject to the §3.3 source-field rule (re-run live or restore before publishing). |
| `src/data_pipeline.py` | Fetch (5 searches via the helper, ≥ 2 s spacing, one 30 s retry on 5xx only, then fallback; batched `videos` calls ≤ 50 IDs, batched `channels` calls ≤ 50 IDs; playlist top-up only per §3.2), clean/dedupe/filter into the video frame, call `youtube_kpi.py` for KPIs/groupings/recommendations, `generate_synthetic(seed=42)`, `--offline` / `--use-cache` mode (runs from committed cache, no network, never generates synthetic data), `save_outputs()` writing raw JSONs + `videos.csv` + `data_source.json`. Mirror Day 2/3's function shapes (`fetch_search`, `fetch_video_details`, `fetch_channel_details`, `clean_videos`, `save_outputs`, `generate_synthetic`, `_load_cache`, `main`) so the tester can reuse the Day 1–3 test patterns. **Never log the API key; never put the key in any file.** |
| `src/youtube_kpi.py` | **Pure KPI/topic module. Pure, testable functions, no I/O, no network.** Signatures the coder must implement (names fixed so the notebook, app and tests import them, never re-implement them): `parse_duration_iso8601(duration: str) -> int` (ISO 8601 → seconds; `PT12M34S` → 754; raises on unparseable input); `duration_bucket(duration_seconds: int) -> str` (one of `short`, `short_form`, `medium`, `long`, `deep_dive` per §4.2 boundaries); `classify_topic(title: str, tags: list[str], description: str) -> str` (keyword lists + priority order verbatim from §4.2); `classify_format(title: str, tags: list[str]) -> str` (`tutorial` / `explainer` / `other`, verbatim from §4.2); `compute_kpis(videos_df) -> pd.DataFrame` (adds `days_since_publish`, `views_per_day`, `engagement_rate`, `like_rate`, `comment_rate`, `views_per_subscriber`, `duration_seconds`, `publish_hour_utc`, `publish_hour_pacific`, `publish_dow`, `duration_bucket`, `topic`, `format`, `channel_size`, `high_performer` per §4.1–4.3; medians never means; missing counts stay NaN); `build_recommendations(videos_df) -> list[dict]` (one dict per recommendation with `recommendation`, `evidence`, `sample_basis`, `caveat` per §4.4; n < 10 groups labelled thin-sample or omitted; no causal verbs). |
| `src/make_charts.py` | `python -m src.make_charts` regenerates **exactly the 4 PNGs in §7** in `outputs/charts/`, offline from the committed processed CSV only (no network, no API). Every chart: title, labelled axes with units, legend where needed, source note ("Source: YouTube Data API v3" or "SYNTHETIC DATA — API unavailable on 2026-11-08" when synthetic), readable at dashboard size, drawn **to scale** (no truncated or misleading axes). Must not create extra PNGs. |
| `src/app.py` | Streamlit creator KPI dashboard: topic multi-select (default all), duration-bucket filter, high-performer toggle, KPI summary (median views/day, median engagement rate, video count, channel count — medians, never means), the 4 charts (or their data rendered natively), the recommendation list with evidence + caveat per item, channel-concentration note if §3.2 applies, descriptive-not-causal sentence (§4.3) in the header, "Data from the YouTube Data API v3" attribution with link to YouTube's Terms of Service + synthetic banner if `data_source.json` says synthetic. **Layout must use `width='stretch'` (the current Streamlit API) — never the deprecated `use_container_width`** (Day 2 day-log lesson). **Human-readable labels everywhere** — no raw slugs (`data_analytics`, `ai_ml`, `short_form`) shown to the user; display "Data Analytics", "AI & Machine Learning", "Short-form (1–5 min)" etc. Must not crash on edge cases — Day 1 lesson (b): sort/reset indexes before any positional lookup. |
| `notebooks/analysis.ipynb` | Full analysis top-to-bottom, offline: load `videos.csv`, recompute KPIs/groupings via `youtube_kpi.py`, reproduce the 4 charts, answer each §2 question with numbers, show the recommendation table. Resolve the project root from the notebook file's own location via `_find_root()` (check for `data/processed/videos.csv` from the notebook's directory upward); **never from `Path.cwd()` alone** — Day 1 lesson (e). A copy executed outside the project must fail with a clear `FileNotFoundError`. Must execute end-to-end offline via nbconvert (CI runs it). |
| `tests/test_pipeline.py` | pytest, offline, **≥7 tests** (target 10–12). Must cover at minimum: (1) ISO 8601 duration parsing on hand-computed cases (`PT12M34S` → 754, `PT1H2M3S` → 3723, `PT45S` → 45; unparseable input raises); (2) duration buckets at every boundary (60, 61, 300, 301, 900, 901, 1800, 1801); (3) topic classification priority order (a title matching both `python` and `sql` keywords → `python`; `other` for a title matching nothing); (4) format classification (`tutorial` vs `explainer` vs `other`, `tutorial` wins on overlap); (5) KPI formulas on a hand-computed row (`views_per_day`, `engagement_rate`, `like_rate`, `comment_rate`, `views_per_subscriber`; missing like count → NaN engagement, never 0; `days_since_publish` minimum 1); (6) high-performer flag = top quartile of `views_per_day` on a constructed frame; (7) synthetic generation deterministic with seed 42 and n=200, 20 channels × 10 videos; (8) synthetic never overwrites the live cache and `*_synthetic.json` does not satisfy the cache check; (9) `--offline`/`--use-cache` runs without network; (10) committed CSV matches the published findings in README/insights (recompute one video's `engagement_rate` from the CSVs); (11) notebook `_find_root()` resolves correctly — **and the suite must pass both from the repo root and from inside the day folder** (Day 2 CI lesson: the test must exec the notebook namespace with `__file__` set to the notebook path, and the coder must run the full suite from both locations before handoff); (12) "Data from the YouTube Data API v3" attribution present in app + charts/README and the §4.3 descriptive-not-causal sentence present in README + app + insights. Replace the scaffold `tests/test_smoke.py` if present (delete it — do not keep both test files). |
| `outputs/insights_summary.md` | Plain-language findings (§2): one finding per §2 question (each citing its number from `videos.csv` and its chart), limitations (§3.1, §4.2–4.3), descriptive-not-causal sentence (§4.3). Does NOT carry the recommendation list — that lives in `outputs/recommendations.md` by this plan's choice (§5). |
| `outputs/recommendations.md` | **Recommendation list (this plan's choice — separate file, not folded into insights_summary.md):** every §4.4 recommendation with its `recommendation`, `evidence`, `sample_basis` and `caveat` fields, each number recomputed from `videos.csv`. No causal verbs anywhere. |
| `outputs/charts/*.png` | Exactly 4 PNGs (§7), regenerated by `src/make_charts.py`. No extra PNGs in this folder — CI asserts the count is exactly 4. |
| `screenshots/dashboard.png` | **REAL capture of the running Streamlit app** (full page), taken during the coder's smoke test — not a composite of the static charts. If a real capture is genuinely impossible, flag it explicitly as a composite in the handoff and in the README caption — do not silently pass a composite off as a screenshot. |
| `requirements.txt` | Pinned exact `==` versions, verified in the build venv (Python 3.12): `pandas`, `numpy`, `matplotlib`, `plotly`, `streamlit`, `requests`, `pytest`, **`jupyter==1.1.1` + `nbformat==5.11.1`** (required — CI executes the notebook via nbconvert). No new runtime dependency (brief §3.4); the exact pins are set at optimizer time from the venv that actually ran. |
| `pyproject.toml` | Ruff + black settings mirroring Day 3 exactly: `[tool.ruff] line-length = 88, target-version = "py312"`, `[tool.black] line-length = 88`, `[tool.pytest.ini_options] testpaths = ["tests"]`. Dev tools (ruff 0.17.4, black 26.10.1) are pinned once in the portfolio-root `requirements-dev.txt`, shared by all days. |
| `.gitignore` | Mirror Day 3 exactly: `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.venv/`, `venv/`, `.env`, `*.key`, `*.log`, `.streamlit/secrets.toml`, `.ipynb_checkpoints/`, plus `data/raw/*_synthetic.json` (synthetic fallback output is never committed; live `data/raw/*.json` IS committed). **Must NOT exclude `data/`** — diff `.gitignore` against this plan before sign-off (Day 1 lesson d). |
| `LICENSE` | MIT, keep as scaffolded. |

### Coder environment (Day 1/2/3 lessons applied)

- Create `.venv` with the pinned deps installed and hand it off working — the tester provisions nothing and must never install the project's own deps from scratch; if the venv is missing the tester reports "blocked: no venv".
- Run `black` + `ruff` **before** handoff (Day 1 lesson: lint left to the end cost a full fix cycle). `black --check` + `ruff check` must pass on `src/` and `tests/`.
- Capture the real `screenshots/dashboard.png` during the coder's own smoke test (fresh port 8502+, never assume 8501 is free; kill the server and verify the port is free afterwards — Day 1 lesson c).
- Run the full pytest suite **both from the repo root and from inside the day folder** before handoff (Day 2 CI lesson).
- One writer per file; build only what this plan lists; no extra web searches.

## 7. Charts (exactly 4 — CI asserts the count)

`python -m src.make_charts` regenerates exactly these 4 PNGs, offline from the
committed processed CSV. All 4 must be well-labelled (title, axes with units,
legend, source note), **drawn to scale** (no truncated or misleading axes)
and legible at dashboard size. Human-readable labels on every chart — no raw
slugs.

| # | Filename | Content |
|---|---|---|
| 1 | `01_views_by_topic.png` | **Median views per day by topic** — horizontal bars per topic group (§4.2) with median `views_per_day` labelled and n per bar, plus the overall-sample median as a dashed reference line, so which topics perform best — and on how much evidence — is visible at a glance. |
| 2 | `02_duration_vs_performance.png` | **Duration vs performance** — median `views_per_day` (bars) and median `engagement_rate` (line/markers on a second axis, clearly labelled) per duration bucket (§4.2), with n per bucket, so the length trade-off is comparable at a glance. Shorts (≤ 60 s) shown as their own bucket, not dropped. |
| 3 | `03_publish_time_heatmap.png` | **Publish-time heatmap** — median `views_per_day` by publish hour (UTC, 0–23, x-axis) and day of week (Mon–Sun, y-axis), annotated with n per cell where the cell is thin (n < 5 marked as such), with the caption that the channel audience timezone is unknown and the pattern is descriptive only (§4.2). |
| 4 | `04_engagement_scatter.png` | **Engagement scatter** — log10(view count) (x) vs `engagement_rate` % (y) for every video, coloured by high-performer status (top quartile `views_per_day` vs rest), with topic shown by marker shape or a faceted legend, so whether high performers also engage better — or just reach further — is visible at a glance. |

## 8. Success checklist (roadmap minimum success criteria — all must pass)

- [ ] Problem statement + audience written (§1, in README and this plan)
- [ ] Data source documented: provider, endpoints, the 5 queries, collection date (2026-11-08), licence/attribution ("Data from the YouTube Data API v3" + link to YouTube's Terms of Service), quota used, row counts — in `data/README.md` and `data/processed/data_source.json` (with the §3.3 source-field rule satisfied: live re-run or restored field before publishing)
- [ ] Repeatable prep steps documented (fetch → clean → KPIs → groupings → recommendations → charts, with `--offline` mode) + KPI/grouping definitions (§4) written down
- [ ] ≥2 well-labelled visualisations produced — Day 4 produces exactly 4 (§7), **drawn to scale and legible**, plus a functional dashboard: the Streamlit dashboard runs and renders (smoke gate, §9)
- [ ] Interpretation written (`outputs/insights_summary.md`, one finding per §2 question) + **evidence-cited recommendations** (`outputs/recommendations.md`, every recommendation with its numbers + caveat, zero causal verbs) — and all §4.6 targets pass (or each miss is reported and diagnosed, never tuned away)
- [ ] README with setup instructions, sample outputs (KPI table + chart thumbnails), and limitations
- [ ] No credentials / private records in the repo; no huge raw files committed (raw JSONs <1 MB each, <5 MB per day folder); `.gitignore` does not exclude `data/`
- [ ] One metric manually validated by hand and recorded in `data/README.md` (recompute one video's `engagement_rate` and `views_per_day` from the raw `videos` JSON, matching to the last digit)
- [ ] Pipeline runs end-to-end from a clean checkout (`pip install -r requirements.txt`, `python -m src.data_pipeline --offline`, `python -m src.make_charts`, `pytest tests/ -q`) — **pytest passing both from the repo root and from inside the day folder**
- [ ] Notebook runs top-to-bottom without errors (offline, via nbconvert, with `_find_root()`)
- [ ] Pinned dependencies in `requirements.txt`; `black --check` + `ruff check` clean
- [ ] Streamlit smoke gate passed: fresh port 8502+, HTTP 200 on `/` and on `/_stcore/health`, real `screenshots/dashboard.png` captured, server killed and port verified free
- [ ] Charts to scale and legible; frozen-tree check passed immediately before push (every file the READMEs reference exists on disk — charts, screenshot, CSVs, recommendations report)

## 9. Coder handoff checklist (reference — coder must satisfy all of these before the tester starts)

Per AGENTS.md / Day 1 retrospective, the coder hands off only when **all** of
the following hold; the tester verifies in the coder's venv and provisions nothing:

1. `.venv` exists with pinned deps installed (requirements.txt matches the venv that actually ran).
2. `black --check src tests` and `ruff check src tests` pass (exit 0).
3. `pytest tests/ -q` passes (≥7 tests, offline) **from the repo root AND from inside the day folder**.
4. `.gitignore` matches §6 (in particular: does NOT exclude `data/`; excludes only `data/raw/*_synthetic.json`).
5. `screenshots/dashboard.png` is a REAL capture of the running app (or explicitly flagged as a composite in the handoff + README caption).
6. `python -m src.make_charts` regenerates exactly 4 PNGs in `outputs/charts/` (offline, from committed CSVs); notebook executes end-to-end offline via nbconvert.
7. Every number in README / dashboard / notebook / insights matches `data/processed/videos.csv`, and every recommendation number matches `outputs/recommendations.md`.
8. `data/processed/data_source.json` `source` field is correct for the published data (§3.3) — re-run live or restore before handoff.
9. `src/app.py` uses `width='stretch'` throughout — no `use_container_width` anywhere in the tree.
10. No causal verbs in any recommendation; the §4.3 descriptive-not-causal sentence is in the README, app header, and insights summary.

**Tester smoke gate (mandatory, for the tester's reference):** start
`streamlit run src/app.py` on a fresh port (8502 or higher, never 8501);
confirm HTTP 200 on `/` and on `/_stcore/health` with a clean server log;
capture a full-page screenshot to `screenshots/dashboard.png`; kill the server
and verify the port is free; record port, HTTP statuses and screenshot size in
`test_report.md`.

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| YouTube 403 `quotaExceeded` / outage on fetch day | ≥ 2 s spacing, one 30 s retry on 5xx only, then cached → synthetic (§3.5); synthetic is labelled everywhere and re-fetched before publishing. June 2026 bucket split: coder's actual fetch is ground truth (§3.2). |
| `order=viewCount` used by habit | Brief §2.1 forbids it; this plan repeats the ban (§3.2); tester checks the fetch code. |
| Means used instead of medians | §4 mandates medians everywhere; tester validates on a hand-computed frame (§6, test 5). |
| Missing like/comment counts filled with 0 | §4.1 mandates NaN, never 0; tester validates (§6, test 5). |
| Keyword lists re-tuned after seeing results | §4.2/§4.6 forbid it: `other` > 30% is reported, not re-tuned; a miss is diagnosed, not tuned away. |
| Causal claims in recommendations | §4.4 format + checklist item 10: every recommendation cites numbers + caveat; no causal verbs; tester greps the wording. |
| Publish-hour pattern read as a prescription | §4.2 confound stated in plan, README, notebook, chart 03 caption and dashboard; channel timezone unknown. |
| `use_container_width` deprecation (Day 2 day-log lesson) | §6 mandates `width='stretch'` in `app.py`; handoff checklist item 9 greps for the deprecated call. |
| Offline run overwriting `data_source.json` source to `"cache"` (Day 2 day-log lesson) | §3.3 rule: re-run live or restore the field before publishing; handoff checklist item 8; publisher frozen-tree check includes it. |
| `.gitignore` silently dropping raw data (Day 1 lesson d) | §6 diff check at coder handoff; publisher frozen-tree check before push. |
| Screenshot going missing before push (Day 1 lesson) | Treat `screenshots/dashboard.png` as a checked deliverable; verify it exists at every handoff; publisher re-verifies immediately before pushing. |
| Notebook cwd trap (Day 1 lesson e) + Day 2 CI failure (test passed inside the day folder, failed from the repo root) | `_find_root()` from the notebook file's own location; notebook test execs with `__file__` set to the notebook path; full suite run from both locations (§6, test 11). |
| Dashboard crash invisible to pytest (Day 1 lesson b) | Mandatory Streamlit smoke gate (§9) + real screenshot. |
| Chart count drift (extra PNG breaks CI) | `make_charts.py` writes exactly the 4 files in §7 and no others; CI asserts count == 4. |
| API key leaked into code/logs/repo | Key comes only from the connector (§3.3); pipeline never logs it; tester checks for secrets. |

## 11. Brief-vs-plan differences

**No contradictions on data, sample, KPIs or validation.** This plan adopts
the brief's endpoints and parameters (§3.1, verbatim), the 5 queries (§3.1),
the quota budget ≈ 508 units (§3.2), the expected row counts 250 → ~200–240
→ ~180–230 (§3.2), the KPI definitions (§4.1, verbatim), the duration
buckets, topic/format keyword groupings and priority orders (§4.2,
verbatim), the top-quartile high-performer definition (§4.3), the
recommendation format (§4.4), the validation checks (§4.5), the synthetic
parameters (seed 42, n=200, §3.5), the licence tensions (§3.4) and the
out-of-scope ruling on comment sentiment (§4.2) without change. Additions
and choices made by the plan (not contradictions):

- **Recommendation output chosen:** a separate `outputs/recommendations.md`
  (the brief offered the recommendation format but fixed no file); the plan
  chooses the separate file so the plain-language findings note stays
  readable — mirroring Day 3's separate evaluation report.
- **Processed-file names fixed** where the brief left them to the plan:
  `videos.csv` (one row per video, §6 column list) and `data_source.json`
  (with `queries`, `max_results_per_query`, `video_count`,
  `channel_count`, `quota_units_used`, `api`, `top_up` fields).
- **Raw-file names fixed:** `search_<query-slug>.json` (one per query),
  `videos_details.json`, `channels_details.json`.
- **New module `src/youtube_kpi.py`** with fixed function signatures (§6)
  — the brief names no module; the pipeline module keeps the Day 2/3 shape.
- **Exact 4 chart filenames** (§7) and the ≥7-test list (§6), including the
  Day 2 CI lesson (suite must pass from the repo root AND inside the day
  folder).
- **Targets table (§4.6) added by the plan:** ≥180 final videos, ≥90%
  like-count presence, ≥80% subscriber-count presence, zero duplicate
  `videoId`s, 100% duration parse, engagement sanity 0.5–8%, `other` ≤ 30%,
  largest channel ≤ 20% — the brief states the underlying expectations but
  fixes no pass/fail numbers; these are the plan's fixed targets.
- **Fetch spacing:** the plan states ≥ 2 s between calls (the brief's
  verified polite-use rule, §1.6); this is stricter than a 1 s minimum and
  therefore satisfies it.
- **Day-log lessons applied:** `width='stretch'` (not `use_container_width`)
  in `app.py`; human-readable labels (no raw slugs) in the dashboard and
  charts; the `data_source.json` `"cache"` source-field rule (§3.3);
  `_find_root()` from the notebook's own location (Day 1 lesson e);
  `.gitignore` must NOT exclude `data/` (Day 1 lesson d); real screenshot
  at coder/tester handoff (not a composite); coder runs black+ruff before
  handoff; tester provisions nothing.
- **3 research questions** (§2) instead of Day 3's 3 anomaly questions,
  per this day's scope.

If the coder finds any of these unworkable, it goes back to the planner with
the exact point — the coder does not silently substitute a different
convention.

## 12. Build order (coder)

1. `.venv` + pinned deps → 2. `src/youtube_kpi.py` (pure functions:
   duration parsing → buckets → topic/format classification → KPIs →
   high-performer flag → recommendations, §6) → 3. `src/data_pipeline.py`
   (fetch the 5 searches → dedupe/filter → batched `videos`/`channels`
   calls → clean → KPIs → save; verify ~180–230 rows, report quota units
   used, dedupe/filter counts, and channel concentration) → 4. `pytest` on
   the KPI tests as they land (from both the repo root and the day folder)
   → 5. `src/make_charts.py` (exactly 4 PNGs) → 6.
   `notebooks/analysis.ipynb` (offline, `_find_root()`) → 7. `src/app.py` +
   smoke test + real `screenshots/dashboard.png` → 8. `README.md`,
   `data/README.md`, `outputs/insights_summary.md`,
   `outputs/recommendations.md` (numbers from the CSVs only) → 9. `black` +
   `ruff` + full `pytest` (both locations) + handoff checklist (§9).

**Token note:** this plan reuses the brief's verified numbers (endpoints,
queries, quota budget, KPI/grouping definitions, synthetic parameters)
verbatim — no re-verification, no extra searches. Later roles reuse the
tester's verified figures verbatim; nobody recomputes a finding from scratch
(a spot-check from the committed CSVs is the most that is ever needed).

## 13. Handoff (planner → coder)

**What was produced:** exactly one file —
`day-04-youtube-video-performance-analyzer/plan.md` (this file). No other
file was written or modified.

**Exact file tree the coder must build:** §5 — `README.md`, `LICENSE`,
`requirements.txt`, `pyproject.toml`, `.gitignore`, `data/README.md`,
`data/raw/` (5 search JSONs + `videos_details.json` +
`channels_details.json`), `data/processed/` (`videos.csv`,
`data_source.json`), `notebooks/analysis.ipynb`, `src/`
(`data_pipeline.py`, `youtube_kpi.py`, `make_charts.py`, `app.py`),
`outputs/` (`insights_summary.md`, `recommendations.md`, `charts/` with
exactly 4 PNGs), `screenshots/dashboard.png`, `tests/test_pipeline.py`.
Build only what §5 lists — no extra files.

**Known gaps:** no date-bounded sample is possible (helper limitation —
stated as a limitation, §3.1); search relevance ranking is undocumented;
the June 2026 quota-bucket split means the coder's actual fetch is the
ground truth on quota (§3.2); the `other` topic bucket may exceed 30%
(then report, don't re-tune, §4.2); subscriber counts are hidden for some
channels; comment sentiment is out of scope (no comments endpoint, §4.2);
no new dependency is added (brief §3.4), so pins are set at optimizer time
from the venv that actually ran.

**Coder's first step:** read `research_brief.md` + this `plan.md`, then
fetch the live data — the 5 searches in §3.1 (one per query, `maxResults=50`,
`order=relevance`), dedupe by `videoId`, then the batched `videos` and
`channels` calls — before writing any analysis code.
