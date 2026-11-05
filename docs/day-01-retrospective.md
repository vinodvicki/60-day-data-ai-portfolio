# Day 1 retrospective — Crypto Market Intelligence Dashboard

**Date:** 2026-11-05 · **Repo:** `vinodvicki/60-day-data-ai-portfolio` ·
**Day:** 01 (Crypto Market Intelligence Dashboard — BTC vs ETH vs SOL)
**Note:** this is the standalone Day 1 retrospective. The same material is
summarised in `docs/multi-agent-workflow.md` (§ "Retrospective — Day 1"),
which remains the workflow's living document.

## What worked

- **Research once, build from paper.** The research brief + plan contained
  every endpoint, parameter and metric definition; the coder needed no extra
  web searches and the build matched the plan's file tree and function
  signatures.
- **Independent manual validation.** The tester hand-checked BTC max
  drawdown (peak $105,951.50 on 2025-11-11 → trough $58,566.09 on
  2026-07-01 = −44.7237%, match ≤1e-9); the optimizer re-checked every
  published number against the committed CSVs. The checks caught nothing —
  which is the point: cheap checks, publishable confidence.
- **Live-first fetch with a labelled fallback.** Keyless CoinGecko access
  worked (HTTP 200, no key), so the synthetic path stayed unused — but it
  existed, documented, and would have been labelled everywhere.
- **Small dependency set, pinned late.** Pinning exact versions at optimizer
  time (from the venv that actually ran) was simpler and more accurate than
  guessing pins up front.
- **Publisher spot-checks, not recomputation.** The publisher verified the
  three findings from the committed CSVs (BTC −20.7% / ETH −26.2% /
  SOL −38.5%; drawdowns −44.7% / −56.2% / −62.9%; BTC–ETH correlation
  0.906 full window, 0.890 latest 90d) without re-running the live fetch.

## What was slow, wasteful, or error-prone

- **Parallel agents duplicated work.** Two agents wrote the notebook/charts
  area and the README/docs area concurrently; the optimizer arrived to find
  `README.md`, `data/README.md` and `outputs/insights_summary.md` already
  written (well, and accurately) while the task brief still listed them as
  missing. Rework was avoided only because the files happened to be good —
  the optimizer still had to re-verify every number instead of writing once.
- **`.venv` was empty when the tester started.** The tester had to install
  dependencies before it could verify anything, which cost a full install
  cycle inside the verification step.
- **`.gitignore` deviated from the plan.** The coder ignored
  `data/raw/*.json` although the plan says explicitly "do NOT ignore
  `data/`". The raw JSONs are small (~40 KB each) and are part of the
  deliverable, so the exclusion would have silently dropped the provenance
  artefacts from the repo. The optimizer caught and fixed it.
- **Lint was left to the end.** Four files needed `black` reformatting and
  `ruff` flagged 8 issues (unused import, unused `noqa`s, import order).
  None was a bug, but all of it was avoidable.
- **The dashboard screenshot arrived last and had to be composed.** A real
  Streamlit screenshot was not captured during the coder's smoke test, so
  the optimizer composed `screenshots/dashboard.png` from the four static
  charts instead. It is honest (labelled as a composite) and to scale, but
  it is not a screenshot of the running app.
- **The dashboard image went missing before publishing.** During the
  publisher's review, `screenshots/dashboard.png` (listed at 724 KB in the
  tree check) was no longer on disk when the publisher tried to read it —
  the `screenshots/` directory was empty. No agent in the chain had deleted
  it deliberately; the cause is unknown (concurrent cleanup or a failed
  write). The publisher regenerated it from charts 01–04 with PIL
  (1500×3258, header + footer labelling it a composite, not a literal
  app screenshot, 698 KB) and verified the file before pushing — and then
  a real full-page capture of the running Streamlit app (1400×3600,
  604 KB, sidebar with BTC + ETH selected, summary table covering all
  three coins) replaced the composite at 19:17 UTC. The publisher updated
  the Day 1 README caption to describe the file honestly as a real
  screenshot instead of a composite. Lesson:
  treat `screenshots/dashboard.png` as a checked deliverable — verify it
  exists at every handoff, and never assume a file listed an hour ago is
  still there.

## Which roles need sharpening

- **Coder:** run `black` + `ruff` before handoff; hand off with a working
  venv (deps installed); capture the real running-app screenshot during
  the smoke test; diff `.gitignore` against the plan before sign-off.
- **Tester:** verify only, in the coder's venv — never install the project's
  own dependencies from scratch; if the venv is missing, report
  "blocked: no venv" instead of installing.
- **Optimizer:** verify numbers, don't rewrite good docs. If a doc already
  exists and its numbers check out against the data, fix only concrete
  gaps instead of rewriting it.
- **Publisher / reviewer:** re-verify every referenced asset exists on disk
  immediately before pushing (not just at review start); a README that
  embeds a missing image is a failed push.

## Concrete changes for Days 2–60

1. **Orchestrator assigns one writer per file.** No two agents write the
   same file in the same day; overlapping scopes are sequenced, not
   parallelised.
2. **Coder's handoff checklist** (before the tester starts): venv exists
   with pinned deps installed; `black --check` + `ruff check` pass;
   `pytest` passes; `.gitignore` matches the plan; `screenshots/dashboard.png`
   is a real capture of the running app (or explicitly flagged as a
   composite).
3. **Tester provisions nothing.** The tester runs verification only, in the
   coder's venv; if the venv is missing, the tester reports "blocked: no
   venv" instead of installing.
4. **Optimizer verifies numbers, doesn't rewrite good docs.** If a doc
   already exists and its numbers check out against the data, the optimizer
   fixes only concrete gaps (stale statements, missing sections) instead of
   rewriting it.
5. **CI from Day 1 onward.** `.github/workflows/ci.yml` at the portfolio
   root already covers Day 1 (install → lint → pytest); each new day adds
   its own job (or extends the matrix) rather than inventing a new
   workflow file.
6. **Publisher re-checks assets at push time.** Immediately before pushing,
   the publisher confirms every file the READMEs reference exists on disk
   (charts, screenshots, CSVs); any missing asset blocks the push until
   regenerated or the reference removed.
7. **Keep the 6 roles.** No new agent roles are added; when a day needs a
   new capability (e.g. an ML evaluator), it is a step inside the existing
   coder/tester/optimizer roles, documented in that day's `plan.md`.
