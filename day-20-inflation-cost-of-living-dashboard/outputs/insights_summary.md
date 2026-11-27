# Day 20 — Inflation & Cost of Living Dashboard: Insights

**Window:** Mar 2006 – Oct 2026 (248 months; Oct 2025 CPI missing — see
Limitations). **Latest data: October 2026.** Source: U.S. Bureau of Labor
Statistics via FRED. All figures from `data/processed/`.

## Finding 1 — Prices are up 69% since March 2006; a dollar buys 30 cents' worth

Headline CPI rose from 199.70 (Mar 2006) to 337.48 (Oct 2026), **+69.0%**
(2.58%/yr compounded). The fixed $100 basket from Mar 2006 costs **$168.99**
in Oct 2026, and the purchasing power of $1 (1982–84 dollars) has fallen to
**$0.30**. Inflation peaked at **8.98% year on year in June 2022**; the
latest readable year-on-year rate is **3.72% (Sep 2026)** — the Oct 2026
rate is undefined because BLS published no Oct 2025 CPI.

## Finding 2 — The averages hide a split: essentials up ~80%, apparel up 15%

Since Mar 2006: housing **+80.0%**, food at home **+79.4%**, medical care
**+79.1%** — each about 10–11 pp above headline — while apparel is up only
**+15.0%** (54 pp below headline) and education **+29.9%** (39 pp below).
Energy is the live driver right now: **+20.4% year on year (Sep 2026)**,
with transportation **+7.8%**, both far above the 3.7% headline rate.
Households feel the categories they cannot avoid; the index average
understates that pressure.

## Finding 3 — Pay has risen, but only just kept ahead — and it slipped behind in Sep 2026

Nominal hourly pay rose **+89.6%** ($20.04 → $38.00), but after inflation
real hourly pay is up only **+12.2%** ($10.04 → $11.26 in 1982–84
dollars; indexed 100 → 112.2). At the margin the gap has closed the wrong
way: real pay **fell 0.54% year on year in Sep 2026** as energy-driven
inflation outran a 3.1% nominal pay rise. Twenty years of real gains are
thin, and the latest year gave some back.

## Recommendation (analytical next step — never investment advice)

Track the **category split, not the headline**: budget and pay
conversations should use the food/housing/medical basket (+79–80% since
2006) rather than the 69% headline, and any pay-rise benchmark should be
set against core inflation (2.57% YoY, Sep 2026) plus the energy swing,
not the headline alone. Next step: rebuild this dashboard when the
November 2026 CPI lands (2026-12-10) to restore a readable YoY series.

## Limitations

- **October 2025 CPI was never published** (2025 lapse in
  appropriations); Oct 2026 YoY and Nov 2025 MoM are undefined, not zero.
- Latest data October 2026 (FRED lag ≈ 1 month).
- Real earnings use headline CPI as the deflator; no tax, benefits, or
  hours-worked adjustment; hourly wage only, all private employees.
- The $100 basket is a fixed-basket illustration: no substitution, no BLS
  weight changes.
- No forecast is made; this dashboard is descriptive.
