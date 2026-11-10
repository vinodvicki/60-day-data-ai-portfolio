# Test report — Day 06 Viral Content Trend Explorer

**Tester:** Role 4 (independent verification; coder's claims not taken on trust)
**Date:** 2026-11-10 (runs at ~19:09–19:13 PST)
**Day folder:** `~/workspace/goals/60-day-data-ai-portfolio/day-06-viral-content-trend-explorer/`
**Repo:** `vinodvicki/60-day-data-ai-portfolio` (branch `main`)
**Venv used:** the coder's `.venv/` in the day folder (Python 3.12.3, Streamlit 1.66.1). Nothing installed.

## Verdict: PASS

All 8 gates pass. Two defects are recorded below (D-1 minor display, D-2 process-level);
neither changes any number and neither blocks the release, but D-2 must be fixed before
the publisher's frozen-tree check or the next offline run will silently corrupt the
provenance record again.

## 1. What was run (exact commands) and exact results

All commands run from the day folder unless stated otherwise; `.venv/bin/` binaries used.

### Gate 1 — compile + pytest (both locations)

```
.venv/bin/python -m py_compile src/*.py tests/*.py
# -> PY_COMPILE_OK, exit 0

.venv/bin/python -m pytest tests/ -q
# -> 22 passed in 3.55s, exit 0

cd ~/workspace/goals/60-day-data-ai-portfolio/
day-06-viral-content-trend-explorer/.venv/bin/python -m pytest day-06-viral-content-trend-explorer/tests/ -q
# -> 22 passed in 1.98s, exit 0
```

**Result: PASS — 22/22 from inside the day folder AND 22/22 from the repo root.**

### Gate 2 — lint / format

```
.venv/bin/python -m black --check src tests
# -> "All done! 6 files would be left unchanged." exit 0

.venv/bin/python -m ruff check src tests
# -> "All checks passed!" exit 0
```

**Result: PASS — black clean, ruff clean.**

### Gate 3 — pipeline run offline from committed cache

```
.venv/bin/python -m src.data_pipeline --offline
# -> exit 0; stdout ends:
#    "wrote data/processed/videos.csv (472 rows), comments.csv (0 rows),
#     trend_table.csv, data_source.json (source=cache, synthetic=False)"
#    trend table printed: python 69/88 -8.05 -0.2159 fading; ai_ml 77/62
#    +6.36 +0.2419 accelerating; sql 52/43 +3.81 +0.2093 accelerating;
#    career 3/4, bi_viz 6/4, general 7/10 insufficient data; other 22/25 stable.
#    backtest computable=False; age-guard flips: none; median engagement 0.0149.
```

Reproduction check (md5 before vs after the offline run):

| file | md5 before | md5 after | rows |
|---|---|---|---|
| `data/processed/videos.csv` | `036c2a669ed83771ac8a5ae369fea78d` | `036c2a669ed83771ac8a5ae369fea78d` (identical) | 472 data rows (236 window A / 236 window B) |
| `data/processed/trend_table.csv` | `e8c67711ca1550e32c6f3577148f483d` | `e8c67711ca1550e32c6f3577148f483d` (identical) | 7 rows + header |
| `data/processed/comments.csv` | — | header only, 0 rows | 0 |

**Result: PASS — offline run reproduces `videos.csv` byte-identically (472 rows) and
`trend_table.csv` identically.** No network was used (offline mode).

**Side effect found (see D-2):** the offline run overwrote `data/processed/data_source.json`
(`source` "live" → "cache", `generated_at_utc` 2026-11-10T14:20:41Z → 2026-11-10T19:09:36Z,
`quota_units_used` 1019 → 0). I restored the live record from the verbatim copy I had
captured before the run and re-verified it (see §8). `videos.csv`/`trend_table.csv` were
not touched by the restore.

### Gate 4 — notebook execution

```
.venv/bin/python -m jupyter nbconvert --to notebook --execute notebooks/analysis.ipynb \
    --output /tmp/day06_nb_test.ipynb --allow-errors --ExecutePreprocessor.timeout=300
# -> exit 0, "Writing 724039 bytes to /tmp/day06_nb_test.ipynb"
# -> executed notebook: 16 cells, 0 error cells
```

**Result: PASS — 16 cells, 0 error cells.**

### Gate 5 — Streamlit smoke gate (mandatory)

```
nohup .venv/bin/streamlit run src/app.py --server.port 8502 --server.address 127.0.0.1
# log: "Uvicorn server started on 127.0.0.1:8502", no errors/tracebacks in the log

curl http://127.0.0.1:8502/                 -> HTTP 200
curl http://127.0.0.1:8502/_stcore/health   -> HTTP 200, body "ok"
```

Screenshot: one-shot headless captures (`chrome-headless-shell --screenshot` and
Firefox `--screenshot`) both fired before Streamlit's websocket session rendered and
caught only the loading skeleton, so the screenshot was taken via Chrome DevTools
Protocol (Node 24 built-in WebSocket, `chrome-headless-shell` with
`--remote-debugging-port=9222`): navigate, wait 15 s real time, capture at
1440×6500. The resulting image is a genuine render of the running app.

- `screenshots/dashboard.png` (overwritten, coder's file replaced): **576,348 bytes,
  1440×6500 px** (coder's was 576,011 bytes, 1440×6500).
- Dashboard renders fully with correct numbers: title "Viral Content Trend Explorer",
  metrics 472 videos / 2 accelerating / 1 fading / 3 insufficient data; classification
  table Python 69/88 −8.05 pp −21.6%, AI & ML 77/62 +6.36 +24.2%, SQL 52/43 +3.81
  +20.9%; sections 1–6 all present (momentum chart, weekly volume, velocity, sentiment
  "No sentiment snapshot… 0 videos, 0 comments analysed", backtest "Not computable",
  Day 4 long-run context). Truncation warning banner present. No error text anywhere.
- Sidebar "Topic" multiselect renders correctly (7 chips; the last row scrolls inside
  the widget, which is standard Streamlit behaviour — not a defect).
- Server log: clean, zero errors / tracebacks / exceptions.

Teardown:

```
kill <streamlit pid>; kill <chrome pid>
curl http://127.0.0.1:8502/  -> connection refused (curl exit 7, HTTP 000)
ss -ltn | grep 8502           -> port 8502 not listening
pgrep -af "streamlit run"     -> 0 streamlit server processes
pgrep -af "chrome-headless"   -> 0 processes
```

**Result: PASS — port 8502, HTTP 200 on `/` and `/_stcore/health`, real screenshot
576,348 bytes / 1440×6500, server killed, port verified free.**

### Gate 6 — hand-validation of one metric (Python, from `videos.csv`)

Recomputed independently from `data/processed/videos.csv` (age ≥ 7 days for velocity):

| Quantity | My computation | `trend_table.csv` / `data/README.md` | Match |
|---|---|---|---|
| n_recent (A) | 69 | 69 | ✓ |
| n_prior (B) | 88 | 88 | ✓ |
| Window totals A / B | 236 / 236 | 236 / 236 | ✓ |
| Share recent | 69/236 × 100 = 29.2373% → **29.24%** | 29.24% | ✓ |
| Share prior | 88/236 × 100 = 37.2881% → **37.29%** | 37.29% | ✓ |
| Share change | 29.2373 − 37.2881 = **−8.0508 pp → −8.05 pp** | −8.05 pp | ✓ |
| Volume growth | (69 − 88)/88 = **−0.2159 (−21.6%)** | −0.2159 | ✓ |
| Prior median views/day | sorted age-eligible (n=88, median age 30 d) → **5.5919** (5.591935…) | 5.5919 | ✓ |
| Recent median views/day | 0 age-eligible videos → **undefined** | undefined (blank) | ✓ |
| Classification | share ≤ −3 pp and growth ≤ −20%, n ≥ 10 both windows → **fading** | fading | ✓ |

**Result: PASS — Python's full momentum numbers match `trend_table.csv` to the last digit.**

### Gate 7 — chart legibility (`outputs/charts/`, all 1800×825)

| Chart | Verdict | Notes |
|---|---|---|
| `01_trend_momentum.png` | **PASS** | Both panels legible; ±3 pp / ±20% threshold lines drawn; every value labelled (+6.4, +3.8, −8.1, …); n shown as recent/prior per topic; legend readable. |
| `02_weekly_volume.png` | **PASS** | Stacked bars + 2-week rolling mean legible; totals 20 / 216 / 236 labelled; W9 marked partial (`*`); empty weeks honestly empty; source note explains truncation. |
| `03_views_velocity.png` | **PASS** | Drawn to scale: "Other" prior median **49.2/day** dwarfs the others (0.3–6.7/day) exactly as reported. Every bar still carries a legible number + median age + n (Python 5.6, age 30d, n=88; AI & ML 4.1, 31d, n=62; SQL 3.6, 30d, n=43; Career 2.0, 30d, n=4; BI & Visualisation 6.7, 30d, n=4; General Data Analytics 0.3, 30d, n=10; Other 49.2, 30d, n=25). Recent-window "no data" is stated in the caption and legend. The small bars are short because the scale is honest, not because anything is hidden. |
| `04_sentiment_mood.png` | **PASS with minor defect D-1** | Honest empty state: "No sentiment snapshot: no eligible video… 0 videos, 0 comments analysed." Legible. Footer caption contradicts the empty state (see D-1). |

**Result: PASS — all 4 charts to scale and legible.**

### Gate 8 — `data_source.json` source field

```
data/processed/data_source.json  ->  "source": "live",
    "generated_at_utc": "2026-11-10T14:20:41Z", "synthetic": false,
    "quota_units_used": 1019, "video_count": 472,
    all 10 per_query_window entries "truncated": true
```

**Result: PASS — source is "live" at the end of testing** (restored after my offline run
flipped it — see D-2; values re-verified field by field against the pre-run capture).
Note: the restored file's md5 differs from the pre-run md5 (`64f16b41…`) only in
formatting (key order/whitespace) — no byte-level backup of the original existed, so
byte-identity could not be re-established; every field value is identical.

## 2. Defects found

### D-1 (minor, display) — stale footer on the empty-state sentiment chart

- **File/line:** `src/make_charts.py`, lines 293–296, inside the `if comments.empty:` branch
  of `chart_04_sentiment` (lines 275–296). The non-empty branch reuses the same caption
  at line 328, where it is correct.
- **What:** the chart body says "0 videos, 0 comments analysed" but the footer reads
  "As classified by our rule-based model — five videos, not the topics." A reader sees
  "five videos" on a chart that analysed zero videos.
- **Fix:** in the empty branch, use an empty-state footer, e.g.
  "No videos qualified for the sentiment snapshot." Do not change the body text.
- **Impact:** cosmetic only; no number is wrong anywhere else.

### D-2 (process-level, must fix before the next offline run / push) — offline pipeline run overwrites the live provenance record

- **File:** `src/data_pipeline.py` (offline path) writing `data/processed/data_source.json`.
- **What:** every `--offline` / `--use-cache` run rewrites `data_source.json` with
  `source: "cache"`, `generated_at_utc` = now, `quota_units_used: 0` — destroying the
  live-fetch provenance (source "live", generated 2026-11-10T14:20:41Z, quota 1019).
  This is the second occurrence: the coder's handoff §3.4 records the same overwrite
  happening once before and being hand-restored. It happened again during this test
  run (19:09:36Z) and I restored it the same way.
- **Fix (optimizer's first job):** make the offline path not clobber the live record —
  e.g. skip writing `data_source.json` in `--offline` mode when a live record already
  exists, or write the cache record to a separate file. Then re-verify `source: "live"`.
  Do not just hand-restore again; the next offline verification (CI, publisher
  frozen-tree check) will flip it a third time.
- **Impact:** the committed tree is currently correct (restored + verified), so this
  does not block the release — but it will silently recur on every offline run.

## 3. Known gaps confirmed (not defects, not tuned away — as documented by the coder)

- **Truncation dominates the sample:** all 10 query-windows returned exactly 50 videos
  (`truncated: true` in `data_source.json`); recent window effectively 2026-11-08 → 11-09,
  prior 2026-10-08 → 10-10; W1–W3 and W6–W8 empty; only 2 of 8 full weeks have ≥ 5 videos.
  Volume numbers are lower bounds; classifications compare two truncated slices.
  Stated on the dashboard, in the charts, and in `data/README.md`.
- **Velocity / backtest / sentiment empty by consequence:** recent-window velocity undefined
  (0 age-eligible videos), backtest not computable, sentiment 0 videos / 0 comments.
  All three are stated explicitly wherever they would appear; nothing was filled in.
- **Oversize raw file:** `data/raw/videos_details.json` is **2,110,466 bytes (~2.0 MB)**,
  over the 1 MB/file guideline. Total `data/` is **3.9 MB**, inside the 5 MB/day limit.
  (Note: my offline run updated that file's mtime to 19:09; byte size is unchanged at
  2,110,466, matching the coder's figure.)
- **Findings re-checked, not re-derived:** AI & ML accelerating (+6.36 pp, +24.2%, 77 vs 62);
  SQL accelerating (+3.81 pp, +20.9%, 52 vs 43); Python fading (−8.05 pp, −21.6%, 69 vs 88);
  median engagement 1.49%; `other` share 10.0%. All match `trend_table.csv`.

## 4. Plan §8 success-checklist spot-check (tester-verified items)

- pytest 22/22 from day folder and repo root ✓ · black/ruff clean ✓ · notebook 0 errors ✓
- pipeline `--offline` reproduces 472 rows byte-identically ✓ · pinned `requirements.txt`
  present (not re-verified line-by-line; venv matches it per coder handoff) · charts to
  scale and legible ✓ · Streamlit smoke gate ✓ · one metric hand-validated to the last
  digit ✓ · `data_source.json` source "live" ✓ · `data/` 3.9 MB total, `.gitignore` not
  re-checked here (optimizer's item) · no credentials observed in the files read.

## 5. Handoff to the optimizer

**The one thing to do first: fix D-2** — stop the offline pipeline run from overwriting
the live `data_source.json` (skip writing it in `--offline` mode when a live record
exists, or write the cache record elsewhere), then re-run `pytest` and re-verify
`source: "live"`, `generated_at_utc: 2026-11-10T14:20:41Z`, `quota_units_used: 1019`.
Second: fix the D-1 footer on the empty-state sentiment chart (`src/make_charts.py`
lines 293–296) and regenerate `04_sentiment_mood.png`. Do not re-run a live API fetch;
the data is verified. Do not touch the truncation/velocity/backtest/sentiment
emptiness — those are documented limitations, not bugs.
