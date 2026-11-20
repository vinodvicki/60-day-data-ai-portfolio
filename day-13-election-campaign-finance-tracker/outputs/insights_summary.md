# Day 13 — Election Campaign Finance Tracker: Insights

2024 US federal election cycle, as filed with the FEC. All figures are
reported dollars; nothing here claims money caused any election outcome.
Full methods and caveats: `README.md`, `data/README.md`.

## Finding 1 — The presidential race is most of the candidate money, and two candidates are most of that

Candidates raised **$6,503.1M** in the cycle. Presidential candidates
account for $2,718.2M (41.8%), House $2,275.5M (35.0%), Senate
$1,509.5M (23.2%). Within that, Harris and Biden each report
**$1,175.2M (18.07%)** — together 36.1% of all candidate receipts —
because they share principal committee C00703975 (Harris Victory Fund);
the cycle total therefore counts their shared ~$1.18B twice. The next
candidate, Sherrod Brown (Senate, OH), raised $96.5M — less than a
twelfth of either. The top 10 candidates take 45.7%. At the other end,
the median candidate raised **$814** and 2,116 of the 4,376 candidates
with totals raised **$0**: the filed universe is a few very large
campaigns plus thousands of paper candidacies.

*Chart: `outputs/charts/02_top_candidates.png`.*

## Finding 2 — Individuals are the majority of candidate money, and about a third of it is small-dollar

Of the 2,259 candidates with a published itemized/unitemized split
($6,286.0M of receipts), individuals contributed **$3,734.5M (59.4%)**:
$2,508.4M itemized (donations over $200, donor disclosed) and
**$1,226.1M unitemized (≤ $200), a 32.8% small-dollar share**. The
remaining $2,551.6M came from other sources (PAC money, party
transfers, candidate loans, other receipts). Small-dollar share is
highest for Senate Democrats (36.1%) and presidential Democrats
(34.6%), lowest for House Republicans (28.1%). The split covers only
2,259 of 4,376 candidates with totals — the other 2,117 have no split
on record, so the mix describes the covered subset, not the cycle.

*Chart: `outputs/charts/03_funding_mix.png`.*

## Finding 3 — Committee money is bigger than candidate money, and it flows through two conduits

Non-candidate committees raised **$22,724.6M** — 3.5× the candidate
total (the two universes overlap through transfers and must never be
added). Hybrid PACs lead ($7,074.5M), then super PACs ($5,100.4M),
nonqualified PACs ($3,664.6M) and qualified party committees
($3,416.6M). Two online fundraising conduits dominate the table:
**ActBlue $3,821.2M (16.8% of committee receipts)** and WinRed
$1,686.5M (7.4%). The largest party committee, the DNC, raised
$683.7M; the RNC $475.8M. The committee file is also where the cycle's
concentration lives: the median committee raised $35,279, while 2,318
of 10,102 raised $0.

*Chart: `outputs/charts/01_receipts_by_office_party.png`.*

## Finding 4 — The state ranking is a headquarters map, not a donor map

PA leads the state table at **$2,525.2M (38.8%)**, then CA $460.6M
(7.1%), TX $312.7M (4.8%), AZ $228.6M (3.5%) and MD $208.5M (3.2%).
PA's lead is the Biden/Harris campaign HQ in Philadelphia — state is
the candidate's mailing-address state as filed, and the two
presidential campaigns alone are $2,350.4M of PA's $2,525.2M. State
totals are not population-adjusted and say nothing about where donors
live. 64 presidential candidates with no usable state on file are
excluded from the table.

*Chart: `outputs/charts/04_state_totals.png`.*

## Finding 5 — Candidates spent slightly more than they raised, and the cash pile is one filing

Candidates disbursed **$6,728.3M** against $6,503.1M raised — a median
burn rate of 0.997, with 532 candidates (12.2%) spending more than
they raised (normal for campaigns spending down prior-cycle cash).
Presidential candidates disbursed $3,038.4M, more than House
($2,141.5M) and Senate ($1,548.4M) combined. The reported $1,373.5M
cash on hand is misleading as a total: **$775.8M (56.5%) is a single
filing** (Norris, P40010415) that reports $775.8M cash on $35.4M of
receipts and fails the cash identity check. Excluding it, candidate
cash on hand is **$597.7M**. Candidates owe $458.8M in debts as filed.

## Recommendation (analytical next step — never investment advice)

The next useful cut is **donor-level**: the itemized contributions
file (`indiv24`) names every donor over $200, which would let the
small-dollar story be tested against actual donor counts and
geography instead of aggregates — and would show whether PA's lead
survives once headquarters addresses are separated from donor
addresses. That file is large (tens of millions of rows) and needs a
streaming/aggregated build, so it is a follow-up project, not part of
this day.

## Limitations

- Candidate ($6,503.1M) and committee ($22,724.6M) totals overlap
  through transfers; adding them double-counts. The Biden/Harris
  shared committee double-counts ~$1.18B inside the candidate total.
- The funding mix covers 2,259 of 4,376 candidates with totals.
- No per-capita figures (no Census key); state rankings reflect where
  candidates file from.
- No outcome variable; no causal claims.
- Filed data, warts included: 385 of 2,378 candidate summaries fail
  the cash identity; Norris and Gambert are reported as filed.
