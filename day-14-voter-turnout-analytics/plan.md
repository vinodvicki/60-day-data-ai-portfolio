# Day 14 — Voter Turnout Analytics: Build Plan

**Status:** PLAN — planner sign-off complete (AGENTS.md, stage 2).
**Source of truth:** `research_brief.md` (2026-11-21) + this plan. **If brief
and plan disagree, the plan wins and the difference is noted in §11.** The
coder must reuse the brief + this plan. **No extra web searches.**
**Roadmap entry (verbatim):** "Compare turnout by geography and public
demographic indicators without implying causal relationships. GitHub
deliverable: Turnout map and evidence-limited insights memo."
**Victor's decisions (voice call 2026-11-20, non-negotiable):** descriptive
ONLY — **NO predictive model**. Turnout map + evidence-limited insights
memo, no causal claims. Outliers screened during skewness screening —
reported as found, never dropped silently.

> **SCAFFOLD NOTE (planner stage, 2026-11-21 — see §5).**
> `python agents/orchestrator.py --day 14 --slug voter-turnout-analytics
> scaffold` **refused** (exit 1) because the day folder already existed
> with `research_brief.md` in it — the orchestrator never overwrites an
> existing folder. The slug is correct (no double prefix:
> `day-14-voter-turnout-analytics`, not `day-14-day-14-…`). The planner
> replicated the scaffold template by hand instead: `LICENSE`,
> `.gitignore`, `requirements.txt`, `.pre-commit-config.yaml`,
> `src/requirements.txt` copied verbatim from the Day 1 template;
> `pyproject.toml` copied from Day 13 (strict-by-default scaffold
> config); `src/__init__.py`, placeholder `README.md`,
> `data/README.md`, `outputs/insights_summary.md`,
> `notebooks/analysis.ipynb`, `tests/test_smoke.py` written as the
> scaffold writes them; `REQUIRED_DIRS` created. `research_brief.md`
> was **not** touched. The coder fills in the placeholders per §5/§6 —
> no scaffold step remains.

| Item | Value |
|---|---|
| Fetch date | 2026-11-21 |
| Source | University of Florida Election Lab (Michael McDonald), general-election turnout rates 1980–2024 — `Turnout_1980_2022_v1.2.csv` (116,830 B) + `Turnout_2024G_v0.4.csv` (8,378 B), both HEAD 200 on 2026-11-21; EAVS 2024 V1 zip as cross-check only; Census cartographic boundary file `cb_2024_us_state_500k.zip` for map geometry |
| Expected rows | ~51 jurisdictions × 23 elections (1980–2024 biennial) — coder confirms exact row counts after concatenation |
| Date range | General elections 1980–2024 (biennial); no 2026 rows |
| Deliverable | Turnout map (state choropleth, 2024 VEP turnout) + evidence-limited insights memo — descriptive only, no model, no causal claims |
| Scope | Descriptive analysis of state-level voter turnout by geography and over time, with demographic indicators from inside the UF files shown as associations only. **No predictive model, no county map, no ACS/Census API demographics, no causal claims, no party variable** (brief §1d, §2). |

## 1. Problem statement + audience

**Problem.** US voter turnout differs sharply by state and by election type —
in 2024 the national voting-eligible-population (VEP) turnout was 64.30%,
while in the 2022 midterm it was 46.12% — but the figures a reader finds
online mix three different denominators (voting-eligible, voting-age, and
registered voters), compare presidential years against midterms as if they
were one trend, and sometimes present a state's rate without saying what
it is a rate *of*. This project does the comparison once, in the open:
one authoritative denominator (VEP, from the UF Election Lab), like-with-like
comparisons within cycle type only, a state choropleth for 2024, a
1980–2024 time series split by cycle type, a ranked state table, and the
demographic indicators the files themselves carry shown next to turnout as
associations — with the source, the denominator, and the coverage limits
stated on every surface.

**Five hard limits are stated up front and labelled on every surface
(README, notebook, insights, dashboard, charts, tables):**

1. **Descriptive only — no predictive model.** Nothing in this build
   forecasts a future election or estimates what turnout "would have
   been". No regression model, no classifier, no fitted line presented
   as a prediction. Correlations are reported as associations (§2.0).
2. **State level only — no county map.** No verified no-key source gives
   a county-level denominator (brief §1d: MIT county file is
   guestbook-blocked and carries votes only, no denominator; Census API
   is key-blocked). A county "turnout rate" built on total county
   population would be a different, misleading metric. The map is a
   **state choropleth** (50 states + DC).
3. **VEP is the primary metric; VAP and registered-voter turnout are
   never mixed with it.** VAP turnout is reported alongside, never as a
   substitute, never averaged with VEP (§4.1). EAVS registered-voter
   figures are a cross-check on the numerator only (§2.0).
4. **Compare only within cycle type.** Presidential years are compared
   with presidential years, midterms with midterms. A
   presidential-to-midterm change is labelled a "cycle-type change",
   not a trend (§2.0).
5. **No causal claims, no party variable, no editorial adjectives.**
   The data contains no party variable and none is added. No state is
   described as "abysmal" or "impressive" — the number, the rank, and
   the percentage-point change are reported (§2, brief §2).

**Audience / decision-maker.** A nonpartisan reader (citizen, student,
journalist) who wants to know where turnout is higher or lower, how it
has moved over time, and which demographic indicators move with it — and
a data reviewer checking the method, who wants a documented denominator
(VEP), counted exclusions, a recomputation cross-check against the file's
own rates, an EAVS cross-check on the 2024 numerator, and every published
number matching the committed CSVs.

## 2. Decisions (frozen)

### 2.0 THE DECIDER RULES — first decisions, non-negotiable

These four rules settle every judgement call in this build. If any later
choice conflicts with one of them, the rule wins.

- **RULE 1 — VEP from UF is authoritative; EAVS is a cross-check only,
  never an override.** The primary metric is VEP turnout recomputed
  from the UF files (`TOTAL_BALLOTS_COUNTED ÷ VEP × 100`, §4.1). If the
  EAVS cross-check (§3.3) disagrees with a UF numerator, the UF figure
  stands and the disagreement is recorded in `data_source.json` and
  disclosed in the insights memo — the pipeline never overwrites a UF
  figure with an EAVS figure, never averages the two, and never plots
  an EAVS-derived rate on the same axis as a VEP rate. The EAVS
  registered-voter denominator differs from VEP by construction
  (registration is a subset of eligibility), so the two rates are
  different metrics, not two estimates of one metric.
- **RULE 2 — Demographic associations are descriptive only.** Every
  association between a demographic indicator and turnout is reported
  as a Pearson **and** Spearman correlation with **n, r, and p**
  (§4.3), computed on 2024 state-level data (and, where stated,
  separately within a cycle type — never pooled across cycle types
  without labelling the pool). Allowed language: "moves with",
  "associated with", "higher/lower than". Forbidden language: "causes",
  "drives", "explains", "because of", and any fitted/predictive
  reading of a correlation. A correlation is never presented without
  its n and p, and never without the sentence that correlation is not
  causation. No regression model is fitted — a scatter with a
  correlation coefficient is the whole analysis.
- **RULE 3 — Outlier rule (Victor's instruction).** During skewness
  screening, flag states with VEP turnout outside the 1.5×IQR fence
  **or** with |z| > 3 **within their cycle type**, and list every
  flagged state in the memo with its value (§4.4). **Flagged rows stay
  in every chart and table.** Nothing is dropped, winsorised or
  imputed without a written note in the memo naming the rows and the
  reason — and no such dropping is planned: missing values (pre-2010
  state ballots) stay missing, never filled. Skewness itself is
  reported per cycle type (a number, not a judgement).
- **RULE 4 — Cycle-type comparison rule.** `cycle_type` =
  `presidential` if `YEAR % 4 == 0`, else `midterm`. Every time-series
  chart and table splits or colours by cycle type. Change over time is
  reported in percentage points (pp) **within** a cycle type only
  (presidential vs previous presidential, 4-year gap; midterm vs
  previous midterm). A presidential-to-midterm change is labelled
  "cycle-type change" wherever it appears, never a trend, and no
  single trend line is drawn through alternating cycle types.

- **Tester gate (mandatory):** the tester verifies the rules were
  actually used — a test asserts the recomputed VEP turnout matches
  the file's `VEP_TURNOUT_RATE` within 0.05 pp on every row (§3.3); a
  test asserts no EAVS figure appears in any committed turnout table;
  a test asserts every outlier-flagged state in `outliers.csv` is
  still present in `turnout_long.csv` and in the 2024 ranking; a test
  asserts no chart or table mixes cycle types without labelling them.
  If any rule is violated, the build fails.

### 2.1 Research questions (exactly 3)

1. **How does turnout differ across states, and how has each state
   changed since the last same-cycle election?** 2024 VEP turnout by
   state (map + ranking), top/bottom states, and the pp change since
   2020 (presidential) and since 2022 where the comparison is
   like-with-like (§4.2).
2. **How has turnout moved over time, 1980–2024?** National VEP (and
   VAP) turnout by year, split by cycle type — presidential and
   midterm series shown separately, with pre-2010 national figures
   labelled "estimated" (§4.2).
3. **Which demographic indicators move with turnout?** State-level
   associations (2024) between VEP turnout and the indicators inside
   the UF files — noncitizen share, ineligible-felon share, overseas
   eligible share — reported as Pearson/Spearman correlations with n,
   r and p, descriptive only (§4.3).

### 2.2 Other frozen decisions

- **Analysis covers 1980–2024 only.** No 2026 rows, even though a
  2026 general election has not occurred (brief §1d).
- **Column 5 is parsed by content, never by header** (brief §1c.1):
  URL → `SOURCE_URL`, digits → `VOTE_FOR_HIGHEST_OFFICE`, blank →
  missing. Never parse a URL as a vote count, never treat a missing
  vote count as zero. Analyses needing `VOTE_FOR_HIGHEST_OFFICE`
  exclude 2020/2022/2024 rows and say so.
- **2024 file has no YEAR column.** Add `YEAR=2024` when concatenating
  (brief §1c.2). `VOTE_FOR_HIGHEST_OFFICE` is missing for 2024 — no
  analysis in this build needs it, so nothing is filled.
- **Pre-2010 state ballots stay null; national pre-2010 VEP turnout is
  labelled "estimated"** in every chart, table and memo sentence that
  uses it (brief §1c.3). Rounded estimates in the file (e.g. 2020
  Wisconsin 3,310,000 ballots) are reported as filed, never
  "corrected".
- **No ACS / Census API demographics.** Key-blocked (brief §1d,
  re-verified 2026-11-21). Demographic indicators come only from
  inside the UF files. The CPS supplement is context only and is not
  cited as 2024 (brief §1d — p20-585 is November 2020).
- **No Power BI file:** no `.pbix` is produced (same decision as
  Days 8–13 — a `.pbix` cannot be built or verified in this
  environment); the turnout map is delivered as the Streamlit app +
  static charts. The SQL skill is covered by the §4.5 check.
- **Geography is the Census cartographic boundary file, not Plotly
  geo.** Day 13 dropped mapping because Plotly geo needs a CDN
  topojson that fails in this environment; this day's choropleth is
  drawn with **geopandas + matplotlib from the downloaded shapefile**
  (§3.1), fully offline. No CDN, no tile server, no web map.

## 3. Data — source, endpoints, fetch rules, provenance, licence

### 3.1 Source and download (verified, from the brief — copy, do not re-search)

- **Source:** University of Florida Election Lab, Michael McDonald —
  general-election turnout rates. Documentation hub:
  `https://election.lab.ufl.edu/voter-turnout/`.
- **Download — PRIMARY (verified 2026-11-21, HEAD 200 + ranged GET 206):**
  - `Turnout_1980_2022_v1.2.csv` — **116,830 bytes** —
    `https://election.lab.ufl.edu/data-downloads/turnoutdata/Turnout_1980_2022_v1.2.csv`
  - `Turnout_2024G_v0.4.csv` — **8,378 bytes** —
    `https://election.lab.ufl.edu/data-downloads/turnoutdata/Turnout_2024G_v0.4.csv`
  Total **~125 KB**. No key, no login, no rate limit. One download of
  each file per build; cache under `data/raw/` and re-use it
  (`--offline` / `--use-cache` per the Day 1 pattern). The 2024 file is
  version **0.4 — preliminary**; the memo says so wherever 2024
  figures appear.
- **Documentation files (verified HEAD 200, coder reads both in full at
  build time):** `Turnout_1980_2022_v1.2_doc.txt` (9,877 bytes, v1.2,
  dated 10/8/2024) and `Turnout_2024G_v0.4_doc.txt` (v0.4, dated
  3/2/2026). Both state the licence and the VAP/VEP construction.
  They are downloaded at build time for reference and are **not**
  committed (they are documentation, not data); their versions and
  dates are recorded in `data_source.json`.
- **File format:** comma-separated CSV, one row per state per election
  (50 states + DC + a "United States" total row). Verified columns
  (1980–2022 file): `YEAR, STATE, STATE_ABV, TOTAL_BALLOTS_COUNTED,
  VOTE_FOR_HIGHEST_OFFICE, VAP, NONCITIZEN_PCT, INELIGIBLE_PRISON,
  INELIGIBLE_PROBATION, INELIGIBLE_PAROLE, INELIGIBLE_FELONS_TOTAL,
  ELIGIBLE_OVERSEAS, VEP, VEP_TURNOUT_RATE, VAP_TURNOUT_RATE`.
  Verified columns (2024 file): same list **minus** `YEAR` and
  `VOTE_FOR_HIGHEST_OFFICE`, with the 5th column header **blank**
  (holds source URLs — §1c.1). See §3.2 for the parsing rules.
- **Geography — Census cartographic boundary file (verified 2026-11-21,
  HEAD 200):** `cb_2024_us_state_500k.zip` — **3,242,450 bytes** —
  `https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_500k.zip`.
  Over the 1 MB/file rule: **download at build time, gitignore, do not
  commit** (§3.4). Join on state FIPS (`STATEFP`) / postal abbreviation.
  County boundaries are **not used** (§1 limits).
- **EAVS 2024 — CROSS-CHECK ONLY (verified 2026-11-21, HEAD 200):**
  `2024_EAVS_for_Public_Release_nolabel_V1_csv.zip` — **2,076,499
  bytes** —
  `https://www.eac.gov/sites/default/files/2025-06/2024_EAVS_for_Public_Release_nolabel_V1_csv.zip`.
  Over the 1 MB/file rule: **download at build time, gitignore, do not
  commit** (§3.4). A V2 release dated 2026-02-12 is reported by a
  third-party reproducibility guide only — the coder checks the EAC's
  own index page
  (`https://www.eac.gov/research-and-data/datasets-codebooks-and-surveys`)
  for the newest official release and uses V2 if it is linked there,
  otherwise the pinned V1 URL above. Whichever version is used is
  recorded in `data_source.json`.
- **Coverage (from the brief's probe, to be confirmed from the files):**
  2024 United States — ballots **156,766,239**; VAP **264,798,961**;
  VEP **243,803,423**; VEP turnout **64.30%**; VAP turnout **59.20%**.
  2022 United States — ballots **112,030,874**; VEP **242,907,672**;
  VEP turnout **46.12%**. Sampled 2024 state VEP turnout (file head
  only — **not** a ranking): Colorado **73.40%**, Connecticut 67.00%,
  Alaska 63.55%, California 62.26%, Alabama 58.70%, Arkansas 54.06%.
  The coder computes the full ranking; no maximum/minimum is claimed
  here.
- **Licence / attribution:** UF Election Lab data is released under
  **Creative Commons Attribution 4.0 (CC BY 4.0)** (stated in both
  documentation files). Cite verbatim in `data/README.md`, the
  notebook and the day README:
  > Source: Michael McDonald, University of Florida Election Lab,
  > General Election Turnout Rates 1980–2022 v1.2 and 2024 General
  > Election Turnout Rates v0.4 (https://election.lab.ufl.edu/voter-turnout/),
  > CC BY 4.0. Retrieved 2026-11-21.
  EAVS data is a work of the U.S. federal government (public domain);
  if used: "Source: U.S. Election Assistance Commission, 2024 Election
  Administration and Voting Survey
  (https://www.eac.gov/research-and-data/studies-and-reports)."
  Census boundary files are U.S. federal government works (public
  domain); attribute the Census Bureau in `data/README.md`. No personal
  data is handled: all figures are state-level aggregates.

### 3.2 Cleaning rules (frozen — the tester tests these)

Applied in this order; every step's excluded-row count is recorded in
`data_source.json` and reported in `data/README.md`:

1. **Download:** one GET per file per build (`--live`); cache under
   `data/raw/`; re-use with `--use-cache`. One retry after 60 s on HTTP
   429/5xx, then stop and report — never hammer the host. Verify byte
   sizes against §3.1 (116,830 and 8,378); a size mismatch fails the
   build loudly — it is the proof the right files were fetched.
2. **Parse column 5 by content** (§2.2): read the raw 5th column as
   text; a value starting with `http` → `SOURCE_URL`; an all-digits
   value → `VOTE_FOR_HIGHEST_OFFICE`; blank → missing in both. Never
   trust the header. Record the counts of each case per file.
3. **Concatenate:** add `YEAR=2024` to the 2024 file; concatenate with
   the 1980–2022 file on the common columns. The "United States" total
   row is kept and flagged `is_national = True`; state rows are
   `is_national = False`. DC is a state row (51 jurisdictions
   including DC).
4. **Types:** parse `YEAR` as int; ballots, VAP, VEP and the
   ineligibility counts as numeric (blank → missing, never 0).
   `NONCITIZEN_PCT` is a percent as filed. Drop no rows for missing
   ballots — pre-2010 state ballots are null by design (§1c.3) and
   stay null; count nulls per year and record them.
5. **VEP reconciliation check:** for every row, recompute VEP as
   `VAP − noncitizen VAP − ineligible felons + eligible overseas`
   (noncitizen VAP = `VAP × NONCITIZEN_PCT ÷ 100`) and flag rows where
   the recomputed VEP differs from the file's `VEP` by more than
   **0.5% of the file VEP**. Record the flagged count and the max
   difference in `data_source.json`. The file's `VEP` is used
   throughout — the recomputation is a check, never a replacement.
6. **Cycle type:** `cycle_type = presidential` if `YEAR % 4 == 0`,
   else `midterm`. Derived, never read from the file.
7. **Deduplicate:** drop exact duplicate (YEAR, STATE_ABV) rows,
   keeping the first (count them; expected 0).
8. **No imputation, no winsorising, no dropping of outliers.** Missing
   stays missing; flagged outliers stay in the table (§2.0 Rule 3).
   Turnout rates are recomputed, never overwritten (see §3.3).

### 3.3 Cross-checks (frozen — run before the tester starts)

- **Recompute check (mandatory):** recompute VEP turnout from
  `TOTAL_BALLOTS_COUNTED ÷ VEP × 100` for every row and confirm it
  matches the file's `VEP_TURNOUT_RATE` within **0.05 pp** (rounding
  tolerance). Spot-checks that must pass: 2024 United States
  **64.30%** (156,766,239 ÷ 243,803,423); 2022 United States
  **46.12%**; 2024 Colorado **73.40%**; 2024 California **62.26%**;
  2024 Arkansas **54.06%**. If any recomputed rate differs by more
  than 0.05 pp, **stop and report it as a defect — do not silently
  overwrite the file's rate with the recomputed one.** Record the max
  absolute difference in `data_source.json`.
- **EAVS cross-check (sample only):** cross-check the 2024 numerator
  (ballots counted) for **two sampled states** against the EAVS 2024
  file and record any disagreement over **0.5%** in the insights memo
  and in `data_source.json`. Per §2.0 Rule 1 the UF figure stands
  regardless; EAVS never overrides and never enters a committed
  turnout table.
- **Shapefile join check:** after joining the 2024 state table to the
  Census geometry on postal abbreviation, assert all 51 jurisdictions
  (50 states + DC) joined and record any unmatched abbreviation. A
  missing jurisdiction fails the build loudly — the map must not
  silently drop a state.

### 3.4 Data-size and commit rule (READ CAREFULLY)

- The two raw UF CSVs total **~125 KB** (each < 1 MB) — inside the
  portfolio rule (files < 1 MB each, < 5 MB per day folder). Therefore
  the **raw CSVs ARE committed** as the provenance record (same rule as
  Day 1's raw JSONs).
- **`.gitignore` MUST exclude the shapefile and the EAVS zip and their
  unpacked contents:**
  `data/raw/cb_2024_us_state_500k.zip`, `data/raw/shapefile/`,
  `data/raw/2024_EAVS_for_Public_Release_nolabel_V1_csv.zip`,
  `data/raw/eavs/`, plus the standard synthetic line
  `data/raw/*_synthetic.json`. The shapefile zip (3,242,450 B) and the
  EAVS zip (2,076,499 B) are both over 1 MB; their unpacked contents
  are regenerable from the downloads.
- **`.gitignore` must NOT exclude `data/` itself** — only the lines
  above (plus the standard cache/venv lines from the scaffold). All
  processed files in §3.5 and the two UF CSVs are committed. (Day 13
  lesson: the validator flags any broad `data/` exclusion — see §8 —
  and the tester diffs `.gitignore` against this list before sign-off.)
- **The pipeline downloads the CSVs at build time** (`--live`),
  verifies the sizes in §3.1, and caches them under `data/raw/` for
  re-use (`--use-cache`). `--offline` runs from the committed CSVs +
  processed files only (no network, no shapefile/EAVS needed) and
  regenerates charts + summaries from them. If the shapefile is absent
  in an offline run, chart 01 is regenerated from the committed
  `state_2024.csv` only if the geometry is cached — otherwise the
  chart step reports "shapefile absent, chart 01 not regenerated" and
  the committed PNG stands; the offline run never writes a broken
  chart.
- **`.gitignore` otherwise follows the scaffold default:**
  `__pycache__/`, `.venv/`, `venv/`, `.env`, `*.key`, `*.log`,
  `.streamlit/secrets.toml`, `.pytest_cache/`,
  `.ipynb_checkpoints/`, plus the shapefile/EAVS/synthetic lines
  above. The tester diffs `.gitignore` against this list before sign-off.

### 3.5 Committed processed files (all < 1 MB; regenerable with one command)

| File | Contents |
|---|---|
| `data/processed/data_source.json` | Source, URLs, CSV byte sizes, fetch date, doc versions/dates, row counts (per file / concatenated / cleaned / excluded per rule / null ballots per year), column-5 parse counts, VEP reconciliation result (flagged count, max difference), recompute cross-check result (max difference, spot-checks), EAVS version + sample cross-check result, shapefile join result, cycle-type rule, metric definitions, manual validation, versions |
| `data/processed/turnout_long.csv` | One row per jurisdiction per election (~51 × 23 expected — coder confirms): `year`, `state`, `state_abv`, `is_national`, `cycle_type`, `total_ballots_counted`, `vote_for_highest_office`, `source_url`, `vap`, `noncitizen_pct`, `ineligible_felons_total`, `eligible_overseas`, `vep`, `vep_turnout_rate`, `vap_turnout_rate`, `vep_turnout_recomputed`, `felon_share_vap`, `overseas_share_vep` |
| `data/processed/national_series.csv` | One row per election year (national "United States" row only): `year`, `cycle_type`, `total_ballots_counted`, `vap`, `vep`, `vep_turnout_rate`, `vap_turnout_rate`, `vep_turnout_pp_change_same_cycle`, `national_estimated` (true for pre-2010 years, §1c.3) |
| `data/processed/state_2024.csv` | One row per jurisdiction for 2024 (51 rows + US total flagged separately): `state`, `state_abv`, `total_ballots_counted`, `vep`, `vep_turnout_rate`, `vap_turnout_rate`, `rank_vep`, `pp_change_vs_2020`, `noncitizen_pct`, `felon_share_vap`, `overseas_share_vep`, `is_outlier` |
| `data/processed/correlations.csv` | One row per (indicator × scope): `indicator`, `scope` (e.g. `2024_states`, `2024_presidential_pooled`), `n`, `pearson_r`, `pearson_p`, `spearman_r`, `spearman_p` — descriptive only, §4.3 |
| `data/processed/outliers.csv` | One row per flagged state per screening pass: `year`, `cycle_type`, `state_abv`, `vep_turnout_rate`, `rule` (`iqr` / `z`), `statistic_value` — every flagged state, reported as found (§2.0 Rule 3) |

- The committed processed CSVs are the offline-reproducible record:
  every number in the README, insights and dashboard must match them.
- **Offline rule (Day 5/6 lesson):** `--offline` must NOT clobber
  `data_source.json` fields recorded by a live run (`source: "live"`,
  counts, fetch date, cross-checks). It regenerates only the derived
  tables/charts from the committed CSVs; **a test asserts this — the
  offline run skips writing `data_source.json` entirely when a live
  record already exists.** **CI-flake lesson (Day 9, 2026-11-13):** the
  offline-reproduction test compares regenerated floats with a
  **tolerance** (absolute ≤ 0.01 on rates in pp, relative ≤ 1e-6
  elsewhere) — never byte-exact — because environment rounding flakes
  byte comparisons.

### 3.6 Fallback, licence, attribution

- **Synthetic fallback (only if both UF files fail):** per brief §4 —
  retry once after 60 s per URL, then stop and report to the
  orchestrator — **do not silently substitute synthetic data**. If a
  synthetic fallback were ever authorised, it must be built from the
  brief's documented parameters (51 jurisdictions × 23 elections,
  1980–2024 biennial; VEP turnout ~46% in midterms / ~60–66% in
  presidential years; state spread roughly ±10 pp around the national
  figure for the cycle type; VAP > VEP always; noncitizen share 2–15%;
  ineligible felons ≥ 0; overseas eligible ≥ 0; seed 42), stored as
  `data/raw/*_synthetic.csv` (git-ignored, NEVER overwrites real
  data), recorded in `data_source.json` as `synthetic: true, seed: 42`,
  and labelled "SYNTHETIC — NOT REAL DATA" in every chart, the
  notebook, and the README. Methods (§4) are unchanged. Not expected
  to be needed (both UF HEADs probed HTTP 200 with real rows).
- **Licence: CC BY 4.0 (UF Election Lab); public domain (EAVS, Census
  boundaries).** Attribution verbatim per §3.1.
- **No Power BI file:** no `.pbix` is produced (§2.2); the turnout map
  is delivered as the Streamlit app + static charts. Recorded here so
  the coder does not re-litigate it. The SQL skill is covered by the
  §4.5 check.

## 4. Analysis — definitions (from the brief, frozen; planner decisions in §11)

### 4.1 Turnout definitions (DECIDED — exact, from brief §2)

- **VEP turnout (PRIMARY metric)** = `TOTAL_BALLOTS_COUNTED ÷ VEP × 100`.
  The file's `VEP_TURNOUT_RATE` column is the lab's own computation of
  this; the coder recomputes it from the two columns and confirms
  agreement within 0.05 pp (§3.3). VEP = voting-eligible population.
- **VEP (denominator)** = `VAP − noncitizen VAP − ineligible felons
  (prison + probation + parole) + eligible overseas citizens`. The file
  carries each component, so the coder verifies the arithmetic per row
  and flags rows where it does not reconcile (§3.2 rule 5). VEP is the
  preferred denominator: it counts only people legally eligible to vote.
- **VAP turnout (secondary metric)** = `TOTAL_BALLOTS_COUNTED ÷ VAP × 100`,
  where VAP = voting-age population (resident population age 18+). VAP
  turnout is always lower than VEP turnout because VAP includes
  noncitizens and ineligible felons. Report it alongside VEP turnout,
  never as a substitute, and never average the two.
- **Registered-voter turnout (EAVS cross-check only)** = ballots cast ÷
  registered voters (EAVS). A third denominator, lower than VEP. Used
  only to cross-check the 2024 numerator for two sampled states; never
  plotted on the same axis as VEP turnout without a separate labelled
  series — and in this build it is not plotted at all.
- **Numerator** = `TOTAL_BALLOTS_COUNTED` (all ballots counted, not
  votes for a candidate). It exceeds `VOTE_FOR_HIGHEST_OFFICE`
  wherever both exist. The primary metric uses ballots counted; a
  vote-for-highest-office rate is a different metric and must be
  labelled as such if ever shown.
- **Change over time** = percentage-point (pp) change in VEP turnout.
  Compare like with like only: presidential vs previous presidential
  (4-year gap), midterm vs previous midterm. A presidential-to-midterm
  change must be labelled "cycle-type change", not a trend.
- **Cycle type** = `presidential` if `YEAR % 4 == 0`, else `midterm`.
  Every time-series chart and table splits or colours by cycle type.
- **Demographic indicators (descriptive only):**
  `NONCITIZEN_PCT` (noncitizen share of VAP), ineligible-felon share
  of VAP (`INELIGIBLE_FELONS_TOTAL ÷ VAP`), overseas eligible share
  (`ELIGIBLE_OVERSEAS ÷ VEP`). Shown as state-level context next to
  turnout (scatter / ranked table), with the memo stating the
  association only — see §2.0 Rule 2.

### 4.2 Geography and time (DECIDED)

- **State ranking 2024** (`state_2024.csv`): all 51 jurisdictions
  ranked by 2024 VEP turnout, rank 1 = highest. "Top/bottom" always
  means top/bottom by the stated metric, with the metric and year
  named in the title (brief §2 rule 5). The US total row is shown
  separately, never ranked among states.
- **Change since last same-cycle election:** for each state,
  `pp_change_vs_2020` = 2024 VEP turnout − 2020 VEP turnout (both
  presidential). Where 2020 is missing for a state, the change is
  blank and the state is counted as "no prior-cycle value", never
  filled. The national series carries the same-cycle pp change for
  every year (§3.5).
- **National time series** (`national_series.csv`): the "United States"
  row per year, presidential and midterm series plotted as two
  separate series (different markers/colours, no connecting line
  across cycle types). Pre-2010 points are labelled "estimated" on the
  chart and in the table.
- **Map scope:** 50 states + DC. The choropleth colours states by 2024
  VEP turnout on a single sequential scale with the numeric range
  stated in the legend; Alaska and Hawaii are shown in standard inset
  positions (documented in the chart footnote), not dropped and not
  left at true scale where they would be unreadable.

### 4.3 Demographic associations (DECIDED — descriptive only)

- For each indicator (§4.1) compute, on the 2024 state rows (n = 51,
  DC included; US total excluded): **Pearson r + p** and **Spearman
  ρ + p**, recorded in `correlations.csv` with n. A second scope,
  `2024_presidential_pooled`, is NOT computed — 2024 is a single
  presidential year, so one scope suffices; the plan fixes the scope
  list to `2024_states` only (see §11).
- **Interpretation rule:** report r, n and p together, in the same
  sentence or table row, followed by the association-only sentence
  ("This association does not show that [indicator] caused turnout to
  change."). No p-value is reported without its n; no correlation is
  plotted without its r, n and p annotated on the chart. A non-significant
  result is reported as "no clear association in these data", never
  hidden.
- **No model:** no regression line is fitted as a prediction. Chart 04
  may show a scatter with the correlation annotated; if a trend line is
  drawn for visual reference it is labelled "descriptive fit, not a
  model" and is never used to predict any state's turnout.

### 4.4 Skewness screening and outliers (DECIDED — Victor's instruction)

- Compute skewness of VEP turnout **within each cycle type**
  (presidential years pooled, midterm years pooled — labelled as
  pooled, never mixed into one number) and report both values in the
  notebook and `data_source.json`.
- Flag states per §2.0 Rule 3 (1.5×IQR fence or |z| > 3 within cycle
  type) for the 2024 presidential year and for the pooled presidential
  series; record every flagged state in `outliers.csv` and list them in
  the memo with their values. Flagged rows stay in every chart and
  table. The memo states the screening method, the fence values, and
  the count of flagged states — including zero, if none are flagged.

### 4.5 SQL check (roadmap core skill — small, honest)

The notebook answers one question twice — once in pandas, once in SQL —
on the committed `turnout_long.csv` loaded into an in-memory SQLite
database (`sqlite3`, stdlib): average VEP turnout by cycle type, and the
top state by 2024 VEP turnout, asserted equal to the pandas result. A
test asserts the SQL and pandas numbers agree. This is the day's SQL
element; no `.pbix` is built (§3.6) and the pipeline itself stays pandas.

### 4.6 Insights structure (DECIDED)

`outputs/insights_summary.md` carries one finding per §2.1 question with
exact numbers, the top-10 / bottom-10 state tables, the correlation
table (r, n, p), the outlier list, and limitations (descriptive only,
no model; state level only; 2024 figures are the lab's preliminary v0.4
release; pre-2010 national figures estimated; VAP vs VEP vs
registered-voter denominators never mixed; EAVS cross-check only, UF
authoritative). No finding without a number; no recommendation beyond
"what the data shows" — this is a transparency project, not an advice
product, and the insights say so.

## 5. File tree (exact — build only this)

```
day-14-voter-turnout-analytics/
├── README.md  requirements.txt  .gitignore  pyproject.toml  LICENSE
├── .pre-commit-config.yaml
├── research_brief.md  plan.md  coder_handoff.md  test_report.md
├── optimizer_handoff.md  publisher_handoff.md
├── data/
│   ├── README.md
│   ├── raw/
│   │   ├── Turnout_1980_2022_v1.2.csv   (116,830 B, committed)
│   │   └── Turnout_2024G_v0.4.csv       (8,378 B, committed)
│   └── processed/
│       ├── data_source.json
│       ├── turnout_long.csv    (~51 × 23 rows, one per jurisdiction per election)
│       ├── national_series.csv (one row per election year)
│       ├── state_2024.csv      (51 rows + US total flagged separately)
│       ├── correlations.csv    (one row per indicator)
│       └── outliers.csv        (one row per flagged state)
├── notebooks/analysis.ipynb
├── src/
│   ├── __init__.py
│   ├── data_pipeline.py
│   ├── turnout.py
│   ├── make_charts.py
│   └── app.py
├── outputs/
│   ├── insights_summary.md
│   └── charts/
│       ├── 01_turnout_map_2024.png
│       ├── 02_turnout_over_time.png
│       ├── 03_state_ranking_2024.png
│       └── 04_demographic_scatter.png
├── screenshots/
│   └── dashboard.png
└── tests/
    └── test_pipeline.py
```

Notes: the scaffold's `tests/test_smoke.py` is **DELETED** and replaced by
`tests/test_pipeline.py` (do not keep two test files). The scaffold's
placeholder `README.md`, `data/README.md`, `notebooks/analysis.ipynb`,
`outputs/insights_summary.md`, `requirements.txt` and `pyproject.toml`
are filled in by the coder — not new files. The shapefile zip and EAVS
zip are **git-ignored and absent at handoff** (§3.4 — they are
downloaded at build time into `data/raw/shapefile/` and `data/raw/eavs/`
and deleted after the build if the coder chooses; the committed raw
artefacts are the two UF CSVs, §3.5). No extra modules, no extra charts,
no `.pbix`, no model card, no county layer. The scaffold's
`requirements.txt` is Day 1's list — the coder replaces it with the §6
pinned stack (Day 13 stack **plus geopandas + scipy**, minus nothing
else: no scikit-learn, no openpyxl this day — there is no model and no
XLSX).

## 6. Per-file responsibilities

| File | Responsibility |
|---|---|
| `src/data_pipeline.py` | Download the 2 UF CSVs (primary; 1 retry after 60 s on 429/5xx, then stop and report); verify byte sizes (§3.1); download the shapefile zip + EAVS zip at build time (git-ignored, §3.4); read both doc `.txt` files in full and record versions/dates; apply cleaning rules §3.2 in order, counting every exclusion/null; run the recompute + EAVS + shapefile-join cross-checks (§3.3); build all 5 processed CSVs (§3.5); write `data_source.json` (live fields); modes `--live` / `--offline` / `--use-cache` / `--synthetic` (brief §4 generator, seed 42). `--offline` skips writing `data_source.json` when a live record exists (§3.5). |
| `src/turnout.py` | Pure turnout functions, no I/O, no network — all tested: `cycle_type(year)` (`presidential` if `year % 4 == 0` else `midterm`), `vep_turnout(ballots, vep)`, `vap_turnout(ballots, vap)`, `pp_change(current, previous)`, `recompute_vep(vap, noncitizen_pct, felons_total, overseas)`, `felon_share_vap(felons_total, vap)`, `overseas_share_vep(overseas, vep)`, `parse_column5(value)` (URL → `SOURCE_URL`, digits → vote count, blank → missing), `flag_outliers(series)` (1.5×IQR fence + \|z\| > 3, returns flagged index + fence values), `skewness(series)`, `correlate(x, y)` (Pearson r + p and Spearman ρ + p with n), `top_bottom(df, column, n)` (deterministic tie-break by state abbreviation) |
| `src/make_charts.py` | Exactly 4 PNGs (§7), matplotlib `Agg` (+ geopandas for chart 01), offline from processed CSVs only (chart 01 also needs the downloaded shapefile — see §3.4 offline note), every chart footnoted with the source + CC BY 4.0 attribution + coverage ("general elections 1980–2024, 50 states + DC + US total; pre-2010 national figures estimated") + synthetic label if applicable |
| `src/app.py` | Streamlit dashboard loading processed CSVs only (offline): KPI row (2024 national VEP turnout %, 2022 midterm VEP turnout %, highest/lowest 2024 state + rate, jurisdictions covered); the 4 charts embedded; state ranking table (with pp change vs 2020); national time-series table; correlation table (r, n, p); outlier list; methods + limitations panel (descriptive only, no model, state level only, VEP vs VAP vs registered-voter denominators, 2024 v0.4 preliminary, pre-2010 estimated); source links on every section (UF Election Lab, EAC, Census boundaries); `width="stretch"` (Day 2 lesson — no deprecated `use_container_width`); footer with CC BY 4.0 attribution |
| `notebooks/analysis.ipynb` | Offline top-to-bottom, ≤ 16 cells, 0 error cells via nbconvert, `_find_root()` from the notebook file location (Day 1 lesson (e)): load + audit (row counts, column-5 parse counts, null ballots per year, VEP reconciliation); national series + cycle-type split; 2024 ranking + pp change vs 2020; skewness screening + outlier list; demographic correlations (r, n, p); the 4 charts inline; Q1–Q3 answered with exact numbers; the SQL check (§4.5); **map section guarded by the shapefile's presence** — if `data/raw/shapefile/` is present it re-renders the choropleth via `src.make_charts` and asserts it matches the committed PNG's source table; if absent it loads the committed CSVs + PNG and prints a note that the re-render was skipped (still 0 errors). The notebook never downloads data itself. |
| `tests/test_pipeline.py` | ≥ 15 tests: column-5 parsing (URL → `SOURCE_URL`, digits → vote count, blank → missing — a test asserts a 2020 row's URL is never parsed as a vote count); `YEAR=2024` added on concatenation; VEP recompute matches the file rate within 0.05 pp on fixtures (incl. the 2024 US 64.30% spot-check from the committed CSVs); VAP turnout < VEP turnout wherever both exist; cycle-type derivation (`2024 → presidential`, `2022 → midterm`); pp change computed within cycle type only; pre-2010 null ballots stay null (never filled); VEP reconciliation flags a fixture row with a planted mismatch; outlier flagging (fixture series with a planted outlier is flagged; flagged rows remain in the table); correlation function returns n, r, p on fixtures and handles a constant series without crashing; top/bottom deterministic tie-break by abbreviation; state table sums/joins: 51 jurisdictions in `state_2024.csv`, US total flagged separately; SQL-vs-pandas agreement (§4.5); offline run does not clobber `data_source.json` live fields; **offline reproduction uses tolerance comparison (Day 9 CI lesson), not byte-exact**; synthetic files never overwrite live files; no committed file > 1 MB, `data/` < 5 MB; `.gitignore` contains the shapefile/EAVS exclusions while the two UF CSVs are NOT ignored; no EAVS figure in any committed turnout table |
| `data/README.md` | Provenance: UF Election Lab URLs, CSV byte sizes, doc versions/dates, CC BY 4.0 attribution verbatim, EAVS version + cross-check result, Census boundary attribution, fetch date, row counts (per file / concatenated / cleaned / excluded per rule / null ballots per year), column-5 parse counts, VEP reconciliation result, recompute cross-check result (incl. the five spot-checks), shapefile join result, cycle-type rule, metric definitions, manual validation, versions, denominator provenance (2024 VAP construction: Census Vintage 2023, extrapolated to Nov. 1, 2024; `NONCITIZEN_PCT` from the 2024 1-Year ACS — brief §1c.5) |
| `outputs/insights_summary.md` | One finding per §2.1 question with exact numbers + top-10/bottom-10 tables + correlation table (r, n, p) + outlier list + limitations (§4.6) |
| `README.md` | Problem, audience, setup, how to run (live/offline), sample outputs (KPI table + chart thumbnails), headline findings with numbers, top-10/bottom-10 tables, the decider rules (§2.0) stated plainly, validation, limitations, attribution, source links |
| `requirements.txt` | Pinned `==` versions verified in the build venv (Python 3.12.3): Day 13 stack (pandas, numpy, matplotlib, plotly, streamlit, requests, pytest, jupyter, nbformat) **plus geopandas (choropleth geometry) and scipy (Pearson/Spearman p-values)**. No scikit-learn (no model), no openpyxl (no XLSX) this day. The coder pins the exact versions that install and verify in the build venv and records them — no version is guessed in this plan. No other new runtime dependency without a plan change |
| `pyproject.toml` / `.gitignore` | Scaffold defaults (ruff/black line-length 88; strict mypy, coverage source `src`); `.gitignore` per §3.4 (shapefile + EAVS + synthetic excluded; the two UF CSVs and `data/` itself NOT excluded) |

Key function signatures (coder follows these names):

```python
# src/data_pipeline.py
def download_file(url: str, dest: Path) -> Path
def load_turnout_csv(path: Path) -> pd.DataFrame  # raw read, column 5 as text
def parse_column5(value: str | None) -> tuple[str | None, float | None]
def clean_turnout(df_1980_2022: pd.DataFrame, df_2024: pd.DataFrame) -> tuple[pd.DataFrame, dict]
def recompute_check(df: pd.DataFrame) -> dict  # max diff vs file rate, spot-checks
def eavs_cross_check() -> dict  # two sampled states, §3.3
def write_data_source(path: Path, record: dict) -> None

# src/turnout.py
def cycle_type(year: int) -> str
def vep_turnout(ballots: float, vep: float) -> float | None
def vap_turnout(ballots: float, vap: float) -> float | None
def pp_change(current: float, previous: float) -> float
def recompute_vep(vap: float, noncitizen_pct: float, felons_total: float, overseas: float) -> float
def felon_share_vap(felons_total: float, vap: float) -> float | None
def overseas_share_vep(overseas: float, vep: float) -> float | None
def parse_column5(value: str | None) -> tuple[str | None, float | None]
def flag_outliers(series: pd.Series) -> pd.DataFrame  # flagged rows + fence values
def skewness(series: pd.Series) -> float
def correlate(x: pd.Series, y: pd.Series) -> dict  # n, pearson_r, pearson_p, spearman_r, spearman_p
def top_bottom(df: pd.DataFrame, column: str, n: int) -> tuple[pd.DataFrame, pd.DataFrame]
```

## 7. Charts (exactly 4, matplotlib, to scale and legible)

All charts: title naming the metric + denominator + year/coverage,
labelled axes with units (turnout in %, pp where a change is shown),
source footnote ("Source: Michael McDonald, University of Florida
Election Lab, General Election Turnout Rates 1980–2022 v1.2 and 2024
General Election Turnout Rates v0.4, CC BY 4.0 — VEP turnout = ballots
counted ÷ voting-eligible population"), coverage footnote ("General
elections 1980–2024, 50 states + DC + US total; pre-2010 national
figures estimated"), no truncated axes, legible at 100% zoom. One
sequential colour scale, used identically on charts 01 and 03 (same
metric, same scale); cycle-type colours fixed on chart 02
(presidential #2e6fb7 blue, midterm #7f8c8d grey — the same palette on
every surface, neither cycle type given a visual advantage).

1. **01_turnout_map_2024.png** — State choropleth: 2024 VEP turnout by
   state. geopandas + matplotlib from the Census `cb_2024_us_state_500k`
   shapefile joined on postal abbreviation; single sequential scale with
   the numeric range in the legend; Alaska/Hawaii in standard inset
   positions (footnote says so); DC labelled; title names the metric
   ("2024 general election — VEP turnout by state (%)"). Answers Q1's
   geography half. The roadmap deliverable's map.
2. **02_turnout_over_time.png** — National VEP turnout 1980–2024.
   Two series (presidential, midterm) with different markers, no line
   connecting across cycle types; pre-2010 points marked "estimated";
   2024 point annotated (64.30%, preliminary v0.4); y-axis in %.
   Answers Q2.
3. **03_state_ranking_2024.png** — Top 10 and bottom 10 states by 2024
   VEP turnout. Horizontal bars, one panel per end (or one chart with
   both ends labelled), labelled with state + rate + rank; US total
   shown as a reference line (64.30%), never ranked. Title names the
   metric and year. Answers Q1's ranking half.
4. **04_demographic_scatter.png** — Demographic indicators vs 2024 VEP
   turnout. Three small-multiple scatter panels (noncitizen share;
   ineligible-felon share of VAP; overseas eligible share of VEP),
   one dot per state, each panel annotated with Pearson r, Spearman ρ,
   n and p; footnote: "Association only — not a causal claim."
   Answers Q3.

The Streamlit dashboard embeds the 4 PNGs (as Days 6–13 do) so the README
thumbnails and the app agree.

## 8. Success checklist (roadmap minimum success criteria — all must pass)

- [ ] Problem statement + audience written (§1, in README and this plan)
- [ ] Data source documented: provider, URLs, CSV byte sizes, licence
      (CC BY 4.0, verbatim attribution), fetch date (2026-11-21), doc
      versions/dates, row counts (per file / concatenated / cleaned /
      excluded per rule / null ballots per year), column-5 parse counts,
      VEP reconciliation result — in `data/README.md` and
      `data/processed/data_source.json`
- [ ] Repeatable prep steps documented (download → parse column 5 →
      concatenate → clean → recompute check → aggregate → charts, with
      `--offline` mode) + metric definitions (§4.1) written down
- [ ] **Decider rules (§2.0) stated in the plan and honoured in the
      build**: VEP from UF authoritative, EAVS cross-check only; demographic
      associations descriptive only (Pearson/Spearman with n, r, p,
      "moves with" language); outliers screened during skewness
      screening and reported as found, never dropped; cycle-type
      comparisons like-with-like only; **tester verified the rules were
      actually used** (recompute within 0.05 pp, no EAVS figure in any
      turnout table, flagged outliers still present, no unlabelled
      cycle-type mixing — test + test_report evidence)
- [ ] **Turnout map + evidence-limited insights memo delivered**
      (roadmap deliverable): state choropleth (2024 VEP turnout) +
      Streamlit dashboard + README with source links on every section,
      KPI row, state ranking table, national time-series table,
      correlation table, outlier list, 4 charts
- [ ] **Turnout compared by geography**: 2024 state ranking (top/bottom
      10), choropleth, pp change vs 2020 per state
- [ ] **Turnout compared over time**: national VEP turnout 1980–2024
      split by cycle type, with pre-2010 figures labelled estimated
- [ ] **Demographic indicators analysed descriptively**: correlations
      (Pearson + Spearman, n, r, p) for noncitizen share, felon share,
      overseas share vs 2024 VEP turnout — association language only,
      no causal claims, no model
- [ ] **Skewness screening + outlier reporting done** (§4.4): skewness
      per cycle type reported, every flagged state listed in the memo
      with its value, flagged rows retained everywhere
- [ ] **Nonpartisan presentation verified**: same metrics/columns/charts
      for every state; no party variable; no causal claims; no editorial
      adjectives; every chart/table states its coverage, denominator
      and source link
- [ ] **State comparison honest**: state-level only (no county map, no
      county rate built on total population); denominators named on
      every surface; VAP never substituted for VEP
- [ ] **SQL check done** (§4.5): average VEP turnout by cycle type and
      top state by 2024 VEP turnout via in-memory SQLite asserted equal
      to pandas, in the notebook and a test
- [ ] Exactly **4 charts** (§7), drawn to scale and legible, plus a
      functional dashboard: the Streamlit dashboard runs and renders
      (smoke gate below)
- [ ] Interpretation written (`outputs/insights_summary.md`, one finding
      per §2.1 question with exact numbers) + limitations (§4.6)
- [ ] README with setup instructions, sample outputs (KPI table + chart
      thumbnails), validation results, the decider rules, and limitations
- [ ] No credentials / private records in the repo; **no copying others'
      code** — all code is Victor's own original work; **data-size rule
      honoured** (no file > 1 MB, `data/` < 5 MB; raw UF CSVs committed
      per §3.4, shapefile + EAVS zips git-ignored and absent at handoff;
      `.gitignore` matches §5/§6 and does NOT exclude `data/`)
- [ ] **One metric manually validated by hand** and recorded in
      `data/README.md` (the tester recomputes one metric — e.g. the 2024
      US VEP turnout, 156,766,239 ÷ 243,803,423 = 64.30% — from the
      committed CSVs, matching to the last digit)
- [ ] Pipeline runs end-to-end from a clean checkout (`pip install -r
      requirements.txt`, `python -m src.data_pipeline --live`,
      `python -m src.make_charts`, `pytest tests/ -q`) — **pytest passing
      both from the repo root and from inside the day folder, with
      coverage at or above the threshold (30, from CHANGELOG.md /
      .github/workflows/ci.yml — the measured floor, Day 8 at 34.94%)**
- [ ] **Notebook runs top-to-bottom without errors** (offline, via
      nbconvert — **exit 0 with 0 error cells** — with `_find_root()`
      and the guarded map section, §6)
- [ ] Pinned dependencies in `requirements.txt` (Day 13 stack plus
      geopandas + scipy; no scikit-learn, no openpyxl this day);
      **`black --check` + `ruff check` clean**;
      **`mypy src tests` clean** (strict-by-default — every `src/`
      function annotated, test functions annotated `-> None`)
- [ ] Streamlit smoke gate passed: **fresh port 8502+**, HTTP 200 on `/`
      and on `/_stcore/health`, **real `screenshots/dashboard.png`**
      captured (**< 1 MB**), server killed and port verified free
- [ ] **Offline pipeline run must NOT clobber `data_source.json`**
      (skip writing it when a live record exists — §3.5, tested)
- [ ] **No base64 strings quoted in docs** (validator false-positive
      rule — never paste base64 content into any `.md` file; the
      validator strips `image/png` blobs from notebooks before scanning,
      but code cells and markdown are still scanned — Day 10/11 lesson)
- [ ] **Orchestrator validate clean** for the day folder
      (`python agents/orchestrator.py --day 14 validate`) — **target
      11/11 checks pass**
- [ ] Charts to scale and legible; frozen-tree check passed immediately
      before push (every file the READMEs reference exists on disk —
      charts, screenshot, CSVs)

## 9. Coder handoff checklist (reference — coder must satisfy all of these before the tester starts)

- [ ] venv exists with pinned deps installed; `black --check` + `ruff check` pass; `mypy src tests` clean; `pytest` passes (≥ 15 tests, coverage ≥ 30, from repo root and from the day folder)
- [ ] `.gitignore` matches §3.4/§5 (shapefile zip + `shapefile/` + EAVS zip + `eavs/` + synthetic excluded; the two UF CSVs and `data/` itself NOT excluded; nothing else in `data/` excluded)
- [ ] `screenshots/dashboard.png` is a real capture of the running app on a fresh port (8502+), < 1 MB
- [ ] `data/` total < 5 MB, no file > 1 MB; **no shapefile/EAVS zip on disk at handoff** (git-ignored, §3.4); `data_source.json` records live counts, cleaning exclusions, column-5 parse counts, VEP reconciliation, recompute cross-check (incl. the five spot-checks), EAVS version + sample result, shapefile join result
- [ ] Counts verified against §3.1; decider rules (§2.0) implemented — recompute within 0.05 pp, no EAVS figure in any turnout table, flagged outliers retained, cycle types never mixed without labelling
- [ ] `tests/test_smoke.py` deleted — only `tests/test_pipeline.py` exists
- [ ] Notebook runs via nbconvert with exit 0 and 0 error cells; SQL check asserts in the notebook
- [ ] Build only what §5 lists; no extra web searches; no base64 strings in any doc

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| A UF CSV fails to download or is truncated | 1 retry after 60 s, then stop and report; byte-size check (§3.1) fails the build loudly; synthetic fallback (§3.6) only if both fail |
| Column 5 parsed as votes (URL read as a number) | Parse-by-content rule (§3.2 rule 2) + test asserting a 2020 URL row is never a vote count; a URL in the numeric column fails the build |
| 2024 file's missing YEAR column breaks the concat | `YEAR=2024` added explicitly (§3.2 rule 3); concat asserts the year range 1980–2024 |
| Recomputed VEP turnout disagrees with the file rate | > 0.05 pp fails the build loudly (§3.3) — stop and report, never silently overwrite |
| VEP arithmetic does not reconcile for some rows | Flagged and counted (§3.2 rule 5), file VEP used throughout; a large flagged share is reported, not hidden |
| EAVS V2 replaces V1 on the EAC index page | Coder checks the EAC index page first (§3.1); whichever version is used is recorded in `data_source.json` |
| Shapefile download fails / join misses a state | Join check asserts all 51 jurisdictions (§3.3); a missing state fails the build — the map never silently drops a state |
| geopandas install is heavy / slow in the venv | Pinned in `requirements.txt` only after verifying in the build venv (§6); chart 01 is the only consumer, so a failure is isolated to the map step and reported, not worked around with a different metric |
| Pre-2010 national figures misread as exact | "Estimated" label on every surface that uses them (§1, §4.2, §7) |
| A correlation is read as a cause | §2.0 Rule 2: n, r, p together + association-only language on every surface; no model fitted |
| An outlier is dropped or winsorised | §2.0 Rule 3 + test asserting flagged rows remain in the table; memo lists every flagged state |
| Cycle types mixed into one trend | §2.0 Rule 4: separate series, no cross-cycle connecting line; test asserts no unlabelled mixing |
| County map attempted (MIT file / Census API) | Out of scope by design (§1, §2.2): MIT file guestbook-blocked, no county denominator, Census API key-blocked — do not retry either |
| Byte-exact offline comparison flakes in CI (Day 9 lesson) | Tolerance-based comparison in the offline test (§3.5) |
| Push-manifest / remote-head loss (Day 7 lesson) | Publisher keeps the push manifest under `~/workspace/` (never `/tmp`); re-check the remote head after any uncertain write |
| Base64 passed to `create_or_update_file` (Day 8 lesson) | Never pass base64 content to `create_or_update_file` — it stores the base64 text as the file. Use push-files from disk for file updates, or pass raw text. Never quote base64 strings in docs (§8). |
| GitHub write-approval card times out (Days 10/12 lesson) | Push step needs the card allowed first; a timed-out card leaves nothing pending, so a retry starts a fresh card rather than waiting on the old one. Per the Day 13 task: attempt the push ONCE; on policy_denied stop immediately, re-check the head, leave everything staged, report the blocker + resume steps. |
| Day 8 defect — double-prefixed slug | The folder is `day-14-voter-turnout-analytics` (verified — the scaffold refusal proves the name already existed in exactly this form). Never create a `day-14-day-14-…` folder; if the orchestrator refuses again, replicate the template by hand as the planner did (§5 note), never force a second folder. |

## 11. Differences from the brief (plan wins)

- **Decider rules (§2.0):** the brief required the planner to state the
  authoritative denominator, the correlation reporting rule, the outlier
  rule and the cycle-type rule. The plan **fixes** all four: UF VEP
  authoritative with EAVS cross-check only (never overrides, never
  averaged, never plotted on the same axis); correlations as Pearson +
  Spearman with n, r, p and "moves with" language, no model; outliers
  flagged by 1.5×IQR or |z| > 3 within cycle type, listed in the memo,
  never dropped; like-with-like comparisons only, cross-cycle change
  labelled "cycle-type change".
- **Correlation scope (§4.3):** the brief left the scope open. The plan
  **fixes** a single scope, `2024_states` (n = 51, DC included, US
  total excluded) — 2024 is one presidential year, so no pooled
  presidential scope is computed and no scope is pooled across cycle
  types.
- **VEP reconciliation tolerance (§3.2 rule 5):** the brief required the
  coder to verify the VEP arithmetic and flag non-reconciling rows but
  set no tolerance. The plan **fixes** > 0.5% of the file VEP as the
  flag threshold, with the flagged count and max difference recorded.
- **Choropleth library (§2.2, §7):** the brief verified the shapefile
  but named no drawing library. The plan **fixes** geopandas +
  matplotlib, fully offline from the downloaded shapefile — Plotly geo
  is excluded (Day 13 lesson: its CDN topojson fails in this
  environment).
- **Doc `.txt` files (§3.1):** the brief required the coder to read both
  documentation files in full. The plan **fixes** that they are
  downloaded at build time for reference and **not committed** (they
  are documentation, not data); their versions and dates are recorded
  in `data_source.json`.
- **Offline chart-01 behaviour (§3.4):** the brief did not cover an
  offline run without the shapefile. The plan **fixes** it: the offline
  run reports "shapefile absent, chart 01 not regenerated" and the
  committed PNG stands; it never writes a broken chart.
- **Map insets (§4.2):** the brief did not specify Alaska/Hawaii
  handling. The plan **fixes** standard inset positions, documented in
  the chart footnote — neither state is dropped.
- **Notebook map section (§6):** the brief did not cover the notebook's
  map dependency. The plan **fixes** the guarded section (re-render if
  the shapefile is present, otherwise load the committed PNG + note),
  mirroring the Day 13 guarded-join pattern.
- **Dependency stack (§6):** the brief named no stack. The plan
  **fixes** the Day 13 stack plus geopandas (choropleth) and scipy
  (correlation p-values), no scikit-learn (no model — Victor's
  decision), no openpyxl — with exact versions pinned by the coder
  from the verified build venv, not guessed in this plan.
