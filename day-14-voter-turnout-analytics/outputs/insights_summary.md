# Insights summary — Day 14: Voter Turnout Analytics

**Coverage:** general elections 1980–2024, 50 states + DC + US total.
**Primary metric:** VEP turnout = ballots counted ÷ voting-eligible population.
**Source:** Michael McDonald, University of Florida Election Lab, General
Election Turnout Rates 1980–2022 v1.2 and 2024 General Election Turnout Rates
v0.4, CC BY 4.0. Retrieved 2026-11-21.

This memo is evidence-limited by design: it describes what the data shows,
states the denominator and the coverage on every finding, and makes no causal
claims. Nothing here forecasts a future election. This is a transparency
project, not an advice product.

## Finding 1 — Turnout differs widely across states in 2024 (Q1)

In the 2024 general election, VEP turnout across the 51 jurisdictions ranged
from **50.26% (Hawaii) to 76.66% (Wisconsin)** — a 26.40 pp spread — against a
national figure of **64.30%**. District of Columbia: **64.94%** (rank 25).

**Top 10 states, 2024 VEP turnout:**

| Rank | State | VEP turnout | pp change vs 2020 |
|---|---|---|---|
| 1 | Wisconsin | 76.66% | +1.62 pp |
| 2 | Minnesota | 76.50% | −2.71 pp |
| 3 | Michigan | 74.85% | +1.58 pp |
| 4 | Maine | 74.55% | −0.32 pp |
| 5 | New Hampshire | 73.74% | −0.22 pp |
| 6 | Colorado | 73.40% | −3.29 pp |
| 7 | Oregon | 71.87% | −3.46 pp |
| 8 | Virginia | 71.46% | −0.33 pp |
| 9 | Pennsylvania | 71.44% | +1.51 pp |
| 10 | Iowa | 70.95% | −1.09 pp |

**Bottom 10 states, 2024 VEP turnout:**

| Rank | State | VEP turnout | pp change vs 2020 |
|---|---|---|---|
| 42 | New Mexico | 59.71% | −0.78 pp |
| 43 | Indiana | 59.05% | −2.01 pp |
| 44 | Alabama | 58.70% | −2.76 pp |
| 45 | Tennessee | 57.92% | −1.32 pp |
| 46 | Mississippi | 57.75% | −2.88 pp |
| 47 | Texas | 56.83% | −2.96 pp |
| 48 | West Virginia | 55.56% | −1.63 pp |
| 49 | Arkansas | 54.06% | −2.11 pp |
| 50 | Oklahoma | 53.46% | −0.97 pp |
| 51 | Hawaii | 50.26% | −5.09 pp |

**Change since the last same-cycle election (2024 vs 2020, both
presidential):** 7 states rose and 44 fell; the median change was **−1.68 pp**
(range −6.57 to +1.90 pp). The national figure fell **−1.69 pp** (65.99% →
64.30%). No state is described here beyond its number, its rank, and its pp
change.

## Finding 2 — Turnout moves in two separate bands over time (Q2)

National VEP turnout runs in two bands that must not be read as one trend:
presidential years **55.28%–65.99%**, midterm years **36.61%–50.05%**.

| Year | Cycle type | VEP turnout | pp change vs last same-cycle year |
|---|---|---|---|
| 1998 | midterm | 39.31% | — (no prior-cycle value in the file) |
| 2000 | presidential | 55.28% | — |
| 2002 | midterm | 40.48% | +1.17 pp |
| 2004 | presidential | 60.86% | +5.58 pp |
| 2006 | midterm | 41.40% | +0.92 pp |
| 2008 | presidential | 62.17% | +1.31 pp |
| 2010 | midterm | 40.99% | −0.41 pp |
| 2012 | presidential | 58.57% | −3.60 pp |
| 2014 | midterm | 36.61% | −4.38 pp |
| 2016 | presidential | 60.12% | +1.55 pp |
| 2018 | midterm | 50.05% | +13.44 pp |
| 2020 | presidential | 65.99% | +5.87 pp |
| 2022 | midterm | 46.12% | −3.93 pp |
| 2024 | presidential | 64.30% | −1.69 pp |

The highest presidential-year figure in the series is **2020 (65.99%)**; the
highest midterm-year figure is **2018 (50.05%)**, which rose 13.44 pp from
2014 — the largest same-cycle move in the series. The 2024 figure (64.30%) is
the lab's preliminary v0.4 release. Pre-2010 national figures are estimated;
national VEP turnout is not reported in the file for 1980–1996.

## Finding 3 — Which demographic indicators move with turnout (Q3)

State-level associations for 2024 (n = 51, DC included, US total excluded).
Correlation is not causation; no model is fitted.

| Indicator | n | Pearson r | Pearson p | Spearman ρ | Spearman p |
|---|---|---|---|---|---|
| Noncitizen share of VAP | 51 | −0.07 | 0.639 | −0.04 | 0.804 |
| Ineligible-felon share of VAP | 51 | −0.40 | 0.003 | −0.40 | 0.003 |
| Overseas eligible share of VEP | 0 | — | — | — | — |

- **Noncitizen share:** no clear association in these data (r = −0.07,
  p = 0.639).
- **Ineligible-felon share:** moves with turnout (r = −0.40, p = 0.003):
  states with a higher ineligible-felon share of VAP tended to have lower
  2024 VEP turnout. This association does not show that the felon share
  caused turnout to change.
- **Overseas eligible share:** no association is computable (n = 0) — the
  lab does not apportion eligible overseas voters to states.

## Outliers — flagged, never dropped

Screening method: within each cycle type, a state's VEP turnout is flagged
when it lies outside the 1.5×IQR fence or its |z| > 3. Skewness: presidential
years pooled **−0.27**, midterm years pooled **+0.06**.

**2024 pass: no state was flagged.** The 2024 spread (50.26%–76.66%) contains
no value outside the 2024 fence.

**Pooled presidential pass (all presidential years, 1980–2024): 5 flagged
state-years**, all retained in every chart and table:

| Year | State | VEP turnout | Rule |
|---|---|---|---|
| 1980 | District of Columbia | 37.90% | IQR + z (z = −3.26) |
| 1980 | South Carolina | 42.35% | IQR |
| 1988 | South Carolina | 42.46% | IQR |
| 1996 | Nevada | 41.23% | IQR |
| 2016 | Hawaii | 43.19% | IQR |

## Cross-checks and validation

- **Recompute check:** VEP turnout recomputed from ballots ÷ VEP matches the
  file's rate within 0.05 pp on all 987 rows carrying both figures (max
  difference 0.0226 pp). Spot-checks: 2024 US 64.30%, 2022 US 46.12%,
  2024 Colorado 73.40%, California 62.26%, Arkansas 54.06%.
- **VEP reconciliation:** 0 rows flagged (tolerance 0.5%); max relative
  difference 0.058%.
- **EAVS cross-check (2024 numerator):** sampled states Colorado −0.011% and
  California +0.15% (both within 0.5%). Additional states Arkansas −5.71%
  and Texas +0.78% differ by more than 0.5% and are disclosed here: the
  Arkansas gap is consistent with 2 Arkansas jurisdictions missing F1a in the
  EAVS file, and the Texas UF figure is a round-number estimate (11,400,000).
  UF figures stand in every case.
- **Shapefile join:** 51/51 jurisdictions joined; 0 unmatched.
- **Manual validation:** 2024 US VEP turnout recomputed by hand from the
  committed CSV — 156,766,239 ÷ 243,803,423 × 100 = 64.30% — diff 0.0 pp.
- **SQL check:** average VEP turnout by cycle type and the top 2024 state
  agree between pandas and in-memory SQLite (see `notebooks/analysis.ipynb`).

## Limitations

- **Descriptive only; no predictive model; no causal claims.** Associations
  are reported with n, r and p, and only as associations.
- **State level only.** No county map and no county rate — no verified no-key
  source gives a county-level denominator.
- **2024 figures are the lab's preliminary v0.4 release** (dated 3/2/2026).
- **Pre-2010 national figures are estimated;** national VEP turnout is not
  reported in the file for 1980–1996. Pre-2010 state ballots are null for 200
  state-year rows and stay null, never filled.
- **VAP vs VEP vs registered-voter denominators are never mixed.** VAP
  turnout is reported alongside VEP turnout, never as a substitute; EAVS
  registered-voter figures cross-check the numerator only.
- **State-level overseas eligible voters are not apportioned by the lab**,
  so no state-level overseas association is computable.
- **No party variable** exists in the data and none is added; states are
  compared on turnout only, with the same metrics, charts and table columns.
