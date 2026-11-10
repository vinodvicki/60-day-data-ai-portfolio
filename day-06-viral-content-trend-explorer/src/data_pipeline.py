"""Day 6 — Viral Content Trend Explorer: fetch -> clean -> metrics -> save.

Source: YouTube Data API v3 via the custom.youtube connector helper
(~/workspace/custom-connectors/custom.youtube/bin/youtube.py).
Two 30-day publish-date cohorts (prior 2026-09-11 -> 2026-10-11, recent
2026-10-11 -> 2026-11-10), 5 queries, order=date, 50/page, one page per
query-window. The API returns a current snapshot of each video's
statistics, not daily history — so these are cohort comparisons, not a
record of views rising or falling over time. No causal claims anywhere.

Fetch rules (see research_brief.md / plan.md):
- 10 search calls (100 units each) + batched videos calls (1 unit each,
  <= 50 IDs per call) + batched channels calls (1 unit each) + 5
  comment-threads calls (1 unit each, one page of 100 threads per video).
  Budget <= 1,018 units.
- >= 2 s between calls; one retry after 30 s on HTTP 5xx / timeout only;
  no retry on 403 quotaExceeded — stop and fall back.
- The API key is held by the connector and is NEVER put in any file,
  env var, log, command argument, or the repo. The helper is invoked
  as a subprocess; the pipeline never sees the key.
- If fetch fails and no cache exists, deterministic synthetic data
  (seed=42) is generated and clearly labelled SYNTHETIC everywhere.
  Synthetic output goes to data/raw/*_synthetic.json only — it never
  overwrites the live cache.
- Offline mode: `python3 src/data_pipeline.py --offline` (or
  `--use-cache`) uses only the committed data/raw/*.json cache, makes
  no network calls, never generates synthetic data, and exits
  non-zero if no cache exists. An offline/cache run never overwrites
  an existing live data_source.json — the live provenance record is
  preserved (D-2 fix, 2026-11-10).
"""

from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

try:  # run as a module: python -m src.data_pipeline
    from src.sentiment import is_non_latin, score_comment
    from src.trends import (
        AGE_GUARD_DAYS,
        FETCH_DATE,
        assign_topic,
        assign_week,
        assign_window,
        backtest_holdout,
        build_trend_table,
        days_since_publish,
        duration_bucket,
        parse_duration,
        sensitivity_check,
        weekly_volume_table,
    )
except ImportError:  # run as a script: python src/data_pipeline.py
    from sentiment import is_non_latin, score_comment  # type: ignore[no-redef]
    from trends import (  # type: ignore[no-redef]
        AGE_GUARD_DAYS,
        FETCH_DATE,
        assign_topic,
        assign_week,
        assign_window,
        backtest_holdout,
        build_trend_table,
        days_since_publish,
        duration_bucket,
        parse_duration,
        sensitivity_check,
        weekly_volume_table,
    )

HELPER = (
    Path.home()
    / "workspace"
    / "custom-connectors"
    / "custom.youtube"
    / "bin"
    / "youtube.py"
)

#: The five Day 4 queries, with file slugs (plan.md §3.4 — do not change).
QUERIES: list[tuple[str, str]] = [
    ("data analytics", "data_analytics"),
    ("machine learning tutorial", "machine_learning_tutorial"),
    ("Python data analysis", "python_data_analysis"),
    ("artificial intelligence explained", "artificial_intelligence_explained"),
    ("SQL tutorial", "sql_tutorial"),
]

WINDOWS = {
    "prior": ("2026-09-11T00:00:00Z", "2026-10-11T00:00:00Z"),
    "recent": ("2026-10-11T00:00:00Z", "2026-11-10T00:00:00Z"),
}
WINDOW_LABEL = {"prior": "B", "recent": "A"}
MAX_RESULTS = 50
FETCH_DATE_STR = "2026-11-10"
SLEEP_BETWEEN_CALLS = 2.0
RETRY_AFTER_SECONDS = 30.0

#: Sentiment snapshot topics (plan.md §3.3): one top video per topic,
#: Window A, age >= 7 days, comments enabled. "other" never contributes.
SENTIMENT_TOPICS = ["python", "ai_ml", "sql", "career", "bi_viz"]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DAY04_FRAME = (
    PROJECT_ROOT.parent
    / "day-04-youtube-video-performance-analyzer"
    / "data"
    / "processed"
    / "videos.csv"
)

# Set by main(); "live" | "cache" | "synthetic".
SOURCE = "live"


class FetchError(RuntimeError):
    """A YouTube helper call failed (code + reason, never the API key)."""


def _run_helper(args: list[str]) -> dict:
    """Run one helper call; one retry after 30 s on HTTP 5xx / timeout."""
    command = [sys.executable, str(HELPER), *args]
    last_error: FetchError | None = None
    for attempt in (1, 2):
        try:
            proc = subprocess.run(
                command, check=False, capture_output=True, text=True, timeout=60
            )
        except subprocess.TimeoutExpired as exc:
            last_error = FetchError(f"timeout after 60 s: {exc}")
            if attempt == 1:
                time.sleep(RETRY_AFTER_SECONDS)
                continue
            raise last_error from exc
        if proc.returncode == 0:
            return json.loads(proc.stdout)
        message = (proc.stderr or proc.stdout or "").strip()
        # The helper prints "HTTP {code} from {path}: {body[:500]}".
        code = message.split()[1] if message.startswith("HTTP ") else "?"
        last_error = FetchError(f"HTTP {code}: {message[:300]}")
        if code.startswith("5") and attempt == 1:
            time.sleep(RETRY_AFTER_SECONDS)
            continue
        raise last_error
    raise last_error  # pragma: no cover - loop always returns/raises


# ---------------------------------------------------------------------------
# Fetch (live)
# ---------------------------------------------------------------------------


def fetch_search_window(query: str, window: str) -> dict:
    """One search call: 50 newest videos in one query-window (100 units)."""
    start, end = WINDOWS[window]
    return _run_helper(
        [
            "search",
            "--query",
            query,
            "--max-results",
            str(MAX_RESULTS),
            "--order",
            "date",
            "--published-after",
            start,
            "--published-before",
            end,
        ]
    )


def fetch_video_details(video_ids: list[str]) -> dict:
    """Batched videos call, <= 50 IDs (1 unit). Returns {"items": [...]}."""
    items: list[dict] = []
    calls = 0
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        if calls:
            time.sleep(SLEEP_BETWEEN_CALLS)
        result = _run_helper(["videos", "--ids", ",".join(chunk)])
        calls += 1
        items.extend(result.get("items", []))
    return {"items": items, "calls": calls}


def fetch_channel_details(channel_ids: list[str]) -> dict:
    """Batched channels call, <= 50 IDs (1 unit). Returns {"items": [...]}."""
    items: list[dict] = []
    calls = 0
    for i in range(0, len(channel_ids), 50):
        chunk = channel_ids[i : i + 50]
        if calls:
            time.sleep(SLEEP_BETWEEN_CALLS)
        result = _run_helper(["channels", "--ids", ",".join(chunk)])
        calls += 1
        items.extend(result.get("items", []))
    return {"items": items, "calls": calls}


def fetch_sentiment_comments(video_id: str) -> dict:
    """One page of 100 newest top-level comment threads (1 unit)."""
    return _run_helper(
        [
            "comment-threads",
            "--video-id",
            video_id,
            "--max-results",
            "100",
            "--order",
            "time",
            "--text-format",
            "plainText",
        ]
    )


def fetch_all() -> tuple[dict, dict, dict, int]:
    """Fetch the 10 query-windows + batched details.

    Returns (search_raw, videos_raw, channels_raw, quota_units) where
    search_raw maps (slug, window) -> verbatim search response.
    """
    search_raw: dict[tuple[str, str], dict] = {}
    quota = 0
    first = True
    zero_windows = 0
    for query, slug in QUERIES:
        for window in ("prior", "recent"):
            if not first:
                time.sleep(SLEEP_BETWEEN_CALLS)
            first = False
            result = fetch_search_window(query, window)
            quota += 100
            search_raw[(slug, window)] = result
            n = len(result.get("items", []))
            if n == 0:
                zero_windows += 1
            print(f"  search {slug} {window}: {n} items (truncated={n == 50})")
    if zero_windows >= 3:
        raise RuntimeError(
            f"{zero_windows} of 10 query-windows returned 0 items — "
            "treating as a failed fetch (see research_brief §1.8)"
        )
    # Collect surviving IDs per window (dedupe happens in clean_videos,
    # but the detail fetch needs the ID list first).
    ids_by_window: dict[str, list[str]] = {"prior": [], "recent": []}
    seen: dict[str, set[str]] = {"prior": set(), "recent": set()}
    for (slug, window), result in search_raw.items():
        for item in result.get("items", []):
            snippet = item.get("snippet", {})
            if snippet.get("liveBroadcastContent") != "none":
                continue
            video_id = item.get("id", {}).get("videoId", "")
            if not video_id or video_id in seen[window]:
                continue
            seen[window].add(video_id)
            ids_by_window[window].append(video_id)
    all_ids = ids_by_window["prior"] + ids_by_window["recent"]
    time.sleep(SLEEP_BETWEEN_CALLS)
    videos_raw = fetch_video_details(all_ids)
    quota += videos_raw["calls"]
    print(
        f"  videos details: {len(videos_raw['items'])} items in "
        f"{videos_raw['calls']} call(s)"
    )
    channel_ids = sorted({item["snippet"]["channelId"] for item in videos_raw["items"]})
    time.sleep(SLEEP_BETWEEN_CALLS)
    channels_raw = fetch_channel_details(channel_ids)
    quota += channels_raw["calls"]
    print(
        f"  channels details: {len(channels_raw['items'])} items in "
        f"{channels_raw['calls']} call(s)"
    )
    return search_raw, videos_raw, channels_raw, quota


# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------


def load_day04_frame() -> pd.DataFrame:
    """Layer A context frame (read-only; never enters the momentum math)."""
    if not DAY04_FRAME.exists():
        return pd.DataFrame(columns=["video_id"])
    return pd.read_csv(DAY04_FRAME, dtype={"video_id": str})


def clean_videos(
    search_raw: dict[tuple[str, str], dict],
    videos_raw: dict,
    channels_raw: dict,
) -> tuple[pd.DataFrame, dict]:
    """Build the Layer B video frame from raw responses.

    Filter order (each step counted): candidates -> dedupe -> live/
    upcoming -> no viewCount. Returns (frame, counts).
    """
    counts = {
        "candidates": 0,
        "unique_after_dedupe": 0,
        "dropped_live_or_upcoming": 0,
        "dropped_no_view_count": 0,
        "final_videos": 0,
    }
    # Candidates: every search item, before any filter.
    for result in search_raw.values():
        counts["candidates"] += len(result.get("items", []))
    # Dedupe by videoId within each window; keep first occurrence and
    # its query of origin. A video appearing in both windows is kept in
    # the window containing its publishedAt.
    origin: dict[str, dict] = {}
    for (slug, window), result in search_raw.items():
        for item in result.get("items", []):
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId", "")
            if not video_id:
                continue
            if snippet.get("liveBroadcastContent") != "none":
                counts["dropped_live_or_upcoming"] += 1
                continue
            published_at = snippet.get("publishedAt", "")
            try:
                window_of_published = assign_window(published_at)
            except ValueError:
                counts["dropped_live_or_upcoming"] += 1
                continue
            key_window = WINDOW_LABEL[window]
            if video_id in origin:
                # Keep the window whose bounds contain publishedAt.
                if origin[video_id]["window"] != window_of_published:
                    origin[video_id]["window"] = window_of_published
                continue
            origin[video_id] = {
                "window": key_window,
                "query_origin": slug,
                "published_at": published_at,
            }
    counts["unique_after_dedupe"] = len(origin)

    details = {item["id"]: item for item in videos_raw.get("items", [])}
    subscribers = {
        item["id"]: item.get("statistics", {}).get("subscriberCount")
        for item in channels_raw.get("items", [])
    }
    rows: list[dict] = []
    for video_id, meta in origin.items():
        item = details.get(video_id)
        if item is None:
            counts["dropped_no_view_count"] += 1
            continue
        stats = item.get("statistics", {})
        if "viewCount" not in stats:
            counts["dropped_no_view_count"] += 1
            continue
        snippet = item.get("snippet", {})
        try:
            duration_seconds = parse_duration(
                item.get("contentDetails", {}).get("duration", "")
            )
        except ValueError:
            counts["dropped_no_view_count"] += 1
            continue
        published_at = snippet.get("publishedAt") or meta["published_at"]
        days = days_since_publish(published_at, FETCH_DATE)
        view_count = int(stats["viewCount"])
        like_count = (
            int(stats["likeCount"]) if stats.get("likeCount") is not None else None
        )
        comment_count = (
            int(stats["commentCount"])
            if stats.get("commentCount") is not None
            else None
        )
        sub_raw = subscribers.get(snippet.get("channelId", ""))
        subscriber_count = int(sub_raw) if sub_raw is not None else None
        topic = assign_topic(
            snippet.get("title", ""),
            snippet.get("tags") or [],
            snippet.get("description", ""),
        )
        views_per_day = view_count / days if days >= AGE_GUARD_DAYS else float("nan")
        engagement = (
            (like_count + comment_count) / view_count
            if like_count is not None and comment_count is not None and view_count > 0
            else float("nan")
        )
        rows.append(
            {
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "channel_id": snippet.get("channelId", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "published_at": published_at,
                "window": meta["window"],
                "week": assign_week(published_at),
                "topic": topic,
                "query_origin": meta["query_origin"],
                "view_count": view_count,
                "like_count": like_count,
                "comment_count": comment_count,
                "subscriber_count": subscriber_count,
                "duration_seconds": duration_seconds,
                "duration_bucket": duration_bucket(duration_seconds),
                "days_since_publish": days,
                "views_per_day": views_per_day,
                "engagement_rate": engagement,
                "like_rate": (
                    like_count / view_count
                    if like_count is not None and view_count > 0
                    else float("nan")
                ),
                "comment_rate": (
                    comment_count / view_count
                    if comment_count is not None and view_count > 0
                    else float("nan")
                ),
                "views_per_subscriber": (
                    view_count / subscriber_count if subscriber_count else float("nan")
                ),
                "is_shorts": duration_seconds <= 60,
            }
        )
    counts["final_videos"] = len(rows)
    columns = [
        "video_id",
        "title",
        "channel_id",
        "channel_title",
        "published_at",
        "window",
        "week",
        "topic",
        "query_origin",
        "view_count",
        "like_count",
        "comment_count",
        "subscriber_count",
        "duration_seconds",
        "duration_bucket",
        "days_since_publish",
        "views_per_day",
        "engagement_rate",
        "like_rate",
        "comment_rate",
        "views_per_subscriber",
        "is_shorts",
    ]
    frame = pd.DataFrame(rows, columns=columns)
    if not frame.empty:
        frame = frame.sort_values("published_at").reset_index(drop=True)
        assert frame["video_id"].is_unique, "duplicate videoId in final frame"
    return frame, counts


def pick_sentiment_videos(videos: pd.DataFrame) -> list[dict]:
    """Top video by views_per_day per sentiment topic in Window A.

    Eligible: Window A, age >= 7 days, views_per_day present. One per
    topic; a topic with no eligible video contributes none (no
    substitution from another topic or window).
    """
    picks: list[dict] = []
    recent = videos[videos["window"] == "A"]
    for topic in SENTIMENT_TOPICS:
        sub = recent[(recent["topic"] == topic) & recent["views_per_day"].notna()]
        if sub.empty:
            print(f"  sentiment: no eligible video for topic {topic}")
            continue
        top = sub.sort_values("views_per_day", ascending=False).iloc[0]
        picks.append(
            {
                "video_id": str(top["video_id"]),
                "title": str(top["title"]),
                "topic": topic,
                "views_per_day": float(top["views_per_day"]),
            }
        )
    return picks


def clean_comments(
    raw: dict[str, dict], picks: list[dict]
) -> tuple[pd.DataFrame, dict]:
    """Build the analysed comment frame from raw thread responses.

    Filter order (each step counted): owner -> empty -> non-Latin.
    Returns (frame, filter_counts).
    """
    counts = {
        "fetched": 0,
        "owner": 0,
        "empty": 0,
        "non_latin": 0,
        "analysed": 0,
    }
    pick_by_id = {p["video_id"]: p for p in picks}
    rows: list[dict] = []
    for video_id, result in raw.items():
        pick = pick_by_id.get(video_id)
        if pick is None:
            continue
        channel_id = ""
        for item in result.get("items", []):
            counts["fetched"] += 1
            thread = item.get("snippet", {})
            channel_id = thread.get("channelId", "")
            top = thread.get("topLevelComment", {}).get("snippet", {})
            comment_id = top.get("id") or item.get("id", "")
            # (1) Channel-owner comments are not audience sentiment.
            author_channel = (top.get("authorChannelId") or {}).get("value", "")
            if author_channel and author_channel == channel_id:
                counts["owner"] += 1
                continue
            text = top.get("textDisplay") or top.get("textOriginal") or ""
            # (2) Empty text carries no signal.
            if not text.strip():
                counts["empty"] += 1
                continue
            # (3) Non-Latin heuristic (stdlib unicodedata only).
            if is_non_latin(text):
                counts["non_latin"] += 1
                continue
            score, sentiment, scored_words = score_comment(text)
            rows.append(
                {
                    "comment_id": comment_id,
                    "video_id": video_id,
                    "video_title": pick["title"],
                    "topic": pick["topic"],
                    "author_display_name": top.get("authorDisplayName", ""),
                    "text": text,
                    "published_at": top.get("publishedAt", ""),
                    "like_count": int(top.get("likeCount") or 0),
                    "total_reply_count": int(thread.get("totalReplyCount") or 0),
                    "sentiment_score": score,
                    "sentiment": sentiment,
                    "scored_words": scored_words,
                    "language_flag": "latin",
                }
            )
    counts["analysed"] = len(rows)
    columns = [
        "comment_id",
        "video_id",
        "video_title",
        "topic",
        "author_display_name",
        "text",
        "published_at",
        "like_count",
        "total_reply_count",
        "sentiment_score",
        "sentiment",
        "scored_words",
        "language_flag",
    ]
    frame = pd.DataFrame(rows, columns=columns)
    if not frame.empty:
        frame = frame.sort_values("published_at").reset_index(drop=True)
    return frame, counts


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------


def save_outputs(
    videos: pd.DataFrame,
    comments: pd.DataFrame,
    trend_table: pd.DataFrame,
    search_raw: dict | None,
    videos_raw: dict | None,
    channels_raw: dict | None,
    comment_raw: dict | None,
    quota_units: int,
    counts: dict,
    comment_counts: dict,
    per_query_window: dict,
    overlap_with_day04: int,
    channel_concentration: dict,
    synthetic: bool = False,
) -> bool:
    """Write raw JSONs, processed CSVs and data_source.json.

    Returns True if data_source.json was written. An offline/cache run
    never overwrites an existing live provenance record (D-2 fix): if
    data_source.json already says source "live", it is left untouched
    and this returns False. A live or synthetic run always writes it.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    if synthetic:
        payload = {
            "synthetic": True,
            "seed": 42,
            "search": {
                f"{slug}_{window}": result
                for (slug, window), result in (search_raw or {}).items()
            },
            "videos_details": videos_raw,
            "channels_details": channels_raw,
            "comments": comment_raw,
        }
        (RAW_DIR / "videos_synthetic.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False)
        )
    else:
        for (slug, window), result in (search_raw or {}).items():
            (RAW_DIR / f"search_{slug}_{window}.json").write_text(
                json.dumps(result, indent=2, ensure_ascii=False)
            )
        (RAW_DIR / "videos_details.json").write_text(
            json.dumps(videos_raw, indent=2, ensure_ascii=False)
        )
        (RAW_DIR / "channels_details.json").write_text(
            json.dumps(channels_raw, indent=2, ensure_ascii=False)
        )
        for video_id, result in (comment_raw or {}).items():
            (RAW_DIR / f"comments_{video_id}.json").write_text(
                json.dumps(result, indent=2, ensure_ascii=False)
            )
    videos.to_csv(PROCESSED_DIR / "videos.csv", index=False)
    comments.to_csv(PROCESSED_DIR / "comments.csv", index=False)
    trend_table.to_csv(PROCESSED_DIR / "trend_table.csv", index=False)
    source = {
        "source": SOURCE,
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "synthetic": synthetic,
        "seed": 42 if synthetic else None,
        "fetch_date": FETCH_DATE_STR,
        "snapshot_dates": {
            "day04_frame": "2026-11-08",
            "fresh_fetch": FETCH_DATE_STR,
        },
        "windows": {
            "prior": list(WINDOWS["prior"]),
            "recent": list(WINDOWS["recent"]),
        },
        "queries": [query for query, _ in QUERIES],
        "max_results_per_query": MAX_RESULTS,
        "order": "date",
        "per_query_window": per_query_window,
        "video_count": len(videos),
        "channel_count": int(videos["channel_id"].nunique()) if not videos.empty else 0,
        "quota_units_used": quota_units,
        "api": "youtube-data-api-v3",
        "age_guard_days": AGE_GUARD_DAYS,
        "overlap_with_day04_frame": overlap_with_day04,
        "channel_concentration": channel_concentration,
        "counts": {
            **counts,
            "sentiment_videos": len(comment_raw or {}),
            "sentiment_comments_analysed": comment_counts["analysed"],
            "sentiment_comments_fetched": comment_counts["fetched"],
        },
        "comment_filters": comment_counts,
    }
    source_path = PROCESSED_DIR / "data_source.json"
    if SOURCE == "cache" and source_path.exists():
        try:
            existing_source = json.loads(source_path.read_text()).get("source")
        except (OSError, ValueError):
            existing_source = None
        if existing_source == "live":
            print(
                "preserving live data_source.json — an offline/cache run "
                'does not overwrite provenance (source stays "live")'
            )
            return False
    source_path.write_text(json.dumps(source, indent=2))
    return True


# ---------------------------------------------------------------------------
# Synthetic fallback (seed 42 — labelled SYNTHETIC everywhere downstream)
# ---------------------------------------------------------------------------

SYNTHETIC_TITLES = {
    "python": [
        "Python Data Analysis Tutorial for Beginners",
        "Learn Python Pandas for Data Analysis",
        "Python Numpy Tutorial — Data Analysis Basics",
    ],
    "ai_ml": [
        "Machine Learning Tutorial for Beginners",
        "Artificial Intelligence Explained Simply",
        "Deep Learning Neural Network Tutorial",
    ],
    "sql": [
        "SQL Tutorial for Beginners — Full Course",
        "Learn SQL Queries Step by Step",
        "MySQL Tutorial for Data Analysts",
    ],
    "career": [
        "Data Analyst Career Roadmap 2026",
        "How to Get a Data Analyst Job",
        "Data Analyst Interview Questions and Salary",
    ],
    "bi_viz": [
        "Power BI Dashboard Tutorial for Beginners",
        "Excel Data Analysis Full Course",
        "Tableau Visualization Tutorial",
    ],
    "general": [
        "What Is Data Analytics? Full Guide",
        "Data Science for Beginners Explained",
        "Data Analyst Full Course 2026",
    ],
}

SYNTHETIC_TEMPLATES = {
    "positive": [
        "This {topic} tutorial is amazing, thank you so much!",
        "Great explanation, finally I understand it",
        "Best video on this topic, really helpful",
        "Thank you, this {topic} course is excellent and clear",
        "Wonderful tutorial, I learned so much today",
        "Perfect explanation, love this channel",
    ],
    "neutral": [
        "What software is used in this video?",
        "Can anyone explain the part at 5 minutes?",
        "Is this {topic} tutorial good for beginners?",
        "What is the next video about?",
        "Just started learning {topic} today",
        "Came here from the previous video",
    ],
    "negative": [
        "This is so confusing and boring",
        "Terrible audio, I could not follow anything",
        "Worst tutorial, full of mistakes",
        "This {topic} video is unclear and too fast",
        "Bad explanation, I wasted my time here",
        "Horrible quality, disappointing video",
    ],
}


def generate_synthetic(seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Deterministic synthetic videos + comments (seed 42).

    300 videos in the Day 4 frame's proportions (python 150, ai_ml 85,
    sql 45, career 12, bi_viz 5, general 3), with a built-in trend by
    construction: python volume rising (30% of its videos in W1–W3,
    70% in W6–W9), sql falling (70% in W1–W3, 30% in W6–W9), other
    topics uniform. Sentiment: 5 videos x 100 template comments, mix
    45/35/20 positive/neutral/negative by construction. Synthetic trends
    are constructed by design, so accelerating/fading calls on synthetic
    data have no interpretation.
    """
    rng = random.Random(seed)
    proportions = {
        "python": 150,
        "ai_ml": 85,
        "sql": 45,
        "career": 12,
        "bi_viz": 5,
        "general": 3,
    }
    start = datetime(2026, 9, 11, tzinfo=UTC)
    end = datetime(2026, 11, 10, tzinfo=UTC)
    span_days = (end - start).days
    rows: list[dict] = []
    index = 0
    for topic, n in proportions.items():
        for _ in range(n):
            index += 1
            if topic == "python":
                # 30% in W1–W3 (days 0–20), 70% in W6–W9 (days 35–59).
                day = rng.randint(0, 20) if rng.random() < 0.30 else rng.randint(35, 59)
            elif topic == "sql":
                day = rng.randint(0, 20) if rng.random() < 0.70 else rng.randint(35, 59)
            else:
                day = rng.randint(0, span_days - 1)
            published = start + pd.Timedelta(days=day, hours=rng.randint(0, 23))
            view_count = int(
                min(5_000_000, max(100, rng.lognormvariate(math.log(50_000), 1.2)))
            )
            like_count = round(view_count * rng.uniform(0.02, 0.06))
            comment_count = round(view_count * rng.uniform(0.0005, 0.005))
            subscriber_count = int(
                min(10_000_000, max(1_000, rng.lognormvariate(math.log(100_000), 1.0)))
            )
            duration_seconds = int(
                min(3600, max(60, rng.lognormvariate(math.log(600), 0.8)))
            )
            days = days_since_publish(published, FETCH_DATE)
            title = rng.choice(SYNTHETIC_TITLES[topic])
            rows.append(
                {
                    "video_id": f"synthetic-{index:04d}",
                    "title": title,
                    "channel_id": f"UCsynthetic{index % 40:02d}",
                    "channel_title": f"Synthetic Channel {index % 40}",
                    "published_at": published.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "window": assign_window(published),
                    "week": assign_week(published),
                    "topic": topic,
                    "query_origin": "synthetic",
                    "view_count": view_count,
                    "like_count": like_count,
                    "comment_count": comment_count,
                    "subscriber_count": subscriber_count,
                    "duration_seconds": duration_seconds,
                    "duration_bucket": duration_bucket(duration_seconds),
                    "days_since_publish": days,
                    "views_per_day": (
                        view_count / days if days >= AGE_GUARD_DAYS else float("nan")
                    ),
                    "engagement_rate": (like_count + comment_count) / view_count,
                    "like_rate": like_count / view_count,
                    "comment_rate": comment_count / view_count,
                    "views_per_subscriber": view_count / subscriber_count,
                    "is_shorts": duration_seconds <= 60,
                }
            )
    videos = pd.DataFrame(rows).sort_values("published_at").reset_index(drop=True)
    picks = pick_sentiment_videos(videos)
    comment_raw: dict[str, dict] = {}
    for pick in picks:
        items: list[dict] = []
        plan = [("positive", 45), ("neutral", 35), ("negative", 20)]
        idx = 0
        for sentiment, count in plan:
            for _ in range(count):
                idx += 1
                text = rng.choice(SYNTHETIC_TEMPLATES[sentiment]).format(
                    topic=pick["topic"]
                )
                published = start + pd.Timedelta(days=rng.randint(0, span_days - 1))
                comment_id = f"synthetic-{pick['video_id']}-{idx:03d}"
                items.append(
                    {
                        "kind": "youtube#commentThread",
                        "id": comment_id,
                        "snippet": {
                            "channelId": "UCsynthetic",
                            "videoId": pick["video_id"],
                            "topLevelComment": {
                                "kind": "youtube#comment",
                                "id": comment_id,
                                "snippet": {
                                    "channelId": "UCsynthetic",
                                    "videoId": pick["video_id"],
                                    "textDisplay": text,
                                    "textOriginal": text,
                                    "authorDisplayName": f"Synthetic Commenter {idx:03d}",
                                    "authorChannelId": {"value": "UCsynthetic-author"},
                                    "likeCount": rng.randint(0, 200),
                                    "publishedAt": published.strftime(
                                        "%Y-%m-%dT%H:%M:%SZ"
                                    ),
                                    "updatedAt": published.strftime(
                                        "%Y-%m-%dT%H:%M:%SZ"
                                    ),
                                },
                            },
                            "canReply": True,
                            "totalReplyCount": rng.randint(0, 5),
                            "isPublic": True,
                        },
                    }
                )
        rng.shuffle(items)
        comment_raw[pick["video_id"]] = {"items": items}
    comments, _ = clean_comments(comment_raw, picks)
    return videos, comments


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


def _load_cache() -> tuple[dict, dict, dict] | None:
    """Load the committed raw JSONs. None if any search/detail file is missing.

    A synthetic file never satisfies this check — the cache is live data
    only (plan.md §3.5).
    """
    search_raw: dict[tuple[str, str], dict] = {}
    for _, slug in QUERIES:
        for window in ("prior", "recent"):
            path = RAW_DIR / f"search_{slug}_{window}.json"
            if not path.exists():
                return None
            search_raw[(slug, window)] = json.loads(path.read_text())
    videos_path = RAW_DIR / "videos_details.json"
    channels_path = RAW_DIR / "channels_details.json"
    if not videos_path.exists() or not channels_path.exists():
        return None
    return (
        search_raw,
        json.loads(videos_path.read_text()),
        json.loads(channels_path.read_text()),
    )


def _load_comment_cache(picks: list[dict]) -> dict[str, dict] | None:
    """Load committed comments_<video_id>.json for the picked videos."""
    raw: dict[str, dict] = {}
    for pick in picks:
        path = RAW_DIR / f"comments_{pick['video_id']}.json"
        if not path.exists():
            return None
        raw[pick["video_id"]] = json.loads(path.read_text())
    return raw


# ---------------------------------------------------------------------------
# Shared build (live / cache / synthetic converge here)
# ---------------------------------------------------------------------------


def _channel_concentration(videos: pd.DataFrame) -> dict:
    """Distinct channels and the largest single channel's share per window."""
    out: dict[str, dict] = {}
    for window in ("A", "B"):
        sub = videos[videos["window"] == window]
        if sub.empty:
            out[window] = {"distinct_channels": 0, "top_channel_share": None}
            continue
        counts = sub["channel_id"].value_counts(normalize=True)
        out[window] = {
            "distinct_channels": int(sub["channel_id"].nunique()),
            "top_channel": str(counts.index[0]),
            "top_channel_share": round(float(counts.iloc[0]) * 100, 2),
        }
    return out


def _sanity_report(videos: pd.DataFrame) -> None:
    """Sanity checks (plan.md §4.6): report, do not silently pass."""
    if videos.empty:
        print("WARNING: empty video frame")
        return
    median_engagement = videos["engagement_rate"].median()
    print(f"  sanity: median engagement_rate={median_engagement:.4f}")
    if not (0.005 <= median_engagement <= 0.08):
        print(
            "  WARNING: median engagement_rate outside the Day 4 sanity "
            "range 0.5–8% — definition/parsing checked, value reported "
            "as-is (plan §4.6)"
        )
    median_vpd = videos.loc[
        videos["days_since_publish"] >= AGE_GUARD_DAYS, "views_per_day"
    ].median()
    print(f"  sanity: median views_per_day (age >= 7d)={median_vpd:.1f}")
    if not (median_vpd > 0):
        raise RuntimeError("median views_per_day is not positive")


def _build_and_save(
    videos: pd.DataFrame,
    comments: pd.DataFrame,
    search_raw: dict | None,
    videos_raw: dict | None,
    channels_raw: dict | None,
    comment_raw: dict | None,
    quota_units: int,
    counts: dict,
    comment_counts: dict,
    per_query_window: dict,
    synthetic: bool = False,
) -> None:
    """Compute the trend table + validation and write all outputs."""
    day04 = load_day04_frame()
    overlap = (
        int(videos["video_id"].isin(set(day04["video_id"])).sum())
        if not day04.empty
        else 0
    )
    trend_table = build_trend_table(videos)
    weekly = weekly_volume_table(videos)
    backtest = backtest_holdout(weekly)
    sensitivity = sensitivity_check(videos)
    print("  trend table:")
    print(
        trend_table[
            [
                "topic",
                "n_A",
                "n_B",
                "share_change_pp",
                "volume_growth",
                "classification",
                "mixed_signal",
            ]
        ].to_string(index=False)
    )
    print(
        f"  backtest: predicted={backtest['predicted_topic']} "
        f"growth={backtest['predicted_growth']} W8 top-2="
        f"{backtest['w8_top2']} hit={backtest['hit']} "
        f"computable={backtest['computable']}"
    )
    flipped = [t for t, s in sensitivity.items() if s["flipped"]]
    print(f"  age-guard sensitivity flips: {flipped or 'none'}")
    _sanity_report(videos)
    wrote_source = save_outputs(
        videos,
        comments,
        trend_table,
        search_raw,
        videos_raw,
        channels_raw,
        comment_raw,
        quota_units,
        counts,
        comment_counts,
        per_query_window,
        overlap,
        _channel_concentration(videos),
        synthetic=synthetic,
    )
    print(
        f"wrote data/processed/videos.csv ({len(videos)} rows), "
        f"comments.csv ({len(comments)} rows), trend_table.csv, "
        + (
            f"data_source.json (source={SOURCE}, synthetic={synthetic})"
            if wrote_source
            else "data_source.json preserved (live record kept)"
        )
    )


def main() -> None:
    global SOURCE
    parser = argparse.ArgumentParser(description="Day 6 data pipeline")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="run from the committed cache, no network",
    )
    parser.add_argument("--use-cache", action="store_true", help="alias for --offline")
    args = parser.parse_args()

    if args.offline or args.use_cache:
        SOURCE = "cache"
        cached = _load_cache()
        if cached is None:
            raise SystemExit(
                "ERROR: --offline but no complete cache in data/raw/ "
                "(need all 10 search_<slug>_<window>.json files plus "
                "videos_details.json and channels_details.json)"
            )
        print("offline mode: using committed cache, no network")
        search_raw, videos_raw, channels_raw = cached
        videos, counts = clean_videos(search_raw, videos_raw, channels_raw)
        picks = pick_sentiment_videos(videos)
        comment_raw = _load_comment_cache(picks)
        if comment_raw is None:
            raise SystemExit(
                "ERROR: --offline but a sentiment video's "
                "comments_<video_id>.json is missing from data/raw/"
            )
        comments, comment_counts = clean_comments(comment_raw, picks)
        per_query_window = {
            f"{slug}_{window}": {
                "items": len(result.get("items", [])),
                "truncated": len(result.get("items", [])) == MAX_RESULTS,
            }
            for (slug, window), result in search_raw.items()
        }
        _build_and_save(
            videos,
            comments,
            search_raw,
            videos_raw,
            channels_raw,
            comment_raw,
            0,
            counts,
            comment_counts,
            per_query_window,
        )
        return

    SOURCE = "live"
    print("live mode: fetching 10 query-windows + details + comments")
    try:
        search_raw, videos_raw, channels_raw, quota = fetch_all()
    except (FetchError, RuntimeError) as exc:
        print(f"live fetch failed: {exc}")
        cached = _load_cache()
        if cached is not None:
            SOURCE = "cache"
            print("falling back to committed cache")
            search_raw, videos_raw, channels_raw = cached
            videos, counts = clean_videos(search_raw, videos_raw, channels_raw)
            picks = pick_sentiment_videos(videos)
            comment_raw = _load_comment_cache(picks)
            if comment_raw is None:
                raise SystemExit(
                    "ERROR: cache fallback but a sentiment video's "
                    "comments_<video_id>.json is missing"
                )
            comments, comment_counts = clean_comments(comment_raw, picks)
            per_query_window = {
                f"{slug}_{window}": {
                    "items": len(result.get("items", [])),
                    "truncated": len(result.get("items", [])) == MAX_RESULTS,
                }
                for (slug, window), result in search_raw.items()
            }
            _build_and_save(
                videos,
                comments,
                search_raw,
                videos_raw,
                channels_raw,
                comment_raw,
                0,
                counts,
                comment_counts,
                per_query_window,
            )
            return
        SOURCE = "synthetic"
        print("no cache — generating labelled synthetic data (seed 42)")
        videos, comments = generate_synthetic(seed=42)
        counts = {
            "candidates": 500,
            "unique_after_dedupe": 300,
            "dropped_live_or_upcoming": 0,
            "dropped_no_view_count": 0,
            "final_videos": len(videos),
        }
        comment_counts = {
            "fetched": 500,
            "owner": 0,
            "empty": 0,
            "non_latin": 0,
            "analysed": len(comments),
        }
        per_query_window = {
            f"{slug}_{window}": {"items": 50, "truncated": True}
            for _, slug in QUERIES
            for window in ("prior", "recent")
        }
        _build_and_save(
            videos,
            comments,
            {},
            {"items": []},
            {"items": []},
            {},
            0,
            counts,
            comment_counts,
            per_query_window,
            synthetic=True,
        )
        print(
            f"synthetic: {len(videos)} videos, {len(comments)} comments, "
            f"source={SOURCE}"
        )
        return

    print(f"live fetch complete: quota used ~{quota} units")
    # Persist the raw responses immediately, before any cleaning, so a
    # later failure cannot lose a paid-for fetch.
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for (slug, window), result in search_raw.items():
        (RAW_DIR / f"search_{slug}_{window}.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False)
        )
    (RAW_DIR / "videos_details.json").write_text(
        json.dumps(videos_raw, indent=2, ensure_ascii=False)
    )
    (RAW_DIR / "channels_details.json").write_text(
        json.dumps(channels_raw, indent=2, ensure_ascii=False)
    )
    videos, counts = clean_videos(search_raw, videos_raw, channels_raw)
    print(
        f"  candidates={counts['candidates']} "
        f"unique={counts['unique_after_dedupe']} "
        f"final={counts['final_videos']}"
    )
    picks = pick_sentiment_videos(videos)
    print(f"  sentiment videos: {len(picks)} picked")
    comment_raw: dict[str, dict] = {}
    comment_quota = 0
    zero_comment_videos = 0
    for i, pick in enumerate(picks):
        if i:
            time.sleep(SLEEP_BETWEEN_CALLS)
        try:
            result = fetch_sentiment_comments(pick["video_id"])
        except FetchError as exc:
            if "commentsDisabled" in str(exc):
                print(f"  {pick['video_id']}: comments disabled — 0 fetched")
                result = {"items": []}
            else:
                raise
        comment_raw[pick["video_id"]] = result
        comment_quota += 1
        n = len(result.get("items", []))
        if n == 0:
            zero_comment_videos += 1
        print(f"  comments {pick['video_id']} ({pick['topic']}): {n} threads")
    if zero_comment_videos >= 3:
        raise RuntimeError(
            f"{zero_comment_videos} of {len(picks)} sentiment videos returned "
            "0 comments — treating as a failed fetch (see research_brief §1.8)"
        )
    quota += comment_quota
    comments, comment_counts = clean_comments(comment_raw, picks)
    print(
        f"  comments fetched={comment_counts['fetched']} "
        f"analysed={comment_counts['analysed']}"
    )
    per_query_window = {
        f"{slug}_{window}": {
            "items": len(result.get("items", [])),
            "truncated": len(result.get("items", [])) == MAX_RESULTS,
        }
        for (slug, window), result in search_raw.items()
    }
    _build_and_save(
        videos,
        comments,
        search_raw,
        videos_raw,
        channels_raw,
        comment_raw,
        quota,
        counts,
        comment_counts,
        per_query_window,
    )


if __name__ == "__main__":
    main()
