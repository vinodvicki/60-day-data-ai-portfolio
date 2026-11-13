# 60-Day Data Analytics + AI Portfolio

**60 days. 60 projects. 20 industries.** One publishable, end-to-end
real-world data + AI project per day, built to the roadmap source document
held locally (`60_Day_Data_Analytics_AI_GitHub_Project_Roadmap_0_4qxt.pdf`,
**not committed to this repo**).

Each day: define one decision-maker, one practical problem and 2–3 questions →
obtain public or synthetic data (with source, date range and terms noted) →
prepare and validate → analyse with metrics and charts (baseline before ML/AI)
→ deliver a notebook, dashboard or small working demo → explain with 3–5
findings, business implications, limitations and next actions → publish clean
code, README, requirements, charts and example results.

> A one-day project means a functional first release, not a production system.
> Never commit private, confidential or identifiable data — or credentials.

## Progress

| Day | Project | Sector | Status |
|---|---|---|---|
| [01](day-01-crypto-market-intelligence/) | Crypto Market Intelligence Dashboard — BTC vs ETH vs SOL over 366 daily observations (2025-11-05 → 2026-11-05) | Crypto | ✅ Done (2026-11-05) |
| [02](day-02-crypto-risk-volatility-analyzer/) | Crypto Risk & Volatility Analyzer — BTC vs ETH vs SOL over 366 daily observations (2025-11-06 → 2026-11-06) | Crypto | ✅ Done (2026-11-06) |
| [03](day-03-crypto-market-anomaly-detector/) | Crypto Market Anomaly Detector — 54 flagged days (baseline rules + Isolation Forest) over 366 daily observations (2025-11-07 → 2026-11-07) | Crypto | ✅ Done (2026-11-07) |
| [04](day-04-youtube-video-performance-analyzer/) | YouTube Video Performance Analyzer — 244 videos, 143 channels, median 611 views/day, 2.20% engagement | Social media | ✅ Done (2026-11-08) |
| [05](day-05-social-media-sentiment-analyzer/) | Social Media Sentiment Analyzer — 1,462 comments on 12 videos, 40.6% positive (rule-based model), validation accuracy 0.617 | Social media | ✅ Done (2026-11-09) |
| [06](day-06-viral-content-trend-explorer/) | Viral Content Trend Explorer — 472 videos, 406 channels, AI & ML and SQL accelerating, Python fading | Social media | ✅ Done (2026-11-10) |
| [07](day-07-disease-prevalence-dashboard/) | Disease Prevalence Dashboard — 6 chronic conditions, 2,956 counties (2023), national diabetes 12.05%, West Virginia highest at 15.88% | Healthcare | ✅ Done (2026-11-11) |
| [08](day-08-hospital-readmission-risk-model/) | Hospital Readmission Risk Model — 101,766 encounters, logistic ROC-AUC 0.6612, HistGB 0.6761, both calibrated (Brier 0.0971 / 0.0956 vs 0.1006 baseline) | Healthcare | ✅ Done (2026-11-12) |
| [09](day-09-healthcare-resource-demand-forecast/) | Healthcare Resource Demand Forecast — 8-week Holt-Winters forecast 3.03% → 13.87%, mean RMSE 0.4693 vs seasonal naïve 0.8244, 161 weeks NSSP + bed utilisation 72.5% | Healthcare | ✅ Done (2026-11-13) |
| 10–60 | See the roadmap catalog | — | Planned |

Day 1 headline findings (live CoinGecko data (Powered by CoinGecko), 366 daily observations, 2025-11-05 → 2026-11-05):
BTC −20.7%, ETH −26.2%, SOL −38.5% total return; max drawdowns −44.7% /
−56.2% / −62.9%; BTC–ETH daily-return correlation 0.906. Full detail in
[Day 1](day-01-crypto-market-intelligence/) →
[`outputs/insights_summary.md`](day-01-crypto-market-intelligence/outputs/insights_summary.md).

Day 2 headline findings (live CoinGecko data (Powered by CoinGecko), 366 daily observations, 2025-11-06 → 2026-11-06):
BTC −26.8%, ETH −34.7%, SOL −45.1% total return; max drawdowns −44.7% /
−56.2% / −62.9%, none recovered by 2026-11-06; BTC–ETH daily-return
correlation 0.908; Sharpe −0.49 / −0.41 / −0.65; one-day VaR 95% −3.4% /
−4.7% / −5.3%. Full detail in
[Day 2](day-02-crypto-risk-volatility-analyzer/) →
[`outputs/insights_summary.md`](day-02-crypto-risk-volatility-analyzer/outputs/insights_summary.md).

Day 3 headline findings (live CoinGecko data (Powered by CoinGecko), 366 daily observations, 2025-11-07 → 2026-11-07):
54 unusual days flagged out of 1,005 flaggable days (37 by the z-score
rules, 39 by the Isolation Forest, 22 by both; Jaccard 0.41); 10 High /
23 Medium / 21 Low severity; most extreme day 2026-08-20 (ETH +17.5%,
return z = 10.8, volume 3.8× its 30-day average); on 30 planted anomalies
the two methods together found 30 of 30 (recall 1.00, precision 0.974).
Full detail in
[Day 3](day-03-crypto-market-anomaly-detector/) →
[`outputs/insights_summary.md`](day-03-crypto-market-anomaly-detector/outputs/insights_summary.md).

Day 4 headline findings (live YouTube Data API v3 data, 244 videos from 143 channels, fetched 2026-11-08):
median 611 views/day, median engagement 2.20%; best topic AI & ML 914 views/day (n=68, solid groups n≥10); best length Long 15–30 min 851 views/day (n=41); top quartile 3,124 vs 380 views/day, engagement 2.01% vs 2.32% (reach ≠ engagement); best weekday Wednesday 878 views/day (n=34). Full detail in
[Day 4](day-04-youtube-video-performance-analyzer/) →
[`outputs/insights_summary.md`](day-04-youtube-video-performance-analyzer/outputs/insights_summary.md).

Day 5 headline findings (live YouTube Data API v3 data, 1,462 top-level
comments on 12 videos, fetched 2026-11-09, 16 quota units):
40.6% positive, 52.6% neutral, 6.8% negative as classified by our own
rule-based lexicon model — but 55.3% of comments matched no lexicon word
and are neutral by default; AI & ML the most negative topic (13.3%
negative, n=294); 59.0% of comments matched no theme; human validation
(n=120) accuracy 0.617, macro-F1 0.613. Full detail in
[Day 5](day-05-social-media-sentiment-analyzer/) →
[`outputs/insights_summary.md`](day-05-social-media-sentiment-analyzer/outputs/insights_summary.md).

Day 6 headline findings (live YouTube Data API v3 data, 472 recently
published data/AI videos in two 30-day cohorts, 236 per window, fetched
2026-11-10, 1,019 quota units): AI & Machine Learning accelerating
(+6.36 pp, +24.2%, 77 vs 62 videos) and SQL accelerating (+3.81 pp,
+20.9%, 52 vs 43); Python fading (−8.05 pp, −21.6%, 69 vs 88); Career /
BI & Visualisation / General Data Analytics insufficient data; velocity,
backtest and sentiment snapshot all empty by consequence — no recent
video aged ≥ 7 days (all 10 query-windows truncated at 50, recent window
effectively Nov 8–9 vs Oct 8–10); median engagement 1.49%. Full detail in
[Day 6](day-06-viral-content-trend-explorer/) →
[`outputs/insights_summary.md`](day-06-viral-content-trend-explorer/outputs/insights_summary.md).

Day 7 headline findings (live CDC PLACES county data, 6 chronic conditions, 2,956 counties in 2023 and 3,144 in 2022, fetched 2026-11-11):
national diabetes 12.05% (2023) vs 11.97% (2022); West Virginia the highest state for diabetes (15.88%), COPD (10.63%), heart disease (8.73%) and obesity (40.63%); diabetes spans 4.9% (Madison County, ID) to 27.1% (Greene County, AL); heart disease fell on the median matched county (−0.50 pp, 86.3% of counties down) while diabetes rose (+0.10 pp); Kentucky and Pennsylvania have no 2023 rows in the source release and Loving County, TX is suppressed, so national 2022→2023 moves are partly compositional. Full detail in
[Day 7](day-07-disease-prevalence-dashboard/) →
[`outputs/insights_summary.md`](day-07-disease-prevalence-dashboard/outputs/insights_summary.md).

Day 8 headline findings (live UCI Diabetes 130-US Hospitals 1999–2008 data, 101,766 encounters, fetched 2026-11-12):
101,766 raw encounters, 11,357 readmitted within 30 days (11.16%); 1,652
expired/hospice exclusions leave 100,114 modelled, split patient-grouped
train 80,090 / test 20,024 with 0 patient overlap. Logistic regression
ROC-AUC 0.6612, PR-AUC 0.2071, Brier 0.0971, calibration slope 0.913 /
intercept −0.161; HistGradientBoosting ROC-AUC 0.6761, PR-AUC 0.2293, Brier
0.0956, slope 1.070 / intercept +0.143 — both beat the prevalence-only
baseline (ROC-AUC 0.5, PR-AUC 0.1116, Brier 0.1006 at test prevalence
0.1135), but at threshold 0.5 both models barely flag anyone (sensitivity
0.0128 / 0.0088), so they rank patients modestly and their probabilities
are roughly calibrated, not decision-ready. Discrimination is weakest for
the oldest patients (age [90-100) ROC-AUC 0.5079 logistic / 0.5611 HistGB)
and strongest at [20-30) (0.7531 / 0.7991); strongest odds ratios:
swing-bed admission 5.32, Hematology specialty 3.38, psychiatric hospital
3.00. Full detail in
[Day 8](day-08-hospital-readmission-risk-model/) →
[`outputs/insights_summary.md`](day-08-hospital-readmission-risk-model/outputs/insights_summary.md).

Day 9 headline findings (live CDC NSSP ED-visit data, 25,116 rows, 161 weeks, fetched 2026-11-13; HHS bed capacity 81,713 rows, 2020-01-01 → 2024-04-27):
Holt-Winters 8-week forecast of national Combined respiratory ED share rises 3.03% → 13.87% (weeks ending 2026-11-07 → 2026-12-26; bands Moderate, Moderate, High, High, Surge, Surge, Surge, Surge), final-week 80% interval 12.76–14.91% and 95% interval 12.08–15.38%; latest observed week 2.3% (2026-10-31), observed max 10.4% (2023-12-30) — the final two forecast weeks exceed the observed max and are read as a severe-season scenario. Backtest (3 rolling origins): Holt-Winters mean RMSE 0.4693 vs seasonal naïve 0.8244, 80%-interval coverage 75.0% vs 91.67% against the ≈80% target. Historically Low 89 / Moderate 35 / High 19 / Surge 18 of 161 weeks; top states Hawaii 7.0%, Florida 3.4%, Louisiana 2.9%, Washington 2.8%, Texas 2.6%; bed utilisation averaged 72.5% (max 78.9%) and was 74.95% in its final week (2024-04-27). Full detail in
[Day 9](day-09-healthcare-resource-demand-forecast/) →
[`outputs/insights_summary.md`](day-09-healthcare-resource-demand-forecast/outputs/insights_summary.md).

## Roadmap phases

| Phase | Days | Focus | Sectors |
|---|---|---|---|
| 1 | 01–15 | Data fundamentals + NLP | Crypto · Social media · Healthcare · Retail · Politics |
| 2 | 16–30 | Forecasting + ML + economics | Agriculture · Finance · Technology · Education · Transport |
| 3 | 31–45 | Domain analytics + risk | Climate · Hospitality · Housing · Energy · Cybersecurity |
| 4 | 46–60 | Product thinking + deployment | Public services · Manufacturing · E-commerce · Jobs · Sports |

## Standards (every day)

- **Problem first:** one decision-maker, one problem, 2–3 questions, stated in
  the README before any code.
- **Documented provenance:** data source, collection date, endpoint, row
  counts and licence/usage constraints in `data/README.md`.
- **Reproducible:** pinned `requirements.txt` (exact `==` versions verified
  in the build venv), `python3 src/data_pipeline.py --offline  # offline from committed data` →
  `python3 src/make_charts.py` → app runs from a clean checkout.
- **Validated:** at least one metric checked by hand, independently of the
  pipeline, and recorded in `data/README.md`.
- **At least two well-labelled visualisations** (title, axes with units,
  legend, source note) or a functional evaluation report.
- **Findings + one actionable recommendation** (analytical next step — never
  investment advice, never a price prediction).
- **Clean code:** modular `src/`, type hints + docstrings, `black` formatted
  and `ruff` clean, offline smoke tests (`pytest`) passing.
- **No credentials, no private data, no huge raw files** committed.
  `.gitignore` excludes `.venv/`, `__pycache__/`, `.env`, secrets — but does
  NOT ignore `data/` (small project datasets are part of the deliverable).
- **CI** (the single consolidated `.github/workflows/ci.yml`) runs tests + lint on every push and
  pull request.

How the days are built: see [`docs/multi-agent-workflow.md`](docs/multi-agent-workflow.md)
— the 6-role workflow (researcher → planner → coder → tester → optimizer →
publisher/reviewer), its token-lean rules, and the Day 1 retrospective.

## How to run Day 1

```bash
cd day-01-crypto-market-intelligence
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 src/data_pipeline.py --offline  # no network; uses committed cache
python3 src/make_charts.py  # regenerate outputs/charts/*.png
streamlit run src/app.py        # dashboard at http://localhost:8501
pytest tests/ -q                # 14 offline tests
```

A live fetch (`python3 src/data_pipeline.py`) is 3 calls ≥5 s apart with a possible 60 s retry on 429.

Each later day follows the same layout (`README.md`, `requirements.txt`,
`.gitignore`, `LICENSE`, `research_brief.md`, `plan.md`, `data/`,
`notebooks/`, `src/`, `outputs/`, `screenshots/`, `tests/`).

## License

Code: MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Victor. Third-party CoinGecko data is **not** covered by the MIT licence; it is under separate CoinGecko terms — see `day-01-crypto-market-intelligence/data/README.md` (the redistribution question is unresolved; no legal certainty is claimed).
