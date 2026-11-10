"""Day 6 — Viral Content Trend Explorer: offline pytest suite.

Covers trends.py (pure math), the Day 5 sentiment copy, synthetic
fallback determinism, the offline cache path, the committed CSVs
matching trend_table.csv, the notebook root resolution, and the
attribution / cohort-comparison wording. Runs from the repo root and
from inside the day folder.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import data_pipeline as pipeline
from src.sentiment import classify_sentiment, is_non_latin, score_comment
from src.trends import (
    TOPIC_ORDER,
    assign_topic,
    assign_week,
    assign_window,
    backtest_holdout,
    build_trend_table,
    classify_topic,
    compute_views_per_day,
    duration_bucket,
    mixed_signal,
    parse_duration,
    sensitivity_check,
    share_change,
    topic_share,
    volume_growth,
)

# ---------------------------------------------------------------------------
# (1) Topic assignment
# ---------------------------------------------------------------------------


def test_topic_python_priority_over_sql():
    # "Python" is checked first in the §4.1 priority order.
    assert assign_topic("SQL and Python guide", [], "") == "python"
    assert assign_topic("Python pandas tutorial", [], "") == "python"


def test_topic_assignment_each_rule():
    assert assign_topic("SQL Tutorial - Full Course", [], "") == "sql"
    assert assign_topic("Machine learning tutorial", [], "") == "ai_ml"
    assert assign_topic("ChatGPT explained", [], "") == "ai_ml"
    assert assign_topic("Power BI dashboard tutorial", [], "") == "bi_viz"
    assert assign_topic("Data analyst career roadmap", [], "") == "career"
    assert assign_topic("What is data analytics?", [], "") == "general"
    assert assign_topic("Random daily vlog", [], "") == "other"


def test_topic_assignment_uses_tags_and_description():
    assert assign_topic("My video", ["numpy"], "") == "python"
    assert assign_topic("My video", [], "learn mysql fast") == "sql"


# ---------------------------------------------------------------------------
# (2) Window / week boundaries
# ---------------------------------------------------------------------------


def test_window_boundary_belongs_to_recent():
    assert assign_window("2026-10-11T00:00:00Z") == "A"
    assert assign_window("2026-10-10T23:59:59Z") == "B"
    assert assign_window("2026-09-11T00:00:00Z") == "B"
    assert assign_window("2026-11-09T23:59:59Z") == "A"


def test_week_assignment_boundaries():
    assert assign_week("2026-09-11T00:00:00Z") == "W1"
    assert assign_week("2026-10-30T12:00:00Z") == "W8"
    assert assign_week("2026-11-06T00:00:00Z") == "W9"  # partial week
    assert assign_week("2026-11-09T23:30:18Z") == "W9"


def test_duration_parse_and_bucket():
    assert parse_duration("PT12M34S") == 754
    assert parse_duration("PT1H2M3S") == 3723
    assert parse_duration("PT60S") == 60
    assert duration_bucket(60) == "Short"
    assert duration_bucket(300) == "Short-form"
    assert duration_bucket(900) == "Medium"
    assert duration_bucket(1800) == "Long"
    assert duration_bucket(1801) == "Deep-dive"
    with pytest.raises(ValueError):
        parse_duration("not-a-duration")


# ---------------------------------------------------------------------------
# (3) views_per_day guard
# ---------------------------------------------------------------------------


def test_views_per_day_age_guard():
    assert compute_views_per_day(1000, 3) is None  # below the 7-day guard
    assert compute_views_per_day(1000, 6) is None
    assert compute_views_per_day(1000, 7) == pytest.approx(1000 / 7)
    assert compute_views_per_day(0, 7) == 0.0


# ---------------------------------------------------------------------------
# (4) Momentum math on a hand-computed frame
# ---------------------------------------------------------------------------


def _hand_frame() -> pd.DataFrame:
    """Hand-built frame: python 12 in A / 10 in B, ai_ml 5 in A / 10 in B.

    Totals: A = 17, B = 20. python share A = 12/17 = 70.59%,
    share B = 10/20 = 50.00% -> change +20.59 pp, growth +20%.
    """
    rows = []
    for _ in range(12):
        rows.append(
            {
                "topic": "python",
                "window": "A",
                "view_count": 700,
                "days_since_publish": 7,
            }
        )
    for _ in range(10):
        rows.append(
            {
                "topic": "python",
                "window": "B",
                "view_count": 700,
                "days_since_publish": 30,
            }
        )
    for _ in range(5):
        rows.append(
            {
                "topic": "ai_ml",
                "window": "A",
                "view_count": 700,
                "days_since_publish": 7,
            }
        )
    for _ in range(10):
        rows.append(
            {
                "topic": "ai_ml",
                "window": "B",
                "view_count": 700,
                "days_since_publish": 30,
            }
        )
    return pd.DataFrame(rows)


def test_momentum_math_hand_computed():
    frame = _hand_frame()
    assert topic_share({"python": 12, "ai_ml": 5}, 17)["python"] == pytest.approx(
        12 / 17 * 100
    )
    assert share_change(70.59, 50.0) == pytest.approx(20.59)
    assert volume_growth(12, 10) == pytest.approx(0.2)
    assert volume_growth(5, 0) is None  # no prior baseline, never infinite
    table = build_trend_table(frame)
    python = table[table["topic"] == "python"].iloc[0]
    assert python["n_A"] == 12 and python["n_B"] == 10
    assert python["share_A"] == pytest.approx(70.59, abs=0.01)
    assert python["share_B"] == pytest.approx(50.0)
    assert python["share_change_pp"] == pytest.approx(20.59, abs=0.01)
    assert python["volume_growth"] == pytest.approx(0.2)
    assert python["classification"] == "accelerating"
    ai_ml = table[table["topic"] == "ai_ml"].iloc[0]
    assert ai_ml["classification"] == "insufficient data"  # n_A = 5 < 10


def test_classification_threshold_boundaries():
    # Exactly at the thresholds with n >= 10 -> accelerating.
    assert classify_topic(12, 10, 3.0, 0.2) == "accelerating"
    assert classify_topic(10, 13, -3.0, -0.2308) == "fading"
    # Just under either threshold -> stable.
    assert classify_topic(12, 10, 2.99, 0.2) == "stable"
    assert classify_topic(12, 10, 3.0, 0.199) == "stable"
    # n = 9 in either window -> insufficient data, never classified.
    assert classify_topic(9, 10, 5.0, 0.5) == "insufficient data"
    assert classify_topic(10, 9, -5.0, -0.5) == "insufficient data"
    # No prior-window baseline -> reported as such, never infinite growth.
    assert classify_topic(10, 0, 5.0, None) == "no prior baseline"


# ---------------------------------------------------------------------------
# (5) Mixed-signal flag
# ---------------------------------------------------------------------------


def test_mixed_signal_flag():
    assert mixed_signal("accelerating", -0.31) is True
    assert mixed_signal("accelerating", -0.29) is False
    assert mixed_signal("fading", 0.31) is True
    assert mixed_signal("fading", 0.29) is False
    assert mixed_signal("stable", -0.5) is False
    assert mixed_signal("accelerating", None) is False


# ---------------------------------------------------------------------------
# (6) Holdout backtest
# ---------------------------------------------------------------------------


def _weekly_frame(w8_python: int, w8_ai_ml: int, w8_sql: int = 0) -> pd.DataFrame:
    data = {topic: [0] * 9 for topic in TOPIC_ORDER}
    weeks = ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9"]
    # python grows W1–W3 (30) -> W5–W7 (60); ai_ml flat (60 -> 60).
    for week in ("W1", "W2", "W3"):
        data["python"][weeks.index(week)] = 10
        data["ai_ml"][weeks.index(week)] = 20
    for week in ("W5", "W6", "W7"):
        data["python"][weeks.index(week)] = 20
        data["ai_ml"][weeks.index(week)] = 20
    data["python"][7] = w8_python
    data["ai_ml"][7] = w8_ai_ml
    data["sql"][7] = w8_sql
    return pd.DataFrame(data, index=weeks)


def test_backtest_hit_and_miss():
    hit = backtest_holdout(_weekly_frame(25, 20))
    assert hit["predicted_topic"] == "python"
    assert hit["computable"] is True
    assert hit["hit"] is True
    miss = backtest_holdout(_weekly_frame(5, 25, 10))
    assert miss["predicted_topic"] == "python"
    assert miss["hit"] is False


def test_backtest_degenerate_is_not_computable():
    # No first-half videos at all and an empty W8: no prediction to check.
    empty = pd.DataFrame(
        {topic: [0] * 9 for topic in TOPIC_ORDER},
        index=["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9"],
    )
    result = backtest_holdout(empty)
    assert result["computable"] is False
    assert result["hit"] is None


# ---------------------------------------------------------------------------
# (7) Age-guard sensitivity flip
# ---------------------------------------------------------------------------


def test_age_guard_sensitivity_flip():
    rows = [
        # Window A, young (age 8–9): fast; old (age 20–21): slow.
        {"topic": "python", "window": "A", "view_count": 8000, "days_since_publish": 8},
        {"topic": "python", "window": "A", "view_count": 9000, "days_since_publish": 9},
        {
            "topic": "python",
            "window": "A",
            "view_count": 2000,
            "days_since_publish": 20,
        },
        {
            "topic": "python",
            "window": "A",
            "view_count": 2100,
            "days_since_publish": 21,
        },
        # Window B: steady 500/day at either guard.
        {
            "topic": "python",
            "window": "B",
            "view_count": 15500,
            "days_since_publish": 31,
        },
        {
            "topic": "python",
            "window": "B",
            "view_count": 16000,
            "days_since_publish": 32,
        },
    ]
    frame = pd.DataFrame(rows)
    result = sensitivity_check(frame)
    assert result["python"]["direction_7d"] == "up"
    assert result["python"]["direction_14d"] == "down"
    assert result["python"]["flipped"] is True


# ---------------------------------------------------------------------------
# (8) Sentiment copy — Day 5 hand-computed cases
# ---------------------------------------------------------------------------


def test_sentiment_copy_matches_day5_cases():
    score, label, scored = score_comment("I love this tutorial, amazing work")
    assert (score, label, scored) == (0.7184, "positive", 2)
    score, label, scored = score_comment("This is terrible and boring")
    assert (score, label, scored) == (-0.6124, "negative", 2)
    # Negation flips the next scored word.
    score, label, _ = score_comment("not good")
    assert (score, label) == (-0.25, "negative")
    # Intensifier multiplies the next scored word by 1.5.
    score, label, _ = score_comment("very helpful")
    assert (score, label) == (0.3612, "positive")
    assert classify_sentiment(0.05) == "positive"
    assert classify_sentiment(-0.05) == "negative"
    assert classify_sentiment(0.0) == "neutral"
    assert classify_sentiment(0.049) == "neutral"


def test_non_latin_heuristic():
    assert is_non_latin("Привет мир это тестовый комментарий") is True
    assert is_non_latin("This is a normal English comment") is False
    assert is_non_latin("") is False


# ---------------------------------------------------------------------------
# (9) Synthetic fallback
# ---------------------------------------------------------------------------


def test_synthetic_deterministic_proportions_and_trend():
    videos_a, comments_a = pipeline.generate_synthetic(seed=42)
    videos_b, _ = pipeline.generate_synthetic(seed=42)
    assert len(videos_a) == 300
    assert videos_a.equals(videos_b)  # deterministic with seed 42
    counts = videos_a["topic"].value_counts().to_dict()
    assert counts == {
        "python": 150,
        "ai_ml": 85,
        "sql": 45,
        "career": 12,
        "bi_viz": 5,
        "general": 3,
    }
    # Built-in trend by construction: python rises, sql falls.
    python = videos_a[videos_a["topic"] == "python"]
    sql = videos_a[videos_a["topic"] == "sql"]
    early_weeks = ["W1", "W2", "W3"]
    late_weeks = ["W6", "W7", "W8", "W9"]
    assert (
        python[python["week"].isin(late_weeks)].shape[0]
        > python[python["week"].isin(early_weeks)].shape[0]
    )
    assert (
        sql[sql["week"].isin(early_weeks)].shape[0]
        > sql[sql["week"].isin(late_weeks)].shape[0]
    )
    assert len(comments_a) == 500  # 5 videos x 100 template comments


# ---------------------------------------------------------------------------
# (10) Synthetic never satisfies the cache check
# ---------------------------------------------------------------------------


def test_synthetic_files_do_not_satisfy_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "RAW_DIR", tmp_path)
    (tmp_path / "videos_synthetic.json").write_text('{"synthetic": true}')
    (tmp_path / "comments_synthetic.json").write_text('{"synthetic": true}')
    assert pipeline._load_cache() is None


def test_generate_synthetic_writes_no_files():
    before = {p.name for p in (ROOT / "data" / "raw").iterdir()}
    pipeline.generate_synthetic(seed=42)
    after = {p.name for p in (ROOT / "data" / "raw").iterdir()}
    assert before == after


# ---------------------------------------------------------------------------
# (11) Offline run uses the committed cache, no network
# ---------------------------------------------------------------------------


def test_offline_run_reproduces_live_outputs():
    source_path = ROOT / "data" / "processed" / "data_source.json"
    before = source_path.read_text()
    assert json.loads(before)["source"] == "live"
    proc = subprocess.run(
        [sys.executable, "-m", "src.data_pipeline", "--offline"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "offline mode" in proc.stdout
    videos = pd.read_csv(ROOT / "data" / "processed" / "videos.csv")
    assert len(videos) == 472
    # D-2 fix: an offline run must not clobber the live provenance
    # record — data_source.json is byte-identical afterwards (plan.md
    # §3.5). No restore needed.
    assert source_path.read_text() == before


# ---------------------------------------------------------------------------
# (12) Committed CSVs match the published trend table
# ---------------------------------------------------------------------------


def test_committed_csv_matches_trend_table():
    videos = pd.read_csv(ROOT / "data" / "processed" / "videos.csv")
    table = pd.read_csv(ROOT / "data" / "processed" / "trend_table.csv")
    assert len(videos) == 472
    assert videos["video_id"].is_unique
    assert set(table["topic"]) == set(TOPIC_ORDER)
    # Recompute python's full momentum numbers by hand from videos.csv.
    python = videos[videos["topic"] == "python"]
    n_a = int((python["window"] == "A").sum())
    n_b = int((python["window"] == "B").sum())
    total_a = int((videos["window"] == "A").sum())
    total_b = int((videos["window"] == "B").sum())
    share_a = n_a / total_a * 100
    share_b = n_b / total_b * 100
    row = table[table["topic"] == "python"].iloc[0]
    assert (n_a, n_b) == (69, 88)
    assert row["n_A"] == n_a and row["n_B"] == n_b
    assert row["share_A"] == pytest.approx(share_a, abs=0.01)
    assert row["share_B"] == pytest.approx(share_b, abs=0.01)
    assert row["share_change_pp"] == pytest.approx(share_a - share_b, abs=0.01)
    assert row["volume_growth"] == pytest.approx((n_a - n_b) / n_b, abs=0.0001)
    assert row["classification"] == "fading"
    eligible_b = python[(python["window"] == "B") & (python["days_since_publish"] >= 7)]
    median_b = (eligible_b["view_count"] / eligible_b["days_since_publish"]).median()
    assert row["median_views_per_day_B"] == pytest.approx(median_b, abs=0.001)
    # Window A has no age-eligible videos, so its velocity is undefined.
    assert pd.isna(row["median_views_per_day_A"])
    assert row["velocity_n_A"] == 0


# ---------------------------------------------------------------------------
# (13) Notebook _find_root() resolves from the notebook's own location
# ---------------------------------------------------------------------------


def test_notebook_find_root():
    notebook = json.loads((ROOT / "notebooks" / "analysis.ipynb").read_text())
    code_cells = [
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    ]
    assert code_cells, "notebook has no code cells"
    namespace: dict = {"__file__": str(ROOT / "notebooks" / "analysis.ipynb")}
    code = compile(code_cells[0], "analysis.ipynb cell 1", "exec")
    exec(code, namespace)  # noqa: S102 - plan §6 test 13 requires exec
    root = namespace["_find_root"]()
    assert root == ROOT
    assert (root / "data" / "processed" / "videos.csv").exists()


# ---------------------------------------------------------------------------
# (14) Attribution + cohort-comparison wording
# ---------------------------------------------------------------------------


def test_attribution_and_cohort_sentence_present():
    app_text = (ROOT / "src" / "app.py").read_text()
    readme_text = (ROOT / "README.md").read_text()
    briefing_text = (ROOT / "outputs" / "weekly_briefing.md").read_text()
    cohort_sentence = (
        "Trends here compare two 30-day cohorts of recently published videos"
    )
    assert "Data from the YouTube Data API v3" in app_text
    assert "Data from the YouTube Data API v3" in readme_text
    assert "https://www.youtube.com/t/terms" in app_text
    assert cohort_sentence in readme_text
    assert cohort_sentence in app_text
    assert cohort_sentence in briefing_text
    assert "use_container_width" not in app_text
