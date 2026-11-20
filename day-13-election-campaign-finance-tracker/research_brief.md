# Day 13 — Election Campaign Finance Tracker: Research Brief

**Status:** VERIFIED — one lean probe pass completed 2026-11-19 (researcher, stage 1).
**Business question:** Where did the money in the 2024 US federal election cycle come from, who spent it, and how do contributions and spending differ across candidates, parties, offices and states — presented nonpartisanly, with every number traceable to its FEC filing?

## 1. Data source — verified from scratch

**Source:** U.S. Federal Election Commission (FEC), 2024 two-year cycle (2023-01-01 → 2024-12-31).
Primary path is the FEC **bulk downloads** (no key, no rate limit, full coverage). The
openFEC API is the cross-check path only. No api.data.gov key exists in this workspace
(only `custom.elevenlabs` and `custom.youtube` connectors are present; no FEC connector,
no `FEC_API_KEY` in the environment) — the build must not depend on a key.

### 1a. Bulk downloads (PRIMARY — verified 2026-11-19, HEAD requests)

Base: `https://www.fec.gov/files/bulk-downloads/2024/`

| File | HEAD result | Size | Contents (per FEC file descriptions) |
|---|---|---|---|
| `cn24.zip` | HTTP 200 | 356,337 bytes | Candidate master: one row per candidate — candidate ID, name, party, office, state, district, election year |
| `webk24.zip` | HTTP 200 | 469,667 bytes | Committee summary (Form 3/3X/3P summary): one row per committee — total receipts, total disbursements, cash on hand, debts, itemized/unitemized contribution splits |
| `ccl24.zip` | HTTP 200 | 94,262 bytes | Candidate–committee linkage: which committees belong to which candidate |

Total of the three zips: **~920 KB** — inside the 1 MB/file and 5 MB/day rules, so all three
are committed as the raw provenance record. Each zip unpacks to a pipe-delimited `.txt`
with a header row; the coder must verify the header at build time and fail loudly if an
expected money column is absent (see §1c fallback).

Files deliberately NOT used (verified too large for this day's rules):
- `oth24.zip` — 505,095,990 bytes (~505 MB), contributions from other committees. Out of scope.
- `pas224.zip` — 24,509,782 bytes, committee-to-committee Schedule A. Out of scope.
- Individual-contributions bulk file (`indiv24.zip`, GB-scale, not HEAD-probed — known
  GB-scale from FEC documentation): **not fetched**. Donor-level analysis is therefore
  limited to the aggregates the summary files carry (itemized vs unitemized, per candidate
  and per committee). This is a disclosed coverage limit, not a gap to work around by
  sampling Schedule A through the rate-limited API.

### 1b. openFEC API (CROSS-CHECK ONLY — verified 2026-11-19, `api_key=DEMO_KEY`)

Base: `https://api.open.fec.gov/v1`. `DEMO_KEY` is the public demo key; it works but is
rate-limited: response headers show `X-Ratelimit-Limit: 10`, `X-Ratelimit-Remaining: 9`
on every probe call (a 10-requests-per-minute bucket; the documented DEMO_KEY allowance
is 30 requests/hour). **Design rule: at most ~10 API calls in the whole build, spaced
≥ 6 s apart, with one retry after 60 s on 429.** A free personal key (api.data.gov/signup)
would raise the limit to 1,000/hour, but no key is available and the build must not wait
for one — the bulk files are the primary path precisely so the API is never load-bearing.

| Endpoint | Probe result |
|---|---|
| `GET /candidates/?cycle=2024&per_page=1` | HTTP 200; `pagination.count` = **9,796** candidates in cycle 2024 |
| `GET /candidates/totals/?cycle=2024&per_page=2&sort=-receipts` | HTTP 200; `pagination.count` = **5,321** candidates with totals. Top row: candidate `P80000722`, disbursements **$1,185,795,517.32**, coverage 2021-01-01 → 2024-12-31, address Philadelphia PA |
| `GET /candidate/P40009458/totals/?cycle=2024` | HTTP 200; full totals object (contributions, individual_itemized/unitemized_contributions, disbursements, cash on hand, debts, loans). Candidate `P40009458` (ZORC, TONY): contributions $560.00, disbursements $61,078.01 |
| `GET /candidate/P80000722/committees/?cycle=2024` | HTTP 200; `pagination.count` = 1; first row committee `C00703975` "HARRIS VICTORY FUND", type `N` (PAC — Nonqualified) |
| `GET /committees/?cycle=2024&sort=-total_receipts` | HTTP **422** — `total_receipts` is NOT a sortable field on `/committees/`. Do not use it. |
| `GET /committees/totals/?cycle=2024` | HTTP **404** — this endpoint does not exist. Committee totals must come from the bulk `webk24.zip` or per-committee `/committee/{id}/totals/` (too many calls — do not use). |
| `GET /candidate/H8CA05098/totals/?cycle=2024` | HTTP 200, `count: 0` — the invented ID returns empty, as expected; proves the endpoint answers honestly rather than erroring |
| `GET /schedules/schedule_a/?committee_id=C00431445&two_year_transaction_period=2024` | HTTP 200, `count: 0` — the invented committee ID returns empty; endpoint shape confirmed but **not used** (see donor limit above) |

**Cross-check the coder must run (one API call, not a fetch):** after building the
candidate table from bulk, compare the bulk-derived top candidate by receipts against
`/candidates/totals/?cycle=2024&per_page=1&sort=-receipts` — the candidate ID and the
receipts figure must agree within rounding ($1 tolerance for float formatting). The
probe already establishes the top row is `P80000722` with disbursements $1,185,795,517.32.

### 1c. Fallback if a bulk header is wrong

If `webk24.zip` does not contain the expected money columns (total receipts /
disbursements / cash on hand), the coder falls back to the API candidate totals:
`GET /candidates/totals/?cycle=2024&per_page=100&sort=-receipts`, paginating through
5,321 rows (~54 pages) at ≤ 10 calls/minute with 6 s spacing and one 60 s retry on 429
(~6 minutes total). Record which path was used in `data_source.json`. The fallback is
documented here so the coder does not have to re-discover the pagination math.

### 1d. What was NOT available — recorded, not silently dropped

- **Census ACS state populations (for per-capita normalisation):** `GET
  https://api.census.gov/data/2023/acs/acs5?get=NAME,B01003_001E&for=state:*` returns
  HTTP 200 with an HTML page titled **"Missing Key"** — the Census API now requires a
  key for this call and none is available. **Per-capita figures are out of scope for
  Day 13.** State comparisons use totals and shares only, and the README/insights must
  say plainly that state totals are not population-adjusted.
- **2026 cycle:** in progress, partial coverage. The analysis cycle is **2024 only**
  (complete, certified cycle). Do not mix 2026 rows in.

## 2. Metric definitions — exact

All money figures are **reported dollars as filed with the FEC** (nominal USD, no
inflation adjustment — a single two-year cycle, so none is needed). Never annualise,
never impute, never net receipts against disbursements.

- **Total receipts** (per candidate or committee, cycle 2024) = all money taken in as
  reported on the summary filing (`webk` total-receipts column; API field `receipts`).
- **Total disbursements** = all money spent (`webk` total-disbursements column; API
  field `disbursements`).
- **Cash on hand (end of period)** = ending cash balance (`cash_on_hand_end_period`).
- **Individual contributions** = money from individuals; split into **itemized**
  (donors who gave > $200 in the cycle and are named in filings) and **unitemized**
  (small-dollar, ≤ $200, reported only in aggregate). API fields:
  `individual_itemized_contributions`, `individual_unitemized_contributions`.
- **Small-dollar share** = unitemized individual contributions ÷ total individual
  contributions. A funding-mix descriptor only — never read it as a headcount of donors.
- **Other receipts** = receipts − individual contributions (PAC contributions, party
  transfers, candidate loans, other). Report as a residual, labelled as such.
- **Burn rate** = disbursements ÷ receipts. Purely descriptive (how much of what came in
  went out); > 1 is possible and normal for candidates spending down prior-cycle cash.
- **Party share** = a party's candidates' receipts ÷ all candidates' receipts (same
  office or same cycle). Parties compared symmetrically: DEM, REP, LIB, GRN, IND/other
  all shown with the same columns; no party is the reference group.
- **Top-N concentration** = share of total receipts held by the top 5 / top 10 candidates
  (or committees). A concentration fact, not a judgement.
- **Coverage** = `coverage_start_date` → `coverage_end_date` on the totals record;
  the 2024-cycle totals cover 2021-01-01 → 2024-12-31 for most presidential candidates
  (the cycle spans the two calendar years before the election year for filing purposes).

### Nonpartisan interpretation rules (binding on every surface)

1. All candidates and parties are presented with the **same metrics, same charts, same
   table columns**. No candidate or party is singled out for praise or criticism.
2. No causal claims: never "money caused the win / loss". The data has no outcome
   variable in scope and the brief forbids adding one.
3. No editorial adjectives about amounts ("obscene", "modest", "war chest") — report the
   number, the share, and the rank.
4. Every chart and table states its coverage (cycle 2024, candidates with totals = 5,321
   of 9,796 filed candidates) and its source link (fec.gov bulk file or openFEC endpoint).
5. "Top" always means top by the stated metric, with the metric named in the title.

## 3. Licence / attribution

- FEC data is a work of the United States federal government and is in the **public
  domain** (no licence restriction). Attribution to include in README + data/README.md:
  "Source: U.S. Federal Election Commission, 2024 cycle bulk data
  (https://www.fec.gov/data/browse-data/?tab=bulk-data) and openFEC API
  (https://api.open.fec.gov/v1). Retrieved 2026-11-19."
- No personal data beyond what the FEC itself publishes: candidate and committee names
  are public officials/committees. Individual donor names are NOT in this build (no
  Schedule A fetch), so no donor PII is handled at all.

## 4. Synthetic-fallback note (only if all three bulk files fail)

- Labelled synthetic, seed 42, `synthetic: true` in `data_source.json` (per AGENTS.md
  data rule); never overwrite a real download.
- Generate ~5,300 candidates / ~14,000 committees mimicking the real schema and
  marginals: party mix DEM ~35% / REP ~35% / other ~30% of filed candidates; office
  mix H ~75% / S ~10% / P ~1% / other ~14%; receipts log-normal with a long right tail
  (median ~$50k, top ~$1.2B); itemized share 40–90%; cash on hand ≥ 0; coverage dates
  inside 2023-01-01 → 2024-12-31. Then run the identical pipeline so the fallback
  exercises the same code path.
- Fallback is a last resort: the live sources verified healthy in this pass (all three
  bulk HEADs HTTP 200, API HTTP 200), so the coder should expect the real download to work.

## 5. Verification status

- [x] Bulk endpoints confirmed against the official source (HEAD 200 + byte sizes for
      cn24/webk24/ccl24; oth24/pas224 sizes recorded as out-of-scope)
- [x] API endpoints confirmed (candidates 9,796; candidate totals 5,321; top candidate
      P80000722, disbursements $1,185,795,517.32; linkage endpoint; 422/404 negative
      results recorded so the coder does not retry them)
- [x] Rate limits recorded (DEMO_KEY 10/min bucket; ≤ 10 calls total in the build)
- [x] No api.data.gov key available in the workspace (connectors checked: only
      custom.elevenlabs and custom.youtube; no FEC_API_KEY in environment)
- [x] Census per-capita path verified unavailable without a key ("Missing Key" page) —
      per-capita out of scope, recorded in §1d
- [x] Metric definitions + nonpartisan rules recorded exactly (§2)
- [x] Licence / attribution recorded (§3)
- [x] No probe copy retained — HEAD-only probes plus tiny JSON responses; nothing
      written to data/raw/ or data/processed/
- [ ] Unverified — for the coder to measure, not assumed here: exact row counts of the
      three unpacked bulk files; exact column names of webk24 (header verification);
      final candidate/committee counts after cleaning; top-10 receipts figures;
      small-dollar shares by party/office
