"""Day 4 — YouTube Video Performance Analyzer: fetch -> clean -> KPIs
-> groupings -> recommendations -> save.

Source: YouTube Data API v3 via the custom.youtube connector helper
(~/workspace/custom-connectors/custom.youtube/bin/youtube.py).
Descriptive, historical performance analysis only. Patterns describe
this sampled set — never presented as causal findings or a guarantee
of future performance. Educational analysis only.

Fetch rules (see research_brief.md / plan.md):
- Exactly 5 fixed searches (one per query, maxResults=50,
  order=relevance — the helper default; never pass --order).
- >= 2 s between calls; one retry after 30 s on HTTP 5xx / timeout
  only; no retry on 403 quotaExceeded — stop and fall back.
- Batched videos calls (<= 50 IDs) then batched channels calls
  (<= 50 IDs) for subscriber counts.
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
  non-zero if no cache exists.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:  # run as a module: python -m src.data_pipeline
    from src.youtube_kpi import compute_kpis, parse_duration_iso8601
except ImportError:  # run as a script: python src/data_pipeline.py
    from youtube_kpi import (  # type: ignore[no-redef]
        compute_kpis,
        parse_duration_iso8601,
    )

HELPER = (
    Path.home()
    / "workspace"
    / "custom-connectors"
    / "custom.youtube"
    / "bin"
    / "youtube.py"
)
QUERIES = [
    "data analytics",
    "machine learning tutorial",
    "Python data analysis",
    "artificial intelligence explained",
    "SQL tutorial",
]
QUERY_SLUGS = [
    "data-analytics",
    "machine-learning-tutorial",
    "python-data-analysis",
    "artificial-intelligence-explained",
    "sql-tutorial",
]
MAX_RESULTS = 50
FETCH_DATE_STR = "2026-11-08"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Set by main(); "live" | "cache" | "synthetic".
DATA_SOURCE = "live"
# Quota units used by this run (best estimate): 100/search, 1/videos,
# 1/channels call. Updated by the fetch functions.
QUOTA_UNITS_USED = 0
# Row-count ledger, filled by clean_videos().
COUNTS: dict[str, int] = {}


def _run_helper(args: list[str]) -> dict:
    """One helper call with >= 2 s spacing and one 30 s retry on 5xx.

    Raises RuntimeError with the HTTP code in the message so the
    caller can follow the plan §3.2 error table (no retry on 403
    quotaExceeded; one retry on 5xx only). Never logs the API key —
    the helper never prints it.
    """
    time.sleep(2)
    for attempt in range(2):
        proc = subprocess.run(
            [sys.executable, str(HELPER), *args],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if proc.returncode == 0:
            return json.loads(proc.stdout)
        err = (proc.stderr or proc.stdout or "").strip()
        code = None
        if err.startswith("HTTP "):
            try:
                code = int(err.split()[1])
            except (IndexError, ValueError):
                code = None
        if code is not None and 500 <= code < 600 and attempt == 0:
            print(f"  helper {args[0]}: HTTP {code}; retrying after 30 s ...")
            time.sleep(30)
            continue
        raise RuntimeError(f"helper {' '.join(args[:2])}: {err[:500]}")
    raise RuntimeError(f"helper {' '.join(args[:2])}: failed after retry")


def fetch_search(query: str, max_results: int = MAX_RESULTS) -> dict:
    """One search call (100 quota units)."""
    global QUOTA_UNITS_USED
    QUOTA_UNITS_USED += 100
    return _run_helper(["search", "--query", query, "--max-results", str(max_results)])


def fetch_video_details(video_ids: list[str]) -> dict:
    """Batched videos calls, <= 50 IDs each (1 quota unit per call)."""
    global QUOTA_UNITS_USED
    items: list[dict] = []
    for i in range(0, len(video_ids), 50):
        QUOTA_UNITS_USED += 1
        payload = _run_helper(["videos", "--ids", ",".join(video_ids[i : i + 50])])
        items.extend(payload.get("items", []))
    return {"kind": "youtube#videoListResponse", "items": items}


def fetch_channel_details(channel_ids: list[str]) -> dict:
    """Batched channels calls, <= 50 IDs each (1 quota unit per call)."""
    global QUOTA_UNITS_USED
    items: list[dict] = []
    for i in range(0, len(channel_ids), 50):
        QUOTA_UNITS_USED += 1
        payload = _run_helper(["channels", "--ids", ",".join(channel_ids[i : i + 50])])
        items.extend(payload.get("items", []))
    return {"kind": "youtube#channelListResponse", "items": items}


def fetch_all() -> dict[str, dict]:
    """Run the full §3.2 fetch: 5 searches, dedupe, batched details.

    Returns {filename-stem: raw JSON} keyed by the plan §5 raw names
    (without the .json suffix).
    """
    raw: dict[str, dict] = {}
    seen: dict[str, dict] = {}
    for query, slug in zip(QUERIES, QUERY_SLUGS):
        payload = fetch_search(query)
        raw[f"search_{slug}"] = payload
        for item in payload.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if not video_id or video_id in seen:
                continue
            seen[video_id] = item
    COUNTS["candidates"] = sum(
        len(raw[f"search_{slug}"].get("items", [])) for slug in QUERY_SLUGS
    )
    COUNTS["unique_after_dedupe"] = len(seen)
    usable = [
        video_id
        for video_id, item in seen.items()
        if item.get("snippet", {}).get("liveBroadcastContent") == "none"
    ]
    COUNTS["dropped_live_or_upcoming"] = len(seen) - len(usable)
    raw["videos_details"] = fetch_video_details(usable)
    channel_ids: list[str] = []
    for item in seen.values():
        channel_id = item.get("snippet", {}).get("channelId")
        if channel_id and channel_id not in channel_ids:
            channel_ids.append(channel_id)
    raw["channels_details"] = fetch_channel_details(channel_ids)
    return raw


def _to_int(value: object) -> int | float:
    if value is None:
        return float("nan")
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return float("nan")


def clean_videos(raw: dict[str, dict]) -> pd.DataFrame:
    """Build the cleaned video frame from the raw search/videos/channels
    JSONs. Dedupes by videoId (first occurrence wins), drops live /
    upcoming streams and rows with no viewCount, and joins subscriber
    counts. Missing like/comment/subscriber counts stay NaN, never 0.
    """
    videos = {
        item["id"]: item
        for item in raw["videos_details"].get("items", [])
        if isinstance(item.get("id"), str)
    }
    channels = {
        item["id"]: item
        for item in raw["channels_details"].get("items", [])
        if isinstance(item.get("id"), str)
    }
    # Dedupe across the five search files (first occurrence wins).
    seen: dict[str, dict] = {}
    for slug in QUERY_SLUGS:
        for item in raw.get(f"search_{slug}", {}).get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if video_id and video_id not in seen:
                seen[video_id] = item
    COUNTS["candidates"] = sum(
        len(raw.get(f"search_{slug}", {}).get("items", [])) for slug in QUERY_SLUGS
    )
    COUNTS["unique_after_dedupe"] = len(seen)
    rows: list[dict] = []
    dropped_live = 0
    dropped_no_views = 0
    dropped_missing_details = 0
    for video_id, search_item in seen.items():
        snippet = search_item.get("snippet", {})
        if snippet.get("liveBroadcastContent") != "none":
            dropped_live += 1
            continue
        detail = videos.get(video_id)
        if detail is None:
            dropped_missing_details += 1
            continue
        stats = detail.get("statistics", {})
        if "viewCount" not in stats:
            dropped_no_views += 1
            continue
        detail_snippet = detail.get("snippet", {})
        content = detail.get("contentDetails", {})
        channel_id = detail_snippet.get("channelId", "")
        channel_stats = channels.get(channel_id, {}).get("statistics", {})
        rows.append(
            {
                "video_id": video_id,
                "title": detail_snippet.get("title", ""),
                "channel_id": channel_id,
                "channel_title": detail_snippet.get("channelTitle", ""),
                "published_at": detail_snippet.get("publishedAt", ""),
                "days_since_publish": None,
                "view_count": int(stats["viewCount"]),
                "like_count": _to_int(stats.get("likeCount")),
                "comment_count": _to_int(stats.get("commentCount")),
                "subscriber_count": _to_int(channel_stats.get("subscriberCount")),
                "duration_seconds": parse_duration_iso8601(content.get("duration", "")),
                "category_id": detail_snippet.get("categoryId", ""),
                "tags": detail.get("snippet", {}).get("tags") or [],
                "description": detail_snippet.get("description", ""),
            }
        )
    COUNTS["dropped_live_or_upcoming"] = dropped_live
    COUNTS["dropped_no_view_count"] = dropped_no_views
    COUNTS["dropped_missing_details"] = dropped_missing_details
    COUNTS["final_videos"] = len(rows)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = compute_kpis(df)
    columns = [
        "video_id",
        "title",
        "channel_id",
        "channel_title",
        "published_at",
        "days_since_publish",
        "view_count",
        "like_count",
        "comment_count",
        "subscriber_count",
        "duration_seconds",
        "duration_bucket",
        "topic",
        "format",
        "category_id",
        "publish_hour_utc",
        "publish_hour_pacific",
        "publish_dow",
        "channel_size",
        "views_per_day",
        "engagement_rate",
        "like_rate",
        "comment_rate",
        "views_per_subscriber",
        "high_performer",
    ]
    return df[columns]


def save_outputs(videos: pd.DataFrame, raw: dict[str, dict]) -> None:
    """Write raw JSONs to data/raw/, videos.csv + data_source.json to
    data/processed/.

    When DATA_SOURCE is "synthetic", raw JSONs go ONLY to
    data/raw/*_synthetic.json and the live cache is never written,
    touched, or deleted. Otherwise they go to their plan §5 names.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for stem, payload in raw.items():
        if DATA_SOURCE == "synthetic":
            dest = RAW_DIR / f"{stem}_synthetic.json"
        else:
            dest = RAW_DIR / f"{stem}.json"
        dest.write_text(json.dumps(payload))
    videos.to_csv(PROCESSED_DIR / "videos.csv", index=False)
    channel_count = int(videos["channel_id"].nunique()) if len(videos) else 0
    (PROCESSED_DIR / "data_source.json").write_text(
        json.dumps(
            {
                "source": DATA_SOURCE,
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "synthetic": DATA_SOURCE == "synthetic",
                "seed": 42 if DATA_SOURCE == "synthetic" else None,
                "queries": QUERIES,
                "max_results_per_query": MAX_RESULTS,
                "video_count": len(videos),
                "channel_count": channel_count,
                "quota_units_used": QUOTA_UNITS_USED,
                "api": "youtube-data-api-v3",
                "top_up": None,
                "fetch_date": FETCH_DATE_STR,
                "counts": COUNTS,
            },
            indent=2,
        )
    )


def _iso_duration(seconds: int) -> str:
    hours, rem = divmod(int(seconds), 3600)
    minutes, secs = divmod(rem, 60)
    parts = "PT"
    if hours:
        parts += f"{hours}H"
    if minutes:
        parts += f"{minutes}M"
    parts += f"{secs}S"
    return parts


def generate_synthetic(seed: int = 42) -> dict[str, dict]:
    """Deterministic synthetic fallback (brief §5.1 / plan §3.5).

    200 videos across 20 synthetic channels (10 each). Views
    log-normal (median 50,000, sigma_log 1.2, clipped to
    [100, 5,000,000]); likes 2–6% of views; comments 0.05–0.5% of
    views; subscribers log-normal (median 100,000, sigma_log 1.0,
    clipped to [1,000, 10,000,000]); durations log-normal (median
    600 s, sigma_log 0.8, clipped to [60, 3600]); published uniformly
    over the 365 days before 2026-11-08. Titles/tags are assembled
    from fixed template lists per topic group so the keyword grouping
    classifies them. Returns data in the same shape as the live API
    responses so clean_videos() works unchanged. Only called when
    the fetch fails AND no cache exists.
    """
    rng = np.random.default_rng(seed)
    templates = [
        (
            "python",
            "Python Data Analysis Tutorial for Beginners",
            ["python", "pandas", "data analysis"],
            "27",
        ),
        (
            "sql",
            "SQL Tutorial: Learn SQL for Data Analysis",
            ["sql", "mysql", "database"],
            "27",
        ),
        (
            "ai_ml",
            "Machine Learning Tutorial: Neural Networks Explained",
            ["machine learning", "deep learning", "neural"],
            "28",
        ),
        (
            "bi_viz",
            "Power BI Dashboard Tutorial for Data Analytics",
            ["power bi", "dashboard", "visualization"],
            "27",
        ),
        (
            "career",
            "Data Analyst Career Roadmap: Salary and Interview Guide",
            ["career", "data analyst", "interview"],
            "27",
        ),
        (
            "general",
            "What Is Data Analytics? A Complete Introduction",
            ["data analytics", "data science", "guide"],
            "27",
        ),
    ]
    raw: dict[str, dict] = {}
    video_items: list[dict] = []
    channel_items: list[dict] = []
    search_items: dict[str, list[dict]] = {slug: [] for slug in QUERY_SLUGS}
    start = pd.Timestamp("2025-11-08", tz="UTC")
    for ch in range(20):
        channel_id = f"UCsynthetic{ch:02d}0000000000000"
        subs = int(np.clip(rng.lognormal(np.log(100_000), 1.0), 1_000, 10_000_000))
        channel_items.append(
            {
                "id": channel_id,
                "snippet": {
                    "title": f"Synthetic Creator {ch + 1:02d}",
                    "publishedAt": "2020-01-01T00:00:00Z",
                },
                "statistics": {
                    "subscriberCount": str(subs),
                    "viewCount": str(subs * 10),
                    "videoCount": "10",
                },
            }
        )
        for v in range(10):
            idx = ch * 10 + v
            _topic, title_base, tags, category = templates[idx % len(templates)]
            video_id = f"SYNTH{idx:08d}"
            views = int(np.clip(rng.lognormal(np.log(50_000), 1.2), 100, 5_000_000))
            likes = round(views * rng.uniform(0.02, 0.06))
            comments = round(views * rng.uniform(0.0005, 0.005))
            duration = int(np.clip(rng.lognormal(np.log(600), 0.8), 60, 3600))
            published = start + pd.Timedelta(days=int(rng.integers(0, 365)))
            title = f"{title_base} — Part {v + 1}"
            search_item = {
                "id": {"videoId": video_id},
                "snippet": {
                    "publishedAt": published.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "channelId": channel_id,
                    "title": title,
                    "description": f"{title_base} for data analytics learners.",
                    "channelTitle": f"Synthetic Creator {ch + 1:02d}",
                    "liveBroadcastContent": "none",
                },
            }
            search_items[QUERY_SLUGS[idx % len(QUERY_SLUGS)]].append(search_item)
            video_items.append(
                {
                    "id": video_id,
                    "snippet": {
                        "title": title,
                        "channelId": channel_id,
                        "channelTitle": f"Synthetic Creator {ch + 1:02d}",
                        "publishedAt": published.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "description": (f"{title_base} for data analytics learners."),
                        "tags": tags,
                        "categoryId": category,
                        "liveBroadcastContent": "none",
                    },
                    "statistics": {
                        "viewCount": str(views),
                        "likeCount": str(likes),
                        "commentCount": str(comments),
                    },
                    "contentDetails": {
                        "duration": _iso_duration(duration),
                        "definition": "hd",
                        "dimension": "2d",
                        "licensedContent": False,
                    },
                }
            )
    for slug in QUERY_SLUGS:
        raw[f"search_{slug}"] = {
            "kind": "youtube#searchListResponse",
            "items": search_items[slug],
        }
    raw["videos_details"] = {
        "kind": "youtube#videoListResponse",
        "items": video_items,
    }
    raw["channels_details"] = {
        "kind": "youtube#channelListResponse",
        "items": channel_items,
    }
    COUNTS["candidates"] = 200
    COUNTS["unique_after_dedupe"] = 200
    COUNTS["dropped_live_or_upcoming"] = 0
    COUNTS["dropped_no_view_count"] = 0
    COUNTS["dropped_missing_details"] = 0
    COUNTS["final_videos"] = 200
    return raw


def _load_cache() -> dict[str, dict] | None:
    # Loads only the exact live-cache filenames; a *_synthetic.json
    # file alone never satisfies the cache (ignored by construction).
    cached: dict[str, dict] = {}
    stems = [f"search_{slug}" for slug in QUERY_SLUGS] + [
        "videos_details",
        "channels_details",
    ]
    for stem in stems:
        path = RAW_DIR / f"{stem}.json"
        if not path.exists():
            return None
        cached[stem] = json.loads(path.read_text())
    return cached


def main() -> None:
    """Orchestrate: fetch (or cache, or synthetic) -> clean -> KPIs
    -> save.

    --offline / --use-cache: skip the network entirely; use only the
    committed data/raw/*.json cache (never generate synthetic data).
    Exits non-zero if no cache exists.
    """
    global DATA_SOURCE, QUOTA_UNITS_USED
    parser = argparse.ArgumentParser(
        description="YouTube Video Performance Analyzer pipeline: "
        "fetch, clean, KPIs, groupings, recommendations."
    )
    parser.add_argument(
        "--offline",
        "--use-cache",
        dest="offline",
        action="store_true",
        help="Use cached data/raw/*.json only; make no network calls "
        "and never generate synthetic data",
    )
    args = parser.parse_args()
    raw: dict[str, dict] | None = None
    if args.offline:
        cached = _load_cache()
        if cached is None:
            print("Offline mode: no cached data/raw/*.json found; cannot fetch.")
            raise SystemExit(1)
        raw = cached
        DATA_SOURCE = "cache"
        QUOTA_UNITS_USED = 0
        print("Offline mode: using cached data/raw/ JSON (no network).")
    else:
        try:
            print("Fetching YouTube Data API v3 (5 searches + details) ...")
            raw = fetch_all()
            DATA_SOURCE = "live"
            print("Live YouTube fetch succeeded.")
        # Any fetch failure falls back to cache, then synthetic (§3.5).
        except Exception as exc:  # noqa: BLE001
            print(f"Live fetch failed: {exc}")
            cached = _load_cache()
            if cached is not None:
                raw = cached
                DATA_SOURCE = "cache"
                QUOTA_UNITS_USED = 0
                print("Using cached data/raw/ JSON.")
            else:
                raw = generate_synthetic(seed=42)
                DATA_SOURCE = "synthetic"
                print(
                    "SYNTHETIC DATA — API unavailable; using deterministic "
                    "fallback (seed=42). Do not present as real data."
                )

    videos = clean_videos(raw)
    save_outputs(videos, raw)

    print(f"\nData source: {DATA_SOURCE.upper()}")
    print(f"Quota units used: {QUOTA_UNITS_USED}")
    print(f"Counts: {COUNTS}")
    if len(videos):
        print(f"Final videos: {len(videos)}")
        print("Like-count presence: " f"{videos['like_count'].notna().mean():.1%}")
        print(
            "Subscriber-count presence: "
            f"{videos['subscriber_count'].notna().mean():.1%}"
        )
        print("Median views/day: " f"{videos['views_per_day'].median():,.0f}")
        print(
            "Median engagement rate: "
            f"{videos['engagement_rate'].median() * 100:.2f}%"
        )
        print("Other-topic share: " f"{(videos['topic'] == 'other').mean():.1%}")
        top_channel = videos["channel_id"].value_counts(normalize=True)
        print(
            "Largest channel share: "
            f"{top_channel.iloc[0]:.1%} ({top_channel.index[0]})"
        )
    if DATA_SOURCE == "synthetic":
        print(
            "Wrote data/raw/*_synthetic.json "
            "(synthetic — live cache untouched), "
            "data/processed/videos.csv"
        )
    else:
        print("Wrote data/raw/*.json, data/processed/videos.csv")


if __name__ == "__main__":
    main()
