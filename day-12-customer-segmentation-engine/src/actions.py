"""Exactly one tailored action per segment (plan §4.5).

Each action names the segment, the behaviour it targets, and the £ at
stake (``gbp_at_stake`` = the segment's ``revenue_gbp``): revenue to
protect for Champions / Loyal / Big Spenders, revenue at risk or
already lapsed for At Risk / Hibernating / Lost, revenue to grow for
Potential Loyalists / New Customers. Pure functions, no I/O, no network.
"""

import pandas as pd

_ACTION_TEMPLATES = {
    "Champions": (
        "Protect them first: VIP retention — early access, a personal "
        "thank-you and priority service — to protect £{gbp:,.2f} of "
        "revenue from the retailer's best customers."
    ),
    "Loyal Customers": (
        "Keep them buying: a loyalty reward and replenishment reminders "
        "for their regular lines — to protect £{gbp:,.2f} of steady "
        "revenue."
    ),
    "Big Spenders": (
        "Grow the basket, not the frequency: curated high-value bundles "
        "and a spend-based perk — to protect £{gbp:,.2f} of "
        "high-value revenue."
    ),
    "Potential Loyalists": (
        "Convert the momentum: a second-purchase nudge with a small "
        "incentive on a complementary line — to grow £{gbp:,.2f} of "
        "recent revenue into repeat revenue."
    ),
    "New Customers": (
        "Onboard, don't discount hard: a welcome sequence showing the "
        "range and a first-repeat incentive — to grow £{gbp:,.2f} of "
        "first-purchase revenue into a second order."
    ),
    "At Risk": (
        "Win them back now: a targeted win-back offer on the lines they "
        "used to buy, before they lapse — £{gbp:,.2f} of revenue is "
        "at risk."
    ),
    "Hibernating": (
        "Reactivate cheaply or let go: one low-cost reactivation email "
        "featuring what's new since they last bought — £{gbp:,.2f} of "
        "revenue has already lapsed and will not repeat without action."
    ),
    "Lost": (
        "Stop spending to reach them: remove from paid campaigns and "
        "keep only the cheapest occasional touch — £{gbp:,.2f} of "
        "revenue has already lapsed; do not chase it with costly offers."
    ),
}


def gbp_at_stake(profile_row: pd.Series) -> float:
    """£ at stake for a segment = its revenue (plan §4.5)."""
    return float(profile_row["revenue_gbp"])


def action_for(segment: str, profile_row: pd.Series) -> str:
    """The exactly-one tailored action for ``segment``.

    The Unattributed row has no action ("—"). Unknown segment names
    get a generic action that still embeds the £ at stake.
    """
    if segment == "Unattributed (no CustomerID)":
        return "—"
    gbp = gbp_at_stake(profile_row)
    template = _ACTION_TEMPLATES.get(segment)
    if template is None:
        return (
            f"Review this segment's behaviour and target it with one "
            f"tailored offer — £{gbp:,.2f} of revenue is at stake."
        )
    return template.format(gbp=gbp)


def build_actions(segment_profile: pd.DataFrame) -> pd.DataFrame:
    """Fill ``action`` + ``gbp_at_stake`` for every segment row."""
    out = segment_profile.copy()
    out["gbp_at_stake"] = out.apply(gbp_at_stake, axis=1)
    out["action"] = [action_for(str(row["segment"]), row) for _, row in out.iterrows()]
    return out
