"""Streamlit dashboard for Day 15 — Political News Coverage Analyzer.

Loads processed CSVs + data_source.json only (offline). Every surface
states the coverage limits: descriptive only (no predictive model),
title + description text only, VADER is a general-purpose lexicon not
built for news text, keyword topic matching is crude, and the RSS
feeds are rolling latest-N lists so the window actually achieved per
outlet may be shorter than 14 days. Sentiment is language tone only.
"""

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
CHARTS = ROOT / "outputs" / "charts"

GUARDRAIL_SENTENCE = "Sentiment measures the emotional tone of the words used; it is not a measure of factual accuracy, fairness, or political bias."
LIMITS_BANNER = (
    "Descriptive only — no predictive model, no causal claims. "
    "Title + description text only — no full article text. VADER is a "
    "general-purpose social-media lexicon, not built for news text. "
    "Keyword topic matching is crude; see the sample review. RSS feeds "
    "are rolling latest-N lists, so the window actually achieved per "
    "outlet may be shorter than 14 days."
)
ZERO_OUTLET_NOTE = (
    "WSJ and CNN returned no usable articles in the window "
    "2026-11-08–2026-11-22 (their feeds served older items), so they "
    "appear with n=0 in every table and chart. They are not dropped."
)
FEED_LINKS = {
    "NYT": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "WSJ": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    "Fox News": "https://moxie.foxnews.com/google-publisher/latest.xml",
    "CNN": "http://rss.cnn.com/rss/edition.rss",
    "NPR": "https://feeds.npr.org/1001/rss.xml",
    "BBC News": "https://feeds.bbci.co.uk/news/rss.xml",
}
SITE_LINKS = {
    "NYT": "https://www.nytimes.com/",
    "WSJ": "https://www.wsj.com/",
    "Fox News": "https://www.foxnews.com/",
    "CNN": "https://www.cnn.com/",
    "NPR": "https://www.npr.org/",
    "BBC News": "https://www.bbc.com/news",
}


@st.cache_data
def load_data() -> dict[str, Any]:
    """Load the processed tables and the provenance record (offline)."""
    record = json.loads((PROC / "data_source.json").read_text(encoding="utf-8"))
    stats = json.loads((PROC / "stats_results.json").read_text(encoding="utf-8"))
    return {
        "record": record,
        "stats": stats,
        "articles": pd.read_csv(PROC / "articles.csv"),
        "attention": pd.read_csv(PROC / "topic_attention.csv"),
        "by_outlet": pd.read_csv(PROC / "sentiment_by_outlet.csv"),
        "by_topic": pd.read_csv(PROC / "sentiment_by_topic.csv"),
        "sample": pd.read_csv(PROC / "sample_review.csv"),
    }


def _fmt(x: float | None, digits: int = 3) -> str:
    """Format a number or '—' when missing."""
    if x is None or pd.isna(x):
        return "—"
    return f"{float(x):.{digits}f}"


def _agree_bool(value: object) -> bool:
    """Normalise a sample-review ``agree`` cell to a bool."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "y")


def main() -> None:
    """Render the dashboard."""
    st.set_page_config(page_title="Political News Coverage Analyzer", layout="wide")
    data = load_data()
    record = data["record"]
    stats = data["stats"]
    articles = data["articles"]
    attention = data["attention"]
    by_outlet = data["by_outlet"]
    by_topic = data["by_topic"]
    sample = data["sample"]

    st.title("Political News Coverage Analyzer — six outlets, 2026-11-08–2026-11-22")
    st.caption(
        "Topics, attention and language sentiment across an explicitly defined "
        "corpus: NYT, WSJ, Fox News, CNN, NPR and BBC News RSS feeds, "
        "title + description text only, 2026-11-08–2026-11-22. "
        "Source: outlet RSS feeds (links in the methods section)."
    )
    st.info(GUARDRAIL_SENTENCE)
    st.warning(LIMITS_BANNER)
    st.warning(ZERO_OUTLET_NOTE)

    total = len(articles)
    n_with_articles = int((by_outlet["n"] > 0).sum())
    topics_covered = int(
        (attention[attention["outlet"] == "ALL"]["n_articles"] > 0).sum()
    )
    top_cell = (
        attention[attention["outlet"] != "ALL"]
        .sort_values("attention_share_pct", ascending=False)
        .iloc[0]
    )
    reviewed = sample[
        sample["reviewer_topic"].notna() & (sample["reviewer_topic"] != "")
    ]
    if len(reviewed) > 0:
        n_agree = int(reviewed["agree"].map(_agree_bool).sum())
        agreement = f"{n_agree / len(reviewed) * 100:.1f}%"
    else:
        n_agree = 0
        agreement = "Pending"

    st.subheader("Headline figures")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Articles in corpus", str(total))
    col2.metric("Outlets with articles", f"{n_with_articles} of 6")
    col3.metric("Topics covered", str(topics_covered))
    col4.metric(
        "Largest attention share",
        f"{float(top_cell['attention_share_pct']):.1f}%",
        delta=f"{top_cell['outlet']} — {top_cell['topic']} "
        f"(n={int(top_cell['n_articles'])})",
    )
    col5.metric("Sample-review agreement", agreement)

    st.subheader("Attention share by topic and outlet")
    st.image(str(CHARTS / "01_attention_share_by_topic.png"), width="stretch")
    st.caption(
        "Within-outlet share of each outlet's corpus, with N per topic. "
        "Source: outlet RSS feeds; title + description text only; "
        "window 2026-11-08–2026-11-22."
    )
    st.dataframe(
        attention[attention["outlet"] != "ALL"][
            [
                "outlet",
                "topic",
                "n_articles",
                "attention_share_pct",
                "wilson_ci_low",
                "wilson_ci_high",
                "outlet_total",
            ]
        ],
        width="stretch",
    )
    st.caption(
        "Attention share = articles(outlet, topic) ÷ articles(outlet, all "
        "topics) × 100, with a Wilson 95% CI. Every share is shown with "
        "its N beside it."
    )

    st.subheader("Mean language sentiment by outlet")
    st.image(str(CHARTS / "02_mean_sentiment_by_outlet.png"), width="stretch")
    st.caption(
        "Mean VADER compound with 95% CI, title + description text only. "
        "Dashed lines mark the VADER thresholds (±0.05). "
        "Source: outlet RSS feeds; VADER vaderSentiment "
        f"{record['vader_version']}."
    )
    st.dataframe(by_outlet, width="stretch")
    st.caption(
        "Mean compound with 95% CI (t-interval, or bootstrap with 1,000 "
        "resamples when |skew| > 1; see ci_method), median, and the % of "
        "articles with positive / neutral / negative language. "
        "VADER was not built for news text."
    )

    st.subheader("Mean language sentiment by topic and outlet")
    st.image(str(CHARTS / "03_sentiment_by_topic_heatmap.png"), width="stretch")
    st.caption(
        "Cell = mean VADER compound, annotated with the value and N. "
        "Cells with n < 5 are hatched and labelled 'small n'. "
        "Source: outlet RSS feeds; title + description text only."
    )

    st.subheader("Share of articles by language-sentiment label and outlet")
    st.image(str(CHARTS / "04_sentiment_distribution.png"), width="stretch")
    st.caption(
        "% of each outlet's articles with positive / neutral / negative "
        "language (VADER thresholds ±0.05). Source: outlet RSS feeds."
    )
    st.dataframe(
        by_topic[
            [
                "outlet",
                "topic",
                "n",
                "mean_compound",
                "ci_low",
                "ci_high",
                "median_compound",
                "pct_positive",
                "pct_neutral",
                "pct_negative",
                "small_n",
            ]
        ],
        width="stretch",
    )

    st.subheader("Statistical tests")
    chi = stats["chi_square_topic_outlet"]
    st.markdown(
        f"**Topic × outlet (chi-square):** χ² = {_fmt(chi['chi2'], 2)}, "
        f"df = {chi['df']}, asymptotic p = {_fmt(chi['p_value'], 3)}. "
        f"Minimum expected cell count {_fmt(chi['min_expected'], 2)} — "
        "below 5, so the sparse-cell rule applied: collapsed to the 4 "
        "largest topics + All other topics "
        f"(χ² = {_fmt(chi['collapsed_chi2'], 2)}, "
        f"p = {_fmt(chi['collapsed_p_value'], 3)}), still sparse, so the "
        "conclusion rests on the permutation p-value "
        f"(10,000 shuffles, seed 42): p = {_fmt(chi['permutation_p_value'], 3)}. "
        f"Outlets excluded from the test (no articles in the window): "
        f"{', '.join(str(o) for o in chi['excluded_outlets'])}."
    )
    sent = stats["sentiment_by_outlet"]
    st.markdown(
        f"**Language sentiment by outlet ({sent['test']}):** statistic = "
        f"{_fmt(sent['statistic'], 2)}, p = {_fmt(sent['p_value'], 3)}. "
        f"Why this test: {sent['why']}."
    )
    pairwise = pd.DataFrame(stats["pairwise_tests"])
    if not pairwise.empty:
        st.markdown(
            "**Pairwise outlet differences** (Mann-Whitney U with Bonferroni "
            "correction — corrected p-values only):"
        )
        st.dataframe(pairwise, width="stretch")
    st.markdown(
        "**Language sentiment by topic within each outlet:** tested only "
        "where at least 2 topics had n ≥ 5. Fox News: one-way ANOVA, "
        f"F = {_fmt(stats['sentiment_by_topic_within_outlet']['Fox News'].get('statistic'), 2)}, "
        f"p = {_fmt(stats['sentiment_by_topic_within_outlet']['Fox News'].get('p_value'), 3)} "
        "(topics: Other, Technology & AI). BBC News: one-way ANOVA, "
        f"F = {_fmt(stats['sentiment_by_topic_within_outlet']['BBC News'].get('statistic'), 2)}, "
        f"p = {_fmt(stats['sentiment_by_topic_within_outlet']['BBC News'].get('p_value'), 3)} "
        "(topics: Other, Technology & AI). No other outlet had 2 topics "
        "with n ≥ 5."
    )
    st.caption(
        "A significant result would mean only that the distribution of "
        "topics, or the average language tone, differs across outlets in "
        "this corpus and window."
    )

    st.subheader("Sample review — 30-article design, 20 drawn")
    st.markdown(
        "Stratified sample, 5 articles per outlet with articles in the "
        "window, seed 42. WSJ and CNN had no articles to sample, so the "
        "drawn sample is 20 articles (5 each from NYT, Fox News, NPR and "
        "BBC News). The reviewer reads each title + description and records "
        "the topic a human reader would assign; the agreement rate is "
        "reported next to every topic finding once the review is complete."
    )
    st.dataframe(sample, width="stretch")
    if len(reviewed) > 0:
        st.markdown(
            f"**Agreement rate:** {agreement} "
            f"({n_agree} of {len(reviewed)} "
            "reviewed articles)."
        )
    else:
        st.markdown(
            "**Agreement rate:** pending — the tester completes the "
            "`reviewer_topic` column in `data/processed/sample_review.csv`."
        )

    st.subheader("Methods and limitations")
    st.markdown(
        "- **Corpus:** six outlet RSS feeds, one GET per feed on "
        "2026-11-22, parsed with feedparser; raw XML stored in "
        "`data/raw/`. Window 2026-11-08–2026-11-22 inclusive, enforced "
        "on `pubDate`; items outside the window dropped and counted; "
        "deduplicated by URL.\n"
        "- **Coverage actually achieved:** NYT 2026-11-20–2026-11-22 "
        "(n=10); Fox News 2026-11-22 (n=24); NPR 2026-11-21–2026-11-22 "
        "(n=10); BBC News 2026-11-11–2026-11-22 (n=31); WSJ and CNN "
        "n=0 — their feeds served older items (WSJ 20 items dated January "
        "2025, CNN 46 items dated April 2023 plus 4 with no parseable "
        "date), all dropped by the window filter. "
        "No outlet is claimed to cover the full 14 days unless its "
        "earliest `pubDate` reaches back that far.\n"
        "- **Topics:** frozen 10-topic keyword dictionary (see README); "
        "most hits wins, ties go to the earliest keyword in the text, "
        "zero hits means Other. Keyword matching is crude — a headline "
        "can mention a word without being about that topic.\n"
        "- **Sentiment:** VADER compound on title + description "
        "(original-cased text); thresholds ±0.05. VADER is a "
        "general-purpose social-media lexicon, not built for news text.\n"
        "- **Statistics:** chi-square with the sparse-cell rule "
        "(collapse, then permutation p-value); Shapiro-Wilk normality "
        "gate picks ANOVA or Kruskal-Wallis; pairwise tests only with "
        "a stated correction. Every share carries a Wilson 95% CI; "
        "every mean carries a 95% CI.\n"
        "- **Descriptive only:** no predictive model, no fact-checking, "
        "no causal claims. GDELT was not used (optional cross-check "
        "only; the researcher verified it rate-limits).\n"
        "- **Sample review:** 5 articles per outlet with articles, "
        "seed 42, fixed once drawn; the dictionary is not tuned after "
        "seeing the agreement rate."
    )
    st.markdown("**Feed URLs**")
    for outlet, url in FEED_LINKS.items():
        st.markdown(
            f"- {outlet}: [{url}]({url}) — site: [{SITE_LINKS[outlet]}]({SITE_LINKS[outlet]})"
        )

    st.markdown("---")
    st.caption(
        "Attribution: headlines, descriptions and links only — no full "
        "article text republished. Outlet content is the outlets' own. "
        "VADER (`vaderSentiment`) is MIT-licensed. "
        "Source: outlet RSS feeds; VADER vaderSentiment "
        f"{record['vader_version']}; fetched {record['fetch_date']}."
    )


if __name__ == "__main__":
    main()
