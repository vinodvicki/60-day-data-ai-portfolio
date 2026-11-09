# Research Brief — Day 5: Social Media Sentiment Analyzer

**Project:** Day 5 of the 60-day Data + AI portfolio
**Roadmap entry (exact):** "DAY 05 | Social Media Sentiment Analyzer — Problem / analysis: Classify public comments by sentiment and extract recurring themes or complaints while documenting model limitations. GitHub deliverable: Sentiment trend chart and top-theme summary." Section context (Days 4–6, Social Media & Digital Marketing): Core skills: API integration, NLP, sentiment analysis, text visualization. Suggested data: YouTube Data API; public, permissioned comment and metadata datasets.
**Date written:** 2026-11-09 (researcher role, role 1 of 6)
**Status:** Research only — three lean verification probes were run (see §1.3). No live dataset was fetched. Fetching is the coder's job.

---

## 1. Verified source, endpoints, and parameters

### 1.1 Source

**YouTube Data API v3** — base URL `https://youtube.googleapis.com/youtube/v3` — via the `custom.youtube` connector (`~/workspace/custom-connectors/custom.youtube/`, helper `bin/youtube.py`). Read-only API-key auth: the key belongs to Victor's Google Cloud project `60-day-data-ai-portfolio` (project ID `day-data-ai-portfolio`), restricted to YouTube Data API v3 only, free tier, no payment method. **The key is held by the connector and is never put in any file, env var, log, command argument, or the repo.** The helper sends it as the `key` query parameter through the connector's surrogate exchange; redirects are refused by the helper.

This day reuses the Day 4 data source (YouTube) but a **new endpoint family** (comments, not videos). Nothing from Days 1–3 carries over except the workflow conventions (provenance, synthetic fallback, `.gitignore` rule — see §5). The video corpus is fixed in §2 from Day 4's processed frame (`day-04-.../data/processed/videos.csv`, 244 videos, fetched live 2026-11-08) — the IDs are public identifiers and the pipeline fetches fresh comment data live for exactly those IDs. No new search calls are needed.

### 1.2 Endpoints (verified from the official docs + live probe, 2026-11-09)

The helper was extended for this day (see §1.4) and now exposes six commands. Parameters below are what the helper actually sends — copy them, do not re-derive them.

| Command | API endpoint | Parameters sent by the helper | Cost |
|---|---|---|---|
| `search --query "..." --max-results N` | `GET /search` | `part=snippet`, `q=<query>`, `type=video`, `maxResults=N`, `order=relevance` | **100 units** |
| `videos --ids ID[,ID...]` | `GET /videos` | `part=snippet,statistics,contentDetails`, `id=<comma-separated, up to 50>` | **1 unit** |
| `channels --ids ID[,ID...]` | `GET /channels` | `part=snippet,statistics`, `id=<comma-separated, up to 50>` | **1 unit** |
| `playlist-items --playlist-id PL --max-results N` | `GET /playlistItems` | `part=snippet,contentDetails`, `playlistId=<id>`, `maxResults=N` | **1 unit** |
| `comment-threads --video-id ID --max-results N --order time\|relevance --page-token T --text-format plainText\|html` | `GET /commentThreads` | `part=snippet`, `videoId=<id>`, `maxResults=N` (1–100), `order=<order>`, `textFormat=<format>`, `pageToken=<token>` (only when given) | **1 unit** |
| `comments --parent-id ID --max-results N --page-token T --text-format plainText\|html` | `GET /comments` | `part=snippet`, `parentId=<id>`, `maxResults=N`, `textFormat=<format>`, `pageToken=<token>` (only when given) | **1 unit** |

Full invocations (the two new ones):

```text
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py comment-threads --video-id VIDEO_ID --max-results 100 --order time --text-format plainText
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py comment-threads --video-id VIDEO_ID --max-results 100 --order time --page-token NEXT_PAGE_TOKEN --text-format plainText
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py comments --parent-id COMMENT_ID --max-results 20 --text-format plainText
```

### 1.3 Verification probes (the lean probes — run 2026-11-09, all exit 0)

**Probe 1 — `comment-threads`, max-results 2, order=time, video `yZvFH7B6gKI`** (CareerFoundry "What Is Data Analytics?", Day 4 comment_count 970):

```text
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py comment-threads --video-id yZvFH7B6gKI --max-results 2 --order time --text-format plainText
```

- **Result:** exit 0, ~0.8 s. Response `kind: "youtube#commentThreadListResponse"`, `pageInfo: {totalResults: 2, resultsPerPage: 2}`, `nextPageToken` present, 2 items.
- **Items:** (1) the channel owner's pinned promo comment (`UgxdIrI-f6edGbmFlid4AaABAg`, "@careerfoundry", published `2021-03-25T13:15:16Z`, `totalReplyCount: 13`, text starts "Next Steps - Subscribe for our channel…"); (2) a viewer comment (`UgyOm0OPvF_DUbkiTyd4AaABAg`, "@BboyVReck", published `2026-11-07T02:08:14Z`, likeCount 0, "My CFO come up to me about this kind job role. 0 experience.").
- **Cost: 1 unit.**

**Probe 2 — same call, max-results 100** (to test `pageInfo.totalResults` and pagination):

- **Result:** exit 0. `pageInfo: {totalResults: 100, resultsPerPage: 100}`, 100 items, `nextPageToken` present. Oldest item `2021-03-25T13:15:16Z`, newest `2026-11-07T02:08:14Z`.
- **Finding — `pageInfo.totalResults` is unreliable: it echoed the page size (2, then 100), not the video's real comment total (970 per Day 4).** Never use it as a count; the pipeline paginates on `nextPageToken` only and counts rows itself.
- **Finding — pinned comments surface first even with `order=time`.** The 2021 channel-owner comment was item 1 of a time-ordered page. The pipeline must sort by `publishedAt` itself and must never trust response order. Channel-owner comments are excluded (§2.2) — the pinned promo comment is not audience sentiment.
- **Cost: 1 unit.**

**Probe 3 — `comments.list`, parentId `UgxdIrI-f6edGbmFlid4AaABAg` (the pinned thread, 13 replies), max-results 2:**

- **Result:** exit 0. Response `kind: "youtube#commentListResponse"`, 2 items (replies by @sunnygawande5283, 2021-07-07, and @saraho8134, 2021-08-26). Verified the endpoint works; the build does **not** fetch replies (§2.2), so this probe is verification only.
- **Cost: 1 unit.**

**Probe total: 3 units.** No further probe calls were made — the coder does the live fetch.

### 1.4 Response fields the coder will use

**`commentThreads` → `snippet.topLevelComment.snippet` (per thread):** `id` (comment/thread ID — the thread `id` equals the top-level comment `id`), `textDisplay` (with `textFormat=plainText` this equals `textOriginal`; use `textDisplay`), `textOriginal`, `authorDisplayName`, `authorChannelId.value`, `authorChannelUrl`, `likeCount` (int), `publishedAt` (ISO 8601 UTC), `updatedAt`, `canReply`, `viewerRating`. **`snippet` (thread level):** `channelId` (the video's channel), `videoId`, `totalReplyCount`, `canReply`, `isPublic`. With `part=snippet` only, no `replies` object is returned — replies are not fetched (§2.2).
**`commentThreads` → top level:** `nextPageToken` (absent on the last page), `pageInfo` (unreliable — see §1.3, ignore `totalResults`).
**`comments` → `snippet` (per reply):** same comment fields as above plus `parentId`. Not used by the build except as the documented fallback if the planner ever adds replies.

### 1.5 What the API does NOT offer (verified — do not assume otherwise)

- **No date filter.** `commentThreads.list` has **no** `publishedAfter` / `publishedBefore` parameter (checked against the official parameter table, 2026-11-09). A time-bounded sample is therefore impossible at the API level: the pipeline fetches newest-first (`order=time`) and filters by `publishedAt` **after** fetching (§2.2). Do not add date parameters to the helper for this endpoint — they do not exist.
- **No language filter.** There is no language parameter on `commentThreads.list`. Non-English comments are handled after fetching by the §3.4 heuristic, not by the API.
- **No sentiment, no search within a video's comments for this build.** `searchTerms` exists on the endpoint but the build does not use it (it would bias the sample toward keyword-matching comments).
- **`maxResults` caps at 100 per call** (asking for more silently returns 100 — verified by the probe returning exactly 100). Pagination via `pageToken` is required for more.
- **Quota note — conflicting documentation (open item, resolved in favour of the official docs page + the probe):** the official `commentThreads/list` docs page states quota cost **1 unit**; the generated client-library reference (googleapis.github.io) says "The snippet part has a quota cost of 2 units". The official docs page is authoritative, the probe succeeded, and the coder's actual fetch is the ground truth — if a `quotaExceeded` appears far earlier than the §1.6 budget predicts, stop and check the Google Cloud Console quota page instead of retrying.
- **Comments can be disabled per video.** If a video has comments disabled, `commentThreads.list` returns an empty `items` list (or a 403 `commentsDisabled` — the exact behaviour is not probed; the pipeline treats empty items as "0 comments fetched, record and continue" and a 403 `commentsDisabled` the same way, after one check that the video ID is correct). The 12-video corpus (§2.1) was chosen from videos with live comment counts in Day 4, so disabled comments are not expected — but the pipeline must not crash on it.
- **Read-only, public data only.** No posting, no private data (API key, no OAuth scopes). Timeout 30 s per request (helper). Redirects refused.

### 1.6 Quota and rate limits (verified)

- **Daily quota: 10,000 units/day, free tier, resets at midnight Pacific Time.** `commentThreads.list` = 1 unit; `comments.list` = 1 unit (official docs + connector doc). Search = 100 units (not used by this build).
- **Polite-use rule for the coder:** ≥ 2 s between calls; one retry after 30 s on HTTP 5xx only; **no retry on 403 `quotaExceeded`** — stop and fall back (§5). Never hammer the API.
- **Quota budget for the planned build (§2):** 12 videos × up to 3 pages × 1 unit = **≤ 36 units** (plus the researcher's 3-unit probe = day total ≤ 39 units, < 0.5% of the daily quota). There is ample headroom for one full re-run if a call fails; there is no headroom for exploratory extra calls, so the coder runs exactly the §2 design.
- **June 2026 quota change (open item, same as Day 4):** Google split the daily quota into separate buckets from 2026-06-01. The 10,000-unit framing above is the connector doc's figure and the probes succeeded within it, so the build proceeds on that basis — but the coder's actual fetch is the ground truth (see §1.5 quota note).

### 1.7 Error handling

| Error | Meaning | Coder action |
|---|---|---|
| `400 keyInvalid` | Stored key wrong or project misconfigured | Stop. Do not retry. Report as blocked; key is the connector's business, never to be pasted or hard-coded anywhere. |
| `403 quotaExceeded` | Daily quota hit | Stop immediately. No retry. Fall back to cache, then synthetic (§5). |
| `403 accessNotConfigured` | YouTube Data API v3 not enabled on the project | Stop. Report as blocked (it was enabled 2026-11-07 and the probes succeeded, so this is not expected). |
| `403 commentsDisabled` (or empty `items`) | Comments disabled on that video, or none returned | Record 0 fetched for that video, continue with the other 11. Do not treat as a build failure unless ≥ 4 videos return 0. |
| `403` other (e.g. `forbidden`) | Request rejected for another reason | Check the request first (video ID well-formed, `maxResults` ≤ 100); one careful retry only if the request was malformed. |
| HTTP 5xx / timeout | Transient server/network failure | One retry after 30 s, then fall back (§5). |
| Empty `items` on a page with `nextPageToken` present | API quirk | Stop paging that video, count what was fetched, continue — this is not an error. |

The helper exits non-zero with `HTTP {code} from {path}: {body[:500]}` — the pipeline must catch that, log the code/reason, and follow the table above. **Never log the API key** (the helper never prints it; keep it that way).

---

## 2. Sample strategy (what the coder fetches — bounded, reproducible)

### 2.1 Corpus — fixed list of 12 videos (do not invent, add, or swap any video)

Selected 2026-11-09 from Day 4's processed frame (`day-04-.../data/processed/videos.csv`, 244 videos) by a fixed rule written before seeing any comment text: **top 2 videos by `comment_count` within each Day 4 topic group (`ai_ml`, `sql`, `python`, `career`) + the top `bi_viz` video + the next 3 highest overall not already selected** — capped at 12, max 1 video per channel (the rule produced 12 distinct channels), known non-English titles excluded (the Spanish SQL course `DFg1V-rO6Pg` ranked below the cut; the language filter in §3.4 is the backstop, not the selector).

| # | Video ID | Title (short) | Channel | Day 4 topic | Day 4 comment_count | Published |
|---|---|---|---|---|---|---|
| 1 | `fa8k8IQ1_X0` | A.I. ‐ Humanity's Final Invention? | Kurzgesagt – In a Nutshell | ai_ml | 21,781 | 2024-08-06 |
| 2 | `5KmopXwjXik` | Godfather of AI WARNS: "You Have No Idea What's Coming" | The Diary Of A CEO Clips | ai_ml | 17,810 | 2025-09-27 |
| 3 | `HXV3zeQKqGY` | SQL Tutorial - Full Database Course for Beginners | freeCodeCamp.org | sql | 11,938 | 2018-07-02 |
| 4 | `7S_tz1z_5bA` | SQL Course for Beginners [Full Course] | Programming with Mosh | sql | 10,826 | 2019-03-20 |
| 5 | `aircAruvnKk` | But what is a neural network? \| Deep learning chapter 1 | 3Blue1Brown | python | 9,493 | 2017-10-05 |
| 6 | `SSKVgrwhzus` | SQL Full Course for Beginners (30 Hours) – From Zero to Hero | Data with Baraa | python | 8,864 | 2025-03-27 |
| 7 | `t2oOFs4WgI0` | Beyond the Numbers: A Data Analyst Journey \| Anna Leach \| TEDxPSU | TEDx Talks | career | 4,450 | 2018-03-02 |
| 8 | `yZvFH7B6gKI` | What Is Data Analytics? - An Introduction (Full Guide) | CareerFoundry | career | 970 | 2021-03-25 |
| 9 | `qrbf9DtR3_c` | Excel Data Analysis Full Course Tutorial (7+ Hours) | Learn Skills Daily | bi_viz | 1,209 | 2024-05-31 |
| 10 | `aZ5EsdnpLMI` | Artificial Intelligence \| 60 Minutes Full Episodes | 60 Minutes | ai_ml | 8,101 | 2023-12-30 |
| 11 | `pCJ15nGFgVg` | Excel for Data Analytics - Full Course for Beginners | Luke Barousse | python | 4,818 | 2024-10-14 |
| 12 | `9f-GarcDY58` | Machine Learning Full Course \| Learn Machine Learning | Simplilearn | python | 4,624 | 2019-08-30 |

Corpus facts (computed from Day 4's frame, 2026-11-09): 12 videos, 12 distinct channels (max 1 per channel), topics python 4 / ai_ml 3 / sql 2 / career 2 / bi_viz 1, video publish range 2017-10-05 → 2025-09-27, combined Day 4 `comment_count` **104,884**. The corpus is a defined set of high-comment-volume data/AI videos — it is **not** a random sample of YouTube comments, and no finding may be generalised beyond "comments on these 12 videos". Video 8 (`yZvFH7B6gKI`) is the probe video; its inclusion is by the fixed rule (2nd career video by comment count), not because it was probed.

### 2.2 Fetch rules

- **Exactly 12 `comment-threads` call sequences** (one per video in §2.1), `maxResults=100`, `order=time` (newest first), `textFormat=plainText`, `part=snippet` (top-level comments only — **no `replies` part, no `comments.list` calls**: replies are out of scope; a thread's reply count is recorded but reply text is not fetched).
- **Pagination per video:** follow `nextPageToken` for **up to 3 pages (300 threads)** per video, stopping early when (a) no `nextPageToken` is returned, or (b) the **oldest comment on the page is older than the window start (2025-11-09)** — there is no point paging further back once the page is entirely outside the window. Never fetch a 4th page for any video.
- **Time window (applied AFTER fetching, on `publishedAt`):** **2025-11-09 → 2026-11-09** (12 months ending on the fetch date). Comments outside the window are dropped from the analysed frame and counted. The window is a post-fetch filter, not an API parameter (§1.5).
- **Deduplicate** by comment `id` across pages (overlap is not expected with `pageToken` paging, but dedupe anyway and record any duplicates dropped).
- **Filter (in this order, each step counted):** (1) drop threads whose top-level comment's `authorChannelId` equals the video's channel ID (channel-owner comments, incl. pinned promos — not audience sentiment); (2) drop empty/whitespace-only text; (3) drop comments outside the window; (4) drop non-English comments per the §3.4 heuristic (counted separately, never silently).
- **Expected row counts (coder must verify the actuals and report them; do not assume these):** 12 videos × up to 300 threads = **≤ 3,600 fetched threads** → after window + owner + language filtering **~1,500–2,500 analysed comments** (the window is the big reducer: the newest 300 comments on a high-volume video may cover only weeks). If the final analysed count lands below **800**, the coder reports it as a thin-sample caveat in the README; the analysis still runs, but monthly trend cells with n < 30 are flagged thin and the theme list is labelled thin-sample. If any single video contributes > 40% of the final frame, the dashboard must say so — the findings would be dominated by one video's audience.
- **Polite use:** ≥ 2 s between calls; one retry after 30 s on HTTP 5xx / timeout only; no retry on 403 `quotaExceeded` (§1.7).
- **Raw size guard:** one raw file per video (`data/raw/comments_<video_id>.json`, verbatim API responses for that video's pages, concatenated `items` with page boundaries recorded). At ~0.8–1 KB per thread × ≤ 300 threads, each file is ≤ ~300 KB and the raw total is ≤ ~3.6 MB — inside the 5 MB/day rule and the 1 MB/file guideline. If a raw file would exceed 1 MB, the pipeline must stop paging that video earlier and record the truncation (do not silently write an oversize file).

### 2.3 Why this design (and what was rejected)

- **Fixed 12-video corpus from Day 4's frame** is deterministic and reproducible (no new search calls, no relevance-ranking drift between runs, 0 search quota) and reuses verified video metadata (topics, comment counts) instead of re-deriving them. The cost is corpus bias: these are high-comment-volume videos, so the comment sample skews toward videos whose audiences comment a lot. That bias is stated in every output.
- **`order=time` (newest first) + post-fetch window filter** is the only way to get a time-bounded sample (§1.5 — no API date filter). The trade-off: the window is filled unevenly across videos (high-volume videos contribute mostly recent weeks; quiet videos contribute the whole year). The trend chart therefore shows monthly sentiment share **with n per month** so thin months are visible, never a smooth line that hides its evidence.
- **Top-level comments only, no replies:** replies are conversational (often "@user I agree") and would need `comments.list` + `parentId` pagination per thread — a large call count for text that adds little theme signal. Stated as scope, not an oversight.
- **Rejected — `order=relevance`:** returns YouTube's top-ranked comments (most-liked, most-replied), which over-represents extreme/polarised comments and destroys the time ordering the trend chart needs.
- **Rejected — fresh searches to pick videos:** costs 100 units per search, re-introduces relevance-ranking drift, and duplicates Day 4's verified video selection for no analytical gain.
- **Rejected — `allThreadsRelatedToChannelId`:** returns comments across a whole channel plus channel discussion-tab comments — wrong unit of analysis (this day is about comments *on videos*, grouped by video topic).

---

## 3. Method — sentiment model, themes, metrics, validation

All metrics are computed on the cleaned comment frame (one row per analysed comment). **Sentiment here is a model output, not ground truth** — the dashboard, notebook, insights summary and README must all say so, and the validation in §3.5 is the evidence for how far the model can be trusted.

### 3.1 Sentiment model (fixed — the planner/coder must not substitute a different model without a plan change)

**An original, transparent, rule-based lexicon scorer written for this project** (in `src/sentiment.py`). It is *VADER-style* in shape only — a word-polarity sum with negation and intensifier handling, normalised to [−1, +1] — but **the lexicon is authored for this project, not copied**: no VADER lexicon file, no NLTK download, no pretrained model, no paid API, no copied project code. Every word, weight and rule lives in the code with a comment saying what it does, so any reader can audit the full model in one file.

| Component | Rule (implement verbatim) |
|---|---|
| Lexicon | Two word lists authored in the code: **positive words** (e.g. great, excellent, love, amazing, helpful, clear, easy, thanks, brilliant, awesome, perfect, best, fantastic, useful, good, nice, enjoy, learn, beautiful, wonderful) and **negative words** (e.g. bad, terrible, awful, hate, worst, boring, confusing, useless, wrong, slow, broken, disappointing, horrible, annoying, stupid, dumb, waste, poor, unclear, hard). Each word carries polarity **+1 / −1**; a small explicit set of strong words (**love, amazing, brilliant, excellent, fantastic, perfect, hate, terrible, awful, horrible, worst, useless**) carries **±2**. The lists must be written out in full in `src/sentiment.py` (target ~100–150 words per side) — the tester verifies the lists are present and counts them. |
| Tokenisation | Lower-case, split on non-letters (keep apostrophes inside words, e.g. `don't` stays one token), strip URLs and @mentions before scoring (they carry no sentiment). |
| Negation | `not, no, never, n't, don't, doesn't, didn't, can't, won't, isn't, wasn't, aren't, couldn't, shouldn't` flip the polarity of the **next 3 scored words** (a token window of 3). Double negation is not handled — documented as a limitation. |
| Intensifiers | `very, extremely, so, really, absolutely, totally, super, incredibly, truly, quite, pretty` multiply the next scored word's polarity by **1.5**. |
| Emoji | A small explicit map in the code: positive `😍 😂 👍 ❤️ 🔥 🙌 👏 😊 🎉 💯` (+1 each, max +2 per comment); negative `😡 👎 😢 💩 🤮 😤 😠` (−1 each, max −2 per comment). Documented as a crude signal, not a full emoji model. |
| Exclamation | +0.25 per `!` in the text, capped at +0.5, applied to the raw sum **only if the sum is already positive** (excitement amplifies praise; it does not turn a complaint positive). |
| Normalisation | `compound = s / sqrt(s² + 15)` where `s` is the raw summed score (the same normaliser shape VADER publishes — a standard saturating function, documented in the code, not copied code). Result in (−1, +1). |
| Classification | `compound ≥ +0.05` → **positive**; `compound ≤ −0.05` → **negative**; otherwise **neutral** (the ±0.05 thresholds VADER publishes — standard, documented in the code). |
| Output columns | `sentiment_score` (compound, 4 dp), `sentiment` (positive / neutral / negative), plus `scored_words` (count of lexicon words matched — 0 means the comment carried no lexicon signal and is neutral by default, which is itself a finding). |

**What the model cannot do (limitations to document prominently — the roadmap requires it):** no sarcasm/irony detection ("great, another 30-hour course 🙄" scores positive); no context ("not bad" is handled by negation, but "this is not the best tutorial, the other one is" is not); no slang/neologism coverage beyond the authored lists; short comments ("ok", "lol", "first") usually score neutral by default, not by meaning; non-English is excluded, not translated; emoji handling is a tiny explicit map; the lexicon was authored before seeing the comments and must **not** be tuned after seeing validation results (tuning on the validation set would invalidate it — if a word is missing, report it as a limitation, do not add it).

### 3.2 Themes (fixed — deterministic, no clustering model)

Two complementary, fully transparent theme methods (both reported; neither is a black-box topic model):

1. **Keyword themes (fixed lists, authored before seeing the data).** Each comment is assigned **up to 2** themes by keyword match on lower-cased text; a comment matching none is `other`. Lists (implement verbatim in `src/sentiment.py`, `classify_themes`):

| Theme | Keywords (match any) |
|---|---|
| `praise` | thank, thanks, great, amazing, awesome, excellent, love, brilliant, fantastic, wonderful, best, perfect, helpful, useful, clear, easy to follow, well explained, good job, nice, beautiful |
| `tutorial_quality` | explained, explanation, clear, unclear, confusing, confused, understand, understood, step by step, detailed, thorough, beginner friendly, pace, too fast, too slow, rushed |
| `requests` | please make, more videos, next video, part 2, tutorial on, cover, request, want more, do a video, can you make |
| `career` | job, career, interview, salary, switch, beginner, start, learning path, roadmap, get a job, hired |
| `criticism` | wrong, incorrect, mistake, error, outdated, misleading, bad, terrible, boring, waste, useless, disappointed, poor |
| `questions` | how do, how to, what is, why, question, can anyone, does anyone, help me, stuck, error (in the sense of a problem the commenter hit — overlaps `criticism` by design; `questions` wins only when the text contains a `?`) |
| `audio_video` | audio, sound, voice, volume, quality, video quality, blurry, captions, subtitles, accent |
| `price_cost` | price, cost, expensive, free, paid, worth, money, course fee |
| `humor` | lol, haha, funny, 😂, joke, hilarious |
| `other` | no keyword match |

   Priority note: `questions` requires a `?` in the text (else it is not a question); `criticism` and `tutorial_quality` may co-occur with `praise` on the same comment — up to 2 themes are kept, in the order above. If `other` exceeds 40% of the analysed frame, the theme lists are too narrow — **report it, do not silently re-tune the keywords after seeing results**.
2. **Top words / bigrams (data-driven).** After stopword removal (a fixed stopword list in the code, ~80 common English words + `video, youtube, channel, tutorial, course, like, just, really, get, got, one, much, many, also, even, still, way, thing, things, lot`), count unigrams and bigrams separately for positive, negative and neutral comments; report the top 20 of each. This is the check on whether the fixed themes missed a recurring topic — if a bigram dominates that no theme covers, it is reported as an unthemed finding, not folded into a theme list after the fact.

### 3.3 Metrics / KPIs (definitions fixed — the planner/coder must not redefine them)

| Metric | Formula | Notes |
|---|---|---|
| `comment_count_analysed` | Rows in `comments.csv` after §2.2 filtering | The headline n. |
| `sentiment_share` | Share of analysed comments per class (positive / neutral / negative) | Overall and per month, per video, per topic. Always shown with n. |
| `mean_compound` | Mean `sentiment_score` per group | Descriptive only; the median is also reported (scores are bounded and skewed). |
| `positive_rate` / `negative_rate` | Positive (negative) comments / analysed comments in the group | The trend-chart quantities, monthly. |
| `theme_count` / `theme_share` | Comments carrying a theme / analysed comments (a comment can carry 2 themes, so theme shares sum to > 100% — state this wherever themes are shown) | Per theme, overall and split by sentiment class. |
| `comments_per_video` | Analysed comments per video | Plus each video's share of the frame (§2.2 concentration rule). |
| `monthly_n` | Analysed comments per calendar month in the window | Trend cells with n < 30 are flagged thin. |
| `like_count` (comment) | `snippet.likeCount` (int) | Reported as a distribution (median likes per sentiment class) — do not use likes as a sentiment signal. |
| `scored_words` | Lexicon words matched per comment | Share of comments with 0 scored words is a model-coverage finding. |
| `validation_*` | §3.5 — accuracy, per-class precision/recall/F1, confusion matrix | On the human-labelled sample only, never on the full frame. |

**Use shares and medians for every comparison** — comment counts per video are heavily skewed and a single viral video would dominate any mean. No causal claims: a theme (e.g. "pace complaints cluster on long courses") is reported as *"in these comments, …"* — never "long courses cause complaints".

### 3.4 Language filter (heuristic, documented)

No language parameter exists on the endpoint (§1.5), so non-English comments are identified after fetching: strip emoji/URLs/mentions, take the alphabetic characters, and if **> 20% of letters are non-Latin** (Unicode script check via `unicodedata`, stdlib only), mark the comment `language_flag = "non_latin"` and exclude it from sentiment scoring (it is counted in `data_source.json` and `data/README.md`, and its video/topic/month are still recorded in the raw frame for audit). This is a crude heuristic, not a language identifier: it will miss non-English comments written in Latin script (e.g. Spanish, French) — those will mostly score neutral (no lexicon match) and inflate the neutral share, which is a stated limitation, not a hidden one. No new dependency (`langdetect` etc.) is added for this.

### 3.5 Validation — human-labelled sample (the credibility core of this day)

There is no labelled YouTube-comment sentiment dataset in this project, so the coder/tester creates one:

- **Sample:** stratified random sample of **120 comments** from the analysed frame — **40 per predicted class** (positive / neutral / negative), sampled with `random.Random(42)` so it is reproducible. Sampled *after* the pipeline runs, from `comments.csv`.
- **Labelling:** a human (the coder, then independently spot-checked by the tester on 30 of the 120) reads each comment's text **without seeing the predicted label** and assigns `positive / neutral / negative` by the fixed rubric: positive = the commenter expresses approval, enjoyment, gratitude or praise; negative = disapproval, frustration, complaint or criticism; neutral = factual, a question with no evaluative tone, or no discernible sentiment. Sarcasm is labelled by *intended* sentiment where it is unmistakable, and flagged in a `notes` column. The labels live in `data/processed/validation_labels.csv` (`comment_id, human_label, notes`) — committed, so the evaluation is reproducible.
- **Reporting:** confusion matrix (3×3), per-class precision/recall/F1, overall accuracy, macro-F1 — computed by the pipeline from `validation_labels.csv` + `comments.csv` and shown in chart 04, the notebook, the dashboard and the insights summary. **No pass threshold is set in advance** — the deliverable is the honest measurement, whatever it is. A lexicon baseline on noisy YouTube comments is expected to land well below a trained model; if macro-F1 is under 0.60 the README must say plainly that the model is a weak baseline and must not be used for decisions. **The lexicon must not be tuned after seeing the validation results** (§3.1) — tuning on the validation set would invalidate the measurement.
- **Tester hand-validation (mandatory, separate from the 120):** the tester recomputes **one** comment's `sentiment_score` by hand from the lexicon rules in §3.1 and matches `comments.csv` to the last digit; recorded in `data/README.md` with the comment ID and the hand-computed number.

### 3.6 What "good" looks like — targets table

| Metric | Target |
|---|---|
| Analysed comments in `comments.csv` | **≥ 800** (expected ~1,500–2,500; < 800 = thin-sample caveat, §2.2) |
| Videos contributing | **≥ 10 of 12** with ≥ 20 analysed comments each (else report which videos under-delivered and why) |
| Monthly trend coverage | **≥ 8 of 12 months** with n ≥ 30 (else flag thin months on the chart) |
| Validation sample | **120 labelled** (40 per predicted class), labels committed, P/R/F1 per class reported |
| Model coverage | Share of comments with 0 scored words reported; if > 25%, say so prominently |
| Theme coverage | `other` theme share **≤ 40%** (if above, report — do not re-tune) |
| Concentration | Largest single video **≤ 40%** of the frame (if above, dashboard says so) |
| Charts | Exactly 4 PNGs (§7 of the plan), drawn to scale, legible, source-noted |
| Limitations | §3.1 limitations + §1.5 API limits stated in README, dashboard, notebook and insights summary — **zero** presentation of sentiment as ground truth |

If a target is missed, the correct response is to report the miss and diagnose it — **not** to re-tune the lexicon, theme lists, buckets, or thresholds after seeing the results. The model, themes and window are fixed in this brief before the fetch runs.

**Conventions the coder must not re-decide:** lexicon word lists + weights + negation window (3) + intensifier (×1.5) + normaliser `s / sqrt(s² + 15)` + thresholds (±0.05) per §3.1; theme lists per §3.2; window 2025-11-09 → 2026-11-09; top-level comments only; `order=time`; max 3 pages per video; owner comments excluded; non-Latin heuristic per §3.4; validation sample 120 (40/class, seed 42). If any of these is unworkable, send it back to the planner with the exact point — do not silently substitute a different convention.

---

## 4. Deliverable shape (for the planner — the roadmap's two artefacts, plus the portfolio pattern)

- **Sentiment trend chart** (roadmap): monthly positive/neutral/negative shares with n per month — chart 01 (§7 of the plan).
- **Top-theme summary** (roadmap): theme counts + shares, split by sentiment, with example short excerpts per theme (≤ 3 per theme, truncated to 120 chars, no author names shown in the summary) — chart 03 + `outputs/themes_summary.md` (this plan's choice — a separate file so the findings note stays readable).
- **Portfolio pattern (Days 1–4):** `src/data_pipeline.py`, `src/sentiment.py` (pure model — no I/O, no network), `src/make_charts.py` (exactly 4 PNGs), `src/app.py` (Streamlit dashboard), `notebooks/analysis.ipynb`, `tests/test_pipeline.py`, `data/raw/comments_<video_id>.json`, `data/processed/comments.csv` + `data_source.json` + `validation_labels.csv`, `outputs/insights_summary.md` + `outputs/themes_summary.md`, `README.md`, `data/README.md`, `requirements.txt` (pinned), `pyproject.toml`, `.gitignore` (must NOT exclude `data/`).

---

## 5. Fallback parameters, licence, and open conflicts

### 5.1 Synthetic fallback (same conventions as Days 1–4, new parameters for comments)

Only if the live fetch fails **and** no cache exists (`data/raw/comments_*.json` in this day folder). Deterministic, **seed 42**:

| Field | Synthetic rule |
|---|---|
| `n` | **1,800 synthetic comments** across the same 12 video IDs (150 per video, spread over the window 2025-11-09 → 2026-11-09) |
| `text` | Assembled from fixed template lists per sentiment class, so the lexicon scores them as designed: positive templates ("This tutorial is amazing, thank you so much!", "Great explanation, finally I understand it", "Best video on this topic, really helpful"), neutral templates ("What software is used in this video?", "Can anyone explain the part at 5 minutes?", "Watching this in 2026"), negative templates ("This is so confusing and boring", "Terrible audio, I could not follow anything", "Worst tutorial, full of mistakes") — each template used with small variations (video/topic word swaps), recorded in the code |
| `sentiment mix` | 45% positive / 35% neutral / 20% negative by construction (the templates are chosen to score that way — verify after generation and report the actuals) |
| `like_count` | `U(0, 50)` for neutral, `U(0, 200)` for positive/negative (rounded) |
| `published_at` | Uniform over the window |
| `author` | "Synthetic Commenter NN" (no real display names) |

Output goes **only** to `data/raw/*_synthetic.json` — it must never overwrite the live cache. `data/processed/data_source.json` records `synthetic: true` + `seed: 42`. All downstream outputs are labelled SYNTHETIC. Synthetic data follows the same schema as live data (same columns, §3.3) so the pipeline, notebook, and dashboard run unchanged. Note: synthetic sentiment is uniform by construction, so on synthetic data the trend/theme findings have no interpretation — state this in the README, notebook, and insights summary if the synthetic path is used.

### 5.2 Cache reuse note

There is no prior comment cache — Day 5 is the first comments day. A cache fallback is only valid if a Day 5 fetch has previously succeeded and written `data/raw/` files in the Day 5 folder. Do **not** reuse any other day's data — the source differs entirely (Day 4 fetched video metadata, not comments).

### 5.3 Data provenance (Day 3 plan §3 conventions, carried over)

- `data/README.md` (coder writes it) records: provider, endpoints used, the 12-video corpus (§2.1, with the selection rule), access date (2026-11-09), quota units used, row counts (fetched → window/owner/language filtered → analysed, with each filter's count), video concentration, the licence/attribution note (§5.5) + the tensions stated honestly (§5.4), and the hand-validated metric (§3.5). `data/processed/data_source.json` records `source` (`"live"`, `"cache"` or `"synthetic"`), `generated_at_utc`, `synthetic` (bool), `seed` (`null` for live data, `42` for synthetic), plus `video_ids` (the 12 IDs), `window_start` / `window_end`, `max_pages_per_video` (3), `comment_count_fetched`, `comment_count_analysed`, `quota_units_used` (best estimate), `api` (`"youtube-data-api-v3"`), and `filters` (counts per §2.2 step).
- **Data-source field rule (Day 2 day-log lesson — mandatory):** an offline pipeline run (`--offline` / `--use-cache`) overwrites `data_source.json`'s `source` field to `"cache"`. Before publishing, the coder/optimizer must either **re-run the pipeline live** (restoring `"live"`) or **restore the field by hand with the true value and record the correction** in `data/README.md`. A published `data_source.json` that says `"cache"` when the data was in fact fetched live is a defect.
- **Data-commit rule (from Day 1):** small raw data IS committed — files under 1 MB each, under 5 MB per day folder — because the raw files are the provenance record. **`.gitignore` must NOT exclude `data/`.** Synthetic fallback output goes to `data/raw/*_synthetic.json` and is git-ignored; it must never overwrite the live cache. `python3 src/data_pipeline.py --offline` / `--use-cache` runs from the committed cache with no network.
- **Key rule:** the API key comes only from the `custom.youtube` connector. No `.env` file, no key in code, no key in any committed file, no key in logs.

### 5.4 Open conflicts / gaps (for the planner — mandatory resolution order)

1. **Quota cost discrepancy (resolve first, at build time).** Official docs page: 1 unit per `commentThreads.list` call; generated client-library reference: "snippet part has a quota cost of 2 units". Resolution order: (a) run the §2 design as written; (b) if `quotaExceeded` appears far earlier than the ~36-unit budget predicts, stop, check the Google Cloud Console quota page for the bucket breakdown, and report the actual bucket limits — do not retry or add calls. (Same June 2026 quota-bucket caveat as Day 4, §1.6.)
2. **Comment text is user-generated content (record honestly).** The raw JSONs contain public comments verbatim, including display names. They are a dated one-time snapshot (2026-11-09) committed as the provenance record, following the Days 1–4 convention; they are not re-served by a live service and the dashboard shows only aggregates plus short excerpts (≤ 120 chars, ≤ 3 per theme, no author names in the summary). No YouTube page found states explicitly whether committing verbatim comment text to a public GitHub repo counts as redistribution, so this is unresolved and no legal certainty is claimed. State the snapshot date and the tension in `data/README.md`. (Same treatment as Day 4's §5.4 item 3, extended from video metadata to comment text.)
3. **Derived-metrics tension (same as Day 4, carried over).** Sentiment scores and theme assignments are computed from API data by basic arithmetic/rule matching for an offline educational analysis, not a service offering metrics to users; the dashboard shows the underlying counts next to every derived rate. No legal certainty is claimed; `data/README.md` states the tension honestly.
4. **No API date filter / no language filter** (§1.5). The window and the language heuristic are post-fetch, with the uneven-coverage and Latin-script limitations stated in every output — not worked around with extra calls.
5. **`pageInfo.totalResults` is unreliable** (§1.3) — never report it; count rows from the fetched items.
6. **Pinned/owner comments surface first even with `order=time`** (§1.3) — the pipeline sorts by `publishedAt` and excludes owner comments; do not trust response order.
7. **Sentiment is a model output, not ground truth** (§3.1, §3.5). The lexicon is a weak baseline by design; the validation sample is the evidence. No claim in any output may present a sentiment share as "how viewers feel" without the "as classified by our rule-based model" qualifier and the validation numbers beside it.
8. **Dependency:** none new (§3.1 — stdlib + the Day 1–4 stack: pandas, NumPy, matplotlib, Plotly, Streamlit). If the planner adds one, it must be pinned and justified in the plan.

### 5.5 Licence / attribution

- Data is public YouTube comment text and metadata fetched under the **YouTube API Services Terms of Service and Developer Policies** (checked 2026-11-09). Attribution is required: include on the dashboard and in the repo README, legible: **"Data from the YouTube Data API v3"** with a link to YouTube's Terms of Service (`https://www.youtube.com/t/terms`), per the Developer Policies requirement that API clients display a link to YouTube's Terms of Service.
- Do not redistribute raw bulk data or re-host the API. Cache the fetched responses locally for the project only (§5.3, §5.4 item 2).
- Only public metadata is used — no user data beyond public comment text/display names, no private data. The API key has no OAuth scopes.
- Code in this repo is MIT (see `LICENSE`); YouTube data is under separate YouTube terms, not MIT.
- **No copying code or tutorials from the web.** All code is Victor's own original work, written from this brief and the plan. The sentiment lexicon is authored for this project (§3.1); the normaliser shape and ±0.05 thresholds are standard published VADER conventions, documented as such, not copied code.

---

## Handoff (researcher → planner)

**What was produced:** exactly one file — `day-05-social-media-sentiment-analyzer/research_brief.md` (this file) — plus a small, scoped extension to the shared YouTube helper (`~/workspace/custom-connectors/custom.youtube/bin/youtube.py`: two new subcommands, `comment-threads` and `comments`, each with `--page-token` support; the helper's own usage text updated). Three verification probes were run; no live dataset was fetched; no other file was written.

**Verified numbers:**
- Probe 1 (2026-11-09): `comment-threads --video-id yZvFH7B6gKI --max-results 2 --order time` → exit 0, `youtube#commentThreadListResponse`, 2 items (pinned owner comment 2021-03-25 + viewer comment 2026-11-07), `nextPageToken` present, cost **1 unit**.
- Probe 2: same call, `--max-results 100` → exit 0, 100 items, `nextPageToken` present, dates 2021-03-25 → 2026-11-07; `pageInfo.totalResults` echoed the page size (2, then 100) — **unreliable, never use as a count**; pinned comment surfaces first even with `order=time`. Cost **1 unit**.
- Probe 3: `comments --parent-id UgxdIrI-f6edGbmFlid4AaABAg --max-results 2` → exit 0, `youtube#commentListResponse`, 2 replies. Cost **1 unit**. (Verification only — replies are out of scope for the build.)
- Probe total: **3 units**.
- Quota budget for the build: 12 videos × up to 3 pages × 1 unit = **≤ 36 units**; day total including probes ≤ **39 units (< 0.5% of the 10,000/day quota)**.
- Corpus: 12 videos, 12 distinct channels, topics python 4 / ai_ml 3 / sql 2 / career 2 / bi_viz 1, publish range 2017-10-05 → 2025-09-27, combined Day 4 `comment_count` **104,884**.
- Expected rows: ≤ 3,600 fetched threads → **~1,500–2,500 analysed comments** after window/owner/language filtering (coder verifies actuals).
- Endpoints: `/commentThreads` (1 unit, `part=snippet`, `maxResults` 1–100, `order=time|relevance`, `textFormat=plainText`, `pageToken` for pagination) and `/comments` (1 unit, `parentId`); **no `publishedAfter`/`publishedBefore` and no language parameter exist** — window and language are post-fetch filters.

**Key decisions:**
- Corpus: fixed 12-video list (§2.1) from Day 4's frame by a fixed rule (top-2 per topic + top bi_viz + next 3 overall, max 1 per channel); no new searches, 0 search quota.
- Fetch: `order=time`, `maxResults=100`, up to 3 pages/video, early stop when the page is entirely older than the window start; window 2025-11-09 → 2026-11-09 applied post-fetch; owner comments excluded; top-level comments only, no replies.
- Sentiment: original rule-based lexicon scorer authored for this project (VADER-style shape: word sum + negation window 3 + intensifier ×1.5 + `s / sqrt(s² + 15)` normaliser + ±0.05 thresholds; lexicon written in the code, ~100–150 words per side, strong words ±2, small emoji map). No VADER lexicon, no NLTK, no pretrained model, no paid API.
- Themes: fixed keyword lists (up to 2 per comment) + data-driven top unigrams/bigrams per sentiment class. `other` > 40% is reported, not re-tuned.
- Validation: stratified human-labelled sample of 120 (40 per predicted class, seed 42), labels committed in `validation_labels.csv`, per-class P/R/F1 + confusion matrix reported; no pass threshold set in advance; **lexicon must not be tuned after seeing validation results**.
- Synthetic fallback: seed 42, n=1,800, template comments per sentiment class (45/35/20 mix by construction), `data/raw/*_synthetic.json` only.
- Licence tensions recorded honestly: quota-cost documentation conflict (1 vs 2 units), comment text as user-generated content in a committed snapshot, derived-metrics tension — none claimed as legally certain.

**Known gaps:** no API date filter (window is post-fetch, uneven coverage across videos); no language filter (Latin-script non-English will mostly score neutral); `pageInfo.totalResults` unreliable; pinned comments surface first with `order=time`; sentiment model cannot handle sarcasm, slang or context; replies not fetched; June 2026 quota-bucket split means the coder's actual fetch is the ground truth on quota.

**Planner's first step:** take this brief as the source of truth for data, sample design, model, themes, and validation targets, and write `plan.md` — starting with the exact file tree (including the per-video raw JSONs, `comments.csv`, `validation_labels.csv`, and the 4 charts) and the per-file responsibilities for the coder.
