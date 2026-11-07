# Test report — Day 03 Crypto Market Anomaly Detector

**Role:** Tester (role 4 of 6). **Date:** 2026-11-07. **Tester:** Jarvis (subagent).
**Verdict: CONDITIONAL FAIL — the build is verified correct, but the day does
NOT meet the plan's full success checklist.** All code, data, tests, lint,
smoke gate, charts, notebook and provenance checks pass. Two of the five
plan §4.4 evaluation targets are missed (defects D1, D2 below), both
independently confirmed to the 6th decimal. Per plan §4.4 thresholds were
fixed before evaluation and must NOT be tuned to pass, so these are not
code defects the optimizer can fix by tuning — they are a publish decision
for Victor / the publisher, with the misses already disclosed honestly in
`outputs/anomaly_evaluation.md` §4.

No code, data or docs were edited by the tester. The only files the tester
wrote are this report and a fresh `screenshots/dashboard.png` (real capture,
overwriting the coder's capture — see §4). One side effect to record: the
§3 offline pipeline re-run temporarily flipped
`data/processed/data_source.json` `source` to `"cache"` (plan §3.3 rule);
the original file was restored byte-identical afterwards and the md5 check
passes (see §3).

## 1. Compile — PASS

`cd day-03-crypto-market-anomaly-detector && .venv/bin/python -m py_compile src/anomaly.py src/data_pipeline.py src/make_charts.py src/app.py`
→ exit 0. Python 3.12.3; venv has sklearn 1.9.1, pandas 3.1.1, streamlit 1.66.1.

## 2. pytest — PASS (coder's claim confirmed exactly)

In the coder's venv (nothing installed):

- Inside the day folder: `.venv/bin/python -m pytest tests/test_pipeline.py -q`
  → **23 passed in 11.49 s**, exit 0.
- From the portfolio repo root: `day-03-.../.venv/bin/python -m pytest day-03-crypto-market-anomaly-detector/tests/test_pipeline.py -q`
  → **23 passed in 10.25 s**, exit 0.

## 3. Offline pipeline re-run — PASS (byte-identical reproduction)

`.venv/bin/python src/data_pipeline.py --offline` → exit 0, ~6 s, no network.
Printed: 366 rows/coin, 2025-11-07 → 2026-11-07; baseline flag rate 3.7%
(37 flags, universe 1,005); contamination 0.0368; timeline 54 flags
(both=22, baseline-only=15, forest-only=17); Jaccard (injected run) 0.472;
baseline P 0.524 / R 0.733 / F1 0.611; forest P 0.462 / R 0.600 / F1 0.522;
union P 0.436 / R 0.800 / F1 0.565; per-type recall joint 0.9 / price 1.0 /
volume 0.5.

md5 comparison against pre-run hashes: all four CSVs byte-identical
(`crypto_daily.csv` 1,098 rows = 366/coin, `crypto_daily_injected.csv`
1,098 rows, `anomaly_timeline.csv` 54 rows, `injected_anomalies.csv`
30 rows). `data_source.json` differed only because the offline run set
`source` to `"cache"`; restored byte-identical from backup — final md5
check: all 5 files OK, `source: "live"`, `synthetic: false`, `seed: null`.

## 4. Streamlit smoke gate — PASS

- Port **8503** (fresh; coder used 8502, never 8501).
- `GET /` → **HTTP 200**; `GET /_stcore/health` → **HTTP 200** (`ok`).
- Server log: clean — no errors/tracebacks from the app. Only benign
  Streamlit telemetry noise (CORS fetch of `data.streamlit.io/metrics.json`
  blocked; no app error).
- Real full-page screenshot captured with the venv's Playwright + headless
  Firefox (viewport 1400×4900) → `screenshots/dashboard.png`,
  **1,135,983 bytes, 1400×4900 px** — a real render of the running app
  (title, sidebar filters, metrics 54 / 22 / 15 / 17 / Jaccard 0.41,
  per-coin overlap table, timeline table, most-extreme flags, all 4 charts,
  footer). App numbers in the screenshot agree with the timeline:
  per-coin baseline 14/13/10, forest 13/13/13, both 8/8/6, totals 19/18/17.
- Server killed afterwards; `ss` shows **port 8503 free**, no streamlit
  process remains (curl after kill: connection refused, as expected).

## 5. Manual validation of one metric — PASS

ETH 2026-08-20, recomputed independently from `crypto_daily.csv`
(trailing 30-day mean/std of prior daily returns, excluding today):

- `return_z`: recomputed **10.838289024** vs committed timeline value
  **10.838289** → diff **2.4e-08** (rounding at the CSV's 6 d.p.; the value
  rounds exactly to the stored figure).
- `volume_z`: recomputed **4.912120872** vs committed **4.912121** → diff
  **1.3e-07** (same 6-d.p. rounding).
- The same independent recomputation reproduced the entire flag set:
  symmetric difference vs `anomaly_timeline.csv` = **0** (no missing, no
  extra flags). The coder's hand-check claim (10.838289) is confirmed.

## 6. Chart legibility — PASS (with two cosmetic notes, C1–C2)

All 4 PNGs in `outputs/charts/` inspected at full resolution (exactly 4,
no extras). All are drawn to scale, axes labelled with units, legends
present, source note present, no cut-off axes, no overlapping text at full
size. Every plotted number agrees with the committed CSVs (chart 1 legend
counts BTC 4/6/9, ETH 3/6/9, SOL 3/9/5; chart 3 rule counts R1 12/10/5,
R2 3/4/4, R3 5/4/6 and severity/both splits all match the timeline;
chart 4 bars match §7 exactly).

- **C1 (cosmetic, confirms coder's note):** chart 3 middle-panel subtitle
  `(High / Medium / Low (§4.2))` — at full size the `§` is legible, but at
  the small dashboard-embedded size it reads as `($4.2)`. Cosmetic only.
- **C2 (cosmetic):** chart 2's top-right corner is crowded — legend
  (Unflagged 1044 / Low 21 / Medium 23 / High 10) plus the three
  R1/R2/R2-floor guide labels sit in the same corner — but everything
  remains readable at full size. The guide labels are correctly captioned
  as median-σ approximations. Two forest-only points sit at log volume
  ratio ≈ −4.7 (volume ~1% of trailing mean); these are data-driven flags,
  not a chart error.
- Minor observation (not a defect): in the dashboard screenshot the
  timeline table's Explanation column is cut off at the right edge
  (Streamlit dataframe horizontal scroll); the full text exists in the CSV.

## 7. Independent verification of the evaluation numbers — CONFIRMED

Recomputed with a hand-written script in `/tmp` (own rolling-z, rules and
forest code — no import of `src/anomaly`), from the committed
`crypto_daily.csv`, `crypto_daily_injected.csv` and
`injected_anomalies.csv`, ±1-day tolerance, n=30 (10 per type).
First attempt used the real-run contamination (0.0368) for the injected
run and diverged on the forest; corrected to the pipeline's rule
(contamination = each run's own baseline rate — injected run 0.051741),
after which **every number matched the coder's claims exactly**.
Cross-checked again by running the coder's own `evaluate()` on the
committed injected CSV — identical results. (Precision here is the
coder's definition: TP = matched injections, FP = flags not within ±1 day
of any injection; P = TP/(TP+FP).)

| Metric | Recomputed (independent) | Coder claimed | Target | Verdict |
|---|---|---|---|---|
| Union recall | 0.800000 (TP 24/30) | 0.800 | ≥ 0.80 | **PASS** (exactly at target) |
| Union precision | 0.436364 (TP 24, FP 31, 72 flags) | 0.436 | ≥ 0.50 | **FAIL — D1** |
| Union F1 | 0.564706 | 0.565 | — | — |
| Baseline P / R / F1 | 0.523810 / 0.733333 / 0.611111 (TP 22, FP 20, 52 flags) | 0.524 / 0.733 / 0.611 | — | — |
| Forest P / R / F1 | 0.461538 / 0.600000 / 0.521739 (TP 18, FP 21, 54 flags) | 0.462 / 0.600 / 0.522 | — | — |
| Jaccard, real data | 0.407407 (22/54) | 0.407 | ≥ 0.30 | **PASS** |
| Jaccard, injected run | 0.472222 (34/72) | 0.472 | — | — |
| Baseline flag rate | 0.036816 (37/1,005) = 3.7% | 3.7% | 2–5% | **PASS** |
| Per-type recall, price spike | 1.00 (10/10) | 1.00 | ≥ 0.60 | **PASS** |
| Per-type recall, volume surge | 0.50 (5/10) | 0.50 | ≥ 0.60 | **FAIL — D2** |
| Per-type recall, joint shock | 0.90 (9/10) | 0.90 | ≥ 0.60 | **PASS** |

Anomaly counts confirmed from `anomaly_timeline.csv`: **54 flagged days**
(baseline 37 = both 22 + baseline-only 15; forest 39 = both 22 +
forest-only 17); severity High 10 / Medium 23 / Low 21; rules R1 27,
R2 11, R3 15; per coin 19/18/17. Flag-month concentration in the insights
also confirmed: Feb 2026 = 16, Aug 2026 = 11, Apr/May/Jul 2026 = 0.
Warm-up NaN counts confirmed: `return_z` NaN 31/coin, `volume_z` NaN
60/coin (coder's disclosed 60-day volume warm-up).

## 8. Lint — PASS

`.venv/bin/black --check src tests` → exit 0 (5 files unchanged).
`.venv/bin/ruff check src tests` → exit 0 ("All checks passed!").
`grep use_container_width src/` → none; `width="stretch"` used 6× in
`src/app.py`.

## 9. Ethics guard — PASS

Searched `README.md`, `src/app.py`, `outputs/insights_summary.md`,
`outputs/anomaly_evaluation.md`, `data/README.md` for "manipulation".
Every occurrence is in the disclaimer/negative sense only ("not evidence
of manipulation", "never presented as proven manipulation", "no
ground-truth manipulation label", "cannot distinguish … from
manipulation"). The §4.5 ethics sentence is present in README, app and
insights. No flagged day is presented as proven manipulation anywhere.

## 10. Provenance — PASS

`data/processed/data_source.json`: `source: "live"`, `synthetic: false`,
`seed: null`, window 2025-11-07 → 2026-11-07, coins
bitcoin/ethereum/solana. Raw JSONs 39,951 / 40,155 / 39,836 bytes (<1 MB
each, ~120 KB total); no `*_synthetic.json` files exist. `.gitignore`
mirrors Day 2 and does NOT exclude `data/` (only
`data/raw/*_synthetic.json`).

## Extra check (plan §8 notebook item)

`jupyter nbconvert --to notebook --execute notebooks/analysis.ipynb`
→ executed end-to-end offline, **13 cells, 0 error outputs**. (One
standard Jupyter warning about unencrypted TCP kernel transport — not an
error.)

## Plan §8 success checklist — item-by-item

| §8 item | Verdict |
|---|---|
| Problem statement + audience written | PASS |
| Data source documented (provider, endpoint, date, licence, row counts; `data_source.json` source-field rule satisfied) | PASS |
| Repeatable prep steps + anomaly definitions documented | PASS |
| ≥2 well-labelled visualisations, to scale and legible, + functional evaluation report + dashboard runs (smoke gate) | PASS (cosmetic C1, C2 only) |
| Interpretation written (one finding per §2 question) + one actionable recommendation + separate evaluation report | PASS (recommendation at `outputs/insights_summary.md:41`) |
| README with setup, sample outputs, limitations | PASS |
| No credentials / private records; no huge raw files; `.gitignore` does not exclude `data/` | PASS |
| One metric manually validated by hand and recorded | PASS (§5 above; diff 2.4e-08) |
| Pipeline runs end-to-end; pytest passing from repo root AND day folder | PASS |
| Notebook runs top-to-bottom without errors (offline, `_find_root()`) | PASS |
| Pinned dependencies incl. scikit-learn; black + ruff clean | PASS (`scikit-learn==1.9.1` in `requirements.txt`) |
| Streamlit smoke gate (fresh port, HTTP 200 ×2, real screenshot, killed, port free) | PASS |
| Charts to scale and legible | PASS |
| **Evaluation targets (§4.4, part of the §8 success criteria)** | **FAIL — D1 and D2** |

## Defects

### D1 — Union precision 0.436 < 0.50 target (CONFIRMED)
- `outputs/anomaly_evaluation.md:103` (target table) and `:112` (diagnosis);
  `outputs/charts/04_evaluation.png` (Union precision bar 0.44).
- Independently recomputed: TP 24, FP 31, 72 union flags on the injected
  run → precision 24/(24+31) = **0.436364** vs target ≥ 0.50.
  Shortfall 0.064. Diagnosis (already in the evaluation report §4):
  precision counts genuine unusual real days as false positives by
  construction, because the test labels only the 30 planted anomalies.
- Not fixable by threshold tuning — plan §4.4 forbids tuning after
  evaluation. Publish decision, not a code fix.

### D2 — Volume-surge per-type recall 0.50 < 0.60 target (CONFIRMED)
- `outputs/anomaly_evaluation.md:107` (target table) and `:121`
  (diagnosis); `outputs/charts/04_evaluation.png` (Volume surge bar 0.50).
- Independently recomputed: **5 of 10** planted volume surges detected
  (union, ±1-day tolerance) → recall **0.50** vs target ≥ 0.60.
  Diagnosis (already in the report §4): planted 4× surges on quiet-volume
  days are only 1.5×–2.6× their trailing mean (volume_z 1.9–2.8, just
  under R2's bar of 3). This is the detector's known blind spot.
- Not fixable by threshold tuning — plan §4.4 forbids it. Publish
  decision, not a code fix.

### Known non-defects (coder-disclosed, verified, no action needed)
- `volume_z` warm-up is 60 days, not 30 (first 60 `volume_z` per coin
  NaN; confirmed in the CSVs). Documented in `src/anomaly.py`, tested.
- `fit_isolation_forest` returns `tuple[dict[str, IsolationForest],
  pd.DataFrame]` (`src/anomaly.py:134-139`), not the plan's literal
  `tuple[IsolationForest, pd.DataFrame]` — one forest per coin, so the
  plan's signature does not fit; behaviour matches the plan otherwise.
- Chart 2 threshold guides are labelled median-σ approximations (stated
  in the chart caption and README) — deliberate, not a data error.
- Notebook summary markdown is static text while Q1–Q3 cells recompute
  live (verified consistent for this build).

## Optimizer's first step

Do NOT touch thresholds, rules, or the forest to chase D1/D2 — the plan
forbids post-evaluation tuning. Instead: (1) confirm the two misses are
already stated plainly with their numbers in the README, insights and
evaluation report (they are — spot-checked above); (2) fix only the
cheap cosmetics if Victor wants them — C1 (`§4.2` → spell out
"Section 4.2" in chart 3's subtitle) and C2 (chart 2 legend/guide
crowding) — then re-run `python -m src.make_charts` and the full pytest
suite; (3) hand the publisher a release where the two failed targets are
flagged as a **publish decision for Victor** (ship with the misses
disclosed, or send back to the planner for a target/method change),
because the day otherwise passes every build, test, lint, smoke, chart,
notebook and provenance check.

---

# Re-verification (2026-11-07)

**Role:** Tester (role 4 of 6, re-verification of rework #2). **Date:** 2026-11-07.
**Verdict: PASS — the day now meets the plan's §8 success checklist.**
The rework #1 blocker is resolved by the planner's one-number fix (joint
volume 3.0× → 5.0×), the pipeline runs exit 0 with a silent self-check, and
all five §4.4 targets now pass on the regenerated evaluation, confirmed by
independent recomputation to the 6th decimal. The original D1/D2 findings
above stay on record — they were measurement defects, fixed by the §4.4
amendments, not by detector tuning.

No code, data or docs were edited by the tester. The only file the tester
wrote is this appended section plus a fresh `screenshots/dashboard.png`
(real capture, overwriting the coder's pre-rework capture — see §R5).
The §R3 offline pipeline re-run temporarily flipped
`data/processed/data_source.json` `source` to `"cache"` (plan §3.3 rule);
the original file was restored byte-identical afterwards (md5
`7aa05c959a2d3dddd5e063f4a53b76e7`, `source: "live"`, `synthetic: false`,
`seed: null`).

## R1. Compile — PASS

`cd day-03-crypto-market-anomaly-detector && .venv/bin/python -m py_compile src/anomaly.py src/data_pipeline.py src/make_charts.py src/app.py`
→ exit 0.

## R2. pytest — PASS (coder's claim confirmed exactly)

In the coder's venv (nothing installed):

- Inside the day folder: `.venv/bin/python -m pytest tests/test_pipeline.py -q`
  → **25 passed in 14.69 s**, exit 0.
- From the portfolio repo root: `day-03-.../.venv/bin/python -m pytest day-03-crypto-market-anomaly-detector/tests/test_pipeline.py -q`
  → **25 passed in 12.72 s**, exit 0.

## R3. Offline pipeline re-run — PASS (byte-identical reproduction)

`.venv/bin/python -m src.data_pipeline --offline` → exit 0, ~6 s, no network,
self-check silent (no `HARNESS BUG` assertion). Printed: 366 rows/coin,
2025-11-07 → 2026-11-07; baseline flag rate 3.7% (37 flags, universe 1,005);
contamination 0.0368; timeline 54 flags (both=22, baseline-only=15,
forest-only=17); Jaccard (injected run) 0.538; baseline P 1.000 / R 1.000 /
F1 1.000 (TP 30/30, FP 0); forest P 0.967 / R 0.733 / F1 0.834 (TP 22/30,
FP 2); union P 0.974 / R 1.000 / F1 0.987 (TP 30/30, FP 2); per-type recall
1.0 / 1.0 / 1.0.

md5 comparison against pre-run hashes: all four processed CSVs
byte-identical (`crypto_daily.csv` 1,098 rows, `crypto_daily_injected.csv`
1,098 rows, `anomaly_timeline.csv` 54 rows, `injected_anomalies.csv`
30 rows) and all four charts byte-identical. `data_source.json` differed
only by the `"cache"` flip; restored byte-identical — final md5 check:
all 9 files OK.

## R4. Independent recomputation of all five §4.4 targets — CONFIRMED

Recomputed with a hand-written script in `/tmp/reverify_day03.py` (own
rolling-z, rules and forest code — no import of `src/anomaly`), from the
committed `crypto_daily.csv`, `crypto_daily_injected.csv`,
`injected_anomalies.csv` and `anomaly_timeline.csv`, ±1-day tolerance,
n=30, with the amended precision rule (a flag is a true positive if it
matches an injection **or** a clean-data flag; FP only if it matches
neither). Contamination = each run's own baseline rate (real 0.0368,
injected 0.059701), as in the pipeline. Cross-checks: the recomputation
reproduced the entire real-data flag set with symmetric difference **0**
vs `anomaly_timeline.csv`.

| Metric | Recomputed (independent) | Coder claimed | Target | Verdict |
|---|---|---|---|---|
| Union recall | 1.000000 (TP 30/30) | 1.000 | ≥ 0.80 | **PASS** |
| Union precision | 0.974359 (TP flags 76/78, FP 2) | 0.974 | ≥ 0.50 | **PASS** |
| Union F1 | 0.987013 | 0.987 | — | — |
| Baseline P / R / F1 | 1.000000 / 1.000000 / 1.000000 (TP 30, FP 0, 60 flags) | 1.000 / 1.000 / 1.000 | — | — |
| Forest P / R / F1 | 0.966667 / 0.733333 / 0.833987 (TP 22, FP 2, 60 flags) | 0.967 / 0.733 / 0.834 | — | — |
| Jaccard, real data | 0.407407 (22/54) | 0.407 | ≥ 0.30 | **PASS** |
| Jaccard, injected run | 0.538462 (42/78) | 0.538 | — | — |
| Baseline flag rate | 0.036816 (37/1,005) = 3.7% | 3.7% | 2–5% | **PASS** |
| Per-type recall, price spike | 1.00 (10/10) | 1.00 | ≥ 0.60 | **PASS** |
| Per-type recall, volume surge | 1.00 (10/10) | 1.00 | ≥ 0.60 | **PASS** |
| Per-type recall, joint shock | 1.00 (10/10) | 1.00 | ≥ 0.60 | **PASS** |

Real-data anomaly counts re-confirmed unchanged: **54 flagged**
(baseline 37 = both 22 + baseline-only 15; forest 39 = both 22 +
forest-only 17); severity High 10 / Medium 23 / Low 21; per coin 19/18/17.
Warm-up NaN counts unchanged: `return_z` NaN 31/coin, `volume_z` NaN
60/coin.

**Joint-plant bar check (from the regenerated injected CSVs):** all 10
joint shocks clear both bars — min |return_z| 2.64, min volume_z **2.07**.
Worst case: **SOL 2026-09-19, volume_z 2.07** (|return_z| 2.75), exactly
the planner/coder claim. The other two former failures now pass:
SOL 2026-08-26 volume_z 2.46 (|return_z| 2.64), ETH 2026-09-02 volume_z
2.41 (|return_z| 2.72). All 10 price spikes clear their bar (min
|return_z| 3.85) and all 10 volume surges clear theirs (min volume_z
3.65, ratio 5.00). Constructions in `injected_anomalies.csv`: 10 ×
`4.0x trailing return std`, 10 × `5.0x trailing mean volume`, 10 ×
`3.0x trailing return std + 5.0x trailing mean volume`; 10 per coin.
The planner's amendment-2 prose slip is confirmed (coder's note 3):
"Worst joint |return_z| 2.46" is wrong — 2.46 is SOL 2026-08-26's
volume_z; the worst joint |return_z| is **2.64**. The amendment's table
(2.64 / 2.46) is correct. No action needed.

## R5. Streamlit smoke gate — PASS (fresh screenshot)

- Port **8504** (fresh; coder used 8502, first verification used 8503, never 8501).
- `GET /` → **HTTP 200**; `GET /_stcore/health` → **HTTP 200** (`ok`).
- Server log: clean — no errors/tracebacks.
- Real full-page screenshot captured with the venv's Playwright + headless
  Firefox (viewport 1400×4900) → `screenshots/dashboard.png`,
  **1,139,325 bytes, 1400×4900 px**, md5
  `d8d80ec72e98cf9bb5631869accef594` — a real render of the running app
  (metrics 54 / 22 / 15 / 17 / Jaccard 0.41, per-coin overlap table
  19/18/17, timeline table, most-extreme flags, all 4 charts, and the new
  evaluation text: "Union recall 1.00 (30 of 30 found…) and precision
  0.974 (76 of 78 flags…)"). The stale pre-rework text (0.44 / 24-of-30)
  is gone.
- Note: the first capture attempt (4 s wait after load) showed blank
  metric cards and empty chart 3/4 sections — the app was still rendering.
  Re-captured after a 15 s wait; the final screenshot shows the complete
  page (4 `<img>` elements present). Screenshot timing, not an app defect.
- Server killed afterwards; `ss` shows **port 8504 free**, no streamlit
  process remains (curl after kill: connection refused, as expected).

## R6. Chart legibility — PASS (with one new cosmetic note, C3)

Charts 01–03 byte-identical to the coder's claimed hashes
(`892557cd…`, `bd3d9054…`, `935dad88…`) and to the first verification's
set — unchanged and still legible; they render correctly in the fresh
dashboard screenshot. Chart 04 regenerated only (new md5
`d0ce51b7d351784fbf8aa23269a5a08a`); inspected at full resolution — every
plotted number matches the §R4 recomputation (baseline 1.00/1.00/1.00,
forest 0.97/0.73/0.83, union 0.97/1.00/0.99, per-type 1.00/1.00/1.00,
Jaccard (real data) 0.41, target lines at 0.80 / 0.50 / 0.60). The
dashboard-embedded chart 04 text in `src/app.py` (lines 235–240) and in
`outputs/anomaly_evaluation.md:97,132`, `README.md:68` and
`outputs/insights_summary.md:34–35` all agree with the recomputed numbers.

- **C3 (cosmetic, new):** chart 04's left-panel legend box overlaps the
  "Baseline–forest Jaccard (real data): 0.41 (target ≥ 0.30)" caption at
  the bottom of the panel — the caption's first characters sit behind the
  legend. The numbers are still readable at full size, but the overlap
  is worse at dashboard-embedded size. Optimizer fix: move the legend or
  the Jaccard caption apart when it next regenerates the charts.
- C1 (chart 3 `§4.2` subtitle) and C2 (chart 2 crowded top-right corner)
  are unchanged — still open, still cosmetic, still optimizer items per
  the plan amendment (not coder work).

## R7. Lint — PASS

`.venv/bin/black --check src tests` → exit 0 (5 files unchanged).
`.venv/bin/ruff check src tests` → exit 0 ("All checks passed!").
`grep use_container_width src/` → none; `width="stretch"` used 6× in
`src/app.py`.

## R8. Notebook — PASS

`jupyter nbconvert --to notebook --execute notebooks/analysis.ipynb`
(executed to `/tmp/nb_executed.ipynb`, the committed file untouched, md5
unchanged) → executed end-to-end offline, **13 cells, 0 error outputs**.
The executed Q3 cell prints union P 0.974 / R 1.000 / F1 0.987, per-type
recall 1.0 / 1.0 / 1.0, Jaccard (injected) 0.538, all three target checks
PASS; the Q2 cell prints Jaccard (real) 0.407 and the per-coin overlap
table (BTC 14/13/8, ETH 13/13/8, SOL 10/13/6). (One standard Jupyter
warning about unencrypted TCP kernel transport — not an error.)

## R9. Ethics guard — PASS

Searched `README.md`, `src/app.py`, `outputs/insights_summary.md`,
`outputs/anomaly_evaluation.md`, `data/README.md` for "manipulation".
Every occurrence is in the disclaimer/negative sense only ("not evidence
of manipulation", "never presented as proven manipulation", "no
ground-truth manipulation label", "cannot distinguish … from
manipulation"). The §4.5 ethics sentence is present in README, app and
insights. No flagged day is presented as proven manipulation anywhere.

## R10. No detector changes leaked in — PASS

Spot-checked against the first verified build: R1–R3 thresholds
identical (`src/anomaly.py:118–120`: R1 `|return_z| >= 3`, R2
`volume_z >= 3` and `volume_ratio >= 2`, R3 both `>= 2`); Isolation
Forest identical (`random_state=42`, `n_estimators=200`, contamination
from each run's own baseline rate, `src/anomaly.py:143–145, 169–171,
198`); the only `mean_vol` multiple changes are the two intended ones
(`src/anomaly.py:388` volume surge 5.0×, `:396` joint shock 5.0×);
`HARNESS BUG` self-check present (`src/anomaly.py:438`); the real-data
flag timeline is byte-identical through the re-run (md5
`158bbea8…`) and my independent flag-set reproduction matches it exactly
(symmetric difference 0). Only `inject_anomalies` / `evaluate` + docs +
chart 04 changed, as the amendments scoped.

## Plan §8 success checklist — item-by-item (re-verification)

| §8 item | Verdict |
|---|---|
| Problem statement + audience written | PASS (unchanged) |
| Data source documented (`data_source.json` source-field rule satisfied) | PASS — `source: "live"`, `synthetic: false`, `seed: null`, restored byte-identical after the offline re-run |
| Repeatable prep steps + anomaly definitions documented | PASS (unchanged) |
| ≥2 well-labelled visualisations, to scale and legible, + functional evaluation report + dashboard runs (smoke gate) | PASS (cosmetic C1, C2, C3 only) |
| Interpretation written + one actionable recommendation + separate evaluation report | PASS (numbers updated to the new evaluation and verified in §R4/§R6) |
| README with setup, sample outputs, limitations | PASS |
| No credentials / private records; no huge raw files; `.gitignore` does not exclude `data/` | PASS (unchanged) |
| One metric manually validated by hand and recorded | PASS (first verification §5; ETH 2026-08-20 `return_z` diff 2.4e-08 — unchanged data) |
| Pipeline runs end-to-end; pytest passing from repo root AND day folder | PASS (§R2, §R3) |
| Notebook runs top-to-bottom without errors (offline, `_find_root()`) | PASS (§R8) |
| Pinned dependencies incl. scikit-learn; black + ruff clean | PASS (§R7) |
| Streamlit smoke gate (fresh port, HTTP 200 ×2, real screenshot, killed, port free) | PASS (§R5, port 8504) |
| Charts to scale and legible | PASS (§R6, C3 cosmetic only) |
| **Evaluation targets (§4.4, part of the §8 success criteria)** | **PASS — all five targets pass (§R4)** |

## Defects

None remaining that block the §8 checklist. Original D1/D2 are **closed**
by the §4.4 amendments and this re-verification: union precision is now
0.974 (≥ 0.50) and volume-surge per-type recall is now 1.00 (≥ 0.60),
both confirmed independently.

### Cosmetic notes (optimizer items, not blockers)

- **C3 (new):** chart 04 legend overlaps the Jaccard caption —
  `outputs/charts/04_evaluation.png`, left panel bottom. Move the legend
  or the caption when the charts are next regenerated.
- **C1 (carried):** chart 3 middle-panel subtitle `§4.2` reads as
  `($4.2)` at small sizes — spell out "Section 4.2".
- **C2 (carried):** chart 2 top-right legend/guide-label crowding —
  spread the legend and the R1/R2/R2-floor guide labels apart.

## Optimizer's first step

Fix only the cheap cosmetics C1/C2/C3 when regenerating the charts
(`python -m src.make_charts`, then re-run the full pytest suite) — do
not touch thresholds, rules, the forest, or the injection harness; all
five §4.4 targets already pass and the detector is verified unchanged.
Then hand the publisher a release where the day meets every §8 item:
the only remaining work is the cosmetic chart tidy-up and the standard
frozen-tree check before push.
