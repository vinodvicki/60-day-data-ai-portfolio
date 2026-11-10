# Weekly Briefing — Viral Content Trend Explorer

**Date: 2026-11-10.** Windows covered: prior 2026-09-11 → 2026-10-11 (Window B, 236 videos) vs recent 2026-10-11 → 2026-11-10 (Window A, 236 videos). Sample: 472 recently published data/AI YouTube videos, fetched live 2026-11-10.

> Trends here compare two 30-day cohorts of recently published videos. The API gives a current snapshot of each video's statistics, not daily history — so these are cohort comparisons, not a record of views rising or falling over time.

Generated from `data/processed/trend_table.csv` — every number below comes from that computed table, not from memory. No sentiment number is used in any classification, and no claim here is causal: each paragraph states what the sample shows, with its caveat.

## Headlines

- **Top accelerating topic: AI & Machine Learning** — share 26.27% → 32.63% (+6.36 pp), volume +24.2% (62 → 77 videos).
- **Top fading topic: Python** — share 37.29% → 29.24% (-8.05 pp), volume -21.6% (88 → 69 videos).
- **Velocity cross-check: not computable.** No recent video is aged ≥ 7 days, so every recent-window velocity median is undefined and no mixed-signal flag can be raised.
- **Sentiment snapshot: empty.** 0 videos, 0 comments analysed — no recent video is aged ≥ 7 days, so no video qualifies for the mood snapshot.
- **Holdout backtest: not computable.** Weeks W1–W3 hold no videos and W8 is empty, so no hit/miss is claimed.

## One paragraph per topic

### AI & Machine Learning — accelerating

In this sample, AI & Machine Learning videos numbered 77 in the recent window and 62 in the prior window, a volume change of +24.2%; the topic's share of all videos in the sample moved from 26.27% to 32.63% (+6.36 percentage points). Classification: accelerating. Median views per day was undefined (no age-eligible videos) in the recent window and 4.1 views/day (median age 31 days, n=62) in the prior window, so no velocity change can be computed and no mixed-signal flag applies. Caveat: both windows are truncated to their newest 50 videos per query, so these counts are lower bounds, and the comparison covers effectively Nov 8–9 against Oct 8–10, not two full 30-day windows.

### SQL — accelerating

In this sample, SQL videos numbered 52 in the recent window and 43 in the prior window, a volume change of +20.9%; the topic's share of all videos in the sample moved from 18.22% to 22.03% (+3.81 percentage points). Classification: accelerating. Median views per day was undefined (no age-eligible videos) in the recent window and 3.6 views/day (median age 30 days, n=43) in the prior window, so no velocity change can be computed and no mixed-signal flag applies. Caveat: both windows are truncated to their newest 50 videos per query, so these counts are lower bounds, and the comparison covers effectively Nov 8–9 against Oct 8–10, not two full 30-day windows.

### Python — fading

In this sample, Python videos numbered 69 in the recent window and 88 in the prior window, a volume change of -21.6%; the topic's share of all videos in the sample moved from 37.29% to 29.24% (-8.05 percentage points). Classification: fading. Median views per day was undefined (no age-eligible videos) in the recent window and 5.6 views/day (median age 30 days, n=88) in the prior window, so no velocity change can be computed and no mixed-signal flag applies. Caveat: both windows are truncated to their newest 50 videos per query, so these counts are lower bounds, and the comparison covers effectively Nov 8–9 against Oct 8–10, not two full 30-day windows.

### Other — stable

In this sample, Other videos numbered 22 in the recent window and 25 in the prior window, a volume change of -12.0%; the topic's share of all videos in the sample moved from 10.59% to 9.32% (-1.27 percentage points). Classification: stable. Median views per day was undefined (no age-eligible videos) in the recent window and 49.2 views/day (median age 30 days, n=25) in the prior window, so no velocity change can be computed and no mixed-signal flag applies. Caveat: both windows are truncated to their newest 50 videos per query, so these counts are lower bounds, and the comparison covers effectively Nov 8–9 against Oct 8–10, not two full 30-day windows.

### Career — insufficient data

In this sample, Career videos numbered 3 in the recent window and 4 in the prior window, a volume change of -25.0%; the topic's share of all videos in the sample moved from 1.69% to 1.27% (-0.42 percentage points). Classification: insufficient data. Median views per day was undefined (no age-eligible videos) in the recent window and 2.0 views/day (median age 30 days, n=4) in the prior window, so no velocity change can be computed and no mixed-signal flag applies. Caveat: both windows are truncated to their newest 50 videos per query, so these counts are lower bounds, and the comparison covers effectively Nov 8–9 against Oct 8–10, not two full 30-day windows.

### Business Intelligence & Visualisation — insufficient data

In this sample, Business Intelligence & Visualisation videos numbered 6 in the recent window and 4 in the prior window, a volume change of +50.0%; the topic's share of all videos in the sample moved from 1.69% to 2.54% (+0.85 percentage points). Classification: insufficient data. Median views per day was undefined (no age-eligible videos) in the recent window and 6.7 views/day (median age 30 days, n=4) in the prior window, so no velocity change can be computed and no mixed-signal flag applies. Caveat: both windows are truncated to their newest 50 videos per query, so these counts are lower bounds, and the comparison covers effectively Nov 8–9 against Oct 8–10, not two full 30-day windows.

### General Data Analytics — insufficient data

In this sample, General Data Analytics videos numbered 7 in the recent window and 10 in the prior window, a volume change of -30.0%; the topic's share of all videos in the sample moved from 4.24% to 2.97% (-1.27 percentage points). Classification: insufficient data. Median views per day was undefined (no age-eligible videos) in the recent window and 0.3 views/day (median age 30 days, n=10) in the prior window, so no velocity change can be computed and no mixed-signal flag applies. Caveat: both windows are truncated to their newest 50 videos per query, so these counts are lower bounds, and the comparison covers effectively Nov 8–9 against Oct 8–10, not two full 30-day windows.

## Velocity sensitivity

Recomputing velocity change with a 14-day age guard instead of 7 days flips no topic's velocity direction, because velocity change is undefined at both guards. The volume classification does not depend on velocity.

## Audience mood (sentiment snapshot)

No mood lines: the snapshot has 0 videos and 0 analysed comments. The snapshot needs the top video by views per day in each topic in the recent window, aged ≥ 7 days — all 236 recent videos were published 2026-11-08/09. This is a consequence of the same truncation that empties the weekly buckets, not a scoring failure.

## What to keep in mind

- All 10 query-windows returned exactly 50 videos (the one-page cap), so each window holds only its newest videos. Weekly buckets W1–W3 and W6–W8 are empty; W9 is partial (5 days). Volume numbers are lower bounds for their windows.
- The volume classification compares two truncated slices (Nov 8–9 vs Oct 8–10), not two full 30-day windows.
- `other` is 10.0% of the sample (47 of 472 videos), within the ≤ 30% target; the keyword taxonomy was not re-tuned.
- No single channel dominates either window (largest share: recent 3.4%, prior 2.5%).
- Median engagement rate is 1.49%, inside the Day 4 sanity range of 0.5–8%.

Data from the YouTube Data API v3 — see [YouTube's Terms of Service](https://www.youtube.com/t/terms).