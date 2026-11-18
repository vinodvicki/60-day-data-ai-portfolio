## What this PR does

<!-- One day per PR, unless the change is repo-wide (CI, docs, tooling). -->

## Day

<!-- e.g. Day 13 — Election Campaign Finance Tracker, or "repo-wide". -->

## Gates run

<!-- List each gate and its result. All must pass before merge. -->

- [ ] `ruff check src tests`
- [ ] `black --check src tests`
- [ ] `mypy src tests`
- [ ] `pytest tests/ -q --cov=src --cov-fail-under=<threshold>` (coverage: ___%)
- [ ] Streamlit smoke test (HTTP 200 + real screenshot)
- [ ] `python agents/orchestrator.py --day NN validate` (___/11)
- [ ] Manual validation of one metric (which one, value, how checked)

## Notes

<!-- Limitations, caveats, anything the reviewer should know. -->
