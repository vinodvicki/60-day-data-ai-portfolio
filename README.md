# 60-Day Data Analytics + AI Portfolio

[![CI](https://github.com/vinodvicki/60-day-data-ai-portfolio/actions/workflows/ci.yml/badge.svg)](https://github.com/vinodvicki/60-day-data-ai-portfolio/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/vinodvicki/60-day-data-ai-portfolio/blob/main/LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)

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
| [10](day-10-retail-sales-intelligence-dashboard/) | Retail Sales Intelligence Dashboard — UCI Online Retail, 527,795 cleaned lines, £10.28m revenue; Nov 2011 peak £1.46m (2.86× Feb), top 222 customers 47.94% of revenue, Holt-Winters 8-week forecast £3.06m (mean RMSE £55,505 vs naïve £62,801) | Retail | ✅ Done (2026-11-14) |
| [11](day-11-inventory-demand-forecast/) | Inventory Demand Forecast — UCI Online Retail, 527,795 cleaned lines, 5,241,272 units over 52 full weeks; top-20 SKU 4-week forecast 69,194 units, aggregate 627,508, reorder total 97,314; moving average wins overall (WAPE 44.16% vs naïve 44.33%), aggregate naïve 8.25% | Retail | ✅ Done (2026-11-15) |
| [12](day-12-customer-segmentation-engine/) | Customer Segmentation Engine — UCI Online Retail, 527,795 cleaned lines, 4,334 customers; RFM + KMeans (k = 2, silhouette 0.4330): Champions 1,661 drive 84.9% of attributed revenue (£7,436,335.44), Hibernating 2,673 hold 15.1%; SBC↔KMeans agreement 51.5%, pytest 28/28 | Retail | ✅ Done (2026-11-16) |
| [13](day-13-election-campaign-finance-tracker/) | Election Campaign Finance Tracker — FEC 2024 cycle, 4,376 candidates with totals, $6,503.1M candidate receipts; Harris & Biden $1,175.2M each, ActBlue $3,821.2M, PA $2,525.2M (HQ effect), pytest 32/32 | Politics, Elections & Public Policy | ✅ Done (2026-11-19) |
| [14](day-14-voter-turnout-analytics/) | Voter Turnout Analytics — 2024 national VEP turnout 64.30% (156.8M ballots ÷ 243.8M VEP), −1.69 pp vs 2020; Wisconsin 76.66% highest, Hawaii 50.26% lowest; felon-share r = −0.40, pytest 31/31 | Politics, Elections & Public Policy | ✅ Done (2026-11-21) |
| [15](day-15-political-news-coverage-analyzer/) | Political News Coverage Analyzer — 75 RSS articles (NYT 10, Fox News 24, NPR 10, BBC News 31; WSJ and CNN n=0), Other 42.7% of the corpus; mean language sentiment −0.240 to +0.048, no outlet difference beyond chance (Kruskal-Wallis p=0.553), sample-review agreement 55.0%, pytest 38/38 | Politics, Elections & Public Policy | ✅ Done (2026-11-22) |
| [16](day-16-crop-yield-prediction/) | Crop Yield Prediction — USA maize yield 2000–2025 (26 years), Ridge best model held-out RMSE 0.540 t/ha; naive "last year's yield" wins at 0.287 t/ha; heat days strongest weather driver, pytest 21/21 | Agriculture & Farming | ✅ Done (2026-11-23) |
| [17](day-17-drought-impact-analyzer/) | Drought Impact Analyzer — growing-season DSCI vs detrended maize yield r = −0.61, p = 0.0009 (n = 26 years); 2012 worst drought year (DSCI 200.4, yield 2.24 t/ha below trend); Davis County, IA hardest-hit county, pytest 34/34 | Agriculture & Farming | ✅ Done (2026-11-24) |
| 17–60 | See the roadmap catalog | — | Planned |

## Live demos

Dashboards are hosted on Streamlit Community Cloud (free tier), one app
per day, deployed straight from this repo — see
[docs/live-demos.md](docs/live-demos.md) for the deploy steps and the
per-day entrypoints. Apps are not yet deployed; the table in
docs/live-demos.md records each live URL as it goes up.

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

Day 10 headline findings (UCI Online Retail, Chen 2015, dataset 352, CC BY 4.0; 541,909 rows fetched 2026-11-14, 527,795 cleaned lines, Dec 2010 – Dec 2011):
Total revenue £10,283,243.98 across 19,776 orders (AOV £519.99; 4,334 identified customers; repeat rate 65.27%). November 2011 is the peak month at £1,457,745.53 — 2.86× February 2011 (£508,952.87) — and September–November together are 34.96% of annual revenue. The UK is 85.18% of revenue; non-UK orders average £814.03 per order against £489.24 in the UK. RFM + KMeans (k = 4, silhouette 0.616): the top 222 customers (5.12%) drive 47.94% (£4,200,055.35) of identified revenue, while 1,066 lapsed customers (24.60%) last bought 247.5 days ago on average. Holt-Winters (additive trend, no seasonality) 8-week forecast totals £3,061,051.48 (2011-12-05 → 2012-01-23) and beats the naïve baseline in the backtest (mean RMSE £55,504.52 vs £62,800.78). Full detail in
[Day 10](day-10-retail-sales-intelligence-dashboard/) →
[`outputs/insights_summary.md`](day-10-retail-sales-intelligence-dashboard/outputs/insights_summary.md).

Day 11 headline findings (UCI Online Retail, Chen 2015, dataset 352, CC BY 4.0; 541,909 rows fetched 2026-11-15, 527,795 cleaned lines, Dec 2010 – Dec 2011):
5,241,272 units over 52 full weeks; the top 20 SKUs by revenue are forecast to sell 69,194 units over the 4 weeks starting 2011-12-05 (aggregate 627,508, naïve repeating week 52's 156,877 units), with a total order-up-to of 97,314 units (69,194 forecast + 28,120 safety stock) at 95%/90% service levels, assuming zero on-hand and a 1-week lead time. On the Christmas-ramp holdout the 4-week moving average is best overall (WAPE 44.16% vs naïve 44.33%, Holt 45.52%, gradient boosting 65.51%, Croston-SBA 80.30%); per cluster, moving average wins smooth (34.03%) and erratic (47.26%), Holt wins intermittent (52.35%) and naïve wins lumpy (29.74%), while naïve wins the aggregate at 8.25%. Demand is mostly lumpy: of 3,897 SKUs with any demand, 1,932 (49.6%) are lumpy and only 137 (3.5%) smooth; the two lumpy SKUs hold 38,073 units of the reorder total and are flagged review-manually. Full detail in
[Day 11](day-11-inventory-demand-forecast/) →
[`outputs/insights_summary.md`](day-11-inventory-demand-forecast/outputs/insights_summary.md).

Day 12 headline findings (UCI Online Retail, Chen 2015, dataset 352, CC BY 4.0; 541,909 rows fetched 2026-11-16, 527,795 cleaned lines, Dec 2010 – Dec 2011):
RFM + KMeans with k re-derived (k = 2, silhouette 0.4330; k = 3: 0.3374, k = 4: 0.3339) — KMeans decides segment assignment, RFM scores only name and explain: Champions 1,661 customers (38.3%) drive 84.9% (£7,436,335.44) of attributed revenue, while Hibernating 2,673 (61.7%) hold 15.1% (£1,324,731.21); £1,522,177.33 (14.80%) of cleaned revenue has no CustomerID and is unattributed. The SBC cross-check agrees with KMeans for only 51.5% of multi-order customers (1,458 of 2,829), and the RFM-score rule would disagree with KMeans for 2,830 of 4,334 customers — the methods genuinely see different groups. One tailored action per segment: VIP retention for Champions (£7,436,335.44 to protect), one low-cost reactivation email for Hibernating (£1,324,731.21 already lapsed). Tests 28/28 pass. Full detail in
[Day 12](day-12-customer-segmentation-engine/) →
[`outputs/insights_summary.md`](day-12-customer-segmentation-engine/outputs/insights_summary.md).

Day 13 headline findings (FEC 2024 cycle bulk data + openFEC API, retrieved 2026-11-19; 5,332 candidates, 4,376 with totals; 10,102 non-candidate committees):
Candidates raised $6,503.1M and spent $6,728.3M; Harris and Biden each report $1,175.2M (18.07%) and share principal committee C00703975, so the total counts their shared ~$1.18B twice, while the median candidate raised $814. Individuals gave $3,734.5M (59.4%) of the $6,286.0M raised by the 2,259 candidates with a published itemized/unitemized split, 32.8% of it small-dollar (≤ $200). Non-candidate committees raised $22,724.6M, led by ActBlue at $3,821.2M (16.8%). PA leads the state table at $2,525.2M (38.8%) — the Biden/Harris HQ effect, not Pennsylvania donors. Read the $1,373.5M cash total with care: $775.8M (56.5%) is one filing (Norris, P40010415) that fails the cash-identity check; excluding it, candidate cash is $597.7M. Tests 32/32 pass, coverage 51.82%. Full detail in
[Day 13](day-13-election-campaign-finance-tracker/) →
[`outputs/insights_summary.md`](day-13-election-campaign-finance-tracker/outputs/insights_summary.md).

Day 14 headline findings (UF Election Lab VEP turnout, 1980–2024, retrieved 2026-11-21; 1,196 long rows, 52 jurisdictions):
2024 national VEP turnout 64.30% (156,766,239 ballots ÷ 243,803,423 VEP), down 1.69 pp from 65.99% in 2020; the 2022 midterm was 46.12%, down 3.93 pp from 50.05% in 2018. Wisconsin leads 2024 at 76.66%, Hawaii trails at 50.26%; 7 states rose vs 2020, 44 fell (median change −1.68 pp). Presidential-year national turnout ranged 55.28% (2000) to 65.99% (2020); midterm years 36.61% (2014) to 50.05% (2018). Demographic associations are descriptive only: noncitizen share vs turnout r = −0.07, p = 0.639 (n = 51, no clear association); ineligible-felon share r = −0.40, p = 0.003 (moves with turnout; association only). Five outlier rows are reported as filed, never dropped. Tests 31/31 pass, coverage 65.20%. Full detail in
[Day 14](day-14-voter-turnout-analytics/) →
[`outputs/insights_summary.md`](day-14-voter-turnout-analytics/outputs/insights_summary.md).

Day 15 headline findings (outlet RSS feeds, 2026-11-08–2026-11-22; 75 articles: NYT 10, Fox News 24, NPR 10, BBC News 31; WSJ and CNN contributed none — their feeds served only items outside the window):
Corpus-wide, the largest topic shares went to Other (42.7%, 32 of 75) and Technology & AI (22.7%, 17 of 75), then Elections & campaigns (9.3%, 7 of 75); the largest single cell is BBC News × Other at 61.3% (19 of 31, Wilson 95% CI 43.8%–76.3%). Mean language sentiment (VADER compound, title + description text only) was NYT −0.046, Fox News −0.127, NPR −0.240 and BBC News +0.048, and every outlet's 95% CI includes 0. The topic distribution does not differ across outlets beyond chance (chi-square χ²=31.94, p=0.234; collapsed p=0.091; permutation p=0.2214), nor does mean sentiment (Kruskal-Wallis H=2.09, p=0.553). The sample review agreed on 55.0% (11 of 20 articles) — the honest measure of the frozen keyword dictionary. Sentiment is language tone only, never factual bias. Tests 38/38 pass, coverage 56.35%. Full detail in
[Day 15](day-15-political-news-coverage-analyzer/) →
[`outputs/insights_summary.md`](day-15-political-news-coverage-analyzer/outputs/insights_summary.md).

Day 16 headline findings (FAO via Our World in Data maize yields + Open-Meteo ERA5 weather, Iowa/Illinois centroids, retrieved 2026-11-23; 26 annual rows, 2000–2025):
USA maize yield rose from 8.59 t/ha (2000) to 11.71 t/ha (2025), with the 2012 drought year lowest at 7.73 t/ha. Ridge regression is the best of three models on the held-out years 2020–2025 (RMSE 0.540 t/ha, 8.61 bu/acre), ahead of Random Forest (0.592) and OLS (0.785) — but no model beats the naive one-step baseline of last year's yield (RMSE 0.287 t/ha); all beat the train-mean baseline (1.479). The year trend dominates (r = +0.83); among weather drivers, heat hurts most (heat days standardised coefficient −0.49; July mean temperature r = −0.39) while July and June rainfall are mildly positive (r ≈ +0.23). Drivers are associations, not causation; the weather is a 2-state Corn Belt proxy for the national yield series. 2024 yield hand-validated at 11.253324 t/ha (179.28 bu/acre), diff 0.0. Tests 21/21 pass, coverage 47.58%. Full detail in
[Day 16](day-16-crop-yield-prediction/) →
[`outputs/insights_summary.md`](day-16-crop-yield-prediction/outputs/insights_summary.md).

Day 17 headline findings (U.S. Drought Monitor REST API, retrieved 2026-11-24; 1,357 weekly DSCI rows per state, 5,226 county-years, 201 counties; yield FAO via Our World in Data + weather Open-Meteo ERA5, 2000–2025):
Growing-season mean DSCI (Iowa + Illinois average) vs detrended maize yield: r = −0.61, p = 0.0009, R² = 0.38 (n = 26) — each extra 100 DSCI points is associated with about 0.76 t/ha (12 bu/acre) less yield; the raw-yield correlation is far weaker (r = −0.30, p = 0.14) because the technology trend (+0.116 t/ha/yr) masks the signal. Rain totals alone do not explain yield: growing-season precipitation anomaly r = +0.27, p = 0.18; July rain alone r = +0.24, p = 0.23. 2012 is the case study: DSCI 200.4, rain −183 mm (−31%), yield 7.73 t/ha, 2.24 t/ha below trend; worst-hit county that year was Massac County, IL (73.9% in D2+ drought). The 15 hardest-hit counties by 26-year mean D2+ share are all in Iowa — Davis County tops the ranking (12.7%; worst year 2023, 67.3%) — and the worst county-year is Woodbury County, IA in 2023 (97.7% in D2+). The AR(1) 2026 DSCI forecast is 50.2 (interval 1.8–98.5), barely beating the naive last-year forecast on the 2025 backtest (error 8.8 vs 9.3). Iowa 2012 growing-season mean DSCI hand-validated at 204.153846, diff 0.0. Tests 34/34 pass, coverage 51.84%. Full detail in
[Day 17](day-17-drought-impact-analyzer/) →
[`outputs/insights_summary.md`](day-17-drought-impact-analyzer/outputs/insights_summary.md).

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
  and `ruff` clean, `mypy` clean (gradual typing; new days strict-by-default),
  offline smoke tests (`pytest`) passing with coverage measured
  (`--cov=src`, threshold in CI — see `CHANGELOG.md`).
- **No credentials, no private data, no huge raw files** committed.
  `.gitignore` excludes `.venv/`, `__pycache__/`, `.env`, `.env.*`, `*.pem`,
  `*.key`, `credentials*`, secrets — but does NOT ignore `data/` (small
  project datasets are part of the deliverable).
- **CI** (the single consolidated `.github/workflows/ci.yml`) runs lint,
  format, type-check, tests with coverage, orchestrator validation, and
  chart/notebook smoke on every push and pull request. Dependabot opens
  weekly pip updates. Pre-commit hooks (ruff, black, secret scan) run at
  commit time.

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
