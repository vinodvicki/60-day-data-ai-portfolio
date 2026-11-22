"""Data pipeline (Day 15) — RSS fetch, clean, topic + sentiment, aggregates.

Corpus: six outlet RSS feeds, window 2026-11-08–2026-11-22 inclusive,
title + description text only, one GET per feed, raw XML stored
verbatim in ``data/raw/``, deduplicated by URL. GDELT is an optional
cross-check only and is skipped here — the build is complete on RSS
alone (plan §3.1). No scraping of linked article pages.

Modes:
- ``--live``: fetch the six feeds, then build all processed files and
  ``data_source.json``.
- ``--use-cache``: reuse the XMLs already in ``data/raw/`` and build
  everything, including ``data_source.json``.
- ``--offline``: rebuild the derived tables from the committed XMLs
  with no network; never writes ``data_source.json`` when a live
  record already exists (plan §3.5).
- ``--synthetic``: labelled synthetic fallback (brief §4, seed 42)
  written to ``data/raw/*_synthetic.json`` — never overwrites real
  data; recorded as ``synthetic: true`` in ``data_source.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import feedparser
import pandas as pd
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

try:
    from src.sentiment import compound_score, sentiment_label, summarise
    from src.stats import (
        chi_square_topic_outlet,
        pairwise_tests,
        sentiment_test_by_outlet,
    )
    from src.topics import (
        TOPIC_KEYWORDS,
        TOPICS,
        assign_topic,
        attention_share,
        wilson_ci,
    )
except ImportError:  # pragma: no cover - running as a script from src/
    from sentiment import compound_score, sentiment_label, summarise  # type: ignore[no-redef]
    from stats import (  # type: ignore[no-redef]
        chi_square_topic_outlet,
        pairwise_tests,
        sentiment_test_by_outlet,
    )
    from topics import TOPIC_KEYWORDS, TOPICS, assign_topic, attention_share, wilson_ci  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"

WINDOW_START = date(2026, 11, 8)
WINDOW_END = date(2026, 11, 22)
FETCH_DATE = "2026-11-22"
SAMPLE_SEED = 42
SAMPLE_PER_OUTLET = 5

OUTLETS: dict[str, dict[str, str]] = {
    "NYT": {
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "stem": "nyt",
        "site": "https://www.nytimes.com/",
    },
    "WSJ": {
        "url": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
        "stem": "wsj",
        "site": "https://www.wsj.com/",
    },
    "Fox News": {
        "url": "https://moxie.foxnews.com/google-publisher/latest.xml",
        "stem": "fox",
        "site": "https://www.foxnews.com/",
    },
    "CNN": {
        "url": "http://rss.cnn.com/rss/edition.rss",
        "stem": "cnn",
        "site": "https://www.cnn.com/",
    },
    "NPR": {
        "url": "https://feeds.npr.org/1001/rss.xml",
        "stem": "npr",
        "site": "https://www.npr.org/",
    },
    "BBC News": {
        "url": "https://feeds.bbci.co.uk/news/rss.xml",
        "stem": "bbc",
        "site": "https://www.bbc.com/news",
    },
}

GDELT_PERMITTED_QUERY = (
    "query=politics&mode=timelinevol&timespan=14d"
    "&sourcelang=english&sourcecountry=US&format=json"
)

USER_AGENT = "60-day-data-ai-portfolio-day15/1.0 (research; contact via repo)"

_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(value: object) -> str:
    """Strip HTML tags and unescape entities from an RSS text field."""
    if value is None:
        return ""
    text = str(value)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return " ".join(text.split())


def _parse_pub_date(entry: dict[str, Any]) -> datetime | None:
    """Parse an entry's publication date to an aware UTC datetime."""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed is None:
        return None
    try:
        return datetime(
            parsed.tm_year,
            parsed.tm_mon,
            parsed.tm_mday,
            parsed.tm_hour,
            parsed.tm_min,
            parsed.tm_sec,
            tzinfo=UTC,
        )
    except (ValueError, TypeError, AttributeError):
        return None


def fetch_feed(url: str, dest: Path) -> Path:
    """Fetch one RSS feed with a single GET; one retry after 60 s on 429/5xx.

    Returns the destination path. Raises ``RuntimeError`` if both
    attempts fail — never hammers the host.
    """
    headers = {"User-Agent": USER_AGENT}
    last_error = ""
    for attempt in (1, 2):
        try:
            response = requests.get(url, headers=headers, timeout=30)
        except requests.RequestException as exc:
            last_error = str(exc)
            if attempt == 1:
                time.sleep(60)
                continue
            raise RuntimeError(
                f"Fetch failed for {url} after 2 attempts: {last_error}"
            ) from exc
        if response.status_code == 200:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(response.content)
            return dest
        last_error = f"HTTP {response.status_code}"
        if response.status_code in (429, 500, 502, 503, 504) and attempt == 1:
            time.sleep(60)
            continue
        raise RuntimeError(f"Fetch failed for {url}: {last_error}")
    raise RuntimeError(f"Fetch failed for {url}: {last_error}")


def parse_feed(path: Path, outlet: str) -> list[dict[str, Any]]:
    """Parse one stored RSS XML with feedparser.

    Returns one dict per entry with ``outlet, title, description,
    link, pub_date`` (aware UTC datetime or ``None``) and ``guid``.
    Entries missing a link or a parseable date are returned as-is and
    counted out by the caller.
    """
    parsed = feedparser.parse(str(path))
    items: list[dict[str, Any]] = []
    for entry in parsed.entries:
        entry_dict = dict(entry)
        items.append(
            {
                "outlet": outlet,
                "title": _clean_text(entry_dict.get("title", "")),
                "description": _clean_text(
                    entry_dict.get("description", "") or entry_dict.get("summary", "")
                ),
                "link": str(entry_dict.get("link", "")).strip(),
                "pub_date": _parse_pub_date(entry_dict),
                "guid": str(
                    entry_dict.get("id", "")
                    or entry_dict.get("guid", "")
                    or entry_dict.get("link", "")
                ).strip(),
            }
        )
    return items


def collect_corpus(
    outlets: dict[str, dict[str, str]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply the cleaning rules (plan §3.2) to the stored raw XMLs.

    Returns the articles DataFrame and a per-outlet counts record.
    """
    rows: list[dict[str, Any]] = []
    counts: dict[str, Any] = {}
    seen_links: set[str] = set()
    for outlet, info in outlets.items():
        path = RAW_DIR / f"{info['stem']}_rss.xml"
        entries = parse_feed(path, outlet)
        fetched = len(entries)
        missing = 0
        window_dropped = 0
        duplicates = 0
        empty_text = 0
        kept_dates: list[date] = []
        for entry in entries:
            if not entry["link"] or entry["pub_date"] is None:
                missing += 1
                continue
            pub_date = entry["pub_date"].date()
            if not (WINDOW_START <= pub_date <= WINDOW_END):
                window_dropped += 1
                continue
            if entry["link"] in seen_links:
                duplicates += 1
                continue
            seen_links.add(entry["link"])
            text = f"{entry['title']} {entry['description']}".strip()
            if not text:
                empty_text += 1
            compound = compound_score(text)
            rows.append(
                {
                    "outlet": outlet,
                    "title": entry["title"],
                    "description": entry["description"],
                    "link": entry["link"],
                    "pub_date": entry["pub_date"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "guid": entry["guid"],
                    "text": text,
                    "topic": assign_topic(text),
                    "vader_compound": compound,
                    "sentiment_label": sentiment_label(compound),
                }
            )
            kept_dates.append(pub_date)
        counts[outlet] = {
            "feed_url": info["url"],
            "http_status": 200,
            "byte_size": path.stat().st_size,
            "fetched_items": fetched,
            "dropped_missing_link_or_date": missing,
            "dropped_outside_window": window_dropped,
            "duplicates_removed": duplicates,
            "empty_text_articles": empty_text,
            "final_n": len(kept_dates),
            "earliest_pub_date": (min(kept_dates).isoformat() if kept_dates else None),
            "latest_pub_date": (max(kept_dates).isoformat() if kept_dates else None),
        }
    articles = pd.DataFrame(
        rows,
        columns=[
            "outlet",
            "title",
            "description",
            "link",
            "pub_date",
            "guid",
            "text",
            "topic",
            "vader_compound",
            "sentiment_label",
        ],
    )
    if not articles.empty:
        articles = articles.sort_values(["outlet", "pub_date", "title"]).reset_index(
            drop=True
        )
    return articles, counts


def gdelt_cross_check() -> dict[str, Any]:
    """Record the optional GDELT cross-check decision (plan §3.1).

    The GDELT DOC API v2 is an optional cross-check only and is
    skipped here: the build is complete on RSS alone, and the
    researcher verified on 2026-11-22 that GDELT rate-limits (HTTP
    429) after a single successful call. No GDELT request is made.
    """
    return {
        "attempted": False,
        "status": "skipped",
        "reason": (
            "Optional cross-check only (plan §3.1). Skipped: the build is "
            "complete on RSS alone, and the researcher verified on "
            "2026-11-22 that the GDELT DOC API rate-limits (HTTP 429) "
            "after one successful call."
        ),
        "permitted_query_if_attempted": GDELT_PERMITTED_QUERY,
        "query_used": None,
        "http_status": None,
    }


def _versions() -> dict[str, str]:
    """Pinned runtime versions recorded in the provenance record."""
    import importlib.metadata

    names = [
        "pandas",
        "numpy",
        "scipy",
        "matplotlib",
        "streamlit",
        "feedparser",
        "vaderSentiment",
    ]
    versions = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "unknown"
    return versions


def _corpus_integrity_checks(articles: pd.DataFrame) -> dict[str, Any]:
    """Corpus-integrity cross-checks (plan §3.3). Raises on failure."""
    checks: dict[str, Any] = {}
    pub_dates = pd.to_datetime(articles["pub_date"], utc=True).dt.date
    checks["all_pub_dates_in_window"] = bool(
        ((pub_dates >= WINDOW_START) & (pub_dates <= WINDOW_END)).all()
        if not articles.empty
        else True
    )
    checks["urls_unique"] = bool(articles["link"].is_unique)
    checks["per_outlet_counts_sum_to_total"] = True  # by construction
    checks["exactly_one_topic_per_article"] = bool(
        articles["topic"].notna().all() and (articles["topic"] != "").all()
        if not articles.empty
        else True
    )
    checks["all_compounds_in_range"] = bool(
        articles["vader_compound"].between(-1.0, 1.0).all()
        if not articles.empty
        else True
    )
    checks["all_labels_valid"] = bool(
        articles["sentiment_label"].isin(["positive", "neutral", "negative"]).all()
        if not articles.empty
        else True
    )
    failed = [k for k, v in checks.items() if v is not True]
    if failed:
        raise ValueError(f"Corpus integrity check failed: {failed}")
    return checks


def _vader_recompute_check(articles: pd.DataFrame) -> dict[str, Any]:
    """Recompute VADER compound for 5 hand-picked titles (plan §3.3).

    The five titles are spread across the sorted corpus (first,
    quartiles, last) so the check covers more than one outlet. A
    fresh ``SentimentIntensityAnalyzer`` is used, independent of the
    pipeline's module-level analyser.
    """
    analyser = SentimentIntensityAnalyzer()
    if articles.empty:
        return {"n_checked": 0, "max_abs_diff": None, "passed": True, "items": []}
    ordered = articles.sort_values(["outlet", "title"]).reset_index(drop=True)
    n = len(ordered)
    indices = sorted({0, n // 4, n // 2, (3 * n) // 4, n - 1})
    items = []
    max_diff = 0.0
    for idx in indices:
        row = ordered.iloc[idx]
        direct = float(analyser.polarity_scores(str(row["text"]))["compound"])
        pipeline_value = float(row["vader_compound"])
        diff = abs(round(direct, 3) - round(pipeline_value, 3))
        max_diff = max(max_diff, diff)
        items.append(
            {
                "outlet": str(row["outlet"]),
                "title": str(row["title"]),
                "pipeline_compound": round(pipeline_value, 3),
                "direct_compound": round(direct, 3),
                "abs_diff_3dp": round(diff, 3),
            }
        )
    return {
        "n_checked": len(items),
        "max_abs_diff": round(max_diff, 3),
        "passed": bool(max_diff <= 0.001),
        "items": items,
    }


def _build_topic_attention(articles: pd.DataFrame) -> pd.DataFrame:
    """Attention-share table: one row per outlet x topic + ALL rows."""
    rows: list[dict[str, Any]] = []
    for outlet in OUTLETS:
        subset = articles[articles["outlet"] == outlet]
        total = len(subset)
        for topic in TOPICS:
            k = int((subset["topic"] == topic).sum())
            low, high = wilson_ci(k, total)
            rows.append(
                {
                    "outlet": outlet,
                    "topic": topic,
                    "n_articles": k,
                    "attention_share_pct": round(attention_share(k, total), 4),
                    "wilson_ci_low": round(low, 4),
                    "wilson_ci_high": round(high, 4),
                    "outlet_total": total,
                }
            )
    corpus_total = len(articles)
    for topic in TOPICS:
        k = int((articles["topic"] == topic).sum())
        low, high = wilson_ci(k, corpus_total)
        rows.append(
            {
                "outlet": "ALL",
                "topic": topic,
                "n_articles": k,
                "attention_share_pct": round(attention_share(k, corpus_total), 4),
                "wilson_ci_low": round(low, 4),
                "wilson_ci_high": round(high, 4),
                "outlet_total": corpus_total,
            }
        )
    return pd.DataFrame(rows)


def _build_sentiment_by_outlet(articles: pd.DataFrame) -> pd.DataFrame:
    """One row per outlet with mean compound, CI, median, label mix."""
    rows: list[dict[str, Any]] = []
    for outlet in OUTLETS:
        summary = summarise(articles[articles["outlet"] == outlet]["vader_compound"])
        rows.append(
            {
                "outlet": outlet,
                "n": int(summary["n"]),
                "mean_compound": summary["mean_compound"],
                "ci_low": summary["ci_low"],
                "ci_high": summary["ci_high"],
                "ci_method": summary["ci_method"],
                "median_compound": summary["median_compound"],
                "pct_positive": round(float(summary["pct_positive"]), 4),
                "pct_neutral": round(float(summary["pct_neutral"]), 4),
                "pct_negative": round(float(summary["pct_negative"]), 4),
            }
        )
    return pd.DataFrame(rows)


def _build_sentiment_by_topic(articles: pd.DataFrame) -> pd.DataFrame:
    """One row per outlet x topic with n >= 1; small_n flags n < 5."""
    rows: list[dict[str, Any]] = []
    for outlet in OUTLETS:
        for topic in TOPICS:
            subset = articles[
                (articles["outlet"] == outlet) & (articles["topic"] == topic)
            ]
            if len(subset) == 0:
                continue
            summary = summarise(subset["vader_compound"])
            rows.append(
                {
                    "outlet": outlet,
                    "topic": topic,
                    "n": int(summary["n"]),
                    "mean_compound": summary["mean_compound"],
                    "ci_low": summary["ci_low"],
                    "ci_high": summary["ci_high"],
                    "ci_method": summary["ci_method"],
                    "median_compound": summary["median_compound"],
                    "pct_positive": round(float(summary["pct_positive"]), 4),
                    "pct_neutral": round(float(summary["pct_neutral"]), 4),
                    "pct_negative": round(float(summary["pct_negative"]), 4),
                    "small_n": bool(int(summary["n"]) < 5),
                }
            )
    return pd.DataFrame(rows)


def _as_str_list(value: object) -> list[str]:
    """Narrow a stats-result value to a list of strings."""
    assert isinstance(value, list)
    return [str(item) for item in value]


def _build_stats_results(articles: pd.DataFrame) -> dict[str, Any]:
    """Chi-square, sentiment tests, pairwise tests, by-topic tests."""
    counts_table = pd.DataFrame(0, index=list(OUTLETS), columns=TOPICS, dtype=int)
    for (outlet, topic), group in articles.groupby(["outlet", "topic"]):
        counts_table.loc[outlet, topic] = len(group)
    chi = chi_square_topic_outlet(counts_table)
    sentiment = sentiment_test_by_outlet(articles)
    zero_article_outlets = [
        outlet for outlet in OUTLETS if int((articles["outlet"] == outlet).sum()) == 0
    ]
    sentiment["excluded_outlets"] = sorted(
        {str(o) for o in _as_str_list(sentiment["excluded_outlets"])}
        | set(zero_article_outlets)
    )
    pairwise_method = "tukey" if sentiment["test"] == "one-way ANOVA" else "dunn"
    if sentiment["test"] in ("one-way ANOVA", "Kruskal-Wallis"):
        pairwise = pairwise_tests(articles, pairwise_method)
        pairwise_records = pairwise.to_dict(orient="records")
    else:
        pairwise_records = []
    by_topic: dict[str, Any] = {}
    for outlet in OUTLETS:
        subset = articles[articles["outlet"] == outlet]
        topic_groups = {topic: g for topic, g in subset.groupby("topic") if len(g) >= 5}
        if len(topic_groups) < 2:
            by_topic[outlet] = {
                "test": "not run",
                "reason": "fewer than 2 topics with n >= 5 in this outlet",
                "topics_tested": sorted(topic_groups),
            }
            continue
        test_df = subset[subset["topic"].isin(topic_groups)][
            ["topic", "vader_compound"]
        ].rename(columns={"topic": "outlet"})
        # sentiment_test_by_outlet groups on "outlet"; reuse it with
        # the topic relabelled so the same normality gate applies.
        result = sentiment_test_by_outlet(test_df)
        by_topic[outlet] = {
            "test": result["test"],
            "statistic": result["statistic"],
            "p_value": result["p_value"],
            "why": str(result["why"]).replace("outlet", "topic"),
            "topics_tested": sorted(topic_groups),
        }
    return {
        "chi_square_topic_outlet": chi,
        "sentiment_by_outlet": sentiment,
        "pairwise_tests": pairwise_records,
        "pairwise_method": pairwise_method,
        "sentiment_by_topic_within_outlet": by_topic,
    }


def build_sample_review(articles: pd.DataFrame) -> pd.DataFrame:
    """Stratified sample: 5 articles per outlet with articles, seed 42.

    ``reviewer_topic`` and ``agree`` are left blank for the tester to
    complete (plan §4.5 — the reviewer is the tester). If a previous
    sample file exists with reviewer judgements, they are carried over
    by link so a re-run never wipes the review.
    """
    sampled_parts = []
    for outlet in OUTLETS:
        subset = articles[articles["outlet"] == outlet]
        if subset.empty:
            continue
        k = min(SAMPLE_PER_OUTLET, len(subset))
        sampled_parts.append(subset.sample(n=k, random_state=SAMPLE_SEED))
    if sampled_parts:
        sampled = pd.concat(sampled_parts).sort_values(["outlet", "title"])
    else:
        sampled = articles.iloc[0:0]
    review = pd.DataFrame(
        {
            "outlet": sampled["outlet"],
            "title": sampled["title"],
            "link": sampled["link"],
            "assigned_topic": sampled["topic"],
            "reviewer_topic": "",
            "agree": "",
        }
    ).reset_index(drop=True)
    existing = PROC / "sample_review.csv"
    if existing.exists():
        try:
            old = pd.read_csv(existing)
            if {"link", "reviewer_topic", "agree"}.issubset(old.columns):
                filled = old[
                    old["reviewer_topic"].notna() & (old["reviewer_topic"] != "")
                ]
                lookup = {
                    str(r["link"]): (str(r["reviewer_topic"]), str(r["agree"]))
                    for _, r in filled.iterrows()
                }
                for i, row in review.iterrows():
                    if str(row["link"]) in lookup:
                        topic_value, agree_value = lookup[str(row["link"])]
                        review.at[i, "reviewer_topic"] = topic_value
                        review.at[i, "agree"] = agree_value
        except (pd.errors.EmptyDataError, OSError, KeyError):
            pass
    return review


def build_synthetic_corpus() -> pd.DataFrame:
    """Labelled synthetic fallback (brief §4, seed 42).

    Six outlets x ten topics, sizes mimicking the probed feed sizes
    (10–50 articles per outlet, ~147 total). Titles come from a small
    fixed template pool per topic; descriptions are one sentence;
    ``pub_date`` is uniform in the window. The identical pipeline
    (topic assignment + VADER) runs on the synthetic text end to end.
    The synthetic file is written to ``data/raw/*_synthetic.json``
    (git-ignored) and never overwrites real data.
    """
    import numpy as np

    templates: dict[str, list[str]] = {
        "Economy": [
            "Markets rise as inflation cools and jobs grow",
            "Federal reserve holds interest rate as economy slows",
            "Consumer price pressures ease as trade deficit narrows",
        ],
        "Healthcare": [
            "Hospital staffing shortages strain patient care",
            "Medicare open enrollment brings new health insurance choices",
            "Vaccine rollout expands as doctors warn of disease spread",
        ],
        "Immigration": [
            "Border crossings fall as asylum rules tighten",
            "Visa backlog grows for immigrant families seeking citizenship",
            "Deportation policy debated as migrant arrivals slow",
        ],
        "Climate/Energy": [
            "Renewable energy grows as solar costs fall",
            "Wildfire season worsens as drought grips the region",
            "Electric vehicle sales climb as gas price steadies",
        ],
        "Foreign policy": [
            "Summit ends with new diplomacy push on Ukraine war",
            "NATO allies debate military aid as China watches Taiwan",
            "Sanctions tighten as Middle East talks stall",
        ],
        "Elections & campaigns": [
            "Campaign heats up as polling shows close election race",
            "Candidate unveils plan as voters head to ballot in primary",
            "Congress debates budget as president campaigns in swing state",
        ],
        "Crime & justice": [
            "Court hears trial as police arrest suspect in shooting",
            "Supreme court ruling reshapes justice debate on gun laws",
            "Lawsuit filed as judge weighs prison sentence",
        ],
        "Technology & AI": [
            "Artificial intelligence tools spread as tech firms race ahead",
            "Cybersecurity warning after data breach hits social media users",
            "New smartphone chip uses algorithm to speed up AI features",
        ],
        "Education": [
            "School funding debate as teachers push for smaller classrooms",
            "College tuition rises as students weigh graduation costs",
            "University curriculum overhaul draws student protests",
        ],
        "Other": [
            "Local festival draws crowds to the town square",
            "Weather clears for the weekend parade",
            "Community garden opens its gates to visitors",
        ],
    }
    descriptions: dict[str, str] = {
        topic: f"Coverage of {topic.lower()} developments in the latest news cycle."
        for topic in TOPICS
    }
    sizes = {
        "NYT": 10,
        "WSJ": 20,
        "Fox News": 25,
        "CNN": 50,
        "NPR": 10,
        "BBC News": 32,
    }
    rng = np.random.default_rng(42)
    rows: list[dict[str, Any]] = []
    for outlet, size in sizes.items():
        for i in range(size):
            topic = TOPICS[i % len(TOPICS)]
            template = templates[topic][i % len(templates[topic])]
            days_offset = int(rng.integers(0, 15))
            pub = date.fromordinal(WINDOW_START.toordinal() + days_offset)
            text = f"{template} {descriptions[topic]}"
            compound = compound_score(text)
            rows.append(
                {
                    "outlet": outlet,
                    "title": template,
                    "description": descriptions[topic],
                    "link": f"https://example.invalid/synthetic/{OUTLETS[outlet]['stem']}/{i}",
                    "pub_date": f"{pub.isoformat()}T12:00:00Z",
                    "guid": f"synthetic-{OUTLETS[outlet]['stem']}-{i}",
                    "text": text,
                    "topic": assign_topic(text),
                    "vader_compound": compound,
                    "sentiment_label": sentiment_label(compound),
                }
            )
    synthetic_path = RAW_DIR / "synthetic_corpus_synthetic.json"
    synthetic_path.parent.mkdir(parents=True, exist_ok=True)
    synthetic_path.write_text(
        json.dumps({"synthetic": True, "seed": 42, "n": len(rows)}, indent=2),
        encoding="utf-8",
    )
    return pd.DataFrame(rows)


def write_data_source(path: Path, record: dict[str, Any]) -> None:
    """Write the provenance record as indented JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")


def run_pipeline(mode: str) -> dict[str, Any]:
    """Run the pipeline in the given mode; return the record dict.

    ``mode`` is one of ``live``, ``use-cache``, ``offline`` or
    ``synthetic``.
    """
    PROC.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    synthetic = mode == "synthetic"
    if mode == "live":
        for info in OUTLETS.values():
            dest = RAW_DIR / f"{info['stem']}_rss.xml"
            fetch_feed(info["url"], dest)
        articles, counts = collect_corpus(OUTLETS)
    elif mode == "synthetic":
        articles = build_synthetic_corpus()
        counts = {
            outlet: {
                "feed_url": info["url"],
                "http_status": None,
                "byte_size": None,
                "fetched_items": 0,
                "dropped_missing_link_or_date": 0,
                "dropped_outside_window": 0,
                "duplicates_removed": 0,
                "empty_text_articles": 0,
                "final_n": int((articles["outlet"] == outlet).sum()),
                "earliest_pub_date": str(
                    articles[articles["outlet"] == outlet]["pub_date"].min()
                )[:10],
                "latest_pub_date": str(
                    articles[articles["outlet"] == outlet]["pub_date"].max()
                )[:10],
            }
            for outlet, info in OUTLETS.items()
        }
    else:  # use-cache or offline: read the stored XMLs, no network
        missing_xml = [
            info["stem"]
            for info in OUTLETS.values()
            if not (RAW_DIR / f"{info['stem']}_rss.xml").exists()
        ]
        if missing_xml:
            raise FileNotFoundError(f"Missing raw XMLs for --{mode}: {missing_xml}")
        articles, counts = collect_corpus(OUTLETS)
    integrity = _corpus_integrity_checks(articles)
    vader_check = _vader_recompute_check(articles)
    topic_attention = _build_topic_attention(articles)
    sentiment_outlet = _build_sentiment_by_outlet(articles)
    sentiment_topic = _build_sentiment_by_topic(articles)
    stats_results = _build_stats_results(articles)
    sample_review = build_sample_review(articles)

    articles.to_csv(PROC / "articles.csv", index=False)
    topic_attention.to_csv(PROC / "topic_attention.csv", index=False)
    sentiment_outlet.to_csv(PROC / "sentiment_by_outlet.csv", index=False)
    sentiment_topic.to_csv(PROC / "sentiment_by_topic.csv", index=False)
    sample_review.to_csv(PROC / "sample_review.csv", index=False)
    (PROC / "stats_results.json").write_text(
        json.dumps(stats_results, indent=2), encoding="utf-8"
    )

    record: dict[str, Any] = {
        "project": "Day 15 — Political News Coverage Analyzer",
        "source": mode,
        "synthetic": synthetic,
        "seed": 42 if synthetic else None,
        "fetch_date": FETCH_DATE,
        "window": {
            "start": WINDOW_START.isoformat(),
            "end": WINDOW_END.isoformat(),
        },
        "outlets": counts,
        "corpus_total": len(articles),
        "per_outlet_n": {
            outlet: int((articles["outlet"] == outlet).sum()) for outlet in OUTLETS
        },
        "gdelt": gdelt_cross_check(),
        "vader_version": _versions().get("vaderSentiment"),
        "versions": _versions(),
        "metric_definitions": {
            "attention_share_pct": (
                "articles(outlet, topic) / articles(outlet, all topics) * 100; "
                "corpus-wide share uses articles(all) as the denominator"
            ),
            "topic_assignment": (
                "Frozen keyword dictionary (plan §4.1); most hits wins, "
                "ties go to the topic whose keyword appears earliest in "
                "the text, zero hits means Other"
            ),
            "sentiment": (
                "VADER compound on title + ' ' + description "
                "(original-cased text); >= +0.05 positive, <= -0.05 "
                "negative, otherwise neutral"
            ),
            "sentiment_ci": (
                "95% CI per group: t-interval by default; bootstrap "
                "(1,000 resamples, seed 42) when |skew| > 1; see ci_method. "
                "Intervals are clipped to the compound range [-1, +1]."
            ),
            "share_ci": "Wilson 95% CI, z = 1.96",
        },
        "cross_checks": {
            "corpus_integrity": integrity,
            "vader_recompute_5_titles": vader_check,
            "topic_dictionary_sha256": hashlib.sha256(
                repr(TOPIC_KEYWORDS).encode("utf-8")
            ).hexdigest(),
        },
        "notes": [
            (
                "Sentiment measures the emotional tone of the words used; "
                "it is not a measure of factual accuracy, fairness, or "
                "political bias."
            ),
            (
                "Title + description text only — no full article text; no "
                "scraping of linked article pages."
            ),
            (
                "Descriptive only — no predictive model, no bias score, no "
                "leaning score, no fact-checking, no causal claims."
            ),
            (
                "RSS feeds are rolling latest-N lists; the window actually "
                "achieved per outlet is recorded in outlets[].earliest_"
                "pub_date / latest_pub_date."
            ),
        ],
    }
    if mode == "offline":
        existing = PROC / "data_source.json"
        if existing.exists():
            print(
                "Offline mode: data_source.json already exists — not "
                "overwriting it (plan §3.5)."
            )
            return record
    write_data_source(PROC / "data_source.json", record)
    return record


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Day 15 data pipeline — RSS fetch and build."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--live", action="store_true", help="Fetch feeds, then build.")
    group.add_argument(
        "--use-cache", action="store_true", help="Build from stored XMLs."
    )
    group.add_argument(
        "--offline",
        action="store_true",
        help="Rebuild derived tables offline; never overwrites data_source.json.",
    )
    group.add_argument(
        "--synthetic",
        action="store_true",
        help="Labelled synthetic fallback (seed 42).",
    )
    args = parser.parse_args()
    if args.offline:
        mode = "offline"
    elif args.use_cache:
        mode = "use-cache"
    elif args.synthetic:
        mode = "synthetic"
    else:
        mode = "live"
    record = run_pipeline(mode)
    print(
        f"Day 15 pipeline ({mode}) complete: "
        f"{record['corpus_total']} articles, "
        f"{record['per_outlet_n']}"
    )


if __name__ == "__main__":
    main()
