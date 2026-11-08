# Day 04 — YouTube Video Performance Analyzer: Insights

Sample: 244 public data/AI-adjacent YouTube videos from 143 channels,
fetched 2026-11-08 via the YouTube Data API v3 (5 fixed queries × 50
results, order=relevance). Median 611 views/day; median engagement rate
2.20%. All comparisons use medians, never means.

Performance patterns here describe this sampled set of public videos. They are descriptive, not causal, and are not a guarantee of future performance.

## Finding 1 — Which topics, formats and durations perform best?

**AI & Machine Learning videos had the highest median views per day of any
solid topic group: 914 views/day (n=68), against 611 overall.** Python, the
largest group, sat below the overall median at 489 (n=123); SQL at 707
(n=39); Career at 642 (n=10). BI & Visualisation's 2,574 median rests on
just n=3 and General Data on n=1 — neither is evidence of anything. The
"Other" topic group is empty (0 videos), so the keyword grouping covered
the whole sample.

**Long videos (15–30 min) had the highest median views per day of any
length: 851 (n=41).** Deep-dives over 30 minutes were close behind at 734
(n=76), then medium videos (5–15 min) at 610 (n=78). Short-form (1–5 min)
was lowest at 288 (n=19), below Shorts (≤ 60 s) at 369 (n=30) — short does
not mean better in this sample. Engagement was flattest across lengths:
long videos also led on median engagement (2.78%), but the whole range
only spans 2.12% (deep-dive) to 2.78% (long).

**Tutorials edged explainers: 596 views/day (n=192) vs 504 (n=14).** The
explainer group is small, so the gap is suggestive rather than firm. The
residual "other" format group (n=38) had the highest median of all at
1,582 — but it is a leftover bucket of videos matching neither keyword
list, not a format a creator can aim at.

**The top quartile (n=61) reached far further without engaging better:
3,124 vs 380 median views/day, but 2.01% vs 2.32% median engagement.**
AI & Machine Learning made up 48% of the top quartile against 21% of the
rest; Python made up 38% against 55%. Deep-dives were 39% of the top
quartile. No single channel dominates it (largest share 8.2%).

Charts: `outputs/charts/01_views_by_topic.png`,
`outputs/charts/02_duration_vs_performance.png`,
`outputs/charts/04_engagement_scatter.png`.

## Finding 2 — When should a creator publish?

**Almost nothing honest can be concluded about publish time from this
sample.** By weekday, Wednesday had the highest median at 878 views/day
(n=34) and Friday the lowest at 373 (n=41), with Saturday 829 (n=24),
Monday 825 (n=30), Tuesday 793 (n=47), Sunday 664 (n=17) and Thursday 577
(n=51) in between — a spread of roughly 2.4x, but each day's median rests
on 17–51 videos drawn from a relevance-ranked sample, and the day a video
was published is confounded with its age, topic and channel.

By hour the picture is thinner still: most hour/day cells hold 1–4 videos,
and even the hours with n ≥ 5 span only 357 to 1,397 median views/day
(08:00 UTC highest at 1,397, n=7; 18:00 UTC lowest at 357, n=13), with no
stable pattern. The channel audience timezone is unknown — the API does
not reveal it — so an hour pattern cannot be read as a posting schedule.
The honest answer to "when should a creator publish" is: this sample does
not contain one.

Chart: `outputs/charts/03_publish_time_heatmap.png`.

## Finding 3 — What concrete recommendations follow?

Six evidence-cited recommendations are listed separately in
`outputs/recommendations.md`, each with its numbers, sample basis and
caveat. In short: lean into AI & Machine Learning topics and long-form
(15–30 min) videos, keep the tutorial format, treat Career topics as an
engagement play rather than a reach play, and do not chase a publish hour
— the sample does not support one. The one recommendation that cuts
against intuition is the top-quartile finding: the videos that reached
furthest engaged slightly *less* (2.01% vs 2.32%), so reach and
engagement should be optimised as separate goals, not assumed to move
together.

The claims that must *not* be made: that long videos or AI topics *drive*
more views (the sample is cross-sectional and relevance-ranked); that
Wednesday or 08:00 UTC is the best time to post (thin cells, unknown
audience timezone); that BI & Visualisation is the best topic (n=3); or
anything about a specific creator or video beyond the aggregated evidence.

## Limitations

- Relevance-ranked snapshot as of 2026-11-08, not a date-bounded cohort;
  the sample mixes 2017 and 2026 videos and `views_per_day` only partly
  corrects for age.
- Search relevance ranking is undocumented; findings describe the returned
  set, not all of YouTube.
- No causal claims; no guarantee of future performance.
- Channel size matters in this sample (large channels 887 views/day,
  n=78; mid-size 680, n=83; small 367, n=83) and confounds every
  topic/format comparison — a topic popular with large channels looks
  better than the same topic on small ones.
- Comment sentiment is out of scope — no comments endpoint exists in the
  helper.
- Data from the YouTube Data API v3. Derived rates are basic arithmetic on
  returned statistics for an offline educational analysis, shown next to
  the underlying counts.
