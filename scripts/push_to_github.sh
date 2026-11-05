#!/usr/bin/env bash
# Push script — 60-Day Data Analytics + AI Portfolio, Day 1
# (Crypto Market Intelligence Dashboard)
#
# PREREQUISITE — DO THIS FIRST, BY HAND ON GITHUB:
#   Victor must create the EMPTY public repo
#   https://github.com/vinodvicki/60-day-data-ai-portfolio
#   (GitHub > New repository > name "60-day-data-ai-portfolio" > Public >
#   do NOT tick "Add a README", "Add .gitignore" or "Choose a license" —
#   the repo must be completely empty, otherwise this push will be rejected.)
#   This script does NOT create the repo and does NOT push until that
#   empty repo exists. If the remote does not exist, `git push` will fail
#   with "repository not found" and nothing will have been uploaded.
#
# What this script does (from the portfolio root):
#   1. git init (only if this folder is not already a git repo)
#   2. git add -A   (respects .gitignore: .venv, __pycache__, .env, *.key,
#      .streamlit/secrets.toml are excluded; small data/ files ARE committed)
#   3. git commit -m "Day 01: crypto market intelligence dashboard"
#   4. git branch -M main
#   5. git remote add origin https://github.com/vinodvicki/60-day-data-ai-portfolio.git
#      (skipped if a remote named origin already exists)
#   6. git push -u origin main
#
# Run from anywhere:  bash scripts/push_to_github.sh
# (or: ./scripts/push_to_github.sh — it is executable.)
# After it runs, verify on https://github.com/vinodvicki/60-day-data-ai-portfolio
# that README.md renders, the 4 charts and screenshots/dashboard.png display,
# and the CI workflows show green.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE_URL="https://github.com/vinodvicki/60-day-data-ai-portfolio.git"
cd "$REPO_ROOT"

echo "== Portfolio root: $REPO_ROOT =="

echo "== Step 1: git init (if needed) =="
if [ -d .git ]; then
  echo "Already a git repository — skipping git init."
else
  git init
  echo "Initialised new git repository."
fi

echo "== Step 2: pre-flight checks =="
echo "Checking the frozen tree (files the READMEs reference must exist)..."
test -f day-01-crypto-market-intelligence/README.md
test -f day-01-crypto-market-intelligence/outputs/charts/01_price_indexed.png
test -f day-01-crypto-market-intelligence/outputs/charts/02_rolling_volatility.png
test -f day-01-crypto-market-intelligence/outputs/charts/03_drawdown.png
test -f day-01-crypto-market-intelligence/outputs/charts/04_relative_volume.png
test -f day-01-crypto-market-intelligence/screenshots/dashboard.png
test -f day-01-crypto-market-intelligence/data/processed/crypto_daily.csv
test -f day-01-crypto-market-intelligence/data/processed/crypto_metrics.csv
test -f day-01-crypto-market-intelligence/LICENSE
echo "Frozen-tree check passed (all referenced assets present)."
echo "Files staged for commit (excluding ignored .venv / __pycache__ / .env / *.key):"
git status --porcelain | head -50 || true

echo "== Step 3: git add =="
git add -A
echo "Staged."

echo "== Step 4: git commit =="
if git diff --cached --quiet; then
  echo "Nothing new to commit — skipping commit (tree already committed?)."
else
  git commit -m "Day 01: crypto market intelligence dashboard"
  echo "Committed."
fi

echo "== Step 5: branch -M main =="
git branch -M main

echo "== Step 6: remote origin =="
if git remote get-url origin >/dev/null 2>&1; then
  echo "Remote 'origin' already set to: $(git remote get-url origin)"
  echo "Expected: $REMOTE_URL"
else
  git remote add origin "$REMOTE_URL"
  echo "Added remote origin: $REMOTE_URL"
fi

echo "== Step 7: git push -u origin main =="
echo "NOTE: this requires the empty public repo vinodvicki/60-day-data-ai-portfolio"
echo "to already exist on GitHub. If it does not, this step will fail and nothing"
echo "will have been uploaded — create the repo on GitHub and re-run this script."
git push -u origin main

echo "== DONE =="
echo "Verify at: https://github.com/vinodvicki/60-day-data-ai-portfolio"
echo "- README renders, charts + screenshots/dashboard.png display"
echo "- Actions tab: CI workflows run (see publish_checklist.md for the known"
echo "  ci.yml / daily-project.yml overlap — both will run on Day 1 changes)"
