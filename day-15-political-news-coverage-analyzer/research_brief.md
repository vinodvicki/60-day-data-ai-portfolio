# Day 15 — Political News Coverage Analyzer: Research Brief

**Status:** VERIFIED — one lean probe pass completed 2026-11-22 (researcher, stage 1).
**Business question:** How do major US news outlets differ in the topics they cover,
how much attention each topic gets, and the language sentiment of that coverage —
compared across an explicitly defined corpus, without ever equating sentiment with
factual bias?

**Scope decisions (roadmap entry, verbatim — non-negotiable):** "Compare topics,
attention, and language sentiment across an explicitly defined news corpus; do not
equate sentiment with factual bias." Deliverable is a source-comparison report with
sample review and limitations. Core skills: statistics, mapping, NLP, careful
nonpartisan interpretation. **No predictive model, no bias scoring, no fact-checking
of individual claims.** Sentiment is a property of the *language used*, not a
measure of truth or of political leaning.

## 1. Data source — verified from scratch

**PRIMARY: outlet RSS feeds (no key, no login, no rate limit observed).** RSS is the
primary collection method because it worked for every outlet tested except two
(see §1c), while the GDELT API rate-limited on the second call (§1b). RSS returns
headline + description + link + publication date per item — **no full article text**.
All sentiment and topic work therefore runs on **title + description text only**;
that limitation must be stated on every surface that shows a sentiment number.

### 1a. Corpus definition (explicit — the planner/coder must use exactly this)

**Outlets (6, verified working 2026-11-22):** chosen to span the US political
spectrum with well-known national outlets, and limited to feeds that returned
HTTP 200 with real items in this probe:

| Outlet | Feed URL (verified) | Probe result (2026-11-22) |
|---|---|---|
| The New York Times | `https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml` | HTTP 200, **10 items** |
| The Wall Street Journal | `https://feeds.a.dj.com/rss/RSSWorldNews.xml` | HTTP 200, **20 items** |
| Fox News | `https://moxie.foxnews.com/google-publisher/latest.xml` | HTTP 200, **25 items** |
| CNN | `http://rss.cnn.com/rss/edition.rss` | HTTP 200, **50 items** |
| NPR | `https://feeds.npr.org/1001/rss.xml` | HTTP 200, **10 items** |
| BBC News (US coverage) | `https://feeds.bbci.co.uk/news/rss.xml` | HTTP 200, **32 items** |

**Date window:** articles with `pubDate` in **2026-11-08 to 2026-11-22 inclusive**
(14 days ending on the research date). RSS feeds are rolling "latest N items" lists,
not archives, so the window is enforced by filtering on `pubDate` at collection
time; items outside the window are dropped and the drop count per outlet is
recorded. **Expected coverage warning:** feeds holding only 10 items (NYT, NPR)
may cover fewer than 14 days — the coder must report the actual earliest `pubDate`
per outlet in `data_source.json` and in the report, and must NOT claim a full
14-day window for an outlet whose feed does not reach back that far.

**Collection method:** one GET per feed at build time (6 requests total), parse
with `feedparser`, store the raw items verbatim in `data/raw/<outlet>_rss.xml`
(small files, committed as the provenance record — each feed was 8–262 KB in the
probe; total expected well under the 1 MB/file and 5 MB/day rules). Deduplicate by
URL. Keep only items whose `pubDate` falls in the window. Fields kept per article:
`outlet, title, description, link, pub_date, guid`. No scraping of the linked
article pages — RSS text only.

**Corpus size (estimate, not a claim):** the six feeds held 147 items at probe
time; after the 14-day `pubDate` filter the collected corpus will be smaller
(RSS lists are rolling and the newest items dominate). The coder records the exact
final N per outlet; no minimum N is guaranteed here.

### 1b. GDELT DOC API v2 (SECONDARY / cross-check — verified once, then rate-limited)

Base: `https://api.gdeltproject.org/api/v2/doc/doc` — free, no key.

- **Verified working once (2026-11-22):** `GET .../doc?query=politics&mode=artlist&maxrecords=5&format=json&timespan=1d`
  returned HTTP **200**, 2,042 bytes, 5 real articles (fields: `url, url_mobile,
  title, seendate, socialimage, domain, language, sourcecountry`). Note the
  unfiltered query returns non-English, non-US items (e.g. Malay, Chinese) —
  **any GDELT query must include `sourcelang=english&sourcecountry=US`**.
- **Rate limit (verified, twice):** the second call (~40 s later, domain-filtered)
  and a third call (after a further 20 s pause) both returned HTTP **429** with
  body: *"Please limit requests to one every 5 seconds or contact
  kalev.leetaru5@gmail.com for larger queries."* The 429 persisted well past the
  stated 5-second spacing, so the effective limit from this environment is stricter
  than documented. **Build rule: at most one GDELT call, spaced ≥ 60 s from any
  other GDELT call, with exponential backoff (60 s, 120 s) and a hard stop after
  3 attempts; a persistent 429 means GDELT is skipped, not retried all day.**
- **The bare docs URL returned 429 too** (`GET .../doc/doc` with no parameters),
  so do not use a bare-URL health check.
- **Use in this build:** OPTIONAL cross-check only — one `artlist` query per
  outlet with `domain:<outlet-domain>` to confirm the outlet published in the
  window, or one `timelinevol` query for overall volume context. GDELT is NOT
  the primary source for Day 15 and the build must succeed with RSS alone. If
  GDELT is used, record the exact query string and the 429/backoff behaviour in
  `data_source.json`.
- GDELT terms: free for research use; attribution "Source: GDELT Project
  (https://www.gdeltproject.org/)" if used.

### 1c. What was NOT available — recorded, not silently dropped

- **Associated Press: EXCLUDED (verified blocked).** `https://apnews.com/rss`
  returned curl exit 000 (no response) on the first attempt and HTTP **403** on
  retry. AP is not in the corpus. Do not add it without a verified working feed.
- **Reuters: EXCLUDED (verified blocked).** `https://www.reuters.com/rssFeed/topNews`
  returned HTTP **401**. Reuters is not in the corpus.
- **Full article text: OUT OF SCOPE.** RSS gives title + description only.
  Scraping outlet article pages would breach outlet terms and is not attempted.
  Sentiment/topic results are explicitly "headline + summary language" results.
- **FEC / election data (roadmap "suggested data"): NOT the corpus.** The roadmap
  lists "FEC campaign finance datasets; official election data; Census" as suggested
  data, but those are the wrong data type for a news-coverage comparison — Day 13
  already covered FEC finance, Day 14 covered election turnout. They are recorded
  here as considered and not used for the corpus itself; the planner may cite Day 13/14
  findings as context only, and must not re-fetch FEC data for this day.
- **No API key exists in this workspace and none is needed** for RSS or GDELT.

## 2. Metric definitions — exact

All metrics are computed per **outlet** and per **topic** from the collected corpus.
Every number is reported with its N (article count) beside it; no rate is reported
without its denominator.

- **Corpus / attention (PRIMARY):** `articles(outlet, topic)` = count of collected
  articles from that outlet assigned to that topic. **Attention share** =
  `articles(outlet, topic) ÷ articles(outlet, all topics) × 100` (within-outlet
  share, so outlets with different feed sizes are comparable). Also report the
  corpus-wide share `articles(topic) ÷ articles(all) × 100`. Never compare raw
  counts across outlets as "attention" without the share beside them — feed sizes
  differ by design (10 vs 50 items at probe time).
- **Topic assignment:** frozen keyword dictionary, defined once in code and printed
  in full in the README. Ten topics: **Economy, Healthcare, Immigration,
  Climate/Energy, Foreign policy, Elections & campaigns, Crime & justice,
  Technology & AI, Education, Other**. Assignment rule: lowercase title +
  description, count dictionary keyword hits per topic, assign the topic with the
  most hits; ties → the topic whose keyword appears earliest in the text; zero hits
  → `Other`. The dictionary must be frozen before the pipeline runs (no tuning
  after seeing results) and listed verbatim in the report. Known limit: keyword
  matching is crude — the report must include a **sample review** (roadmap
  deliverable): a random sample of 30 articles (5 per outlet) with assigned topic
  shown alongside the title, manually spot-checked, and the agreement rate reported.
- **Language sentiment (lexicon-based, frozen):** **VADER** (`vaderSentiment`,
  pinned version) applied to `title + " " + description` of each article.
  Compound score in [−1, +1]; standard VADER thresholds: **≥ +0.05 positive,
  ≤ −0.05 negative, otherwise neutral**. Report per outlet and per topic: mean
  compound with 95% confidence interval, median, and the % positive / neutral /
  negative. VADER is a general-purpose social-media lexicon — it was not built for
  news text, and that limitation must be stated wherever sentiment is shown.
  No other sentiment model is used; no model is trained.
- **Statistical comparisons (planned):**
  - **Topic × outlet:** chi-square test of independence on the 6 × 10
    contingency table of article counts (report χ², degrees of freedom, p-value;
    if any expected cell count < 5, report Fisher's exact test on the collapsed
    table instead and say so — do not silently run chi-square on sparse cells).
  - **Sentiment across outlets:** one-way ANOVA on compound scores by outlet,
    or Kruskal–Wallis if the compound distribution is non-normal (test normality
    per outlet with Shapiro–Wilk on the sample; report which test was used and why).
    Pairwise outlet differences only with a stated correction (Tukey HSD after
    ANOVA, or Dunn with Bonferroni after Kruskal–Wallis); never report uncorrected
    pairwise p-values as findings.
  - **Sentiment by topic within an outlet:** same test family as above, topic as
    the grouping variable; report only if N per group ≥ 5.
  - **Uncertainty:** every mean sentiment carries a 95% CI (t-interval, or
    bootstrap with 1,000 resamples if the distribution is skewed — state which);
    every share carries a Wilson 95% CI. No point estimate is shown without its
    interval in the report or dashboard.
- **What is NOT computed:** no bias score, no leaning score, no "most biased
  outlet" ranking, no fact-checking, no claim that any outlet's coverage is true
  or false. Sentiment differences are differences in *language*, nothing more.

### Nonpartisan interpretation rules (binding on every surface — README, insights summary, notebook, dashboard)

1. **Sentiment ≠ factual bias, stated everywhere.** The sentence "Sentiment measures
   the emotional tone of the words used; it is not a measure of factual accuracy,
   fairness, or political bias" (or equivalent) appears in the README, the insights
   summary, the notebook, and the dashboard. No chart title, axis label, or caption
   may use the words "bias", "biased", "leaning", "left", or "right" to describe an
   outlet.
2. **Same metrics, same charts, same table columns for every outlet.** No outlet is
   the reference group; no outlet is singled out for commentary beyond what the
   numbers say.
3. **No causal claims:** never "outlet X covered Y because …" or "X emphasises Y
   to …". Allowed language: "covered more/fewer articles on", "a larger/smaller
   share of its corpus", "more positive/negative language on average".
4. **No editorial adjectives about outlets or coverage** ("alarmist", "fair",
   "obsessed", "ignoring") — report the count, the share, the mean sentiment and
   its CI.
5. **Every chart and table states its coverage** (outlets, date window actually
   achieved per outlet, N per outlet, title+description text only) and its source
   (RSS feed URLs, GDELT query if used, VADER version).
6. **"Most/least covered" always means by the stated metric** (count or share),
   with the outlet, topic and window named in the title.

## 3. Licence / attribution

- RSS feeds are the outlets' own content, fetched for analysis. **Do not republish
  full article text** — the repo stores headlines, descriptions and links only, plus
  derived counts and scores. Attribute each outlet by name with a link to its site
  in README + data/README.md.
- GDELT (if used): free for research; "Source: GDELT Project
  (https://www.gdeltproject.org/)".
- VADER lexicon: `vaderSentiment` is MIT-licensed; record the pinned version in
  `requirements.txt` and `data_source.json`.
- No personal data is handled: all figures are article-level aggregates from
  public feeds.

## 4. Synthetic-fallback note (only if all RSS feeds fail)

- Labelled synthetic, seed 42, `synthetic: true` in `data_source.json` (per
  AGENTS.md data rule); never overwrite a real download.
- Generate 6 outlets × 10 topics mimicking the probed feed sizes (10–50 articles
  per outlet, total ~150 articles): titles drawn from a small fixed template pool
  per topic (e.g. "Markets rise as …", "Hospital staffing …"), descriptions one
  sentence, `pub_date` uniform in 2026-11-08–2026-11-22, sentiment assigned by
  construction so the VADER pipeline still runs end-to-end. Then run the identical
  pipeline so the fallback exercises the same code path.
- Fallback is a last resort: all six RSS feeds verified HTTP 200 with real items in
  this pass, so the coder should expect the real collection to work. GDELT alone
  failing is NOT a fallback trigger — RSS alone is a complete build.

## 5. Verification status

- [x] Primary endpoints confirmed against the live feeds (2026-11-22): NYT 200/10
      items, WSJ 200/20, Fox 200/25, CNN 200/50, NPR 200/10, BBC 200/32
- [x] GDELT DOC API confirmed working once (200, 5 articles, 2,042 bytes) and its
      rate limit confirmed twice (429, "one every 5 seconds", persisting past 20 s)
- [x] AP feed confirmed unusable (000 then 403) and Reuters confirmed blocked
      (401) — both excluded with reasons, not silently dropped
- [x] Corpus defined explicitly: 6 outlets, 14-day window 2026-11-08–2026-11-22,
      RSS-only collection, title + description text only
- [x] Metric definitions recorded exactly (§2): attention share, frozen keyword
      topics + 30-article sample review, VADER compound with standard thresholds,
      chi-square / ANOVA-or-Kruskal–Wallis with correction, Wilson + t/bootstrap CIs
- [x] Nonpartisan guardrail recorded (§2, binding on README, insights summary,
      notebook and dashboard): sentiment is never equated with factual bias
- [x] Licence / attribution recorded (§3); synthetic fallback parameters recorded
      (§4, seed 42)
- [x] No probe copy retained — HEAD/GET probes only (largest single fetch 262 KB,
      Fox feed, discarded); nothing written to data/raw/ or data/processed/
- [ ] Unverified — for the coder to measure, not assumed here: exact final N per
      outlet after the 14-day `pubDate` filter; actual earliest `pubDate` per outlet
      (feeds may not reach back 14 days); final topic dictionary hit rates and the
      30-article sample-review agreement rate; chi-square cell counts (sparse-cell
      fallback decision); VADER version to pin

## Cross-check the coder must run (before the tester starts)

After collecting the corpus, verify per outlet: (1) every stored article's
`pub_date` is inside 2026-11-08–2026-11-22 and its URL is unique (no duplicates);
(2) the sum of per-outlet counts equals the corpus total; (3) recompute VADER
compound for 5 hand-picked titles and confirm the pipeline's score matches a
direct `vaderSentiment` call to 3 decimal places; (4) confirm the topic dictionary
in code is byte-identical to the one printed in the README. If any outlet returns
zero usable articles in the window, report it in the insights memo with its feed
status — do not silently drop the outlet from the tables.

---

## Handoff — researcher → planner

1. **What was produced:** this brief —
   `day-15-political-news-coverage-analyzer/research_brief.md`.
2. **Verified numbers:** RSS feeds all HTTP 200 on 2026-11-22 — NYT 10 items,
   WSJ 20, Fox 25, CNN 50, NPR 10, BBC 32 (147 items across the six feeds at
   probe time). GDELT DOC API: one HTTP 200 (5 articles, 2,042 bytes), then
   HTTP 429 twice with "one every 5 seconds" (persisted past a 20 s pause).
   AP RSS: 000 then 403. Reuters RSS: 401. Window 2026-11-08–2026-11-22.
3. **Known gaps:** AP and Reuters are excluded (blocked feeds) — corpus is 6
   outlets, not 8; RSS gives title + description only, no full text; feeds with
   10 items may not cover the full 14-day window (coder must report actual
   coverage per outlet); GDELT is rate-limited and optional-only; final N, topic
   hit rates, sample-review agreement and the sparse-cell test decision are for
   the coder to measure.
4. **Planner's first step:** read §1a (explicit corpus: 6 outlets, window,
   RSS-only) and §2 (attention share, frozen keyword topics + sample review,
   VADER thresholds, chi-square/ANOVA-or-Kruskal–Wallis, and the nonpartisan
   rules that must appear on README, insights summary, notebook and dashboard),
   then fix the file tree around an RSS-collected, 6-outlet comparison build:
   collected corpus + topic/attention/sentiment tables + source-comparison
   report with sample review and limitations, no bias score, no model.
