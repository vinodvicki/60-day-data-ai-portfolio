# Day 12 — Customer Segmentation Engine: Insights

**Data:** UCI Online Retail (Chen 2015), DOI 10.24432/C5BW33, CC BY 4.0 —
historical 2010–2011 data. 541,909 raw rows → 527,795 cleaned rows,
£10,283,243.98 cleaned revenue, 4,334 identified customers, snapshot
2011-12-10. RFM scores are relative to this customer base, not absolute.
**Decider (plan §2.0):** KMeans on log1p + scaled R/F/M decides every
segment assignment; RFM scores name and explain; SBC is a cross-check.

## Finding 1 — Which customer groups does this retailer actually have?

Two segments, starkly unequal. **Champions: 1,661 customers (38.3%)**
drive **£7,436,335.44 — 84.9% of attributed revenue** (72.3% of total
cleaned revenue). **Hibernating: 2,673 customers (61.7%)** account for
only **£1,324,731.21 — 15.1% of attributed revenue**. The median
customer bought 51 days ago, twice, for £668.13. Champions' median
profile is 17 days since last order, 6 orders, £2,044.87 spend (mean
£4,477.02); Hibernating's is 97 days, 1 order, £358.38 (mean £495.60).
RFM scores spread almost evenly from 3 to 15 (331 customers score 3,
348 score 15), so the score distribution alone does not reveal the
split — the clustering does. The top customer (14646) spent £279,138.02
across 72 orders. (Chart 01, Chart 03.)

## Finding 2 — Who is worth protecting, who is slipping away, and who is already gone?

**Champions are worth protecting:** recent (median 17 days), frequent
(median 6 orders) and high-spending — £7.44m of revenue sits with them.
**Hibernating customers are already mostly gone:** median 97 days since
their last order and a single order each; 1,505 customers (34.7% of the
base) bought exactly once and never returned. Their £1.32m of revenue
will not repeat without action. A further **£1,522,177.33 (14.80% of
cleaned revenue) has no CustomerID at all** and cannot be attributed to
any segment — it is shown as its own line, not hidden inside the
segments. The SBC cross-check agrees with KMeans for only **51.5%** of
multi-order customers (1,458 of 2,829): most customers are Intermittent
(2,175, 50.2%), with only 59 Smooth and 88 Erratic — this retailer's
customers order irregularly, so demand-pattern quadrants do not line up
with value segments. The disagreement is reported, not averaged away,
and SBC never overrides a KMeans assignment. (Chart 02, Chart 04.)

## Finding 3 — What should the retailer do differently for each group?

Exactly one tailored action per segment, each with the £ at stake
(= the segment's revenue). No second action, no action without a £
figure.

| Segment | Customers | Revenue £ | Action | £ at stake |
|---|---:|---:|---|---:|
| Champions | 1,661 | £7,436,335.44 | Protect them first: VIP retention — early access, a personal thank-you and priority service. | £7,436,335.44 to protect |
| Hibernating | 2,673 | £1,324,731.21 | Reactivate cheaply or let go: one low-cost reactivation email featuring what's new since they last bought. | £1,324,731.21 already lapsed |
| Unattributed (no CustomerID) | — | £1,522,177.33 | — (cannot be attributed to any segment) | £1,522,177.33 unattributed |

## Limitations

- **Historical data:** 2010–2011 — the segments describe that year, not
  today; no claim is made about current customers.
- **Relative scores:** RFM scores are relative to this customer base;
  recompute if the base changes.
- **VAT status unknown:** the dataset does not state whether prices
  include VAT.
- **Unattributed revenue:** 14.80% of cleaned revenue (£1,522,177.33)
  has no CustomerID and is excluded from every segment.
- **SBC/KMeans disagreement:** agreement is only 51.5% over multi-order
  customers; the two methods genuinely disagree about nearly half the
  comparable base.
- **Coarse split:** k = 2 is what the silhouette rule selects on this
  data (0.4330 vs 0.3374 for k = 3), so "Hibernating" mixes one-time
  buyers with lapsed repeat buyers; a finer k would separate them, but
  the plan's rule, not preference, chose k = 2.
