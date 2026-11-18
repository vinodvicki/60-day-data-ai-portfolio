# Contributing

This is a personal portfolio built one project per day, by a fixed
six-role workflow. Contributions are welcome as issues and pull
requests that fit the workflow below — drive-by refactors and new
dependencies are not.

## The six-role workflow

Every day is built in this fixed order (see `AGENTS.md` and
`docs/multi-agent-workflow.md` for the full detail):

1. **Researcher** — verifies the data source, endpoints, rate limits and
   metric definitions once; writes `research_brief.md`.
2. **Planner** — writes `plan.md`: problem, audience, questions, exact
   file tree, per-file responsibilities, success checklist. The plan is
   the source of truth.
3. **Coder** — builds the working project: `src/`, `notebooks/`,
   `outputs/charts/`, `tests/`, `data/`, draft README and docs.
4. **Tester** — verifies, never edits to pass: `py_compile`, `pytest`
   (with coverage), Streamlit smoke test + real screenshot, manual
   validation of one metric, chart legibility check.
5. **Optimizer** — makes the tree release-ready: pinned
   `requirements.txt`, `black`/`ruff` clean, `mypy` clean, missing docs
   filled, every published number verified against the committed CSVs.
6. **Publisher / reviewer** — frozen-tree check, push to GitHub, verify
   the live page renders.

One writer per file. A later role never re-does an earlier role's work.

## Quality gates (every day, before push)

From the day folder, in its venv:

```bash
pip install -r requirements.txt
pip install -r ../../requirements-dev.txt   # ruff, black, pytest-cov, mypy, pre-commit
python -m ruff check src tests
python -m black --check src tests
python -m mypy src tests                    # gradual typing; see pyproject.toml
python -m pytest tests/ -q --cov=src --cov-report=term-missing --cov-fail-under=30
streamlit run src/app.py                    # smoke: HTTP 200 + real screenshot
python ../../agents/orchestrator.py --day NN validate   # 11/11 checks
```

- Dependencies are pinned with `==`; no new runtime dependency without
  a plan change.
- Small raw data **is** committed (files < 1 MB, `data/` < 5 MB per day)
  as the provenance record; `.gitignore` must never exclude `data/`.
- All code is original work. No credentials, no private data, no huge
  files. Charts must be to scale and legible.
- Pre-commit hooks (ruff, black, secret scan) run at commit time:
  `pre-commit install` once after cloning.

## Issues and pull requests

- **Bug report:** use the bug-report template; include the day folder,
  the exact command, and the full error output.
- **New day proposal:** use the day-proposal template; a new day needs a
  roadmap entry (problem, skills, suggested data) before work starts.
- **Pull requests:** one day per PR unless the change is repo-wide
  (CI, docs, tooling). CI must be green; the PR description should list
  the gates run and their results.

## Releases

Days are published one at a time to `main`; there are no versioned
releases. The changelog is `CHANGELOG.md`.
