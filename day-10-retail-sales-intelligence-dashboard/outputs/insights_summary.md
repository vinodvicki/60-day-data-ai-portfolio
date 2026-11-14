# Day 10 — Retail Sales Intelligence Dashboard: Insights

**Source:** UCI Online Retail (Chen 2015), DOI 10.24432/C5BW33, CC BY 4.0.
Fetched 2026-11-14. Cleaned set: 527,795 transaction lines from 541,909 raw
rows, 19,776 orders, 4,334 identified customers, total revenue
**£10,283,243.98** (GBP). All numbers below are from the committed processed
CSVs in `data/processed/`; every figure can be re-derived from them. This is an
analytical exercise on public historical retail transactions (Dec 2010 – Dec
2011) — not a current-market or forward-trading tool.

## Finding 1 — Where does the revenue come from? (Q1)

**Seasonality dominates the year.** November 2011 is the peak month at
**£1,457,745.53** (2,751 orders) — **2.86×** February 2011 (£508,952.87, the low
month) and 1.81× the average full month. September–November together are
**£3,594,965.43 (34.96% of annual revenue)**. December 2011 (£615,501.60) is
partial — 9 days of data only — and is excluded from month-over-month
comparisons; month-over-month growth in the full months runs from −25.3%
(April) to +43.6% (May), with the Q4 ramp starting in September (+39.9%).

**The catalogue is a long tail.** The top SKU, REGENCY CAKESTAND 3 TIER, is
£174,484.74 (1.70%, 1,988 orders). The second, PAPER CRAFT LITTLE BIRDIE
(£168,469.60, 1.64%), is a single wholesale order of 80,995 units — one
transaction, not a popular product. The top 10 SKUs together are only **9.41%**
of revenue, and the largest derived product group (SET) is 7.35% while "Other"
is 65.46%. No single product or group carries the business.

**Geography is concentrated, but the overseas tail is wholesale-shaped.** The
UK is **85.18% of revenue (£8,759,372.58, 17,904 orders, AOV £489.24)**.
Non-UK revenue is £1,523,871.40 with an AOV of £814.03 — overseas orders are
fewer but bigger: the Netherlands averages £3,052.57 per order (93 orders) and
Australia £2,467.34 (56 orders). The next countries after the UK are the
Netherlands (£283,889.34, 2.76%), EIRE (£271,164.30, 2.64%), Germany
(£205,569.89, 2.00%) and France (£184,582.74, 1.79%).

*Chart: `outputs/charts/01_monthly_sales.png`, `outputs/charts/02_product_country.png`.*

## Finding 2 — Who are the customers, and which groups behave alike? (Q2)

RFM + KMeans (k = 4, seed 42) on the 4,334 identified customers; silhouette
**0.616** — the clusters are well separated.

| Cluster | Customers | Share of customers | Share of identified revenue | Mean recency (days) | Mean frequency | Mean monetary (£) |
|---|---|---|---|---|---|---|
| Champions | 13 | 0.30% | 18.68% | 6.4 | 81.77 | 125,862.44 |
| Big spenders | 209 | 4.82% | 29.26% | 14.4 | 22.02 | 12,265.65 |
| Occasional buyers | 3,046 | 70.28% | 46.27% | 42.8 | 3.64 | 1,330.93 |
| Lapsed | 1,066 | 24.60% | 5.79% | 247.5 | 1.54 | 475.91 |

**The top 222 customers (5.12%) drive 47.94% of identified-customer revenue
(£4,200,055.35).** The business is a broad base of occasional buyers (70.28%
of customers, 46.27% of revenue) plus a small, very valuable core — and a
large lapsed tail (1,066 customers, 24.60%) that has not bought in ~8 months
on average. Rows with no CustomerID (131,455 rows, **14.80% of revenue**,
£1,522,177.33) are excluded from this question only; the shares above are
shares of *identified*-customer revenue (£8,761,066.65). This is descriptive
segmentation, not a churn model.

*Chart: `outputs/charts/03_rfm_clusters.png`.*

## Finding 3 — What demand is coming next? (Q3)

Weekly revenue (51 full ISO weeks) is forecast **8 weeks ahead**
(2011-12-05 → 2012-01-23). Holt-Winters (additive trend, no seasonality) beat
the naïve baseline in the backtest at both rolling origins (8 and 16 weeks,
8-week horizons): mean RMSE **£55,504.52 vs £62,800.78** (origin 8: £38,624.28
vs £51,795.73; origin 16: £72,384.76 vs £73,805.83), so Holt-Winters is the
published forecast. The 8 weeks total **£3,061,051.48**, rising from
£346,552.30 to £418,710.57 per week, with 80% and 95% prediction intervals
from a residual bootstrap (seed 42, 1,000 paths). The last full week
(2011-11-28) was £310,353.86; the highest weekly revenue in the year was
£374,736.15.

No seasonality is modelled: one year of data cannot support a seasonal fit
(statsmodels needs ≥ 2 cycles), so this is a **trend extrapolation** — the
December spike visible in the history is discussed but not modelled, and the
intervals widen with horizon (80% band at week 8: £337,189.50–£680,787.88).

*Chart: `outputs/charts/04_forecast.png`.*

## Commercial recommendations (exactly three)

Each follows the fixed structure **evidence → action → expected effect**; the
evidence numbers are from the committed CSVs and the expected effects are
stated in measured terms.

### 1. Protect the 222 highest-value customers

- **Evidence:** Champions (13) plus Big spenders (209) are 5.12% of identified
  customers and 47.94% of identified revenue (£4,200,055.35 of
  £8,761,066.65). Champions alone average £125,862.44 each.
- **Action:** Give them named-account service, priority allocation of the
  top-10 SKUs and early access to Q4 stock — before the September ramp, not
  during it.
- **Expected effect:** Losing even 10% of that base costs ~£420,000 a year
  (10% × £4,200,055.35). Protecting it is the highest-value defensive action
  available.

### 2. Build stock 6–8 weeks before the September ramp

- **Evidence:** September–November are £3,594,965.43 (34.96%) of annual
  revenue, and November alone is £1,457,745.53 — 2.86× February — on 2,751
  orders. The ramp starts in September (+39.9% month-over-month).
- **Action:** Pre-build inventory of the top-10 SKUs (9.41% of revenue) and
  the SET/JUMBO groups before September, sized to the November run-rate
  rather than the annual average.
- **Expected effect:** A 5% stock-out on November revenue alone is ~£73,000
  (5% × £1,457,745.53) of lost sales in the single biggest month.

### 3. Win back the 1,066 lapsed customers

- **Evidence:** Lapsed customers are 24.60% of customers but only 5.79% of
  revenue; they last bought 247.5 days ago on average and their mean spend is
  £475.91, against £1,330.93 for Occasional buyers.
- **Action:** A targeted re-engagement offer (not a blanket discount — the
  lapsed group is price-sensitive by definition of having stopped buying) to
  the 1,066, prioritising those whose last purchase was most recent.
- **Expected effect:** Bringing back 10% of them at their mean spend
  (£475.91) is worth ~£50,732 (107 × £475.91); if they return at the
  Occasional-buyer mean (£1,330.93), ~£141,877.

## Limitations

- **Single retailer, single year (2010–2011):** historical data, not a
  current-market tool. Seasonality is observed, not estimated from multiple
  years; the forecast is a trend extrapolation, not a seasonal prediction.
- **Product groups are derived** (first alphabetic word of the product
  description), not source categories — "Other" is 65.46% of revenue.
- **Prices may or may not include VAT** — the dataset does not state it.
- **14.80% of revenue (£1,522,177.33) has no CustomerID** and is excluded
  from RFM/clustering only; cluster shares are shares of identified-customer
  revenue.
- **No Saturday transactions at all** in the data — a data quirk (the retailer
  apparently did not trade on Saturdays), not a finding about demand.
- **Recommendations are commercial judgements grounded in measured numbers,
  not measured effects:** the £-values are what is at stake if the stated
  assumption holds, not a measured uplift.
- The SQL check (notebook): monthly revenue and the top-5 countries recomputed
  in SQLite and asserted equal to the pandas result.
