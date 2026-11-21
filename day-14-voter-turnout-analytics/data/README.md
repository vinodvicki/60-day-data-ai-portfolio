# Data provenance — Day 14: Voter Turnout Analytics

## Source (primary)

Source: Michael McDonald, University of Florida Election Lab, General Election
Turnout Rates 1980–2022 v1.2 and 2024 General Election Turnout Rates v0.4
(https://election.lab.ufl.edu/voter-turnout/), CC BY 4.0. Retrieved 2026-11-21.

| File | URL | Size (bytes) | Rows |
|---|---|---|---|
| `Turnout_1980_2022_v1.2.csv` | https://election.lab.ufl.edu/data-downloads/turnoutdata/Turnout_1980_2022_v1.2.csv | 116,830 | 1,144 (52 jurisdictions × 22 elections, 1980–2022) |
| `Turnout_2024G_v0.4.csv` | https://election.lab.ufl.edu/data-downloads/turnoutdata/Turnout_2024G_v0.4.csv | 8,378 | 52 (52 jurisdictions × 2024) |

Both files are committed under `data/raw/` (total ~125 KB, each under the 1 MB
rule) as the provenance record. No key, no login, no rate limit was observed;
one GET per file per build, then the committed copy is reused (`--offline` /
`--use-cache`).

Documentation files (read in full at build time, **not** committed — they are
documentation, not data): `Turnout_1980_2022_v1.2_doc.txt`, version **1.2**,
dated **10/8/2024** (9,877 bytes); `Turnout_2024G_v0.4_doc.txt`, version
**0.4**, dated **3/2/2026** (5,319 bytes). The 2024 file is a **preliminary
v0.4 release**; every surface that uses 2024 figures says so.

## Cross-check source (EAVS 2024 — cross-check only, never authoritative)

Source: U.S. Election Assistance Commission, 2024 Election Administration and
Voting Survey (https://www.eac.gov/research-and-data/studies-and-reports).
File `2024_EAVS_for_Public_Release_nolabel_V1_csv.zip` (2,076,499 bytes),
version **V1**. The EAC index page was checked at build time (2026-11-21); no
V2 dataset was linked there, so the pinned V1 URL was used. The zip is over
the 1 MB/file rule: downloaded at build time, git-ignored, and deleted after
the build. Variable used: **F1a (total ballots cast)**, summed by state.

Cross-check result (2024 numerator, UF ballots counted vs EAVS ballots cast):

| State | UF ballots | EAVS ballots | Difference | Within 0.5%? |
|---|---|---|---|---|
| Colorado (sampled) | 3,241,120 | 3,240,754 | −0.011% | yes |
| California (sampled) | 16,140,044 | 16,164,330 | +0.15% | yes |
| Arkansas (additional) | 1,190,172 | 1,122,179 | −5.71% | **no** |
| Texas (additional) | 11,400,000 | 11,488,820 | +0.78% | **no** |

The Arkansas gap is consistent with 2 Arkansas jurisdictions missing F1a in
the EAVS file; the Texas UF figure is a round-number estimate (11,400,000).
Per the decider rules the UF figures stand in every case; EAVS never
overrides, averages, or enters a committed turnout table. No EAVS figure
appears in any processed CSV (asserted by a test).

## Map geometry

U.S. Census Bureau cartographic boundary file `cb_2024_us_state_500k.zip`
(3,242,450 bytes, public domain), downloaded at build time, git-ignored, and
deleted after the build. Join on state FIPS / postal abbreviation (`STUSPS`).
**Join result: all 51 jurisdictions (50 states + DC) joined; 0 unmatched.**
The shapefile carries 56 features (states + DC + territories); territories
are not part of this analysis.

## Row counts

- 1980–2022 file: 1,144 rows (52 per year × 22 elections).
- 2024 file: 52 rows.
- Concatenated: 1,196 rows; duplicates dropped: 0; cleaned: **1,196 rows**
  (51 jurisdictions × 23 elections + 23 US total rows).
- `turnout_long.csv`: 1,196 rows. `national_series.csv`: 23 rows (one per
  election year). `state_2024.csv`: 52 rows (51 jurisdictions + US total).
  `correlations.csv`: 3 rows. `outliers.csv`: 5 rows.

## Cleaning (plan §3.2, in order)

1. **Download** one GET per file; byte sizes verified against the table above.
2. **Column 5 parsed by content** (never by header): URL → `SOURCE_URL`,
   digits → `VOTE_FOR_HIGHEST_OFFICE`, blank → missing. Counts — 1980–2022
   file: 51 URLs, 1,039 vote counts, 54 blank; 2024 file: 51 URLs, 0 vote
   counts, 1 blank. (The 2020 rows' URLs are never parsed as vote counts —
   asserted by a test.)
3. **Concatenate:** `YEAR=2024` added to the 2024 file. The "United States"
   row is kept and flagged `is_national = True`; DC is a state row.
   (The 1980–2022 file leaves the national row's abbreviation blank; it is
   normalised to "US".)
4. **Types:** numbers parsed from comma-grouped text; `NONCITIZEN_PCT` is a
   percent as filed; blank → missing, never 0. No rows dropped for missing
   ballots.
5. **VEP reconciliation:** VEP recomputed per row as VAP − noncitizen VAP −
   ineligible felons + eligible overseas; **0 rows flagged** over the 0.5%
   tolerance; max relative difference **0.058%**. The file's VEP is used
   throughout — the recomputation is a check, never a replacement.
6. **Cycle type:** `presidential` if `YEAR % 4 == 0`, else `midterm`.
7. **Deduplicate:** 0 exact duplicate (YEAR, STATE_ABV) rows.
8. **No imputation, no winsorising, no dropping of outliers.** Missing stays
   missing; flagged outliers stay in the table.

Null ballots counted (pre-2010 state ballots are null by design; national
VEP turnout is not reported in the file for 1980–1996):

| Year | Null ballots | Year | Null ballots | Year | Null ballots |
|---|---|---|---|---|---|
| 1980 | 18 | 1990 | 18 | 2000 | 13 |
| 1982 | 20 | 1992 | 16 | 2002 | 16 |
| 1984 | 19 | 1994 | 13 | 2004 | 4 |
| 1986 | 18 | 1996 | 13 | 2006 | 6 |
| 1988 | 19 | 1998 | 13 | 2008 | 3 |

Total null ballots: **209** (200 state-year rows + 9 national rows,
1980–1996). All years 2010–2024 are complete.

## Cross-checks (plan §3.3)

- **Recompute check:** VEP turnout recomputed as
  `TOTAL_BALLOTS_COUNTED ÷ VEP × 100` for the 987 rows carrying both figures
  matches the file's `VEP_TURNOUT_RATE` within 0.05 pp — max difference
  **0.0226 pp**, 0 rows over tolerance. Spot-checks (all pass):

  | Check | File rate | Recomputed |
  |---|---|---|
  | 2024 United States | 64.30% | 64.30% |
  | 2022 United States | 46.12% | 46.12% |
  | 2024 Colorado | 73.40% | 73.40% |
  | 2024 California | 62.26% | 62.26% |
  | 2024 Arkansas | 54.06% | 54.06% |

- **EAVS cross-check:** see the table above (sampled CO, CA within 0.5%;
  additional AR, TX disclosed as over 0.5%; UF stands).
- **Shapefile join check:** 51/51 jurisdictions joined, 0 unmatched.

## Metric definitions (plan §4.1)

- **VEP turnout (primary)** = `TOTAL_BALLOTS_COUNTED ÷ VEP × 100`.
  VEP = voting-eligible population.
- **VEP (denominator)** = `VAP − noncitizen VAP − ineligible felons
  (prison + probation + parole) + eligible overseas citizens`.
- **VAP turnout (secondary)** = `TOTAL_BALLOTS_COUNTED ÷ VAP × 100`,
  where VAP = voting-age population (resident population age 18+). Always
  lower than VEP turnout; reported alongside, never as a substitute, never
  averaged with VEP.
- **Registered-voter turnout (EAVS cross-check only)** = ballots cast ÷
  registered voters. A third denominator, used only to cross-check the 2024
  numerator for sampled states.
- **Numerator** = `TOTAL_BALLOTS_COUNTED` (all ballots counted, not votes for
  a candidate).
- **Change over time** = percentage-point (pp) change in VEP turnout, within
  the same cycle type only. A presidential-to-midterm change is a
  "cycle-type change", not a trend.
- **Cycle type** = `presidential` if `YEAR % 4 == 0`, else `midterm`.
- **Demographic indicators (descriptive only):** `NONCITIZEN_PCT`
  (noncitizen share of VAP), ineligible-felon share of VAP
  (`INELIGIBLE_FELONS_TOTAL ÷ VAP`), overseas eligible share
  (`ELIGIBLE_OVERSEAS ÷ VEP`).

## Denominator provenance (2024 VAP construction, brief §1c.5)

Per the 2024 documentation file: VAP from the Census Bureau's Vintage 2023
July 1, 2022 and July 1, 2023 VAP estimates, extrapolated to Nov. 1, 2024;
`NONCITIZEN_PCT` from the 2024 1-Year American Community Survey. Eligible
overseas voters (3,325,217 nationally) are estimated from the Federal Voting
Assistance Program November 2022 report and Department of Defense personnel
reports; the lab does **not** apportion overseas eligible voters to states,
so state-level overseas shares are not computable in this build.

## Manual validation

2024 United States VEP turnout recomputed by hand from the committed 2024
CSV: **156,766,239 ÷ 243,803,423 × 100 = 64.3003% → 64.30%**, matching the
file's rate to the last digit — **diff 0.0 pp**.

## Versions

- Python 3.12.3; pandas 3.1.1, numpy 2.5.4, matplotlib 3.11.2, plotly 7.1.0,
  streamlit 1.66.1, requests 2.34.2, pytest 9.2.0, jupyter 1.1.1,
  nbformat 5.11.1, geopandas 1.2.0, scipy 1.18.1 (see `requirements.txt`).
- Dev tools: ruff 0.17.4, black 26.10.1, mypy 2.4.1, pytest-cov 7.1.0
  (portfolio-root `requirements-dev.txt`).
- Fetch date: 2026-11-21. Pipeline: `python -m src.data_pipeline --live`
  (or `--offline` / `--use-cache` / `--synthetic`, seed 42 for the fallback).

## Data-size rule

Committed data totals ~290 KB (two raw CSVs ~125 KB + five processed CSVs);
no committed file is over 1 MB and `data/` is under 5 MB. The shapefile zip
(3,242,450 bytes), the EAVS zip (2,076,499 bytes), and their unpacked contents
are git-ignored and absent at handoff; they are re-downloaded by `--live`.
