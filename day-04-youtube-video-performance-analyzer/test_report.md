# Test report — Day 04 YouTube Video Performance Analyzer

**Role:** Tester (role 4 of 6). **Date:** 2026-11-08. **Tester:** Jarvis (subagent).
**Verdict: NOT READY — three documentation defects (D1, D2, D3) block publishing
as-is.** Every build gate passes — compile, pytest (both locations), lint,
offline pipeline reproduction, notebook, Streamlit smoke gate, chart
legibility, provenance, secrets — and every plan §4.6 target passes on
independent recomputation. But the published-docs cross-check found three
mismatches against the committed CSVs: a wrong coverage number
(`data/README.md`), a wrong video ID (`data/README.md`), and a recommendation
whose claim contradicts the CSV (`outputs/recommendations.md`, also rendered
verbatim in the live dashboard). All three are one-line fixes for the
optimizer — no code logic, data, re-fetch, or method change is needed — but
the day must not be published until they are fixed and pytest is re-run.

No code, data, or docs were edited by the tester, except restoring
`data/processed/data_source.json` byte-identical after the §3 offline
pipeline re-run (see §3) and writing this report plus a fresh
`screenshots/dashboard.png` (real full-page capture, overwriting the coder's
capture — see §4).

## 1. Compile — PASS

`cd day-04-youtube-video-performance-analyzer && .venv/bin/python -m py_compile src/youtube_kpi.py src/data_pipeline.py src/make_charts.py src/app.py tests/test_pipeline.py`
→ exit 0. Python 3.12.3; venv has pandas 3.1.1, numpy 2.5.4, matplotlib
3.11.2, plotly 7.1.0, streamlit 1.66.1, requests 2.34.2, pytest 9.2.0,
jupyter 1.1.1, nbformat 5.11.1 (all 9 `requirements.txt` pins match the venv
freeze exactly — see §8).

## 2. pytest — PASS (coder's claim confirmed exactly)

In the coder's venv (nothing installed):

- Inside the day folder: `.venv/bin/python -m pytest tests/test_pipeline.py -q`
  → **15 passed in 1.96 s**, exit 0.
- From the portfolio repo root: `day-04-.../.venv/bin/python -m pytest day-04-youtube-video-performance-analyzer/tests/test_pipeline.py -q`
  → **15 passed in 2.00 s**, exit 0.

The 15 tests cover the plan §6 list: duration parsing on hand-computed cases
(`PT12M34S` → 754, `PT1H2M3S` → 3723, `PT45S` → 45, `PT9M4S` → 544) and the
day-component regression test (`P1DT4H41M8S` → 103268 — a real duration in
this dataset, video `cnjhHZNJEDk`, see D2); duration buckets at every
boundary (60, 61, 300, 301, 900, 901, 1800, 1801, plus 107308 → `deep_dive`);
topic priority (`python` beats `sql`); format classification; KPI formulas on
a hand-computed row; high-performer top-quartile flag; synthetic determinism
(seed 42); synthetic/cache separation; `--offline` mode; CSV-vs-published
findings; notebook `_find_root()`; attribution + descriptive sentence; and
evidence-cited recommendations with no causal verbs.

## 3. Offline pipeline re-run — PASS (byte-identical reproduction)

`.venv/bin/python -m src.data_pipeline --offline` → exit 0, ~0.9 s, no
network. Printed: `Data source: CACHE`, quota 0, counts
`{'candidates': 250, 'unique_after_dedupe': 244, 'dropped_live_or_upcoming': 0,
'dropped_no_view_count': 0, 'dropped_missing_details': 0, 'final_videos': 244}`;
like-count presence 97.5%; subscriber-count presence 100.0%; median
views/day 611; median engagement 2.20%; other-topic share 0.0%; largest
channel share 4.1% (`UCsvqVGtbbyHaMoevxPAq9Fg`).

md5 comparison against pre-run hashes: `data/processed/videos.csv`
byte-identical (md5 `98dc345d…`); all 4 charts byte-identical. The offline
run flipped `data/processed/data_source.json` `source` to `"cache"` (plan
§3.3 rule, as expected) and rewrote the raw JSONs (timestamps only — sizes
identical, and `videos.csv` byte-identical proves content unchanged). The
original `data_source.json` was restored byte-identical from backup — final
md5 `a8b0a163233b8343243c8f2fae625383`, `source: "live"`, `synthetic: false`,
`seed: null`.

## 4. Streamlit smoke gate — PASS

- Port **8503** (fresh; coder used 8502, never 8501).
- `GET /` → **HTTP 200**; `GET /_stcore/health` → **HTTP 200** (`ok`).
- Server log: clean — zero `error`/`traceback` lines.
- Real full-page screenshot captured with the venv's Playwright + headless
  Firefox → `screenshots/dashboard.png`, **1,109,719 bytes, 1440×5200 px**,
  md5 `add5c275a3bb2ac47526189fbcb6dfbd` — a real render of the running app
  (title, sidebar filters, KPI metrics 244 / 611 / 2.20% / 143, topic and
  length tables, top-quartile text, all 4 charts, all 6 recommendations,
  footer with attribution and quota note). Rendered-page text confirmed to
  contain 611, 2.20%, 244, 914, 851, 3,124, Wednesday, the
  descriptive-not-causal sentence, and the YouTube Data API v3 attribution.
- Screenshot note: Playwright's `full_page=True` captured only the 900 px
  viewport on the first attempt, because Streamlit's document body is
  viewport-height and the content lives in a scrolling `MAIN` element
  (5,155 px tall). Re-captured with a 1440×5200 viewport so the whole app
  fits in one frame; the first partial capture was overwritten by this
  complete one. (The coder's 1440×7500 capture was overwritten only by this
  successful full-page capture, per the task rule.)
- Server killed afterwards; **port 8503 free** (curl after kill: connection
  refused, exit 7), no Streamlit process remains.

## 5. Manual validation of one metric — PASS (with a convention note, C3)

Video `yZvFH7B6gKI`, recomputed independently from
`data/raw/videos_details.json` with my own code (no import of
`src/youtube_kpi`):

| Quantity | My recomputation | Committed CSV | Diff |
|---|---|---|---|
| Engagement rate | (53,644 + 970) / 2,354,250 = **0.023198046086864182** | 0.023198046086864182 | **0.0 (exact)** |
| Views/day (code's convention) | 2,354,250 / 2,053 = **1146.736483195324** | 1146.736483195324 | **0.0 (exact)** |
| Duration | `PT9M4S` = 9×60 + 4 = **544 s** | 544 | **0** |
| Days since publish | 2,053 (see C3) | 2,053 | 0 |

The coder's hand-check claim in `data/README.md` (engagement
0.023198046086864182, views/day 1146.736483195324, duration 544 s) is
confirmed exactly. Full-frame check with the same independent code:
engagement formula matches all 244 rows (0 mismatches at rel > 1e-9);
views/day matches all 244 rows under the code's Timestamp convention
(0 mismatches; the one row where raw `.days` is 0, `0ER5O5SA_OE`, is
correctly clipped to the minimum 1 by `clip(lower=1)`); duration parse
matches the raw ISO 8601 string for all 244 rows (0 mismatches), including
both day-component videos (`cnjhHZNJEDk` `P1DT4H41M8S` = 103,268 s and
`SSKVgrwhzus` `P1DT5H48M28S` = 107,308 s).

## 6. Chart legibility — PASS (with two cosmetic notes, C1–C2)

All 4 PNGs in `outputs/charts/` inspected at full resolution (exactly 4, no
extras). All are drawn to scale, axes labelled with units, legends present,
source note present, human-readable labels (no raw slugs), no cut-off axes,
no overlapping text at full size. Every plotted number agrees with the
committed CSVs (chart 01: General 108 n=1, Career 642 n=10, BI & Viz 2,574
n=3, AI & ML 914 n=68, SQL 707 n=39, Python 489 n=123, overall-median line
611; chart 02: 369/288/610/851/734 views/day and 2.14/2.24/2.32/2.78/2.12%
engagement; chart 03: cells annotated with median + n, thin cells marked;
chart 04: legend Rest n=183 / Top quartile n=61).

- **C1 (cosmetic):** chart 03's colour scale is dominated by three thin
  cells (Wednesday 08:00 23,291 n=1; Sunday 11:00 17,571 n=1; Saturday
  18:00 15,774 n=2), so most cells wash to near-white. Honest and to
  scale, and the n annotations make the thin cells visible — but the bulk
  pattern is hard to read. A capped/log colour scale would help; not a
  defect.
- **C2 (cosmetic, plan-wording deviation):** chart 04 shows no topic
  encoding, although plan §7 says "topic shown by marker shape or a
  faceted legend" — shape is used for high-performer status instead
  (circles vs diamonds). The chart still answers its stated question
  (high performers reach further without engaging better). Optimizer item
  only.

## 7. Independent verification of the §4.6 targets — ALL PASS

Recomputed with a hand-written script in `/tmp/day04_verify.py` (own
parsing, medians, and grouping code — no import of `src/youtube_kpi`),
from the committed `data/processed/videos.csv` and
`data/raw/videos_details.json`.

| Metric | Recomputed (independent) | Coder claimed | Target | Verdict |
|---|---|---|---|---|
| Final videos | 244 | 244 | ≥ 180 | **PASS** |
| Like-count presence | 97.5% (238/244) | 97.5% | ≥ 90% | **PASS** |
| Subscriber-count presence | 100% (244/244) | 100% | ≥ 80% | **PASS** |
| Duplicate `videoId`s | 0 | 0 | 0 | **PASS** |
| Duration parse | 100% (244/244, all > 0) | 100% | 100% | **PASS** |
| Median engagement rate | 2.20% (0.021991) | 2.20% | 0.5–8% | **PASS** |
| `other` topic share | 0.0% (0/244) | 0.0% | ≤ 30% | **PASS** |
| Largest channel share | 4.1% (Simplilearn, 10/244) | 4.1% | ≤ 20% | **PASS** |
| High-performer comparison | top quartile n=61 vs rest n=183; 3,124 vs 380 views/day; engagement 2.01% vs 2.32% | same | reported with n | **PASS** |

Headline KPIs cross-checked from the CSV: median views/day 611
(611.382…); best topic AI & ML 914 (n=68); best length Long 15–30 min 851
(n=41); tutorials 596 (n=192) vs explainers 504 (n=14); best weekday
Wednesday 878 (n=34); no interpretable publish-hour pattern (hours with
n ≥ 5 span 357–1,397 median views/day; 08:00 UTC highest at 1,397, n=7;
18:00 UTC lowest at 357, n=13). Top-quartile composition confirmed: AI &
ML 47.5% of the top quartile vs 21.3% of the rest; Python 37.7% vs 54.6%;
deep-dives 39.3% of the top quartile; largest channel in the top quartile
8.2% (freeCodeCamp.org, 5/61). Channel-size medians confirmed: large 887
(n=78), mid 680 (n=83), small 367 (n=83). Published range 2017-05-19 to
2026-11-07; median age 800.5 days. "Machine Learning Explained" titles
(`PeMlggyqz0Y`, `znF2U_3Z210`) classify as tutorial because "learning"
contains the keyword "learn" — plan rule verbatim, as the coder disclosed;
not a defect. Thin groups confirmed as disclosed: BI & Visualisation n=3,
General Data n=1.

## 8. Lint — PASS

`.venv/bin/black --check src tests` → exit 0 (5 files unchanged).
`.venv/bin/ruff check src tests` → exit 0 ("All checks passed!").
`grep use_container_width src/` → none; `width="stretch"` used 6× in
`src/app.py`. `requirements.txt` pins match the venv freeze exactly for
all 9 pins (pandas 3.1.1, numpy 2.5.4, matplotlib 3.11.2, plotly 7.1.0,
streamlit 1.66.1, requests 2.34.2, pytest 9.2.0, jupyter 1.1.1,
nbformat 5.11.1). The venv additionally contains playwright 1.64.1, ruff
0.17.4 and black 26.10.1, which are not in `requirements.txt` — dev/test
tools, pinned at the portfolio root per the plan; not a defect (see C5).

## 9. Provenance, secrets, file tree — PASS (except D1/D2, §11)

- `data/processed/data_source.json`: `source: "live"`, `synthetic: false`,
  `seed: null`, `api: "youtube-data-api-v3"`, `video_count: 244`,
  `channel_count: 143`, `quota_units_used: 508`, `max_results_per_query:
  50`, the 5 queries verbatim, `top_up: null`. Quota arithmetic checks:
  5×100 + 5×1 + 3×1 = 508; day total 100 (probe) + 508 (manual fetch) +
  508 + 508 (two pipeline runs) = 1,624, as stated in the READMEs.
- Raw counts close exactly: 5 search JSONs × 50 items; 244 unique search
  IDs = 244 `videos_details.json` items = 244 CSV rows; 143
  `channels_details.json` items = 143 distinct channels. Dedupe 250 → 244
  (6 duplicates dropped) confirmed.
- Raw sizes: 5 search JSONs ~53–54 KB each, `channels_details.json`
  306,044 bytes, `videos_details.json` **1,466,881 bytes (~1.47 MB)** —
  over the 1 MB per-file guideline; total raw ~2.0 MB, inside the 5 MB
  per-day limit. Disclosed in `data/README.md` with rationale (plan-fixed
  filename, provenance record, regenerable). Recorded as known gap G1
  (§12), a publisher decision — not a numbered defect.
- `.gitignore` mirrors the plan: does NOT exclude `data/`; excludes only
  `data/raw/*_synthetic.json`. No `*_synthetic.json` files exist; no
  `.env` file exists.
- Secrets: zero `AIza` strings and zero key assignments in `src/`,
  `tests/`, `*.md`, `*.txt`, `*.toml`, `data/README.md`,
  `data_source.json`, `outputs/*.md`, and in the raw JSONs. (One grep
  pattern matched base64 PNG data inside `notebooks/analysis.ipynb` —
  image bytes, not a credential.)
- File tree matches plan §5 exactly — no extra files, no extra charts
  (exactly 4 PNGs in `outputs/charts/`).
- No causal verbs in any recommendation: the only "guarantee" hits in
  README/insights/app are the required disclaimer sentence ("not a
  guarantee of future performance"). The §4.3 descriptive-not-causal
  sentence is present in README, app, and insights; "Data from the
  YouTube Data API v3" attribution with the ToS link is present in README,
  app, and charts.

## 10. Notebook — PASS

`.venv/bin/jupyter nbconvert --to notebook --execute
notebooks/analysis.ipynb` (output to `/tmp/day04_nb_executed.ipynb`, the
committed file untouched, md5 unchanged) → executed end-to-end offline,
**16 cells, 0 error outputs**. (One standard Jupyter warning about
unencrypted TCP kernel transport — not an error.)

## Plan §8 success checklist — item-by-item

| §8 item | Verdict |
|---|---|
| Problem statement + audience written | PASS |
| Data source documented (provider, endpoints, 5 queries, date, licence, quota, row counts; `data_source.json` source-field rule satisfied) | PASS — `source: "live"`, restored byte-identical after the offline re-run |
| Repeatable prep steps + KPI/grouping definitions documented | PASS |
| ≥2 well-labelled visualisations, to scale and legible, + functional dashboard (smoke gate) | PASS (cosmetic C1, C2 only) |
| Interpretation written + evidence-cited recommendations, all §4.6 targets pass | **FAIL — §4.6 targets pass, but recommendation 2's wording contradicts the CSV (D3)** |
| README with setup, sample outputs, limitations | PASS |
| No credentials / private records; no huge raw files; `.gitignore` does not exclude `data/` | PASS, except the disclosed 1.47 MB `videos_details.json` over the 1 MB per-file guideline (G1, publisher decision) |
| One metric manually validated by hand and recorded | PASS (§5; engagement diff 0.0) |
| Pipeline runs end-to-end; pytest passing from repo root AND day folder | PASS |
| Notebook runs top-to-bottom without errors (offline, `_find_root()`) | PASS |
| Pinned dependencies; black + ruff clean | PASS |
| Streamlit smoke gate (fresh port, HTTP 200 ×2, real screenshot, killed, port free) | PASS |
| Charts to scale and legible | PASS |
| **Published numbers all match the committed CSVs** | **FAIL — D1, D2, D3** |

## 11. Defects

### D1 — `comment_count` presence is 243/244, not 244/244 (CONFIRMED)
- `data/README.md:67`: "| Videos with `comment_count` present | 244 of 244 (100%) |".
- Independently counted from `data/processed/videos.csv`: **243 of 244
  (99.6%)** have a `comment_count`. Video `b0KaGBOU4Ys` ("What is AI?")
  has `like_count` 829.0 but an empty `comment_count` — and the raw
  `data/raw/videos_details.json` confirms its `statistics` object has no
  `commentCount` key (comments disabled), so the CSV is right and the
  README is wrong. Consequence: `engagement_rate` is empty for 7 rows
  (6 missing likes + this 1 missing comments), not 6.
- Fix: change the line to "243 of 244 (99.6%; 1 video has comments
  disabled — recorded as missing, never 0)".

### D2 — Day-component duration misattributed to the wrong video (CONFIRMED)
- `data/README.md:69`: "one video is `P1DT4H41M8S` = 103,268 s, the 30-hour
  SQL course `SSKVgrwhzus`".
- From `data/raw/videos_details.json`: `P1DT4H41M8S` = 103,268 s belongs to
  video **`cnjhHZNJEDk`** ("2026 FREE Data Analyst Bootcamp [24 Hours+]"
  — Alex The Analyst). Video **`SSKVgrwhzus`** ("SQL Full Course for
  Beginners (30 Hours)") has duration **`P1DT5H48M28S` = 107,308 s**.
  The 103,268 s number is correct for `P1DT4H41M8S`, and the parser test
  (`tests/test_pipeline.py:41-42`) is correct — only the README's video
  ID (and the "30-hour" description attached to the wrong video) is
  wrong.
- Fix: change the line to name `cnjhHZNJEDk` for `P1DT4H41M8S` =
  103,268 s, and note `SSKVgrwhzus` is `P1DT5H48M28S` = 107,308 s (the
  actual ~30-hour course).

### D3 — Recommendation 2 claims AI & ML is the best topic "of any topic group" — BI & Visualisation is higher (CONFIRMED)
- `outputs/recommendations.md:18` (heading) and `:21-22`
  (Recommendation field): "In this sample, AI & Machine Learning videos
  had the highest median views per day of any topic group."
  Evidence cited: median 914 views/day (n=68) vs 611 overall.
- From `data/processed/videos.csv`: **BI & Visualisation median is 2,574
  views/day (n=3) — higher than AI & ML's 914.** The claim as written is
  false. The same file's own "What was deliberately not recommended"
  section acknowledges BI & Visualisation's 2,574 median, and the main
  `README.md:91` states the finding correctly with the qualifier "Best
  topic by median views/day (solid groups, n ≥ 10)". The generator code
  is the source of the wording: `src/youtube_kpi.py:266-267` builds the
  sentence as "the highest median views per day of any topic group",
  even though the selection at `:261` correctly restricts to solid
  topics (`count >= 10`). The dashboard renders this sentence verbatim
  (visible in `screenshots/dashboard.png`, recommendation 2), so the
  false claim is live in the app too.
- Fix (optimizer, one line + matching doc edit): reword
  `src/youtube_kpi.py:267` to state the restriction, e.g. "the highest
  median views per day of any solid topic group (n ≥ 10)" — and make the
  identical change in `outputs/recommendations.md:18,21-22`. No test
  asserts the exact wording (`tests/test_pipeline.py:305-313` checks
  evidence/caveat structure and no causal verbs only), but re-run the
  full pytest suite after the edit. Note rec 1 ("any length group") and
  rec 3 ("highest median engagement rate of any topic group") were
  checked and are correct as written — Long 851 is the highest of all
  five duration buckets, and Career 2.95% is the highest of all six
  topics.

## 12. Known gaps / cosmetic notes (not defects)

- **G1 (disclosed, publisher decision):** `data/raw/videos_details.json`
  is 1,466,881 bytes (~1.47 MB), over the 1 MB per-file commit guideline
  in plan §3.3/§8; total raw data is ~2.0 MB, inside the 5 MB per-day
  limit. Disclosed with rationale in `data/README.md` ("File sizes"
  section): the plan fixes that filename and it is the provenance record
  for every number in `videos.csv`. The publisher must accept the
  disclosed exception (recommended — splitting the file would break the
  plan-fixed filename) or send it back to the planner.
- **C3 (convention note, not a defect):** `days_since_publish` is
  `(Timestamp('2026-11-08', UTC) − publishedAt).dt.days`, clipped at ≥1
  (`src/youtube_kpi.py:172-174`) — full 24-hour periods from the publish
  timestamp to 2026-11-08 00:00 UTC. Under a calendar-date reading the
  day count would be +1 for 243 of 244 rows (e.g. `yZvFH7B6gKI`: 2,054
  days, views/day 1146.178188899708 vs the CSV's 1146.736483195324, rel
  diff 4.87e-4; worst case the newest video `IPKOx66fogE`, published
  2026-11-05T10:49:08Z: 57,164.5 vs 38,109.7 views/day, rel diff 33%).
  Headline medians are unaffected (611.38 vs 611.17 — both round to 611).
  The code, its tests, and `data/README.md` are mutually consistent and
  the plan's formula as written is what the code implements, so this is
  not a data error — but the plan formula is ambiguous between the two
  readings, and one clarifying sentence in `data/README.md` (that days
  are full 24-hour periods to 2026-11-08 00:00 UTC) would close it.
- **C4 (cosmetic):** in the tall-viewport full-page capture the sidebar's
  "Top-quartile performers only" checkbox is not visible (it was visible
  in the 900 px viewport capture) — likely a sidebar scroll-container
  artifact of the tall viewport, not an app defect; the filters render
  and the app functions.
- **C5 (observation, not a defect):** the venv contains playwright 1.64.1
  plus ruff 0.17.4 / black 26.10.1, none of which are in
  `requirements.txt` (9 runtime pins only). Dev/test tools, pinned at
  the portfolio root per the plan.
- Coder-disclosed items verified, no action needed: "Machine Learning
  Explained" titles classify as tutorial via the "learn" keyword (plan
  rule verbatim); thin groups BI & Visualisation n=3 and General Data
  n=1 are labelled thin-sample everywhere; the duration parser accepts a
  day component (regression test at `tests/test_pipeline.py:41-42,65`).

## Optimizer's first step

Fix D1–D3 only — no code logic, data, re-fetch, or method change:

1. `data/README.md:67` → comment presence 243 of 244 (99.6%), naming
   `b0KaGBOU4Ys` as the comments-disabled video.
2. `data/README.md:69` → `P1DT4H41M8S` = 103,268 s belongs to
   `cnjhHZNJEDk`; `SSKVgrwhzus` is `P1DT5H48M28S` = 107,308 s.
3. `src/youtube_kpi.py:267` → add the solid-group qualifier to the
   recommendation-2 sentence, and make the identical change in
   `outputs/recommendations.md:18,21-22`.
4. Optionally add the C3 one-liner to `data/README.md` and the C1/C2
   chart tweaks if cheap (do not regenerate charts for cosmetics alone).
5. Re-run the full pytest suite from both locations (`pytest` inside the
   day folder and from the portfolio root) and confirm 15 passed, then
   hand the publisher a release where the only remaining open item is
   the disclosed G1 file-size exception for the publisher to accept.
