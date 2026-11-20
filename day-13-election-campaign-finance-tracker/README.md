# Day 13 — Election Campaign Finance Tracker

Transparent, nonpartisan tracking of reported contributions and spending
in the **2024 US federal election cycle**, from the Federal Election
Commission's own filings. Candidates and committees are presented exactly
as filed — no editorialising, no claim that money caused any outcome.

## Problem

Campaign-finance data is public but hard to read: the FEC publishes it as
headerless bulk files and a paginated API, with candidate money and
committee money in separate universes that must never be added together
without noting the double-count. This project turns those filings into a
transparent contributions/spending dashboard with source links, so anyone
can see who raised what, where it came from, and how it was spent.

## Headline findings (2024 cycle, as filed)

- **Candidates raised $6,503.1M and spent $6,728.3M.** 4,376 candidates
  have published totals; 956 filed but have no totals on record (kept,
  never counted as $0).
- **Two candidates dominate.** Harris (P00009423) and Biden (P80000722)
  each report **$1,175.2M (18.07%)** — they share principal committee
  C00703975 (Harris Victory Fund), so the $6,503.1M total counts their
  shared ~$1.18B **twice**. The top 10 candidates take 45.7% of all
  candidate receipts. The median candidate raised **$814**; 2,116 of
  4,376 with totals raised $0.
- **By office:** presidential candidates raised $2,718.2M and spent
  $3,038.4M; House $2,275.5M / $2,141.5M; Senate $1,509.5M / $1,548.4M.
- **By party:** DEM $4,522.0M (69.5%), REP $1,801.5M (27.7%),
  IND $126.7M (1.9%). Every party present in the filings is shown —
  nothing is dropped, including the handful of rows whose party code is
  plainly a filing error (e.g. `"18"`, `"KY"`); they hold negligible money.
- **Where the money came from:** of the 2,259 candidates with a
  published itemized/unitemized split ($6,286.0M of receipts),
  individuals gave **$3,734.5M (59.4%)** — $2,508.4M itemized (donors
  over $200, named) and **$1,226.1M unitemized (small-dollar, ≤ $200)**,
  a 32.8% small-dollar share. Small-dollar share by office: Senate DEM
  36.1%, presidential DEM 34.6%, Senate REP 32.9%, presidential REP 32.3%,
  House DEM 30.4%, House REP 28.1%.
- **Committees (non-candidate) raised $22,724.6M and spent $22,249.7M**
  across 10,102 committees. By type: hybrid PACs (V) $7,074.5M, super
  PACs (O) $5,100.4M, nonqualified PACs (N) $3,664.6M, qualified party
  committees (Y) $3,416.6M, qualified PACs (Q) $1,855.1M. ActBlue alone
  moved **$3,821.2M (16.8%)**, WinRed $1,686.5M (7.4%), Harris Victory
  Fund $1,314.0M (5.8%).
- **States:** PA leads at **$2,525.2M (38.8%)** — not Pennsylvania
  donors, but the Biden/Harris campaign HQ in Philadelphia (state is the
  candidate's mailing-address state as filed). Then CA $460.6M (7.1%),
  TX $312.7M (4.8%), AZ $228.6M (3.5%), MD $208.5M (3.2%). State totals
  are **not** population-adjusted. 64 presidential candidates with no
  usable state on file are excluded from the state table.
- **Spending:** median burn rate (disbursements ÷ receipts) is 0.997;
  532 candidates (12.2%) spent more than they raised this cycle.
- **Read the cash total with care.** Candidates report $1,373.5M cash
  on hand — but **$775.8M (56.5%) is one filing**, Norris (P40010415),
  which reports $775.8M cash on $35.4M of receipts and fails the cash
  identity check. Excluding it, candidate cash on hand is **$597.7M**.
  Gambert (P40010522) disbursed $220.5M on $0 receipts. Both figures are
  reported as filed and never altered; the FEC itself reports them.

## Dataset

- **FEC bulk downloads, 2024 cycle** (`https://www.fec.gov/files/bulk-downloads/2024/`):
  `cn24.zip` (candidate master, 9,796 rows), `webk24.zip` (committee
  summaries, 12,379 rows), `ccl24.zip` (candidate–committee linkage,
  8,619 rows), `webl24.zip` (candidate summaries, 2,378 rows).
- **openFEC API** (`https://api.open.fec.gov/v1/candidates/totals/`,
  `DEMO_KEY`): 5,321 rows for 4,294 unique candidates (755 duplicated).
- **Census per-capita figures are out of scope** — the Census API needs
  a key that is not available, so no per-capita figures are published.
- Full provenance, row counts and the cleaning audit: `data/README.md`
  and `data/processed/data_source.json`.

## Tools

Python 3.12, pandas, matplotlib, Streamlit, requests, pytest, mypy,
ruff, black. No other runtime dependencies.

## Method

1. **Download** the four bulk zips (no key needed) and fetch the API
   candidate totals (54 pages, cached in `data/raw/api_pages/`).
2. **Load the headerless bulk files** with fixed column names taken from
   the FEC file descriptions. The layout is verified two ways: the cash
   identity (COH_BOP + receipts − disbursements = COH_COP) holds for
   91.8% of committee summaries and 83.8% of candidate summaries, and
   bulk rows match the live API **to the cent** for two candidates.
3. **Candidate money = the filed candidate summary (`webl`) where
   present (2,378 candidates), API list values otherwise (1,998,
   flagged `receipts_source`).** The list endpoint overstates
   multi-committee candidates (max $64.7M; Sanders $36.3M vs $8.2M
   filed), so it is never trusted where the filed summary exists. The
   82 candidates in `webl` but absent from the API list are added from
   the bulk file.
4. **Funding mix** (itemized vs unitemized) is computed over the
   2,259 candidates with a valid split only; unitemized = individual −
   itemized, and the 37 candidates where the list itemized exceeds the
   filed individual total get no split.
5. **Committee money** comes from `webk` only, excluding the 12
   principal committees present in the file (their money is already
   inside the candidate totals). Candidate committees are largely absent
   from `webk` (only 179 of 12,379 rows), so candidate money is never
   taken from it.
6. **States** use the mailing-address state as filed, falling back to
   the office state and then the API state. Candidates coded `00`/`US`
   (64, all presidential) are excluded from the state table.
7. **One metric hand-validated:** the top candidate total ($1,175.2M
   for Harris and Biden) was checked against the openFEC
   single-candidate endpoint and the `webl` bulk file to the cent —
   see `data/README.md`.

## Key insights

See `outputs/insights_summary.md` for the full write-up, and
`notebooks/analysis.ipynb` for the worked analysis (16 cells, offline,
including the pandas-vs-SQL check).

## Visuals

- `outputs/charts/01_receipts_by_office_party.png` — candidate receipts
  by office and party
- `outputs/charts/02_top_candidates.png` — top 10 candidates by receipts
- `outputs/charts/03_funding_mix.png` — itemized vs unitemized vs other,
  by office (split-covered candidates only)
- `outputs/charts/04_state_totals.png` — top 15 states by candidate
  receipts
- `screenshots/dashboard.png` — the running Streamlit dashboard

## How to run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.data_pipeline --live        # full rebuild (downloads + API)
python -m src.data_pipeline --use-cache   # rebuild from the cached API pages
python -m src.data_pipeline --offline     # regenerate tables from committed CSVs
python -m src.make_charts
streamlit run src/app.py
pytest tests/ --cov=src --cov-fail-under=30
```

`--live` needs network (FEC bulk downloads + openFEC API with
`DEMO_KEY`); `--offline` and `--use-cache` do not re-fetch. Synthetic
fallback data (`--synthetic`) is clearly labelled and never overwrites
live files.

## Validation

- **pytest: 32 passed** (pure-function tests, committed-table tests,
  builder tests on fixtures, chart smoke tests, offline reproduction
  with tolerance). **Coverage 51.82%** of `src/` (threshold 30).
- **mypy** (`mypy src tests`): clean. **black + ruff**: clean.
- **Streamlit smoke:** port 8502, HTTP 200 on `/` and
  `/_stcore/health` (`ok`), real full-page screenshot
  `screenshots/dashboard.png` (1440×7149, 968,319 bytes); server killed
  and port verified free. Chart 02's value labels were cut off at the
  right edge in the first capture — shortened to "$1.18B (18.1%)" and
  the axis widened, then the screenshot re-taken.
- **Notebook:** 16 cells, nbconvert exit 0, 0 error cells, including the
  SQL-vs-pandas party-totals check and the guarded join re-run.
- **Orchestrator:** `python agents/orchestrator.py --day 13 validate`
  green.

## Limitations

- **Two universes, never added.** Candidate ($6,503.1M) and committee
  ($22,724.6M) totals overlap through transfers; adding them
  double-counts. The shared Biden/Harris committee double-counts
  ~$1.18B inside the candidate total itself.
- **Cash on hand is dominated by one anomalous filing** (Norris,
  $775.8M — see above). The ex-Norris figure ($597.7M) is the robust one.
- **The funding mix covers 2,259 of 4,376 candidates with totals.**
  The other 2,117 have no published split; the mix must not be read as
  covering the whole cycle.
- **No per-capita figures** (no Census key). State rankings reflect
  where candidates file from, not where donors live — PA is the
  Biden/Harris HQ effect.
- **No outcome variable.** Nothing here says money caused any election
  result.
- **Filed data, warts included.** 385 of 2,378 candidate summaries and
  826 of 10,126 committee summaries fail the cash identity (amended
  filings); one candidate reports −$0.76 receipts. Values are reported
  as filed, never altered.
- **79 candidates** have 2024-cycle totals but a 2023-election-year
  master record; their name/state come from the API totals and their
  principal committee from the linkage file.

## License

Public domain data (U.S. Federal Election Commission). Code in this
folder is the author's own work.
