# Day 15 — Political News Coverage Analyzer: Build Plan

**Status:** PLAN — planner sign-off complete (AGENTS.md, stage 2).
**Source of truth:** `research_brief.md` (2026-11-22) + this plan. **If brief
and plan disagree, the plan wins and the difference is noted in §11.** The
coder must reuse the brief + this plan. **No extra web searches.**
**Roadmap entry (verbatim):** "Compare topics, attention, and language
sentiment across an explicitly defined news corpus; do not equate sentiment
with factual bias. GitHub deliverable: Source-comparison report with sample
review and limitations."
**Victor's decisions (standing, non-negotiable):** descriptive ONLY —
**NO predictive model, NO bias score, NO leaning score**. Source-comparison
report with sample review and limitations. No causal claims.

> **SCAFFOLD NOTE (planner stage, 2026-11-22).**
> The day folder already existed with `research_brief.md` in it and a
> scaffold `plan.md` stub (plus a stray researcher checkpoint line at its
> end) — the orchestrator never overwrites an existing folder, so the
> planner replaced the whole stub with this plan. The coder fills in the
> remaining scaffold placeholders per §5/§6 — no scaffold step remains.
> The slug is correct (no double prefix:
> `day-15-political-news-coverage-analyzer`, not
> `day-15-day-15-…`).

| Item | Value |
|---|---|
| Fetch date | 2026-11-22 |
| Source | Outlet RSS feeds (6 outlets, no key, no login) — NYT, WSJ, Fox News, CNN, NPR, BBC News (US coverage); GDELT DOC API v2 optional cross-check only |
| Expected corpus | ~147 items at probe time across the six feeds; final N per outlet confirmed by the coder after the 14-day `pubDate` filter — no minimum N is guaranteed |
| Date range | Articles with `pubDate` in **2026-11-08–2026-11-22 inclusive** (14 days ending on the research date) |
| Deliverable | Source-comparison report with sample review and limitations (README + `outputs/insights_summary.md` + Streamlit dashboard + 4 charts) |
| Scope | Descriptive comparison of topics, attention and language sentiment across the explicitly defined 6-outlet corpus. **Sentiment is language tone only — NEVER equated with factual bias. No bias/leaning/left/right language about outlets; no causal claims; same metrics/charts/columns for every outlet.** |

## 1. Problem statement + audience

**Problem.** Readers are told that outlets "cover different things" or
"sound different", but those claims are rarely shown with a corpus anyone
can check: which outlets, which dates, which text, counted how. This
project does the comparison once, in the open: six named national outlets,
one fixed 14-day window (2026-11-08–2026-11-22), title + description text
only, one frozen keyword dictionary for ten topics, one frozen lexicon
(VADER) for language sentiment, and the same attention, topic and
sentiment tables for every outlet — with the source feeds, the window
actually achieved per outlet, the N per outlet, and the limits stated on
every surface.

**Four hard limits are stated up front and labelled on every surface
(README, notebook, insights, dashboard, charts, tables):**

1. **Sentiment is language tone only — never factual bias.** The
   sentence *"Sentiment measures the emotional tone of the words used;
   it is not a measure of factual accuracy, fairness, or political
   bias"* appears in the README, the insights summary, the notebook and
   the dashboard (§2, brief §2 rule 1). No chart title, axis label or
   caption may use the words "bias", "biased", "leaning", "left" or
   "right" to describe an outlet.
2. **Title + description text only — no full article text.** RSS gives
   headline + description + link + publication date per item. Every
   sentiment and topic result is a "headline + summary language" result
   (§3.1). No scraping of linked article pages.
3. **Descriptive only — no predictive model, no bias score, no
   leaning score, no fact-checking.** Nothing in this build ranks
   outlets by bias, predicts what an outlet will cover, or says
   whether any outlet's coverage is true or false (§2, §4).
4. **No causal claims, no editorial adjectives about outlets.**
   Allowed language: "covered more/fewer articles on", "a
   larger/smaller share of its corpus", "more positive/negative
   language on average". Forbidden: "outlet X covered Y because …",
   "X emphasises Y to …", "alarmist", "fair", "obsessed", "ignoring"
   (§2 rules 3–4).

**Audience / decision-maker.** A nonpartisan reader (citizen, student,
journalist) who wants to see, for the same two weeks, what six major
outlets covered, how much attention each topic got, and how the language
sounded — and a data reviewer checking the method, who wants the explicit
corpus (feed URLs, window, drop counts), the frozen topic dictionary
printed verbatim, a recomputation cross-check on VADER scores, a
30-article sample review with an agreement rate, and every published
number matching the committed CSVs.

## 2. Decisions (frozen)

### 2.0 THE NONPARTISAN GUARDRAIL — first decisions, non-negotiable

These five rules (brief §2, binding on every surface) settle every
judgement call in this build. If any later choice conflicts with one of
them, the rule wins.

- **RULE 1 — Sentiment ≠ factual bias, stated everywhere.** The
  sentence in §1 limit 1 (or its exact equivalent) appears in the
  README, the insights summary, the notebook and the dashboard. No
  chart title, axis label or caption uses "bias", "biased", "leaning",
  "left" or "right" to describe an outlet. The words "left"/"right"
  may appear only inside quoted article titles, never as an outlet
  label.
- **RULE 2 — Same metrics, same charts, same table columns for every
  outlet.** No outlet is the reference group; no outlet is singled out
  for commentary beyond what the numbers say. Every chart shows all
  six outlets (or states why an outlet is absent — e.g. zero usable
  articles in the window, §3.3).
- **RULE 3 — No causal claims.** Never "outlet X covered Y because …"
  or "X emphasises Y to …". Allowed language is §1 limit 4.
- **RULE 4 — No editorial adjectives about outlets or coverage**
  ("alarmist", "fair", "obsessed", "ignoring") — report the count, the
  share, the mean sentiment and its CI.
- **RULE 5 — Every chart and table states its coverage** (outlets,
  date window actually achieved per outlet, N per outlet,
  title+description text only) and its source (RSS feed URLs, GDELT
  query if used, VADER version). "Most/least covered" always means by
  the stated metric (count or share), with the outlet, topic and
  window named in the title.

- **Tester gate (mandatory):** the tester verifies the rules were
  actually used — a test asserts the guardrail sentence appears in
  README, insights summary, notebook and app; a test asserts no
  forbidden word ("bias", "biased", "leaning", "left", "right") appears
  in any chart title/caption or dashboard heading describing an outlet
  (quoted article titles excluded); a test asserts every committed
  table carries the same columns for all six outlets; a test asserts
  the topic dictionary in code is byte-identical to the one printed in
  the README. If any rule is violated, the build fails.

### 2.1 Research questions (exactly 3)

1. **What topics did each outlet cover, and how much attention did
   each topic get?** Article counts and within-outlet attention shares
   per topic per outlet (§4.1), plus the corpus-wide share.
2. **How does the language sentiment of coverage differ across outlets
   and topics?** Mean VADER compound (with 95% CI), median, and %
   positive / neutral / negative per outlet and per topic (§4.2) —
   differences in *language*, nothing more.
3. **Are the topic and sentiment differences across outlets larger
   than chance?** Chi-square on the topic × outlet table and
   ANOVA-or-Kruskal–Wallis on sentiment by outlet, with corrected
   pairwise tests only (§4.3).

### 2.2 Other frozen decisions

- **Corpus is exactly the brief's §1a six outlets and window.** AP and
  Reuters are excluded (verified blocked — AP 000 then 403, Reuters
  401). Do not add them without a verified working feed.
- **FEC / election data (roadmap "suggested data") is NOT the corpus.**
  The roadmap lists "FEC campaign finance datasets; official election
  data; Census" as suggested data, but those are the wrong data type
  for a news-coverage comparison — Day 13 already covered FEC finance,
  Day 14 covered election turnout. They are recorded as considered and
  not used; the planner may cite Day 13/14 findings as context only,
  and the coder must not re-fetch FEC data for this day (brief §1c).
- **No Power BI file:** no `.pbix` is produced (same decision as
  Days 8–14 — a `.pbix` cannot be built or verified in this
  environment). The source comparison is delivered as the Streamlit app
  + static charts.
- **GDELT is optional cross-check only** (§3.1). The build must succeed
  on RSS alone; GDELT failing (429) is NOT a fallback trigger.
- **The topic dictionary (§4.1) is frozen in this plan.** No tuning
  after seeing results. The coder copies it verbatim into
  `src/topics.py` and prints it verbatim in the README; the tester
  asserts byte-identity (§2.0).

## 3. Data — source, endpoints, fetch rules, provenance, licence

### 3.1 Source and download (verified, from the brief — copy, do not re-search)

- **Source:** outlet RSS feeds, fetched for analysis. No key, no login,
  no rate limit observed (brief §1). One GET per feed at build time
  (6 requests total), parsed with `feedparser`, raw XML stored verbatim
  in `data/raw/<outlet>_rss.xml` (small files, committed as the
  provenance record — each feed was 8–262 KB in the probe; total
  expected well under the 1 MB/file and 5 MB/day rules).

| Outlet | Feed URL (verified 2026-11-22) | Probe result |
|---|---|---|
| The New York Times | `https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml` | HTTP 200, **10 items** |
| The Wall Street Journal | `https://feeds.a.dj.com/rss/RSSWorldNews.xml` | HTTP 200, **20 items** |
| Fox News | `https://moxie.foxnews.com/google-publisher/latest.xml` | HTTP 200, **25 items** |
| CNN | `http://rss.cnn.com/rss/edition.rss` | HTTP 200, **50 items** |
| NPR | `https://feeds.npr.org/1001/rss.xml` | HTTP 200, **10 items** |
| BBC News (US coverage) | `https://feeds.bbci.co.uk/news/rss.xml` | HTTP 200, **32 items** |

- **Date window:** articles with `pubDate` in **2026-11-08–2026-11-22
  inclusive** (14 days ending on the research date). RSS feeds are
  rolling "latest N items" lists, not archives, so the window is
  enforced by filtering on `pubDate` at collection time; items outside
  the window are dropped and the drop count per outlet is recorded.
  **Expected coverage warning:** feeds holding only 10 items (NYT, NPR)
  may cover fewer than 14 days — the coder must report the actual
  earliest `pubDate` per outlet in `data_source.json` and in the report,
  and must NOT claim a full 14-day window for an outlet whose feed does
  not reach back that far.
- **Fields kept per article:** `outlet, title, description, link,
  pub_date, guid`. **Deduplicate by URL.** No scraping of the linked
  article pages — RSS text only.
- **Corpus size (estimate, not a claim):** the six feeds held 147 items
  at probe time; after the 14-day `pubDate` filter the collected corpus
  will be smaller (RSS lists are rolling and the newest items dominate).
  The coder records the exact final N per outlet; no minimum N is
  guaranteed here.
- **GDELT DOC API v2 — OPTIONAL cross-check only (brief §1b):**
  `https://api.gdeltproject.org/api/v2/doc/doc`, free, no key. Verified
  working once (2026-11-22: `query=politics&mode=artlist&maxrecords=5
  &format=json&timespan=1d` → HTTP 200, 5 articles, 2,042 bytes), then
  rate-limited twice (HTTP 429, "Please limit requests to one every 5
  seconds", persisting past a 20 s pause). **Build rule: at most one
  GDELT call, spaced ≥ 60 s from any other GDELT call, with exponential
  backoff (60 s, 120 s) and a hard stop after 3 attempts; a persistent
  429 means GDELT is skipped, not retried all day.** The bare docs URL
  also returned 429 — do not use a bare-URL health check. Any GDELT
  query must include `sourcelang=english&sourcecountry=US`. If used,
  the plan fixes the single permitted form: one `timelinevol` query
  for overall volume context (`query=politics&mode=timelinevol
  &timespan=14d&sourcelang=english&sourcecountry=US&format=json`) —
  not one query per outlet. Record the exact query string and the
  429/backoff behaviour in `data_source.json`. GDELT is NOT the primary
  source and the build must succeed with RSS alone. Attribution if used:
  "Source: GDELT Project (https://www.gdeltproject.org/)".
- **Licence / attribution:** RSS feeds are the outlets' own content,
  fetched for analysis. **Do not republish full article text** — the
  repo stores headlines, descriptions and links only, plus derived
  counts and scores. Attribute each outlet by name with a link to its
  site in README + `data/README.md`. `vaderSentiment` is MIT-licensed;
  record the pinned version in `requirements.txt` and
  `data_source.json`. No personal data is handled: all figures are
  article-level aggregates from public feeds.

### 3.2 Cleaning rules (frozen — the tester tests these)

Applied in this order; every step's excluded-row count is recorded in
`data_source.json` and reported in `data/README.md`:

1. **Download:** one GET per feed per build (`--live`); cache under
   `data/raw/`; re-use with `--use-cache`. One retry after 60 s on HTTP
   429/5xx, then stop and report — never hammer the host. Store the raw
   XML verbatim (`data/raw/<outlet>_rss.xml`); record each feed's HTTP
   status, byte size and item count before filtering.
2. **Parse:** `feedparser` only. Keep `title, description, link,
   pub_date, guid` per item. Items missing a `link` or a parseable
   `pub_date` are dropped and counted (a missing link cannot be
   deduplicated; a missing date cannot be window-checked).
3. **Window filter:** keep only items whose `pub_date` falls in
   2026-11-08–2026-11-22 inclusive. Record the drop count per outlet
   and the actual earliest/latest `pub_date` per outlet.
4. **Deduplicate by URL** (exact link match), keeping the first;
   record the duplicate count per outlet (expected 0–small).
5. **Text:** analysis text = `title + " " + description`, lowercased
   for topic matching; VADER runs on the original-cased text (VADER
   uses capitalisation and punctuation as signals — do not lowercase
   before scoring). Empty title + description → topic `Other`,
   sentiment compound 0.0 (neutral), counted and recorded.
6. **Topic assignment:** frozen dictionary (§4.1) — count keyword hits
   per topic on the lowercased text; assign the topic with the most
   hits; ties → the topic whose keyword appears earliest in the text;
   zero hits → `Other`. No tuning after seeing results.
7. **Sentiment:** VADER compound on the analysis text (§4.2); standard
   thresholds ≥ +0.05 positive, ≤ −0.05 negative, otherwise neutral.
8. **No imputation, no dropping of outlets.** If an outlet returns zero
   usable articles in the window, report it in the insights memo with
   its feed status — do not silently drop the outlet from the tables
   (brief §5 cross-check).

### 3.3 Cross-checks (frozen — run before the tester starts)

- **Corpus integrity (mandatory):** per outlet — (1) every stored
  article's `pub_date` is inside 2026-11-08–2026-11-22 and its URL is
  unique (no duplicates); (2) the sum of per-outlet counts equals the
  corpus total; (3) every article has exactly one topic assigned
  (including `Other`); (4) every article has a VADER compound in
  [−1, +1] and a sentiment label. Any failure stops the build and is
  reported as a defect.
- **VADER recompute check (mandatory):** recompute the VADER compound
  for 5 hand-picked titles and confirm the pipeline's score matches a
  direct `vaderSentiment` call to 3 decimal places (brief §5).
- **Topic dictionary check (mandatory):** confirm the dictionary in
  code is byte-identical to the one printed in the README (brief §5) —
  the tester asserts this.
- **Attention-share spot-check (mandatory, the hand-validation metric
  — §4.4):** hand-recompute one attention-share cell from
  `articles.csv` (see §4.4 for the exact procedure).

### 3.4 Data-size and commit rule (READ CAREFULLY)

- The six raw RSS XML files total **well under 5 MB** (each 8–262 KB at
  probe time, each < 1 MB) — inside the portfolio rule (files < 1 MB
  each, < 5 MB per day folder). Therefore the **raw XMLs ARE committed**
  as the provenance record (same rule as Day 1's raw JSONs).
- **`.gitignore` MUST exclude only the standard lines plus the
  synthetic line** `data/raw/*_synthetic.json` (§3.5). There is no
  large download this day (no shapefile, no zip) — nothing else in
  `data/` is excluded.
- **`.gitignore` must NOT exclude `data/` itself** — all processed
  files in §3.5 and the six raw XMLs are committed. (Day 13/14 lesson:
  the validator flags any broad `data/` exclusion, and the tester diffs
  `.gitignore` against this list before sign-off.)
- **The pipeline fetches the feeds at build time** (`--live`) and
  caches them under `data/raw/` for re-use (`--use-cache`).
  `--offline` runs from the committed XMLs + processed files only (no
  network) and regenerates charts + summaries from them.
- **`.gitignore` otherwise follows the scaffold default:**
  `__pycache__/`, `.venv/`, `venv/`, `.env`, `*.key`, `*.log`,
  `.streamlit/secrets.toml`, `.pytest_cache/`,
  `.ipynb_checkpoints/`, plus the synthetic line above. The tester diffs
  `.gitignore` against this list before sign-off.

### 3.5 Committed processed files (all < 1 MB; regenerable with one command)

| File | Contents |
|---|---|
| `data/processed/data_source.json` | Sources, feed URLs, HTTP statuses, byte sizes, fetch date, item counts before/after the window filter per outlet, drop + duplicate counts per outlet, actual earliest/latest `pub_date` per outlet, GDELT query + 429/backoff behaviour if used, VADER version, metric definitions, cross-check results (corpus integrity, VADER recompute, dictionary check), manual validation (§4.4), versions |
| `data/processed/articles.csv` | One row per collected article: `outlet, title, description, link, pub_date, guid, text, topic, vader_compound, sentiment_label` |
| `data/processed/topic_attention.csv` | One row per (outlet × topic): `outlet, topic, n_articles, attention_share_pct, wilson_ci_low, wilson_ci_high, outlet_total` — plus corpus-wide rows (`outlet = ALL`) with the corpus-wide share |
| `data/processed/sentiment_by_outlet.csv` | One row per outlet: `outlet, n, mean_compound, ci_low, ci_high, ci_method, median_compound, pct_positive, pct_neutral, pct_negative` |
| `data/processed/sentiment_by_topic.csv` | One row per (outlet × topic) with n ≥ 1, same columns as above (groups with n < 5 flagged `small_n = True` and not used for within-outlet topic tests, §4.3) |
| `data/processed/sample_review.csv` | The 30 sampled articles (§4.5): `outlet, title, link, assigned_topic, reviewer_topic, agree` |
| `data/processed/stats_results.json` | Chi-square (χ², df, p, expected-cell minimum, sparse-cell decision), ANOVA-or-Kruskal–Wallis (test used + why, statistic, p), pairwise tests (method, correction, p-values), normality results (Shapiro–Wilk per outlet), sentiment-by-topic test results where n ≥ 5 |

- The committed processed CSVs are the offline-reproducible record:
  every number in the README, insights and dashboard must match them.
- **Offline rule (Day 5/6 lesson):** `--offline` must NOT clobber
  `data_source.json` fields recorded by a live run (`source: "live"`,
  counts, fetch date, cross-checks). It regenerates only the derived
  tables/charts from the committed XMLs/CSVs; **a test asserts this —
  the offline run skips writing `data_source.json` entirely when a live
  record already exists.** **CI-flake lesson (Day 9, 2026-11-13):** the
  offline-reproduction test compares regenerated floats with a
  **tolerance** (absolute ≤ 0.01 on shares in pp and on compound scores,
  relative ≤ 1e-6 elsewhere) — never byte-exact — because environment
  rounding flakes byte comparisons.

### 3.6 Fallback, licence, attribution

- **Synthetic fallback (only if all RSS feeds fail):** per brief §4 —
  retry once after 60 s per feed, then stop and report to the
  orchestrator — **do not silently substitute synthetic data**. If a
  synthetic fallback were ever authorised, it must be built from the
  brief's documented parameters (6 outlets × 10 topics mimicking the
  probed feed sizes, 10–50 articles per outlet, total ~150 articles;
  titles drawn from a small fixed template pool per topic, e.g. "Markets
  rise as …", "Hospital staffing …"; descriptions one sentence;
  `pub_date` uniform in 2026-11-08–2026-11-22; sentiment assigned by
  construction so the VADER pipeline still runs end-to-end; seed 42),
  stored as `data/raw/*_synthetic.json` (git-ignored, NEVER overwrites
  real data), recorded in `data_source.json` as `synthetic: true,
  seed: 42`, and labelled "SYNTHETIC — NOT REAL DATA" in every chart,
  the notebook, and the README. Methods (§4) are unchanged. Not
  expected to be needed (all six RSS feeds probed HTTP 200 with real
  items). **GDELT alone failing is NOT a fallback trigger — RSS alone
  is a complete build.**
- **Licence:** outlet RSS content is the outlets' own — headlines,
  descriptions and links only, no full article text republished.
  Attribution per outlet by name with a link to its site in README +
  `data/README.md`. VADER (`vaderSentiment`) MIT-licensed. GDELT (if
  used): "Source: GDELT Project (https://www.gdeltproject.org/)".
- **No Power BI file:** no `.pbix` is produced (§2.2).

## 4. Analysis — definitions (from the brief, frozen; planner decisions in §11)

### 4.1 Topic assignment + attention (DECIDED — exact, from brief §2)

- **Frozen topic dictionary** (defined once in `src/topics.py`, printed
  verbatim in the README — the tester asserts byte-identity). Ten
  topics; matching is on lowercased `title + " " + description`, one hit
  counted per keyword occurrence per topic (a keyword appearing twice
  counts twice). Assignment: most hits wins; ties → the topic whose
  keyword appears earliest in the text; zero hits → `Other`. `Other`
  has no keywords — it is the fallback only.

| Topic | Keywords (lowercase, matched as substrings on lowercased text) |
|---|---|
| Economy | economy, economic, inflation, jobs, unemployment, wages, market, stock, recession, gdp, interest rate, federal reserve, trade, tariff, deficit, budget, consumer price, mortgage |
| Healthcare | health, healthcare, hospital, doctor, medicare, medicaid, vaccine, disease, drug, pharmaceutical, insurance, clinic, patient, mental health |
| Immigration | immigration, immigrant, migrant, border, asylum, deportation, visa, citizenship, refugee, customs |
| Climate/Energy | climate, energy, carbon, emission, renewable, solar, wind power, oil, gas price, electric vehicle, wildfire, hurricane, drought, environment |
| Foreign policy | foreign policy, ukraine, russia, china, taiwan, middle east, israel, gaza, nato, diplomacy, sanction, war, military, defense, treaty, summit |
| Elections & campaigns | election, campaign, vote, voter, candidate, polling, poll, ballot, primary, democrat, republican, congress, senate, house of representatives, governor, president, white house |
| Crime & justice | crime, police, court, trial, justice, prison, shooting, murder, arrest, lawsuit, supreme court, judge, gun, fentanyl |
| Technology & AI | technology, artificial intelligence, ai, tech, cybersecurity, cyberattack, data breach, social media, smartphone, semiconductor, robot, algorithm |
| Education | education, school, teacher, student, college, university, tuition, curriculum, classroom, graduation, childcare |
| Other | *(no keywords — fallback for zero hits)* |

- **Known limit (stated on every surface showing a topic number):**
  keyword matching is crude — a headline can mention a word without
  being about that topic. The report therefore includes the sample
  review (§4.5): the agreement rate is the honest measure of how far
  the dictionary can be trusted, and it is reported next to every
  topic finding, never hidden.
- **Attention share (PRIMARY)** = `articles(outlet, topic) ÷
  articles(outlet, all topics) × 100` (within-outlet share, so outlets
  with different feed sizes are comparable). Also report the
  corpus-wide share `articles(topic) ÷ articles(all) × 100`. **Never
  compare raw counts across outlets as "attention" without the share
  beside them** — feed sizes differ by design (10 vs 50 items at probe
  time). Every share carries a Wilson 95% CI (§4.3). Every number is
  reported with its N beside it; no rate is reported without its
  denominator.

### 4.2 Language sentiment (DECIDED — exact, from brief §2)

- **VADER** (`vaderSentiment`, pinned version) applied to
  `title + " " + description` of each article, on the original-cased
  text. Compound score in [−1, +1]; standard VADER thresholds:
  **≥ +0.05 positive, ≤ −0.05 negative, otherwise neutral**. Report per
  outlet and per topic: mean compound with 95% CI, median, and the %
  positive / neutral / negative. **VADER is a general-purpose
  social-media lexicon — it was not built for news text, and that
  limitation must be stated wherever sentiment is shown.** No other
  sentiment model is used; no model is trained.
- **CI rule (plan fixes):** every mean sentiment carries a 95% CI —
  t-interval by default; if the compound distribution for that group
  has |skew| > 1, bootstrap with 1,000 resamples (seed 42) instead, and
  the `ci_method` column in the processed CSVs states which was used.
  Every share carries a Wilson 95% CI. **No point estimate is shown
  without its interval in the report or dashboard.**

### 4.3 Statistical comparisons (DECIDED — exact, from brief §2)

- **Topic × outlet:** chi-square test of independence on the 6 × 10
  contingency table of article counts (report χ², degrees of freedom,
  p-value). **Sparse-cell rule (plan fixes):** if any expected cell
  count < 5, collapse the 10 topics into the 4 largest topics by corpus
  count + "All other topics" (a 6 × 5 table) and re-check; if any
  expected cell is still < 5, run chi-square on the full 6 × 10 table
  but report a permutation p-value (10,000 label shuffles, seed 42)
  alongside the asymptotic p-value, and state which p-value the
  conclusion rests on. Never silently run chi-square on sparse cells.
- **Sentiment across outlets:** test normality per outlet with
  Shapiro–Wilk on the compound scores; if every outlet's p > 0.05,
  one-way ANOVA; otherwise Kruskal–Wallis. Report which test was used
  and why. Pairwise outlet differences only with a stated correction
  (Tukey HSD after ANOVA — `scipy.stats.tukey_hsd`; Dunn's test after
  Kruskal–Wallis — pairwise Mann–Whitney U with Bonferroni correction,
  implemented in `src/stats.py`); **never report uncorrected pairwise
  p-values as findings.**
- **Sentiment by topic within an outlet:** same test family as above,
  topic as the grouping variable; report only if N per group ≥ 5
  (groups with n < 5 are flagged `small_n = True` in
  `sentiment_by_topic.csv` and excluded from the test).
- **Interpretation rule:** a significant result is reported as "the
  distribution of topics / the average language tone differs across
  outlets in this corpus and window" — never as evidence about an
  outlet's fairness, accuracy or intent, and never as a bias ranking.

### 4.4 Hand-validation metric (DECIDED — the tester checks exactly this)

The tester hand-validates **one attention-share cell** and records it in
`data/README.md` and `test_report.md`:

1. From the committed `data/processed/articles.csv`, pick the
   (outlet, topic) cell with the **largest attention share** in
   `topic_attention.csv`.
2. Count by hand (filter + count in the CSV, no pipeline code) the
   articles from that outlet assigned to that topic, and the outlet's
   total article count.
3. Recompute `count ÷ outlet_total × 100` and compare with the
   committed `attention_share_pct` for that cell — **must match to
   0.01 percentage points**.
4. Also recompute the Wilson 95% CI for that cell by hand (standard
   Wilson formula, z = 1.96) and compare with the committed
   `wilson_ci_low` / `wilson_ci_high` — **must match to 0.01 pp**.

The brief's VADER cross-check (§3.3) is a second, separate check the
tester also runs: recompute VADER compound for 5 hand-picked titles
against a direct `vaderSentiment` call, matching to 3 decimal places.
Both checks are recorded; the attention-share cell is the named
hand-validation metric for §8.

### 4.5 Sample review (DECIDED — roadmap deliverable)

- **Design:** a random sample of **30 articles, 5 per outlet**,
  stratified by outlet, drawn with seed 42 from `articles.csv` after
  collection. The sample is fixed once drawn — no re-drawing to improve
  the agreement rate.
- **Review:** for each sampled article the reviewer reads the title (+
  description) and records `reviewer_topic` — the topic a human reader
  would assign — alongside the dictionary's `assigned_topic`, in
  `data/processed/sample_review.csv`. The reviewer is the tester (a
  human judgement, recorded, not a pipeline output).
- **Agreement rate** = `agreeing articles ÷ 30 × 100`, reported in the
  insights summary, the README and the dashboard next to every topic
  finding, with the per-outlet agreement counts. Disagreements are
  listed (title + assigned vs reviewer topic) — the review is a
  limitation check, not a pass/fail gate: **no minimum agreement rate
  is required**, but the rate must be reported honestly and the
  dictionary must not be tuned after seeing it.
- **Sample-review table** in the dashboard shows all 30 rows (outlet,
  title, assigned topic, reviewer topic, agree).

### 4.6 Insights structure (DECIDED)

`outputs/insights_summary.md` carries one finding per §2.1 question with
exact numbers, the attention-share table (with N and Wilson CIs), the
sentiment table (mean, CI, median, % positive/neutral/negative), the
statistical test results (χ²/df/p, ANOVA-or-Kruskal–Wallis + pairwise
correction), the sample-review agreement rate with the disagreement list,
and limitations (descriptive only, no model, no bias score; title +
description text only; VADER not built for news text; keyword matching
is crude; feeds are rolling latest-N lists so the window actually
achieved per outlet may be shorter than 14 days; GDELT optional and
rate-limited). No finding without a number; no recommendation beyond
"what the data shows" — this is a transparency project, not an advice
product, and the insights say so. The guardrail sentence (§1 limit 1)
appears at the top of the insights summary.

## 5. File tree (exact — build only this)

```
day-15-political-news-coverage-analyzer/
├── README.md  requirements.txt  .gitignore  pyproject.toml  LICENSE
├── .pre-commit-config.yaml
├── research_brief.md  plan.md  coder_handoff.md  test_report.md
├── optimizer_handoff.md  publisher_handoff.md
├── data/
│   ├── README.md
│   ├── raw/
│   │   ├── nyt_rss.xml          (committed)
│   │   ├── wsj_rss.xml          (committed)
│   │   ├── fox_rss.xml          (committed)
│   │   ├── cnn_rss.xml          (committed)
│   │   ├── npr_rss.xml          (committed)
│   │   └── bbc_rss.xml          (committed)
│   └── processed/
│       ├── data_source.json
│       ├── articles.csv          (one row per collected article)
│       ├── topic_attention.csv   (one row per outlet × topic + corpus-wide rows)
│       ├── sentiment_by_outlet.csv   (one row per outlet)
│       ├── sentiment_by_topic.csv    (one row per outlet × topic)
│       ├── sample_review.csv     (30 rows, 5 per outlet)
│       └── stats_results.json
├── notebooks/analysis.ipynb
├── src/
│   ├── __init__.py
│   ├── data_pipeline.py
│   ├── topics.py
│   ├── sentiment.py
│   ├── stats.py
│   ├── make_charts.py
│   └── app.py
├── outputs/
│   ├── insights_summary.md
│   └── charts/
│       ├── 01_attention_share_by_topic.png
│       ├── 02_mean_sentiment_by_outlet.png
│       ├── 03_sentiment_by_topic_heatmap.png
│       └── 04_sentiment_distribution.png
├── screenshots/
│   └── dashboard.png
└── tests/
    └── test_pipeline.py
```

Notes: the scaffold's `tests/test_smoke.py` is **DELETED** and replaced by
`tests/test_pipeline.py` (do not keep two test files). The scaffold's
placeholder `README.md`, `data/README.md`, `notebooks/analysis.ipynb`,
`outputs/insights_summary.md`, `requirements.txt` and `pyproject.toml`
are filled in by the coder — not new files. No extra modules, no extra
charts, no `.pbix`, no model, no bias score, no GDELT module (the optional
GDELT call, if attempted, lives inside `data_pipeline.py` — §6). The
scaffold's `requirements.txt` is Day 1's list — the coder replaces it
with the §6 pinned stack (Day 14 stack **plus feedparser +
vaderSentiment**, minus geopandas — there is no map this day — and no
scikit-learn, no openpyxl: no model and no XLSX).

## 6. Per-file responsibilities

| File | Responsibility |
|---|---|
| `src/data_pipeline.py` | Fetch the 6 RSS feeds (primary; one GET per feed, 1 retry after 60 s on 429/5xx, then stop and report); parse with `feedparser`; store raw XML verbatim under `data/raw/`; apply cleaning rules §3.2 in order, counting every exclusion/duplicate; run the corpus-integrity + VADER-recompute + dictionary cross-checks (§3.3); build all 6 processed files (§3.5); write `data_source.json` (live fields); optional GDELT call per §3.1 (at most one, ≥ 60 s spacing, backoff 60 s/120 s, hard stop after 3 attempts, 429 → skip and record); modes `--live` / `--offline` / `--use-cache` / `--synthetic` (brief §4 generator, seed 42). `--offline` skips writing `data_source.json` when a live record exists (§3.5). |
| `src/topics.py` | Pure topic functions, no I/O, no network — all tested: the frozen `TOPIC_KEYWORDS` dict (§4.1, verbatim), `assign_topic(text)` (most hits wins; ties → earliest keyword position; zero hits → `Other`), `attention_share(count, total)`, `wilson_ci(k, n)` (Wilson 95% CI, z = 1.96) |
| `src/sentiment.py` | Pure sentiment functions, no I/O — all tested: `compound_score(text)` (VADER compound on `title + " " + description`), `sentiment_label(compound)` (≥ +0.05 positive, ≤ −0.05 negative, else neutral), `summarise(scores)` (mean, t- or bootstrap 95% CI with `ci_method`, median, % positive/neutral/negative) |
| `src/stats.py` | Pure statistics functions, no I/O — all tested: `chi_square_topic_outlet(table)` (χ², df, p, min expected cell, sparse-cell decision per §4.3), `permutation_pvalue(table, n_permutations=10000, seed=42)`, `sentiment_test_by_outlet(df)` (Shapiro–Wilk per outlet → ANOVA or Kruskal–Wallis, statistic, p, test used + why), `pairwise_tests(...)` (Tukey HSD after ANOVA; Dunn via pairwise Mann–Whitney U + Bonferroni after Kruskal–Wallis), `bootstrap_ci(values, n_resamples=1000, seed=42)` |
| `src/make_charts.py` | Exactly 4 PNGs (§7), matplotlib `Agg`, offline from processed CSVs only, every chart footnoted with the source (RSS feed URLs) + coverage (outlets, window actually achieved per outlet, N per outlet, title+description text only) + VADER version + the guardrail sentence in short form ("Sentiment is language tone, not factual bias") where space allows; synthetic label if applicable |
| `src/app.py` | Streamlit dashboard loading processed CSVs only (offline): KPI row (corpus total N, N per outlet, topics covered, sample-review agreement rate); the 4 charts embedded; attention-share table (with N + Wilson CIs); sentiment tables (mean, CI, median, % pos/neu/neg); statistical test results; sample-review table (30 rows); methods + limitations panel (descriptive only, no model, no bias score; title+description text only; VADER not built for news text; keyword matching crude; rolling-feed window limits; GDELT optional/rate-limited); the guardrail sentence (§1 limit 1) displayed at the top of the dashboard; source links on every section (feed URLs, GDELT if used, VADER); `width="stretch"` (Day 2 lesson — no deprecated `use_container_width`); footer with outlet attribution |
| `notebooks/analysis.ipynb` | Offline top-to-bottom, ≤ 16 cells, 0 error cells via nbconvert, `_find_root()` from the notebook file's own location (Day 1 lesson (e)): load + audit (row counts, window-filter drops + duplicates per outlet, actual earliest/latest `pub_date` per outlet, corpus-integrity checks); attention-share tables; VADER sentiment by outlet and topic; chi-square + ANOVA-or-Kruskal–Wallis with the sparse-cell decision; the 30-article sample review + agreement rate; the 4 charts inline; Q1–Q3 answered with exact numbers; the guardrail sentence in the notebook; the notebook never downloads data itself |
| `tests/test_pipeline.py` | ≥ 15 tests: topic assignment (most-hits wins; tie → earliest keyword; zero hits → `Other`; `Other` has no keywords); attention share (share sums to 100% per outlet; raw counts never presented without share); Wilson CI (bounds contain the share; 0/0 handled); VADER label thresholds (+0.05/−0.05 boundaries; compound in [−1, +1]); dictionary in code byte-identical to the README listing; corpus integrity (every `pub_date` in window, URLs unique, per-outlet counts sum to corpus total, exactly one topic per article); window filter drops out-of-window items and counts them; dedupe by URL; guardrail sentence present in README, insights, notebook and app; no forbidden word in chart titles/captions or dashboard headings (quoted article titles excluded); same columns for all six outlets in committed tables; chi-square sparse-cell rule (fixture with an expected cell < 5 triggers the collapse/permutation path); ANOVA-vs-Kruskal–Wallis selection follows the Shapiro–Wilk rule on fixtures; pairwise tests carry a correction (no uncorrected p-values reported); sample review is 30 rows, 5 per outlet, seed 42 reproducible; offline run does not clobber `data_source.json` live fields; **offline reproduction uses tolerance comparison (Day 9 CI lesson), not byte-exact**; synthetic files never overwrite live files; no committed file > 1 MB, `data/` < 5 MB; `.gitignore` contains the synthetic exclusion while the six raw XMLs are NOT ignored |
| `data/README.md` | Provenance: 6 feed URLs, HTTP statuses, byte sizes, fetch date, item counts before/after the window filter per outlet, drop + duplicate counts, actual earliest/latest `pub_date` per outlet, GDELT query + 429/backoff behaviour if used, VADER version, metric definitions, the frozen topic dictionary verbatim, cross-check results (corpus integrity, VADER recompute, dictionary check), manual validation (§4.4), sample-review method, outlet attribution with links |
| `outputs/insights_summary.md` | One finding per §2.1 question with exact numbers + attention-share table (N + Wilson CIs) + sentiment tables + test results + sample-review agreement rate with disagreement list + limitations (§4.6); guardrail sentence at the top |
| `README.md` | Problem, audience, setup, how to run (live/offline), sample outputs (KPI table + chart thumbnails), headline findings with numbers, attention + sentiment tables, the frozen topic dictionary verbatim, the nonpartisan guardrail (§2.0) stated plainly, validation, limitations, attribution, source links |
| `requirements.txt` | Pinned `==` versions verified in the build venv (Python 3.12.3): Day 14 stack (pandas, numpy, scipy, matplotlib, streamlit, requests, pytest, jupyter, nbformat) **plus feedparser (RSS parsing) and vaderSentiment (VADER lexicon)**. No geopandas (no map), no scikit-learn (no model), no openpyxl (no XLSX) this day. The coder pins the exact versions that install and verify in the build venv and records them — no version is guessed in this plan. No other new runtime dependency without a plan change |
| `pyproject.toml` / `.gitignore` | Scaffold defaults (ruff/black line-length 88; strict mypy, coverage source `src`); `.gitignore` per §3.4 (synthetic excluded; the six raw XMLs and `data/` itself NOT excluded) |

Key function signatures (coder follows these names):

```python
# src/data_pipeline.py
def fetch_feed(url: str, dest: Path) -> Path
def parse_feed(path: Path, outlet: str) -> list[dict]  # feedparser; fields per §3.1
def collect_corpus(outlets: dict[str, str]) -> tuple[pd.DataFrame, dict]  # window filter + dedupe + counts
def gdelt_cross_check() -> dict  # optional, §3.1; at most one call
def write_data_source(path: Path, record: dict) -> None

# src/topics.py
TOPIC_KEYWORDS: dict[str, list[str]]  # §4.1, frozen
def assign_topic(text: str) -> str
def attention_share(count: int, total: int) -> float
def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]

# src/sentiment.py
def compound_score(text: str) -> float
def sentiment_label(compound: float) -> str  # positive / neutral / negative
def summarise(scores: pd.Series) -> dict  # mean, ci_low, ci_high, ci_method, median, pct_*

# src/stats.py
def chi_square_topic_outlet(table: pd.DataFrame) -> dict
def permutation_pvalue(table: pd.DataFrame, n_permutations: int = 10000, seed: int = 42) -> float
def sentiment_test_by_outlet(df: pd.DataFrame) -> dict  # normality → ANOVA or Kruskal–Wallis
def pairwise_tests(df: pd.DataFrame, method: str) -> pd.DataFrame  # corrected p-values only
def bootstrap_ci(values: pd.Series, n_resamples: int = 1000, seed: int = 42) -> tuple[float, float]
```

## 7. Charts (exactly 4, matplotlib, to scale and legible)

All charts: title naming the metric + coverage (outlets, window, N),
labelled axes with units (share in %, compound in [−1, +1]),
source footnote ("Source: outlet RSS feeds — NYT, WSJ, Fox News, CNN,
NPR, BBC News; title + description text only; window 2026-11-08–
2026-11-22; VADER vaderSentiment <version>"), coverage footnote
("Corpus: <N> articles; N per outlet: NYT <n>, WSJ <n>, Fox <n>, CNN
<n>, NPR <n>, BBC <n>; window actually achieved per outlet in
data_source.json"), no truncated axes, legible at 100% zoom. **No chart
title, axis label or caption uses "bias", "biased", "leaning", "left" or
"right" to describe an outlet.** One consistent outlet colour palette,
used identically on every chart (no outlet given a visual advantage);
sentiment charts use a single diverging scale centred at 0 with the
VADER thresholds (±0.05) marked. Every chart states its N.

1. **01_attention_share_by_topic.png** — Attention share by topic and
   outlet. Grouped horizontal bars: one panel per outlet (or one
   grouped chart with outlet facets), x-axis = within-outlet attention
   share (%), bars labelled with share + N; topics sorted by
   corpus-wide share. Title names the metric and window ("Attention
   share by topic and outlet — share of each outlet's corpus,
   2026-11-08–2026-11-22"). Answers Q1.
2. **02_mean_sentiment_by_outlet.png** — Mean VADER compound by outlet
   with 95% CI. Dot-and-whisker: one point per outlet, whiskers = the
   95% CI, dashed lines at the VADER thresholds (+0.05 / −0.05),
   N annotated per outlet; y-axis = mean compound [−1, +1]. Title
   names the metric and text ("Mean language sentiment (VADER
   compound) by outlet — title + description text only,
   2026-11-08–2026-11-22"). Caption: "Sentiment is language tone,
   not factual bias." Answers Q2's outlet half.
3. **03_sentiment_by_topic_heatmap.png** — Mean VADER compound by
   topic × outlet. Heatmap (6 outlets × 10 topics), cell = mean
   compound, annotated with the value + N; cells with n < 5 hatched
   and labelled "small n"; single diverging scale centred at 0.
   Title names the metric and window ("Mean language sentiment
   (VADER compound) by topic and outlet, 2026-11-08–2026-11-22").
   Answers Q2's topic half.
4. **04_sentiment_distribution.png** — Sentiment-label mix by outlet.
   100% stacked horizontal bars: % positive / neutral / negative per
   outlet (VADER thresholds ±0.05), segments labelled with % + N;
   outlets in the same order as chart 01. Title names the metric and
   window ("Share of articles by language-sentiment label and outlet
   (VADER ±0.05), 2026-11-08–2026-11-22"). Caption: "Sentiment is
   language tone, not factual bias." Answers Q2's distribution half.

The Streamlit dashboard embeds the 4 PNGs (as Days 6–14 do) so the README
thumbnails and the app agree.

## 8. Success checklist (roadmap minimum success criteria — all must pass)

- [ ] Problem statement + audience written (§1, in README and this plan)
- [ ] Data source documented: provider (6 RSS feeds), URLs, HTTP
      statuses, byte sizes, fetch date (2026-11-22), item counts
      before/after the window filter per outlet, drop + duplicate
      counts, actual earliest/latest `pub_date` per outlet, GDELT query
      + 429/backoff behaviour if used, VADER version — in
      `data/README.md` and `data/processed/data_source.json`
- [ ] Repeatable prep steps documented (fetch → parse → window filter →
      dedupe → topic assign → VADER → aggregate → charts, with
      `--offline` mode) + metric definitions (§4.1–§4.3) written down
- [ ] **Nonpartisan guardrail (§2.0) stated in the plan and honoured in
      the build**: guardrail sentence in README, insights, notebook and
      dashboard; no bias/leaning/left/right language about outlets; no
      causal claims; no editorial adjectives; same metrics/columns/
      charts for every outlet; every chart/table states its coverage,
      window and source; **tester verified the rules were actually
      used** (guardrail-sentence test, forbidden-word test,
      same-columns test, dictionary byte-identity test — test +
      test_report evidence)
- [ ] **Source-comparison report with sample review and limitations
      delivered** (roadmap deliverable): README + insights summary +
      Streamlit dashboard + 4 charts, with source links on every
      section, KPI row, attention-share table, sentiment tables, test
      results, sample-review table
- [ ] **Topics compared across outlets**: attention shares (with N and
      Wilson CIs) per outlet × topic, plus corpus-wide shares
- [ ] **Language sentiment compared across outlets and topics**: mean
      VADER compound with 95% CI, median, % positive/neutral/negative
      per outlet and per topic — language tone only, never equated
      with factual bias
- [ ] **Statistical comparisons done** (§4.3): chi-square on topic ×
      outlet (with the sparse-cell decision stated), ANOVA-or-
      Kruskal–Wallis on sentiment by outlet (test used + why),
      pairwise tests only with a stated correction, sentiment-by-topic
      tests only where N per group ≥ 5
- [ ] **Sample review done** (§4.5): 30 articles, 5 per outlet, seed
      42; agreement rate reported next to every topic finding, with
      the disagreement list; dictionary not tuned after seeing it
- [ ] **Descriptive only — verified**: no predictive model, no bias
      score, no leaning score, no fact-checking, no causal claims
- [ ] **Title + description text only — verified**: no scraping of
      linked article pages; the limitation stated on every surface
      showing a sentiment or topic number
- [ ] Exactly **4 charts** (§7), drawn to scale and legible, plus a
      functional dashboard: the Streamlit dashboard runs and renders
      (smoke gate below)
- [ ] Interpretation written (`outputs/insights_summary.md`, one finding
      per §2.1 question with exact numbers) + limitations (§4.6)
- [ ] README with setup instructions, sample outputs (KPI table + chart
      thumbnails), validation results, the frozen topic dictionary
      verbatim, the nonpartisan guardrail, and limitations
- [ ] No credentials / private records in the repo; **no copying others'
      code** — all code is Victor's own original work; **data-size rule
      honoured** (no file > 1 MB, `data/` < 5 MB; raw RSS XMLs committed
      per §3.4; `.gitignore` matches §5/§6 and does NOT exclude `data/`)
- [ ] **One metric manually validated by hand** and recorded in
      `data/README.md` (§4.4 — the largest attention-share cell,
      recomputed from `articles.csv` to 0.01 pp, Wilson CI also
      recomputed to 0.01 pp; plus the 5-title VADER recompute to 3
      decimals)
- [ ] Pipeline runs end-to-end from a clean checkout (`pip install -r
      requirements.txt`, `python -m src.data_pipeline --live`,
      `python -m src.make_charts`, `pytest tests/ -q`) — **pytest passing
      both from the repo root and from inside the day folder, with
      coverage at or above the threshold (30, from CHANGELOG.md /
      .github/workflows/ci.yml — the measured floor, Day 8 at 34.94%)**
- [ ] **Notebook runs top-to-bottom without errors** (offline, via
      nbconvert — **exit 0 with 0 error cells** — with `_find_root()`,
      §6)
- [ ] Pinned dependencies in `requirements.txt` (Day 14 stack plus
      feedparser + vaderSentiment; no geopandas, no scikit-learn, no
      openpyxl this day); **`black --check` + `ruff check` clean**;
      **`mypy src tests` clean** (strict-by-default — every `src/`
      function annotated, test functions annotated `-> None`)
- [ ] Streamlit smoke gate passed: **fresh port 8502+**, HTTP 200 on `/`
      and on `/_stcore/health`, **real `screenshots/dashboard.png`**
      captured (**< 1 MB**), server killed and port verified free
- [ ] **Offline pipeline run must NOT clobber `data_source.json`**
      (skip writing it when a live record exists — §3.5, tested)
- [ ] **No base64 strings quoted in docs** (validator false-positive
      rule — never paste base64 content into any `.md` file; the
      validator strips `image/png` blobs from notebooks before scanning,
      but code cells and markdown are still scanned — Day 10/11 lesson)
- [ ] **Orchestrator validate clean** for the day folder
      (`python agents/orchestrator.py --day 15 validate`) — **target
      11/11 checks pass**
- [ ] Charts to scale and legible; frozen-tree check passed immediately
      before push (every file the READMEs reference exists on disk —
      charts, screenshot, CSVs)

## 9. Coder handoff checklist (reference — coder must satisfy all of these before the tester starts)

- [ ] venv exists with pinned deps installed; `black --check` + `ruff check` pass; `mypy src tests` clean; `pytest` passes (≥ 15 tests, coverage ≥ 30, from repo root and from the day folder)
- [ ] `.gitignore` matches §3.4/§5 (synthetic excluded; the six raw XMLs and `data/` itself NOT excluded; nothing else in `data/` excluded)
- [ ] `screenshots/dashboard.png` is a real capture of the running app on a fresh port (8502+), < 1 MB
- [ ] `data/` total < 5 MB, no file > 1 MB; `data_source.json` records live counts, window-filter drops + duplicates, actual earliest/latest `pub_date` per outlet, GDELT behaviour if used, cross-check results
- [ ] Counts verified against §3.1; guardrail (§2.0) implemented — guardrail sentence on all four surfaces, no forbidden words in chart/dashboard text about outlets, same columns for all outlets, dictionary byte-identical to the README listing
- [ ] `tests/test_smoke.py` deleted — only `tests/test_pipeline.py` exists
- [ ] Notebook runs via nbconvert with exit 0 and 0 error cells
- [ ] Build only what §5 lists; no extra web searches; no base64 strings in any doc

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| An RSS feed returns fewer than 14 days of items (NYT/NPR held 10) | Report the actual earliest `pubDate` per outlet (§3.1); never claim a full 14-day window for an outlet whose feed does not reach back that far |
| A feed fails at build time (429/5xx) | 1 retry after 60 s, then stop and report; synthetic fallback (§3.6) only if all feeds fail |
| GDELT 429s again | Optional only — skip it and record the behaviour (§3.1); never a fallback trigger, never retried all day |
| Keyword dictionary mis-assigns topics | Sample review (§4.5) measures it honestly; agreement rate reported next to every topic finding; dictionary never tuned after seeing results |
| VADER misreads news language (not built for news text) | Limitation stated wherever sentiment is shown (§4.2); VADER is the only model, no second model added to "fix" it |
| Chi-square cells are sparse (small corpus) | Sparse-cell rule (§4.3): collapse to 6 × 5, then permutation p-value if still sparse; never silently run chi-square on sparse cells |
| Sentiment distribution is non-normal | Shapiro–Wilk gate (§4.3) picks Kruskal–Wallis + Dunn/Bonferroni; the test used and why are recorded |
| An outlet has zero usable articles in the window | Report it with its feed status in the memo (§3.2 rule 8) — never silently drop the outlet from the tables |
| A sentiment difference is read as a bias ranking | §2.0 Rules 1–4 + tester gate: no bias/leaning/left/right language, no "most biased" ranking, no causal claims |
| Byte-exact offline comparison flakes in CI (Day 9 lesson) | Tolerance-based comparison in the offline test (§3.5) |
| Push-manifest format (Day 14 lesson) | Publisher keeps push manifests **NUL-delimited, paths ending in NUL**; keep them under `~/workspace/` (never `/tmp`); re-check the remote head after any uncertain write |
| Optimizer changes the pytest count (Day 14 lesson) | The optimizer updates the README pytest count itself when it adds a regression test — no follow-up count-fix commit |
| Binaries pushed after code (Day 13/14 lesson) | **Upload the 6 PNGs (4 charts + dashboard screenshot) BEFORE the code push** so CI never sees an incomplete tree; check the post-upload CI run before calling the day complete |
| Base64 passed to `create_or_update_file` (Day 8 lesson) | Never pass base64 content to `create_or_update_file` — it stores the base64 text as the file. Use push-files from disk for file updates, or pass raw text. Never quote base64 strings in docs (§8). |
| GitHub write-approval card times out (Days 10/12/13 lesson) | Push step needs the card allowed first; a timed-out card leaves nothing pending, so a retry starts a fresh card rather than waiting on the old one. Attempt the push ONCE; on policy_denied stop immediately, re-check the head, leave everything staged, report the blocker + resume steps. |
| Day 8 defect — double-prefixed slug | The folder is `day-15-political-news-coverage-analyzer` (verified). Never create a `day-15-day-15-…` folder; if the orchestrator refuses again, replicate the template by hand as the Day 14 planner did (§5 note), never force a second folder. |

## 11. Differences from the brief (plan wins)

- **Topic dictionary keyword lists (§4.1):** the brief names the ten
  topics and the assignment rule (most hits wins; ties → earliest
  keyword; zero hits → `Other`) but gives no keyword lists. The plan
  **fixes** the full keyword list per topic — frozen before the coder
  runs the pipeline, printed verbatim in the README, byte-identity
  asserted by a test.
- **Sparse-cell fallback (§4.3):** the brief says "report Fisher's
  exact test on the collapsed table instead" if any expected cell < 5.
  The plan **fixes** the collapse (4 largest topics + "All other
  topics" → 6 × 5, re-check) and, if cells are still sparse, a
  **permutation p-value (10,000 shuffles, seed 42)** on the full 6 × 10
  table instead of Fisher — Fisher's exact is only defined for 2 × 2
  tables, so a 6 × 10 Fisher is not computable with the pinned stack;
  the permutation p-value is the honest equivalent, and both p-values
  are reported with the conclusion's basis stated.
- **Pairwise tests (§4.3):** the brief names "Tukey HSD after ANOVA, or
  Dunn with Bonferroni after Kruskal–Wallis". The plan **fixes** the
  implementations: `scipy.stats.tukey_hsd` for Tukey HSD, and Dunn's
  test as pairwise Mann–Whitney U with Bonferroni correction in
  `src/stats.py` (no extra dependency).
- **Sentiment CI method (§4.2):** the brief allows "t-interval, or
  bootstrap with 1,000 resamples if the distribution is skewed — state
  which". The plan **fixes** the decision rule: bootstrap (1,000
  resamples, seed 42) when |skew| > 1, otherwise t-interval; the
  `ci_method` column records which was used per group.
- **GDELT form (§3.1):** the brief allows "one `artlist` query per
  outlet … or one `timelinevol` query". The plan **fixes** a single
  permitted form if GDELT is attempted at all: one `timelinevol`
  query for overall volume context — not one query per outlet (six
  calls would breach the verified rate limit).
- **Hand-validation metric (§4.4):** the brief's cross-check (§5)
  covers VADER recompute (5 titles, 3 decimals) and dictionary
  byte-identity. The plan **fixes** the named hand-validation metric
  for §8: the largest attention-share cell, recomputed by hand from
  `articles.csv` to 0.01 pp with its Wilson CI also recomputed to
  0.01 pp.
- **Dependency stack (§6):** the brief named `feedparser` and
  `vaderSentiment` only. The plan **fixes** the Day 14 stack plus
  feedparser + vaderSentiment, minus geopandas (no map), no
  scikit-learn (no model — Victor's decision), no openpyxl — with exact
  versions pinned by the coder from the verified build venv, not guessed
  in this plan.
- **FEC / election data (§2.2):** the brief records the roadmap's
  suggested FEC/election/Census data as "considered and not used for
  the corpus itself". The plan **confirms** this and fixes the rule:
  the coder must not re-fetch FEC data for this day; Day 13/14 findings
  may be cited as context only.
- **Sample-review reviewer (§4.5):** the brief requires a 30-article
  sample review with the agreement rate reported. The plan **fixes**
  the design: stratified 5 per outlet, seed 42, fixed once drawn, the
  tester as reviewer, no minimum agreement rate required, disagreements
  listed.
