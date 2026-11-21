# Day 14 — Voter Turnout Analytics: Research Brief

**Status:** VERIFIED — one lean probe pass completed 2026-11-21 (researcher, stage 1).
**Business question:** How does voter turnout differ across US states and over time, and
which demographic indicators move with it — described only, with every number traceable
to its source and no claim about what caused any difference?

**Scope decisions (Victor, voice call 2026-11-20 — non-negotiable):** descriptive ONLY.
No predictive model is added. Deliverable is a turnout map plus an evidence-limited
insights memo. No causal claims. Outliers are screened during skewness screening and
**reported as found, never dropped silently**.

## 1. Data source — verified from scratch

**Source:** University of Florida Election Lab, Michael McDonald — general-election
turnout rates. The primary path is two small direct CSV downloads (no key, no
rate limit, no login). No API key exists in this workspace and none is needed.

### 1a. UF Election Lab turnout files (PRIMARY — verified 2026-11-21, HEAD + ranged GET)

| File | URL | Probe result | Size |
|---|---|---|---|
| `Turnout_1980_2022_v1.2.csv` | `https://election.lab.ufl.edu/data-downloads/turnoutdata/Turnout_1980_2022_v1.2.csv` | HEAD 200; ranged GET 206, header + 2022/2020/2018 rows read | **116,830 bytes** |
| `Turnout_2024G_v0.4.csv` | `https://election.lab.ufl.edu/data-downloads/turnoutdata/Turnout_2024G_v0.4.csv` | HEAD 200; ranged GET 206, header + 2024 rows read | **8,378 bytes** |

Total of the two files: **~125 KB** — inside the 1 MB/file and 5 MB/day rules, so both
are committed as the raw provenance record. Each file is one row per state per election
(50 states + DC + a "United States" total row). The 1980–2022 file covers general
elections 1980–2022 in two-year steps; the 2024 file adds the 2024 general election.
The two files must be concatenated by the coder with `YEAR=2024` added to the 2024
file (it has no YEAR column — see §1c).

Verified columns (1980–2022 file): `YEAR, STATE, STATE_ABV, TOTAL_BALLOTS_COUNTED,
VOTE_FOR_HIGHEST_OFFICE, VAP, NONCITIZEN_PCT, INELIGIBLE_PRISON, INELIGIBLE_PROBATION,
INELIGIBLE_PAROLE, INELIGIBLE_FELONS_TOTAL, ELIGIBLE_OVERSEAS, VEP, VEP_TURNOUT_RATE,
VAP_TURNOUT_RATE`. Verified columns (2024 file): same list **minus** `YEAR` and
`VOTE_FOR_HIGHEST_OFFICE`, and with the 5th column header **blank** (see §1c quirk —
that column holds source URLs in both files).

Verified values (ranged GET, not assumed): 2024 United States — total ballots counted
**156,766,239**; VAP **264,798,961**; VEP **243,803,423**; VEP turnout **64.30%**;
VAP turnout **59.20%**. 2022 United States — ballots **112,030,874**; VEP
**242,907,672**; VEP turnout **46.12%**. Sampled 2024 state VEP turnout rates (first
rows read only — **not** a ranking): Colorado **73.40%**, Connecticut 67.00%, Alaska
63.55%, California 62.26%, Alabama 58.70%, Arkansas 54.06%. The coder computes the
full ranking; no maximum/minimum is claimed here because only the head of the file
was read.

Documentation files (verified HEAD 200, ranged GET read): `Turnout_1980_2022_v1.2_doc.txt`
(9,877 bytes, v1.2, dated 10/8/2024) and `Turnout_2024G_v0.4_doc.txt` (v0.4, dated
3/2/2026). Both state the licence and the VAP/VEP construction; the coder must read
both in full at build time. Note the 2024 file is version **0.4** — a preliminary
version number; the memo must say the 2024 figures are the lab's v0.4 release.

### 1b. EAVS 2024 (CROSS-CHECK ONLY — verified 2026-11-21, HEAD)

Base: U.S. Election Assistance Commission, Election Administration and Voting Survey.

| File | URL | Probe result | Size |
|---|---|---|---|
| `2024_EAVS_for_Public_Release_nolabel_V1_csv.zip` | `https://www.eac.gov/sites/default/files/2025-06/2024_EAVS_for_Public_Release_nolabel_V1_csv.zip` | HEAD 200 | **2,076,499 bytes** |

Use: cross-check 2024 ballots counted and registered-voter counts for a sample of
states only. The zip is **over the 1 MB/file rule, so it is NOT committed** — download
at build time, use, and gitignore it. A V2 release dated 2026-02-12 is reported by a
third-party reproducibility guide; the coder must check the EAC's own index page
(`https://www.eac.gov/research-and-data/datasets-codebooks-and-surveys`) for the
newest official release and use V2 if it is linked there, otherwise the pinned V1 URL
above. Record which version was used in `data_source.json`. EAVS is a survey of
election administrators, not a turnout-rate source on its own: its registered-voter
denominator differs from VEP (§2) and the two rates must never be averaged or mixed.

### 1c. Schema quirks the coder must handle (found in probes, not guessed)

1. **Column 5 is not what its header says.** In the 1980–2022 file the header reads
   `VOTE_FOR_HIGHEST_OFFICE`, but for 2020 and 2022 rows that column holds a **source
   URL** (e.g. a state election-results link) or is blank; for 2018 and earlier rows it
   holds the actual vote-for-highest-office count. In the 2024 file the same column
   has a **blank header** and holds source URLs (the 2024 doc names it `SOURCE`).
   The doc confirms the SOURCE field "leaked" into the time-series file for recent
   years. **Rule: parse column 5 by content — URL → store as `SOURCE_URL`, digits →
   `VOTE_FOR_HIGHEST_OFFICE`, blank → missing. Never trust the header, never parse a
   URL as a vote count, never treat a missing vote count as zero.**
2. **2024 file has no YEAR column and no VOTE_FOR_HIGHEST_OFFICE column.** Add
   `YEAR=2024` when concatenating; `VOTE_FOR_HIGHEST_OFFICE` is missing for 2024
   (and for 2020/2022 rows per quirk 1) — analyses that need it must exclude those
   rows and say so, not fill them.
3. **Pre-2010 ballots counted are incomplete.** Per the doc, before 2010 fewer states
   reported total ballots counted; those states are null (not estimated), while the
   national total is estimated by applying the reporting-states ratio of
   `VOTE_FOR_HIGHEST_OFFICE / TOTAL_BALLOTS_COUNTED` to the national vote sum.
   **Rule: state-level pre-2010 gaps stay null; national pre-2010 VEP turnout is
   labelled "estimated" in every chart, table and memo sentence that uses it.**
4. **Rounded estimates exist in the file.** Example verified in probe: 2020 Wisconsin
   `TOTAL_BALLOTS_COUNTED` = 3,310,000 (round number). Treat trailing-zero round
   figures as the lab's estimates, not exact counts; do not "correct" them.
5. **2024 VAP construction (per the 2024 doc):** Census Bureau Vintage 2023
   July 1, 2022 and July 1, 2023 VAP estimates, extrapolated to Nov. 1, 2024;
   `NONCITIZEN_PCT` from the 2024 1-Year American Community Survey. Record this in
   `data/README.md` as the denominator provenance.

### 1d. What was NOT available — recorded, not silently dropped

- **County-level turnout: OUT OF SCOPE.** No verified no-key source gives a
  county-level denominator. The MIT Election Data + Science Lab county presidential
  returns file (Harvard Dataverse, doi:10.7910/DVN/VOQCHQ, "County Presidential
  Election Returns 2000-2024", v20.0, released 2026-02-25, CC0) gives county
  **votes cast** (file `countypres_2000-2024.tab`, 9,845,506 bytes; original CSV
  10,222,208 bytes; MD5 `bd6661282936006b4ef4f5ee71418f3e`) but **no denominator**:
  VEP exists only at state level, and county VAP is not obtainable without a Census
  API key (see below). A county "turnout rate" built on total county population would
  be a different, misleading metric. **Therefore the map is a STATE choropleth, not
  a county map.** The MIT file is recorded here as a considered-and-rejected
  secondary source; the coder must not add it without a plan change.
- **MIT download is guestbook-blocked for anonymous API use (verified).** Direct
  download returns HTTP **400**: "You may not download this file without the required
  Guestbook response for guestbookID 458." Guestbook 458 (`GET /api/guestbooks/458`,
  HTTP 200) requires name, email, institution and position. A POST probe with an
  empty guestbook response did not complete (curl exit 000 — connection failure, no
  response). No personal details were submitted. The file is also 10.2 MB, over the
  data-commit rule in any case.
- **Census API / ACS demographics: unavailable without a key (verified again).**
  `GET https://api.census.gov/data/2023/acs/acs5?get=NAME,B01003_001E&for=state:*`
  returns HTTP 302 redirecting to `https://api.census.gov/data/missing_key.html`
  ("Missing Key"), same finding as Day 13. No Census key exists in this workspace.
  **ACS demographic indicators via the API are out of scope.** The demographic
  indicators in this build are the ones inside the UF files themselves
  (`NONCITIZEN_PCT`, felony-ineligibility components, overseas eligible) plus the
  Census CPS supplement as context only (next bullet).
- **Census CPS Voting and Registration Supplement: context only, wrong year if
  assumed.** Table set `p20-585` is the **November 2020** election supplement
  (page title verified), not 2024; its Table 01 `.xlsx` is 11,626,066 bytes
  (HEAD 200) — over the file rule and the wrong cycle. Do not cite p20-585 as 2024.
  The 2024 supplement's table number was not verified in this pass; if the planner
  wants CPS demographic context (turnout by age/race/education), the coder must
  verify the 2024 table set from census.gov first and use national-level rates only.
- **2026 cycle:** no general election has occurred; analysis covers 1980–2024 only.
  Do not mix in 2026 rows.
- **No rate limits were observed** on any verified download (direct file GETs, no
  API). No rate-limit headers were returned. Build rule: one GET per file, reuse the
  committed copy afterwards; do not re-download in later roles.

### 1e. Geography files for the map (verified 2026-11-21, HEAD)

State choropleth geometry comes from the Census Bureau cartographic boundary files
(no key, direct download):

| File | URL | Probe result | Size |
|---|---|---|---|
| `cb_2024_us_state_500k.zip` | `https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_500k.zip` | HEAD 200 | **3,242,450 bytes** |

Over the 1 MB/file rule: **download at build time, gitignore, do not commit**.
Join on state FIPS / postal abbreviation. County boundaries
(`cb_2024_us_county_500k.zip`, HEAD 200, 11,626,066 bytes) are **not used** — see §1d.

## 2. Metric definitions — exact

All turnout figures are **percentages of a stated denominator, for a stated election**.
Never report a turnout rate without naming its denominator in the same sentence,
table header or chart title. Never compare a presidential-year rate with a
midterm-year rate as a single "trend" without labelling the cycle type.

- **VEP turnout (PRIMARY metric)** = `TOTAL_BALLOTS_COUNTED ÷ VEP × 100`.
  The file's `VEP_TURNOUT_RATE` column is the lab's own computation of this; the
  coder must recompute it from the two columns and confirm agreement (see §5
  cross-check). VEP = voting-eligible population.
- **VEP (denominator)** = `VAP − noncitizen VAP − ineligible felons (prison +
  probation + parole) + eligible overseas citizens`. The file carries each component
  (`VAP`, `NONCITIZEN_PCT`, `INELIGIBLE_PRISON`, `INELIGIBLE_PROBATION`,
  `INELIGIBLE_PAROLE`, `INELIGIBLE_FELONS_TOTAL`, `ELIGIBLE_OVERSEAS`, `VEP`), so the
  coder can verify the arithmetic per row and flag rows where it does not reconcile.
  VEP is the preferred denominator: it counts only people legally eligible to vote.
- **VAP turnout (secondary metric)** = `TOTAL_BALLOTS_COUNTED ÷ VAP × 100`, where
  VAP = voting-age population (resident population age 18+). VAP turnout is always
  lower than VEP turnout because VAP includes noncitizens and ineligible felons.
  Report it alongside VEP turnout, never as a substitute, and never average the two.
- **Registered-voter turnout (EAVS cross-check only)** = ballots cast ÷ registered
  voters (EAVS). A third denominator, lower than VEP (registration is a subset of
  eligibility). Used only to cross-check the 2024 numerator for sampled states;
  never plotted on the same axis as VEP turnout without a separate labelled series.
- **Numerator** = `TOTAL_BALLOTS_COUNTED` (all ballots counted, not votes for a
  candidate). It exceeds `VOTE_FOR_HIGHEST_OFFICE` wherever both exist, because some
  ballots record no vote for the highest office. The primary metric uses ballots
  counted; a vote-for-highest-office rate is a different metric and must be labelled
  as such if ever shown.
- **Change over time** = percentage-point (pp) change in VEP turnout. Compare like
  with like only: presidential year vs previous presidential year (4-year gap),
  midterm vs previous midterm. A presidential-to-midterm change must be labelled
  "cycle-type change", not a trend.
- **Cycle type** = `presidential` if `YEAR % 4 == 0`, else `midterm`. Every
  time-series chart and table splits or colours by cycle type.
- **Demographic indicators (descriptive only):** `NONCITIZEN_PCT` (noncitizen share
  of VAP), ineligible-felon share of VAP (`INELIGIBLE_FELONS_TOTAL ÷ VAP`), overseas
  eligible share (`ELIGIBLE_OVERSEAS ÷ VEP`). These are shown as state-level
  context next to turnout (scatter / ranked table), with the memo stating the
  association only — see nonpartisan rules.
- **Outlier screening (Victor's instruction):** during skewness screening, flag
  states with VEP turnout outside the interquartile-range fence (1.5×IQR) or with
  |z| > 3 within their cycle type, and list every flagged state in the memo with its
  value. **Flagged rows stay in every chart and table.** Nothing is dropped, winsorised
  or imputed without a written note in the memo naming the rows and the reason.
  Missing values (pre-2010 state ballots) stay missing; they are never filled.

### Nonpartisan interpretation rules (binding on every surface)

1. The data contains **no party variable** — states are compared on turnout only,
   with the same metrics, same charts, same table columns. No party is the reference
   group; do not add vote-share or party breakdowns (that would need the MIT county
   file, rejected in §1d).
2. No causal claims: never "X caused higher turnout" or "policy Y drove the change".
   Allowed language: "higher/lower than", "moved with", "associated with", "changed by
   N pp since [year]". Any association with a demographic indicator is reported as
   an association, with the denominator and the cycle type stated.
3. No editorial adjectives about rates ("abysmal", "impressive", "surge" as praise) —
   report the number, the rank, and the pp change.
4. Every chart and table states its coverage (general elections 1980–2024, 50 states
   + DC + US total; pre-2010 national figures estimated — §1c.3) and its source
   (UF Election Lab file + version, EAVS version if used).
5. "Top/bottom" always means top/bottom by the stated metric, with the metric and
   year named in the title.

## 3. Licence / attribution

- UF Election Lab turnout data is released under **Creative Commons Attribution 4.0
  (CC BY 4.0)** (stated in both documentation files). Attribution to include in
  README + data/README.md: "Source: Michael McDonald, University of Florida
  Election Lab, General Election Turnout Rates 1980–2022 v1.2 and 2024 General
  Election Turnout Rates v0.4 (https://election.lab.ufl.edu/voter-turnout/),
  CC BY 4.0. Retrieved 2026-11-21."
- EAVS data is a work of the U.S. federal government (public domain). If used:
  "Source: U.S. Election Assistance Commission, 2024 Election Administration and
  Voting Survey (https://www.eac.gov/research-and-data/studies-and-reports)."
- Census cartographic boundary files are U.S. federal government works (public
  domain); attribute the Census Bureau in data/README.md.
- No personal data is handled: all figures are state-level aggregates.

## 4. Synthetic-fallback note (only if both UF files fail)

- Labelled synthetic, seed 42, `synthetic: true` in `data_source.json` (per AGENTS.md
  data rule); never overwrite a real download.
- Generate 51 jurisdictions × 23 elections (1980–2024 biennial) mimicking the real
  schema and marginals: VEP turnout ~46% in midterms / ~60–66% in presidential
  years (national 2022: 46.12%; 2024: 64.30%); state spread roughly ±10 pp around
  the national figure for the cycle type; VAP > VEP always; noncitizen share 2–15%;
  ineligible felons ≥ 0; overseas eligible ≥ 0 where present. Then run the identical
  pipeline so the fallback exercises the same code path.
- Fallback is a last resort: the live sources verified healthy in this pass (both UF
  HEADs HTTP 200, ranged GETs returned real rows; EAVS zip HEAD 200), so the coder
  should expect the real download to work.

## 5. Verification status

- [x] Primary endpoints confirmed against the official source (HEAD 200 + byte sizes
      for both UF CSVs; ranged GET 206 returned real header + rows for 2024, 2022,
      2020, 2018)
- [x] Exact 2024/2022 national figures recorded from probe rows (2024: 156,766,239
      ballots, VEP 243,803,423, 64.30%; 2022: 112,030,874 ballots, VEP 242,907,672,
      46.12%)
- [x] EAVS 2024 V1 zip confirmed (HEAD 200, 2,076,499 bytes); V2 existence noted
      from a third-party guide only — coder to confirm on the EAC index page
- [x] MIT county file investigated and rejected with reasons (guestbook 400, no
      county denominator, 10.2 MB over the data rule)
- [x] Census API key requirement re-confirmed (302 → missing_key.html) — ACS via API
      out of scope, recorded in §1d
- [x] CPS supplement p20-585 identified as November **2020**, not 2024 — recorded
      in §1d so nobody cites it as 2024
- [x] State shapefile confirmed (HEAD 200, 3,242,450 bytes, gitignored at build)
- [x] Schema quirks recorded (§1c): column-5 URL/vote ambiguity, missing YEAR in
      2024 file, pre-2010 nulls + estimated national totals, rounded estimates
- [x] Metric definitions + nonpartisan rules recorded exactly (§2), including VEP
      vs VAP vs registered voters and the outlier-reporting rule
- [x] Licence / attribution recorded (§3)
- [x] No probe copy retained — HEAD + ranged GETs only (≤ 3,000 bytes per probe);
      nothing written to data/raw/ or data/processed/
- [ ] Unverified — for the coder to measure, not assumed here: exact row counts of
      both UF files after concatenation; per-row VEP arithmetic reconciliation;
      full state ranking of 2024 VEP turnout (only the file head was sampled);
      EAVS V1 vs V2 version decision; pre-2010 missing-state counts per year

## Cross-check the coder must run (before the tester starts)

After building the state table from the two UF files, recompute VEP turnout from
`TOTAL_BALLOTS_COUNTED ÷ VEP × 100` for every row and confirm it matches the file's
`VEP_TURNOUT_RATE` within 0.05 pp (rounding tolerance). Spot-checks that must pass:
2024 United States **64.30%** (156,766,239 ÷ 243,803,423); 2022 United States
**46.12%**; 2024 Colorado **73.40%**; 2024 California **62.26%**; 2024 Arkansas
**54.06%**. Then cross-check the 2024 numerator for two sampled states against the
EAVS 2024 file (ballots counted) and record any disagreement over 0.5% in the
insights memo. If any recomputed rate differs by more than 0.05 pp, stop and report
it as a defect — do not silently overwrite the file's rate with the recomputed one.

---

## Handoff — researcher → planner

1. **What was produced:** this brief —
   `day-14-voter-turnout-analytics/research_brief.md`.
2. **Verified numbers:** UF Election Lab primary files — 1980–2022 v1.2 CSV,
   116,830 bytes, HEAD 200; 2024 v0.4 CSV, 8,378 bytes, HEAD 200; combined ~125 KB,
   committable. 2024 national VEP turnout **64.30%** (156,766,239 ballots ÷
   243,803,423 VEP); 2022 national **46.12%**. EAVS 2024 V1 zip HEAD 200,
   2,076,499 bytes (cross-check only, gitignored). State shapefile HEAD 200,
   3,242,450 bytes (gitignored). Census API key-blocked (302 → missing_key.html).
   MIT county file guestbook-blocked (HTTP 400, guestbook 458) and 10.2 MB.
3. **Known gaps:** county-level turnout is not computable from any verified no-key
   source — the map is a **state** choropleth by design; full state ranking, exact
   row counts, VEP reconciliation and the EAVS V1/V2 decision are for the coder to
   measure; the 2024 file is a preliminary v0.4 release; pre-2010 national totals
   are estimates and some state ballots are null.
4. **Planner's first step:** read §1c (schema quirks — column 5, missing YEAR in
   2024) and §2 (VEP/VAP/registered definitions, cycle-type rule, outlier
   reporting) and fix the file tree around a state-level, 1980–2024 descriptive
   build: concatenated UF table + state choropleth + evidence-limited memo, no
   model, no county layer.
