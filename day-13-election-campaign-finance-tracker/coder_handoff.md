# Coder handoff — Day 13 Election Campaign Finance Tracker

## What was produced

- `src/data_pipeline.py` — full pipeline: bulk download (4 zips, no key),
  openFEC API fetch (54 pages, per-page cache, 7 s spacing, 60 s retry on
  429 max 3 attempts), headerless load with FEC-verified column names,
  cleaning per plan §3.2, candidate table with the `webl` override
  (plan §11 item 17), committee table (principals excluded), derived
  tables, `data_source.json`. Modes: `--live` / `--use-cache` /
  `--offline` / `--synthetic`.
- `src/finance.py` — pure functions (small-dollar share, burn rate,
  other receipts, party share, top-N share, principal committees,
  cash-identity check, party×office / state summaries, top-N).
- `src/make_charts.py` — 4 charts, all 1500×825, each < 1 MB.
- `src/app.py` — Streamlit dashboard (processed CSVs only, offline).
- `tests/test_pipeline.py` — 32 tests.
- `notebooks/analysis.ipynb` — 16 cells, offline, SQL check (§4.6),
  guarded join re-run.
- `README.md`, `data/README.md`, `outputs/insights_summary.md` — all
  numbers verified against the committed CSVs.
- `data/raw/*.zip` (4 files, 1,042,121 bytes total, committed) +
  `data/processed/*.csv` + `data_source.json` (committed).
  Unpacked `.txt` files and `data/raw/api_pages/` are git-ignored.

## Verified numbers (pipeline run 2026-11-19, `--use-cache`, exit 0)

- Candidates: 5,332 rows; 4,376 with totals; 956 filed, no totals.
  Candidate receipts **$6,503,148,091.92**; disbursements
  $6,728,272,984.00; cash $1,373,471,403.75 (ex-Norris $597,691,424.75).
- Top 2: Harris P00009423 and Biden P80000722, **$1,175,189,365.41**
  each (18.07%); top 10 share 45.7%. Hand-validated to the cent
  against the single-candidate endpoint and `webl` (see data/README.md).
- Funding mix (2,259 split-covered, $6,286.0M receipts): individual
  $3,734.5M; itemized $2,508.4M; unitemized $1,226.1M; small-dollar
  share 32.8%. Split invalid 37; no split 2,117.
- Committees: 10,102 non-principal; receipts $22,724,587,172.77;
  disbursements $22,249,713,539.36; cash $1,755,366,050.13.
  ActBlue $3,821.2M (16.8%); WinRed $1,686.5M (7.4%).
- States: 56 rows; PA $2,525.2M (38.8%), CA $460.6M, TX $312.7M.
  64 presidential candidates (00/US) excluded.
- Cash identity hold: webk 91.8%, webl 83.8%. Cross-check (list vs
  webl) max receipt diff $12,107,733.17; post-override $0.
- API: 5,321 rows, 4,294 unique; 1,027 duplicates; 82 webl-only;
  1,998 api-list-only (max receipts $15,192.65).
- Principals: 3,714 distinct (3,643 from cn + 72 filled from ccl);
  12 in webk; 79 API candidates without a 2024 master record.

## Gates (all run in the day venv, 2026-11-19)

- `black --check src tests`: clean. `ruff check src tests`: clean.
- `mypy src tests` (from inside the day folder): clean, 6 files.
- `pytest tests/ --cov=src --cov-fail-under=30`: **32 passed,
  coverage 51.82%**.
- `python -m src.make_charts`: 4 PNGs, each < 1 MB.
- Notebook: nbconvert exit 0, 16 cells, 0 error cells.
- Streamlit smoke (coder run): port 8502, HTTP 200 on `/` and
  `/_stcore/health` (`ok`), real screenshot
  `screenshots/dashboard.png` (1440×7149, 968,319 bytes); server killed
  and port verified free. Chart 02's labels were fixed after the first
  capture (they were cut off at the right edge) and the screenshot
  re-taken.

## Known gaps / defects

- None known in code or data. Two filed-data anomalies are disclosed,
  not fixed: Norris P40010415 ($775.8M cash, fails cash identity) and
  Gambert P40010522 ($220.5M disbursements on $0 receipts); one
  candidate reports −$0.76 receipts (P40004681).
- `src/app.py` is 0% covered by pytest by design (exercised by the
  smoke test, not pytest) — same as other days.

## Next role's first step (Tester)

1. Run the notebook via nbconvert from inside the day folder and
   confirm exit 0 with 0 error cells (it needs the 4 chart PNGs, which
   exist, and the committed CSVs).
2. Run the Streamlit smoke gate on a fresh port (8502+): HTTP 200 on
   `/` and `/_stcore/health`, real screenshot to
   `screenshots/dashboard.png`, server killed, port verified free.
3. Re-run `pytest --cov=src` in the coder's venv and record the
   coverage number; manually validate one metric against the committed
   CSVs; check chart legibility and README number accuracy.
