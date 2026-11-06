# Day 02 — Crypto Risk & Volatility Analyzer: Test Report

**Tester:** role 4 of 6 (verification only — no code, test, or doc was edited to make a test pass).
**Date:** 2026-11-06 (PST). **Venv:** the coder's `.venv` (Python 3.12.3, provisioned nothing).
**Verdict: PASS with 2 defects** (D1 moderate, D2 minor) for the optimizer to fix. All numbers, pipeline, tests, lint, notebook, smoke gate, and hand validation pass.

## 1. Static checks (coder's venv)

| Check | Command | Result |
|---|---|---|
| py_compile | `.venv/bin/python -m py_compile src/data_pipeline.py src/risk_metrics.py src/make_charts.py src/app.py` | **PASS, exit 0** |
| pytest | `.venv/bin/python -m pytest tests/ -q` | **PASS — 21 passed in 1.24 s, exit 0** (21 tests collected; `tests/test_pipeline.py` only, scaffold `test_smoke.py` correctly absent) |
| black | `.venv/bin/black --check src tests` | **PASS, exit 0** — "5 files would be left unchanged" |
| ruff | `.venv/bin/ruff check src tests` | **PASS, exit 0** — "All checks passed!" |

## 2. Pipeline re-run (offline)

- `.venv/bin/python -m src.data_pipeline --offline` → **exit 0**, "Offline mode: using cached data/raw/ JSON (no network)", "Data source: CACHE".
- `data/processed/crypto_daily.csv`: **1,098 rows** (366 bitcoin, 366 ethereum, 366 solana), window **2025-11-06 → 2026-11-06**, **0 gaps** per coin (full date range present).
- First `daily_return` per coin NaN: 1 per coin. `vol_30d_ann` NaN: **30 per coin** (see Observation O1 — the plan's "first 29" wording is shorthand; 30 is the correct consequence of the first return being NaN, and the test at `tests/test_pipeline.py:284` asserts exactly 30).
- Re-run output was **byte-identical** to the committed CSVs (`diff` clean on `crypto_daily.csv`, `crypto_risk_summary.csv`, `crypto_correlations.csv`) — deterministic offline rebuild.
- Per-coin pipeline printout matches the summary: BTC −26.8% total / −44.7% max DD; ETH −34.7% / −56.2%; SOL −45.1% / −62.9%.

## 3. Charts regeneration

- `.venv/bin/python -m src.make_charts` → **exit 0**, "Wrote 4 charts … (synthetic=False)".
- Exactly **4 PNGs** in `outputs/charts/` (no extras), all non-empty, and **byte-identical** to the coder's files (md5sum check passed):
  - `01_drawdown.png` 195,372 B (1500×750)
  - `02_rolling_volatility.png` 179,559 B (1500×750)
  - `03_correlation_heatmap.png` 89,574 B (1050×900)
  - `04_risk_adjusted_returns_var.png` 108,338 B (1500×1050)

## 4. Notebook execution (offline)

- `jupyter nbconvert --to notebook --execute notebooks/analysis.ipynb --output /tmp/day02_nb_out.ipynb --ExecutePreprocessor.timeout=300` → **exit 0**.
- Executed notebook: 13 cells, 6 code cells, **all have execution counts set, 0 error cells**. (Only a benign TCP-without-encryption kernel warning in the log.)

## 5. Mandatory smoke gate (fresh port 8503)

- Server: `.venv/bin/streamlit run src/app.py --server.port 8503 --server.headless true`
- `GET /` → **HTTP 200**; `GET /_stcore/health` → **HTTP 200**.
- Server log `/tmp/day02_streamlit_8503.log`: **0 lines matching error/traceback/exception** — clean.
- Screenshot: headless Firefox 157.0 via Marionette (the plain `--screenshot` flag fires before Streamlit's JS renders and produced a blank page; `/opt/meta-chromium/chrome` refuses to start in this VM — "Hatch WebGL domain policy is required"). Capture after a 20 s render wait, window 1400×3800 → saved to `screenshots/dashboard.png` (overwrote the coder's file only after verifying this capture is good).
  - **New screenshot: `screenshots/dashboard.png`, 1400×3714 px, 469,562 bytes** (coder's was 1400×3600, 467,475 bytes).
  - Verified good: title, summary table, correlations table, all 4 charts, and the full footer ("Powered by CoinGecko. Educational analysis only — not investment advice…") all render; no crash, no blank sections.
- Server killed after capture; `curl` after kill → HTTP 000 (connection refused) and `ss` shows **no 850x listeners — port 8503 free**.

## 6. Hand validation — one metric recomputed independently from the committed CSVs

**Bitcoin max drawdown**, recomputed by hand from `data/processed/crypto_daily.csv` (running max, `price / running_max − 1`, no use of the coder's summary):

- Peak: **$105,951.49599987874 on 2025-11-11**
- Trough: **$58,566.091991843154 on 2026-07-01**
- Max drawdown: **−0.4472367620754484 = −44.72367620754484%**
- Peak-to-trough: **232 days**; not recovered by 2026-11-06
- Agreement with `crypto_risk_summary.csv`: **difference 0.0** (exact, ≤1e-9 required) — peak price/date, trough price/date, and percentage all match exactly. Current drawdown also matches exactly (−0.28263864100418223, diff 0.0); total return matches exactly (−0.2683260549150418, diff 0.0).
- This agrees with the hand-validation already recorded in `data/README.md:34-42`.

**Cross-checks (same independent recomputation, all difference 0.0):** ETH max DD −0.5624211689010022 and SOL max DD −0.6285213411842481; all three coins' vol_30d mean/median/max and max dates (BTC 2026-03-05, ETH 2026-02-26, SOL 2026-02-28); Sharpe (BTC −0.490781, ETH −0.406305, SOL −0.646686); Sortino with the plan's formula `sqrt(mean(min(r,0)^2))` over the full window (BTC −0.694885, ETH −0.590582, SOL −0.916392); VaR 95% / CVaR 95% (BTC −3.378%/−5.023%, ETH −4.671%/−6.813%, SOL −5.285%/−7.057%); correlations full window (BTC–ETH 0.907547, BTC–SOL 0.870060, ETH–SOL 0.875645) and latest 90d (0.899165 / 0.848224 / 0.837093, 90 rows). **Every coder-claimed number in the handoff verifies exactly.**

## 7. Chart legibility verdict (all 4 PNGs opened and read)

| Chart | Verdict |
|---|---|
| 01_drawdown.png | **Legible.** Title, axes with units, legend, 0% line, per-coin max-DD annotations with dates, source footer. Values to scale. |
| 02_rolling_volatility.png | **Legible, minor cosmetic overlap** (see O2). Axes labelled (%), max-vol annotations present, to scale. |
| 03_correlation_heatmap.png | **Legible — coder gap (b) is acceptable.** Colour scale fixed −1 to +1, every cell labelled, latest-90d values in the caption line; the footer/caption is tight but fully readable, nothing clipped. No fix needed. |
| 04_risk_adjusted_returns_var.png | **FAIL on the top panel** (see D1). Bottom VaR/CVaR panel is legible, CVaR ≤ VaR visible. |

**Coder gap (a) — summary table wider than viewport: CONFIRMED as a defect (D2).** In the fresh port-8503 screenshot the summary table is cut off at "Mean 30d v…" — the median/max volatility, Sharpe, Sortino, VaR and CVaR columns are not visible without horizontal scrolling. The numbers exist elsewhere (chart 4, README), but the dashboard's primary table hides its key risk columns.

## 8. Provenance / pins / secrets

- `.gitignore`: **does NOT exclude `data/`** — only `data/raw/*_synthetic.json` (line 12). Correct per plan §6.
- `data/processed/data_source.json`: `source: "live"`, `synthetic: false`, `seed: null`, window 2025-11-06 → 2026-11-06, coins bitcoin/ethereum/solana. **PASS.**
- `requirements.txt` pins vs venv (`pip list`): **all 9 match exactly** — pandas==3.1.1, numpy==2.5.4, matplotlib==3.11.2, plotly==7.1.0, streamlit==1.66.1, requests==2.34.2, pytest==9.2.0, jupyter==1.1.1, nbformat==5.11.1; Python 3.12.3. (Dev tools black==26.10.1, ruff==0.17.4 also present in the venv.)
- **No credentials/secrets:** grep over `*.py/*.md/*.txt/*.toml/*.json/*.ipynb` for hard-coded keys/passwords/tokens found nothing. The only key reference is `os.environ.get("COINGECKO_DEMO_API_KEY")` in `src/data_pipeline.py:392` (env var only, never hard-coded). No `.env` file, no `*_synthetic.json` files present.
- Raw JSONs: ~40 KB each (39,837–40,154 B), under the 1 MB limit. `pyproject.toml` matches plan §6 (ruff/black line-length 88, py312, pytest testpaths).
- README.md summary table (lines 46–48) and `outputs/insights_summary.md` numbers (drawdowns, returns, vols, Sharpe/Sortino, VaR/CVaR, correlations, recovery days) all **match `crypto_risk_summary.csv` / `crypto_correlations.csv`** on spot check. `data/README.md:34-42` records the hand-validated metric.

## 9. Defects

### D1 (moderate) — Chart 04 top panel: Sharpe/Sortino bars are invisible; unlike units share one axis
- **Files:** `src/make_charts.py:207-209, 219` and `src/app.py:172-177`.
- **What:** Total return (%) and Sharpe/Sortino (ratios, ≈ −0.4 to −0.9) are plotted as grouped bars on a single axis labelled "Total return (%) / ratio" spanning roughly −48 to 0. The Sharpe/Sortino bars are ~1% of the axis height — invisible slivers with no value labels — so the panel communicates only total return. Plan §7 requires "twin axis or normalised panel — label clearly, do not plot unlike units on one axis without labelling". The same flaw appears in the dashboard's native Plotly chart 4 (visible in the port-8503 screenshot).
- **Fix (optimizer):** give Sharpe/Sortino their own twin axis or a separate normalised panel, or add value labels to every bar, in both `make_charts.py` and `app.py`; then re-run `make_charts` and re-capture the screenshot.

### D2 (minor) — Dashboard summary risk table is wider than the viewport; key columns hidden
- **File:** `src/app.py:105` (`st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)`).
- **What:** At 1400 px wide the table shows only Coin, Total return, Max drawdown, Current drawdown, Peak → trough, Recovery, and a cut-off "Mean 30d v…" column. Median/max volatility, Sharpe, Sortino, VaR 95% and CVaR 95% require horizontal scrolling. Confirmed in the fresh port-8503 screenshot.
- **Fix (optimizer):** shorten/rotate column content (e.g. split the table into a drawdown/volatility table and a risk-adjusted/tail-risk table, or abbreviate headers and values) so the full risk picture is visible without scrolling; then re-capture the screenshot.

## 10. Observations (not defects)

- **O1 — vol NaN count:** `vol_30d_ann` has 30 NaN rows per coin, not the "first 29" the plan §5/§6 wording suggests. This is the correct consequence of the stated formula (the first daily return is NaN, so the first 30-day window is never complete until row 30); the test at `tests/test_pipeline.py:284` asserts exactly 30 with the comment "first 29 + first return NaN". No code change needed; the plan wording is the only imprecision.
- **O2 — Chart 02 annotation overlap (cosmetic):** in `02_rolling_volatility.png` the "Solana (SOL): 107% (2026-02-28)" and "Ethereum (ETH): 104% (2026-02-26)" labels at the top nearly touch (`src/make_charts.py:122` annotation block). Both remain readable; nudge them apart only if touching chart 04 anyway.
- **O3 — Screenshot tooling note for future days:** plain Firefox `--screenshot` captures before Streamlit's JS renders (blank page) and `/opt/meta-chromium/chrome` refuses to start in this VM ("Hatch WebGL domain policy is required"). The working route was headless Firefox 157.0 driven over Marionette (stdlib-only Python client, `/tmp/day02_marionette_shot.py`, 20 s render wait). Worth keeping as the smoke-gate screenshot method.

## 11. Success-checklist (§8) status

All items pass except the two defects above: problem/audience documented; source/licence/rows documented; repeatable steps + KPI definitions written; 4 well-labelled visualisations + working dashboard (smoke gate passed); interpretation + one actionable recommendation in `outputs/insights_summary.md`; README with setup/sample outputs/limitations; no credentials, raw files <1 MB, `.gitignore` correct; one metric hand-validated (this report §6, `data/README.md:34-42`); pipeline runs end-to-end offline; notebook executes offline with `_find_root()`.
