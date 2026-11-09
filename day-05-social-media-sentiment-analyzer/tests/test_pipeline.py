"""Tests for Day 5 — Social Media Sentiment Analyzer. Offline, no network.

Covers plan §6: lexicon scoring on hand-computed cases, classification
thresholds, theme classification, the non-Latin heuristic, top words /
bigrams, evaluation metrics on a hand-computed confusion case, the
validation sample (stratified 40/40/40, seed 42), synthetic determinism
and cache separation, offline mode, the clean/filter pipeline on a
constructed raw frame, CSV/README consistency, notebook _find_root(),
and attribution / model-not-ground-truth presence.
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
from sentiment import (
    NEGATIVE_WORDS,
    POSITIVE_WORDS,
    classify_sentiment,
    classify_themes,
    evaluate_predictions,
    is_non_latin,
    score_comment,
    top_bigrams,
    top_words,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# --- 1. Scoring on hand-computed cases ---------------------------------------
def test_score_comment_hand_computed():
    # "love" (+2) + "amazing" (+2) = 4 -> 4 / sqrt(31) = 0.7184
    assert score_comment("I love this tutorial, amazing work") == (
        0.7184,
        "positive",
        2,
    )
    # "terrible" (-2) + "boring" (-1) = -3 -> -3 / sqrt(24) = -0.6124
    assert score_comment("This is terrible and boring") == (
        -0.6124,
        "negative",
        2,
    )
    # "not" flips "good" (+1) -> -1 -> -1 / sqrt(16) = -0.25
    assert score_comment("not good") == (-0.25, "negative", 1)
    # "not" flips "bad" (-1) -> +1 -> 0.25
    assert score_comment("not bad") == (0.25, "positive", 1)
    # "very" x1.5 on "helpful" (+1) = 1.5 -> 1.5 / sqrt(17.25) = 0.3612
    assert score_comment("very helpful") == (0.3612, "positive", 1)
    # Two fire emoji, capped at +2, no words -> 2 / sqrt(19) = 0.4588
    assert score_comment("🔥🔥") == (0.4588, "positive", 0)
    # No lexicon signal -> neutral by default, 0 scored words.
    assert score_comment("What software is used?") == (0.0, "neutral", 0)
    assert score_comment("ok") == (0.0, "neutral", 0)
    assert score_comment("") == (0.0, "neutral", 0)
    # "thank" (+1) + "best" (+1, intensified by "so" -> 1.5) = 2.5,
    # +0.25 for "!" -> 2.75 -> 2.75 / sqrt(22.5625) = 0.5789
    assert score_comment("Thank you so much, best explanation ever!") == (
        0.5789,
        "positive",
        2,
    )


def test_lexicon_lists_present_and_counted():
    # Brief §3.1: ~100-150 words per side, strong sets of exactly 6 each.
    assert 100 <= len(POSITIVE_WORDS) <= 160
    assert 100 <= len(NEGATIVE_WORDS) <= 160
    assert not (POSITIVE_WORDS & NEGATIVE_WORDS)
    from sentiment import STRONG_NEGATIVE, STRONG_POSITIVE

    assert STRONG_POSITIVE == {
        "love",
        "amazing",
        "brilliant",
        "excellent",
        "fantastic",
        "perfect",
    }
    assert STRONG_NEGATIVE == {
        "hate",
        "terrible",
        "awful",
        "horrible",
        "worst",
        "useless",
    }


# --- 2. Classification thresholds --------------------------------------------
def test_classify_sentiment_thresholds():
    assert classify_sentiment(0.049) == "neutral"
    assert classify_sentiment(0.05) == "positive"
    assert classify_sentiment(-0.049) == "neutral"
    assert classify_sentiment(-0.05) == "negative"
    assert classify_sentiment(0.0) == "neutral"
    assert classify_sentiment(0.9) == "positive"
    assert classify_sentiment(-0.9) == "negative"


# --- 3. Theme classification ---------------------------------------------------
def test_classify_themes():
    assert classify_themes("Thank you so much, best explanation ever!") == [
        "praise",
        "tutorial_quality",
    ]
    # A question without "?" is not the questions theme.
    assert classify_themes("What software is used") == ["other"]
    assert classify_themes("Can anyone explain the part at 5 minutes?") == ["questions"]
    # Up to 2 themes, in priority order.
    assert classify_themes(
        "thank you, great video, but the audio is bad and too fast, " "how do I fix it?"
    ) == ["praise", "tutorial_quality"]
    assert classify_themes("This is terrible and boring") == ["criticism"]
    assert classify_themes("48:26") == ["other"]
    assert classify_themes("lol that was funny 😂") == ["humor"]


# --- 4. Non-Latin heuristic ----------------------------------------------------
def test_is_non_latin():
    assert is_non_latin("Это отличный урок, спасибо!")
    assert is_non_latin("هذا درس رائع")
    assert not is_non_latin("This is a great tutorial, thanks!")
    # Latin-script Spanish is NOT caught (documented limitation).
    assert not is_non_latin("Este tutorial es muy bueno, gracias")
    assert not is_non_latin("")
    assert not is_non_latin("🔥🔥🔥")


# --- 5. Top words / bigrams ------------------------------------------------------
def test_top_words_and_bigrams_hand_computed():
    # "video" and "tutorial" are stopwords (brief §3.2), so use other words.
    texts = ["great lesson great", "great clip", "bad clip bad"]
    assert top_words(texts, n=10) == [
        ("great", 3),
        ("bad", 2),
        ("clip", 2),
        ("lesson", 1),
    ]
    assert top_bigrams(texts, n=10) == [
        ("bad clip", 1),
        ("clip bad", 1),
        ("great clip", 1),
        ("great lesson", 1),
        ("lesson great", 1),
    ]
    # Stopwords are removed ("the", "is"); "data"/"video" are stopwords too.
    assert top_words(["the video is great"], n=5) == [("great", 1)]


# --- 6. Evaluation metrics on a hand-computed case ------------------------------
def test_evaluate_predictions_hand_computed():
    predicted = ["positive", "positive", "negative", "neutral", "neutral", "positive"]
    human = ["positive", "neutral", "negative", "neutral", "positive", "negative"]
    result = evaluate_predictions(predicted, human)
    # Confusion (rows=true): pos {pos:1, neu:1, neg:0}; neu {pos:1, neu:1,
    # neg:0}; neg {pos:1, neu:0, neg:1}.
    assert result["confusion"]["positive"] == {
        "positive": 1,
        "neutral": 1,
        "negative": 0,
    }
    assert result["confusion"]["negative"] == {
        "positive": 1,
        "neutral": 0,
        "negative": 1,
    }
    # Per-class metrics are rounded to 4 dp by evaluate_predictions.
    assert result["per_class"]["positive"] == {
        "precision": 0.3333,
        "recall": 0.5,
        "f1": 0.4,
        "support": 2,
    }
    assert result["per_class"]["neutral"]["f1"] == 0.5
    assert result["per_class"]["negative"]["precision"] == 1.0
    assert result["per_class"]["negative"]["recall"] == 0.5
    assert result["accuracy"] == 0.5
    assert result["macro_f1"] == 0.5222
    assert result["n"] == 6
    with pytest.raises(ValueError):
        evaluate_predictions(["positive"], ["positive", "neutral"])
    with pytest.raises(ValueError):
        evaluate_predictions(["great"], ["positive"])


# --- 7. Validation sample: stratified 40/40/40, seed 42 -------------------------
def test_validation_sample_stratified_and_reproducible():
    _raw, frame = data_pipeline.generate_synthetic(seed=42)
    sample_a = data_pipeline.draw_validation_sample(frame)
    sample_b = data_pipeline.draw_validation_sample(frame)
    assert sample_a["comment_id"].tolist() == sample_b["comment_id"].tolist()
    assert len(sample_a) == 120
    assert sample_a["predicted"].value_counts().to_dict() == {
        "positive": 40,
        "neutral": 40,
        "negative": 40,
    }
    assert sample_a["comment_id"].is_unique


# --- 8. Synthetic: deterministic, n=1800, 150/video, mix 45/35/20 --------------
def test_synthetic_deterministic():
    raw_a, frame_a = data_pipeline.generate_synthetic(seed=42)
    raw_b, frame_b = data_pipeline.generate_synthetic(seed=42)
    assert raw_a == raw_b
    assert frame_a.equals(frame_b)
    assert len(frame_a) == 1800
    counts = frame_a.groupby("video_id").size()
    assert len(counts) == 12
    assert (counts == 150).all()
    shares = frame_a["sentiment"].value_counts(normalize=True)
    assert shares["positive"] == pytest.approx(0.45, abs=0.05)
    assert shares["neutral"] == pytest.approx(0.35, abs=0.05)
    assert shares["negative"] == pytest.approx(0.20, abs=0.05)
    # Synthetic comments score through the same lexicon path.
    assert set(frame_a["sentiment"].unique()) <= {
        "positive",
        "neutral",
        "negative",
    }


# --- 9. Synthetic never satisfies the cache check --------------------------------
def _load_pipeline_copy(tmp_path: Path):
    """Import a copy of the pipeline rooted at tmp_path (isolated)."""
    day = tmp_path / "day"
    shutil.copytree(PROJECT_ROOT / "src", day / "src")
    (day / "data" / "raw").mkdir(parents=True)
    (day / "data" / "processed").mkdir(parents=True)
    sys.path.insert(0, str(day))
    spec = importlib.util.spec_from_file_location(
        "day05_pipeline_copy", day / "src" / "data_pipeline.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, day


def test_synthetic_does_not_satisfy_cache(tmp_path):
    module, day = _load_pipeline_copy(tmp_path)
    # Only a synthetic file present: cache check must fail.
    (day / "data" / "raw" / "comments_synthetic.json").write_text("{}")
    assert module._load_cache() is None
    # Copy the real live cache in: cache check must pass.
    for video in data_pipeline.VIDEOS:
        shutil.copy(
            PROJECT_ROOT / "data" / "raw" / f"comments_{video['video_id']}.json",
            day / "data" / "raw" / f"comments_{video['video_id']}.json",
        )
    assert module._load_cache() is not None


# --- 10. Offline mode runs without network -----------------------------------------
def test_offline_mode_runs_without_network(tmp_path):
    _module, day = _load_pipeline_copy(tmp_path)
    for video in data_pipeline.VIDEOS:
        shutil.copy(
            PROJECT_ROOT / "data" / "raw" / f"comments_{video['video_id']}.json",
            day / "data" / "raw" / f"comments_{video['video_id']}.json",
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
    assert (day / "data" / "processed" / "comments.csv").exists()
    source = json.loads((day / "data" / "processed" / "data_source.json").read_text())
    assert source["source"] == "cache"
    assert source["synthetic"] is False


# --- 11. Clean/filter pipeline on a constructed raw frame ---------------------------
def _thread(
    comment_id: str,
    text: str,
    published: str,
    author_channel: str = "UCviewer",
    channel_id: str = "UCchan",
    likes: int = 0,
) -> dict:
    return {
        "id": comment_id,
        "snippet": {
            "channelId": channel_id,
            "videoId": "yZvFH7B6gKI",
            "topLevelComment": {
                "kind": "youtube#comment",
                "id": comment_id,
                "snippet": {
                    "channelId": channel_id,
                    "videoId": "yZvFH7B6gKI",
                    "textDisplay": text,
                    "textOriginal": text,
                    "authorDisplayName": "@viewer",
                    "authorChannelId": {"value": author_channel},
                    "likeCount": likes,
                    "publishedAt": published,
                    "updatedAt": published,
                },
            },
            "canReply": True,
            "totalReplyCount": 0,
            "isPublic": True,
        },
    }


def test_clean_comments_filters_in_order():
    raw = {
        "yZvFH7B6gKI": {
            "items": [
                _thread("c1", "Great tutorial, thank you!", "2026-06-01T10:00:00Z"),
                _thread("c1", "Great tutorial, thank you!", "2026-06-01T10:00:00Z"),
                _thread(
                    "c2",
                    "Subscribe to my channel!",
                    "2026-06-02T10:00:00Z",
                    author_channel="UCchan",
                ),
                _thread("c3", "   ", "2026-06-03T10:00:00Z"),
                _thread("c4", "Old comment", "2024-01-01T10:00:00Z"),
                _thread("c5", "Это отличный урок!", "2026-06-04T10:00:00Z"),
            ],
            "pages": 1,
            "calls": 1,
        }
    }
    frame, counts = data_pipeline.clean_comments(raw)
    assert counts == {
        "fetched": 6,
        "duplicates": 1,
        "owner": 1,
        "empty": 1,
        "outside_window": 1,
        "non_latin": 1,
        "analysed": 1,
    }
    assert len(frame) == 1
    assert frame.iloc[0]["comment_id"] == "c1"
    assert frame.iloc[0]["sentiment"] == "positive"
    assert frame.iloc[0]["month"] == "2026-06"


# --- 12. Committed CSV matches the published findings --------------------------------
def test_csv_matches_published_findings():
    df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "comments.csv")
    source = json.loads(
        (PROJECT_ROOT / "data" / "processed" / "data_source.json").read_text()
    )
    assert source["comment_count_analysed"] == len(df)
    assert source["source"] == "live"
    assert source["synthetic"] is False
    assert df["comment_id"].duplicated().sum() == 0
    assert set(df["sentiment"].unique()) <= {"positive", "neutral", "negative"}
    # Recompute one comment's sentiment score from the CSV itself.
    row = df[df["scored_words"] > 0].iloc[0]
    score, sentiment, scored = score_comment(row["text"])
    assert score == pytest.approx(row["sentiment_score"])
    assert sentiment == row["sentiment"]
    assert scored == row["scored_words"]
    # The README states the headline numbers from this CSV.
    readme = (PROJECT_ROOT / "README.md").read_text()
    assert "1,462" in readme  # headline count, comma-formatted
    positive_share = f"{(df['sentiment'] == 'positive').mean() * 100:.1f}%"
    assert positive_share in readme


# --- 13. Notebook _find_root() resolves from the notebook's own location ---------------
def test_notebook_find_root():
    nb = json.loads((PROJECT_ROOT / "notebooks" / "analysis.ipynb").read_text())
    cell_sources = [
        "".join(cell["source"]) for cell in nb["cells"] if cell["cell_type"] == "code"
    ]
    root_cell = next(s for s in cell_sources if "_find_root" in s)
    namespace: dict = {"__file__": str(PROJECT_ROOT / "notebooks" / "analysis.ipynb")}
    exec(compile(root_cell, "<notebook>", "exec"), namespace)  # noqa: S102
    assert namespace["_find_root"]() == PROJECT_ROOT


# --- 14. Attribution + model-not-ground-truth sentence present ---------------------------
def test_attribution_and_model_limitations():
    readme = (PROJECT_ROOT / "README.md").read_text()
    assert "Data from the YouTube Data API v3" in readme
    assert "rule-based model" in readme
    assert "not ground truth" in readme
    app = (PROJECT_ROOT / "src" / "app.py").read_text()
    assert "Data from the YouTube Data API v3" in app
    assert "rule-based model" in app
    insights = (PROJECT_ROOT / "outputs" / "insights_summary.md").read_text()
    assert "rule-based model" in insights
    assert "not ground truth" in insights
    # The validation labels file exists with exactly 120 rows (40/class).
    labels = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "validation_labels.csv")
    assert len(labels) == 120
    assert set(labels["human_label"].unique()) <= {"positive", "neutral", "negative"}
