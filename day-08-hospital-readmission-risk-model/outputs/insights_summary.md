# Day 08 — Hospital Readmission Risk Model: Insights

**Data:** UCI Diabetes 130-US Hospitals 1999–2008 (id 296), 101,766
de-identified encounters; binary target `<30`-day readmission (11,357;
11.16%). Patient-grouped 80/20 hold-out (train 80,090 / test 20,024, seed
42, zero patient overlap); 1,652 expired/hospice discharges excluded.
Every number below is from the committed processed CSVs (`data/processed/`).

## Finding 1 — Prior inpatient visits are the strongest signal (Q1)

On the committed 1,000-row cleaned sample, the <30-day readmission rate
rises steeply with the number of inpatient visits in the previous year:
**7.1%** with 0 prior visits (n=675), **16.7%** with 1 (n=186), **17.2%**
with 2 (n=64) and **22.7%** with 3+ (n=75). Length of stay and medication
load point the same way, but nothing else in the descriptive tables moves
as much. The model agrees: in the HistGB permutation importance
(`feature_importance.csv`), `number_inpatient` is first by a wide margin
(Δ ROC-AUC **0.0753**), discharge disposition second (**0.0532**), and
every other feature is ≤ 0.0071 (`diag_1_group` 0.0071, `payer_code`
0.0059, `medical_specialty` 0.0049). A patient's recent admission history
is, by far, the most informative thing in the record.

## Finding 2 — Both models discriminate modestly, and HistGB is ahead on both curves (Q2)

Test-set results (`model_metrics.csv`), against the prevalence-only
baselines (ROC-AUC 0.5, PR-AUC 0.1116, Brier 0.1006):

| Model | ROC-AUC | PR-AUC | Brier | Sensitivity @ 0.5 | Specificity @ 0.5 | Precision @ 0.5 | F1 |
|---|---|---|---|---|---|---|---|
| Logistic regression | 0.6612 | 0.2071 | 0.0971 | 0.0128 | 0.9977 | 0.4203 | 0.0248 |
| HistGradientBoosting | 0.6761 | 0.2293 | 0.0956 | 0.0088 | 0.9994 | 0.6667 | 0.0174 |

5-fold grouped CV on the train set agrees (ROC-AUC 0.6633 ± 0.0032
logistic; 0.6736 ± 0.0033 HistGB; PR-AUC 0.2177 ± 0.0070 / 0.2334 ±
0.0071), so the hold-out is not a fluke. The honest reading is in the
confusion matrix: at threshold 0.5 the models catch only ~1% of
readmissions (29 of 2,272 logistic; 20 of 2,272 HistGB) — at 11%
prevalence they almost never predict "readmitted". Precision on the few
they do flag is 0.42 / 0.67. The threshold was deliberately not tuned
(plan §4.1); these models rank patients, they do not make a yes/no rule.

## Finding 3 — Calibration is reasonable as-is, with opposite small biases (Q3)

Both models beat the prevalence-only Brier (0.1006): logistic **0.0971**,
HistGB **0.0956**. Calibration slopes are close to the ideal 1 —
logistic **0.913** (slightly over-confident: its high predictions run a
little hot) with intercept **−0.161**, HistGB **1.070** (slightly
under-confident) with intercept **+0.143**. Calibration-in-the-large is
nearly exact: mean predicted risk 0.1125 / 0.1126 vs observed 0.1135. The
decile table tells the same story: the lowest-risk decile is observed at
4.0% / 3.8% against a predicted 4.6% / 4.5%, and the highest-risk decile
at 26.2% / 28.3% against a predicted 27.0% / 26.3%. No recalibration was
applied (out of scope); Platt/isotonic scaling is recorded as future work
in the model card.

## Finding 4 — Performance is broadly consistent by gender and race, but falls off for the oldest patients (Q4)

- **Age:** ROC-AUC is highest at [20-30) (0.753 logistic / 0.799 HistGB)
  and falls steadily with age, to **0.507 / 0.561 at [90-100)** — the
  logistic model is barely better than chance for the oldest patients.
  Age [0-10) has 33 test patients and **0 readmissions**, so its ROC-AUC
  is undefined (flagged small-n, omitted from chart 04(b)).
- **Gender:** Female 0.668 / 0.683, Male 0.654 / 0.669 (logistic / HistGB)
  — a small, consistent gap, not a failure.
- **Race:** Caucasian 0.661 / 0.676 and African American 0.663 / 0.674 are
  near-identical; Hispanic 0.744 / 0.767, Asian 0.702 / 0.657, Other 0.596 /
  0.608 and Missing-race 0.591 / 0.672 are all flagged small-n (n = 402 /
  141 / 319 / 433; positives 44 / 18 / 26 / 43) and should not be
  over-read.
- **Odds ratios (logistic, top by |log-OR|):** discharge to a Medicare
  swing bed **OR 5.32**, to a psychiatric hospital **OR 3.00**,
  Hematology specialty **OR 3.38**, discharge to a rehab facility **OR
  2.30**; discharge to hospice at home is protective (**OR 0.25**),
  as is discharge to a hospice medical facility (**OR 0.41**). These are
  associations from a one-hot model — not causes — and the rare discharge
  categories are noisy; the swing-bed group, for example, is small.

## Recommendation

**Do not use either model as a yes/no readmission rule** — at threshold
0.5 it misses ~99% of readmissions. The defensible next step is to treat
the HistGB predicted risk as a *ranking* for review prioritisation
(highest-risk decile first: 26–28% observed readmission vs 11% overall),
pick an operating threshold against an explicit cost of a missed
readmission vs a false alarm, and then recalibrate (Platt or isotonic)
on a held-out set before anyone quotes a probability. In parallel, the
cheapest modelling win is better history: the signal is concentrated in
prior admissions and discharge destination, so any future feature work
should start there — not with more medication columns.

## Limitations

- Diabetes patients only; 1999–2008 US practice; 130 hospitals; no
  external validation set; encounters after a patient's first readmission
  are not independent observations.
- Small-n subgroups (age [0-10), [10-20), [20-30); Asian, Hispanic, Other,
  Missing-race) are flagged in `subgroup_metrics.csv` — their ROC-AUCs
  are unstable.
- Rare-category odds ratios (e.g. swing bed OR 5.32) come from small
  groups and are noisy; odds ratios are unadjusted-for-collinearity
  coefficients from the one-hot logistic model.
- Sample-based descriptive rates (chart 01(b), notebook Q1) use the
  committed 1,000-row sample, not the full cohort.
- **Not a clinical tool.** This is an analytical exercise on
  de-identified example data.
