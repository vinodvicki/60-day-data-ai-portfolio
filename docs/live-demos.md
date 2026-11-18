# Live demos — hosting the 12 dashboards

## Target

Streamlit Community Cloud (free tier, GitHub-native): one public app per
day folder, deployed straight from this repo. No other hosting is needed
and no app code has to change to deploy.

## Why this fits (verified 2026-11-18)

- Every dashboard reads **committed CSVs only** — `Path(__file__)`-based
  data paths, so they work from any working directory. No dashboard calls
  a live API at runtime and none needs a secret or API key, so nothing
  sensitive is required in Streamlit Cloud settings.
- Every dashboard's imports already work when run as a script
  (`streamlit run src/app.py`): the `from src.x import ...` imports fall
  back to plain sibling imports, and Day 7 inserts its own day folder on
  `sys.path`. Verified by running all 12 apps from the repo root (the
  same working directory Community Cloud uses) — HTTP 200 on `/` and
  `/_stcore/health` for each one.
- Dependency files: Community Cloud looks for `requirements.txt` next to
  the entrypoint file, then at the repo root. Our pinned deps live in
  each day folder (`day-XX/requirements.txt`), one level above the
  entrypoint (`day-XX/src/app.py`), so each `src/` holds a two-line shim,
  `src/requirements.txt`, that forwards to the day's file with
  `-r ../requirements.txt`. Versions are listed exactly once, in the
  day's own `requirements.txt`; the shim was verified by installing Day 1
  from it into a clean virtual environment.
- Python 3.12 (the version every day's venv uses). Pick it in Advanced
  settings when deploying; the default may be older.
- Resource use is small: each app loads a few committed CSVs (largest
  day folder data is ~1 MB) plus the pinned libraries, well inside the
  free tier's 1 GB RAM per app.
- Day 6 reads Day 4's processed CSV for long-run context
  (`day-04-youtube-video-performance-analyzer/data/processed/videos.csv`
  via a `Path(__file__)`-relative path). That works on Community Cloud
  because the whole repo is cloned for every app.

## What Victor has to do (one-time, ~15 minutes for all 12)

This is the one step that needs Victor's own account — nobody else can do
it, and it must not be faked with invented credentials.

1. Go to <https://share.streamlit.io> and sign in with GitHub as
   **vinodvicki** (the same account that owns this repo).
2. Click **Create app** (or **New app**).
3. Pick repository `vinodvicki/60-day-data-ai-portfolio`, branch `main`.
4. Set **Main file path** to the day's entrypoint from the table below
   (for example `day-01-crypto-market-intelligence/src/app.py`).
5. Under **Advanced settings**, pick Python **3.12**. Leave Secrets empty
   — no app needs one.
6. Click **Deploy**. The first build takes a few minutes; the app URL is
   `https://<app-name>.streamlit.app` (Streamlit suggests a name from the
   repo and file — keep it or rename it, then record it here).
7. Repeat for the other 11 days. Each app deploys independently and
   redeploys automatically whenever `main` changes.

## Apps

| Day | Entrypoint (Main file path) | Live URL | Status |
|---|---|---|---|
| 01 | `day-01-crypto-market-intelligence/src/app.py` | — | Not yet deployed |
| 02 | `day-02-crypto-risk-volatility-analyzer/src/app.py` | — | Not yet deployed |
| 03 | `day-03-crypto-market-anomaly-detector/src/app.py` | — | Not yet deployed |
| 04 | `day-04-youtube-video-performance-analyzer/src/app.py` | — | Not yet deployed |
| 05 | `day-05-social-media-sentiment-analyzer/src/app.py` | — | Not yet deployed |
| 06 | `day-06-viral-content-trend-explorer/src/app.py` | — | Not yet deployed |
| 07 | `day-07-disease-prevalence-dashboard/src/app.py` | — | Not yet deployed |
| 08 | `day-08-hospital-readmission-risk-model/src/app.py` | — | Not yet deployed |
| 09 | `day-09-healthcare-resource-demand-forecast/src/app.py` | — | Not yet deployed |
| 10 | `day-10-retail-sales-intelligence-dashboard/src/app.py` | — | Not yet deployed |
| 11 | `day-11-inventory-demand-forecast/src/app.py` | — | Not yet deployed |
| 12 | `day-12-customer-segmentation-engine/src/app.py` | — | Not yet deployed |

Fill in the Live URL column (and the matching "Live demos" section in the
root README) as each app is deployed. Do not invent a URL before the app
exists — an app URL only counts once the deployed page returns HTTP 200.

## For future days (13–60)

- The scaffold already writes `src/requirements.txt` (the same shim), so
  every new day is deployable the same way with no extra work.
- Deploy the new day's app the same day it is pushed, using the same
  steps, and record its URL in the table above and in the root README.
- If a future day's dashboard ever needs a secret (for example a live API
  key at runtime), do **not** commit it: put it in that app's Secrets in
  the Streamlit Cloud settings and note it here.
