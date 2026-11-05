# 60-Day Data Analytics + AI Portfolio

**60 days. 60 projects. 20 industries.** One publishable, end-to-end
real-world data + AI project per day, built to the roadmap in
`60_Day_Data_Analytics_AI_GitHub_Project_Roadmap_0_4qxt.pdf`.

Each day: define one decision-maker, one practical problem and 2–3 questions →
obtain public or synthetic data (with source, date range and terms noted) →
prepare and validate → analyse with metrics and charts (baseline before ML/AI)
→ deliver a notebook, dashboard or small working demo → explain with 3–5
findings, business implications, limitations and next actions → publish clean
code, README, requirements, charts and example results.

> A one-day project means a functional first release, not a production system.
> Never commit private, confidential or identifiable data — or credentials.

## Progress

| Day | Project | Sector | Status |
|---|---|---|---|
| [01](day-01-crypto-market-intelligence/) | Crypto Market Intelligence Dashboard — BTC vs ETH vs SOL over 365 days | Crypto | ✅ Done (2026-11-05) |
| 02 | Crypto Risk & Volatility Analyzer | Crypto | Planned |
| 03 | Crypto Market Anomaly Detector | Crypto | Planned |
| 04–60 | See the roadmap catalog | — | Planned |

Day 1 headline findings (live CoinGecko data, 2025-11-05 → 2026-11-05):
BTC −20.7%, ETH −26.2%, SOL −38.5% total return; max drawdowns −44.7% /
−56.2% / −62.9%; BTC–ETH daily-return correlation 0.906. Full detail in
[Day 1](day-01-crypto-market-intelligence/) →
[`outputs/insights_summary.md`](day-01-crypto-market-intelligence/outputs/insights_summary.md).

## Roadmap phases

| Phase | Days | Focus | Sectors |
|---|---|---|---|
| 1 | 01–15 | Data fundamentals + NLP | Crypto · Social media · Healthcare · Retail · Politics |
| 2 | 16–30 | Forecasting + ML + economics | Agriculture · Finance · Technology · Education · Transport |
| 3 | 31–45 | Domain analytics + risk | Climate · Hospitality · Housing · Energy · Cybersecurity |
| 4 | 46–60 | Product thinking + deployment | Public services · Manufacturing · E-commerce · Jobs · Sports |

## Standards (every day)

- **Problem first:** one decision-maker, one problem, 2–3 questions, stated in
  the README before any code.
- **Documented provenance:** data source, collection date, endpoint, row
  counts and licence/usage constraints in `data/README.md`.
- **Reproducible:** pinned `requirements.txt` (exact `==` versions verified
  in the build venv), `python src/data_pipeline.py` → charts → app runs from
  a clean checkout.
- **Validated:** at least one metric checked by hand, independently of the
  pipeline, and recorded in `data/README.md`.
- **At least two well-labelled visualisations** (title, axes with units,
  legend, source note) or a functional evaluation report.
- **Findings + one actionable recommendation** (analytical next step — never
  investment advice, never a price prediction).
- **Clean code:** modular `src/`, type hints + docstrings, `black` formatted
  and `ruff` clean, offline smoke tests (`pytest`) passing.
- **No credentials, no private data, no huge raw files** committed.
  `.gitignore` excludes `.venv/`, `__pycache__/`, `.env`, secrets — but does
  NOT ignore `data/` (small project datasets are part of the deliverable).
- **CI** (`.github/workflows/ci.yml`) runs tests + lint on every push and
  pull request.

How the days are built: see [`docs/multi-agent-workflow.md`](docs/multi-agent-workflow.md)
— the 6-role workflow (researcher → planner → coder → tester → optimizer →
publisher/reviewer), its token-lean rules, and the Day 1 retrospective.

## How to run Day 1

```bash
cd day-01-crypto-market-intelligence
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/data_pipeline.py     # fetch CoinGecko -> data/processed/*.csv
streamlit run src/app.py        # dashboard at http://localhost:8501
pytest tests/ -q                # 7 offline smoke tests
```

Each later day follows the same layout (`README.md`, `requirements.txt`,
`.gitignore`, `LICENSE`, `research_brief.md`, `plan.md`, `data/`,
`notebooks/`, `src/`, `outputs/`, `screenshots/`, `tests/`).

## License

MIT — see [`day-01-crypto-market-intelligence/LICENSE`](day-01-crypto-market-intelligence/LICENSE).
Copyright (c) 2026 Victor.
