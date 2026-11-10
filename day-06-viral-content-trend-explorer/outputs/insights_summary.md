# Day 06 — Viral Content Trend Explorer: Insights

**Fetch date: 2026-11-10.** 472 recently published data/AI YouTube videos in two 30-day
cohorts: prior window 2026-09-11 → 2026-10-11 (Window B, 236 videos) vs recent window
2026-10-11 → 2026-11-10 (Window A, 236 videos).

> Trends here compare two 30-day cohorts of recently published videos. The API gives a current
> snapshot of each video's statistics, not daily history — so these are cohort comparisons, not a
> record of views rising or falling over time.

**The one fact that shapes every finding below:** all 10 query-windows returned exactly 50
videos (the one-page cap), so each window holds only its newest videos. The recent window
effectively covers 2026-11-08 → 11-09 and the prior window 2026-10-08 → 10-10. Weekly buckets
W1–W3 and W6–W8 are empty, and every volume number is a lower bound for its window. Nothing was
re-tuned to hide that — the thresholds, taxonomy and age guard are fixed by plan.md §4.

## Finding 1 — Which topics are accelerating and which are fading? (Chart 01)

In this sample, **AI & Machine Learning is accelerating** (77 recent vs 62 prior videos, share
26.27% → 32.63%, +6.36 pp, volume +24.2%) and **SQL is accelerating** (52 vs 43, share 18.22% →
22.03%, +3.81 pp, volume +20.9%). **Python is fading** (69 vs 88, share 37.29% → 29.24%,
−8.05 pp, volume −21.6%). Other is stable (22 vs 25, −1.27 pp, −12.0%). Career (3 vs 4),
BI & Visualisation (6 vs 4) and General Data Analytics (7 vs 10) have n < 10 in a window and
are reported as insufficient data, not classified. These are statements about this truncated
sample — the comparison covers effectively Nov 8–9 against Oct 8–10, not two full 30-day windows.

## Finding 2 — Does the velocity story agree with the volume story? (Chart 03)

**It cannot be checked in this sample.** Median views per day (age ≥ 7 days only) is undefined
for the recent window in every topic: all 236 recent videos were published 2026-11-08/09, so
none is aged ≥ 7 days. Every velocity change is therefore undefined, no mixed-signal flag can
be raised, and the volume classification stands on its own with that caveat stated. For
reference only, prior-window medians are: Python 5.6 views/day (median age 30 days, n=88),
AI & Machine Learning 4.1/day (31 days, n=62), SQL 3.6/day (30 days, n=43), Other 49.2/day
(30 days, n=25). The 14-day age-guard sensitivity check flips no topic's velocity direction,
because velocity change is undefined at both guards. The holdout backtest is **not computable**:
weeks W1–W3 hold no videos, so there is no train growth to predict from, and W8 is empty, so
there is no test week — no hit/miss is claimed.

## Finding 3 — What is the audience mood on the fastest-rising video in each topic? (Chart 04)

**There is no mood snapshot in this sample.** The snapshot needs the top video by views per day
in each topic in the recent window, aged ≥ 7 days, with comments enabled — and no recent video
qualifies. 0 videos, 0 comments analysed. This is a consequence of the same truncation that
empties the weekly buckets, not a scoring failure. Day 5's lexicon scorer was copied verbatim
and verified against Day 5's hand-computed cases before use; it simply had no video to score.

## Recommendation (analytical next step — never investment advice)

Do not act on the accelerating/fading calls as if they described two full 30-day windows: they
describe two truncated slices (Nov 8–9 vs Oct 8–10). The honest next step is a second page per
query-window (a planner decision, not a coder re-tune — the plan forbids fetching page 2 in this
build) so the windows actually cover 30 days each; until then, treat the classifications as a
lower-bound signal from the newest videos only, and treat the velocity, backtest and sentiment
panels as empty by design, not as missing work.

## Limitations

- **Snapshot, not history.** The API gives a current snapshot of each video's statistics, not
  daily history. Every "trend" here is a comparison of two publish-date cohorts.
- **Truncation.** All 10 query-windows hit the 50-result one-page cap. Weekly buckets W1–W3
  and W6–W8 are empty; W9 is partial (5 days). Volume numbers are lower bounds.
- **Velocity undefined for the recent window** (no video aged ≥ 7 days), so the velocity
  cross-check, mixed-signal flags and age-guard sensitivity check all come back empty.
- **Backtest not computable** (W1–W3 and W8 empty). **Sentiment snapshot empty** (0 videos,
  0 comments).
- **Sentiment is a model output**, not ground truth, and describes five videos at most.
- **No causal claims.** A classification is a statement about this sample only.
- **Sample notes:** `other` is 10.0% of the sample (47 of 472, within the ≤ 30% target);
  median engagement rate is 1.49% (Day 4 sanity range 0.5–8%); no single channel dominates
  either window (largest share: recent 3.4%, prior 2.5%); Shorts are 53.8% of the recent
  window and 32.6% of the prior window; 10 videos have 0 views; overlap with the Day 4 frame
  is 0 videos.

Data from the YouTube Data API v3 — see
[YouTube's Terms of Service](https://www.youtube.com/t/terms).
