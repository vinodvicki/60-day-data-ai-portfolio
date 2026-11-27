# Day 20 — Research Brief: Inflation & Cost of Living Dashboard

**Roadmap entry (Day 20, Banking, Finance & Economics):** "Compare consumer
prices, earnings, and category-level price movements over time."
**Deliverable:** Purchasing-power dashboard with clearly labeled assumptions.

**Date verified:** 2026-11-27 (one lean probe pass; no live fetch by the
researcher — the coder fetches).

## 1. Data source (verified from scratch)

**Source: FRED (Federal Reserve Bank of St. Louis), `fredgraph.csv` endpoint —
no API key, no sign-up.** This is the same no-key route that worked on Day 18
(IMF benchmark prices). All 10 candidate series returned HTTP 200 on
2026-11-27 with the latest observation 2026-10-01 (FRED lag ≈ 1 month; the
October 2026 CPI release is the newest available — November CPI is released
≈ 2026-12-10, so the analysis window ends 2026-10 and the dashboard must say
so).

Endpoint pattern (one per series, `requests.get`, no headers, no key):

```
https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES_ID>
```

Response: CSV with header `DATE,VALUE`, monthly observations, `.` for missing.
Rate limits: none published for fredgraph.csv; be polite — one request per
series, sequential, ≥1 s spacing, single retry after 30 s on 5xx. No auth.

### 1a. Series verified (all HTTP 200)

| Series | What it is | Start | Latest | Rows |
|---|---|---|---|---|
| CPIAUCSL | CPI-U, All Items, seasonally adjusted (headline CPI, index 1982–84=100) | 1947-01 | 2026-10, 337.476 | 959 |
| CPILFESL | CPI-U less food & energy ("core"), SA | 1957-01 | 2026-10, 339.900 | 839 |
| CPIFABSL | CPI-U: Food at Home, SA | 1967-01 | 2026-10, 348.815 | 719 |
| CPIENGSL | CPI-U: Energy, SA | 1957-01 | 2026-10, 340.197 | 839 |
| CPIHOSSL | CPI-U: Housing, SA | 1967-01 | 2026-10, 362.242 | 719 |
| CPITRNSL | CPI-U: Transportation, SA | 1947-01 | 2026-10, 295.893 | 959 |
| CPIAPPSL | CPI-U: Apparel, SA | 1947-01 | 2026-10, 136.985 | 959 |
| CPIMEDSL | CPI-U: Medical Care, SA | 1947-01 | 2026-10, 595.675 | 959 |
| CPIEDUSL | CPI-U: Education, SA | 1993-01 | 2026-10, 150.458 | 407 |
| CES0500000003 | Avg Hourly Earnings, All Employees, Total Private, SA ($/hour) | 2006-03 | 2026-10, $38.00 | 249 |

**Common joint window:** 2006-03 → 2026-10 (247 months) — set by earnings
(start 2006-03) and by Education (1993, not binding). Headline CPI history
1947 → 2026 is kept as a separate long-run series for context only.

**Rejected / not used:** BLS public API v2
(`https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0`) — no key
needed but capped at 25 queries/day and 10 years per call, and it returns
JSON that needs a key for longer ranges; FRED already carries the same BLS
series with full history, so BLS API adds nothing. Wrong-ID trap (Day 18
lesson): every ID above was verified by actual download, not by guessing
from a list — CPIFABSL (food at home) is correct; do not substitute the NSA
variant (CPIFABNS) casually.

## 2. Metric definitions (frozen — later roles copy these, never redefine)

- **YoY inflation** = `CPI(t) / CPI(t-12) - 1`, monthly, in %.
- **MoM inflation** = `CPI(t) / CPI(t-1) - 1`, in %.
- **Cumulative price change since a base date** = `CPI(t) / CPI(base) - 1`.
- **Real (inflation-adjusted) hourly earnings** = `nominal_earnings(t) /
  CPIAUCSL(t) * 100` (1982–84 dollars). Also reported indexed to 2006-03 = 100
  for the purchasing-power chart.
- **Purchasing power of $1** = `100 / CPIAUCSL(t)` — what $1 in 1982–84 buys
  in today's dollars terms; equivalently the "basket cost" = CPI/100 dollars
  for what $1 bought in 1982–84.
- **Category divergence** = category cumulative change since 2006-03 minus
  headline cumulative change since 2006-03 (pp).
- **Real-wage growth (YoY)** = YoY change of real hourly earnings.
- **Volatility** = standard deviation of monthly log changes (annualised ×√12).
- **Basket cost example** (clearly labelled assumption): a fixed $100
  2006-03 basket costs `100 × CPI(t)/CPI(2006-03)` in month t. This is a
  *fixed-basket illustration*, not a household budget — BLS weights change and
  substitution is ignored; the dashboard must label it as such.

## 3. Assumptions to label on the dashboard (roadmap: "clearly labeled assumptions")

1. All CPI series are **seasonally adjusted** (SA) BLS series via FRED;
   index base 1982–84 = 100.
2. Analysis window **2006-03 → 2026-10** (earnings availability); headline
   CPI shown back to 1947 only as long-run context.
3. Latest data **October 2026** (FRED lag ≈ 1 month); not yet November.
4. Real earnings use headline CPI as the deflator; no tax, benefits, or
   hours-worked adjustment — hourly wage only, all private employees.
5. The "$100 basket" is a fixed-basket illustration (no substitution, no
   weight changes).
6. No forecast is made — this day is descriptive (no model beyond a
   clearly-labelled 12-month trailing-average trend line if shown).

## 4. Fallback parameters (if the live fetch fails)

- Synthetic fallback (labelled `_synthetic.csv`, never overwriting real
  files): monthly headline CPI from 2006-03 as a smooth 2.5%/yr trend with
  AR(1) noise (seed 42, σ = 0.3%/mo); category series as headline × category
  drift factors (food +0.1 pp/yr, energy ± high volatility σ = 2%/mo,
  housing +0.3 pp/yr, medical +0.8 pp/yr, apparel −0.5 pp/yr, transport
  +0.0, education −0.2 pp/yr); earnings as 3.0%/yr trend + noise. The
  fallback exists only so `--offline` runs; the real fetch is expected to
  succeed (all 10 series verified 200 today).
- Offline mode: `python3 src/data_pipeline.py --offline` runs from the
  committed `data/raw/*.csv` cache with no network.

## 5. Terms & attribution

- FRED data are U.S. government (BLS) statistics redistributed by the St.
  Louis Fed; free to use with attribution. Attribution line (in README,
  data/README.md, dashboard footer): "Source: U.S. Bureau of Labor
  Statistics via FRED (Federal Reserve Bank of St. Louis)."
- No key, no account, no scraping of a third-party site. No copied code,
  notebooks or dashboards — all analysis written from this brief and the
  roadmap entry.

## 6. Hand-off to the planner

- 10 series, 1 endpoint pattern, common window 2006-03 → 2026-10 (247
  months), latest month 2026-10.
- **Next role's first step:** freeze the processed-file list in plan.md
  §5 before the first pipeline run (Day 19 lesson: files added after the
  first run forced re-runs).
