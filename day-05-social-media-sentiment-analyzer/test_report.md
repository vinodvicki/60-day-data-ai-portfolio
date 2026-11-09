# Test report — Day 05 Social Media Sentiment Analyzer

Tester role (AGENTS.md stage 4). Verified **only in the coder's venv**
(Python 3.12.3, `.venv` as handed off); nothing provisioned, no code
edited. All checks below were run 2026-11-09 by the tester.

## Verdict: PASS

No blocking defect. Two observations for the optimizer (O1, O2 below);
neither blocks the push.

## Gates

| Gate | Result |
|---|---|
| `py_compile` on `src/*.py`, `tests/*.py` | PASS |
| `black --check src tests` | PASS (5 files unchanged) |
| `ruff check src tests` | PASS (all checks passed) |
| `pytest tests/ -q` (coder's venv) | **15 passed** in 3.74 s |
| Pipeline run `--offline` (in a `/tmp` copy, to avoid rewriting the committed `data_source.json`) | PASS — reproduced `comments.csv` **identically** (1,462 rows, pandas `.equals` True); validation reproduced exactly: accuracy 0.6167, macro-F1 0.6131 |
| Streamlit smoke gate (fresh port **8503**, never 8501) | PASS — HTTP **200** on `/` and on `/_stcore/health`, clean server log (no errors/tracebacks) |
| Real screenshot → `screenshots/dashboard.png` | PASS — **1440×6505, 851,854 bytes**, full page renders (header, KPIs, 4 charts, theme table, excerpts, validation panel, footer); visually inspected top and bottom |
| Server killed, port verified free | PASS — PID 4761 killed; no streamlit process; port 8503 not responding afterwards |
| Notebook executes offline (nbconvert, temp copy) | PASS — **0 error cells**, 16 cells |
| Chart legibility (all 4 viewed) | PASS — titles, axis labels, n-values, source notes and model qualifiers all legible; stacked bars to scale 0–100%; chart 04 metrics line clean (no overlap) |
| Frozen tree (13 files the READMEs reference) | PASS — all exist on disk |
| Validation labels | PASS — exactly **120 rows**, 40 per predicted class; human labels 52 positive / 43 neutral / 25 negative |
| Data rules | PASS — 12 raw files, 2.35 MB total, each <1 MB; `data/` 2,808 KB total (<5 MB); 0 duplicate comment IDs; `.gitignore` does not exclude `data/` |
| Orchestrator validate (Day 5) | **10/11** — see C1 below (confirmed false positive, not a defect) |

## Manual hand-validation (tester, independent of the coder's)

Comment `Ugw1odHrhpmb90kXQZ94AaABAg` (video `yZvFH7B6gKI`):
"I can't believe how helpful this was, amazing job!"

- Tokens: i, can, t, believe, how, helpful, this, was, amazing, job
  (curly apostrophe splits "can't" → can + t; "t" scores 0).
- Scored: helpful **+1**, amazing **+2** (strong) = 3.0. One `!` → +0.25.
  No negation, intensifier, or emoji. Raw sum s = **3.25**.
- Compound = 3.25 / √(3.25² + 15) = 3.25 / √25.5625 = 3.25 / 5.056
  = **0.6428** → positive (≥ 0.05), 2 scored words.
- `comments.csv` records exactly 0.6428 / positive / 2. ✓

Headline numbers recomputed independently from the CSV: positive
40.6%, neutral 52.6%, negative 6.8%; zero scored words 808 = 55.3%;
accuracy (30+25+19)/120 = 0.6167; macro-F1 (0.6522+0.6024+0.5846)/3
= 0.6131. All match the README, dashboard, charts and insights. ✓

## Independent spot-check: 30 of 120 validation labels

Method: 30 comment IDs sampled with seed 7; texts extracted **without**
predicted or human labels; labelled blind from text only; then compared.

- **Agreement with the coder's human labels: 27/30 (90.0%).**
- Agreement with the model's predictions: 17/30 (56.7%); human-vs-model
  on the same 30 is also 17/30 — consistent with reported accuracy 0.617
  (SE ≈ 0.089 on n=30).
- The 3 disagreements are all borderline **positive-vs-neutral** calls
  where I labelled enthusiasm/well-wishing as positive and the coder
  labelled neutral: #14 ("really interested in learning Data analytics…
  Can I still learn and be master?"), #18 ("I will start today 4 nov,
  hope I could do it"), #22 ("2026 Google Data Analytics course. New and
  ready for what's instore ahead. All the best"). This is a
  labelling-boundary difference, not an error — and it shows the human
  labels treat cohort check-ins conservatively, which partly explains the
  model's positive recall of 0.58.
- Model errors visible in the 30 corroborate the reported patterns:
  missed praise ("You are very smart" → neutral, "I can t wait for the
  next upload" → neutral, "Loving It!" → neutral) and negative
  over-prediction on neutral technical content (the long neural-network
  weights explanation → negative; the SQL question → negative).

## Confirmed caveats (not defects)

- **C1 — orchestrator validate 10/11, credentials check.** I independently
  confirmed the coder's claim: `data/raw/comments_qrbf9DtR3_c.json:190`
  is a public YouTube avatar URL
  (`https://yt3.ggpht.com/ytc/AIdro_…ThSk-g8rlByJUfRPLo8n2HtbmB0G7VDfzswGgLJModTHVY6_A=…`)
  whose opaque token trips the `sk-[A-Za-z0-9]{24,}` pattern in
  `SECRET_RE`. No credential in the repo. The scanner was not weakened;
  this is a documented false positive, same standing as Day 4's
  oversize-file 10/11.
- **O1 (observation for optimizer)** — an offline pipeline run rewrites
  `data_source.json` to `source="cache"` / `quota_units_used=0`; the
  committed file currently says `"live"` / 16 (correct). The optimizer
  must not run the pipeline in the day folder before the push, or must
  restore the field by hand afterwards.
- **O2 (observation)** — the labelling boundary above (enthusiastic
  cohort check-ins: positive vs neutral) is the largest source of
  human-label variation; worth a one-line note in the README's
  validation paragraph if the optimizer touches it. Not required.

## Next role's first step (optimizer)

Re-verify every published number against the committed CSVs, pin
`requirements.txt` from the venv that actually ran, and re-run `pytest`
after any change. Do not re-run a live API fetch. Do not run the
pipeline in the day folder (see O1).
