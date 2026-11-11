# Day 07 — Disease Prevalence Dashboard: Insights

**Scope:** CDC PLACES county estimates, 2022–2023, six chronic conditions.
All rates are crude prevalence, % of adults 18+ — model-based estimates,
not counted cases. State and national rates are population-weighted.

## Finding 1 — Geography dominates: the highest places run 2–5× the lowest

Diabetes spans 4.9% (Madison County, ID) to 27.1% (Greene County, AL)
across counties in 2023; obesity spans 16.7% (Boulder County, CO) to
52.9% (Perry County, AL). At state level (population-weighted), West
Virginia is highest for diabetes (15.88%), COPD (10.63%), coronary heart
disease (8.73%) and obesity (40.63%); DC is lowest for diabetes (7.80%),
COPD (4.00%) and obesity (24.70%). The top state runs 2.04× the bottom
for diabetes, 2.66× for COPD, 2.30× for heart disease — but only 1.42×
for asthma, the most evenly spread condition (county range just
7.8–15.3%). The pattern is condition-specific, not one map for all six:
Maine tops asthma (12.64%) while Mississippi tops stroke (4.55%).
(Charts 01, 02.)

## Finding 2 — Five of six conditions edged down in 2023 — but read the fine print

On the 2,956 counties present in both years, the median county moved:
diabetes +0.10 pp, COPD −0.40 pp, asthma −0.10 pp, heart disease −0.50 pp,
stroke −0.10 pp, obesity −0.20 pp. Nationally (population-weighted):
diabetes 11.97% → 12.05% (+0.08 pp), COPD 6.98% → 6.49% (−0.49 pp),
heart disease 6.83% → 6.28% (−0.55 pp), obesity 33.56% → 33.20%
(−0.36 pp). Heart disease fell in 86.3% of matched counties — the most
consistent move of the six; diabetes rose in 54.3%. Two cautions: the
national moves are partly compositional (2023 has no Kentucky or
Pennsylvania rows — see Limitations), and a one-year move of 0.1–0.5 pp
is small next to the median county confidence-interval width (up to 3.9 pp
for diabetes, 15.3 pp for obesity). This is a nudge, not a trend.
(Charts 03, 04.)

## Finding 3 — The biggest county moves are noise; definitions move numbers too

The largest year-over-year swings are all in counties with a few hundred
adults: Kenedy County, TX fell 7.50 pp on diabetes (26.0% → 18.5%) and
7.20 pp on COPD; Kalawao County, HI rose 5.70 pp on diabetes. These moves
are within or near their confidence intervals and should not be read as
real change — the dashboard's biggest-movers tables are a prompt to check
the interval, not a ranking of progress. Separately, definitions alone
move numbers: Tangipahoa parish, LA, has crude diabetes prevalence of
14.6% but age-adjusted prevalence of 13.5% — a 1.1 pp gap in one county,
same year, from the definition alone. And the county median (13.3% for
diabetes) sits a full 1.25 pp above the population-weighted national rate
(12.05%), because small rural counties with higher prevalence count
equally in a median — the exact trap the weighted roll-up exists to avoid.

## Recommendation

For any follow-up analysis, **always report the matched-county median
change next to the national change, and always show the confidence
interval next to a county ranking** — the two numbers that stop this
dataset being misread. The next useful step is a two-condition comparison
(e.g. diabetes vs obesity by county) to test whether the same counties
drive both, using the same matched-county, population-weighted discipline.

## Limitations

- Model-based estimates from survey data, not counted cases; median
  county CI widths run 0.8–15.3 pp by condition.
- Kentucky (120 counties) and Pennsylvania (67 counties) have no rows in
  the 2025 release (2023); Loving County, TX is suppressed. 2023 covers
  2,956 counties vs 3,144 in 2022 — national 2022→2023 moves are partly
  compositional.
- Crude rates only; age-adjusted figures differ (Tangipahoa: 14.6% vs 13.5%).
- County rankings are a starting point for questions, not a health league
  table.
