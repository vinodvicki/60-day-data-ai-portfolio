"""Tests for Day 4 — YouTube Video Performance Analyzer. Offline, no network.

Covers plan §6: duration parsing, bucket boundaries, topic/format
classification priority, KPI formulas on a hand-computed fixture,
high-performer flag, synthetic determinism and cache separation,
offline mode, CSV/README consistency, notebook _find_root(), and
attribution / descriptive-sentence presence.
"""

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import data_pipeline
from youtube_kpi import (
    build_recommendations,
    classify_format,
    classify_topic,
    compute_kpis,
    duration_bucket,
    parse_duration_iso8601,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# --- 1. Duration parsing -------------------------------------------------------
def test_parse_duration_hand_computed():
    assert parse_duration_iso8601("PT12M34S") == 754
    assert parse_duration_iso8601("PT1H2M3S") == 3723
    assert parse_duration_iso8601("PT45S") == 45
    assert parse_duration_iso8601("PT9M4S") == 544
    # A real long video in this dataset carries a day component.
    assert parse_duration_iso8601("P1DT4H41M8S") == 103268


def test_parse_duration_raises():
    with pytest.raises(ValueError):
        parse_duration_iso8601("not a duration")
    with pytest.raises(ValueError):
        parse_duration_iso8601("PT0S")
    with pytest.raises(ValueError):
        parse_duration_iso8601("")


# --- 2. Duration buckets at every boundary --------------------------------------
def test_duration_bucket_boundaries():
    assert duration_bucket(60) == "short"
    assert duration_bucket(61) == "short_form"
    assert duration_bucket(300) == "short_form"
    assert duration_bucket(301) == "medium"
    assert duration_bucket(900) == "medium"
    assert duration_bucket(901) == "long"
    assert duration_bucket(1800) == "long"
    assert duration_bucket(1801) == "deep_dive"
    assert duration_bucket(3) == "short"
    assert duration_bucket(107308) == "deep_dive"


# --- 3. Topic classification priority --------------------------------------------
def test_topic_priority_python_beats_sql():
    # Matches both python and sql keywords -> python wins (first match).
    assert (
        classify_topic(
            "Python and SQL Tutorial for Data Analysis",
            ["python", "sql"],
            "Learn python and sql.",
        )
        == "python"
    )


def test_topic_each_group_and_other():
    assert classify_topic("SQL Tutorial", [], "") == "sql"
    assert classify_topic("Machine Learning Explained with ChatGPT", [], "") == "ai_ml"
    assert classify_topic("Power BI Dashboard Guide", [], "") == "bi_viz"
    assert classify_topic("Data Analyst Career Roadmap", [], "") == "career"
    assert classify_topic("What Is Data Analytics?", [], "") == "general"
    assert classify_topic("Guitar Lessons for Beginners", [], "") == "other"


# --- 4. Format classification ------------------------------------------------------
def test_format_classification():
    assert classify_format("Python Tutorial for Beginners", []) == "tutorial"
    # NOTE: "Machine Learning Explained" classifies as tutorial under the
    # plan's verbatim rule, because "learning" contains the tutorial
    # keyword "learn" — so the explainer case uses a title without it.
    assert classify_format("What Is SQL? An Introduction", []) == "explainer"
    assert classify_format("My Daily Vlog", []) == "other"
    # Tutorial wins on overlap (title matches both lists).
    assert classify_format("Python Tutorial Explained Step by Step", []) == "tutorial"


# --- 5. KPI formulas on a hand-computed fixture --------------------------------------
def _fixture_frame():
    return pd.DataFrame(
        {
            "video_id": ["AAA", "BBB", "CCC"],
            "title": ["Python Tutorial", "SQL Guide", "Vlog"],
            "channel_id": ["UC1", "UC1", "UC2"],
            "channel_title": ["Chan One", "Chan One", "Chan Two"],
            "published_at": [
                "2026-11-07T00:00:00Z",  # 1 day before fetch date
                "2026-10-09T00:00:00Z",  # 30 days before fetch date
                "2026-11-08T00:00:00Z",  # fetch day -> minimum 1 day
            ],
            "view_count": [1000, 60000, 500],
            "like_count": [50.0, 1200.0, float("nan")],
            "comment_count": [10.0, 300.0, 5.0],
            "subscriber_count": [10000.0, 10000.0, float("nan")],
            "duration_seconds": [120, 1200, 45],
            "category_id": ["27", "27", "22"],
            "tags": [["python"], ["sql"], []],
            "description": ["", "", ""],
        }
    )


def test_kpi_formulas_hand_computed():
    df = compute_kpis(_fixture_frame())
    # days_since_publish: 1, 30, and minimum 1 for the fetch-day video.
    assert list(df["days_since_publish"]) == [1, 30, 1]
    # views_per_day = views / days.
    assert df.loc[0, "views_per_day"] == pytest.approx(1000.0)
    assert df.loc[1, "views_per_day"] == pytest.approx(2000.0)
    assert df.loc[2, "views_per_day"] == pytest.approx(500.0)
    # engagement_rate = (likes + comments) / views.
    assert df.loc[0, "engagement_rate"] == pytest.approx(0.06)
    assert df.loc[1, "engagement_rate"] == pytest.approx(0.025)
    # Missing like count -> NaN engagement, never 0.
    assert pd.isna(df.loc[2, "engagement_rate"])
    assert pd.isna(df.loc[2, "like_rate"])
    # like_rate / comment_rate components.
    assert df.loc[0, "like_rate"] == pytest.approx(0.05)
    assert df.loc[0, "comment_rate"] == pytest.approx(0.01)
    # views_per_subscriber; NaN where subscriber count is hidden.
    assert df.loc[0, "views_per_subscriber"] == pytest.approx(0.1)
    assert pd.isna(df.loc[2, "views_per_subscriber"])
    # Buckets and topics on the fixture.
    assert list(df["duration_bucket"]) == [
        "short_form",
        "long",
        "short",
    ]
    assert list(df["topic"]) == ["python", "sql", "other"]


# --- 6. High-performer flag = top quartile of views_per_day -------------------------
def test_high_performer_top_quartile():
    df = compute_kpis(_fixture_frame())
    # views_per_day values 1000, 2000, 500 -> 75th percentile is 1500.
    assert list(df["high_performer"]) == [False, True, False]


# --- 7. Synthetic generation: deterministic, n=200, 20 channels x 10 ------------------
def test_synthetic_deterministic():
    raw_a = data_pipeline.generate_synthetic(seed=42)
    raw_b = data_pipeline.generate_synthetic(seed=42)
    assert raw_a == raw_b
    videos = raw_a["videos_details"]["items"]
    channels = raw_a["channels_details"]["items"]
    assert len(videos) == 200
    assert len(channels) == 20
    counts = pd.Series([v["snippet"]["channelId"] for v in videos]).value_counts()
    assert (counts == 10).all()
    # Synthetic titles classify into the topic groups.
    frame = data_pipeline.clean_videos(raw_a)
    assert len(frame) == 200
    assert set(frame["topic"].unique()) <= {
        "python",
        "sql",
        "ai_ml",
        "bi_viz",
        "career",
        "general",
    }


# --- 8. Synthetic never overwrites the live cache --------------------------------------
def _load_pipeline_copy(tmp_path: Path):
    """Import a copy of the pipeline rooted at tmp_path (isolated)."""
    day = tmp_path / "day"
    shutil.copytree(PROJECT_ROOT / "src", day / "src")
    (day / "data" / "raw").mkdir(parents=True)
    (day / "data" / "processed").mkdir(parents=True)
    sys.path.insert(0, str(day))
    spec = importlib.util.spec_from_file_location(
        "day04_pipeline_copy", day / "src" / "data_pipeline.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, day


def test_synthetic_does_not_satisfy_cache(tmp_path):
    module, day = _load_pipeline_copy(tmp_path)
    # Only a synthetic file present: cache check must fail.
    (day / "data" / "raw" / "videos_details_synthetic.json").write_text("{}")
    assert module._load_cache() is None
    # Copy the real live cache in: cache check must pass.
    for stem in [
        "search_data-analytics",
        "search_machine-learning-tutorial",
        "search_python-data-analysis",
        "search_artificial-intelligence-explained",
        "search_sql-tutorial",
        "videos_details",
        "channels_details",
    ]:
        shutil.copy(
            PROJECT_ROOT / "data" / "raw" / f"{stem}.json",
            day / "data" / "raw" / f"{stem}.json",
        )
    assert module._load_cache() is not None


# --- 9. Offline mode runs without network -----------------------------------------------
def test_offline_mode_runs_without_network(tmp_path):
    _module, day = _load_pipeline_copy(tmp_path)
    for stem in [
        "search_data-analytics",
        "search_machine-learning-tutorial",
        "search_python-data-analysis",
        "search_artificial-intelligence-explained",
        "search_sql-tutorial",
        "videos_details",
        "channels_details",
    ]:
        shutil.copy(
            PROJECT_ROOT / "data" / "raw" / f"{stem}.json",
            day / "data" / "raw" / f"{stem}.json",
        )
    proc = subprocess.run(
        [sys.executable, "-m", "src.data_pipeline", "--offline"],
        cwd=day,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert (day / "data" / "processed" / "videos.csv").exists()
    source = json.loads((day / "data" / "processed" / "data_source.json").read_text())
    assert source["source"] == "cache"
    assert source["synthetic"] is False


# --- 10. Committed CSV matches the published findings ------------------------------------
def test_csv_matches_published_findings():
    df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "videos.csv")
    source = json.loads(
        (PROJECT_ROOT / "data" / "processed" / "data_source.json").read_text()
    )
    assert source["video_count"] == len(df)
    assert source["source"] == "live"
    assert df["video_id"].duplicated().sum() == 0
    # Recompute one video's engagement_rate from the CSV itself.
    row = df[df["video_id"] == "yZvFH7B6gKI"].iloc[0]
    hand_eng = (row["like_count"] + row["comment_count"]) / row["view_count"]
    assert hand_eng == pytest.approx(row["engagement_rate"])
    hand_vpd = row["view_count"] / row["days_since_publish"]
    assert hand_vpd == pytest.approx(row["views_per_day"])
    # The README states the headline numbers from this CSV.
    readme = (PROJECT_ROOT / "README.md").read_text()
    assert str(len(df)) in readme  # "244 videos"
    assert f"{df['views_per_day'].median():,.0f}" in readme


# --- 11. Notebook _find_root() resolves from the notebook's own location -----------------
def test_notebook_find_root():
    nb = json.loads((PROJECT_ROOT / "notebooks" / "analysis.ipynb").read_text())
    cell_sources = [
        "".join(cell["source"]) for cell in nb["cells"] if cell["cell_type"] == "code"
    ]
    root_cell = next(s for s in cell_sources if "_find_root" in s)
    namespace: dict = {"__file__": str(PROJECT_ROOT / "notebooks" / "analysis.ipynb")}
    exec(compile(root_cell, "<notebook>", "exec"), namespace)  # noqa: S102
    assert namespace["_find_root"]() == PROJECT_ROOT


# --- 12. Attribution + descriptive sentence present -----------------------------------------
def test_attribution_and_descriptive_sentence():
    attribution = "Data from the YouTube Data API v3"
    sentence = (
        "Performance patterns here describe this sampled set of public "
        "videos. They are descriptive, not causal, and are not a "
        "guarantee of future performance."
    )
    readme = (PROJECT_ROOT / "README.md").read_text()
    assert attribution in readme
    assert sentence in " ".join(readme.split())
    app = (PROJECT_ROOT / "src" / "app.py").read_text()
    assert attribution in app
    assert sentence in " ".join(app.split())
    insights = (PROJECT_ROOT / "outputs" / "insights_summary.md").read_text()
    assert sentence in " ".join(insights.split())
    # No causal verbs in the recommendations file.
    recs = (PROJECT_ROOT / "outputs" / "recommendations.md").read_text().lower()
    for verb in ("will boost", "causes", "guarantees"):
        assert verb not in recs


def test_recommendations_are_evidence_cited():
    df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "videos.csv")
    recs = build_recommendations(df)
    assert len(recs) >= 4
    for rec in recs:
        assert set(rec) == {
            "recommendation",
            "evidence",
            "sample_basis",
            "caveat",
        }
        assert "not a causal finding" in rec["caveat"]
