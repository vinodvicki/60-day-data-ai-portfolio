# Day 11 — Inventory Demand Forecast: Insights

**Scope:** analytical exercise on public historical retail transactions
(2010–2011) from UCI Online Retail (Chen 2015, DOI 10.24432/C5BW33, CC BY 4.0).
**Forecast: 4-week trend extrapolation from one retailer over one year — NOT a
seasonal prediction. Reorder list: assumes zero on-hand stock and a 1-week
lead time.**

## Finding 1 — How much will sell over the next 4 weeks?

The top 20 SKUs by revenue (12.36% of cleaned full-week revenue, 451,918 units
over the 52 full weeks) are forecast to sell **69,194 units** over the 4 weeks
starting 2011-12-05, using each SKU's cluster-winning method; the aggregate
series (all cleaned SKUs) is forecast at **627,508 units** (naïve — repeats
week 52's 156,877 units). The biggest single 4-week forecasts are 23084 RABBIT
NIGHT LIGHT (17,840 units — naïve, repeating a Christmas-spike week), 22197
POPCORN HOLDER (13,275) and 22086 PAPER CHAIN KIT 50'S CHRISTMAS (6,853).
Actual demand in the primary holdout (weeks 49–52) was 65,201 units for the top
20 and 681,023 for the aggregate, so the published aggregate forecast sits
8% below the most recent 4-week actual — a trend extrapolation, not a seasonal
prediction, and it should be read that way.

## Finding 2 — Which method works, and for what kind of demand?

On the primary holdout (train weeks 1–48, forecast weeks 49–52 — the Christmas
ramp), the **4-week moving average is the best overall method at 44.2%
volume-weighted WAPE** (naïve 44.3%, Holt 45.5%, gradient boosting 65.5%,
Croston-SBA 80.3%). Per cluster: smooth → moving average (34.0%; Croston-SBA
33.6% was within the 0.5 pp tie-break, so the simpler method wins), erratic →
moving average (47.3%; Holt 46.9% within 0.5 pp, simpler wins), intermittent →
Holt ETS (52.4%), lumpy → naïve (29.7%). The aggregate series is the exception:
naïve wins at 8.3% WAPE. Two measured winners contradict the prior (smooth and
erratic were expected to favour Holt/gradient boosting): the Christmas-ramp
holdout punishes trend extrapolation, and 44 usable training rows per SKU is
too little for gradient boosting. Croston-SBA is worst overall because its flat
rate cannot track bulk spikes — 169.3% WAPE on lumpy SKUs. Seasonal naïve is
n/a on both origins (a 52-week series has no y(t−52) for the holdout weeks).
**Clustering:** of the 3,897 SKUs with any demand, 1,932 (49.6%) are lumpy and
only 137 (3.5%) are smooth; erratic lines carry 48.5% of units. The KMeans k = 4
cross-check on the top 200 SKUs agrees with the SBC quadrants only 64.0% of
the time — partial agreement, and SBC remains the decision-maker. The
supplementary mid-year holdout (train weeks 1–29, forecast weeks 30–33)
disagrees for lumpy SKUs (moving average wins there at 169.3% WAPE, not naïve);
the primary winner still governs the reorder list, as fixed in the plan.

## Finding 3 — What should be reordered now?

Total order-up-to across the top 20 is **97,314 units** (69,194 forecast +
28,120 safety stock), at 95% service for smooth/erratic SKUs and 90% for
intermittent/lumpy. The two lumpy SKUs hold 38,073 of it and are flagged
`review-manually`: 23084 RABBIT NIGHT LIGHT (order-up-to 19,343) and 23166
MEDIUM CERAMIC TOP STORAGE JAR (18,730). 23166 is the warning case — a
476-unit forecast but 18,254 units of safety stock, because one training week
sold 74,215 units (its non-zero-week σ is 14,261 units). The next-largest
order-up-to levels are 22197 POPCORN HOLDER (14,550), 22086 PAPER CHAIN KIT
50'S CHRISTMAS (7,468) and 85099B JUMBO BAG RED RETROSPOT (6,384). A 2-week
lead time would raise the reorder points (see the `reorder_point_2wk_units`
column) — the cost of the 1-week assumption is visible per SKU.

## Recommendation 1 — Order the biggest lines now

- **Evidence:** the reorder list's three largest order-up-to levels are 23084
  (19,343 units), 23166 (18,730) and 22197 (14,550) — together 52,623 units,
  54% of the 97,314-unit total — and the published 4-week forecast for the top
  20 is 69,194 units.
- **Action:** place orders up to those levels this week, starting with 22197
  POPCORN HOLDER (14,550 units, erratic, moving-average forecast 13,275) and
  22086 PAPER CHAIN KIT 50'S CHRISTMAS (7,468 units), whose forecasts are the
  most trustworthy of the large lines.
- **Expected effect:** cover for the forecast 69,194 units of demand plus
  28,120 units of safety stock, so the Christmas-ramp weeks are covered at the
  stated 95%/90% service levels instead of stocking out on the lines that
  sell most.

## Recommendation 2 — Review the two lumpy lines manually; do not auto-order them

- **Evidence:** 23084 and 23166 are flagged `review-manually`; 23166's safety
  stock (18,254 units) is 38× its 476-unit forecast, and Croston-SBA's WAPE on
  lumpy SKUs is 169.3% on the primary holdout (and 3,805.9% on the mid-year
  holdout) — the point forecast is not a prediction for these lines.
- **Action:** a buyer reviews 23084 and 23166 by hand before ordering —
  check the bulk-order history (23166 sold 74,215 units in a single training
  week), confirm whether another bulk order is expected, and order against the
  confirmed order book rather than the 19,343 / 18,730 order-up-to levels.
- **Expected effect:** avoids holding ~38,073 units of mostly-slow stock
  (39% of the total order-up-to) on the basis of a forecast that is wrong by
  more than the demand itself on lumpy lines.

## Recommendation 3 — Hold the safety stock the forecast error itself demands

- **Evidence:** the headline error is large — 44.2% overall WAPE on the
  primary holdout, and even the best per-cluster WAPEs are 29.7%–52.4%; the
  aggregate one-step in-sample WAPEs (naïve 25.6%, moving average 18.3%) are
  far below the holdout errors, so the Christmas ramp, not the model, drives
  the miss.
- **Action:** do not cut the safety stock in the reorder list to save working
  capital — keep the 28,120 units of safety stock (29% of the 97,314-unit
  order-up-to total), and re-run the forecast weekly so the 4-week moving
  average tracks the ramp instead of extrapolating a stale level.
- **Expected effect:** the 28,120 units of safety stock is the cover the
  measured 44.2% error demands; cutting it would convert forecast error
  directly into stockouts on the highest-selling weeks of the year.

## Limitations

- Single retailer, single year (2010–2011); the forecast is a trend
  extrapolation, not a seasonal prediction — no seasonal component is fitted
  and nothing is claimed beyond the 4-week horizon.
- The 4-week holdout falls on the Christmas ramp, so errors look worse than a
  mid-year holdout (the supplementary mid-year holdout is reported alongside
  and disagrees for lumpy SKUs).
- Prices may or may not include VAT (the dataset does not state it); no
  currency conversion or tax adjustment. Demand is counted in units; revenue
  (GBP) is used only to rank SKUs.
- No inventory or lead-time data exists: the reorder list is assumption-based
  (zero on-hand, 1-week lead time, 95%/90% service levels). Never treat the
  order-up-to level as a measured stock position.
- One week (2010-12-27) has zero transactions — the retailer was closed over
  Christmas; December 2011 is a partial month (data end 2011-12-09); no
  Saturday transactions (6-day trading week).
- Data-size exception: the raw XLSX (22.6 MB) is git-ignored and re-downloaded
  at build time; committed data is the processed CSVs plus a 1,000-row cleaned
  sample.
