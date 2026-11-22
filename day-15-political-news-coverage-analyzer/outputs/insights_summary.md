# Day 15 — Political News Coverage Analyzer: Insights

Sentiment measures the emotional tone of the words used; it is not a measure of factual accuracy, fairness, or political bias.

**Corpus:** 75 articles, 2026-11-08–2026-11-22, title + description
text only — NYT 10, WSJ 0, Fox News 24, CNN 0, NPR 10, BBC News 31.
WSJ and CNN returned no usable articles in the window (their feeds
served older items: WSJ January 2025, CNN April 2023). Every finding
below is a language and attention finding in this corpus and window
only. This is a transparency project, not an advice product: it
reports what the data shows and nothing more.

## Finding 1 — Topics and attention (Q1)

Corpus-wide, the largest shares went to **Other (42.7%, 32 of 75)** —
articles matching no dictionary keyword — and **Technology & AI
(22.7%, 17 of 75)**, then Elections & campaigns (9.3%, 7 of 75).
The largest single attention-share cell is **BBC News × Other:
61.3% (19 of 31, Wilson 95% CI 43.8%–76.3%)**. Fox News gave its
largest share to Technology & AI (37.5%, 9 of 24, Wilson 95% CI
21.2%–57.3%). NYT's largest share was Other (50.0%, 5 of 10, Wilson
95% CI 23.7%–76.3%) and NPR's was a tie between Other and Technology
& AI (30.0% each, 3 of 10, Wilson 95% CI 10.8%–60.3%).

Attention-share table (within-outlet share, with N and Wilson 95% CI;
full table in `data/processed/topic_attention.csv`):

| Outlet | Largest topic share | 2nd largest |
|---|---:|---:|
| NYT (n=10) | Other 50.0% (5) | Elections & campaigns 20.0% (2) |
| WSJ (n=0) | — | — |
| Fox News (n=24) | Technology & AI 37.5% (9) | Other 20.8% (5) |
| CNN (n=0) | — | — |
| NPR (n=10) | Other 30.0% (3), Technology & AI 30.0% (3) | Elections & campaigns 20.0% (2) |
| BBC News (n=31) | Other 61.3% (19) | Technology & AI 16.1% (5) |

The sample-review agreement rate (55.0% — 11 of 20, see below) is the honest
measure of how far the dictionary can be trusted, and it belongs next
to every topic finding in this section.

## Finding 2 — Language sentiment by outlet and topic (Q2)

Mean VADER compound (95% CI) by outlet, title + description text only:

| Outlet | n | Mean compound | 95% CI | Median | % positive | % neutral | % negative |
|---|---:|---:|---:|---:|---:|---:|---:|
| NYT | 10 | −0.046 | −0.483 to 0.391 | 0.077 | 50.0% | 10.0% | 40.0% |
| WSJ | 0 | — | — | — | — | — | — |
| Fox News | 24 | −0.127 | −0.388 to 0.135 | −0.084 | 29.2% | 16.7% | 54.2% |
| CNN | 0 | — | — | — | — | — | — |
| NPR | 10 | −0.240 | −0.682 to 0.202 | −0.350 | 30.0% | 0.0% | 70.0% |
| BBC News | 31 | 0.048 | −0.187 to 0.283 | 0.000 | 45.2% | 9.7% | 45.2% |

All four outlets with articles have 95% CIs that include 0, so no
outlet's average language tone is distinguishable from neutral in
this corpus. NPR has the largest negative-language share (70.0% of
its 10 articles) and BBC News the largest positive-language share
(45.2% of 31) — both with wide intervals from small samples.

By topic, the only groups with n ≥ 5 are Other and Technology & AI:

| Outlet | Topic | n | Mean compound | 95% CI | Median |
|---|---|---:|---:|---:|---:|
| Fox News | Other | 5 | 0.501 | 0.035 to 0.968 | 0.402 |
| Fox News | Technology & AI | 9 | −0.004 | −0.364 to 0.355 | −0.049 |
| BBC News | Other | 19 | 0.185 | −0.090 to 0.460 | 0.219 |
| BBC News | Technology & AI | 5 | 0.207 | −0.597 to 1.000 | 0.000 |

All other outlet × topic groups have n < 5 and are flagged `small_n`
in `data/processed/sentiment_by_topic.csv`. These are differences in
language tone only.

## Finding 3 — Are the differences larger than chance? (Q3)

- **Topic × outlet:** chi-square on the 4 outlets with articles × 10
  topics: χ² = 31.94, df = 27, asymptotic p = 0.234. Minimum expected
  cell count 0.13 — below 5, so the sparse-cell rule applied: the
  collapsed 4 × 5 table (4 largest topics + All other topics) gives
  χ² = 18.90, df = 12, p = 0.091, still sparse, so the conclusion
  rests on the **permutation p-value (10,000 shuffles, seed 42):
  p = 0.221**. No evidence that the distribution of topics differs
  across outlets in this corpus and window.
- **Sentiment by outlet:** BBC News failed Shapiro-Wilk normality
  (W = 0.919, p = 0.022; Fox News p = 0.128, NPR p = 0.301, NYT
  p = 0.249), so **Kruskal-Wallis: H = 2.09, p = 0.553**. No evidence
  that average language tone differs across outlets. Pairwise
  Mann-Whitney U tests with Bonferroni correction: all 6 corrected
  p-values are 1.000.
- **Sentiment by topic within an outlet:** Fox News one-way ANOVA
  (Other vs Technology & AI): F = 4.26, p = 0.061. BBC News one-way
  ANOVA: F = 0.01, p = 0.941. No other outlet had 2 topics with
  n ≥ 5, so no other within-outlet topic test was run.

In short: in this 75-article corpus, neither the topics covered nor
the average language tone differs across outlets by more than chance
would allow. That is a statement about this corpus and window, not
about the outlets in general.

## Sample review

- **Design:** stratified sample, 5 articles per outlet with articles
  in the window, seed 42, drawn once and fixed. **20 articles drawn**
  (NYT, Fox News, NPR, BBC News) — WSJ and CNN had no articles to
  sample, so the plan's 30-article design (5 per outlet across all
  six) cannot be supplied by the collected corpus.
- **Agreement rate:** 55.0% (11 of 20) — BBC News 2 of 5 (40.0%),
  Fox News 2 of 5 (40.0%), NPR 4 of 5 (80.0%), NYT 3 of 5 (60.0%).
  The tester (2026-11-22) read each sampled title + description and
  recorded the topic a human reader would assign.
- **Disagreements (9):** BBC "'Move on!' Former PMs pile in with
  advice for Andy Burnham" (assigned Technology & AI, reviewer
  Elections & campaigns); BBC "Mexican drug lord on FBI's 10 most
  wanted list arrested in shoot-out" (assigned Healthcare, reviewer
  Crime & justice); BBC "Theresa May 'aghast' at Burnham's EU plans"
  (assigned Other, reviewer Foreign policy); Fox News "$275M
  Obama-era solar fraud case" (assigned Climate/Energy, reviewer
  Crime & justice); Fox News "American Culture Quiz" (assigned
  Technology & AI, reviewer Other); Fox News "Indonesia candy
  factory fire leaves multiple dead" (assigned Crime & justice,
  reviewer Other); NPR "NPR's Senior Podcast Challenge" (assigned
  Technology & AI, reviewer Other); NYT "Drones, Texts and
  Diversions: How Mexico Captured a Most Wanted Man" (assigned
  Healthcare, reviewer Crime & justice); NYT "What Machines Love"
  (assigned Other, reviewer Technology & AI). The sample
  already shows the dictionary's weak points: the frozen keyword `ai`
  matches as a substring inside ordinary words such as "said", and
  `drug` assigns crime reporting to Healthcare. The agreement rate,
  not the dictionary, decides how far the topic numbers can be
  trusted.

## Limitations

- **Descriptive only.** No predictive model, no bias score, no
  leaning score, no fact-checking, no causal claims.
- **Sentiment is language tone only.** VADER is a general-purpose
  social-media lexicon, not built for news text; it reads headline
  and summary wording, not the articles' claims.
- **Title + description text only.** No full article text; no
  scraping of linked article pages.
- **Keyword matching is crude.** A headline can mention a word
  without being about that topic. The sample-review agreement rate
  (55.0%, 11 of 20) is the honest measure of the dictionary's
  trustworthiness.
- **Small, uneven corpus.** 75 articles; WSJ and CNN contributed
  none in the window; NYT and NPR only 10 each. Shares from n=10
  carry wide Wilson intervals, and most topic × outlet cells are
  sparse — hence the permutation p-value.
- **Rolling feeds.** RSS lists are the latest N items, not archives;
  the window actually achieved per outlet is shorter than 14 days
  for every outlet (best: BBC News, 12 days). A later fetch would
  return a different latest-N slice.
- **GDELT not used.** Optional cross-check only; skipped because the
  researcher verified it rate-limits, and the build is complete on
  RSS alone.
- **Sample review complete.** Agreement rate 55.0% (11 of 20;
  BBC News 2/5, Fox News 2/5, NPR 4/5, NYT 3/5); the disagreement
  list is in the Sample review section above.

## What the data shows — and nothing more

For the same two weeks, in the articles these feeds actually served,
the four outlets with articles covered a similar mix of topics
(mostly uncategorised by the frozen dictionary, then Technology &
AI), and their headline + summary language sounded statistically
indistinguishable on average. That is the whole finding.
