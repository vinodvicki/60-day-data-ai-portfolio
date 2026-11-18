# Security Policy

## Reporting a vulnerability

If you find a security issue in this repository, please report it
privately rather than opening a public issue:

- Open a private vulnerability report via GitHub's **Security** tab
  (Report a vulnerability), or
- Email the repository owner directly.

Please include a short description, the affected file(s) and line(s),
and steps to reproduce if you have them. We will acknowledge the report
and work on a fix before any public disclosure.

## What is in scope

- Code in `agents/`, `scripts/`, and any `day-*/src/` folder.
- The CI workflow (`.github/workflows/ci.yml`) and dependency files
  (`requirements-dev.txt`, `day-*/requirements.txt`).
- Any credential, key, or token found committed to the repository —
  please report it immediately; do not use it or share it further.

## What is out of scope

- The datasets themselves: each day's data is public or synthetic and
  its licence/terms are recorded in that day's `data/README.md`.
- Third-party services (CoinGecko, YouTube Data API, CDC) — report
  issues in those services to their own security contacts.

## How this repo protects itself

- No credentials are committed: the orchestrator's secret scan
  (`agents/orchestrator.py validate`) runs on every day folder and is
  enforced in CI; `.gitignore` excludes `.env`, `.env.*`, `*.pem`,
  `*.key`, and `credentials*`.
- Dependencies are pinned (`==`) and Dependabot opens weekly update
  pull requests for the pip requirements files.
