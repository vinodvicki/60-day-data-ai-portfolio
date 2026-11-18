# Day 10 — Test report (Stage 4, DONE 2026-11-14)

**Project:** Retail Sales Intelligence Dashboard. Tester re-verified the coder's
finished tree in the coder's venv (`.venv`, Python 3.12.3). Nothing was
installed; no code was edited to make a test pass. **No defects found.**

## Gates run

| Gate | Result |
|---|---|
| `py_compile` on `src/*.py`, `tests/*.py` | OK |
| pytest from repo root (`day-10-.../tests/`) | **31/31 passed** (22.57 s) |
| pytest from day folder (`tests/`) | **31/31 passed** (15.70 s) |
| black `--check src tests` | clean (7 files unchanged) |
| ruff `check src tests` | clean |
| Pipeline `--offline` (raw XLSX absent) | Runs clean; `cluster_summary.csv` re-derived from `rfm_clusters.csv`; `data_source.json` untouched — `source: "live"`, `synthetic: false`, fetch `2026-11-14T14:19:41Z`, total revenue £10,283,243.98 preserved |
| Notebook offline execution | `jupyter nbconvert --execute` on `notebooks/analysis.ipynb` with the raw file absent: **16 cells, 0 error cells** (guarded forecast section worked as designed) |
| Streamlit smoke | Fresh port **8503**: HTTP 200 on `/`, HTTP 200 on `/_stcore/health`; server killed, port verified free |
| Tester screenshot | `/tmp/tester-dashboard.png`, 1200×6321, palette-quantised 461,265 bytes — **SHA-256 identical to the coder's `screenshots/dashboard.png`** (`87874b79…64fc5`); the app renders deterministically. All sections render; KPIs ("£10.28m", "5,577,139", "19,776", "£519.99", "4,334", "65.27%") not truncated |
| Chart legibility | All 4 standalone PNGs viewed at full size: titles, axis labels with units (GBP), value labels and source footnotes legible; no truncated axes; Dec 2011 bar hatched in chart 01; UK-share callout inside chart 02; log-scale cluster profile in chart 03; forecast intervals + backtest bars in chart 04 |
| `.gitignore` vs plan §3.4/§5 | Matches: `data/raw/online_retail.zip`, `data/raw/Online Retail.xlsx`, `data/raw/*_synthetic.csv` excluded (the documented size exception); nothing else in `data/` excluded |
| File sizes | No committed file > 1 MB; `data/` 500 KB; notebook 904,309 bytes; dashboard.png 461,265 bytes |
| Credential scan | `grep` over all `.py/.md/.txt/.json/.toml/.yml` text files for `api_key`/`password` assignments, `sk-live/test`, `AKIA…`: **clean — no hits** |

## Manual validation (tester, independent of the coder's check)

The coder hand-validated total revenue (£10,283,243.98). The tester validated
different numbers, recomputed by hand from the committed CSVs:

| Metric | Hand recomputation | Published | Match |
|---|---|---|---|
| Forecast total (8 weeks) | 346,552.30 + 356,860.62 + 367,168.95 + 377,477.27 + 387,785.60 + 398,093.92 + 408,402.25 + 418,710.57 = **£3,061,051.48** | £3,061,051.48 | exact (diff £0.00) |
| Holt-Winters mean backtest RMSE | (38,624.28 + 72,384.76) / 2 = **£55,504.52** | £55,504.52 | exact |
| Naïve mean backtest RMSE | (51,795.73 + 73,805.83) / 2 = **£62,800.78** | £62,800.78 | exact |
| UK revenue share | 8,759,372.58 / 10,283,243.98 = **85.18%** | 85.18% | exact |
| Lapsed share of customers | 1,066 / 4,334 = **24.60%** | 24.60% | exact |
| Cluster customer sum | 13 + 209 + 3,046 + 1,066 = **4,334**; revenue shares sum **100.00%** | 4,334 | exact |

## Orchestrator validate false positive — confirmed

Re-ran the check logic by hand: the only hit is
`notebooks/analysis.ipynb:328`, the string `aKiA…` (base64 fragment, middle redacted), which the
validator's case-insensitive `AKIA[0-9A-Z]{16}` pattern matches. It sits
inside the base64-encoded chart PNG embedded in the notebook's chart-01
display output — random base64 image data, not a credential. No key, token,
password or secret exists in the tree. The coder's decision to document it
rather than perturb a verified chart is endorsed. (Shared-tooling note: the
validator should skip `image/png` base64 blobs in `.ipynb` outputs.)

## Defects

None. The tree passes every gate. The optimizer's job is limited to the
release polish in its own handoff checklist (re-verify published numbers,
update the day README if it adds tests, confirm the screenshot file exists).

## Optimizer's first step

Re-verify the three recommendation numbers against the committed CSVs
(£4,200,055.35 / 47.94%; £3,594,965.43 / £1,457,745.53 / ~£73,000;
£50,732 / £141,877), then do the frozen-tree check on the file list in
`coder_handoff.md` — no code changes are needed unless you find a concrete gap.
