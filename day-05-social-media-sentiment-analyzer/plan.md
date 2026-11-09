# Day 05 — Social Media Sentiment Analyzer: Build Plan

**Status:** PLAN — planner sign-off complete (AGENTS.md, stage 2).
**Source of truth:** `research_brief.md` (2026-11-09) + this plan. **If brief and
plan disagree, the plan wins and the difference is noted in §11.** The coder
must reuse the brief + this plan. **No extra web searches.**
**Roadmap entry (verbatim):** "DAY 05 | Social Media Sentiment Analyzer —
Problem / analysis: Classify public comments by sentiment and extract
recurring themes or complaints while documenting model limitations. GitHub
deliverable: Sentiment trend chart and top-theme summary." Section context
(Days 4–6, Social Media & Digital Marketing): Core skills: API integration,
NLP, sentiment analysis, text visualization. Suggested data: YouTube Data
API; public, permissioned comment and metadata datasets.

| Item | Value |
|---|---|
| Fetch date | 2026-11-09 (12-month window 2025-11-09 → 2026-11-09, applied post-fetch — §3) |
| Source | YouTube Data API v3 via the `custom.youtube` connector (helper `bin/youtube.py`, extended 2026-11-09 with `comment-threads` + `comments` subcommands) |
| Corpus | Fixed list of 12 videos from Day 4's frame (§3.1), 12 distinct channels |
| Expected rows | **≤ 3,600 fetched threads → ~1,500–2,500 analysed comments** (the coder must verify the actuals and report them; do not assume them) |
| Quota budget | **≤ 36 units (< 0.5% of the 10,000/day free-tier quota)** — 12 videos × up to 3 pages × 1 unit; day total including the researcher's 3-unit probe ≤ 39 units |
| Scope | Descriptive sentiment/theme analysis of public comments on 12 defined videos only. **Sentiment is a model output, not ground truth; no causal claims; no generalisation beyond these 12 videos' comments.** |

## 1. Problem statement + audience

**Problem.** A data/AI creator can see view counts and like counts on their
videos, but cannot tell what viewers actually *say*: are comments mostly
praise, questions, or complaints — is sentiment improving or souring over
time — and what recurring themes (tutorial clarity, pace, career questions,
audio problems) keep coming up? Day 5 fetches the newest top-level comments
on 12 high-comment-volume data/AI videos, classifies each comment's
sentiment with a transparent rule-based lexicon scorer written for this
project, extracts recurring themes with fixed keyword lists plus
data-driven top words/bigrams, and — the part that makes the numbers
trustworthy — validates the scorer against 120 human-labelled comments and
reports precision/recall/F1 per class. Every sentiment number in every
output carries the qualifier "as classified by our rule-based model" and
sits next to the validation numbers, so nobody mistakes a model output for
ground truth.

**Audience / decision-maker.** A data/AI creator (the portfolio's own field)
deciding what to fix or make next — which complaints recur, which topics
draw praise, whether sentiment on recent videos is trending up or down.
They are not a data analyst: every finding in the dashboard, notebook and
notes must be plain-language, must cite the numbers behind it, must carry
its caveat that sentiment is a model classification validated on 120
human-labelled comments, and must never present a sentiment share as "how
viewers feel" without that qualifier. The dashboard is the decision aid;
`outputs/insights_summary.md` is the plain-language findings note and
`outputs/themes_summary.md` is the evidence-cited theme list (§4.4).

## 2. Research questions (exactly 3)

1. **How positive, neutral or negative are the comments — and is that
   changing over time?** What share of analysed comments falls in each
   sentiment class (overall, per video, per topic), what does the monthly
   trend look like across the 12-month window (with n per month), and how
   much of the neutral share is "no lexicon signal" rather than genuinely
   neutral wording?
2. **What are viewers actually talking about — and what are they
   complaining about?** Which themes recur (praise, tutorial quality,
   requests, career, criticism, questions, audio/video, price, humour),
   how do themes split by sentiment class, and what do the top
   words/bigrams per sentiment class reveal that the fixed theme lists
   missed?
3. **How far can the sentiment model be trusted — and what are its limits?**
   On 120 human-labelled comments, what are the per-class
   precision/recall/F1 and the confusion pattern — and which limitations
   (sarcasm, slang, short comments, Latin-script non-English, no context)
   must a reader keep in mind before acting on any sentiment number?

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
  data source (YouTube) but a **new endpoint family** (comments, not
  videos); nothing carries over except the workflow conventions
  (provenance, synthetic fallback, `.gitignore` rule — §3.3).
- **Endpoints (exactly the two new helper commands; parameters are what the
  helper actually sends — copy them, do not re-derive them):**

| Command | API endpoint | Parameters sent by the helper | Cost |
|---|---|---|---|
| `comment-threads --video-id ID --max-results N --order time --page-token T --text-format plainText` | `GET /commentThreads` | `part=snippet`, `videoId=<id>`, `maxResults=N` (1–100), `order=time`, `textFormat=plainText`, `pageToken=<token>` (only when given) | **1 unit** |
| `comments --parent-id ID --max-results N --page-token T --text-format plainText` | `GET /comments` | `part=snippet`, `parentId=<id>`, `maxResults=N`, `textFormat=plainText`, `pageToken=<token>` (only when given) | **1 unit** |

Full invocations:

```text
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py comment-threads --video-id VIDEO_ID --max-results 100 --order time --text-format plainText
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py comment-threads --video-id VIDEO_ID --max-results 100 --order time --page-token NEXT_PAGE_TOKEN --text-format plainText
python3 ~/workspace/custom-connectors/custom.youtube/bin/youtube.py comments --parent-id COMMENT_ID --max-results 20 --text-format plainText
```

- **The 12-video corpus (fixed — do not invent, add, or swap any video).**
  Selected 2026-11-09 from Day 4's processed frame by the brief's fixed
  rule (top 2 by `comment_count` per Day 4 topic + top `bi_viz` + next 3
  overall, max 1 per channel):

| # | Video ID | Title (short) | Channel | Day 4 topic | Day 4 comment_count | Published |
|---|---|---|---|---|---|---|
| 1 | `fa8k8IQ1_X0` | A.I. ‐ Humanity's Final Invention? | Kurzgesagt – In a Nutshell | ai_ml | 21,781 | 2024-08-06 |
| 2 | `5KmopXwjXik` | Godfather of AI WARNS | The Diary Of A CEO Clips | ai_ml | 17,810 | 2025-09-27 |
| 3 | `HXV3zeQKqGY` | SQL Tutorial - Full Database Course | freeCodeCamp.org | sql | 11,938 | 2018-07-02 |
| 4 | `7S_tz1z_5bA` | SQL Course for Beginners [Full Course] | Programming with Mosh | sql | 10,826 | 2019-03-20 |
| 5 | `aircAruvnKk` | But what is a neural network? | 3Blue1Brown | python | 9,493 | 2017-10-05 |
| 6 | `SSKVgrwhzus` | SQL Full Course for Beginners (30 Hours) | Data with Baraa | python | 8,864 | 2025-03-27 |
| 7 | `t2oOFs4WgI0` | Beyond the Numbers: A Data Analyst Journey | TEDx Talks | career | 4,450 | 2018-03-02 |
| 8 | `yZvFH7B6gKI` | What Is Data Analytics? - An Introduction | CareerFoundry | career | 970 | 2021-03-25 |
| 9 | `qrbf9DtR3_c` | Excel Data Analysis Full Course Tutorial | Learn Skills Daily | bi_viz | 1,209 | 2024-05-31 |
| 10 | `aZ5EsdnpLMI` | Artificial Intelligence \| 60 Minutes | 60 Minutes | ai_ml | 8,101 | 2023-12-30 |
| 11 | `pCJ15nGFgVg` | Excel for Data Analytics - Full Course | Luke Barousse | python | 4,818 | 2024-10-14 |
| 12 | `9f-GarcDY58` | Machine Learning Full Course | Simplilearn | python | 4,624 | 2019-08-30 |

  Corpus facts: 12 videos, 12 distinct channels, topics python 4 / ai_ml 3
  / sql 2 / career 2 / bi_viz 1, video publish range 2017-10-05 →
  2025-09-27, combined Day 4 `comment_count` **104,884**.
- **Response fields the coder will use.** `commentThreads` →
  `snippet.topLevelComment.snippet` per thread: `id`, `textDisplay` (with
  `textFormat=plainText` this equals `textOriginal`; use `textDisplay`),
  `textOriginal`, `authorDisplayName`, `authorChannelId.value`,
  `authorChannelUrl`, `likeCount` (int), `publishedAt` (ISO 8601 UTC),
  `updatedAt`, `canReply`, `viewerRating`. Thread-level `snippet`:
  `channelId`, `videoId`, `totalReplyCount`, `canReply`, `isPublic`. Top
  level: `nextPageToken` (absent on the last page); `pageInfo` is
  **unreliable** — it echoed the page size in the probes (2, then 100),
  never the real total — **never use `totalResults` as a count**.
- **Verification probes (already run by the researcher, 2026-11-09 — do not
  re-run them as separate probes):** `comment-threads --video-id
  yZvFH7B6gKI --max-results 2 --order time` → exit 0,
  `youtube#commentThreadListResponse`, 2 items (pinned owner comment
  2021-03-25 + viewer comment 2026-11-07), `nextPageToken` present, cost 1
  unit. Same call with `--max-results 100` → exit 0, 100 items,
  `nextPageToken` present, dates 2021-03-25 → 2026-11-07, cost 1 unit.
  `comments --parent-id UgxdIrI-f6edGbmFlid4AaABAg --max-results 2` → exit
  0, `youtube#commentListResponse`, 2 replies, cost 1 unit (verification
  only — replies are out of scope). Probe total **3 units**.
- **Hard limits of the API (design constraints, not bugs to fix in Day 5):**
  **no date filter** — `commentThreads.list` has no
  `publishedAfter`/`publishedBefore` (checked against the official
  parameter table 2026-11-09), so the window is a post-fetch filter on
  `publishedAt` (§3.2); **no language filter** — non-English is handled by
  the §4.4 heuristic after fetching; **no sentiment, no `searchTerms` use**
  (it would bias the sample); **`maxResults` caps at 100** per call
  (asking for more silently returns 100); **pinned/owner comments surface
  first even with `order=time`** — the pipeline sorts by `publishedAt`
  itself and excludes owner comments (§3.2); **comments can be disabled
  per video** (empty `items` or 403 `commentsDisabled` — record 0 fetched
  for that video and continue; not a build failure unless ≥ 4 videos
  return 0); read-only, public data only; timeout 30 s per request;
  redirects refused.

### 3.2 Fetch rules

- **Exactly 12 `comment-threads` call sequences** (one per video in §3.1),
  `maxResults=100`, `order=time` (newest first), `textFormat=plainText`,
  `part=snippet` (top-level comments only — **no `replies` part, no
  `comments.list` calls**: replies are out of scope; a thread's reply
  count is recorded but reply text is not fetched). Do **not** use
  `order=relevance` — it returns YouTube's top-ranked comments (most-liked,
  most-replied), which over-represents extreme/polarised comments and
  destroys the time ordering the trend chart needs.
- **Pagination per video:** follow `nextPageToken` for **up to 3 pages (300
  threads)** per video, stopping early when (a) no `nextPageToken` is
  returned, or (b) the **oldest comment on the page is older than the
  window start (2025-11-09)**. Never fetch a 4th page for any video.
- **Time window (applied AFTER fetching, on `publishedAt`):**
  **2025-11-09 → 2026-11-09** (12 months ending on the fetch date).
  Comments outside the window are dropped from the analysed frame and
  counted.
- **Deduplicate** by comment `id` across pages (overlap is not expected
  with `pageToken` paging, but dedupe anyway and record any duplicates
  dropped).
- **Filter (in this order, each step counted):** (1) drop threads whose
  top-level comment's `authorChannelId` equals the video's channel ID
  (channel-owner comments, incl. pinned promos — not audience sentiment);
  (2) drop empty/whitespace-only text; (3) drop comments outside the
  window; (4) drop non-English comments per the §4.4 heuristic (counted
  separately, never silently).
- **Polite use:** ≥ 2 s between calls; **one retry after 30 s on HTTP 5xx /
  timeout only**; **no retry on 403 `quotaExceeded`** — stop and fall back
  (§3.5). Never hammer the API.
- **Quota budget:** 12 videos × up to 3 pages × 1 unit = **≤ 36 units**
  (resets at midnight Pacific Time). Including the researcher's 3-unit
  probe, the day's total is ≤ 39 units — still < 0.5% of quota. There is
  ample headroom for one full re-run if a call fails; there is no headroom
  for exploratory extra calls, so the coder runs exactly this design.
- **Quota-cost discrepancy (open item):** official docs page says 1 unit
  per `commentThreads.list` call; the generated client-library reference
  says "The snippet part has a quota cost of 2 units". The build proceeds
  on 1 unit (official docs page + probe succeeded); if a `quotaExceeded`
  appears far earlier than the ~36-unit budget predicts, stop, check the
  Google Cloud Console quota page, and report the actual bucket limits —
  do not retry or add calls. (Same June 2026 quota-bucket caveat as Day 4.)
- **Error handling (from the brief — follow the table, do not improvise):**

| Error | Meaning | Coder action |
|---|---|---|
| `400 keyInvalid` | Stored key wrong or project misconfigured | Stop. Do not retry. Report as blocked; key is the connector's business, never to be pasted or hard-coded anywhere. |
| `403 quotaExceeded` | Daily quota hit | Stop immediately. No retry. Fall back to cache, then synthetic (§3.5). |
| `403 accessNotConfigured` | YouTube Data API v3 not enabled on the project | Stop. Report as blocked (it was enabled 2026-11-07 and the probes succeeded, so this is not expected). |
| `403 commentsDisabled` (or empty `items`) | Comments disabled on that video, or none returned | Record 0 fetched for that video, continue with the other 11. Not a build failure unless ≥ 4 videos return 0. |
| `403` other (e.g. `forbidden`) | Request rejected for another reason | Check the request first (video ID well-formed, `maxResults` ≤ 100); one careful retry only if the request was malformed. |
| HTTP 5xx / timeout | Transient server/network failure | One retry after 30 s, then fall back (§3.5). |
| Empty `items` on a page with `nextPageToken` present | API quirk | Stop paging that video, count what was fetched, continue — this is not an error. |

  The helper exits non-zero with `HTTP {code} from {path}: {body[:500]}` —
  the pipeline must catch that, log the code/reason, and follow the table
  above. **Never log the API key** (the helper never prints it; keep it
  that way).
- **Expected row counts (coder must verify the actuals and report them; do
  not assume these):** 12 videos × up to 300 threads = **≤ 3,600 fetched
  threads** → after window + owner + language filtering **~1,500–2,500
  analysed comments**. If the final analysed count lands below **800**,
  the coder reports it as a thin-sample caveat in the README; the analysis
  still runs, but monthly trend cells with n < 30 are flagged thin and the
  theme list is labelled thin-sample. If any single video contributes
  > 40% of the final frame, the dashboard must say so.
- **Raw size guard:** one raw file per video
  (`data/raw/comments_<video_id>.json`, verbatim API responses for that
  video's pages, concatenated `items` with page boundaries recorded). At
  ~0.8–1 KB per thread × ≤ 300 threads, each file is ≤ ~300 KB and the raw
  total is ≤ ~3.6 MB — inside the 5 MB/day rule and the 1 MB/file
  guideline. If a raw file would exceed 1 MB, the pipeline must stop
  paging that video earlier and record the truncation (do not silently
  write an oversize file).

### 3.3 Data provenance

- `data/README.md` (coder writes it) records: provider, endpoints used, the
  12-video corpus (§3.1, with the selection rule), access date (2026-11-09),
  quota units used, row counts (fetched → each filter step → analysed, with
  counts), video concentration, licence/attribution note (§3.4) + the
  tensions stated honestly (§3.4), and the hand-validated metric (§4.5).
  `data/processed/data_source.json` records `source` (`"live"`, `"cache"`
  or `"synthetic"`), `generated_at_utc`, `synthetic` (bool), `seed` (`null`
  for live data, `42` for synthetic), plus `video_ids` (the 12 IDs),
  `window_start` / `window_end`, `max_pages_per_video` (3),
  `comment_count_fetched`, `comment_count_analysed`, `quota_units_used`
  (best estimate), `api` (`"youtube-data-api-v3"`), and `filters` (counts
  per §3.2 step).
- **Data-source field rule (Day 2 day-log lesson — mandatory):** an offline
  pipeline run (`--offline` / `--use-cache`) overwrites `data_source.json`'s
  `source` field to `"cache"`. Before publishing, the coder/optimizer must
  either **re-run the pipeline live** (restoring `"live"`) or **restore the
  field by hand with the true value and record the correction** in
  `data/README.md`. A published `data_source.json` that says `"cache"` when
  the data was in fact fetched live is a defect; the publisher's
  frozen-tree check (§8) includes verifying this field.
- **Data-commit rule (from Day 1):** small raw data IS committed — files
  under 1 MB each, under 5 MB per day folder — because the raw files are the
  provenance record. **`.gitignore` must NOT exclude `data/`.** Anything
  larger must be `.gitignore`d and regenerated by the pipeline. Synthetic
  fallback output goes to `data/raw/*_synthetic.json` and is git-ignored; it
  must never overwrite the live cache.
  `python3 src/data_pipeline.py --offline` / `--use-cache` runs from the
  committed cache with no network.
- **Cache reuse note:** there is no prior comment cache — Day 5 is the first
  comments day. A cache fallback is only valid if a Day 5 fetch has
  previously succeeded and written `data/raw/` files in the Day 5 folder.
  Do **not** reuse any other day's data — the source differs entirely (Day
  4 fetched video metadata, not comments).
- **Key rule:** the API key comes only from the `custom.youtube` connector.
  No `.env` file, no key in code, no key in any committed file, no key in
  logs.

### 3.4 Licence / attribution

- Data is public YouTube comment text and metadata fetched under the
  **YouTube API Services Terms of Service and Developer Policies** (checked
  2026-11-09). Attribution is required: include on the dashboard and in
  the repo README, legible: **"Data from the YouTube Data API v3"** with a
  link to YouTube's Terms of Service (`https://www.youtube.com/t/terms`),
  per the Developer Policies requirement that API clients display a link
  to YouTube's Terms of Service.
- Do not redistribute raw bulk data or re-host the API. Cache the fetched
  responses locally for the project only (§3.3).
- Only public metadata is used — no user data beyond public comment
  text/display names, no private data. The API key has no OAuth scopes.
- Code in this repo is MIT (see `LICENSE`); YouTube data is under separate
  YouTube terms, not MIT.
- **Comment text is user-generated content (record honestly, do not resolve
  by redefining the data):** the raw JSONs contain public comments
  verbatim, including display names. They are a dated one-time snapshot
  (2026-11-09) committed as the provenance record, following the Days 1–4
  convention; they are not re-served by a live service and the dashboard
  shows only aggregates plus short excerpts (≤ 120 chars, ≤ 3 per theme,
  no author names in the summary). **No YouTube page found states
  explicitly whether committing verbatim comment text to a public GitHub
  repo counts as redistribution, so this is unresolved and no legal
  certainty is claimed.** State the snapshot date and the tension in
  `data/README.md`.
- **Derived-metrics tension (same as Day 4):** sentiment scores and theme
  assignments are computed from API data by basic arithmetic/rule matching
  for an offline educational analysis, not a service offering metrics to
  users; the dashboard shows the underlying counts next to every derived
  rate. No legal certainty is claimed; `data/README.md` states the tension
  honestly.
- **No copying code or tutorials from the web.** All code is Victor's own
  original work, written from the brief and this plan. The sentiment
  lexicon is authored for this project (§4.1); the normaliser shape and
  ±0.05 thresholds are standard published VADER conventions, documented as
  such, not copied code.

### 3.5 Synthetic fallback rules (if the API is unreachable)

If all requests fail (quota, network block, or outage) after one polite retry:
1. Use a **cached copy** of a previous successful Day 5 fetch if one exists
   (`data/raw/` in this day folder only — see §3.3 cache note).
2. Otherwise generate a **clearly labelled synthetic dataset** for
   development only, deterministic, **seed 42**:

| Field | Synthetic rule |
|---|---|
| `n` | **1,800 synthetic comments** across the same 12 video IDs (150 per video, spread over the window 2025-11-09 → 2026-11-09) |
| `text` | Assembled from fixed template lists per sentiment class, so the lexicon scores them as designed: positive templates ("This tutorial is amazing, thank you so much!", "Great explanation, finally I understand it", "Best video on this topic, really helpful"), neutral templates ("What software is used in this video?", "Can anyone explain the part at 5 minutes?", "Watching this in 2026"), negative templates ("This is so confusing and boring", "Terrible audio, I could not follow anything", "Worst tutorial, full of mistakes") — each template used with small variations (video/topic word swaps), recorded in the code |
| `sentiment mix` | 45% positive / 35% neutral / 20% negative by construction (the templates are chosen to score that way — verify after generation and report the actuals) |
| `like_count` | `U(0, 50)` for neutral, `U(0, 200)` for positive/negative (rounded) |
| `published_at` | Uniform over the window |
| `author` | "Synthetic Commenter NN" (no real display names) |

3. Synthetic output goes **only** to `data/raw/*_synthetic.json` — it must
   never overwrite the live cache. `data/processed/data_source.json`
   records `synthetic: true` + `seed: 42`. All downstream outputs are
   labelled SYNTHETIC. Synthetic data follows the same schema as live data
   (same columns, §4.3) so the pipeline, notebook, and dashboard run
   unchanged. Synthetic files are git-ignored
   (`data/raw/*_synthetic.json` in `.gitignore`); live `data/raw/*.json`
   are committed.
4. Never present synthetic data as real YouTube data. Mark every chart, the
   app and the README **"SYNTHETIC DATA — API unavailable on 2026-11-09"**
   and re-fetch real data before publishing.
   `python3 src/data_pipeline.py --offline` / `--use-cache` runs from the
   committed cache with no network and never generates synthetic data.
5. **Synthetic sentiment is uniform by construction, so on synthetic data
   the trend/theme findings have no interpretation** — state this in the
   README, notebook and insights summary if the synthetic path is used.

## 4. Method — sentiment model, themes, metrics, validation, targets

All metrics are computed on the cleaned comment frame (one row per analysed
comment). **Sentiment here is a model output, not ground truth** — the
dashboard, notebook, insights summary and README must all say so, and the
validation in §4.5 is the evidence for how far the model can be trusted.

### 4.1 Sentiment model (definitions fixed — the planner/coder must not redefine them)

**An original, transparent, rule-based lexicon scorer written for this
project** (in `src/sentiment.py`). VADER-style in shape only — a
word-polarity sum with negation and intensifier handling, normalised to
[−1, +1] — but **the lexicon is authored for this project, not copied**: no
VADER lexicon file, no NLTK download, no pretrained model, no paid API, no
copied project code. Every word, weight and rule lives in the code with a
comment saying what it does, so any reader can audit the full model in one
file.

| Component | Rule (implement verbatim) |
|---|---|
| Lexicon | Two word lists authored in the code: **positive words** and **negative words**. Each word carries polarity **+1 / −1**; a small explicit set of strong words (**love, amazing, brilliant, excellent, fantastic, perfect, hate, terrible, awful, horrible, worst, useless**) carries **±2**. The lists must be written out in full in `src/sentiment.py` (target ~100–150 words per side) — the tester verifies the lists are present and counts them. |
| Tokenisation | Lower-case, split on non-letters (keep apostrophes inside words, e.g. `don't` stays one token), strip URLs and @mentions before scoring (they carry no sentiment). |
| Negation | `not, no, never, n't, don't, doesn't, didn't, can't, won't, isn't, wasn't, aren't, couldn't, shouldn't` flip the polarity of the **next 3 scored words** (a token window of 3). Double negation is not handled — documented as a limitation. |
| Intensifiers | `very, extremely, so, really, absolutely, totally, super, incredibly, truly, quite, pretty` multiply the next scored word's polarity by **1.5**. |
| Emoji | A small explicit map in the code: positive `😍 😂 👍 ❤️ 🔥 🙌 👏 😊 🎉 💯` (+1 each, max +2 per comment); negative `😡 👎 😢 💩 🤮 😤 😠` (−1 each, max −2 per comment). Documented as a crude signal, not a full emoji model. |
| Exclamation | +0.25 per `!` in the text, capped at +0.5, applied to the raw sum **only if the sum is already positive** (excitement amplifies praise; it does not turn a complaint positive). |
| Normalisation | `compound = s / sqrt(s² + 15)` where `s` is the raw summed score (the same normaliser shape VADER publishes — a standard saturating function, documented in the code, not copied code). Result in (−1, +1). |
| Classification | `compound ≥ +0.05` → **positive**; `compound ≤ −0.05` → **negative**; otherwise **neutral** (the ±0.05 thresholds VADER publishes — standard, documented in the code). |
| Output columns | `sentiment_score` (compound, 4 dp), `sentiment` (positive / neutral / negative), plus `scored_words` (count of lexicon words matched — 0 means the comment carried no lexicon signal and is neutral by default, which is itself a finding). |

**What the model cannot do (limitations to document prominently — the
roadmap requires it):** no sarcasm/irony detection ("great, another
30-hour course 🙄" scores positive); no context ("not bad" is handled by
negation, but "this is not the best tutorial, the other one is" is not);
no slang/neologism coverage beyond the authored lists; short comments
("ok", "lol", "first") usually score neutral by default, not by meaning;
non-English is excluded, not translated; emoji handling is a tiny explicit
map; the lexicon was authored before seeing the comments and must **not**
be tuned after seeing validation results (tuning on the validation set
would invalidate it — if a word is missing, report it as a limitation, do
not add it).

### 4.2 Themes (fixed — deterministic, no clustering model)

Two complementary, fully transparent theme methods (both reported; neither
is a black-box topic model):

1. **Keyword themes (fixed lists, authored before seeing the data).** Each
   comment is assigned **up to 2** themes by keyword match on lower-cased
   text; a comment matching none is `other`. Lists (implement verbatim in
   `src/sentiment.py`, `classify_themes`):

| Theme | Keywords (match any) |
|---|---|
| `praise` | thank, thanks, great, amazing, awesome, excellent, love, brilliant, fantastic, wonderful, best, perfect, helpful, useful, clear, easy to follow, well explained, good job, nice, beautiful |
| `tutorial_quality` | explained, explanation, clear, unclear, confusing, confused, understand, understood, step by step, detailed, thorough, beginner friendly, pace, too fast, too slow, rushed |
| `requests` | please make, more videos, next video, part 2, tutorial on, cover, request, want more, do a video, can you make |
| `career` | job, career, interview, salary, switch, beginner, start, learning path, roadmap, get a job, hired |
| `criticism` | wrong, incorrect, mistake, error, outdated, misleading, bad, terrible, boring, waste, useless, disappointed, poor |
| `questions` | how do, how to, what is, why, question, can anyone, does anyone, help me, stuck, error (overlaps `criticism` by design; `questions` wins only when the text contains a `?`) |
| `audio_video` | audio, sound, voice, volume, quality, video quality, blurry, captions, subtitles, accent |
| `price_cost` | price, cost, expensive, free, paid, worth, money, course fee |
| `humor` | lol, haha, funny, 😂, joke, hilarious |
| `other` | no keyword match |

   Priority note: `questions` requires a `?` in the text (else it is not a
   question); `criticism` and `tutorial_quality` may co-occur with `praise`
   on the same comment — up to 2 themes are kept, in the order above. If
   `other` exceeds 40% of the analysed frame, the theme lists are too
   narrow — **report it, do not silently re-tune the keywords after seeing
   results**.
2. **Top words / bigrams (data-driven).** After stopword removal (a fixed
   stopword list in the code, ~80 common English words + `video, youtube,
   channel, tutorial, course, like, just, really, get, got, one, much,
   many, also, even, still, way, thing, things, lot`), count unigrams and
   bigrams separately for positive, negative and neutral comments; report
   the top 20 of each. This is the check on whether the fixed themes
   missed a recurring topic — if a bigram dominates that no theme covers,
   it is reported as an unthemed finding, not folded into a theme list
   after the fact.

### 4.3 Core metrics (definitions fixed — the planner/coder must not redefine them)

| Metric | Formula | Notes |
|---|---|---|
| `comment_count_analysed` | Rows in `comments.csv` after §3.2 filtering | The headline n. |
| `sentiment_share` | Share of analysed comments per class (positive / neutral / negative) | Overall and per month, per video, per topic. Always shown with n. |
| `mean_compound` / `median_compound` | Mean / median `sentiment_score` per group | Descriptive only; both reported (scores are bounded and skewed). |
| `positive_rate` / `negative_rate` | Positive (negative) comments / analysed comments in the group | The trend-chart quantities, monthly. |
| `theme_count` / `theme_share` | Comments carrying a theme / analysed comments (a comment can carry 2 themes, so theme shares sum to > 100% — state this wherever themes are shown) | Per theme, overall and split by sentiment class. |
| `comments_per_video` | Analysed comments per video | Plus each video's share of the frame (§3.2 concentration rule). |
| `monthly_n` | Analysed comments per calendar month in the window | Trend cells with n < 30 are flagged thin. |
| `like_count` (comment) | `snippet.likeCount` (int) | Reported as a distribution (median likes per sentiment class) — do not use likes as a sentiment signal. |
| `scored_words` | Lexicon words matched per comment | Share of comments with 0 scored words is a model-coverage finding. |
| `validation_*` | §4.5 — accuracy, per-class precision/recall/F1, confusion matrix | On the human-labelled sample only, never on the full frame. |

**Use shares and medians for every comparison** — comment counts per video
are heavily skewed and a single viral video would dominate any mean. **No
causal claims.** A theme (e.g. "pace complaints cluster on long courses")
is reported as *"in these comments, …"* — never "long courses cause
complaints". **No sentiment share may be presented as "how viewers feel"
without the "as classified by our rule-based model" qualifier and the
validation numbers beside it.**

### 4.4 Language filter (heuristic, documented)

No language parameter exists on the endpoint (§3.1), so non-English
comments are identified after fetching: strip emoji/URLs/mentions, take the
alphabetic characters, and if **> 20% of letters are non-Latin** (Unicode
script check via `unicodedata`, stdlib only), mark the comment
`language_flag = "non_latin"` and exclude it from sentiment scoring (it is
counted in `data_source.json` and `data/README.md`). This is a crude
heuristic, not a language identifier: it will miss non-English comments
written in Latin script (e.g. Spanish, French) — those will mostly score
neutral (no lexicon match) and inflate the neutral share, which is a stated
limitation, not a hidden one. No new dependency (`langdetect` etc.) is
added for this.

### 4.5 Validation — human-labelled sample (the credibility core of this day)

There is no labelled YouTube-comment sentiment dataset in this project, so
the coder/tester creates one:

- **Sample:** stratified random sample of **120 comments** from the analysed
  frame — **40 per predicted class** (positive / neutral / negative),
  sampled with `random.Random(42)` so it is reproducible. Sampled *after*
  the pipeline runs, from `comments.csv`. The pipeline writes the sample
  frame (`data/processed/validation_sample.csv`: `comment_id, text,
  predicted`) for labelling; the coder labels it blind (text only, no
  predicted label visible while labelling) and writes
  `data/processed/validation_labels.csv` (`comment_id, human_label,
  notes`). The pipeline then computes the evaluation from the two files.
- **Labelling rubric (fixed):** positive = the commenter expresses
  approval, enjoyment, gratitude or praise; negative = disapproval,
  frustration, complaint or criticism; neutral = factual, a question with
  no evaluative tone, or no discernible sentiment. Sarcasm is labelled by
  *intended* sentiment where it is unmistakable, and flagged in the `notes`
  column. The tester independently spot-checks 30 of the 120 labels and
  records agreement.
- **Reporting:** confusion matrix (3×3), per-class precision/recall/F1,
  overall accuracy, macro-F1 — computed by the pipeline from
  `validation_labels.csv` + `comments.csv` and shown in chart 04, the
  notebook, the dashboard and the insights summary. **No pass threshold is
  set in advance** — the deliverable is the honest measurement, whatever it
  is. If macro-F1 is under 0.60 the README must say plainly that the model
  is a weak baseline and must not be used for decisions. **The lexicon
  must not be tuned after seeing the validation results** (§4.1) — tuning
  on the validation set would invalidate the measurement.
- **Tester hand-validation (mandatory, separate from the 120):** the tester
  recomputes **one** comment's `sentiment_score` by hand from the lexicon
  rules in §4.1 and matches `comments.csv` to the last digit; recorded in
  `data/README.md` with the comment ID and the hand-computed number.

### 4.6 What "good" looks like — targets table

| Metric | Target |
|---|---|
| Analysed comments in `comments.csv` | **≥ 800** (expected ~1,500–2,500; < 800 = thin-sample caveat, §3.2) |
| Videos contributing | **≥ 10 of 12** with ≥ 20 analysed comments each (else report which videos under-delivered and why) |
| Monthly trend coverage | **≥ 8 of 12 months** with n ≥ 30 (else flag thin months on the chart) |
| Validation sample | **120 labelled** (40 per predicted class), labels committed, P/R/F1 per class reported |
| Model coverage | Share of comments with 0 scored words reported; if > 25%, say so prominently |
| Theme coverage | `other` theme share **≤ 40%** (if above, report — do not re-tune) |
| Concentration | Largest single video **≤ 40%** of the frame (if above, dashboard says so) |
| Charts | Exactly 4 PNGs (§7), drawn to scale, legible, source-noted |
| Limitations | §4.1 limitations + §3.1 API limits stated in README, dashboard, notebook and insights summary — **zero** presentation of sentiment as ground truth |

If a target is missed, the correct response is to report the miss and
diagnose it — **not** to re-tune the lexicon, theme lists, buckets, or
thresholds after seeing the results. The model, themes and window are fixed
in this brief before the fetch runs.

**Conventions the coder must not re-decide:** lexicon word lists + weights
+ negation window (3) + intensifier (×1.5) + normaliser `s / sqrt(s² + 15)`
+ thresholds (±0.05) per §4.1; theme lists per §4.2; window 2025-11-09 →
2026-11-09; top-level comments only; `order=time`; max 3 pages per video;
owner comments excluded; non-Latin heuristic per §4.4; validation sample
120 (40/class, seed 42). If any of these is unworkable, send it back to the
planner with the exact point — do not silently substitute a different
convention.

## 5. Exact file tree (mirror Day 4's shape)

```
day-05-social-media-sentiment-analyzer/
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
│   │   ├── comments_fa8k8IQ1_X0.json
│   │   ├── comments_5KmopXwjXik.json
│   │   ├── comments_HXV3zeQKqGY.json
│   │   ├── comments_7S_tz1z_5bA.json
│   │   ├── comments_aircAruvnKk.json
│   │   ├── comments_SSKVgrwhzus.json
│   │   ├── comments_t2oOFs4WgI0.json
│   │   ├── comments_yZvFH7B6gKI.json
│   │   ├── comments_qrbf9DtR3_c.json
│   │   ├── comments_aZ5EsdnpLMI.json
│   │   ├── comments_pCJ15nGFgVg.json
│   │   ├── comments_9f-GarcDY58.json
│   │   └── *_synthetic.json   # only if fallback used; git-ignored, never committed
│   └── processed/
│       ├── comments.csv        # ~1,500–2,500 rows expected: one row per analysed comment with all §4.1/§4.3 fields + video/topic/month, themes, language flag
│       ├── validation_sample.csv  # the 120-comment stratified sample (comment_id, text, predicted) — written by the pipeline for labelling
│       ├── validation_labels.csv  # human labels (comment_id, human_label, notes) — committed, reproducible evaluation
│       └── data_source.json    # source, generated_at_utc, synthetic, seed (null live / 42 synthetic), video_ids, window_start/end, max_pages_per_video, comment_count_fetched, comment_count_analysed, quota_units_used, api, filters
├── notebooks/
│   └── analysis.ipynb          # executes end-to-end offline via nbconvert
├── src/
│   ├── data_pipeline.py        # fetch, clean, score, themes, validation eval, synthetic fallback, save outputs
│   ├── sentiment.py            # pure sentiment/theme module, fixed signatures (see §6) — no I/O, no network
│   ├── make_charts.py          # regenerates exactly the 4 PNGs in §7, offline from committed CSVs
│   └── app.py                  # Streamlit sentiment dashboard (width='stretch', §6)
├── outputs/
│   ├── insights_summary.md     # plain-language findings (§2): one finding per question, each citing its number
│   ├── themes_summary.md       # theme list (§4.2): every theme with count, share, sentiment split, example excerpts — CHOSEN as a separate file so the findings note stays readable and the theme list stands alone
│   └── charts/
│       ├── 01_sentiment_trend.png
│       ├── 02_sentiment_by_topic.png
│       ├── 03_top_themes.png
│       └── 04_validation_confusion.png
├── screenshots/
│   └── dashboard.png           # REAL capture of the running app (see §6)
└── tests/
    └── test_pipeline.py        # pytest, offline, ≥10 tests (see §6)
```

Build only what this tree lists. No extra files, no extra charts, no extra
dependencies. (Day 1's `publish_checklist.md` / `test_report.md` are produced
by later roles, not by the coder; the coder must not pre-create them.)

**Not in scope (deferred, do not add):** replies (`comments.list` — verified
but not fetched, §3.1); any new helper capability beyond the two commands
already added; any extra video or top-up route beyond §3.2; any new runtime
dependency (§3.4 of the brief — stdlib + the Day 1–4 stack; sentiment
scoring is hand-written, do not add `nltk`, `textblob`, `vaderSentiment` or
any other NLP package).

## 6. Per-file responsibilities

| File | Responsibility |
|---|---|
| `README.md` | Problem + audience (§1), dataset summary (source, endpoints, the 12-video corpus + selection rule, access date 2026-11-09, window, row counts, quota used, licence note), tools, method (model rules §4.1, theme lists §4.2, validation design §4.5), key insights (filled with real numbers after the run, each with its "as classified by our rule-based model" qualifier), validation results (accuracy, per-class P/R/F1, macro-F1), visuals (the 4 charts embedded), how to run, limitations (§4.1 model limits, §3.1 API limits, corpus bias), model-not-ground-truth sentence in the header + "Data from the YouTube Data API v3" attribution with link to YouTube's Terms of Service. |
| `data/README.md` | Provenance (§3.3): provider, endpoints, the 12-video corpus, access date, quota units used, row counts (fetched → each filter step → analysed), video concentration, licence/attribution note + tensions stated honestly, commit rule, one manually validated metric (by hand, with the numbers — recompute one comment's `sentiment_score` from the lexicon rules), validation sample description, versions used for this build, and the `data_source.json` source-field correction if §3.3 applied. |
| `data/raw/*.json` | Verbatim YouTube API responses, one per video (`comments_<video_id>.json`, that video's pages concatenated with page boundaries recorded). Committed (small, <1 MB each). Never overwritten by synthetic data. |
| `data/processed/comments.csv` | One row per analysed comment, ~1,500–2,500 rows expected: `comment_id, video_id, video_title, channel_title, topic, author_display_name, text, published_at, month, like_count, total_reply_count, sentiment_score, sentiment, scored_words, themes, language_flag`. Text is stored verbatim (public comment text, dated snapshot — see §3.4). |
| `data/processed/validation_sample.csv` | The 120-comment stratified sample written by the pipeline: `comment_id, text, predicted` (40 per predicted class, `random.Random(42)`). Written for labelling; the predicted column is hidden from the labeller while labelling. |
| `data/processed/validation_labels.csv` | Human labels: `comment_id, human_label, notes`. Committed — the evaluation is reproducible from these two files + `comments.csv`. |
| `data/processed/data_source.json` | `source`, `generated_at_utc`, `synthetic` (bool), `seed` (`null` live / `42` synthetic), `video_ids`, `window_start`, `window_end`, `max_pages_per_video` (3), `comment_count_fetched`, `comment_count_analysed`, `quota_units_used`, `api` (`"youtube-data-api-v3"`), `filters` (counts per §3.2 step). Subject to the §3.3 source-field rule (re-run live or restore before publishing). |
| `src/data_pipeline.py` | Fetch (12 `comment-threads` sequences via the helper, ≥ 2 s spacing, one 30 s retry on 5xx only, then fallback; up to 3 pages/video with the §3.2 early-stop rule; raw-size guard), clean/dedupe/filter into the comment frame (owner/empty/window/language steps, each counted), call `sentiment.py` for scoring/themes, `generate_synthetic(seed=42)`, `draw_validation_sample()` (120, 40/class, seed 42), `evaluate_validation()` (confusion matrix + P/R/F1 from `validation_labels.csv`), `--offline` / `--use-cache` mode (runs from committed cache, no network, never generates synthetic data), `save_outputs()` writing raw JSONs + `comments.csv` + `validation_sample.csv` + `data_source.json`. Mirror Day 4's function shapes (`fetch_comment_threads`, `clean_comments`, `save_outputs`, `generate_synthetic`, `_load_cache`, `main`) so the tester can reuse the Day 4 test patterns. **Never log the API key; never put the key in any file.** |
| `src/sentiment.py` | **Pure sentiment/theme module. Pure, testable functions, no I/O, no network.** Signatures the coder must implement (names fixed so the notebook, app and tests import them, never re-implement them): `score_comment(text: str) -> tuple[float, str, int]` (compound score, class, scored-words count per §4.1); `classify_sentiment(compound: float) -> str` (thresholds ±0.05); `classify_themes(text: str) -> list[str]` (up to 2 themes per §4.2, `questions` requires `?`); `is_non_latin(text: str) -> bool` (heuristic per §4.4); `top_words(texts: list[str], n: int = 20) -> list[tuple[str, int]]` and `top_bigrams(texts: list[str], n: int = 20) -> list[tuple[str, int]]` (stopword-filtered, per §4.2); `evaluate_predictions(predicted: list[str], human: list[str]) -> dict` (confusion matrix as nested dict, per-class precision/recall/F1, accuracy, macro-F1). The lexicon word lists, strong-word set, negation/intensifier lists, emoji map and theme keyword lists live in this module as documented constants. |
| `src/make_charts.py` | `python -m src.make_charts` regenerates **exactly the 4 PNGs in §7** in `outputs/charts/`, offline from the committed processed CSVs only (no network, no API). Every chart: title, labelled axes with units, legend where needed, source note ("Source: YouTube Data API v3" or "SYNTHETIC DATA — API unavailable on 2026-11-09" when synthetic), readable at dashboard size, drawn **to scale** (no truncated or misleading axes). Must not create extra PNGs. |
| `src/app.py` | Streamlit sentiment dashboard: topic multi-select (default all), video multi-select, sentiment filter, KPI summary (analysed comments, % positive / neutral / negative **as classified by the model**, validation macro-F1), the 4 charts (or their data rendered natively), the theme table with sentiment split + example excerpts (≤ 3 per theme, ≤ 120 chars, no author names), the validation panel (confusion matrix + per-class P/R/F1), video-concentration note if §3.2 applies, model-not-ground-truth sentence in the header, "Data from the YouTube Data API v3" attribution with link to YouTube's Terms of Service + synthetic banner if `data_source.json` says synthetic. **Layout must use `width='stretch'` (the current Streamlit API) — never the deprecated `use_container_width`** (Day 2 day-log lesson). **Human-readable labels everywhere** — no raw slugs (`ai_ml`, `tutorial_quality`) shown to the user; display "AI & Machine Learning", "Tutorial quality" etc. Must not crash on edge cases — Day 1 lesson (b): sort/reset indexes before any positional lookup. Must not display full comment text in bulk — aggregates + short excerpts only (§3.4). |
| `notebooks/analysis.ipynb` | Full analysis top-to-bottom, offline: load `comments.csv`, recompute scores/themes via `sentiment.py`, reproduce the 4 charts, answer each §2 question with numbers, show the validation table (confusion matrix + P/R/F1 from `validation_labels.csv`), show the top words/bigrams per class. Resolve the project root from the notebook file's own location via `_find_root()` (check for `data/processed/comments.csv` from the notebook's directory upward); **never from `Path.cwd()` alone** — Day 1 lesson (e). A copy executed outside the project must fail with a clear `FileNotFoundError`. Must execute end-to-end offline via nbconvert (CI runs it). |
| `tests/test_pipeline.py` | pytest, offline, **≥10 tests** (target 12–14). Must cover at minimum: (1) scoring on hand-computed cases ("I love this tutorial, amazing work" → positive, exact compound to 4 dp; "This is terrible and boring" → negative; "What software is used?" → neutral, 0 scored words; "not good" → negative via negation; "not bad" → positive via negation; "very helpful" → intensifier ×1.5; emoji-only "🔥🔥" → positive); (2) classification thresholds at the boundaries (compound +0.049 → neutral, +0.05 → positive, −0.05 → negative); (3) theme classification (a comment matching praise + questions keywords → both, capped at 2; a question without `?` → not `questions`; a comment matching nothing → `other`); (4) non-Latin heuristic (Cyrillic/Arabic text → True; plain English → False); (5) top words/bigrams on a constructed corpus (stopwords removed, counts exact); (6) evaluation metrics on a hand-computed 3×3 confusion case (precision/recall/F1 per class exact); (7) validation sample is stratified 40/40/40 and reproducible with seed 42; (8) synthetic generation deterministic with seed 42 and n=1,800, 150 per video, and its sentiment mix is 45/35/20 within ±5 points; (9) synthetic never overwrites the live cache and `*_synthetic.json` does not satisfy the cache check; (10) `--offline`/`--use-cache` runs without network; (11) committed CSV matches the published findings in README/insights (recompute one comment's `sentiment_score` from the CSVs); (12) notebook `_find_root()` resolves correctly — **and the suite must pass both from the repo root and from inside the day folder** (Day 2 CI lesson: the test must exec the notebook namespace with `__file__` set to the notebook path, and the coder must run the full suite from both locations before handoff); (13) "Data from the YouTube Data API v3" attribution present in app + charts/README and the model-not-ground-truth sentence present in README + app + insights. Replace the scaffold `tests/test_smoke.py` if present (delete it — do not keep both test files). |
| `outputs/insights_summary.md` | Plain-language findings (§2): one finding per §2 question (each citing its number from `comments.csv` and its chart), validation results (accuracy, per-class P/R/F1, macro-F1, confusion pattern), limitations (§4.1, §3.1), model-not-ground-truth sentence. Does NOT carry the theme list — that lives in `outputs/themes_summary.md` by this plan's choice (§5). |
| `outputs/themes_summary.md` | **Theme list (this plan's choice — separate file, not folded into insights_summary.md):** every §4.2 theme with count, share, sentiment split, and ≤ 3 short example excerpts (≤ 120 chars, no author names), plus the top-20 unigrams/bigrams per sentiment class. Every number recomputed from `comments.csv`. No causal verbs anywhere. |
| `outputs/charts/*.png` | Exactly 4 PNGs (§7), regenerated by `src/make_charts.py`. No extra PNGs in this folder — CI asserts the count is exactly 4. |
| `screenshots/dashboard.png` | **REAL capture of the running Streamlit app** (full page), taken during the coder's smoke test — not a composite of the static charts. If a real capture is genuinely impossible, flag it explicitly as a composite in the handoff and in the README caption — do not silently pass a composite off as a screenshot. |
| `requirements.txt` | Pinned exact `==` versions, verified in the build venv (Python 3.12): `pandas`, `numpy`, `matplotlib`, `plotly`, `streamlit`, `requests`, `pytest`, **`jupyter==1.1.1` + `nbformat==5.11.1`** (required — CI executes the notebook via nbconvert). No new runtime dependency (brief §5.4); the exact pins are set at optimizer time from the venv that actually ran. |
| `pyproject.toml` | Ruff + black settings mirroring Day 4 exactly: `[tool.ruff] line-length = 88, target-version = "py312"`, `[tool.black] line-length = 88`, `[tool.pytest.ini_options] testpaths = ["tests"]`. Dev tools (ruff 0.17.4, black 26.10.1) are pinned once in the portfolio-root `requirements-dev.txt`, shared by all days. |
| `.gitignore` | Mirror Day 4 exactly: `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.venv/`, `venv/`, `.env`, `*.key`, `*.log`, `.streamlit/secrets.toml`, `.ipynb_checkpoints/`, plus `data/raw/*_synthetic.json` (synthetic fallback output is never committed; live `data/raw/*.json` IS committed). **Must NOT exclude `data/`** — diff `.gitignore` against this plan before sign-off (Day 1 lesson d). |
| `LICENSE` | MIT, keep as scaffolded. |

### Coder environment (Day 1/2/3/4 lessons applied)

- Create `.venv` with the pinned deps installed and hand it off working — the tester provisions nothing and must never install the project's own deps from scratch; if the venv is missing the tester reports "blocked: no venv".
- Run `black` + `ruff` **before** handoff (Day 1 lesson: lint left to the end cost a full fix cycle). `black --check` + `ruff check` must pass on `src/` and `tests/`.
- Capture the real `screenshots/dashboard.png` during the coder's own smoke test (fresh port 8502+, never assume 8501 is free; kill the server and verify the port is free afterwards — Day 1 lesson c).
- Run the full pytest suite **both from the repo root and from inside the day folder** before handoff (Day 2 CI lesson).
- **Labelling is done blind:** when labelling the 120 validation comments, the coder works from `validation_sample.csv` text only — the `predicted` column must not be visible while assigning `human_label`. (Generate a labelling sheet with `comment_id` + `text` only.)
- One writer per file; build only what this plan lists; no extra web searches.

## 7. Charts (exactly 4 — CI asserts the count)

`python -m src.make_charts` regenerates exactly these 4 PNGs, offline from
the committed processed CSVs. All 4 must be well-labelled (title, axes with
units, legend, source note), **drawn to scale** (no truncated or misleading
axes) and legible at dashboard size. Human-readable labels on every chart —
no raw slugs.

| # | Filename | Content |
|---|---|---|
| 1 | `01_sentiment_trend.png` | **Sentiment trend (the roadmap deliverable)** — monthly positive / neutral / negative shares (stacked bars or lines, 2025-11 → 2026-11) with n labelled per month; months with n < 30 marked thin, so the trend is never read without its evidence. Caption: "as classified by our rule-based model". |
| 2 | `02_sentiment_by_topic.png` | **Sentiment by topic** — stacked bars of sentiment share per Day 4 topic group (python / ai_ml / sql / career / bi_viz) with n per bar, plus the overall-sample shares as a reference, so which topics draw the most praise or complaints — and on how much evidence — is visible at a glance. |
| 3 | `03_top_themes.png` | **Top themes (the roadmap deliverable)** — horizontal bars per theme (§4.2) with comment count and share labelled, split by sentiment class (stacked or grouped), so the recurring themes and their tone are comparable at a glance. `other` shown as its own bar, never hidden. |
| 4 | `04_validation_confusion.png` | **Human validation** — 3×3 confusion matrix heatmap (predicted vs human labels, n=120) with per-class precision/recall/F1 annotated, so how far the model can be trusted is visible at a glance. This is the chart that documents the model limitations. |

## 8. Success checklist (roadmap minimum success criteria — all must pass)

- [ ] Problem statement + audience written (§1, in README and this plan)
- [ ] Data source documented: provider, endpoints, the 12-video corpus + selection rule, collection date (2026-11-09), window, licence/attribution ("Data from the YouTube Data API v3" + link to YouTube's Terms of Service), quota used, row counts — in `data/README.md` and `data/processed/data_source.json` (with the §3.3 source-field rule satisfied: live re-run or restored field before publishing)
- [ ] Repeatable prep steps documented (fetch → clean → score → themes → validation → charts, with `--offline` mode) + model/theme definitions (§4) written down
- [ ] ≥2 well-labelled visualisations produced — Day 5 produces exactly 4 (§7), **drawn to scale and legible**, plus a functional dashboard: the Streamlit dashboard runs and renders (smoke gate, §9)
- [ ] Interpretation written (`outputs/insights_summary.md`, one finding per §2 question) + **theme summary** (`outputs/themes_summary.md`, every theme with count, share, sentiment split, excerpts) — and all §4.6 targets pass (or each miss is reported and diagnosed, never tuned away)
- [ ] README with setup instructions, sample outputs (sentiment table + chart thumbnails), validation results, and limitations
- [ ] No credentials / private records in the repo; no huge raw files committed (raw JSONs <1 MB each, <5 MB per day folder); `.gitignore` does not exclude `data/`
- [ ] One metric manually validated by hand and recorded in `data/README.md` (recompute one comment's `sentiment_score` from the lexicon rules, matching to the last digit)
- [ ] Pipeline runs end-to-end from a clean checkout (`pip install -r requirements.txt`, `python -m src.data_pipeline --offline`, `python -m src.make_charts`, `pytest tests/ -q`) — **pytest passing both from the repo root and from inside the day folder**
- [ ] Notebook runs top-to-bottom without errors (offline, via nbconvert, with `_find_root()`)
- [ ] Pinned dependencies in `requirements.txt`; `black --check` + `ruff check` clean
- [ ] Streamlit smoke gate passed: fresh port 8502+, HTTP 200 on `/` and on `/_stcore/health`, real `screenshots/dashboard.png` captured, server killed and port verified free
- [ ] Charts to scale and legible; frozen-tree check passed immediately before push (every file the READMEs reference exists on disk — charts, screenshot, CSVs, theme summary)
- [ ] **Model limitations documented prominently** (roadmap requirement): §4.1 limitations + §3.1 API limits in README, dashboard, notebook and insights summary; **zero** presentation of sentiment as ground truth

## 9. Coder handoff checklist (reference — coder must satisfy all of these before the tester starts)

Per AGENTS.md / Day 1 retrospective, the coder hands off only when **all** of
the following hold; the tester verifies in the coder's venv and provisions nothing:

1. `.venv` exists with pinned deps installed (requirements.txt matches the venv that actually ran).
2. `black --check src tests` and `ruff check src tests` pass (exit 0).
3. `pytest tests/ -q` passes (≥10 tests, offline) **from the repo root AND from inside the day folder**.
4. `.gitignore` matches §6 (in particular: does NOT exclude `data/`; excludes only `data/raw/*_synthetic.json`).
5. `screenshots/dashboard.png` is a REAL capture of the running app (or explicitly flagged as a composite in the handoff + README caption).
6. `python -m src.make_charts` regenerates exactly 4 PNGs in `outputs/charts/` (offline, from committed CSVs); notebook executes end-to-end offline via nbconvert.
7. Every number in README / dashboard / notebook / insights matches `data/processed/comments.csv` and `data/processed/validation_labels.csv`, and every theme number matches `outputs/themes_summary.md`.
8. `data/processed/data_source.json` `source` field is correct for the published data (§3.3) — re-run live or restore before handoff.
9. `src/app.py` uses `width='stretch'` throughout — no `use_container_width` anywhere in the tree.
10. No causal verbs in any finding or theme claim; the model-not-ground-truth sentence is in the README, app header, insights summary and themes summary; every sentiment share carries its "as classified by our rule-based model" qualifier.
11. `data/processed/validation_labels.csv` exists with exactly 120 rows (40 per predicted class) and the evaluation (confusion matrix + P/R/F1) in the README/insights/chart 04 is computed from those labels, not hand-typed.

**Tester smoke gate (mandatory, for the tester's reference):** start
`streamlit run src/app.py` on a fresh port (8502 or higher, never 8501);
confirm HTTP 200 on `/` and on `/_stcore/health` with a clean server log;
capture a full-page screenshot to `screenshots/dashboard.png`; kill the server
and verify the port is free; record port, HTTP statuses and screenshot size in
`test_report.md`. The tester also independently spot-checks 30 of the 120
validation labels (§4.5) and records agreement.

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| YouTube 403 `quotaExceeded` / outage on fetch day | ≥ 2 s spacing, one 30 s retry on 5xx only, then cached → synthetic (§3.5); synthetic is labelled everywhere and re-fetched before publishing. Quota-cost discrepancy (1 vs 2 units): coder's actual fetch is ground truth (§3.2). |
| `order=relevance` used by habit | Brief §2.1 forbids it; this plan repeats the ban (§3.2); tester checks the fetch code. |
| Lexicon tuned after seeing validation results | §4.1/§4.5 forbid it: a miss is diagnosed, not tuned away; the lexicon is authored before the fetch and frozen at coder handoff. |
| Sentiment presented as ground truth | §4.3 qualifier rule + checklist item 10: every sentiment share carries "as classified by our rule-based model" + the validation numbers beside it; tester greps the wording. |
| `pageInfo.totalResults` used as a count | Brief §1.3 proves it unreliable; this plan repeats the ban (§3.1); pipeline counts rows from fetched items only. |
| Pinned/owner comments counted as audience sentiment | §3.2 filter step (1) excludes owner comments; pipeline sorts by `publishedAt`, never trusts response order. |
| Latin-script non-English inflating neutral | §4.4 heuristic + stated limitation; neutral share is always reported alongside the 0-scored-words share (§4.6). |
| Thin months read as a trend | §7 chart 01 marks n < 30 months thin; §4.6 requires ≥ 8 of 12 months with n ≥ 30 or the miss is reported. |
| One video dominating the frame | §3.2 concentration rule (> 40% → dashboard says so); §4.6 target. |
| `use_container_width` deprecation (Day 2 day-log lesson) | §6 mandates `width='stretch'` in `app.py`; handoff checklist item 9 greps for the deprecated call. |
| Offline run overwriting `data_source.json` source to `"cache"` (Day 2 day-log lesson) | §3.3 rule: re-run live or restore the field before publishing; handoff checklist item 8; publisher frozen-tree check includes it. |
| `.gitignore` silently dropping raw data (Day 1 lesson d) | §6 diff check at coder handoff; publisher frozen-tree check before push. |
| Screenshot going missing before push (Day 1 lesson) | Treat `screenshots/dashboard.png` as a checked deliverable; verify it exists at every handoff; publisher re-verifies immediately before pushing. |
| Notebook cwd trap (Day 1 lesson e) + Day 2 CI failure (test passed inside the day folder, failed from the repo root) | `_find_root()` from the notebook file's own location; notebook test execs with `__file__` set to the notebook path; full suite run from both locations (§6, test 12). |
| Dashboard crash invisible to pytest (Day 1 lesson b) | Mandatory Streamlit smoke gate (§9) + real screenshot. |
| Chart count drift (extra PNG breaks CI) | `make_charts.py` writes exactly the 4 files in §7 and no others; CI asserts count == 4. |
| API key leaked into code/logs/repo | Key comes only from the connector (§3.3); pipeline never logs it; tester checks for secrets. |
| Labelling bias (labeller sees the prediction) | §6 coder environment: labelling is done blind from text only; tester spot-checks 30 labels independently (§4.5). |
| Orchestrator validate `.gitignore` false FAIL (Day 4 day-log) | Fixed in this run as a small orchestrator change (§11): the check must only flag broad `data/` exclusions, not the specific `data/raw/*_synthetic.json` pattern; verified by running validate on Day 4 and Day 5. |

## 11. Brief-vs-plan differences

**No contradictions on data, sample, model, themes or validation.** This plan
adopts the brief's endpoints and parameters (§3.1, verbatim), the 12-video
corpus (§3.1), the quota budget ≤ 36 units (§3.2), the expected row counts
≤ 3,600 → ~1,500–2,500 (§3.2), the sentiment model rules (§4.1, verbatim),
the theme lists (§4.2, verbatim), the language heuristic (§4.4), the
validation design (§4.5), the synthetic parameters (seed 42, n=1,800, §3.5),
the licence tensions (§3.4) and the out-of-scope ruling on replies (§3.1)
without change. Additions and choices made by the plan (not contradictions):

- **Theme output chosen:** a separate `outputs/themes_summary.md` (the brief
  offered the theme-summary deliverable but fixed no file); the plan chooses
  the separate file so the plain-language findings note stays readable —
  mirroring Day 4's separate recommendations file.
- **Processed-file names fixed** where the brief left them to the plan:
  `comments.csv` (one row per analysed comment, §6 column list),
  `validation_sample.csv` (the 120-comment sample frame) and
  `validation_labels.csv` (human labels), and `data_source.json` (with
  `video_ids`, `window_start`/`window_end`, `max_pages_per_video`,
  `comment_count_fetched`, `comment_count_analysed`, `quota_units_used`,
  `api`, `filters` fields).
- **Raw-file names fixed:** `comments_<video_id>.json` (one per video).
- **New module `src/sentiment.py`** with fixed function signatures (§6) —
  the brief names no module; the pipeline module keeps the Day 4 shape.
- **Exact 4 chart filenames** (§7) and the ≥10-test list (§6), including the
  Day 2 CI lesson (suite must pass from the repo root AND inside the day
  folder).
- **Targets table (§4.6) added by the plan:** ≥ 800 analysed comments,
  ≥ 10 of 12 videos with ≥ 20 comments, ≥ 8 of 12 months with n ≥ 30,
  120 labelled, 0-scored-words share reported, `other` ≤ 40%, largest
  video ≤ 40% — the brief states the underlying expectations but fixes no
  pass/fail numbers; these are the plan's fixed targets.
- **Fetch spacing:** the plan states ≥ 2 s between calls (the brief's
  verified polite-use rule, §1.6); this is stricter than a 1 s minimum and
  therefore satisfies it.
- **Blind labelling procedure added** (§6 coder environment): the coder
  labels from text only, with the `predicted` column hidden; the tester
  spot-checks 30 labels.
- **Orchestrator fix included in this run** (§10): the `.gitignore` false
  FAIL from the Day 4 day-log is fixed as a small orchestrator change
  (narrow the check to broad `data/` exclusions) and verified by running
  validate on Day 4 and Day 5 — a shared-tool fix, not a day-file change.
- **Day-log lessons applied:** `width='stretch'` (not `use_container_width`)
  in `app.py`; human-readable labels (no raw slugs) in the dashboard and
  charts; the `data_source.json` `"cache"` source-field rule (§3.3);
  `_find_root()` from the notebook's own location (Day 1 lesson e);
  `.gitignore` must NOT exclude `data/` (Day 1 lesson d); real screenshot
  at coder/tester handoff (not a composite); coder runs black+ruff before
  handoff; tester provisions nothing.
- **3 research questions** (§2) instead of Day 4's 3 performance questions,
  per this day's scope.

If the coder finds any of these unworkable, it goes back to the planner with
the exact point — the coder does not silently substitute a different
convention.

## 12. Build order (coder)

1. `.venv` + pinned deps → 2. `src/sentiment.py` (pure functions: lexicon
   scoring → thresholds → themes → language heuristic → top words/bigrams
   → evaluation, §6) → 3. `src/data_pipeline.py` (fetch the 12 videos'
   comment threads → dedupe/filter → score + themes → save; verify
   ~1,500–2,500 rows, report quota units used, filter counts, and video
   concentration) → 4. `pytest` on the sentiment tests as they land (from
   both the repo root and the day folder) → 5. validation labelling (draw
   the 120-comment sample, label blind, write `validation_labels.csv`,
   run `evaluate_validation`) → 6. `src/make_charts.py` (exactly 4 PNGs)
   → 7. `notebooks/analysis.ipynb` (offline, `_find_root()`) → 8.
   `src/app.py` + smoke test + real `screenshots/dashboard.png` → 9.
   `README.md`, `data/README.md`, `outputs/insights_summary.md`,
   `outputs/themes_summary.md` (numbers from the CSVs only) → 10. `black` +
   `ruff` + full `pytest` (both locations) + handoff checklist (§9).
   **The orchestrator `.gitignore` fix (§10/§11) is done first, before step
   1, and verified by running validate on Day 4.**

**Token note:** this plan reuses the brief's verified numbers (endpoints,
corpus, quota budget, model/theme definitions, validation design, synthetic
parameters) verbatim — no re-verification, no extra searches. Later roles
reuse the tester's verified figures verbatim; nobody recomputes a finding
from scratch (a spot-check from the committed CSVs is the most that is ever
needed).

## 13. Handoff (planner → coder)

**What was produced:** exactly one file —
`day-05-social-media-sentiment-analyzer/plan.md` (this file). No other file
was written or modified.

**Exact file tree the coder must build:** §5 — `README.md`, `LICENSE`,
`requirements.txt`, `pyproject.toml`, `.gitignore`, `data/README.md`,
`data/raw/` (12 `comments_<video_id>.json` files),
`data/processed/` (`comments.csv`, `validation_sample.csv`,
`validation_labels.csv`, `data_source.json`),
`notebooks/analysis.ipynb`, `src/` (`data_pipeline.py`, `sentiment.py`,
`make_charts.py`, `app.py`), `outputs/` (`insights_summary.md`,
`themes_summary.md`, `charts/` with exactly 4 PNGs),
`screenshots/dashboard.png`, `tests/test_pipeline.py`. Build only what §5
lists — no extra files.

**Known gaps:** no API date filter / no language filter (post-fetch only,
stated as limitations, §3.1); `pageInfo.totalResults` unreliable (never
use it); pinned/owner comments surface first with `order=time` (filter
step 1, §3.2); sentiment model cannot handle sarcasm, slang or context
(§4.1); replies not fetched; quota-cost documentation conflict (1 vs 2
units — coder's actual fetch is ground truth, §3.2); June 2026 quota-bucket
split (same); no new dependency is added (brief §5.4), so pins are set at
optimizer time from the venv that actually ran.

**Coder's first step:** fix the orchestrator `.gitignore` false FAIL
(§10/§11 — narrow the check to broad `data/` exclusions, verify by running
validate on Day 4), then create the `.venv` and write `src/sentiment.py`
(the pure model, §6) before any fetch code — and fetch the live data (the
12 videos' comment threads in §3.1, `maxResults=100`, `order=time`, up to
3 pages per video with the §3.2 early-stop rule) before writing any
analysis code.
