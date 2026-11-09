# Day 05 — Social Media Sentiment Analyzer: Insights

Corpus: 1,462 analysed top-level public comments on 12 data/AI YouTube
videos, 2025-11-09 → 2026-11-09, fetched live via the YouTube Data API v3
(16 quota units). **Every sentiment share below is as classified by our
rule-based model — it is not ground truth.** Validation against
120 human-labelled comments: accuracy 0.617, macro-F1 0.613.

## Q1 — How is sentiment distributed, and does it move over time?

- **Overall: 40.6% positive, 52.6% neutral, 6.8% negative** (594 / 769 / 99
  of 1,462). But 55.3% of comments (808) matched no lexicon word and are
  neutral by default, not by meaning — the neutral share is inflated and
  the positive/negative shares are under-counts.
- **By topic** (chart 02): AI & ML is the most negative and least positive
  (13.3% negative / 22.8% positive, n=294); within the topic, the
  60 Minutes AI episode is the most negative-classified video
  (20.2% negative, n=99). BI & Visualisation is the most positive (56.1%, n=98);
  career 47.0% (n=381), Python 44.4% (n=500), SQL 37.6% (n=189).
- **By month** (chart 01): positive share ranges 31.9% (2026-09) to 57.1%
  (2025-11, n=14 — thin). The video mix changes month to month and two
  videos contribute ~40% of the corpus, so the trend partly reflects
  which videos were active, not a pure time trend. No causal reading.
- **By video**: the 60 Minutes AI episode is the most negative-classified
  (20.2% negative, n=99); the Simplilearn machine-learning course is the
  most positive-classified (88.9%, but n=9 — too small to trust).

## Q2 — What themes recur, and what do people actually say?

- **59.0% of comments matched no theme** (`other`, 862 of 1,462) — the
  fixed keyword lists missed the large Google Data Analytics
  course-cohort check-in pattern ("here from the Google Data Analytics
  course", "good luck", "starting today"). This is reported, not re-tuned:
  the theme lists were frozen before the data was seen.
- Next largest themes (chart 03): **praise 329 (22.5%)**, 91.2% positive —
  "thank you", "amazing", "helpful" dominate; **career 144 (9.8%)**;
  **tutorial quality 116 (7.9%)**, 70.7% positive.
- **Criticism is small but the most negative theme: 21 comments (1.4%),
  47.6% negative** — mostly "outdated course" and "too corporate"
  complaints, not anger at the creators.
- **Price/cost 38 (2.6%)** is warm, not complaining: viewers are glad
  the content is free ("im just happy i didnt pay for something i could
  watch for free on Youtube").
- Top words/bigrams per class (see `themes_summary.md`): positive —
  "data analytics" 87, "google data" 78, "easy follow" 22; negative —
  "expect good" 6, "hidden layer" 4 (content words, not complaints —
  the lexicon cannot tell the difference).

## Q3 — How far can the model be trusted?

- **Accuracy 0.617, macro-F1 0.613 (n=120, 40 per predicted class).**
  Per class — positive P 0.75 / R 0.58 / F1 0.65 (support 52);
  neutral P 0.62 / R 0.58 / F1 0.60 (support 43);
  negative P 0.47 / R 0.76 / F1 0.58 (support 25).
- **Error patterns** (chart 04): the model over-predicts negative —
  10 truly positive and 11 truly neutral comments were classified
  negative (words like "wrong", "blame", "hard" in otherwise warm
  comments). It also misses praise: 12 truly positive comments
  classified neutral ("top notch", "phenomenal" — praise words outside
  the lexicon).
- This is a **modest baseline**, not a trained model. Do not use these
  sentiment shares for decisions; use them to describe this corpus only.

## Analytical next step

Add a second human labeller and a domain stop-list for content words
("hidden layer", "neural network") before any re-scoring — and keep the
lexicon frozen while measuring, so improvements are attributable.

## Limitations

- Lexicon baseline: no sarcasm, irony, or domain meaning; 55.3% of
  comments carry no scored word; 59.0% match no theme.
- Spanish in Latin script slips through the language filter; curly
  apostrophes split contractions.
- 12 videos from Day 4's frame, top-level comments only, one labeller,
  120 validation comments. Findings describe these 12 videos only and
  are descriptive, not causal. Sentiment is a model estimate, not
  ground truth.
