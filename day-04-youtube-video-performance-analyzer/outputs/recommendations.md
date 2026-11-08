# Day 04 — YouTube Video Performance Analyzer: Recommendations

Every recommendation below is generated from the group medians in
`data/processed/videos.csv` by `build_recommendations`
(`src/youtube_kpi.py`). Each cites its numbers and its caveat. No causal
claims are made anywhere in this file: patterns are described as they
appeared in this sample, never as drivers of future performance.

## 1. Long videos (15–30 min) had the highest median views per day of any length group

- **Recommendation:** In this sample, long (15–30 min) videos had the
  highest median views per day of any length group.
- **Evidence:** median 851 views/day (n=41) vs 611 overall (n=244).
- **Sample basis:** duration Long (15–30 min) (n=41 of 244).
- **Caveat:** Descriptive pattern in a relevance-ranked sample of 244
  videos — not a causal finding.

## 2. AI & Machine Learning videos had the highest median views per day of any solid topic group (n ≥ 10)

- **Recommendation:** In this sample, AI & Machine Learning videos had the
  highest median views per day of any solid topic group (n ≥ 10).
- **Evidence:** median 914 views/day (n=68) vs 611 overall (n=244).
- **Sample basis:** topic AI & Machine Learning (n=68 of 244).
- **Caveat:** Descriptive pattern in a relevance-ranked sample of 244
  videos — not a causal finding.

## 3. Career videos had the highest median engagement rate of any topic group

- **Recommendation:** In this sample, Career videos had the highest median
  engagement rate of any topic group.
- **Evidence:** median engagement 2.95% (n=10) vs 2.20% overall (n=244).
- **Sample basis:** topic Career (n=10 of 244).
- **Caveat:** Descriptive pattern in a relevance-ranked sample of 244
  videos — not a causal finding.
- **Note:** n=10 is the minimum for a recommendation — treat this as a
  lead to test, not a firm finding. Career topics engaged well but
  reached modestly (642 median views/day, n=10).

## 4. Tutorials had the higher median views per day of the two main formats

- **Recommendation:** In this sample, tutorials had the higher median views
  per day of the two main formats.
- **Evidence:** tutorials median 596 views/day (n=192); explainers median
  504 views/day (n=14); overall median 611 views/day.
- **Sample basis:** format comparison (n=206 of 244).
- **Caveat:** Descriptive pattern in a relevance-ranked sample of 244
  videos — not a causal finding.
- **Note:** the explainer group is small (n=14), so the gap is suggestive
  rather than firm.

## 5. Top-quartile videos reached further but engaged slightly less

- **Recommendation:** In this sample, the top-quartile videos by views per
  day had a slightly lower median engagement rate than the rest — reach
  and engagement did not move together.
- **Evidence:** top quartile median engagement 2.01% (n=61) vs 2.32% for
  the rest (n=183); top-quartile median 3,124 views/day vs 380 views/day.
- **Sample basis:** high performers (top quartile of views per day, n=61)
  vs rest (n=183).
- **Caveat:** Descriptive pattern in a relevance-ranked sample of 244
  videos — not a causal finding.

## 6. Wednesday had the highest median views per day of any weekday — treat this as description, not a schedule

- **Recommendation:** In this sample, videos published on Wednesdays had
  the highest median views per day of any weekday — treat this as a
  description of the sample, not a posting schedule.
- **Evidence:** median 878 views/day (n=34) vs 611 overall; the channel
  audience timezone is unknown, so no best time to post can be concluded
  from this.
- **Sample basis:** publish day of week Wednesday (n=34 of 244).
- **Caveat:** Descriptive pattern in a relevance-ranked sample of 244
  videos — not a causal finding.

## What was deliberately not recommended

- **BI & Visualisation as a topic:** its 2,574 median views/day rests on
  n=3 — too thin for a recommendation, so it is omitted.
- **Any publish hour:** most hour/day cells hold 1–4 videos; no hour
  pattern in this sample is interpretable.
- **Short-form as a reach strategy:** short-form (1–5 min) videos had the
  lowest median views per day (288, n=19), below Shorts (369, n=30) —
  but with n=19 this is a weak signal, and it is reported as a finding in
  `outputs/insights_summary.md`, not as a recommendation to avoid the format.
- **Anything about a specific creator or video:** recommendations are drawn
  only from aggregated group medians, never from single videos.
