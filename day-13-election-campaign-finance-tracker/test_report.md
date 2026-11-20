# Test report — Day 13 Election Campaign Finance Tracker

Tester re-verification, 2026-11-19 ~16:40 PST, in the coder's venv
(`day-13-election-campaign-finance-tracker/.venv`, Python 3.12.3).
No code was edited to make anything pass; no dependencies installed.

## Verified results

| Gate | Command / check | Result |
|---|---|---|
| `py_compile` | `python -m py_compile src/*.py tests/*.py` | **OK** |
| black | `black --check src tests` | **Clean** (6 files unchanged) |
| ruff | `ruff check src tests` | **Clean** |
| mypy | `mypy src tests` (from inside the day folder) | **Clean** (6 files, no issues) |
| pytest | `pytest tests/ --cov=src --cov-fail-under=30` | **32 passed, coverage 51.82%** (threshold 30) |
| Pipeline (offline) | `python -m src.data_pipeline --offline` | **Exit 0**; live `data_source.json` preserved (sha256 unchanged, source `live`, generated 2026-11-19T15:58:19Z) |
| Streamlit smoke | Port **8503** (fresh; coder used 8502) | **HTTP 200 on `/`, 200 `ok` on `/_stcore/health`**; server log 0 errors/tracebacks; real full-page screenshot 1440×7149, 968,319 bytes — **byte-identical (sha256 `951f6364…`) to the coder's capture**, so `screenshots/dashboard.png` was left as-is; server killed, port 8503 verified free, no streamlit processes remain |
| Notebook | `jupyter nbconvert --execute --inplace` | **Exit 0, 16 cells, 0 error cells**; join cell took the skip path ("raw .txt files not present — join re-run skipped") because the unpacked `.txt` files were removed after the build per the data-size rule — as the plan allows |
| Orchestrator validate | `python agents/orchestrator.py --day 13 validate` | **11/11 green** (re-run by the coder after the two fixes; tester confirms the tree is unchanged since) |

## Manual validation of one metric (independent of the processed CSVs)

**ActBlue (C00401224) receipts, straight from the committed
`webk24.zip`:** raw bulk value **$3,821,173,165.20** — exactly equal to
`committees.csv` and to the README's $3,821.2M. The raw `webk` receipts
sum over all 12,379 rows is $23,249,449,226.37; the processed
committee total ($22,724,587,172.77, identical in `committees.csv` and
`data_source.json`) is lower by the 12 excluded principal committees
($524.8M) plus the cleaned-out rows, as documented.

## README number accuracy (spot-checked against committed CSVs)

All match at the stated precision: candidate receipts $6,503,148,091.92
($6,503.1M); disbursements $6,728,272,984.00 ($6,728.3M); 4,376 with
totals; top-2 share 36.14% (36.1%); median receipts $814.36 ($814);
small-dollar share 32.83% (32.8%) over 2,259 split-covered candidates;
top state PA $2,525.2M; median burn rate 0.997; 532 candidates with
burn rate > 1.

## Chart legibility (all 4 viewed)

- 01 receipts by office/party: legible; all 9 values readable
  (President DEM $2.37B, REP $262.5M, Other $89.9M; Senate DEM $916.0M,
  REP $538.8M; House DEM $1.24B, REP $1.00B).
- 02 top candidates: legible after the coder's label fix — "$1.18B
  (18.1%)" fits in full for both Harris and Biden.
- 03 funding mix: legible; segment labels (34%/18%/48% President,
  46%/25%/29% Senate, 42%/18%/40% House) and the $2.66B/$1.42B/$2.21B
  split-subset totals all readable; coverage footnote present.
- 04 state totals: legible; all 15 states with n and dollar labels
  (PA $2.53B down to NJ $98.8M).

## Defects found

**None.** No code defects, no number errors, no legibility problems
remain. Two observations (not defects):

1. The dashboard screenshot is 968,319 bytes — under the 1 MB/file
   rule, but close to it. It is a fixed capture, not a growing file.
2. The notebook's committed outputs now show the join re-run *skipped*
   (the raw `.txt` files were deleted after the build to satisfy the
   data-size rule). The join itself was verified in the coder's run
   (3,643 principals from cn + 72 filled from ccl = 3,714) and is
   recorded in the checkpoint and `data/README.md`.

## Verdict

**PASS — release-ready.** The tree is handed to the Optimizer with no
defects to fix.
