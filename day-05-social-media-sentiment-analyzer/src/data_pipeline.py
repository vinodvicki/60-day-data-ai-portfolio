"""Day 5 — Social Media Sentiment Analyzer: fetch -> clean -> score -> save.

Source: YouTube Data API v3 via the custom.youtube connector helper
(~/workspace/custom-connectors/custom.youtube/bin/youtube.py).
Top-level comments only, newest first, on a fixed 12-video corpus taken
from Day 4's processed frame. Sentiment is a model output from our own
rule-based lexicon (src/sentiment.py) — never presented as ground truth.
Educational analysis only.

Fetch rules (see research_brief.md / plan.md):
- Exactly 12 comment-threads sequences (one per video, maxResults=100,
  order=time, textFormat=plainText, part=snippet). No replies fetched.
- Up to 3 pages (300 threads) per video; stop early when a page's oldest
  comment predates the window start (2025-11-09). The window is applied
  AFTER fetching (the API has no date filter).
- >= 2 s between calls; one retry after 30 s on HTTP 5xx / timeout
  only; no retry on 403 quotaExceeded — stop and fall back.
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
import random
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

try:  # run as a module: python -m src.data_pipeline
    from src.sentiment import (
        classify_themes,
        evaluate_predictions,
        is_non_latin,
        score_comment,
    )
except ImportError:  # run as a script: python src/data_pipeline.py
    from sentiment import (  # type: ignore[no-redef]
        classify_themes,
        evaluate_predictions,
        is_non_latin,
        score_comment,
    )

HELPER = (
    Path.home()
    / "workspace"
    / "custom-connectors"
    / "custom.youtube"
    / "bin"
    / "youtube.py"
)

#: Fixed 12-video corpus (research_brief §2.1 — do not change).
VIDEOS = [
    {
        "video_id": "fa8k8IQ1_X0",
        "title": "A.I. ‐ Humanity's Final Invention?",
        "channel_title": "Kurzgesagt – In a Nutshell",
        "topic": "ai_ml",
    },
    {
        "video_id": "5KmopXwjXik",
        "title": 'Godfather of AI WARNS: "You Have No Idea What\'s Coming"',
        "channel_title": "The Diary Of A CEO Clips",
        "topic": "ai_ml",
    },
    {
        "video_id": "HXV3zeQKqGY",
        "title": "SQL Tutorial - Full Database Course for Beginners",
        "channel_title": "freeCodeCamp.org",
        "topic": "sql",
    },
    {
        "video_id": "7S_tz1z_5bA",
        "title": "SQL Course for Beginners [Full Course]",
        "channel_title": "Programming with Mosh",
        "topic": "sql",
    },
    {
        "video_id": "aircAruvnKk",
        "title": "But what is a neural network? | Deep learning chapter 1",
        "channel_title": "3Blue1Brown",
        "topic": "python",
    },
    {
        "video_id": "SSKVgrwhzus",
        "title": "SQL Full Course for Beginners (30 Hours) – From Zero to Hero",
        "channel_title": "Data with Baraa",
        "topic": "python",
    },
    {
        "video_id": "t2oOFs4WgI0",
        "title": "Beyond the Numbers: A Data Analyst Journey | Anna Leach | TEDxPSU",
        "channel_title": "TEDx Talks",
        "topic": "career",
    },
    {
        "video_id": "yZvFH7B6gKI",
        "title": "What Is Data Analytics? - An Introduction (Full Guide)",
        "channel_title": "CareerFoundry",
        "topic": "career",
    },
    {
        "video_id": "qrbf9DtR3_c",
        "title": "Excel Data Analysis Full Course Tutorial (7+ Hours)",
        "channel_title": "Learn Skills Daily",
        "topic": "bi_viz",
    },
    {
        "video_id": "aZ5EsdnpLMI",
        "title": "Artificial Intelligence | 60 Minutes Full Episodes",
        "channel_title": "60 Minutes",
        "topic": "ai_ml",
    },
    {
        "video_id": "pCJ15nGFgVg",
        "title": "Excel for Data Analytics - Full Course for Beginners",
        "channel_title": "Luke Barousse",
        "topic": "python",
    },
    {
        "video_id": "9f-GarcDY58",
        "title": "Machine Learning Full Course | Learn Machine Learning",
        "channel_title": "Simplilearn",
        "topic": "python",
    },
]
VIDEO_BY_ID = {v["video_id"]: v for v in VIDEOS}

MAX_PAGES_PER_VIDEO = 3
MAX_RESULTS = 100
FETCH_DATE_STR = "2026-11-09"
WINDOW_START = datetime(2025, 11, 9, 0, 0, 0, tzinfo=UTC)
WINDOW_END = datetime(2026, 11, 9, 23, 59, 59, tzinfo=UTC)
SLEEP_BETWEEN_CALLS = 2.0
RETRY_AFTER_SECONDS = 30.0

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

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


def fetch_comment_threads(video_id: str) -> dict:
    """Fetch up to 3 pages of top-level comment threads for one video.

    Returns {"items": [...], "pages": n, "calls": n}. Stops early when a
    page has no nextPageToken, returns no items, or its oldest comment
    predates the window start. One quota unit per call.
    """
    items: list[dict] = []
    page_token: str | None = None
    calls = 0
    pages = 0
    for _ in range(MAX_PAGES_PER_VIDEO):
        if calls:
            time.sleep(SLEEP_BETWEEN_CALLS)
        args = [
            "comment-threads",
            "--video-id",
            video_id,
            "--max-results",
            str(MAX_RESULTS),
            "--order",
            "time",
            "--text-format",
            "plainText",
        ]
        if page_token:
            args += ["--page-token", page_token]
        result = _run_helper(args)
        calls += 1
        pages += 1
        page_items = result.get("items", [])
        if not page_items:
            break
        items.extend(page_items)
        page_token = result.get("nextPageToken")
        if not page_token:
            break
        oldest = min(
            item["snippet"]["topLevelComment"]["snippet"]["publishedAt"]
            for item in page_items
        )
        if datetime.fromisoformat(oldest) < WINDOW_START:
            break
    return {"items": items, "pages": pages, "calls": calls}


def fetch_all() -> tuple[dict[str, dict], int]:
    """Fetch comment threads for all 12 videos. Returns (raw, quota)."""
    raw: dict[str, dict] = {}
    quota = 0
    zero_videos = 0
    for video in VIDEOS:
        video_id = video["video_id"]
        try:
            result = fetch_comment_threads(video_id)
        except FetchError as exc:
            message = str(exc)
            if "commentsDisabled" in message:
                print(f"  {video_id}: comments disabled — 0 fetched")
                result = {"items": [], "pages": 0, "calls": 1}
            else:
                raise
        raw[video_id] = result
        quota += result["calls"]
        n = len(result["items"])
        if n == 0:
            zero_videos += 1
        print(f"  {video_id}: {n} threads in {result['pages']} page(s)")
    if zero_videos >= 4:
        raise RuntimeError(
            f"{zero_videos} of 12 videos returned 0 comments — "
            "treating as a failed fetch (see research_brief §1.7)"
        )
    return raw, quota


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def clean_comments(
    raw: dict[str, dict],
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Build the analysed comment frame from raw thread responses.

    Filter order (each step counted): dedupe -> owner -> empty text ->
    outside window -> non-Latin. Returns (frame, filter_counts).
    """
    counts = {
        "fetched": 0,
        "duplicates": 0,
        "owner": 0,
        "empty": 0,
        "outside_window": 0,
        "non_latin": 0,
        "analysed": 0,
    }
    seen: set[str] = set()
    rows: list[dict] = []
    for video in VIDEOS:
        video_id = video["video_id"]
        meta = raw.get(video_id, {"items": []})
        for item in meta.get("items", []):
            counts["fetched"] += 1
            thread = item.get("snippet", {})
            top = thread.get("topLevelComment", {}).get("snippet", {})
            comment_id = top.get("id") or item.get("id", "")
            if not comment_id or comment_id in seen:
                counts["duplicates"] += 1
                continue
            seen.add(comment_id)
            # (1) Channel-owner comments are not audience sentiment.
            author_channel = (top.get("authorChannelId") or {}).get("value", "")
            if author_channel and author_channel == thread.get("channelId", ""):
                counts["owner"] += 1
                continue
            text = top.get("textDisplay") or top.get("textOriginal") or ""
            # (2) Empty text carries no signal.
            if not text.strip():
                counts["empty"] += 1
                continue
            published_at = top.get("publishedAt", "")
            try:
                published = _parse_ts(published_at)
            except ValueError:
                counts["outside_window"] += 1
                continue
            # (3) Window filter (post-fetch — the API has no date filter).
            if not (WINDOW_START <= published <= WINDOW_END):
                counts["outside_window"] += 1
                continue
            # (4) Non-Latin heuristic (stdlib unicodedata only).
            if is_non_latin(text):
                counts["non_latin"] += 1
                continue
            score, sentiment, scored_words = score_comment(text)
            rows.append(
                {
                    "comment_id": comment_id,
                    "video_id": video_id,
                    "video_title": video["title"],
                    "channel_title": video["channel_title"],
                    "topic": video["topic"],
                    "author_display_name": top.get("authorDisplayName", ""),
                    "text": text,
                    "published_at": published_at,
                    "month": published.strftime("%Y-%m"),
                    "like_count": int(top.get("likeCount") or 0),
                    "total_reply_count": int(thread.get("totalReplyCount") or 0),
                    "sentiment_score": score,
                    "sentiment": sentiment,
                    "scored_words": scored_words,
                    "themes": ";".join(classify_themes(text)),
                    "language_flag": "latin",
                }
            )
    counts["analysed"] = len(rows)
    frame = pd.DataFrame(rows)
    if not frame.empty:
        # Never trust response order (pinned comments surface first).
        frame = frame.sort_values("published_at").reset_index(drop=True)
    return frame, counts


def draw_validation_sample(
    frame: pd.DataFrame, n_per_class: int = 40, seed: int = 42
) -> pd.DataFrame:
    """Stratified sample: n_per_class per predicted class, seed 42."""
    rng = random.Random(seed)
    parts = []
    for label in ("positive", "neutral", "negative"):
        subset = frame[frame["sentiment"] == label]
        take = min(n_per_class, len(subset))
        if take:
            parts.append(subset.sample(n=take, random_state=rng.randint(0, 2**31)))
    sample = pd.concat(parts, ignore_index=True) if parts else frame.iloc[0:0]
    return sample[["comment_id", "text", "sentiment"]].rename(
        columns={"sentiment": "predicted"}
    )


def evaluate_validation(frame: pd.DataFrame) -> dict | None:
    """Evaluate predicted vs human labels, if labels exist. Else None."""
    labels_path = PROCESSED_DIR / "validation_labels.csv"
    if not labels_path.exists() or frame.empty:
        return None
    labels = pd.read_csv(labels_path, dtype=str).fillna("")
    merged = frame.merge(labels, on="comment_id", how="inner", suffixes=("", "_human"))
    if merged.empty:
        return None
    return evaluate_predictions(
        merged["sentiment"].tolist(), merged["human_label"].tolist()
    )


def save_outputs(
    frame: pd.DataFrame,
    raw: dict[str, dict],
    quota_units: int,
    counts: dict[str, int],
    synthetic: bool = False,
) -> None:
    """Write raw JSONs, comments.csv, validation sample, data_source.json."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    if synthetic:
        payload = {"synthetic": True, "seed": 42, "videos": raw}
        (RAW_DIR / "comments_synthetic.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False)
        )
    else:
        for video_id, result in raw.items():
            (RAW_DIR / f"comments_{video_id}.json").write_text(
                json.dumps(result, indent=2, ensure_ascii=False)
            )
    frame.to_csv(PROCESSED_DIR / "comments.csv", index=False)
    draw_validation_sample(frame).to_csv(
        PROCESSED_DIR / "validation_sample.csv", index=False
    )
    source = {
        "source": SOURCE,
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "synthetic": synthetic,
        "seed": 42 if synthetic else None,
        "video_ids": [v["video_id"] for v in VIDEOS],
        "window_start": WINDOW_START.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_end": WINDOW_END.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "max_pages_per_video": MAX_PAGES_PER_VIDEO,
        "comment_count_fetched": counts["fetched"],
        "comment_count_analysed": counts["analysed"],
        "quota_units_used": quota_units,
        "api": "youtube-data-api-v3",
        "filters": counts,
    }
    (PROCESSED_DIR / "data_source.json").write_text(json.dumps(source, indent=2))


# ---------------------------------------------------------------------------
# Synthetic fallback (seed 42 — labelled SYNTHETIC everywhere downstream)
# ---------------------------------------------------------------------------

TOPIC_WORDS = {
    "ai_ml": "AI",
    "sql": "SQL",
    "python": "Python",
    "career": "data analyst career",
    "bi_viz": "Excel",
}

SYNTHETIC_TEMPLATES = {
    "positive": [
        "This {topic} tutorial is amazing, thank you so much!",
        "Great explanation, finally I understand it",
        "Best video on this topic, really helpful",
        "Thank you, this {topic} course is excellent and clear",
        "Wonderful tutorial, I learned so much today",
        "Perfect explanation, love this channel",
        "Amazing work, this helped me a lot with {topic}",
        "Fantastic video, so clear and easy to follow",
        "Brilliant teacher, best {topic} tutorial on YouTube",
        "Great job, this {topic} lesson is super useful",
        "Thank you so much, I finally get it now",
        "Excellent content, really well explained",
    ],
    "neutral": [
        "What software is used in this video?",
        "Can anyone explain the part at 5 minutes?",
        "Watching this in 2026",
        "Is this {topic} tutorial good for beginners?",
        "How long did it take to make this video?",
        "What is the next video about?",
        "Does anyone have the notes for this lesson?",
        "I am watching this for my {topic} class",
        "What version is used here?",
        "Can someone share the link mentioned?",
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
        "This is wrong and misleading, awful tutorial",
        "Too slow and boring, I hate this lesson",
        "Useless video, nothing is explained properly",
        "Terrible pacing, confusing and frustrating",
        "Worst {topic} tutorial I have seen",
        "This made {topic} even more confusing for me",
    ],
}


def generate_synthetic(seed: int = 42) -> tuple[dict[str, dict], pd.DataFrame]:
    """Deterministic synthetic comments (150/video, mix 45/35/20 by design).

    Returns (raw, frame) in the same shapes as the live path, so the
    pipeline, notebook and dashboard run unchanged. Sentiment mix is
    uniform by construction — findings on synthetic data have no
    interpretation (stated in README/notebook/insights if used).
    """
    rng = random.Random(seed)
    raw: dict[str, dict] = {}
    start_ts = WINDOW_START.timestamp()
    end_ts = WINDOW_END.timestamp()
    for video in VIDEOS:
        video_id = video["video_id"]
        topic_word = TOPIC_WORDS[video["topic"]]
        items: list[dict] = []
        plan = [("positive", 67), ("neutral", 53), ("negative", 30)]
        index = 0
        for sentiment, count in plan:
            templates = SYNTHETIC_TEMPLATES[sentiment]
            for _ in range(count):
                index += 1
                text = rng.choice(templates).format(topic=topic_word)
                published = datetime.fromtimestamp(
                    rng.uniform(start_ts, end_ts), tz=UTC
                )
                like_max = 50 if sentiment == "neutral" else 200
                comment_id = f"synthetic-{video_id}-{index:03d}"
                items.append(
                    {
                        "kind": "youtube#commentThread",
                        "id": comment_id,
                        "snippet": {
                            "channelId": "UCsynthetic",
                            "videoId": video_id,
                            "topLevelComment": {
                                "kind": "youtube#comment",
                                "id": comment_id,
                                "snippet": {
                                    "channelId": "UCsynthetic",
                                    "videoId": video_id,
                                    "textDisplay": text,
                                    "textOriginal": text,
                                    "authorDisplayName": f"Synthetic Commenter {index:03d}",
                                    "authorChannelId": {"value": "UCsynthetic-author"},
                                    "likeCount": rng.randint(0, like_max),
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
        raw[video_id] = {"items": items, "pages": 2, "calls": 0}
    frame, _counts = clean_comments(raw)
    return raw, frame


def _load_cache() -> dict[str, dict] | None:
    """Load the committed per-video raw JSONs. None if any is missing.

    A synthetic file never satisfies this check — the cache is live data
    only (research_brief §5.2).
    """
    raw: dict[str, dict] = {}
    for video in VIDEOS:
        path = RAW_DIR / f"comments_{video['video_id']}.json"
        if not path.exists():
            return None
        raw[video["video_id"]] = json.loads(path.read_text())
    return raw


def main() -> None:
    global SOURCE
    parser = argparse.ArgumentParser(description="Day 5 data pipeline")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="run from the committed cache, no network",
    )
    parser.add_argument("--use-cache", action="store_true", help="alias for --offline")
    args = parser.parse_args()

    if args.offline or args.use_cache:
        SOURCE = "cache"
        raw = _load_cache()
        if raw is None:
            raise SystemExit(
                "ERROR: --offline but no complete cache in data/raw/ "
                "(need all 12 comments_<video_id>.json files)"
            )
        print("offline mode: using committed cache, no network")
        quota = 0
    else:
        SOURCE = "live"
        print("live mode: fetching comment threads for 12 videos")
        try:
            raw, quota = fetch_all()
        except (FetchError, RuntimeError) as exc:
            print(f"live fetch failed: {exc}")
            raw = _load_cache()
            if raw is not None:
                SOURCE = "cache"
                print("falling back to committed cache")
                quota = 0
            else:
                SOURCE = "synthetic"
                print("no cache — generating labelled synthetic data (seed 42)")
                raw, frame = generate_synthetic(seed=42)
                counts = {
                    "fetched": 1800,
                    "duplicates": 0,
                    "owner": 0,
                    "empty": 0,
                    "outside_window": 0,
                    "non_latin": 0,
                    "analysed": len(frame),
                }
                save_outputs(frame, raw, 0, counts, synthetic=True)
                print(f"synthetic: {len(frame)} comments, source={SOURCE}")
                return
        print(f"live fetch complete: quota used ~{quota} units")

    frame, counts = clean_comments(raw)
    print(
        f"fetched={counts['fetched']} analysed={counts['analysed']} "
        f"filters={counts}"
    )
    if counts["analysed"] < 800:
        print(
            "WARNING: analysed comments below the 800 target — "
            "thin-sample caveat applies (plan §4.6)"
        )
    save_outputs(frame, raw, quota, counts, synthetic=False)
    print(
        f"wrote data/processed/comments.csv ({len(frame)} rows), "
        f"validation_sample.csv, data_source.json (source={SOURCE})"
    )
    evaluation = evaluate_validation(frame)
    if evaluation is not None:
        print(
            f"validation (n={evaluation['n']}): "
            f"accuracy={evaluation['accuracy']} "
            f"macro_f1={evaluation['macro_f1']}"
        )
        for label, metrics in evaluation["per_class"].items():
            print(
                f"  {label}: P={metrics['precision']} "
                f"R={metrics['recall']} F1={metrics['f1']} "
                f"(support {metrics['support']})"
            )
    else:
        print(
            "validation: no validation_labels.csv yet — "
            "label the 120-comment sample to evaluate"
        )


if __name__ == "__main__":
    main()
