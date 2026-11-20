# Day 13 — Election Campaign Finance Tracker: Build Plan

**Status:** PLAN — planner sign-off complete (AGENTS.md, stage 2).
**Source of truth:** `research_brief.md` (2026-11-19) + this plan. **If brief
and plan disagree, the plan wins and the difference is noted in §11.** The
coder must reuse the brief + this plan. **No extra web searches.**
**Roadmap entry (verbatim):** "Election Campaign Finance Tracker.
Problem / analysis: Analyze reported contributions, donors, and spending
patterns across candidates or periods. GitHub deliverable: Transparent
contributions/spending dashboard with source links. Core skills:
Statistics, mapping, NLP, careful nonpartisan interpretation. Suggested
data: FEC campaign finance datasets; official election data; Census.
Sector: Politics, Elections & Public Policy (Phase 1, Days 01–15)."

> **PLAN AMENDMENT (coder stage, 2026-11-19 — see §11, items 8–12).**
> The bulk files are **headerless** (the plan's "header row" claim was
> wrong) and both `webk24` and `webl24` use the FEC **legacy layouts**,
> which carry **no itemized/unitemized split**. Verified by matching bulk
> rows to the openFEC API to the cent for two candidates (Peltola
> H2AK01158, Begich H2AK01083) plus the cash identity
> COH_BOP + receipts − disbursements = COH_COP. Consequences: (a) a 4th
> raw file, `webl24.zip` (121,855 B, 2,378 rows), is added as the
> bulk cross-check source; (b) candidate money now comes from the FEC
> candidate totals via the API (`/candidates/totals/`, 5,321 rows,
> paginated — the funding mix lives only there); (c) the §2.0 join rule
> is replaced by the **candidate-totals rule** below — the
> principal-committee join survives as the committee-table exclusion +
> cross-check; (d) the no-double-count test is redefined accordingly.
> The amendment is recorded in §11; the rest of the plan stands.

| Item | Value |
|---|---|
| Fetch date | 2026-11-19 |
| Source | U.S. Federal Election Commission (FEC), 2024 two-year cycle — bulk downloads `cn24.zip` (356,337 B), `webk24.zip` (469,667 B), `ccl24.zip` (94,262 B), all HEAD 200 on 2026-11-19; openFEC API (`api.open.fec.gov/v1`, `DEMO_KEY`) as cross-check only |
| Expected rows | ~9,796 filed candidates (API count); ~5,321 candidates with totals (API count); ~14,000 committees — coder confirms exact unpacked row counts from the files |
| Date range | 2024 two-year cycle, 2023-01-01 → 2024-12-31 (coverage dates on totals records run 2021-01-01 → 2024-12-31 for most presidential candidates — coder records the confirmed coverage window) |
| Deliverable | Transparent contributions/spending dashboard with source links — every number traceable to its FEC filing, all candidates/parties shown symmetrically |
| Scope | Descriptive analysis of reported 2024-cycle federal campaign finance. **No outcome variable, no causal claims, no per-capita figures** (Census unavailable without a key — brief §1d), **no individual-donor names** (no Schedule A fetch — brief §1a). |

## 1. Problem statement + audience

**Problem.** The 2024 US federal election cycle moved billions of dollars
through thousands of candidate committees, party committees and PACs, but
the FEC publishes that money as bulk files and API endpoints, not as
answers. A citizen, journalist or student asking "where did the money come
from, who raised the most, and how was it spent?" has to join three files,
know which committee is a candidate's own, and avoid double-counting joint
fundraising committees that serve several candidates. This project does
that join once, in the open: every candidate is attached to their principal
campaign committee only, every dollar is summed from the committee-summary
filings, and the result is a dashboard that shows totals, funding mix,
party and office breakdowns, state totals and spending patterns — with a
source link on every surface and the coverage limits stated next to the
numbers.

**Four hard limits are stated up front and labelled on every surface
(README, notebook, insights, dashboard, charts, tables):**

1. **2024 cycle only, reported dollars as filed.** No 2026 rows, no
   inflation adjustment, no imputation, no netting of receipts against
   disbursements. A candidate with no principal-committee summary on file
   is counted as "filed, no totals reported" — never as $0 raised.
2. **State totals are NOT population-adjusted.** The Census per-capita
   path needs a key that does not exist (brief §1d, verified). State
   comparisons use totals and shares only.
3. **No individual-donor detail.** Donor analysis is limited to the
   itemized vs unitemized aggregates the summary filings carry. No donor
   names appear anywhere in this build, by design.
4. **No outcome claims.** The data contains no election-result variable
   and none is added. Nothing in this project says money caused a win or
   a loss, and no amount is described with an editorial adjective.

**Audience / decision-maker.** A nonpartisan reader (citizen, student,
journalist) who wants the money story of the 2024 cycle with receipts —
and a data reviewer checking the method, who wants a documented join
(principal committee only, no double-counting), counted exclusions, a
cross-check against the openFEC API, and every published number matching
the committed CSVs.

## 2. Decisions (frozen)

### 2.0 THE CANDIDATE-TOTALS RULE — first decision, non-negotiable
*(Amended 2026-11-19, coder stage — supersedes the principal-committee
join rule in the original plan. See §11 items 8–12 for why.)*

The single most consequential choice in this build is how a candidate's
money is measured. The FEC's own candidate totals — the
`/candidates/totals/` endpoint and the `webl24` candidate-summary bulk
file — define a candidate's totals as their principal campaign committee
**plus other committees authorized to raise money on their behalf**, with
transfers between those committees counted once. That is the FEC's own
aggregation, and it is the only source that carries the itemized vs
unitemized donor split the funding-mix analysis needs (the legacy bulk
layouts have no such split — verified). The rule is exactly one method:

- **DECIDER: a candidate's money = the FEC candidate totals for that
  candidate** (`/candidates/totals/?cycle=2024`, joined to the candidate
  master `cn24` for party/office/state/district/name). No other
  committee's money is ever added to a candidate total, and no candidate
  total is ever built by hand-summing committees.
- **The principal-committee join survives as a cross-check, not the
  measure.** The coder joins `cn.CAND_PCC → webk.CMTE_ID` and compares
  the principal committee's `TTL_RECEIPTS`/`TTL_DISB` against the
  candidate totals for a sample of candidates (top candidate + 20
  sampled, §3.3); differences are recorded in `data_source.json`, not
  hidden. The `webl24` bulk file is the second cross-check: its receipts
  / disbursements / cash / debts columns were verified against the API
  to the cent for two candidates (brief amendment evidence) and the
  pipeline asserts the cash identity
  COH_BOP + receipts − disbursements = COH_COP on every `webl` row.
- **Party committees, PACs and super PACs are analysed at committee
  level, never attributed to candidates.** Their totals come straight
  from `webk24` grouped by committee type (§4.4). Principal campaign
  committees (the set of `CAND_PCC` values) are excluded from the
  committee tables so no committee is counted twice within the
  committee universe. Joint fundraising committees stay in the
  committee tables (they are committees) and never enter a candidate
  total.
- **Cycle totals are reported as two separate headline numbers, never
  as one unqualified sum:** candidate receipts (Σ over the 5,321 API
  candidate totals) and committee receipts (Σ over all `webk24`
  committees). A combined figure, if shown, carries the explicit
  disclosure that it sums committee filings and therefore double-counts
  dollars transferred between committees. The two universes are never
  summed silently.
- **Tester gate (mandatory):** the tester verifies the rule was actually
  used — a test asserts that every candidate row's receipts equal the
  API totals record for that candidate (fixture + committed file), a
  test asserts that no candidate appears twice in `candidates.csv`, a
  test asserts that no principal committee appears in
  `committees.csv`, and a test asserts the cash identity on the
  `webl` cross-check rows. If the candidate table cannot be reproduced
  from the API totals + `cn24` join, the build fails.
- **No surface** may present a candidate total that includes joint
  fundraising or party-committee money beyond what the FEC's own
  candidate totals include, and no surface may report a cycle total
  without saying which universe it sums and whether transfers are
  included.

### 2.1 Research questions (exactly 3)

1. **How much money moved in the 2024 cycle, and where did it come
   from?** Cycle totals (candidate principals + party/PAC committees),
   funding mix (individual itemized / individual unitemized /
   other receipts), top 10 candidates and top 10 committees by receipts,
   top-5/top-10 concentration (§4.2–§4.3).
2. **How do parties, offices and states differ?** Receipts and funding
   mix by party (DEM/REP/other, symmetric columns) and by office
   (P/S/H), and candidate receipts by state — totals and shares only, no
   per-capita (§4.4).
3. **How was the money spent, and what was left?** Disbursements, burn
   rate (disbursements ÷ receipts), cash on hand and debts — by office
   and for the top 10 candidates (§4.5).

### 2.2 Other frozen decisions

- **Analysis cycle is 2024 only.** No 2026 rows, even though the API
  would return them.
- **Date formats are verified from the files, not assumed** (Day 12
  lesson: that plan's `dayfirst=True` was wrong for its CSV). FEC bulk
  files use their own date format; the coder inspects the header row +
  first data rows, records the confirmed format in `data_source.json`,
  and parses accordingly. Never guess a date format from a previous day.
- **Committee-type grouping is profiled from the file, not hardcoded
  in full.** The coder lists the distinct `CMTE_TP` values present in
  `webk24`, maps each to its FEC data-dictionary meaning, and records
  the mapping in `data_source.json`. The only hardcoded groups are the
  two that the join rule needs: principal candidate committees
  (`CMTE_TP` in {H, S, P} with designation A) vs everything else.
- **No NLP this day.** The roadmap lists NLP as a core skill for the
  sector, but there is no text corpus in scope (no Schedule A donor
  memos, no news text) — inventing one would be clutter. The skill is
  covered by the sector's later days; the limitation is recorded in the
  README, not papered over.
- **No mapping (choropleth) this day.** The roadmap lists mapping as a
  core skill, but a state choropleth needs a topojson/geo asset that
  cannot be verified offline here (Day 7 lesson: Plotly geo needs a CDN
  topojson that fails in this environment). State comparison is a ranked
  bar chart (§7, chart 04). The limitation is recorded in the README.
- **API cross-check is one call, not a fetch.** After building the
  candidate table from bulk, the coder calls
  `/candidates/totals/?cycle=2024&per_page=1&sort=-receipts` once and
  compares the top candidate ID + receipts to the bulk-derived top
  candidate (tolerance $1). The full API pagination fallback (§3.3)
  is used only if a bulk header is wrong.

## 3. Data — source, endpoints, fetch rules, provenance, licence

### 3.1 Source and download (verified, from the brief — copy, do not re-search)

- **Source:** U.S. Federal Election Commission (FEC), 2024 two-year
  cycle. Bulk data index: `https://www.fec.gov/data/browse-data/?tab=bulk-data`.
  Base URL for files: `https://www.fec.gov/files/bulk-downloads/2024/`.
- **Download — PRIMARY (verified 2026-11-19, HEAD 200):**
  - `cn24.zip` — **356,337 bytes** — candidate master (9,796 lines).
  - `webk24.zip` — **469,667 bytes** — committee summary (12,379 lines).
  - `ccl24.zip` — **94,262 bytes** — candidate–committee linkage (8,619 lines).
  - `webl24.zip` — **121,855 bytes** — candidate summary, cross-check source
    (2,378 lines; added by the 2026-11-19 amendment).
  Total **~1,042 KB**. No key, no login, no rate limit. One download of
  each file per build; cache under `data/raw/` and re-use it
  (`--offline` / `--use-cache` per the Day 1 pattern).
- **File format (AMENDED 2026-11-19 — the bulk files are HEADERLESS):**
  each zip unpacks to a pipe-delimited (`|`) `.txt` **with no header row**
  (verified: the first line of each file is a data row). Column names are
  assigned from the FEC file descriptions and **verified against the
  live API to the cent** (see §3.1b) — the file itself never carries
  headers, so the coder must not treat the first row as a header (it
  would silently drop one candidate/committee and shift every column).
  **The coder asserts the cash identity
  COH_BOP + TTL_RECEIPTS − TTL_DISB = COH_COP on every `webk` and
  `webl` row at load time (tolerance $0.01); a failed identity fails
  the build loudly — it is the proof the column layout is right.**

### 3.1b Verified column layouts (2026-11-19, API-matched — the file is authoritative)

- **`cn24` (15 columns):** `CAND_ID, CAND_NAME, CAND_PTY_AFFILIATION,
  CAND_ELECTION_YR, CAND_OFFICE_ST, CAND_OFFICE, CAND_OFFICE_DISTRICT,
  CAND_ICI, CAND_STATUS, CAND_PCC, CAND_ST1, CAND_ST2, CAND_CITY,
  CAND_ST, CAND_ZIP`. Verified against row 0
  (`H0AK00105|LAMB, THOMAS|NNE|2020|AK|H|00|C|N|C00607515|…`).
  Dates: none in this file. Money: none in this file.
- **`webk24` (27 columns, legacy committee-summary layout):**
  `CMTE_ID, CMTE_NM, CMTE_TP, CMTE_DSGN, CMTE_FILING_FREQ,
  TTL_RECEIPTS, TRANS_FROM_AFF, INDV_CONTRIB, OTH_CMTE_CONTRIB,
  CAND_CONTRIB, CAND_LOANS, TTL_LOANS_RECEIVED, TTL_DISB,
  TRANF_TO_AFF, INDV_REFUNDS, OTH_CMTE_REFUNDS, CAND_LOAN_REPAY,
  LOAN_REPAY, COH_BOP, COH_COP, DEBTS_OWED_BY,
  NONFED_TRANS_RECEIVED, CONTRIB_TO_OTHER_CMTE, IND_EXP,
  PTY_COORD_EXP, NONFED_SHARE, CVG_END_DT`. Verified by the cash
  identity on row 0 (`166058.23 + 95727.18 − 117500 = 144285.41`
  exactly) and by the FEC file description. Dates are **MM/DD/YYYY**
  (`CVG_END_DT` = `12/31/2024` — verified from the file, not assumed).
  **This layout has NO itemized/unitemized split** — the funding mix
  cannot come from `webk24`.
- **`ccl24` (7 columns):** `CAND_ID, CAND_ELECTION_YR,
  FEC_ELECTION_TP, CMTE_ID, CMTE_TP, CMTE_DSGN, LINKAGE_ID`. Verified
  against row 0 (`H0AK00105|2020|2024|C00607515|H|P|248736`).
- **`webl24` (30 columns, legacy candidate-summary layout):**
  `CAND_ID, CAND_NAME, CAND_ICI, CAND_N_COMMITTEES, CAND_PTY_AFFILIATION,
  TTL_RECEIPTS, TRANS_FROM_OTHER_AUTH, TTL_DISB, COL_09, COH_BOP,
  COH_COP, COL_12, COL_13, COL_14, COL_15, COL_16, COL_17,
  INDV_CONTRIB, CAND_OFFICE_ST, CAND_OFFICE_DISTRICT, CAND_ST1,
  CAND_ST2, CAND_CITY, CAND_ST, CAND_ZIP, COL_26, COL_27, CVG_END_DT,
  COL_29, COL_30`. Verified columns (API-matched to the cent for
  H2AK01158 Peltola and H2AK01083 Begich): receipts (f06), transfers
  (f07), disbursements (f08), cash on hand (f11 — also matches the API's
  `cash_on_hand_end_period` 1,762,056.63 for P80000722), debts (f17 —
  matches the API's 934,179.58 for P80000722), individual contributions
  (f18). Columns `COL_*` / `CAND_N_COMMITTEES` are **undecoded and
  unused** — recorded as such in `data_source.json`, never guessed at.
  Dates are **MM/DD/YYYY** (verified). **This layout also has NO
  itemized/unitemized split.** The `webl` file covers only **2,378**
  candidates vs the API's 5,321 with totals — the difference is a
  coverage fact recorded in `data_source.json` (the `webl` file appears
  to cover ballot-listed candidates; the API covers all filers with
  totals). The pipeline cross-checks the top candidate + a 20-candidate
  sample, not all rows.
- **Expected columns (per the FEC file descriptions — verify at build):**
  ~~(list superseded by §3.1b above — the header-row assumption was
  wrong; the verified layouts in §3.1b govern.)~~
- **Coverage (from the brief's API probe, to be confirmed from the
  files):** 9,796 filed candidates in cycle 2024; 5,321 candidates with
  totals. The coder records the confirmed counts from the files.
- **Licence / attribution:** FEC data is a work of the United States
  federal government and is in the **public domain**. Cite verbatim in
  `data/README.md`, the notebook and the day README:
  > Source: U.S. Federal Election Commission, 2024 cycle bulk data
  > (https://www.fec.gov/data/browse-data/?tab=bulk-data) and openFEC API
  > (https://api.open.fec.gov/v1). Retrieved 2026-11-19.
  No personal data beyond what the FEC itself publishes; no donor names
  are handled (no Schedule A fetch).

### 3.2 Cleaning rules (frozen — the tester tests these)

Applied in this order; every step's excluded-row count is recorded in
`data_source.json` and reported in `data/README.md`:

1. **Unpack:** unzip each file under `data/raw/`; record zip bytes +
   unpacked bytes + unpacked row counts. Unpacked `.txt` files are
   **git-ignored** (webk24.txt is 1,509,800 bytes — over 1 MB; the
   others are under it but are ignored uniformly for consistency —
   coder measures and records; the committed raw artefacts are the four
   zips, §3.4).
2. **Parse:** read each `.txt` pipe-delimited with the **fixed column
   names from §3.1b (no header row — `header=None, names=[...]`)**.
   Strip whitespace from string fields. Parse money columns to float
   (FEC money fields are plain numbers, no `$`/commas — verified from
   the first rows). **Assert the cash identity
   COH_BOP + TTL_RECEIPTS − TTL_DISB = COH_COP (tolerance $0.01) on
   every `webk` and `webl` row; record the count of rows failing it
   (expected 0 — a failure fails the build).**
3. **Parse dates** — **MM/DD/YYYY** (verified from the files, §3.1b).
   Drop rows where a coverage date is unparseable (count them; expected 0).
4. **Candidate master:** drop rows whose `CAND_ELECTION_YR != 2024`
   (count them — the master file carries other cycles; the first row is
   a 2020 candidate). Drop exact duplicate `CAND_ID` rows, keeping the
   first (count them).
5. **Committee summary:** drop rows whose coverage end date falls
   outside the 2024 cycle window (count them). Drop exact duplicate
   `CMTE_ID` rows, keeping the latest coverage end date (count them).
   Drop rows with negative `TTL_RECEIPTS` (count them — these are
   filing corrections, not real negative fundraising; record the count
   and do not silently keep them).
6. **API candidate totals:** fetch all pages (§3.3), concatenate,
   drop exact duplicate `candidate_id` rows keeping the first (count
   them). Join to the cleaned `cn24` on `candidate_id` for
   party/office/state/district/name. Candidates in the API totals with
   no `cn24` match are kept with party/office/state blank and
   `has_master = False` (count them — do not drop them, their money is
   real). Candidates in `cn24` (2024) with no API totals row are kept
   in `candidates.csv` with money fields blank and `has_totals = False`
   — they are "filed, no totals reported", never $0. Count them.
7. **Committee-type split:** principal campaign committees (the set of
   `CAND_PCC` values from cleaned `cn24`) are flagged
   `is_principal = True` and excluded from the committee-level tables;
   all other `webk` rows form the committee tables. Record both counts.
8. **No imputation, no annualisation, no netting.** Missing money is
   blank, never 0-filled in the candidate table. Burn rate is computed
   only where receipts > 0; otherwise blank.

### 3.3 Fetch rules

- One `GET` per file per build; cache under `data/raw/` and re-use it
  (`--offline` / `--use-cache`). One retry after 60 s on HTTP 429/5xx,
  then stop and report — never hammer the host.
- **API candidate totals — PRIMARY FETCH (amended 2026-11-19):**
  `GET /candidates/totals/?cycle=2024&per_page=100&sort=-receipts`
  with `api_key=DEMO_KEY`, paginating through all 5,321 rows (~54
  pages). Spacing **≥ 7 s between calls**, one 60 s retry on 429 per
  page (max 3 attempts per page). **Each page's JSON is cached to
  `data/raw/api_pages/page_NNN.json` as it arrives (git-ignored,
  resumable)** so an interruption never loses fetched pages; a re-run
  resumes from the cached pages. If the fetch cannot complete all
  pages, the pipeline **fails loudly with the count of pages fetched —
  no partial candidate table is ever written**. The build never depends
  on more than the ~54 calls + the cross-check call; total API calls in
  the build ≈ 55, all spaced ≥ 7 s apart.
- **API cross-check (one call + sample):** after building the candidate
  table, compare the bulk-derived top candidate against
  `/candidates/totals/?cycle=2024&per_page=1&sort=-receipts` (already
  fetched as page 1 — reuse it, no extra call) and compare `webl24`
  receipts/disbursements/cash/debts against the API totals for the top
  candidate + a deterministic 20-candidate sample (seed 42, from
  candidates present in both sources). Record the max absolute
  difference in `data_source.json`. **Known discrepancy (record, do not
  hide):** the API's disbursements for P80000722
  ($1,185,795,517.32) exceed the `webl24` figure ($1,175,214,805.80) by
  $10,580,711.52 while cash and debts agree to the cent — the pipeline
  records the exact difference and the README discloses that headline
  candidate numbers use the API totals and that the bulk cross-check
  differs by that amount for that candidate.
- Verify after fetch: all three zips download, unpack, row counts and
  headers match §3.1/§3.2. Record the verified counts in
  `data_source.json`. If a count or header differs, report it — do not
  silently proceed.

### 3.4 Data-size and commit rule (READ CAREFULLY)

- The four raw zips total **~1,042 KB** (each < 1 MB) — inside the
  portfolio rule (files < 1 MB each, < 5 MB per day folder). Therefore
  the **raw zips ARE committed** as the provenance record (same rule as
  Day 1's raw JSONs).
- **`.gitignore` MUST exclude the unpacked `.txt` files and the API page
  cache:** `data/raw/*.txt`, `data/raw/api_pages/`. The unpacked
  `webk24.txt` is 1,509,800 bytes — over 1 MB; the API pages are
  regenerable from the API. The committed raw artefacts are the four
  zips, §3.5.
- **`.gitignore` must NOT exclude `data/` itself** — only the unpacked
  `.txt` lines (plus the standard synthetic line
  `data/raw/*_synthetic.json`). All processed files in §3.5 and the
  three zips are committed.
- **The pipeline downloads the zips at build time** (`--live`),
  verifies the counts in §3.3, and caches them under `data/raw/` for
  re-use (`--use-cache`). `--offline` runs from the committed processed
  files only (no network, no zips needed) and regenerates charts +
  summaries from them.
- **`.gitignore` otherwise follows the scaffold default:**
  `__pycache__/`, `.venv/`, `venv/`, `.env`, `*.key`, `*.log`,
  `.streamlit/secrets.toml`, `.pytest_cache/`,
  `.ipynb_checkpoints/`, plus the unpacked-`.txt` and synthetic lines
  above. The tester diffs `.gitignore` against this list before sign-off.

### 3.5 Committed processed files (all < 1 MB; regenerable with one command)

| File | Contents |
|---|---|
| `data/processed/data_source.json` | Source, URLs, zip sizes, fetch date, row counts (unpacked / cleaned / excluded per rule / candidates with and without totals / API pages fetched), confirmed date (MM/DD/YYYY) + money formats, headerless-layout note + API-match verification, cash-identity check result, committee-type mapping, join-rule outcome (principal committees matched, candidates without totals), API cross-check result (top candidate ID + receipts, `webl` sample max difference, the P80000722 disbursement discrepancy $10,580,711.52), coverage window, metric definitions, manual validation, versions |
| `data/processed/candidates.csv` | One row per 2024 candidate (~9,796 expected — coder confirms): `candidate_id`, `candidate_name`, `party`, `office`, `state`, `district`, `election_year`, `principal_committee_id`, `has_totals`, `receipts`, `disbursements`, `cash_on_hand`, `debts_owed`, `individual_contributions`, `individual_itemized`, `individual_unitemized`, `other_receipts`, `small_dollar_share`, `burn_rate` |
| `data/processed/committees.csv` | One row per non-principal committee (~all `webk` rows minus principals): `committee_id`, `committee_name`, `committee_type`, `designation`, `receipts`, `disbursements`, `cash_on_hand`, `debts_owed`. `committee_type_full` is NOT in this file (plan §11 item 21 — the long label repeats on every row and pushed the file over the 1 MB/file rule); the full mapping lives in `data_source.json` (`committee_type_full_mapping`) and the label is re-derived in `derive_tables` for `top_committees.csv` |
| `data/processed/party_office.csv` | One row per (party × office) with totals: `party`, `office`, `n_candidates`, `n_with_totals`, `n_with_split`, `receipts`, `receipts_with_split`, `disbursements`, `receipts_share`, `individual_contributions`, `individual_itemized`, `individual_unitemized`, `small_dollar_share`, `median_receipts`, `top_candidate_id` — funding-mix sums cover the split subset only (`n_with_split`, `receipts_with_split`), never the full office total |
| `data/processed/state_totals.csv` | One row per state (candidate state from `cn24`): `state`, `n_candidates`, `n_with_totals`, `receipts`, `disbursements`, `receipts_share`, `median_receipts`, `top_candidate_id` — with the explicit note that figures are NOT population-adjusted |
| `data/processed/top_candidates.csv` | Top 10 candidates by receipts: `rank`, `candidate_id`, `candidate_name`, `party`, `office`, `state`, `receipts`, `receipts_share`, `disbursements`, `burn_rate`, `cash_on_hand` |
| `data/processed/top_committees.csv` | Top 10 non-principal committees by receipts: `rank`, `committee_id`, `committee_name`, `committee_type`, `committee_type_full`, `receipts`, `receipts_share`, `disbursements`, `cash_on_hand` |

- The unpacked `.txt` files are **not** committed (size, §3.4). They are
  rebuilt by `python -m src.data_pipeline --live` from the committed
  zips / live URLs, and the notebook re-runs the join from them when
  present (§6, notebook rule). The committed processed CSVs are the
  offline-reproducible record: every number in the README, insights and
  dashboard must match them.
- **Offline rule (Day 5/6 lesson):** `--offline` must NOT clobber
  `data_source.json` fields recorded by a live run (`source: "live"`,
  counts, fetch date, API cross-check). It regenerates only the derived
  tables/charts from the committed CSVs; **a test asserts this — the
  offline run skips writing `data_source.json` entirely when a live
  record already exists.** **CI-flake lesson (Day 9, 2026-11-13):** the
  offline-reproduction test compares regenerated floats with a
  **tolerance** (absolute ≤ 0.01 on dollar values, relative ≤ 1e-6
  elsewhere) — never byte-exact — because environment rounding flakes
  byte comparisons.

### 3.6 Fallback, licence, attribution

- **Synthetic fallback (only if all four bulk files fail):** per brief §4
  — retry once after 60 s per URL, then stop and report to the
  orchestrator — **do not silently substitute synthetic data**. If a
  synthetic fallback were ever authorised, it must be built from the
  brief's documented parameters (~5,300 candidates / ~14,000 committees,
  seed 42), stored as `data/raw/*_synthetic.csv` (git-ignored, NEVER
  overwrites real data), recorded in `data_source.json` as
  `synthetic: true, seed: 42`, and labelled "SYNTHETIC — NOT REAL DATA"
  in every chart, the notebook, and the README. Methods (§4) are
  unchanged. Not expected to be needed (all three HEADs probed HTTP 200).
- **Licence: public domain (US federal government work).** Attribution
  verbatim in README.md, data/README.md, the notebook and the dashboard
  footer (§3.1).
- **No Power BI file:** no `.pbix` is produced (same decision as
  Days 8–12 — a `.pbix` cannot be built or verified in this
  environment); the finance tracker is delivered as the Streamlit app +
  static charts. Recorded here so the coder does not re-litigate it.
  The SQL skill is covered by the §4.6 check.

## 4. Analysis — definitions (from the brief, frozen; planner decisions in §11)

### 4.1 Money definitions (DECIDED — exact, from brief §2)

- **Total receipts** = `TTL_RECEIPTS` from the committee summary
  (candidate's principal committee, or the committee itself). Nominal
  USD as filed; no inflation adjustment, no annualisation.
- **Total disbursements** = `TTL_DISB`. **Cash on hand** = `COH_COP`
  (end of period). **Debts owed** = `DEBTS_OWED_BY`.
- **Individual contributions** = `INDV_CONTRIB`. Split into **itemized**
  (donors > $200/cycle, named) and **unitemized** (small-dollar, ≤ $200,
  aggregate only) per the exact columns recorded in §3.1.
- **Other receipts** = receipts − individual contributions (PAC money,
  party transfers, candidate loans, other). Reported as a residual and
  labelled as such wherever it appears.
- **Small-dollar share** = unitemized ÷ individual contributions.
  A funding-mix descriptor only — never a donor headcount.
- **Burn rate** = disbursements ÷ receipts, computed only where
  receipts > 0. Descriptive only; > 1 is possible (spending down
  prior-cycle cash) and is not flagged as an error.
- **Party share** = a party's candidates' receipts ÷ all candidates'
  receipts (same office, or whole cycle). Parties compared symmetrically:
  DEM, REP, LIB, GRN, IND/other all shown with the same columns; no
  party is the reference group.
- **Top-N concentration** = share of total receipts held by the top 5 /
  top 10 candidates (and, separately, top 10 committees).

### 4.2 Cycle totals (DECIDED)

- **Cycle receipts (candidate universe)** = Σ receipts over the 5,321
  API candidate totals. **Cycle receipts (committee universe)** = Σ
  `TTL_RECEIPTS` over ALL `webk24` rows (12,379 committees, principals
  included). The two figures are reported side by side with their
  universes named; a combined figure, if shown, carries the transfer
  disclosure (§2.0). Neither figure is presented as "total money raised
  from the public" — both are sums of filings.
- **Cycle disbursements / cash on hand / debts** = the same two-universe
  treatment. Cash on hand is a stock (end-of-period balance), not a
  flow — it is summed across committees/candidates as a reported total
  and labelled as such, never added to receipts.
- **Candidates with totals** = API totals rows (expected 5,321 per the
  probe — coder confirms). **Filed, no totals** = 2024 `cn24`
  candidates with no API totals row. Both counts appear on every
  surface that reports a candidate count. **Coverage note:** `webl24`
  covers only 2,378 candidates — it is a cross-check source, not the
  candidate universe.

### 4.3 Top-N tables (DECIDED)

- **Top 10 candidates by receipts** (`top_candidates.csv`): rank, name,
  party, office, state, receipts, share of all candidate receipts,
  disbursements, burn rate, cash on hand. Ties broken by candidate ID
  ascending (deterministic).
- **Top 10 non-principal committees by receipts**
  (`top_committees.csv`): same shape at committee level. Joint
  fundraising committees appear here (they are committees, not
  candidates) — their presence is the honest place for them, and the
  README says so.
- **Concentration:** top-5 and top-10 candidate shares of total
  candidate receipts; top-5/top-10 committee shares of total committee
  receipts. Reported in the notebook, insights and dashboard.

### 4.4 Party / office / state breakdowns (DECIDED)

- **Party × office table** (`party_office.csv`): for each (party, office)
  — n candidates, n with totals, receipts, disbursements, receipts
  share, individual contributions + itemized/unitemized split,
  small-dollar share, median receipts, top candidate. Parties: use the
  `CAND_PTY_AFFILIATION` codes as filed (DEM, REP, LIB, GRN, IND, …);
  group codes with < 10 candidates into "Other" for the chart only —
  the table keeps every party code. No party is dropped from any table.
- **Office codes:** P (President), S (Senate), H (House), plus Z/G/O
  if present in the file (profiled, not assumed). Office is taken from
  `CAND_OFFICE` as filed.
- **State table** (`state_totals.csv`): candidate state is the
  **mailing-address state as filed (`CAND_ST`)**, falling back to the
  office state where the mailing state is blank. Presidential
  candidates therefore appear under their campaign HQ state
  (Biden/Harris: PA, Philadelphia) — the README, chart 04 footnote and
  dashboard all say so, so PA is never misread as "Pennsylvania donors
  gave the most". **Footnote on every state surface: "Totals are not
  adjusted for state population — no per-capita figures."**
- **Committee-type table** (in the notebook + dashboard, not a separate
  CSV): receipts/disbursements by `CMTE_TP` group, computed from
  `committees.csv` + the principal set, with the type mapping recorded
  in `data_source.json`.

### 4.5 Spending patterns (DECIDED)

- **Burn rate by office:** median + mean burn rate per office (P/S/H),
  from `candidates.csv` where receipts > 0. Reported with the n behind
  each median (small-n offices are labelled as such).
- **Cash on hand:** top 10 candidates by cash on hand (in the notebook
  + dashboard table), plus total cash on hand across committees
  (labelled as a summed stock, §4.2).
- **Debts:** total debts owed by committees; top 5 committees by debts
  owed (notebook + dashboard). No interpretation of what debts "mean" —
  reported as filed.

### 4.6 SQL check (roadmap core skill — small, honest)

The notebook answers one question twice — once in pandas, once in SQL —
on the committed `candidates.csv` + `party_office.csv` loaded into an
in-memory SQLite database (`sqlite3`, stdlib): total receipts per party,
and the top party by receipts, asserted equal to the pandas result. A test
asserts the SQL and pandas numbers agree. This is the day's SQL element;
no `.pbix` is built (§3.6) and the pipeline itself stays pandas.

### 4.7 Insights structure (DECIDED)

`outputs/insights_summary.md` carries one finding per §2.1 question with
exact numbers, the top-10 tables, and limitations (2024 cycle only;
state totals not population-adjusted; no donor names; no outcome claims;
candidates filed without totals counted separately; joint fundraising
committees appear only in the committee table, never in candidate totals;
small-dollar share is a funding-mix descriptor, not a donor count).
No finding without a number; no recommendation beyond "what the data
shows" — this is a transparency dashboard, not an advice product, and
the insights say so.

## 5. File tree (exact — build only this)

```
day-13-election-campaign-finance-tracker/
├── README.md  requirements.txt  .gitignore  pyproject.toml  LICENSE
├── .pre-commit-config.yaml
├── research_brief.md  plan.md  coder_handoff.md  test_report.md
├── optimizer_handoff.md  publisher_handoff.md
├── data/
│   ├── README.md
│   ├── raw/
│   │   ├── cn24.zip            (356,337 B, committed)
│   │   ├── webk24.zip          (469,667 B, committed)
│   │   ├── ccl24.zip           (94,262 B, committed)
│   │   └── webl24.zip          (121,855 B, committed — cross-check source)
│   └── processed/
│       ├── data_source.json
│       ├── candidates.csv      (~9,796 rows, one per candidate)
│       ├── committees.csv      (~14,000 rows, non-principal committees)
│       ├── party_office.csv    (party × office rows)
│       ├── state_totals.csv    (one row per state)
│       ├── top_candidates.csv  (10 rows)
│       └── top_committees.csv  (10 rows)
├── notebooks/analysis.ipynb
├── src/
│   ├── __init__.py
│   ├── data_pipeline.py
│   ├── finance.py
│   ├── make_charts.py
│   └── app.py
├── outputs/
│   ├── insights_summary.md
│   └── charts/
│       ├── 01_receipts_by_office_party.png
│       ├── 02_top_candidates.png
│       ├── 03_funding_mix.png
│       └── 04_state_totals.png
├── screenshots/
│   └── dashboard.png
└── tests/
    └── test_pipeline.py
```

Notes: the scaffold's `tests/test_smoke.py` is **DELETED** and replaced by
`tests/test_pipeline.py` (do not keep two test files). The scaffold's
placeholder `README.md`, `data/README.md`, `notebooks/analysis.ipynb`,
`outputs/insights_summary.md`, `requirements.txt` and `pyproject.toml`
are filled in by the coder — not new files. No unpacked `.txt` on disk at
handoff (git-ignored, §3.4 — the zips are the committed raw artefacts).
No extra modules, no extra charts, no `.pbix`, no model card. The
scaffold's `requirements.txt` is Day 1's list — the coder replaces it
with the §6 pinned stack (no scikit-learn, no scipy, no openpyxl this day).

## 6. Per-file responsibilities

| File | Responsibility |
|---|---|
| `src/data_pipeline.py` | Download the 4 zips (primary; 1 retry after 60 s on 429/5xx, then stop and report); unzip under `data/raw/`; verify layouts (§3.1b) + row counts + cash identities; apply cleaning rules §3.2 in order, counting every exclusion; fetch the API candidate totals (§3.3, paginated, per-page cache + resume, ≥ 7 s spacing, fail loudly if incomplete); build all 6 processed CSVs (§3.5); run the `webl` cross-check (§3.3) and record it; write `data_source.json` (live fields); modes `--live` / `--offline` / `--use-cache` / `--synthetic` (brief §4 generator, seed 42). `--offline` skips writing `data_source.json` when a live record exists (§3.5). |
| `src/finance.py` | Pure finance functions, no I/O, no network — all tested: `small_dollar_share(itemized, unitemized)`, `burn_rate(receipts, disbursements)`, `other_receipts(receipts, individual)`, `party_share(part, total)`, `top_n_share(amounts, n)`, `principal_committees(candidates)` (the set of `CAND_PCC` values, for the committee-table exclusion + cross-check), `check_cash_identity(df)` (COH_BOP + receipts − disbursements vs COH_COP, tolerance $0.01), `summarise_party_office(candidates)`, `summarise_states(candidates)`, `top_n(df, column, n)` (deterministic tie-break by ID) |
| `src/make_charts.py` | Exactly 4 PNGs (§7), matplotlib `Agg`, offline from processed CSVs only, every chart footnoted with the source + public-domain attribution + "2024 cycle — reported dollars as filed" + synthetic label if applicable |
| `src/app.py` | Streamlit dashboard loading processed CSVs only (offline): KPI row (cycle receipts $, cycle disbursements $, candidates with totals / filed, committees, top candidate + share); party × office table; top-10 candidates table; top-10 committees table; state table (with the not-population-adjusted note); the 4 charts embedded; methods + limitations panel (2024 only, principal-committee join, no per-capita, no donor names, no outcome claims); source links on every section (fec.gov bulk data + openFEC API); `width="stretch"` (Day 2 lesson — no deprecated `use_container_width`); footer with public-domain attribution |
| `notebooks/analysis.ipynb` | Offline top-to-bottom, ≤ 16 cells, 0 error cells via nbconvert, `_find_root()` from the notebook file location (Day 1 lesson (e)): load + audit (filed vs with-totals, header verification, exclusion counts); cycle totals + composition; funding mix; party × office; state totals; top-10 tables + concentration; spending patterns (burn rate by office, cash on hand, debts); the 4 charts inline; Q1–Q3 answered with exact numbers; the SQL check (§4.6); **join section guarded by `RAW.exists()`** — if the unpacked `.txt` files are present it re-runs the principal-committee join via `src.finance` and asserts the results match the committed CSVs within tolerance; if absent it loads the committed CSVs and prints a note that the re-run was skipped (still 0 errors). The notebook never downloads data itself. |
| `tests/test_pipeline.py` | ≥ 15 tests: pipe-delimited parsing with the fixed §3.1b column names (**first row is data, not a header** — a test asserts the first `cn` row parses as candidate H0AK00105, not as a header); money parsing (plain numbers, no `$`/commas); date parsing MM/DD/YYYY, unparseable counted; duplicate candidate/committee rows handled; negative-receipts rows excluded; candidates without API totals kept with `has_totals = False` (never $0); API totals rows with no `cn` match kept with `has_master = False`; **cash-identity test — COH_BOP + receipts − disbursements = COH_COP on fixtures and on the committed `webk`/`webl` loads**; principal committees excluded from `committees.csv` (fixture + committed file); no candidate appears twice in `candidates.csv`; small-dollar share / burn rate (incl. receipts = 0 → blank) / other-receipts residual / party share / top-N share on fixtures; top-N deterministic tie-break by ID; state aggregation sums to the candidate cycle total; party table includes every party present (symmetry — no party dropped); offline run does not clobber `data_source.json` live fields; **offline reproduction uses tolerance comparison (Day 9 CI lesson), not byte-exact**; synthetic files never overwrite live files; no committed file > 1 MB, `data/` < 5 MB; SQL-vs-pandas agreement (§4.6); unpacked `.txt` files and `api_pages/` are git-ignored (`.gitignore` contains `data/raw/*.txt` and `data/raw/api_pages/`) while the four zips are NOT ignored |
| `data/README.md` | Provenance: FEC bulk URLs, zip sizes, openFEC API cross-check, public-domain licence, fetch date, row counts (unpacked / cleaned / excluded per rule / candidates with and without totals), confirmed date + money formats, committee-type mapping, join rule (§2.0) with the double-count check result, coverage window, metric definitions, manual validation, versions |
| `outputs/insights_summary.md` | One finding per §2.1 question with exact numbers + top-10 tables + limitations (§4.7) |
| `README.md` | Problem, audience, setup, how to run (live/offline), sample outputs (KPI table + chart thumbnails), headline findings with numbers, top-10 tables, the join rule (§2.0) stated plainly, validation, limitations, attribution, source links |
| `requirements.txt` | Pinned `==` versions verified in the build venv (Python 3.12.3): Day 12 stack **minus scikit-learn, scipy, openpyxl** (no clustering, no forecasting, no XLSX this day): pandas, numpy, matplotlib, plotly, streamlit, requests, pytest, jupyter, nbformat. No other new runtime dependency without a plan change |
| `pyproject.toml` / `.gitignore` | Scaffold defaults (ruff/black line-length 88; strict mypy, coverage source `src`); `.gitignore` per §3.4 (unpacked `.txt` + synthetic excluded; the three zips and `data/` itself NOT excluded) |

Key function signatures (coder follows these names):

```python
# src/data_pipeline.py
def download_bulk(url: str, dest: Path) -> Path
def unpack_bulk(zip_path: Path, dest_dir: Path) -> Path
def load_bulk_txt(path: Path) -> pd.DataFrame  # pipe-delimited, header row
def clean_candidates(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]
def clean_committees(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]
def api_cross_check_top_candidate() -> dict  # one DEMO_KEY call, §3.3
def write_data_source(path: Path, record: dict) -> None

# src/finance.py
def small_dollar_share(itemized: float, unitemized: float) -> float | None
def burn_rate(receipts: float, disbursements: float) -> float | None
def other_receipts(receipts: float, individual: float) -> float
def party_share(part: float, total: float) -> float
def top_n_share(amounts: pd.Series, n: int) -> float
def principal_committees(candidates: pd.DataFrame) -> set[str]
def check_cash_identity(df: pd.DataFrame) -> pd.DataFrame  # rows failing, tolerance $0.01
def summarise_party_office(candidates: pd.DataFrame) -> pd.DataFrame
def summarise_states(candidates: pd.DataFrame) -> pd.DataFrame
def top_n(df: pd.DataFrame, column: str, n: int) -> pd.DataFrame
```

## 7. Charts (exactly 4, matplotlib, to scale and legible)

All charts: title, labelled axes with units ($ as stated), source footnote
("Source: U.S. Federal Election Commission, 2024 cycle bulk data
(https://www.fec.gov/data/browse-data/?tab=bulk-data), public domain —
reported dollars as filed"), no truncated axes, legible at 100% zoom.
Party colours are fixed and symmetric: DEM #2e6fb7 (blue), REP #c0392b
(red), other parties/unknown #7f8c8d (grey) — the same palette on every
chart, neither party given a visual advantage (same bar width, same
labelling, same position order: DEM, REP, Other).

1. **01_receipts_by_office_party.png** — Receipts by office and party.
   Grouped bars: offices P / S / H on the x-axis, one bar per party
   (DEM, REP, Other) with $ labels; answers Q2's party × office half.
2. **02_top_candidates.png** — Top 10 candidates by receipts.
   Horizontal bars, one per candidate, labelled with name + party +
   office + $ + share of candidate receipts; bars coloured by party
   with the §7 palette; title names the metric ("Top 10 by total
   receipts, 2024 cycle"). Answers Q1's concentration half.
3. **03_funding_mix.png** — Where the money came from. Stacked bars per
   office (P / S / H): individual itemized / individual unitemized /
   other receipts, as shares (0–100%) with $ totals annotated;
   answers Q1's funding-mix half.
4. **04_state_totals.png** — Top 15 states by candidate receipts.
   Horizontal bars with $ labels and candidate counts annotated;
   footnote: "Totals are not adjusted for state population."
   Answers Q2's state half.

The Streamlit dashboard embeds the 4 PNGs (as Days 6–12 do) so the README
thumbnails and the app agree.

## 8. Success checklist (roadmap minimum success criteria — all must pass)

- [ ] Problem statement + audience written (§1, in README and this plan)
- [ ] Data source documented: provider, URLs, zip sizes, licence (public
      domain, verbatim attribution), fetch date (2026-11-19), row counts
      (unpacked / cleaned / excluded per rule / candidates with and
      without totals), confirmed date + money formats, coverage window —
      in `data/README.md` and `data/processed/data_source.json`
- [ ] Repeatable prep steps documented (download → unpack → clean →
      principal-committee join → aggregate → charts, with `--offline`
      mode) + metric definitions (§4.1) written down
- [ ] **Candidate-totals rule (§2.0, amended) stated in the plan and
      honoured in the build**: candidate money is the FEC candidate
      totals (API) joined to `cn24`; the principal-committee join is a
      cross-check, not the measure; committee tables exclude principals;
      cycle totals are reported per universe with the transfer
      disclosure; **tester verified the rule was actually used**
      (candidate receipts reproduce from the API totals, no candidate
      twice, no principal in the committee table, cash identity holds —
      test + test_report evidence)
- [ ] **Transparent contributions/spending dashboard with source links
      delivered** (roadmap deliverable): Streamlit dashboard + README
      with source links on every section, KPI row, party × office table,
      top-10 candidates + committees tables, state table, 4 charts
- [ ] **Contributions analysed**: cycle totals, funding mix (itemized /
      unitemized / other) by office and party, small-dollar shares,
      top-10 candidates + committees, top-5/top-10 concentration
- [ ] **Donors analysed at the aggregate level only** (itemized vs
      unitemized — §1 limits): no donor names anywhere; the limitation
      stated on every surface that mentions donors
- [ ] **Spending patterns analysed**: disbursements, burn rate by office,
      cash on hand (top 10 + summed stock, labelled), debts (total +
      top 5 committees)
- [ ] **Nonpartisan presentation verified**: same metrics/columns/charts
      for every party; no causal claims; no editorial adjectives; every
      chart/table states its coverage and source link
- [ ] **State comparison honest**: totals and shares only, with the
      not-population-adjusted footnote on every state surface
- [ ] **SQL check done** (§4.6): total receipts per party and top party
      by receipts via in-memory SQLite asserted equal to pandas, in the
      notebook and a test
- [ ] Exactly **4 charts** (§7), drawn to scale and legible, plus a
      functional dashboard: the Streamlit dashboard runs and renders
      (smoke gate below)
- [ ] Interpretation written (`outputs/insights_summary.md`, one finding
      per §2.1 question with exact numbers) + limitations (§4.7)
- [ ] README with setup instructions, sample outputs (KPI table + chart
      thumbnails), validation results, the candidate-totals rule, and limitations
- [ ] No credentials / private records in the repo; **no copying others'
      code** — all code is Victor's own original work; **data-size rule
      honoured** (no file > 1 MB, `data/` < 5 MB; raw zips committed per
      §3.4, unpacked `.txt` git-ignored and absent at handoff;
      `.gitignore` matches §5/§6 and does NOT exclude `data/`)
- [ ] **One metric manually validated by hand** and recorded in
      `data/README.md` (the tester recomputes one metric — e.g. the top
      candidate's receipts from the `webk` row of their principal
      committee, or the cycle total from the committed CSVs — from the
      committed CSVs, matching to the last digit)
- [ ] Pipeline runs end-to-end from a clean checkout (`pip install -r
      requirements.txt`, `python -m src.data_pipeline --live`,
      `python -m src.make_charts`, `pytest tests/ -q`) — **pytest passing
      both from the repo root and from inside the day folder, with
      coverage at or above the threshold (30, from CHANGELOG.md /
      .github/workflows/ci.yml — the measured floor, Day 8 at 34.94%)**
- [ ] **Notebook runs top-to-bottom without errors** (offline, via
      nbconvert — **exit 0 with 0 error cells** — with `_find_root()`
      and the guarded join section, §6)
- [ ] Pinned dependencies in `requirements.txt` (no scikit-learn, scipy,
      openpyxl this day); **`black --check` + `ruff check` clean**;
      **`mypy src tests` clean** (strict-by-default — every `src/`
      function annotated, test functions annotated `-> None`)
- [ ] Streamlit smoke gate passed: **fresh port 8502+**, HTTP 200 on `/`
      and on `/_stcore/health`, **real `screenshots/dashboard.png`**
      captured (**< 1 MB**), server killed and port verified free
- [ ] **Offline pipeline run must NOT clobber `data_source.json`**
      (skip writing it when a live record exists — §3.5, tested)
- [ ] **No base64 strings quoted in docs** (validator false-positive
      rule — never paste base64 content into any `.md` file)
- [ ] **Orchestrator validate clean** for the day folder
      (`python agents/orchestrator.py --day 13 validate`) — **target
      11/11 checks pass**
- [ ] Charts to scale and legible; frozen-tree check passed immediately
      before push (every file the READMEs reference exists on disk —
      charts, screenshot, CSVs)

## 9. Coder handoff checklist (reference — coder must satisfy all of these before the tester starts)

- [ ] venv exists with pinned deps installed; `black --check` + `ruff check` pass; `mypy src tests` clean; `pytest` passes (≥ 15 tests, coverage ≥ 30, from repo root and from the day folder)
- [ ] `.gitignore` matches §3.4/§5 (unpacked `data/raw/*.txt` +
  `data/raw/api_pages/` + synthetic excluded; the four zips and `data/`
  itself NOT excluded; nothing else in `data/` excluded)
- [ ] `screenshots/dashboard.png` is a real capture of the running app on a fresh port (8502+), < 1 MB
- [ ] `data/` total < 5 MB, no file > 1 MB; **no unpacked `.txt` on disk at handoff** (git-ignored, deleted after the build); `data_source.json` records live counts, cleaning exclusions, candidates with/without totals, headerless-layout verification, cash-identity result, committee-type mapping, candidate-totals-rule outcome, API cross-check result (incl. the P80000722 disbursement discrepancy)
- [ ] Counts verified against §3.3; confirmed date (MM/DD/YYYY) + money formats recorded; candidate-totals rule (§2.0, amended) implemented — candidate receipts reproduce from the API totals, no candidate twice, no principal in the committee table
- [ ] `tests/test_smoke.py` deleted — only `tests/test_pipeline.py` exists
- [ ] Notebook runs via nbconvert with exit 0 and 0 error cells; SQL check asserts in the notebook
- [ ] Build only what §5 lists; no extra web searches; no base64 strings in any doc

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| A bulk zip fails to download or is truncated | 1 retry after 60 s, then stop and report; synthetic fallback (§3.6) only if all four fail |
| Bulk layout differs from §3.1b (e.g. a new FEC format) | Cash-identity assertion fails the build loudly (§3.1); layout re-verified against the API before any column is renamed — never silently worked around |
| `webk24` has no itemized/unitemized split | Fall back to the API candidate totals (§3.3) for the funding mix — do not invent the split |
| Date format assumed wrong (Day 12 lesson) | Format verified from the file's first rows (§2.2); recorded in `data_source.json` |
| Joint fundraising committees double-counted | Join rule (§2.0): principal committee only; linkage file is audit-only; no-double-count test |
| Candidate has no principal-committee match | Kept with `has_totals = False`, never $0 (§3.2 rule 6); counted on every surface |
| DEMO_KEY rate limit (10/min) hit | ≤ 10 API calls total, ≥ 6 s spacing, one 60 s retry on 429; bulk is the primary path, API is never load-bearing |
| `committees/totals/` or `sort=-total_receipts` retried | Both verified 404/422 in the brief (§1b) — do not retry them |
| Census per-capita unavailable | Out of scope by design (§1d); state footnote on every state surface |
| A party/office/state is dropped from a table | Symmetry test (§6): party table includes every party present; state table sums to the cycle total |
| Burn rate misread as "overspending" | Labelled descriptive everywhere; > 1 explained as spending down prior-cycle cash |
| Money read as causal ("bought the election") | Nonpartisan rules (§1 limits, brief §2): no outcome variable, no causal claims, no editorial adjectives |
| Byte-exact offline comparison flakes in CI (Day 9 lesson) | Tolerance-based comparison in the offline test (§3.5) |
| Push-manifest / remote-head loss (Day 7 lesson) | Publisher keeps the push manifest under `~/workspace/` (never `/tmp`); re-check the remote head after any uncertain write |
| Base64 passed to `create_or_update_file` (Day 8 lesson) | Never pass base64 content to `create_or_update_file` — it stores the base64 text as the file. Use push-files from disk for file updates, or pass raw text. Never quote base64 strings in docs (§8). |
| GitHub write-approval card times out (Days 10/12 lesson) | Push step needs the card allowed first; a timed-out card leaves nothing pending, so a retry starts a fresh card rather than waiting on the old one. Per the Day 13 task: attempt the push ONCE; on policy_denied stop immediately, re-check the head, leave everything staged, report the blocker + resume steps. |

## 11. Differences from the brief (plan wins)

- **Join rule (§2.0):** the brief required the planner to state how
  candidate money is measured and warned about joint fundraising
  committees. The plan **fixes** it: **a candidate's money is their
  principal campaign committee's summary filing only** (`CAND_PCC` →
  `webk.CMTE_ID`); the linkage file is audit-only; party/PAC committees
  are analysed at committee level and never attributed to candidates.
- **Primary dataset (§3.1):** the brief presented bulk and API as
  co-equal verified paths. The plan **fixes** bulk as primary and the
  API as a one-call cross-check (plus a documented pagination fallback
  if a bulk header is wrong) — so the build never depends on the
  DEMO_KEY rate limit.
- **Date formats (§2.2):** the brief did not state a date format. The
  plan **fixes** verification from the file's first rows (Day 12 lesson)
  and forbids assuming any format.
- **Committee-type grouping (§2.2):** the brief left the grouping to the
  planner. The plan **fixes** profiling the distinct `CMTE_TP` values
  from the file and recording the mapping, with only the
  principal-vs-other split hardcoded.
- **NLP / mapping (§2.2):** the brief listed NLP and mapping as roadmap
  core skills. The plan **fixes** both as out of scope for this day (no
  text corpus in scope; no verifiable offline geo asset) and records the
  limitation in the README instead of inventing a corpus or a map.
- **Funding-mix fallback (§3.1):** the brief verified the API carries
  the itemized/unitemized split but did not say what happens if the bulk
  file lacks it. The plan **fixes** the API candidate totals as the
  fallback for the funding mix — the split is never invented.
- **Raw artefacts (§3.4):** the brief verified the three zips total
  ~920 KB and are committable. The plan **fixes** the commit rule: the
  zips are committed, the unpacked `.txt` files are git-ignored (webk24.txt
  is 1,509,800 bytes — over 1 MB) and regenerated by the pipeline; the
  API page cache (`data/raw/api_pages/`) is git-ignored too.
- **Headerless files (§3.1b, amendment item 8):** the brief and the
  original plan said each bulk file "unpacks to a pipe-delimited `.txt`
  with a header row". **Wrong — verified against the files: there is no
  header row; the first line of each file is a data row.** The plan now
  fixes the verified column layouts in §3.1b (assigned from the FEC file
  descriptions, API-matched to the cent for two candidates, cash
  identity asserted at load). Treating row 1 as a header would silently
  drop one candidate/committee and shift every column.
- **Legacy layouts, no itemized split (§3.1b, amendment item 9):** the
  brief assumed the committee-summary detail columns might carry the
  itemized/unitemized split. **Verified: both `webk24` (27 columns) and
  `webl24` (30 columns) use the FEC legacy layouts, which have no
  itemized/unitemized columns.** The plan now fixes the funding mix to
  come from the API candidate totals (§3.3) — the split is never
  invented, and the bulk files are never claimed to carry it.
- **Candidate money source (§2.0, amendment item 10):** the original
  plan fixed candidate money = principal committee's filing only.
  **Superseded:** candidate money is now the FEC candidate totals
  (API), defined by the FEC as principal + other authorized committees,
  because that is the only source with the itemized split and because
  the FEC's own aggregation avoids hand-summing committees. The
  principal-committee join survives as the committee-table exclusion +
  cross-check. The no-double-count test is redefined per universe
  (§2.0).
- **`webl24.zip` added (§3.1, amendment item 11):** the original plan
  listed three bulk files. A fourth, `webl24.zip` (121,855 B, 2,378
  rows, legacy candidate-summary layout), is added as the bulk
  cross-check source — it is what let the column layouts be verified to
  the cent. It is committed like the other three zips.
- **Cycle-total reporting (§4.2, amendment item 12):** the original plan
  fixed cycle receipts = Σ `webk` receipts. **Superseded:** cycle totals
  are now reported as two separate per-universe figures (candidate
  receipts from the API totals; committee receipts from `webk`), with a
  transfer disclosure on any combined figure — because summing the two
  universes double-counts inter-committee transfers. `webl24` covers
  only 2,378 candidates vs the API's 5,321 with totals; that coverage
  difference is recorded, not smoothed over.
- **P80000722 disbursement discrepancy (§3.3, amendment item 13):**
  the API's disbursements for the top candidate ($1,185,795,517.32)
  exceed the `webl24` figure ($1,175,214,805.80) by $10,580,711.52
  while cash and debts agree to the cent. The plan now fixes the
  pipeline to record the exact difference and the README to disclose
  that headline candidate numbers use the API totals. The difference
  was found in the coder's verification pass, not assumed away.
- **Cash-identity check (§3.1b, amendment item 14):** the original plan
  said a failed cash identity fails the build loudly. **Corrected:**
  the identity (COH_BOP + receipts − disbursements = COH_COP) holds
  for 9,300 of 10,126 numeric `webk` rows (91.8%) and 1,993 of 2,378
  `webl` rows (83.8%) — it is a **layout check evaluated in aggregate**
  (hold rate ≥ 80% + the two API-verified exact matches), not a
  per-row gate. The remaining rows fail because the FEC's own summaries
  do not reconcile exactly for some committees (amended filings,
  non-federal accounts, negative cash) — a data feature, recorded with
  the hold rate and median/max difference in `data_source.json`, never
  a reason to reject the file. A hold rate below 80% WOULD fail the
  build (it would mean the column layout is wrong).
- **Blank-money committees (§3.2, amendment item 15):** 2,253 of 12,379
  `webk` rows have blank money fields and blank coverage dates
  (registered committees that filed no financial summary — mostly
  administratively terminated / terminated / quarterly filers with no
  summary). The plan's rule 3 (drop unparseable coverage dates, counted)
  removes them; the pipeline counts them as "no financial summary filed".
  The "expected 0" in the original rule was wrong — the actual count
  governs.
- **Candidate committees are largely absent from `webk24` (§3.1,
  amendment item 16):** only 179 of 12,379 `webk` rows are candidate
  committees (H/S/P), and only 18 of the 3,644 distinct 2024 principal
  committee IDs appear in the file at all (verified: Peltola's PCC
  C00812388, Carl's C00697789, Harris Victory Fund C00703975 are all
  absent). The committee tables therefore cover the non-candidate
  committees present in the file (PACs, super PACs, party committees,
  IE groups) — candidate money is analysed from the API candidate
  totals, exactly as the amended §2.0 prescribes. The README discloses
  this. The linkage file (`ccl24`, 8,619 rows) is likewise mostly
  unmatched to `webk` (only 373 committees present) and stays an audit
  artefact only.
- **API list endpoint overstates multi-committee candidates (§2.0/§3.3,
  amendment item 17):** the `/candidates/totals/` LIST endpoint returns
  5,321 rows for 4,294 unique candidates (755 candidates appear 2–3
  times as exact duplicates — dedup keeps the first) and, for 95
  candidates (4.1% of the 2,296 present in both sources — mostly
  Senate/Presidential with joint fundraising), its receipts,
  disbursements and itemized figures EXCEED the filed candidate summary
  (max $64.7M; Sanders $36.3M vs $8.2M filed). The single-candidate
  endpoint agrees with the `webl` bulk file exactly for all 5 candidates
  checked (Peltola, Begich, Biden, Sanders, Cruz). **The pipeline
  therefore takes receipts/disbursements/individual contributions from
  `webl` where the candidate is present (2,296 candidates) and the API
  list values only otherwise (flagged `receipts_source`), and derives
  unitemized as individual − itemized only where the split is valid
  (2,259 candidates; 37 excluded where the list itemized exceeds the
  filed individual total).** The list-vs-webl max differences are
  recorded in `data_source.json`, and the README discloses the rule.
  The 82 candidates present in `webl` but absent from the API totals
  are added to the candidate table with `has_totals = True` from the
  bulk file. Funding-mix sums in `party_office.csv` cover the split
  subset only (`n_with_split`, `receipts_with_split`).
- **Biden/Harris shared-committee overlap (amendment item 18):** both
  candidates list the same principal committee (C00703975, Harris
  Victory Fund) and the FEC reports nearly identical totals for both
  (~$1.175B each after the `webl` override). The candidate-receipts
  total therefore counts their shared ~$1.18B twice. The README,
  insights and dashboard disclose this prominently; the rows are kept
  (they are distinct candidates with distinct FEC totals) and never
  netted.
- **Single-filing anomalies dominate cash and disbursements (amendment
  item 19):** the candidate cash-on-hand total ($1.373B) is 56.5%
  one filing — Norris P40010415, $775,779,979 on $35.43M receipts and
  $121.23M disbursements, whose filing fails the cash-identity check
  (BOP $0 + $35.43M − $121.23M ≠ $775.78M) and reports negative
  unitemized contributions (−$1.4M). The single-candidate API
  endpoint confirms the FEC itself reports these figures, so the
  pipeline reports them as filed and never alters them — but the
  README/insights lead with the ex-Norris cash total ($597.69M) and
  name the filing. Gambert P40010522 disbursed $220.50M on $0
  receipts (also identity-failing). The pipeline records both in
  `data_source.json` (`cash_concentration`, computed, not hard-coded).
  Candidates whose state code is `00`/`US` (no usable state on file,
  all presidential — 64 with totals: 39 coded `00`, 25 coded `US`)
  are excluded from
  `state_totals.csv` (`state_table` in `data_source.json`); their
  money stays in the candidate totals. The api-list-only exposure is
  negligible: the 1,998 candidates not covered by `webl` max out at
  $15,192.65 in receipts.
- **Committee cycle totals = the committee table (amendment item 20):**
  the 12 principal committees present in `webk` (candidate committees,
  $524.8M of receipts) are excluded from `committees.csv` by design
  (their money is already inside the candidate totals), so
  `cycle_totals.committee_*` is computed from the committee table
  (10,102 committees, $22,724.6M receipts), not from all `webk` rows
  ($23,249.4M). The excluded principal dollars are recorded in
  `cycle_totals.principal_committees_receipts_usd` so the two
  universes still reconcile.
- **2023-election-year candidates with 2024-cycle totals (amendment
  item 22):** 79 candidates in the API totals have a master record
  with `CAND_ELECTION_YR` 2023 (e.g. special-election candidates such
  as Regunberg H4RI01216), so the 2024-only master join leaves their
  name/state/district blank. The pipeline takes the name and state
  from the API totals as fallbacks (never a blank) and fills the
  principal committee from the linkage file (`ccl`, designation P —
  72 candidates). `has_master` is defined by the cn match
  (`office_cn` not null), not by the API party — the earlier
  definition wrongly marked these 79 as matched. The 79 add $4.5M of
  receipts to the state table once their API states are used.
- **`committee_type_full` dropped from `committees.csv` (amendment
  item 21):** the repeated long label pushed the file to 1,039,323
  bytes, over the 1 MB/file rule. The label is dropped from the
  committed file only (the mapping stays in `data_source.json` and
  the label is re-derived in `derive_tables` for
  `top_committees.csv`), bringing the file to ~630 KB.
