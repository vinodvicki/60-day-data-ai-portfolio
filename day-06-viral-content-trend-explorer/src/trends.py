"""Day 6 — Viral Content Trend Explorer: pure trend math.

No I/O, no network. All thresholds, windows and buckets are fixed by
plan.md §4 and must not be re-tuned after seeing results.

Design (plan.md §3.1): the YouTube Data API returns a current snapshot of
each video's statistics, not daily history. "Trend" here is a comparison
of two 30-day publish-date cohorts — Window B (prior, 2026-09-11 to
2026-10-11) vs Window A (recent, 2026-10-11 to 2026-11-10) — never a
record of views rising or falling over time.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

import pandas as pd

# ---------------------------------------------------------------------------
# Fixed constants (plan.md §4.1, §4.3, §4.5)
# ---------------------------------------------------------------------------

FETCH_DATE = datetime(2026, 11, 10, tzinfo=UTC)
WINDOW_B_START = datetime(2026, 9, 11, tzinfo=UTC)
WINDOW_A_START = datetime(2026, 10, 11, tzinfo=UTC)
WINDOW_A_END = datetime(2026, 11, 10, tzinfo=UTC)
AGE_GUARD_DAYS = 7
AGE_GUARD_SENSITIVITY_DAYS = 14
MIN_N_PER_WINDOW = 10
SHARE_CHANGE_THRESHOLD_PP = 3.0
VOLUME_GROWTH_THRESHOLD = 0.20
VELOCITY_MIXED_SIGNAL = 0.30

#: Topic taxonomy (Day 4 rule, plan.md §4.1). First match wins, in order.
#: Each entry: (topic, keywords). Matching is on lower-cased
#: title + tags + description.
TOPIC_RULES: list[tuple[str, list[str]]] = [
    ("python", ["python", "pandas", "numpy"]),
    ("sql", ["sql", "mysql", "postgres"]),
    (
        "ai_ml",
        [
            "machine learning",
            "artificial intelligence",
            " ai ",
            "llm",
            "chatgpt",
            "deep learning",
            "neural",
        ],
    ),
    (
        "bi_viz",
        ["power bi", "tableau", "excel", "dashboard", "visualization", "visualisation"],
    ),
    ("career", ["career", "job", "salary", "interview", "roadmap"]),
    ("general", ["data analytics", "data analyst", "data science"]),
]

TOPIC_ORDER = ["python", "ai_ml", "sql", "career", "bi_viz", "general", "other"]

TOPIC_LABELS = {
    "python": "Python",
    "ai_ml": "AI & Machine Learning",
    "sql": "SQL",
    "career": "Career",
    "bi_viz": "Business Intelligence & Visualisation",
    "general": "General Data Analytics",
    "other": "Other",
}

#: Weekly buckets anchored at the start of Window B (plan.md §4.3).
#: (label, start, end-exclusive); W9 is partial (5 days).
WEEK_BOUNDS: list[tuple[str, datetime, datetime]] = [
    ("W1", datetime(2026, 9, 11, tzinfo=UTC), datetime(2026, 9, 18, tzinfo=UTC)),
    ("W2", datetime(2026, 9, 18, tzinfo=UTC), datetime(2026, 9, 25, tzinfo=UTC)),
    ("W3", datetime(2026, 9, 25, tzinfo=UTC), datetime(2026, 10, 2, tzinfo=UTC)),
    ("W4", datetime(2026, 10, 2, tzinfo=UTC), datetime(2026, 10, 9, tzinfo=UTC)),
    ("W5", datetime(2026, 10, 9, tzinfo=UTC), datetime(2026, 10, 16, tzinfo=UTC)),
    ("W6", datetime(2026, 10, 16, tzinfo=UTC), datetime(2026, 10, 23, tzinfo=UTC)),
    ("W7", datetime(2026, 10, 23, tzinfo=UTC), datetime(2026, 10, 30, tzinfo=UTC)),
    ("W8", datetime(2026, 10, 30, tzinfo=UTC), datetime(2026, 11, 6, tzinfo=UTC)),
    ("W9", datetime(2026, 11, 6, tzinfo=UTC), datetime(2026, 11, 11, tzinfo=UTC)),
]

_DURATION_RE = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


# ---------------------------------------------------------------------------
# Topic assignment
# ---------------------------------------------------------------------------


def assign_topic(title: str, tags: list[str], description: str) -> str:
    """Deterministic keyword topic rule (plan.md §4.1), first match wins."""
    text = " ".join([title or "", " ".join(tags or []), description or ""]).lower()
    # Pad so the " ai " keyword only matches the standalone word.
    padded = f" {text} "
    for topic, keywords in TOPIC_RULES:
        for keyword in keywords:
            if keyword.startswith(" ") or keyword.endswith(" "):
                if keyword in padded:
                    return topic
            elif keyword in text:
                return topic
    return "other"


# ---------------------------------------------------------------------------
# Duration
# ---------------------------------------------------------------------------


def parse_duration(iso: str) -> int:
    """Parse an ISO 8601 duration (e.g. PT12M34S) to seconds."""
    match = _DURATION_RE.fullmatch((iso or "").strip())
    if not match:
        raise ValueError(f"unparseable duration: {iso!r}")
    hours, minutes, seconds = (int(g) if g else 0 for g in match.groups())
    total = hours * 3600 + minutes * 60 + seconds
    if total <= 0:
        raise ValueError(f"non-positive duration: {iso!r}")
    return total


def duration_bucket(seconds: int) -> str:
    """Day 4 duration buckets."""
    if seconds <= 60:
        return "Short"
    if seconds <= 300:
        return "Short-form"
    if seconds <= 900:
        return "Medium"
    if seconds <= 1800:
        return "Long"
    return "Deep-dive"


# ---------------------------------------------------------------------------
# Windows and weeks
# ---------------------------------------------------------------------------


def _as_datetime(value) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def assign_window(published_at) -> str:
    """Window A (recent) or B (prior); the 2026-10-11 boundary belongs to A."""
    published = _as_datetime(published_at)
    if published < WINDOW_B_START or published >= WINDOW_A_END:
        raise ValueError(f"published_at outside the two windows: {published_at!r}")
    return "A" if published >= WINDOW_A_START else "B"


def assign_week(published_at) -> str:
    """Weekly bucket W1–W9, anchored 2026-09-11."""
    published = _as_datetime(published_at)
    for label, start, end in WEEK_BOUNDS:
        if start <= published < end:
            return label
    raise ValueError(f"published_at outside the weekly buckets: {published_at!r}")


# ---------------------------------------------------------------------------
# Velocity
# ---------------------------------------------------------------------------


def days_since_publish(published_at, fetch_date: datetime = FETCH_DATE) -> int:
    """Whole days between publish and fetch, minimum 1 (never 0)."""
    published = _as_datetime(published_at)
    return max(1, (fetch_date - published).days)


def compute_views_per_day(
    view_count: int, days: int, min_age_days: int = AGE_GUARD_DAYS
) -> float | None:
    """Views per day; None below the minimum-age guard (plan.md §4.5)."""
    if days < min_age_days:
        return None
    return view_count / max(days, 1)


# ---------------------------------------------------------------------------
# Momentum
# ---------------------------------------------------------------------------


def topic_share(counts: dict, total: int) -> dict:
    """Topic share in percent (0–100) for each topic in ``counts``."""
    if total <= 0:
        return {topic: 0.0 for topic in counts}
    return {topic: count / total * 100 for topic, count in counts.items()}


def volume_growth(n_a: int, n_b: int) -> float | None:
    """(n_A - n_B) / n_B; None when there is no prior-window baseline."""
    if n_b == 0:
        return None
    return (n_a - n_b) / n_b


def share_change(share_a: float, share_b: float) -> float:
    """Share change in percentage points."""
    return share_a - share_b


def classify_topic(
    n_a: int,
    n_b: int,
    share_change_pp: float,
    growth: float | None,
) -> str:
    """Fixed-threshold classification (plan.md §4.5)."""
    if n_b == 0:
        return "no prior baseline"
    if n_a < MIN_N_PER_WINDOW or n_b < MIN_N_PER_WINDOW:
        return "insufficient data"
    if (
        share_change_pp >= SHARE_CHANGE_THRESHOLD_PP
        and growth is not None
        and growth >= VOLUME_GROWTH_THRESHOLD
    ):
        return "accelerating"
    if (
        share_change_pp <= -SHARE_CHANGE_THRESHOLD_PP
        and growth is not None
        and growth <= -VOLUME_GROWTH_THRESHOLD
    ):
        return "fading"
    return "stable"


def velocity_change(median_a: float | None, median_b: float | None) -> float | None:
    """Relative change in median views/day; None if the baseline is missing."""
    if median_a is None or median_b is None or median_b == 0:
        return None
    return (median_a - median_b) / median_b


def mixed_signal(classification: str, vel_change: float | None) -> bool:
    """True when volume and velocity disagree by more than 30% (§4.5)."""
    if vel_change is None:
        return False
    return (
        classification == "accelerating" and vel_change < -VELOCITY_MIXED_SIGNAL
    ) or (classification == "fading" and vel_change > VELOCITY_MIXED_SIGNAL)


def rolling_mean_2wk(weekly_counts: list[int]) -> list[float]:
    """2-week rolling mean: mean of the current and previous week's counts.

    The first week has no previous week, so its rolling value is its own
    count. Display aid only — never a classification input.
    """
    out: list[float] = []
    for i, count in enumerate(weekly_counts):
        if i == 0:
            out.append(float(count))
        else:
            out.append((weekly_counts[i - 1] + count) / 2)
    return out


# ---------------------------------------------------------------------------
# Table builders (pure functions over a cleaned video frame)
# ---------------------------------------------------------------------------


def _median_views_per_day(
    frame: pd.DataFrame, min_age: int
) -> tuple[float | None, int, float | None]:
    """Median views/day for age-eligible rows: (median, n, median age)."""
    eligible = frame[frame["days_since_publish"] >= min_age]
    if eligible.empty:
        return None, 0, None
    vpd = eligible["view_count"] / eligible["days_since_publish"]
    return (
        float(vpd.median()),
        len(eligible),
        float(eligible["days_since_publish"].median()),
    )


def build_trend_table(videos: pd.DataFrame) -> pd.DataFrame:
    """One row per topic with all momentum numbers (plan.md §6).

    ``videos`` needs columns: topic, window, view_count,
    days_since_publish. Returns the trend_table.csv shape.
    """
    rows: list[dict] = []
    totals = {window: int((videos["window"] == window).sum()) for window in ("A", "B")}
    for topic in TOPIC_ORDER:
        sub = videos[videos["topic"] == topic]
        n_a = int((sub["window"] == "A").sum())
        n_b = int((sub["window"] == "B").sum())
        share_a = n_a / totals["A"] * 100 if totals["A"] else 0.0
        share_b = n_b / totals["B"] * 100 if totals["B"] else 0.0
        change = share_change(share_a, share_b)
        growth = volume_growth(n_a, n_b)
        classification = classify_topic(n_a, n_b, change, growth)
        med_a, n_vel_a, age_a = _median_views_per_day(
            sub[sub["window"] == "A"], AGE_GUARD_DAYS
        )
        med_b, n_vel_b, age_b = _median_views_per_day(
            sub[sub["window"] == "B"], AGE_GUARD_DAYS
        )
        vel_7 = velocity_change(med_a, med_b)
        med_a14, _, _ = _median_views_per_day(sub[sub["window"] == "A"], 14)
        med_b14, _, _ = _median_views_per_day(sub[sub["window"] == "B"], 14)
        vel_14 = velocity_change(med_a14, med_b14)
        sensitive = (
            vel_7 is not None and vel_14 is not None and (vel_7 > 0) != (vel_14 > 0)
        )
        rows.append(
            {
                "topic": topic,
                "n_A": n_a,
                "n_B": n_b,
                "share_A": round(share_a, 2),
                "share_B": round(share_b, 2),
                "share_change_pp": round(change, 2),
                "volume_growth": round(growth, 4) if growth is not None else None,
                "median_views_per_day_A": med_a,
                "median_views_per_day_B": med_b,
                "median_age_A": age_a,
                "median_age_B": age_b,
                "velocity_n_A": n_vel_a,
                "velocity_n_B": n_vel_b,
                "velocity_change_7d": round(vel_7, 4) if vel_7 is not None else None,
                "velocity_change_14d": (
                    round(vel_14, 4) if vel_14 is not None else None
                ),
                "classification": classification,
                "mixed_signal": mixed_signal(classification, vel_7),
                "velocity_sensitive_to_guard": sensitive,
            }
        )
    return pd.DataFrame(rows)


def weekly_volume_table(videos: pd.DataFrame) -> pd.DataFrame:
    """Weekly publish volume per topic (rows = weeks W1–W9, cols = topics)."""
    weeks = [label for label, _, _ in WEEK_BOUNDS]
    table = pd.DataFrame(0, index=weeks, columns=TOPIC_ORDER, dtype=int)
    for week in weeks:
        sub = videos[videos["week"] == week]
        for topic in TOPIC_ORDER:
            table.loc[week, topic] = int((sub["topic"] == topic).sum())
    table.index.name = "week"
    return table


def sensitivity_check(videos: pd.DataFrame) -> dict:
    """Per-topic 7-day vs 14-day guard velocity directions (plan.md §4.5)."""
    result: dict[str, dict] = {}
    for topic in TOPIC_ORDER:
        sub = videos[videos["topic"] == topic]
        # Compute explicitly (median, n, age) tuples for clarity.
        med_a7, _, _ = _median_views_per_day(sub[sub["window"] == "A"], 7)
        med_b7, _, _ = _median_views_per_day(sub[sub["window"] == "B"], 7)
        med_a14, _, _ = _median_views_per_day(sub[sub["window"] == "A"], 14)
        med_b14, _, _ = _median_views_per_day(sub[sub["window"] == "B"], 14)
        change_7 = velocity_change(med_a7, med_b7)
        change_14 = velocity_change(med_a14, med_b14)
        direction_7 = (
            "up"
            if change_7 is not None and change_7 > 0
            else "down" if change_7 is not None and change_7 < 0 else "flat/undefined"
        )
        direction_14 = (
            "up"
            if change_14 is not None and change_14 > 0
            else "down" if change_14 is not None and change_14 < 0 else "flat/undefined"
        )
        result[topic] = {
            "velocity_change_7d": change_7,
            "velocity_change_14d": change_14,
            "direction_7d": direction_7,
            "direction_14d": direction_14,
            "flipped": direction_7 != direction_14
            and direction_7 in ("up", "down")
            and direction_14 in ("up", "down"),
        }
    return result


def backtest_holdout(weekly: pd.DataFrame) -> dict:
    """Holdout backtest (plan.md §4.6).

    ``weekly`` is the weekly_volume_table output (rows W1–W9, cols topics).
    Train = W1–W7: predict the topic with the highest topic_share growth
    from the first half (W1–W3) to the second half (W5–W7); test = W8:
    hit if the predicted topic is in the top 2 by topic_share in W8.
    """
    train = weekly.loc[["W1", "W2", "W3", "W4", "W5", "W6", "W7"]]
    first = train.loc[["W1", "W2", "W3"]].sum()
    second = train.loc[["W5", "W6", "W7"]].sum()
    growth: dict[str, float | None] = {}
    for topic in weekly.columns:
        growth[topic] = volume_growth(int(second[topic]), int(first[topic]))
    ranked = sorted(
        growth.items(),
        key=lambda kv: (kv[1] is None, -(kv[1] if kv[1] is not None else 0)),
    )
    predicted = ranked[0][0]
    w8 = weekly.loc["W8"]
    w8_total = int(w8.sum())
    w8_shares = {
        topic: (int(w8[topic]) / w8_total * 100 if w8_total else 0.0)
        for topic in weekly.columns
    }
    top2 = sorted(w8_shares, key=lambda t: -w8_shares[t])[:2]
    # Degenerate case: no train growth exists (every first-half count is
    # zero) or the test week is empty, so there is no prediction to check.
    # Report it as not computable (hit=None) rather than a spurious hit.
    computable = growth[predicted] is not None and w8_total > 0
    return {
        "predicted_topic": predicted,
        "predicted_growth": growth[predicted],
        "growth_by_topic": {k: v for k, v in growth.items()},
        "w8_share": w8_shares,
        "w8_top2": top2,
        "hit": (predicted in top2) if computable else None,
        "computable": computable,
    }
