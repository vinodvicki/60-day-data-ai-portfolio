# Day 19 — Credit Card Fraud Detection: Insights

**Dataset:** 284,807 European card transactions (Sep 2013), 492 frauds
(0.1727%). Test set: 85,443 rows, 148 frauds. All metrics below are on
the held-out test set. Real data — nothing synthetic.

## Finding 1 — The forest wins where it matters, the linear model where it doesn't

Random forest PR-AUC **0.824** vs logistic regression **0.700** — but
logistic regression has the higher ROC-AUC (**0.968** vs **0.944**).
The two rankings disagree: on a 0.17% problem ROC-AUC rewards ranking
legitimate transactions well, while PR-AUC rewards finding the rare
frauds. PR-AUC is the headline metric here, and it picks the forest.
(Chart: `02_pr_curves.png`.)

## Finding 2 — At threshold 0.50 the forest is precise but leaky; the linear model is the opposite

- Random forest: precision **0.972**, recall **0.703** — 104 of 148
  test frauds caught, only 3 false alarms, but $9,762.19 of fraud
  missed.
- Logistic regression: precision **0.067**, recall **0.878** — 130 of
  148 caught, but 1,806 legitimate transactions flagged (review cost
  $9,030) to do it.
- The majority baseline (predict never-fraud) is the accuracy trap:
  99.83% accurate, zero fraud caught, $19,311.89 missed — the most
  expensive option at $2,260.21 per 10,000 transactions.
  (Chart: `03_threshold_tradeoff.png`; table: `model_metrics.csv`.)

## Finding 3 — Lowering the forest's threshold to 0.10 is cheapest overall

At threshold 0.10 the forest catches 124 of 148 frauds (recall 0.838)
with 38 false alarms (precision 0.765); missed fraud falls to
$6,522.19 and review costs just $190, for a total of **$785.58 per
10,000 transactions** — the sweep minimum, vs $1,144.29 at threshold
0.50 and $2,069.13 at 0.95. Best F1 (0.855) sits at threshold 0.30
(precision 0.950, recall 0.777). The cost curve is flat between 0.05
and 0.30 ($786–$858), so the operating point is not knife-edge.
(Chart: `04_cost_curve.png`; table: `threshold_sweep.csv`.)

## Recommendation (analytical next step — never investment advice)

Deploy the random forest at threshold **0.10** for the alert queue:
it catches 84% of frauds at a precision a review team can live with
(about 1 in 4 alerts is real fraud, vs 1 in 15 at threshold 0.50 for
logistic regression). Before production use, re-tune the threshold on
a **separate validation set** — the sweep here is on the test set, so
0.10 is illustrative — and re-estimate the $5 review cost from the
team's actual handling time, since the cost-optimal threshold moves
with it.

## Limitations

- Two days of 2013 European cardholder data — not current fraud
  patterns, not other regions or card products.
- V1–V28 are anonymised PCA components: no feature-level explanation
  of *why* a transaction looks fraudulent is possible.
- Thresholds are swept on the test set and are illustrative.
- The $5 false-alarm review cost is an assumption, not a measured
  figure.
