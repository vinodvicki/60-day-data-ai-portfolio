"""Language-sentiment helpers (Day 15) — VADER, frozen lexicon.

Sentiment here is the emotional tone of the words used. It is not a
measure of factual accuracy, fairness, or political bias. VADER
(``vaderSentiment``) is a general-purpose social-media lexicon; it was
not built for news text, and that limitation is stated wherever a
sentiment number is shown. No other sentiment model is used; no model
is trained.

VADER runs on the original-cased ``title + " " + description`` text
(VADER uses capitalisation and punctuation as signals — do not
lowercase before scoring). Standard VADER thresholds: compound
>= +0.05 is positive, <= -0.05 is negative, otherwise neutral.
"""

from __future__ import annotations

import pandas as pd
from scipy import stats as scipy_stats
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

try:
    from src.stats import bootstrap_ci
except ImportError:  # pragma: no cover - running as a script from src/
    from stats import bootstrap_ci  # type: ignore[no-redef]

from typing import TypedDict

POSITIVE_THRESHOLD: float = 0.05
NEGATIVE_THRESHOLD: float = -0.05


class SentimentSummary(TypedDict):
    """Typed summary of a group of VADER compound scores."""

    n: int
    mean_compound: float | None
    ci_low: float | None
    ci_high: float | None
    ci_method: str
    median_compound: float | None
    pct_positive: float
    pct_neutral: float
    pct_negative: float


_ANALYZER = SentimentIntensityAnalyzer()


def compound_score(text: str) -> float:
    """VADER compound score for ``text`` (in [-1, +1])."""
    if not text or not text.strip():
        return 0.0
    return float(_ANALYZER.polarity_scores(text)["compound"])


def sentiment_label(compound: float) -> str:
    """Standard VADER label: positive / neutral / negative."""
    if compound >= POSITIVE_THRESHOLD:
        return "positive"
    if compound <= NEGATIVE_THRESHOLD:
        return "negative"
    return "neutral"


def summarise(scores: pd.Series) -> SentimentSummary:
    """Summarise a group of VADER compound scores.

    Mean with a 95% CI (t-interval by default; bootstrap with 1,000
    resamples, seed 42, when |skew| > 1), median, and the %
    positive / neutral / negative. The ``ci_method`` value states
    which interval was used.
    """
    values = pd.to_numeric(scores, errors="coerce").dropna()
    n = len(values)
    if n == 0:
        return {
            "n": 0,
            "mean_compound": None,
            "ci_low": None,
            "ci_high": None,
            "ci_method": "n/a (no articles)",
            "median_compound": None,
            "pct_positive": 0.0,
            "pct_neutral": 0.0,
            "pct_negative": 0.0,
        }
    mean = float(values.mean())
    median = float(values.median())
    labels = values.map(sentiment_label)
    pct_positive = float((labels == "positive").mean() * 100.0)
    pct_neutral = float((labels == "neutral").mean() * 100.0)
    pct_negative = float((labels == "negative").mean() * 100.0)
    if n == 1:
        ci_low, ci_high = mean, mean
        ci_method = "n=1 (no interval)"
    else:
        skew = float(scipy_stats.skew(values.to_numpy(dtype=float)))
        if abs(skew) > 1.0:
            ci_low, ci_high = bootstrap_ci(values)
            ci_method = "bootstrap (1000 resamples, seed 42)"
        else:
            sem = float(scipy_stats.sem(values.to_numpy(dtype=float)))
            ci_low, ci_high = scipy_stats.t.interval(
                0.95, df=n - 1, loc=mean, scale=sem
            )
            ci_low, ci_high = float(ci_low), float(ci_high)
            ci_method = "t-interval"
    # Compound scores live in [-1, +1]; clip the interval to that range.
    ci_low = max(-1.0, ci_low)
    ci_high = min(1.0, ci_high)
    return {
        "n": n,
        "mean_compound": mean,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "ci_method": ci_method,
        "median_compound": median,
        "pct_positive": pct_positive,
        "pct_neutral": pct_neutral,
        "pct_negative": pct_negative,
    }
