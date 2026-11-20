"""Pure finance functions for the Day 13 Election Campaign Finance Tracker.

No I/O, no network — every function here is unit-tested in
``tests/test_pipeline.py``. Money is nominal USD as filed with the FEC;
nothing is annualised, imputed or netted here.
"""

from __future__ import annotations

import pandas as pd

#: Tolerance for the cash-identity check, in dollars.
CASH_IDENTITY_TOLERANCE_USD = 0.01


def small_dollar_share(itemized: float, unitemized: float) -> float | None:
    """Unitemized share of individual contributions.

    A funding-mix descriptor only — never a donor headcount. Returns
    ``None`` when there are no individual contributions at all.
    """
    total = itemized + unitemized
    if total <= 0:
        return None
    return unitemized / total


def burn_rate(receipts: float, disbursements: float) -> float | None:
    """Disbursements divided by receipts.

    Descriptive only; values above 1 are possible (spending down
    prior-cycle cash) and are not errors. Returns ``None`` when receipts
    are not positive, so a zero-receipts row never yields a bogus rate.
    """
    if receipts <= 0:
        return None
    return disbursements / receipts


def other_receipts(receipts: float, individual: float) -> float:
    """Receipts minus individual contributions (PAC money, party transfers,
    candidate loans, other). Reported as a residual, labelled as such."""
    return receipts - individual


def party_share(part: float, total: float) -> float:
    """A party's share of a total. Returns 0.0 for a zero total."""
    if total <= 0:
        return 0.0
    return part / total


def top_n_share(amounts: pd.Series, n: int) -> float:
    """Share of the total held by the largest ``n`` values."""
    total = float(amounts.sum())
    if total <= 0:
        return 0.0
    return float(amounts.nlargest(n).sum()) / total


def principal_committees(candidates: pd.DataFrame) -> set[str]:
    """The set of principal campaign committee IDs from a candidate table.

    Used to exclude principal committees from the committee-level tables
    (plan §2.0, amended). Blank/missing IDs are ignored.
    """
    ids = candidates["principal_committee_id"].dropna()
    ids = ids[ids.astype(str).str.strip() != ""]
    return set(ids.astype(str))


def check_cash_identity(df: pd.DataFrame) -> pd.DataFrame:
    """Rows whose cash identity fails: cash_bop + receipts - disbursements
    must equal cash_cop within ``CASH_IDENTITY_TOLERANCE_USD``.

    The identity is the proof that the headerless bulk column layout
    (plan §3.1b) is right; a failing row means the layout is wrong.
    Returns the failing rows (empty when the layout is correct)."""
    expected = df["cash_bop"] + df["receipts"] - df["disbursements"]
    diff = (expected - df["cash_cop"]).abs()
    return df[diff > CASH_IDENTITY_TOLERANCE_USD]


def summarise_party_office(candidates: pd.DataFrame) -> pd.DataFrame:
    """One row per (party, office) with totals (plan §4.4).

    Candidates without totals contribute to ``n_candidates`` but not to
    the money columns. Parties are taken as filed; nothing is dropped.
    """
    rows: list[dict[str, object]] = []
    grouped = candidates.groupby(["party", "office"], dropna=False)
    total_receipts = float(candidates["receipts"].fillna(0).sum())
    for (party, office), group in grouped:
        with_totals = group[group["has_totals"]]
        receipts = float(with_totals["receipts"].fillna(0).sum())
        disbursements = float(with_totals["disbursements"].fillna(0).sum())
        # Funding-mix sums cover the split subset ONLY (candidates with a
        # valid itemized/unitemized split). Summing fillna(0) over the
        # rest would silently understate the mix, so the subset and its
        # receipts are reported alongside.
        split = with_totals[with_totals["individual_unitemized_contributions"].notna()]
        receipts_with_split = float(split["receipts"].fillna(0).sum())
        indiv = float(split["individual_contributions"].fillna(0).sum())
        itemized = float(split["individual_itemized_contributions"].fillna(0).sum())
        unitemized = float(split["individual_unitemized_contributions"].fillna(0).sum())
        median_receipts = (
            float(with_totals["receipts"].median())
            if len(with_totals)
            else float("nan")
        )
        top_id = ""
        if len(with_totals):
            top_row = with_totals.sort_values(
                ["receipts", "candidate_id"], ascending=[False, True]
            ).iloc[0]
            top_id = str(top_row["candidate_id"])
        rows.append(
            {
                "party": party,
                "office": office,
                "n_candidates": len(group),
                "n_with_totals": len(with_totals),
                "n_with_split": len(split),
                "receipts": receipts,
                "receipts_with_split": receipts_with_split,
                "disbursements": disbursements,
                "receipts_share": party_share(receipts, total_receipts),
                "individual_contributions": indiv,
                "individual_itemized": itemized,
                "individual_unitemized": unitemized,
                "small_dollar_share": small_dollar_share(itemized, unitemized),
                "median_receipts": median_receipts,
                "top_candidate_id": top_id,
            }
        )
    out = pd.DataFrame(rows)
    # Deterministic order: receipts desc, then party/office asc — ties in
    # receipts (many $0 rows) must not reorder between runs (the offline
    # reproduction test compares positionally).
    out = out.sort_values(
        ["receipts", "party", "office"], ascending=[False, True, True]
    ).reset_index(drop=True)
    return out


def summarise_states(candidates: pd.DataFrame) -> pd.DataFrame:
    """One row per state with candidate receipts (plan §4.4).

    Totals and shares only — figures are NOT population-adjusted, and the
    dashboard/README carry that footnote on every state surface. The
    non-state codes "00" (presidential candidates with no state on
    file) and "US" are excluded — they are not states — and the
    pipeline counts the excluded candidates in data_source.json.
    """
    rows: list[dict[str, object]] = []
    total_receipts = float(candidates["receipts"].fillna(0).sum())
    grouped = candidates.groupby("state", dropna=False)
    for state, group in grouped:
        if pd.isna(state) or state in ("00", "US"):
            continue
        with_totals = group[group["has_totals"]]
        receipts = float(with_totals["receipts"].fillna(0).sum())
        disbursements = float(with_totals["disbursements"].fillna(0).sum())
        median_receipts = (
            float(with_totals["receipts"].median())
            if len(with_totals)
            else float("nan")
        )
        top_id = ""
        if len(with_totals):
            top_row = with_totals.sort_values(
                ["receipts", "candidate_id"], ascending=[False, True]
            ).iloc[0]
            top_id = str(top_row["candidate_id"])
        rows.append(
            {
                "state": state,
                "n_candidates": len(group),
                "n_with_totals": len(with_totals),
                "receipts": receipts,
                "disbursements": disbursements,
                "receipts_share": party_share(receipts, total_receipts),
                "median_receipts": median_receipts,
                "top_candidate_id": top_id,
            }
        )
    out = pd.DataFrame(rows)
    # Deterministic order: receipts desc, then state asc (same reason as
    # summarise_party_office above).
    out = out.sort_values(["receipts", "state"], ascending=[False, True]).reset_index(
        drop=True
    )
    return out


def top_n(df: pd.DataFrame, column: str, n: int) -> pd.DataFrame:
    """Top ``n`` rows by ``column`` (descending), ties broken by the first
    ID-like column ascending so the result is deterministic."""
    id_col = next(
        (c for c in ["candidate_id", "committee_id"] if c in df.columns),
        df.columns[0],
    )
    ranked = df.sort_values([column, id_col], ascending=[False, True]).head(n)
    ranked = ranked.copy()
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    return ranked.reset_index(drop=True)
