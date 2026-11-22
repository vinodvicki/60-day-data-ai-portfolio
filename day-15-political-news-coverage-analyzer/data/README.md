# Data provenance — Day 15 Political News Coverage Analyzer

Sentiment measures the emotional tone of the words used; it is not a measure of factual accuracy, fairness, or political bias.

## Source

- **Provider:** outlet RSS feeds (6 outlets, no key, no login).
- **Fetch date:** 2026-11-22. One GET per feed, parsed with
  `feedparser` (6.0.14), raw XML stored verbatim in `data/raw/`.
- **Window:** articles with `pubDate` in 2026-11-08–2026-11-22
  inclusive (14 days ending on the fetch date).
- **Fields kept per article:** `outlet, title, description, link,
  pub_date, guid`. Analysis text = `title + " " + description`.
  HTML tags stripped and entities unescaped in the stored title and
  description. No scraping of linked article pages — RSS text only.
- **GDELT:** not used (optional cross-check only; skipped — the
  researcher verified on 2026-11-22 that the GDELT DOC API v2
  rate-limits with HTTP 429 after one successful call, and the build
  is complete on RSS alone). Permitted query if ever attempted:
  `query=politics&mode=timelinevol&timespan=14d&sourcelang=english
  &sourcecountry=US&format=json`.
- **Licence / attribution:** RSS feeds are the outlets' own content,
  fetched for analysis. The repo stores headlines, descriptions and
  links only, plus derived counts and scores — no full article text
  is republished. `vaderSentiment` is MIT-licensed. No personal data
  is handled.

| Outlet | Site |
|---|---|
| NYT | https://www.nytimes.com/ |
| WSJ | https://www.wsj.com/ |
| Fox News | https://www.foxnews.com/ |
| CNN | https://www.cnn.com/ |
| NPR | https://www.npr.org/ |
| BBC News | https://www.bbc.com/news |

## Fetch outcome

All six feeds returned HTTP 200 on 2026-11-22.

| Outlet | Feed URL | HTTP | Bytes | Fetched | Dropped: no link/date | Dropped: outside window | Duplicates | Final N | Earliest | Latest |
|---|---|---|---|---|---|---|---|---|---|---|
| NYT | https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml | 200 | 21,419 | 10 | 0 | 0 | 0 | 10 | 2026-11-20 | 2026-11-22 |
| WSJ | https://feeds.a.dj.com/rss/RSSWorldNews.xml | 200 | 13,317 | 20 | 0 | 20 | 0 | 0 | — | — |
| Fox News | https://moxie.foxnews.com/google-publisher/latest.xml | 200 | 258,357 | 25 | 0 | 1 | 0 | 24 | 2026-11-22 | 2026-11-22 |
| CNN | http://rss.cnn.com/rss/edition.rss | 200 | 130,144 | 50 | 4 | 46 | 0 | 0 | — | — |
| NPR | https://feeds.npr.org/1001/rss.xml | 200 | 14,301 | 10 | 0 | 0 | 0 | 10 | 2026-11-21 | 2026-11-22 |
| BBC News | https://feeds.bbci.co.uk/news/rss.xml | 200 | 26,437 | 33 | 0 | 2 | 0 | 31 | 2026-11-11 | 2026-11-22 |

**Corpus total: 75 articles.** WSJ's feed served 20 items dated
January 2025; CNN's feed served 46 items dated April 2023 (plus 4
items with no parseable date). The Fox News feed contained one item
dated 2026-11-25 (after the fetch date), dropped by the window filter.
No outlet is claimed to cover the full 14 days unless its earliest
`pubDate` reaches back that far (best: BBC News, 12 days).

## Row counts and coverage

- `data/processed/articles.csv`: 75 rows, one per collected article.
- `data/processed/topic_attention.csv`: 70 rows — 6 outlets × 10
  topics, plus 10 corpus-wide rows (`outlet = ALL`).
- `data/processed/sentiment_by_outlet.csv`: 6 rows, one per outlet
  (WSJ and CNN have n=0, with empty mean/CI/median).
- `data/processed/sentiment_by_topic.csv`: 27 rows, one per
  outlet × topic with n ≥ 1 (groups with n < 5 flagged `small_n`).
- `data/processed/sample_review.csv`: 20 rows — 5 per outlet with
  articles in the window (NYT, Fox News, NPR, BBC News), seed 42.
  WSJ and CNN had no articles to sample, so the sample is 20, not
  30; see the note in the README and `coder_handoff.md`.
- `data/processed/stats_results.json`: chi-square, sentiment tests,
  pairwise tests, by-topic tests.
- `data/processed/data_source.json`: full provenance record (sources,
  counts, cross-checks, manual validation, versions).

## Metric definitions

- **Attention share** = `articles(outlet, topic) ÷ articles(outlet,
  all topics) × 100` (within-outlet share); corpus-wide share uses
  `articles(all)` as the denominator. Every share carries a Wilson
  95% CI (z = 1.96).
- **Topic assignment:** frozen 10-topic keyword dictionary (below) —
  most hits wins, ties go to the topic whose keyword appears earliest
  in the text, zero hits means Other. Matching is on lowercased
  `title + " " + description`, keywords as substrings, one hit per
  occurrence.
- **Sentiment:** VADER compound on `title + " " + description`
  (original-cased text); ≥ +0.05 positive, ≤ −0.05 negative,
  otherwise neutral. Mean with 95% CI (t-interval by default;
  bootstrap with 1,000 resamples, seed 42, when |skew| > 1;
  intervals clipped to [−1, +1]); median; % positive / neutral /
  negative. VADER is a general-purpose social-media lexicon, not
  built for news text.
- **Tests:** chi-square on the topic × outlet table with the
  sparse-cell rule (collapse to the 4 largest topics + All other
  topics, then permutation p-value, 10,000 shuffles, seed 42);
  Shapiro-Wilk normality gate picks ANOVA or Kruskal-Wallis;
  pairwise tests only with a stated correction (Tukey HSD after
  ANOVA; pairwise Mann-Whitney U with Bonferroni correction after
  Kruskal-Wallis). Sentiment-by-topic tests only where n ≥ 5.

### Frozen topic dictionary (verbatim — identical to `src/topics.py`)

- **Economy:** economy, economic, inflation, jobs, unemployment,
  wages, market, stock, recession, gdp, interest rate, federal
  reserve, trade, tariff, deficit, budget, consumer price, mortgage
- **Healthcare:** health, healthcare, hospital, doctor, medicare,
  medicaid, vaccine, disease, drug, pharmaceutical, insurance,
  clinic, patient, mental health
- **Immigration:** immigration, immigrant, migrant, border, asylum,
  deportation, visa, citizenship, refugee, customs
- **Climate/Energy:** climate, energy, carbon, emission, renewable,
  solar, wind power, oil, gas price, electric vehicle, wildfire,
  hurricane, drought, environment
- **Foreign policy:** foreign policy, ukraine, russia, china, taiwan,
  middle east, israel, gaza, nato, diplomacy, sanction, war,
  military, defense, treaty, summit
- **Elections & campaigns:** election, campaign, vote, voter,
  candidate, polling, poll, ballot, primary, democrat, republican,
  congress, senate, house of representatives, governor, president,
  white house
- **Crime & justice:** crime, police, court, trial, justice, prison,
  shooting, murder, arrest, lawsuit, supreme court, judge, gun,
  fentanyl
- **Technology & AI:** technology, artificial intelligence, ai, tech,
  cybersecurity, cyberattack, data breach, social media, smartphone,
  semiconductor, robot, algorithm
- **Education:** education, school, teacher, student, college,
  university, tuition, curriculum, classroom, graduation, childcare
- **Other:** *(no keywords — fallback for zero hits)*

## Cross-check results

- **Corpus integrity:** passed — every stored article's `pub_date`
  is inside 2026-11-08–2026-11-22, URLs are unique, per-outlet
  counts sum to the corpus total (75), every article has exactly
  one topic, every VADER compound is in [−1, +1] with a valid label.
- **VADER recompute (pipeline):** 5 titles recomputed with a fresh
  `SentimentIntensityAnalyzer` match the pipeline's compound to
  3 decimals (max difference 0.000).
- **Dictionary check:** sha256 of `repr(TOPIC_KEYWORDS)` is recorded
  in `data_source.json`; a test asserts the dictionary printed in
  the README is byte-identical to the code.

## Manual validation (one metric, by hand — plan §4.4)

Largest attention-share cell, recomputed by hand from
`data/processed/articles.csv` with `csv` + `math` only (no pipeline
code), Wilson 95% CI with z = 1.96:

- **Cell:** BBC News × Other.
- **Hand count:** 19 of 31 BBC News articles assigned Other.
- **Hand share:** 19 ÷ 31 × 100 = **61.2903%**; committed
  `attention_share_pct` = 61.2903%; **difference 0.0000 pp**
  (tolerance 0.01 pp).
- **Hand Wilson CI:** [43.8238%, 76.2671%]; committed
  `[wilson_ci_low, wilson_ci_high]` = [43.8238, 76.2671];
  **difference 0.0000 pp** on both ends (tolerance 0.01 pp).
- **VADER 5-title check (hand):** 5 further titles recomputed with a
  direct `vaderSentiment` call match the pipeline's compound to
  3 decimals (max difference 0.000).

Both checks are also recorded in `data/processed/data_source.json`
under `manual_validation`.

## Sample-review method

Stratified sample, 5 articles per outlet with articles in the
window, seed 42, drawn once from `articles.csv` after collection and
fixed (no re-drawing). `reviewer_topic` is the topic a human reader
would assign after reading the title (+ description); `agree` records
whether it matches the dictionary's `assigned_topic`. The reviewer
is the tester. Agreement rate = agreeing articles ÷ reviewed
articles × 100, reported in the insights summary, the README and
the dashboard next to every topic finding, with the disagreement
list. No minimum agreement rate is required; the dictionary is not
tuned after seeing it. Because WSJ and CNN had no articles in the
window, the drawn sample is 20 articles (5 each from NYT, Fox News,
NPR, BBC News), not 30 — the plan's 30-article design assumes 5
per outlet across all six, which the collected corpus cannot
supply. This deviation is recorded in `coder_handoff.md`.

## Commit rule for data files

- Small raw data IS committed: files under 1 MB each (under 5 MB per
  day folder) are part of the deliverable — `.gitignore` must NOT
  exclude `data/`. Anything larger must be `.gitignore`d and
  regenerated by the pipeline.
- The six raw RSS XMLs total 463,975 bytes (largest: Fox News,
  258,357 bytes) — all committed. Processed files total under 100 KB.
- Synthetic fallback output (`data/raw/*_synthetic.json`) is
  git-ignored and must never overwrite real data. No synthetic data
  was used in this build (`synthetic: false` in `data_source.json`).
- `--offline` regenerates the derived tables from the committed XMLs
  and never overwrites `data_source.json` when a live record exists.

## Versions used for this build

Python 3.12.3; pandas 3.1.1, numpy 2.5.4, scipy 1.18.1, matplotlib
3.11.2, streamlit 1.66.1, feedparser 6.0.14, vaderSentiment 3.3.2.
Full pins in `requirements.txt`; exact versions also recorded in
`data/processed/data_source.json` under `versions`.
