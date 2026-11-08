"""Day 4 — YouTube Video Performance Analyzer: pure KPI / grouping functions.

No I/O, no network. All definitions are fixed by plan.md §4 and must not
be re-tuned after seeing the data:

- views_per_day = view_count / days_since_publish (minimum 1 day).
- engagement_rate = (like_count + comment_count) / view_count.
- Duration buckets: short <= 60s, short_form 61-300s, medium 301-900s,
  long 901-1800s, deep_dive > 1800s.
- Topic: deterministic keyword match on lower-cased title + tags +
  description, first match wins in the priority order
  python -> sql -> ai_ml -> bi_viz -> career -> general -> other.
- Format: tutorial before explainer, else other.
- High performers = top quartile of views_per_day.
- Medians, never means, for every views/engagement comparison.
- Missing like/comment/subscriber counts stay NaN, never 0.
"""

from __future__ import annotations

import re
from datetime import date

import pandas as pd

FETCH_DATE = date(2026, 11, 8)

DURATION_PATTERN = re.compile(
    r"^P(?:(?P<days>\d+)D)?T(?:(?P<hours>\d+)H)?"
    r"(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?$"
)

TOPIC_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("python", ("python", "pandas", "numpy")),
    ("sql", ("sql", "mysql", "postgres")),
    (
        "ai_ml",
        (
            "machine learning",
            "artificial intelligence",
            " ai ",
            "llm",
            "chatgpt",
            "deep learning",
            "neural",
        ),
    ),
    (
        "bi_viz",
        (
            "power bi",
            "tableau",
            "excel",
            "dashboard",
            "visualization",
            "visualisation",
        ),
    ),
    ("career", ("career", "job", "salary", "interview", "roadmap")),
    ("general", ("data analytics", "data analyst", "data science")),
]

TUTORIAL_KEYWORDS = (
    "tutorial",
    "how to",
    "learn",
    "course",
    "beginner",
    "step by step",
)
EXPLAINER_KEYWORDS = ("explained", "what is", "introduction", "guide", "why")

TOPIC_LABELS = {
    "python": "Python",
    "sql": "SQL",
    "ai_ml": "AI & Machine Learning",
    "bi_viz": "BI & Visualisation",
    "career": "Career",
    "general": "General Data",
    "other": "Other",
}
FORMAT_LABELS = {
    "tutorial": "Tutorial",
    "explainer": "Explainer",
    "other": "Other format",
}
BUCKET_LABELS = {
    "short": "Shorts (≤ 60 s)",
    "short_form": "Short-form (1–5 min)",
    "medium": "Medium (5–15 min)",
    "long": "Long (15–30 min)",
    "deep_dive": "Deep-dive (> 30 min)",
}
BUCKET_ORDER = ["short", "short_form", "medium", "long", "deep_dive"]
TOPIC_ORDER = ["python", "sql", "ai_ml", "bi_viz", "career", "general", "other"]

CAUSAL_VERBS = ("will boost", "causes", "guarantees", "will increase")


def parse_duration_iso8601(duration: str) -> int:
    """Parse an ISO 8601 duration (``PT12M34S``) to seconds.

    Raises ValueError on unparseable input and on zero/negative results.
    """
    if not isinstance(duration, str):
        raise TypeError(f"duration must be a string, got {type(duration).__name__}")
    match = DURATION_PATTERN.match(duration.strip())
    if match is None:
        raise ValueError(f"unparseable ISO 8601 duration: {duration!r}")
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    days = int(match.group("days") or 0)
    total = days * 86400 + hours * 3600 + minutes * 60 + seconds
    if total <= 0:
        raise ValueError(f"duration must be positive, got {duration!r}")
    return total


def duration_bucket(duration_seconds: int) -> str:
    """Map a duration in seconds to its fixed bucket (plan §4.2)."""
    if duration_seconds <= 60:
        return "short"
    if duration_seconds <= 300:
        return "short_form"
    if duration_seconds <= 900:
        return "medium"
    if duration_seconds <= 1800:
        return "long"
    return "deep_dive"


def _search_text(title: str, tags: list[str], description: str) -> str:
    parts = [title or "", description or ""]
    parts.extend(tags or [])
    return (" " + " ".join(parts) + " ").lower()


def classify_topic(title: str, tags: list[str], description: str) -> str:
    """Deterministic keyword topic classification, priority order verbatim
    from plan §4.2. First match wins; nothing matches -> ``other``."""
    text = _search_text(title, tags, description)
    for topic, keywords in TOPIC_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return topic
    return "other"


def classify_format(title: str, tags: list[str]) -> str:
    """Format classification verbatim from plan §4.2: ``tutorial`` wins
    over ``explainer`` on overlap; otherwise ``other``."""
    text = _search_text(title, tags, "")
    if any(keyword in text for keyword in TUTORIAL_KEYWORDS):
        return "tutorial"
    if any(keyword in text for keyword in EXPLAINER_KEYWORDS):
        return "explainer"
    return "other"


def compute_kpis(videos_df: pd.DataFrame) -> pd.DataFrame:
    """Add every §4.1 KPI and §4.2 grouping to a cleaned video frame.

    Expects columns: video_id, title, channel_id, channel_title,
    published_at, view_count, like_count, comment_count,
    subscriber_count, duration_seconds, category_id, tags,
    description. ``published_at`` may be a string or datetime.
    Returns a new DataFrame (input untouched) with the KPI columns
    added, including the top-quartile ``high_performer`` flag.
    """
    df = videos_df.copy()
    published = pd.to_datetime(df["published_at"], utc=True)
    fetch_ts = pd.Timestamp(FETCH_DATE, tz="UTC")
    days = (fetch_ts - published).dt.days.clip(lower=1)
    df["days_since_publish"] = days.astype(int)
    df["views_per_day"] = df["view_count"] / df["days_since_publish"]
    df["engagement_rate"] = (df["like_count"] + df["comment_count"]) / df["view_count"]
    df["like_rate"] = df["like_count"] / df["view_count"]
    df["comment_rate"] = df["comment_count"] / df["view_count"]
    df["views_per_subscriber"] = df["view_count"] / df["subscriber_count"]
    df["duration_bucket"] = df["duration_seconds"].map(duration_bucket)
    df["topic"] = [
        classify_topic(title, tags, desc)
        for title, tags, desc in zip(df["title"], df["tags"], df["description"])
    ]
    df["format"] = [
        classify_format(title, tags) for title, tags in zip(df["title"], df["tags"])
    ]
    df["publish_hour_utc"] = published.dt.hour.astype(int)
    df["publish_hour_pacific"] = (published.dt.hour - 8) % 24
    df["publish_dow"] = published.dt.day_name()
    # Channel-size terciles on the sample's own subscriber percentiles.
    subs = df["subscriber_count"]
    lo, hi = subs.quantile(1 / 3), subs.quantile(2 / 3)

    def _size(value: float) -> str:
        if pd.isna(value):
            return "unknown"
        if value <= lo:
            return "small"
        if value <= hi:
            return "mid"
        return "large"

    df["channel_size"] = subs.map(_size)
    # High performers = top quartile of views_per_day.
    threshold = df["views_per_day"].quantile(0.75)
    df["high_performer"] = df["views_per_day"] >= threshold
    return df


def _median(series: pd.Series) -> float:
    return float(series.median()) if series.notna().any() else float("nan")


def build_recommendations(videos_df: pd.DataFrame) -> list[dict]:
    """Build evidence-cited recommendations from group medians (§4.4).

    Every recommendation cites its numbers and carries the descriptive,
    not-causal caveat. Groups with n < 10 are labelled thin-sample or
    omitted. No causal verbs are used anywhere.
    """
    df = videos_df
    n_total = len(df)
    overall_vpd = _median(df["views_per_day"])
    overall_eng = _median(df["engagement_rate"])
    caveat = (
        "Descriptive pattern in a relevance-ranked sample of "
        f"{n_total} videos — not a causal finding."
    )
    recs: list[dict] = []

    def _add(recommendation: str, evidence: str, sample_basis: str) -> None:
        recs.append(
            {
                "recommendation": recommendation,
                "evidence": evidence,
                "sample_basis": sample_basis,
                "caveat": caveat,
            }
        )

    # 1. Best duration bucket by median views per day.
    by_duration = df.groupby("duration_bucket")["views_per_day"].agg(
        ["median", "count"]
    )
    solid = by_duration[by_duration["count"] >= 10]
    if not solid.empty:
        best_bucket = str(solid["median"].idxmax())
        best = solid.loc[best_bucket]
        _add(
            f"In this sample, {BUCKET_LABELS[best_bucket].lower()} videos had "
            "the highest median views per day of any length group.",
            f"median {best['median']:,.0f} views/day "
            f"(n={int(best['count'])}) vs {overall_vpd:,.0f} overall "
            f"(n={n_total})",
            f"duration {BUCKET_LABELS[best_bucket]} "
            f"(n={int(best['count'])} of {n_total})",
        )
    # 2. Best topic by median views per day.
    by_topic = df.groupby("topic")["views_per_day"].agg(["median", "count"])
    solid_topics = by_topic[by_topic["count"] >= 10]
    if not solid_topics.empty:
        best_topic = str(solid_topics["median"].idxmax())
        best = solid_topics.loc[best_topic]
        _add(
            f"In this sample, {TOPIC_LABELS[best_topic]} videos had the "
            "highest median views per day of any solid topic group (n ≥ 10).",
            f"median {best['median']:,.0f} views/day "
            f"(n={int(best['count'])}) vs {overall_vpd:,.0f} overall "
            f"(n={n_total})",
            f"topic {TOPIC_LABELS[best_topic]} "
            f"(n={int(best['count'])} of {n_total})",
        )
    # 3. Best topic by median engagement rate.
    by_topic_eng = df.groupby("topic")["engagement_rate"].agg(["median", "count"])
    solid_eng = by_topic_eng[by_topic_eng["count"] >= 10]
    if not solid_eng.empty:
        best_topic = str(solid_eng["median"].idxmax())
        best = solid_eng.loc[best_topic]
        _add(
            f"In this sample, {TOPIC_LABELS[best_topic]} videos had the "
            "highest median engagement rate of any topic group.",
            f"median engagement {best['median'] * 100:.2f}% "
            f"(n={int(best['count'])}) vs {overall_eng * 100:.2f}% "
            f"overall (n={n_total})",
            f"topic {TOPIC_LABELS[best_topic]} "
            f"(n={int(best['count'])} of {n_total})",
        )
    # 4. Format comparison: tutorial vs explainer medians.
    by_format = df.groupby("format")["views_per_day"].agg(["median", "count"])
    if "tutorial" in by_format.index and "explainer" in by_format.index:
        tut = by_format.loc["tutorial"]
        exp = by_format.loc["explainer"]
        if int(tut["count"]) >= 10 and int(exp["count"]) >= 10:
            better = "tutorials" if tut["median"] >= exp["median"] else "explainers"
            _add(
                f"In this sample, {better} had the higher median views "
                "per day of the two main formats.",
                f"tutorials median {tut['median']:,.0f} views/day "
                f"(n={int(tut['count'])}); explainers median "
                f"{exp['median']:,.0f} views/day "
                f"(n={int(exp['count'])}); overall median "
                f"{overall_vpd:,.0f} views/day",
                f"format comparison (n={int(tut['count'] + exp['count'])} "
                f"of {n_total})",
            )
    # 5. High performers vs the rest: engagement comparison (direction
    # reported honestly — high performers do not always engage more).
    high = df[df["high_performer"]]
    rest = df[~df["high_performer"]]
    if len(high) >= 10 and len(rest) >= 10:
        hp_eng = _median(high["engagement_rate"])
        rest_eng = _median(rest["engagement_rate"])
        if hp_eng > rest_eng:
            direction = "also had a higher median engagement rate than the rest"
        elif hp_eng < rest_eng:
            direction = (
                "had a slightly lower median engagement rate than the "
                "rest — reach and engagement did not move together"
            )
        else:
            direction = "had about the same median engagement rate as the rest"
        _add(
            "In this sample, the top-quartile videos by views per day " f"{direction}.",
            f"top quartile median engagement "
            f"{hp_eng * 100:.2f}% "
            f"(n={len(high)}) vs "
            f"{rest_eng * 100:.2f}% for the "
            f"rest (n={len(rest)}); top-quartile median "
            f"{_median(high['views_per_day']):,.0f} views/day vs "
            f"{_median(rest['views_per_day']):,.0f} views/day",
            f"high performers (top quartile of views per day, "
            f"n={len(high)}) vs rest (n={len(rest)})",
        )
    # 6. Publish-time honesty note (only if a weekday/hour stands out).
    by_dow = df.groupby("publish_dow")["views_per_day"].agg(["median", "count"])
    solid_dow = by_dow[by_dow["count"] >= 10]
    if not solid_dow.empty:
        best_day = str(solid_dow["median"].idxmax())
        best = solid_dow.loc[best_day]
        _add(
            f"In this sample, videos published on {best_day}s had the "
            "highest median views per day of any weekday — treat this "
            "as a description of the sample, not a posting schedule.",
            f"median {best['median']:,.0f} views/day "
            f"(n={int(best['count'])}) vs {overall_vpd:,.0f} overall; "
            "the channel audience timezone is unknown, so no best "
            "time to post can be concluded from this",
            f"publish day of week {best_day} (n={int(best['count'])} " f"of {n_total})",
        )
    return recs


def check_causal_verbs(text: str) -> list[str]:
    """Return any forbidden causal verbs found in *text* (lower-cased)."""
    lowered = text.lower()
    return [verb for verb in CAUSAL_VERBS if verb in lowered]


__all__ = [
    "BUCKET_LABELS",
    "BUCKET_ORDER",
    "FETCH_DATE",
    "FORMAT_LABELS",
    "TOPIC_LABELS",
    "TOPIC_ORDER",
    "build_recommendations",
    "check_causal_verbs",
    "classify_format",
    "classify_topic",
    "compute_kpis",
    "duration_bucket",
    "parse_duration_iso8601",
]
