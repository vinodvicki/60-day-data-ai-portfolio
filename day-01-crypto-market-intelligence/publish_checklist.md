# Day 1 — Publish checklist (Publisher / Reviewer final review)

**Project:** Crypto Market Intelligence Dashboard (BTC vs ETH vs SOL, 366 daily observations)
**Review date:** 2026-11-05 · **Reviewer:** Jarvis (publisher/reviewer role)
**Repo target:** `vinodvicki/60-day-data-ai-portfolio` (public, to be created by Victor)
**Status: READY TO PUSH — blocked only by the unblockers in §6 below. No code or
content defect remains.**

---

## 1. Roadmap success criteria (plan.md §8)

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | Problem statement + audience/decision-maker written | **PASS** | `README.md` "Problem" + "Audience" sections; `plan.md` §1–2 |
| 2 | Data provenance documented: source, endpoint, window, fetch date, keyless/Demo-key outcome, row counts | **PASS** | `data/README.md` — CoinGecko `market_chart/range`, window 2025-11-05 → 2026-11-05, accessed 2026-11-05, keyless HTTP 200 for all 3 coins, 366 rows/coin, 1,098 total, no gaps/duplicates |
| 3 | 2+ labelled charts produced (target 4 + summary table) | **PASS** | 4 PNGs in `outputs/charts/` (01 price indexed, 02 rolling volatility, 03 drawdown, 04 relative volume), all 1500×750, titled, axes labelled with units, "Powered by CoinGecko" footnote; summary table in `outputs/insights_summary.md` + in-app table |
| 4 | 3 findings + 1 actionable recommendation in `outputs/insights_summary.md` (no investment advice) | **PASS** | Exactly 3 findings (momentum, volatility/drawdown, liquidity) + 1 analytical recommendation (add a non-crypto comparator; track turnover weekly); "Educational analysis only — not investment advice" stated; grep finds no buy/sell language outside disclaimers |
| 5 | README with setup instructions, sample outputs (embedded charts + dashboard screenshot), and limitations | **PASS** | `README.md` — setup sequence (venv → pip install → pipeline → make_charts → streamlit → pytest), embeds all 4 charts + `screenshots/dashboard.png`, "Limitations" section, MIT licence note |
| 6 | No credentials in the repo; no huge files committed | **PASS** | Secret grep clean (see §4); no `.env`/`.key`/`.pem`/`secrets.toml` anywhere; largest file `screenshots/dashboard.png` 604,065 B; `data/` total 368 KB (largest single file 160,869 B) — under the 1 MB/file and 5 MB/day limits |
| 7 | One metric manually validated | **PASS** | BTC max drawdown hand-recomputed: peak $105,951.50 (2025-11-11) → trough $58,566.09 (2026-07-01) = −44.723676%, matching the pipeline exactly (< 1e-9); recorded in `data/README.md` and `insights_summary.md`; tester re-verified independently |
| 8 | Pipeline runs end-to-end from a clean checkout | **PASS** | Tester re-ran `python -m src.data_pipeline` (exit 0, live fetch, data hashes unchanged) and `python -m src.make_charts` (exit 0); Streamlit smoke on port 8502: HTTP 200 on `/` and `/_stcore/health`, clean log, server killed, port verified free |
| 9 | Notebook runs top-to-bottom without errors | **PASS** | Tester executed a copy with `jupyter nbconvert --execute`: 7 code cells, 0 errors, original untouched |

**9/9 criteria PASS.**

---

## 2. Test results (re-verified by the publisher, 2026-11-05)

- **pytest (Day 1 venv):** `7 passed in 1.46 s` — `.venv/bin/python -m pytest tests/ -q`, exit 0.
- **Orchestrator validator:** `python3 agents/orchestrator.py --day 1 validate` — **11/11 checks passed**, including README, provenance, 4 charts, insights (3 findings + 1 recommendation), pinned `requirements.txt`, `.gitignore` not excluding `data/`, no credentials, data-size rule, `screenshots/dashboard.png` present (604,065 B), pytest 7 passed.
  - Note: the validator is invoked with `python3`, not `python` — plain `python` is not on PATH in this VM (`python: command not found`).
- **Spot-check from committed CSVs (publisher, independent of the pipeline):**
  BTC −20.7% / max drawdown −44.7%; ETH −26.2% / −56.2%; SOL −38.5% / −62.9%;
  BTC–ETH daily-return correlation 0.906; 1,098 rows (366/coin), 2025-11-05 → 2026-11-05.
  All match the README, `insights_summary.md`, and the tester's manual validation.
- **Pinned versions (verified in venv):** pandas 3.1.1, numpy 2.5.4, matplotlib 3.11.2,
  plotly 7.1.0, streamlit 1.66.1, requests 2.34.2, pytest 9.2.0 (Python 3.12.3).
  Lint: `ruff check` + `black --check` clean (optimizer, re-verified 2026-11-05).

---

## 3. Screenshot status — EXISTS (not a blocker)

`screenshots/dashboard.png` — **present, valid PNG, 1400×3600, 604,065 bytes,
modified 2026-11-05 19:17.** This is the **real full-page capture of the running
Streamlit app** (sidebar with BTC + ETH selected, summary table covering all three
coins), per the tester report and the Day 1 README caption — not the earlier
labelled composite. The disappearance reported by the optimizer (file missing
between coder handoff and optimizer push check) has **not recurred**: the file
was verified present by the tester, the optimizer, and now the publisher's
frozen-tree check immediately before this review. No regeneration was needed
and none was performed.

**Frozen-tree check (all files the READMEs reference, verified on disk now):**
`README.md`, `LICENSE`, `outputs/charts/01–04`, `screenshots/dashboard.png`,
`data/processed/crypto_daily.csv`, `data/processed/crypto_metrics.csv` — all present.

---

## 4. Secrets / .gitignore check

- **Secret grep:** no credential values found anywhere in the tree (excluding
  `.venv`). Only legitimate references: the `api_key` parameter name and the
  `COINGECKO_DEMO_API_KEY` **environment-variable read** in
  `src/data_pipeline.py:338` (`os.environ.get(...)`). No key is hard-coded.
- **No secret files:** no `.env`, `*.key`, `*.pem`, or `.streamlit/secrets.toml`
  anywhere in the portfolio tree.
- **`.gitignore` coverage** (root + day-level, both apply): `__pycache__/`,
  `*.pyc`, `.pytest_cache/`, `.venv/`, `venv/`, `.env`, `*.key`, `*.log`,
  `.streamlit/secrets.toml`, `.ipynb_checkpoints/` — all covered.
  (`.streamlit/secrets.toml` and `.ipynb_checkpoints/` are in the day-level
  file only; the root file covers the rest. Combined coverage is complete.)
- **Data-commit rule honoured:** `.gitignore` does **not** exclude `data/`.
  Raw JSONs (~40 KB each, ~120 KB total) are committed deliberately as the
  provenance record, per `plan.md` §5/§6 and `data/README.md` ("Commit rule").
- **Files that WOULD be committed** (no git repo exists yet, so this is a
  `find` listing excluding `.venv`, `__pycache__`, `.pytest_cache`,
  `.ipynb_checkpoints`): **36 files** — root docs (`README.md`, `AGENTS.md`,
  `requirements-dev.txt`, `.gitignore`, `agents/orchestrator.py`,
  `scripts/run_day.py`, `scripts/push_to_github.sh`, `docs/`, `.github/workflows/`)
  plus the full Day 1 folder (README, LICENSE, plan, research brief, test report,
  this checklist, `src/`, `tests/`, `notebooks/analysis.ipynb`, `data/`,
  `outputs/`, `screenshots/dashboard.png`).

---

## 5. CI overlap — decision for Victor / parent (do NOT delete either workflow)

Both workflows trigger on **every push and pull request with no path filters**:

- `.github/workflows/ci.yml` — Day 1 job only (install → black/ruff → pytest in
  `day-01-crypto-market-intelligence`).
- `.github/workflows/daily-project.yml` — general workflow for every changed day
  folder (install → ruff → black → pytest per changed day) **plus** a root-tooling
  lint job (`agents`, `scripts`).

**Consequence:** any push touching Day 1 runs **both** workflows (Day 1 tested
twice, plus the root lint job). It is redundant but harmless — both should pass.
`daily-project.yml` itself notes Day 1's `ci.yml` job is "kept for history" and
that `daily-project.yml` is the general one for Days 2–60. Consolidating them
into one workflow is a **parent/Victor decision**; per `AGENTS.md`, no agent
deletes either file. Recommendation: leave both in place for the Day 1 push;
decide the consolidation when Day 2 lands (or keep `ci.yml` as the Day 1
historical record and let `daily-project.yml` carry Days 2–60).

---

## 6. Unblockers for push (exact)

The tree is publish-ready. The push is blocked **only** by these three steps,
in order:

1. **Victor creates the empty public repo on GitHub:**
   https://github.com — New repository → name `60-day-data-ai-portfolio` →
   Public → **do NOT add a README, .gitignore, or licence** (repo must be
   completely empty). A GitHub App token previously got a 403 creating this
   repo, so only Victor can create it.
2. **Run the push script** (from anywhere; it is executable and safe — it does
   not create the repo, it only initialises git locally, commits, and pushes):
   `bash scripts/push_to_github.sh`
   (path: `~/workspace/goals/60-day-data-ai-portfolio/scripts/push_to_github.sh`).
   If step 1 has not been done, `git push` fails with "repository not found"
   and nothing is uploaded — just create the repo and re-run.
3. **Verify on github.com:** https://github.com/vinodvicki/60-day-data-ai-portfolio
   — README renders, the 4 charts and `screenshots/dashboard.png` display,
   Actions tab shows the CI workflows running (expect both `ci.yml` and
   `daily-project.yml` to run — see §5).

**NOT done by this review (deliberately):** no push was attempted, no GitHub
repo was created, no source logic or data numbers were modified.
