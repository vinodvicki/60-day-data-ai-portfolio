# Data provenance — Day 13 Election Campaign Finance Tracker

## Source

- **Provider:** U.S. Federal Election Commission (FEC).
  Public domain data.
- **Bulk downloads** (no key required),
  `https://www.fec.gov/files/bulk-downloads/2024/`:
  - `cn24.zip` — candidate master file (`cn`), 9,796 rows.
  - `webk24.zip` — committee summary file (`webk`), 12,379 rows.
  - `ccl24.zip` — candidate–committee linkage file (`ccl`), 8,619 rows.
  - `webl24.zip` — candidate summary file (`webl`), 2,378 rows.
- **openFEC API** (`https://api.open.fec.gov/v1/candidates/totals/`,
  free `DEMO_KEY`, 10 requests/hour at the demo tier — the build makes
  54 paged calls and caches every page in `data/raw/api_pages/` so a
  rebuild with `--use-cache` makes no API calls at all).
- **Window:** the 2024 two-year cycle (2023-01-01 → 2024-12-31).
  No 2026 rows.
- **Retrieved:** 2026-11-19. The Census API was not used — it needs a
  key that is not available, so no per-capita figures exist in this build.
- **Attribution:** "Source: U.S. Federal Election Commission, 2024 cycle
  bulk data and openFEC API. Public domain."

## Fetch outcome

All four bulk zips downloaded (HTTP 200, one retry available) and all 54
API pages fetched (5,321 rows). No source failed; no synthetic fallback
was used (`synthetic: false` in `data_source.json`).

## Row counts and coverage

| File | Raw rows | After cleaning | Notes |
|---|---|---|---|
| `cn24` (candidate master) | 9,796 | 5,212 | 4,584 non-2024 election years removed; 0 duplicate candidate IDs; 1,434 rows have no principal committee |
| `webk24` (committee summaries) | 12,379 | 10,114 | 2,253 committees with no financial summary filed; 8 coverage-end dates outside the window; 4 negative-receipts rows removed; 0 duplicate committee IDs |
| `ccl24` (linkage) | 8,619 | 8,619 | 35 duplicate candidate–committee pairs (audit only) |
| `webl24` (candidate summaries) | 2,378 | 2,378 | Used as the authoritative money source for candidates present in it |

Candidate table: **5,332 rows** = 4,294 unique API-totals candidates
(after dedup of 5,321 list rows — 755 candidates appear 2–3 times as
exact duplicates) + 82 candidates present in `webl` but absent from the
API list + 956 candidates who filed but have no totals on record.
**4,376 have totals; 956 do not.** 79 API candidates have no 2024
master record (2023-election-year rows, e.g. special elections); their
name/state come from the API totals and their principal committee from
the linkage file (72 filled). 120 candidates have no master match at all.

Committee table: **10,102 rows** — the 10,114 cleaned `webk` rows minus
the 12 principal committees present in the file (their money is already
inside the candidate totals).

### Cleaning audit (rules applied in order, plan §3.2)

1. Drop rows whose coverage-end date is unparseable or outside
   2023-01-01 → 2024-12-31 (committees: 2,253 no financial summary +
   8 outside window).
2. Drop negative-receipts committee rows (4).
3. Drop duplicate committee IDs, keeping the first (0).
4. Drop non-2024 election-year candidate rows (4,584).
5. Drop duplicate candidate IDs, keeping the first (0 in `cn`; 1,027
   in the API list).

### Layout verification (the bulk files are headerless)

Column names were assigned from the FEC file descriptions and verified:
the cash identity (COH_BOP + receipts − disbursements = COH_COP)
holds for **91.8% of committee summaries** (9,300/10,126 numeric rows,
median absolute difference $0) and **83.8% of candidate summaries**
(1,993/2,378), and bulk rows match the live single-candidate API
endpoint **to the cent** for five candidates (Peltola, Begich, Biden,
Sanders, Cruz). The remaining failures are amended filings and
non-federal accounts — a data feature, recorded here, not a layout
error. Hold rate below 80% would have failed the build.

### The API list endpoint overstates multi-committee candidates

The `/candidates/totals/` list endpoint returns 5,321 rows for 4,294
unique candidates and, for 95 of them (mostly Senate/presidential with
joint fundraising), reports receipts, disbursements and itemized
contributions **above** the filed candidate summary (max $64.7M;
Sanders $36.3M vs $8.2M filed). The pipeline therefore takes
receipts, disbursements and individual contributions from `webl`
where the candidate is present (2,378 candidates) and the list values
only otherwise (1,998 candidates, flagged `receipts_source`), changing
$392,029,901.45 of receipts. Post-override, the max receipt difference
against `webl` is $0. The 1,998 list-only candidates are all small
(max receipts $15,192.65; $34,753.26 in total), so the residual
exposure is negligible.

### Funding-mix coverage

The itemized/unitemized split is valid for **2,259** candidates
(individual ≥ itemized). **37** candidates have list itemized figures
exceeding the filed individual total and get no split; **2,117**
candidates with totals have no split on record. Mix figures always
use the split subset's receipts ($6,286.0M) as the denominator.

### State coverage

State is the mailing-address state as filed, falling back to the office
state and then the API state. **64 presidential candidates** coded
`00` (39) or `US` (25) have no usable state and are excluded from
`state_totals.csv` ($36,446,075.56 of receipts, $344,058,951.38 of
disbursements — mostly Norris and Gambert, see below); their money
stays in the candidate totals.

### Single-filing anomalies (reported as filed, never altered)

- **Norris (P40010415):** $775,779,979 cash on hand (56.5% of all
  candidate cash) on $35,430,000 receipts and $121,230,010
  disbursements; the filing fails the cash identity and reports
  negative unitemized contributions (−$1,400,000). The FEC
  single-candidate endpoint confirms these figures. Excluding this
  filing, candidate cash on hand is $597,691,424.75.
- **Gambert (P40010522):** $220,504,869 disbursements on $0 receipts.
- One candidate (P40004681) reports −$0.76 receipts (amendment rounding).

## Commit rule for data files

- Small raw data IS committed: the four zips total 1,042,121 bytes
  (each under 1 MB) and the processed CSVs total 1,473,548 bytes —
  the committed data files total 2,515,669 bytes (2,523,409 including
  this README), under the 5 MB/day rule.
  `.gitignore` must NOT exclude `data/`.
- Unpacked `.txt` files (up to 1,509,800 bytes) and the cached API pages
  (`data/raw/api_pages/`, 54 JSONs, 6,603,611 bytes) are git-ignored and
  regenerated by the pipeline; synthetic fallback output
  (`data/raw/*_synthetic.json`) is git-ignored and never overwrites a
  live file. **After the build they were removed from disk** so the
  day folder satisfies the data-size rule as the orchestrator measures
  it (all files on disk under `data/`, not just tracked files):
  `--live` re-creates both (the zips are committed, so only the API
  pages are re-fetched — 54 calls at 7 s spacing). `--offline` needs
  neither. The notebook's guarded join cell prints a skip note when the
  `.txt` files are absent and still finishes with 0 errors.
- `committees.csv` drops the `committee_type_full` label (the repeated
  long text pushed it to 1,039,323 bytes, over the 1 MB/file rule); the
  full type mapping is in `data_source.json`
  (`committee_type_full_mapping`) and the label is re-derived for
  `top_committees.csv`. Result: 776,486 bytes.

## Manual validation (one metric, by hand)

**Top candidate receipts: $1,175,189,365.41 for Harris (P00009423) and
Biden (P80000722).** Checked three ways on 2026-11-19:

1. `data/processed/top_candidates.csv` rows 1–2: both
   $1,175,189,365.41.
2. openFEC single-candidate endpoint
   (`/candidate/P80000722/totals/?cycle=2024`): receipts
   $1,175,189,365.41 — exact match.
3. `webl24` bulk file row for P80000722 (field 6): 1175189365.41 —
   exact match. (The *list* endpoint reports $1,187,297,098.58 for the
   same candidate — the $12,107,733.17 overstatement the pipeline
   corrects; see above.)

## Versions used for this build

Python 3.12.3; pandas 3.1.1; numpy 2.5.4; matplotlib 3.11.2;
streamlit 1.66.1; requests 2.34.2; pytest 9.2.0; mypy 2.4.1;
ruff 0.17.4; black 26.10.1 (all pinned in `requirements.txt` /
`../requirements-dev.txt`).
