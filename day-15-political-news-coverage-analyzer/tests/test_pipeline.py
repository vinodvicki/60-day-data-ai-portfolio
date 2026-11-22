"""Tests for Day 15 — Political News Coverage Analyzer.

Fixture tests cover the pure topic / sentiment / stats functions;
file tests verify the committed tables against the plan's rules
(guardrail sentence on all four surfaces, no forbidden word in chart
titles or dashboard headings, same columns for all six outlets,
dictionary byte-identical to the README listing, sparse-cell rule,
ANOVA-vs-Kruskal-Wallis selection, corrected pairwise tests only,
sample review 5-per-outlet seed 42, offline run never clobbers
data_source.json — tolerance comparison, Day 9 lesson — synthetic
files never overwrite live files, data-size rule, .gitignore rule).
"""

from __future__ import annotations

import ast
import fnmatch
import hashlib
import json
import pprint
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# The day folder must be on sys.path before the src imports: the
# orchestrator runs pytest from the portfolio root (Day 12 pattern).
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import data_pipeline
from src.data_pipeline import (
    build_sample_review,
    build_synthetic_corpus,
    collect_corpus,
    gdelt_cross_check,
    run_pipeline,
)
from src.sentiment import compound_score, sentiment_label, summarise
from src.stats import (
    bootstrap_ci,
    chi_square_topic_outlet,
    pairwise_tests,
    permutation_pvalue,
    sentiment_test_by_outlet,
)
from src.topics import (
    TOPIC_KEYWORDS,
    TOPICS,
    assign_topic,
    attention_share,
    wilson_ci,
)

PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUTLETS = ["NYT", "WSJ", "Fox News", "CNN", "NPR", "BBC News"]
GUARDRAIL_SENTENCE = (
    "Sentiment measures the emotional tone of the words used; "
    "it is not a measure of factual accuracy, fairness, or political bias."
)
FORBIDDEN = re.compile(r"\b(bias|biased|leaning|left|right)\b", re.IGNORECASE)


def _articles() -> pd.DataFrame:
    """Load the committed articles table."""
    return pd.read_csv(PROC / "articles.csv")


def _attention() -> pd.DataFrame:
    """Load the committed attention-share table."""
    return pd.read_csv(PROC / "topic_attention.csv")


# --- topic assignment -------------------------------------------------


def test_assign_topic_most_hits_wins() -> None:
    """Most keyword hits wins."""
    assert assign_topic("Election campaign vote candidate polling") == (
        "Elections & campaigns"
    )
    assert assign_topic("Hospital doctor vaccine patient health") == "Healthcare"


def test_assign_topic_tie_goes_to_earliest_keyword() -> None:
    """Ties go to the topic whose keyword appears earliest in the text."""
    # "war" (Foreign policy) appears before "school" (Education), one hit each.
    assert assign_topic("war school") == "Foreign policy"
    assert assign_topic("school war") == "Education"


def test_assign_topic_zero_hits_is_other() -> None:
    """Zero hits means Other."""
    assert assign_topic("A quiet afternoon in the garden") == "Other"
    assert assign_topic("") == "Other"


def test_other_has_no_keywords() -> None:
    """Other is the fallback only — it has no keywords."""
    assert TOPIC_KEYWORDS["Other"] == []
    assert len(TOPIC_KEYWORDS) == 10


def test_attention_share_sums_to_100_per_outlet() -> None:
    """Attention shares sum to 100% per outlet (and corpus-wide).

    Outlets with no articles in the window sum to 0% — they have no
    share to distribute.
    """
    attention = _attention()
    for outlet, group in attention.groupby("outlet"):
        total = float(group["attention_share_pct"].sum())
        outlet_total = int(group["outlet_total"].iloc[0])
        if outlet_total > 0:
            assert total == pytest.approx(100.0, abs=0.01), outlet
        else:
            assert total == 0.0, outlet


def test_attention_share_zero_total() -> None:
    """A zero-total outlet has a 0.0 share, not a division error."""
    assert attention_share(0, 0) == 0.0
    assert attention_share(5, 0) == 0.0
    assert attention_share(19, 31) == pytest.approx(61.2903, abs=0.0001)


def test_wilson_ci_contains_share() -> None:
    """The Wilson interval contains the share and stays in [0, 100]."""
    low, high = wilson_ci(19, 31)
    assert low <= 61.2903 <= high
    assert 0.0 <= low < high <= 100.0
    low0, high0 = wilson_ci(0, 10)
    assert low0 == 0.0 and high0 > 0.0


def test_wilson_ci_known_value() -> None:
    """Wilson CI for the largest cell matches the hand computation."""
    low, high = wilson_ci(19, 31)
    assert low == pytest.approx(43.8238, abs=0.01)
    assert high == pytest.approx(76.2671, abs=0.01)


def test_wilson_ci_zero_total_handled() -> None:
    """wilson_ci(0, 0) returns (0.0, 0.0)."""
    assert wilson_ci(0, 0) == (0.0, 0.0)


# --- sentiment --------------------------------------------------------


def test_vader_label_thresholds() -> None:
    """Standard VADER thresholds: +0.05 / -0.05 boundaries."""
    assert sentiment_label(0.05) == "positive"
    assert sentiment_label(-0.05) == "negative"
    assert sentiment_label(0.049) == "neutral"
    assert sentiment_label(-0.049) == "neutral"
    assert sentiment_label(0.0) == "neutral"
    assert sentiment_label(0.9) == "positive"
    assert sentiment_label(-0.9) == "negative"


def test_compound_in_range() -> None:
    """Every committed compound is in [-1, +1]."""
    articles = _articles()
    assert articles["vader_compound"].between(-1.0, 1.0).all()
    assert articles["sentiment_label"].isin(["positive", "neutral", "negative"]).all()


def test_compound_score_matches_direct_vader() -> None:
    """Pipeline VADER matches a direct vaderSentiment call to 3 decimals."""
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    analyser = SentimentIntensityAnalyzer()
    for text in [
        "Markets rise as inflation cools",
        "Cartel leader captured in a bloody firefight that left 11 dead",
        "Miley Cyrus marries Maxx Morando in California ceremony",
    ]:
        direct = float(analyser.polarity_scores(text)["compound"])
        assert round(compound_score(text), 3) == round(direct, 3)


def test_summarise_ci_method_rules() -> None:
    """t-interval for symmetric data, bootstrap when |skew| > 1."""
    rng = np.random.default_rng(3)
    symmetric = pd.Series(rng.normal(0, 0.3, 50))
    assert summarise(symmetric)["ci_method"] == "t-interval"
    skewed = pd.Series(np.concatenate([rng.normal(0, 0.1, 45), [0.9, 0.95, 0.99]]))
    assert summarise(skewed)["ci_method"] == "bootstrap (1000 resamples, seed 42)"
    empty = summarise(pd.Series([], dtype=float))
    assert empty["ci_method"] == "n/a (no articles)"
    assert empty["n"] == 0


def test_bootstrap_ci_contains_mean_and_is_deterministic() -> None:
    """Bootstrap CI contains the mean and repeats with the same seed."""
    values = pd.Series([0.1, -0.2, 0.3, 0.0, 0.5, -0.4, 0.2])
    low, high = bootstrap_ci(values)
    assert low <= float(values.mean()) <= high
    assert bootstrap_ci(values) == bootstrap_ci(values)


# --- dictionary byte-identity -----------------------------------------


def test_dictionary_byte_identical_to_readme() -> None:
    """The dictionary printed in the README is byte-identical to the code."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```python\n(.*?)```", readme, re.DOTALL)
    dict_blocks = [b for b in blocks if b.strip().startswith("{'Economy'")]
    assert len(dict_blocks) == 1
    block = dict_blocks[0].strip()
    assert block == pprint.pformat(TOPIC_KEYWORDS, sort_dicts=False)
    assert ast.literal_eval(block) == TOPIC_KEYWORDS


# --- corpus integrity --------------------------------------------------


def test_corpus_pub_dates_in_window() -> None:
    """Every stored article's pub_date is inside 2026-11-08–2026-11-22."""
    articles = _articles()
    dates = pd.to_datetime(articles["pub_date"], utc=True).dt.date
    assert (
        (dates >= pd.to_datetime("2026-11-08").date())
        & (dates <= pd.to_datetime("2026-11-22").date())
    ).all()


def test_corpus_urls_unique() -> None:
    """No duplicate URLs in the corpus."""
    assert _articles()["link"].is_unique


def test_per_outlet_counts_sum_to_total() -> None:
    """Per-outlet counts sum to the corpus total (75)."""
    articles = _articles()
    assert len(articles) == 75
    assert articles.groupby("outlet").size().sum() == 75
    record = json.loads((PROC / "data_source.json").read_text(encoding="utf-8"))
    assert record["corpus_total"] == 75
    assert sum(record["per_outlet_n"].values()) == 75


def test_exactly_one_topic_per_article() -> None:
    """Every article has exactly one topic assigned (including Other)."""
    articles = _articles()
    assert articles["topic"].notna().all()
    assert (articles["topic"] != "").all()
    assert set(articles["topic"]).issubset(set(TOPICS))


# --- window filter + dedupe (crafted feed fixture) ----------------------


_CRAFTED_FEED = """<rss version="2.0"><channel><title>Test</title>
<item><title>Markets rise</title><description>Economy news</description>
<link>https://example.com/a</link><pubDate>Sun, 15 Nov 2026 12:00:00 GMT</pubDate><guid>a</guid></item>
<item><title>Old news</title><description>Old economy</description>
<link>https://example.com/b</link><pubDate>Sun, 01 Nov 2026 12:00:00 GMT</pubDate><guid>b</guid></item>
<item><title>Future news</title><description>Future economy</description>
<link>https://example.com/c</link><pubDate>Wed, 25 Nov 2026 12:00:00 GMT</pubDate><guid>c</guid></item>
<item><title>Markets rise again</title><description>Economy news</description>
<link>https://example.com/a</link><pubDate>Mon, 16 Nov 2026 12:00:00 GMT</pubDate><guid>a</guid></item>
<item><title>No date news</title><description>Economy news</description>
<link>https://example.com/e</link><guid>e</guid></item>
</channel></rss>"""
_EMPTY_FEED = '<rss version="2.0"><channel><title>Empty</title></channel></rss>'


def test_window_filter_drops_out_of_window_items(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Items outside 2026-11-08–2026-11-22 are dropped and counted."""
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "nyt_rss.xml").write_text(_CRAFTED_FEED, encoding="utf-8")
    for stem in ["wsj", "fox", "cnn", "npr", "bbc"]:
        (raw / f"{stem}_rss.xml").write_text(_EMPTY_FEED, encoding="utf-8")
    monkeypatch.setattr(data_pipeline, "RAW_DIR", raw)
    _, counts = collect_corpus(data_pipeline.OUTLETS)
    assert counts["NYT"]["fetched_items"] == 5
    assert counts["NYT"]["dropped_missing_link_or_date"] == 1
    assert counts["NYT"]["dropped_outside_window"] == 2
    assert counts["NYT"]["final_n"] == 1


def test_dedupe_by_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A repeated URL is kept once; the duplicate is counted."""
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "nyt_rss.xml").write_text(_CRAFTED_FEED, encoding="utf-8")
    for stem in ["wsj", "fox", "cnn", "npr", "bbc"]:
        (raw / f"{stem}_rss.xml").write_text(_EMPTY_FEED, encoding="utf-8")
    monkeypatch.setattr(data_pipeline, "RAW_DIR", raw)
    articles, counts = collect_corpus(data_pipeline.OUTLETS)
    assert counts["NYT"]["duplicates_removed"] == 1
    assert len(articles) == 1
    assert articles.iloc[0]["topic"] == "Economy"


# --- guardrail ----------------------------------------------------------


def test_guardrail_sentence_on_all_four_surfaces() -> None:
    """The guardrail sentence appears in README, insights, notebook, app."""
    assert GUARDRAIL_SENTENCE in (ROOT / "README.md").read_text(encoding="utf-8")
    assert GUARDRAIL_SENTENCE in (ROOT / "outputs" / "insights_summary.md").read_text(
        encoding="utf-8"
    )
    assert GUARDRAIL_SENTENCE in (ROOT / "notebooks" / "analysis.ipynb").read_text(
        encoding="utf-8"
    )
    assert GUARDRAIL_SENTENCE in (ROOT / "src" / "app.py").read_text(encoding="utf-8")


def _call_string_literals(source: str, func_names: list[str]) -> list[str]:
    """String literals passed to the named calls in a source file."""
    tree = ast.parse(source)
    literals: list[str] = []
    wanted = set(func_names)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in wanted
            and node.args
        ):
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                literals.append(first.value)
            elif isinstance(first, ast.JoinedStr):
                # f-string title: check the literal parts (the interpolated
                # window label is a constant defined elsewhere in the file).
                parts = "".join(
                    part.value
                    for part in first.values
                    if isinstance(part, ast.Constant) and isinstance(part.value, str)
                )
                literals.append(parts)
    return literals


def test_no_forbidden_words_in_chart_titles_and_dashboard_headings() -> None:
    """No forbidden word in chart titles / axis labels / dashboard headings.

    The guardrail sentence itself ("... not ... political bias") is
    excluded: it negates bias rather than attributing it, and the plan
    requires its short form in chart footnotes.
    """
    charts_source = (ROOT / "src" / "make_charts.py").read_text(encoding="utf-8")
    titles = _call_string_literals(charts_source, ["set_title", "suptitle"])
    assert titles, "no chart titles found to check"
    for title in titles:
        assert FORBIDDEN.search(title) is None, title
    app_source = (ROOT / "src" / "app.py").read_text(encoding="utf-8")
    headings = _call_string_literals(
        app_source, ["title", "header", "subheader", "caption"]
    )
    assert headings, "no dashboard headings found to check"
    for heading in headings:
        cleaned = heading.replace(GUARDRAIL_SENTENCE, "")
        assert FORBIDDEN.search(cleaned) is None, heading


def test_same_columns_for_all_outlets() -> None:
    """Every committed table carries the same columns for all six outlets."""
    attention = _attention()
    for outlet in OUTLETS:
        assert set(attention[attention["outlet"] == outlet]["topic"]) == set(TOPICS)
    by_outlet = pd.read_csv(PROC / "sentiment_by_outlet.csv")
    assert list(by_outlet["outlet"]) == OUTLETS
    assert list(by_outlet.columns) == [
        "outlet",
        "n",
        "mean_compound",
        "ci_low",
        "ci_high",
        "ci_method",
        "median_compound",
        "pct_positive",
        "pct_neutral",
        "pct_negative",
    ]
    assert set(_articles()["outlet"]) <= set(OUTLETS)


def test_sentiment_by_topic_small_n_flag() -> None:
    """Groups with n < 5 are flagged small_n in sentiment_by_topic.csv."""
    by_topic = pd.read_csv(PROC / "sentiment_by_topic.csv")
    assert ((by_topic["n"] < 5) == by_topic["small_n"].astype(bool)).all()
    assert (by_topic["n"] >= 1).all()


# --- statistics ---------------------------------------------------------


def test_chi_square_sparse_cell_rule() -> None:
    """An expected cell < 5 triggers collapse, then the permutation path."""
    table = pd.DataFrame(
        [
            [10, 0, 0, 0, 0, 0, 0, 0, 0, 1],
            [0, 9, 0, 0, 0, 0, 0, 0, 0, 2],
            [0, 0, 8, 0, 0, 0, 0, 0, 0, 3],
            [0, 0, 0, 7, 0, 0, 0, 0, 0, 4],
        ],
        index=["A", "B", "C", "D"],
        columns=[f"T{i}" for i in range(10)],
    )
    result = chi_square_topic_outlet(table)
    assert result["sparse"] is True
    assert result["collapsed"] is True
    perm_p = result["permutation_p_value"]
    assert perm_p is not None
    assert isinstance(perm_p, float)
    assert 0.0 <= perm_p <= 1.0
    assert "permutation p-value" in str(result["conclusion_basis"])


def test_chi_square_dense_table_no_collapse() -> None:
    """A dense table runs plain chi-square with no collapse or permutation."""
    table = pd.DataFrame(
        [
            [20, 18, 22, 19, 21, 20, 19, 18, 20, 21],
            [19, 21, 20, 18, 20, 22, 21, 19, 20, 18],
            [21, 20, 19, 21, 18, 19, 20, 21, 19, 20],
        ],
        index=["A", "B", "C"],
        columns=[f"T{i}" for i in range(10)],
    )
    result = chi_square_topic_outlet(table)
    assert result["sparse"] is False
    assert result["collapsed"] is False
    assert result["permutation_p_value"] is None


def test_permutation_pvalue_range_and_deterministic() -> None:
    """Permutation p-value is in [0, 1] and repeats with the same seed."""
    table = pd.DataFrame(
        [[10, 5], [4, 9], [7, 6]], index=["A", "B", "C"], columns=["X", "Y"]
    )
    first = permutation_pvalue(table, n_permutations=1000, seed=42)
    assert 0.0 <= first <= 1.0
    assert permutation_pvalue(table, n_permutations=1000, seed=42) == first


def test_sentiment_test_selection_follows_shapiro_rule() -> None:
    """ANOVA when every outlet passes Shapiro-Wilk; else Kruskal-Wallis."""
    rng = np.random.default_rng(0)
    normal_df = pd.DataFrame(
        {
            "outlet": ["A"] * 30 + ["B"] * 30,
            "vader_compound": list(rng.normal(0, 0.3, 30))
            + list(rng.normal(0.1, 0.3, 30)),
        }
    )
    assert sentiment_test_by_outlet(normal_df)["test"] == "one-way ANOVA"
    rng = np.random.default_rng(7)
    skewed_df = pd.DataFrame(
        {
            "outlet": ["A"] * 30 + ["B"] * 30,
            "vader_compound": list(rng.normal(0, 0.3, 30))
            + list(rng.exponential(0.3, 30) - 0.5),
        }
    )
    assert sentiment_test_by_outlet(skewed_df)["test"] == "Kruskal-Wallis"


def test_pairwise_tests_carry_a_correction() -> None:
    """Pairwise tests report corrected p-values only — never uncorrected."""
    rng = np.random.default_rng(7)
    df = pd.DataFrame(
        {
            "outlet": ["A"] * 30 + ["B"] * 30,
            "vader_compound": list(rng.normal(0, 0.3, 30))
            + list(rng.exponential(0.3, 30) - 0.5),
        }
    )
    dunn = pairwise_tests(df, "dunn")
    assert bool(dunn["corrected"].all())
    assert "Bonferroni" in str(dunn["method"].iloc[0])
    assert ((dunn["p_value"] >= 0) & (dunn["p_value"] <= 1)).all()
    rng = np.random.default_rng(0)
    normal_df = pd.DataFrame(
        {
            "outlet": ["A"] * 30 + ["B"] * 30,
            "vader_compound": list(rng.normal(0, 0.3, 30))
            + list(rng.normal(0.1, 0.3, 30)),
        }
    )
    tukey = pairwise_tests(normal_df, "tukey")
    assert bool(tukey["corrected"].all())
    assert "Tukey HSD" in str(tukey["method"].iloc[0])
    with pytest.raises(ValueError):
        pairwise_tests(normal_df, "uncorrected")


def test_committed_stats_match_plan_rules() -> None:
    """The committed stats rest the chi-square conclusion on permutation."""
    stats = json.loads((PROC / "stats_results.json").read_text(encoding="utf-8"))
    chi = stats["chi_square_topic_outlet"]
    assert chi["sparse"] is True
    assert chi["permutation_p_value"] is not None
    assert chi["excluded_outlets"] == ["WSJ", "CNN"]
    assert stats["sentiment_by_outlet"]["test"] == "Kruskal-Wallis"
    assert all(record["corrected"] for record in stats["pairwise_tests"])


# --- sample review ------------------------------------------------------


def test_sample_review_stratified_seed_42() -> None:
    """Sample is 5 per outlet with articles, reproducible with seed 42."""
    sample = pd.read_csv(PROC / "sample_review.csv")
    assert len(sample) == 20  # 5 each from NYT, Fox News, NPR, BBC News
    counts = sample.groupby("outlet").size().to_dict()
    assert counts == {
        "NYT": 5,
        "Fox News": 5,
        "NPR": 5,
        "BBC News": 5,
    }
    assert set(sample["assigned_topic"]).issubset(set(TOPICS))
    rebuilt = build_sample_review(_articles())
    assert list(rebuilt["link"]) == list(sample["link"])


def test_gdelt_skipped_not_a_fallback_trigger() -> None:
    """GDELT is recorded as skipped; RSS alone is the complete build."""
    gdelt = gdelt_cross_check()
    assert gdelt["attempted"] is False
    assert gdelt["status"] == "skipped"
    record = json.loads((PROC / "data_source.json").read_text(encoding="utf-8"))
    assert record["gdelt"]["attempted"] is False
    assert record["synthetic"] is False


# --- offline / synthetic / size rules -----------------------------------


def test_offline_run_does_not_clobber_data_source() -> None:
    """--offline skips writing data_source.json when a live record exists."""
    path = PROC / "data_source.json"
    before = path.read_bytes()
    before_hash = hashlib.sha256(before).hexdigest()
    run_pipeline("offline")
    after_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    assert before_hash == after_hash


def test_offline_reproduction_uses_tolerance() -> None:
    """Offline-regenerated shares match the committed ones within 0.01 pp."""
    before = pd.read_csv(PROC / "topic_attention.csv")
    run_pipeline("offline")
    after = pd.read_csv(PROC / "topic_attention.csv")
    merged = before.merge(after, on=["outlet", "topic"], suffixes=("_before", "_after"))
    assert len(merged) == len(before)
    diff = (
        merged["attention_share_pct_before"] - merged["attention_share_pct_after"]
    ).abs()
    assert (diff <= 0.01).all()
    articles_before = pd.read_csv(PROC / "articles.csv")
    assert len(articles_before) == 75


def test_synthetic_files_never_overwrite_live_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Synthetic generation writes only *_synthetic.json, never real data."""
    raw = tmp_path / "raw"
    raw.mkdir()
    monkeypatch.setattr(data_pipeline, "RAW_DIR", raw)
    frame = build_synthetic_corpus()
    assert len(frame) == 147
    assert set(frame["outlet"]) == set(OUTLETS)
    written = sorted(p.name for p in raw.iterdir())
    assert written == ["synthetic_corpus_synthetic.json"]
    assert not any(name.endswith("_rss.xml") for name in written)
    dates = pd.to_datetime(frame["pub_date"], utc=True).dt.date
    assert (
        (dates >= pd.to_datetime("2026-11-08").date())
        & (dates <= pd.to_datetime("2026-11-22").date())
    ).all()


def test_no_committed_file_over_1mb_data_under_5mb() -> None:
    """No committed file over 1 MB; data/ under 5 MB (plan §3.4)."""
    excluded = {".venv", "__pycache__", ".mypy_cache", ".pytest_cache", ".git"}
    big: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in excluded for part in path.parts):
            continue
        if path.stat().st_size > 1_000_000:
            big.append(str(path.relative_to(ROOT)))
    assert big == [], big
    total = sum(p.stat().st_size for p in (ROOT / "data").rglob("*") if p.is_file())
    assert total < 5_000_000, total


def test_gitignore_excludes_synthetic_but_not_raw_xml() -> None:
    """.gitignore excludes synthetic output while the six raw XMLs are kept."""
    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    patterns = [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]
    assert "data/raw/*_synthetic.json" in patterns
    assert not any(p in ("data/", "data", "data/*", "data/raw/") for p in patterns)
    for stem in ["nyt", "wsj", "fox", "cnn", "npr", "bbc"]:
        rel = f"data/raw/{stem}_rss.xml"
        matched = [p for p in patterns if fnmatch.fnmatch(rel, p)]
        assert matched == [], (rel, matched)
