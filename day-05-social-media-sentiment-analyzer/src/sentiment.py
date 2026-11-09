"""Rule-based sentiment scorer + theme classifier for Day 5.

An original, transparent lexicon model written for this project — it is
VADER-*style* in shape only (a word-polarity sum with negation and
intensifier handling, normalised to [-1, +1]). The lexicon below was
authored for this project; it is NOT the VADER lexicon, no NLTK download,
no pretrained model, no paid API, no copied code. Every word, weight and
rule lives in this one file so any reader can audit the full model.

Rules (fixed by research_brief.md §3.1 / plan.md §4.1 — do not re-tune):
  * each lexicon word scores +1 / -1; the STRONG words score +/-2.
  * negation words flip the polarity of the next 3 *scored* words.
  * intensifiers multiply the next scored word by 1.5.
  * a small explicit emoji map adds at most +/-2 per comment.
  * +0.25 per '!' (capped at +0.5), only when the raw sum is positive.
  * compound = s / sqrt(s**2 + 15); class thresholds are +/-0.05.
  * the lexicon was authored BEFORE seeing the comments and must NOT be
    tuned after seeing validation results (that would invalidate the
    measurement — a missing word is reported as a limitation, not added).
"""

from __future__ import annotations

import itertools
import math
import re
import unicodedata
from collections import Counter

# ---------------------------------------------------------------------------
# Lexicon (authored for this project, 2026-11-09, before seeing any comment)
# ---------------------------------------------------------------------------

#: Strong positive words score +2; every other positive word scores +1.
STRONG_POSITIVE = {
    "love",
    "amazing",
    "brilliant",
    "excellent",
    "fantastic",
    "perfect",
}

#: Positive words scoring +1.
POSITIVE_WORDS = {
    "amazing",
    "awesome",
    "beautiful",
    "best",
    "better",
    "brilliant",
    "clear",
    "clearer",
    "clearly",
    "concise",
    "cool",
    "delightful",
    "easy",
    "easiest",
    "easily",
    "effective",
    "efficient",
    "enjoy",
    "enjoyable",
    "enjoyed",
    "enjoying",
    "excellent",
    "fantastic",
    "fascinating",
    "favorite",
    "favourite",
    "fun",
    "funny",
    "glad",
    "good",
    "great",
    "greatest",
    "happy",
    "helpful",
    "helped",
    "helps",
    "impressive",
    "impressed",
    "informative",
    "insightful",
    "inspiring",
    "inspired",
    "interesting",
    "joyful",
    "joy",
    "delight",
    "learn",
    "learned",
    "love",
    "lovely",
    "loved",
    "loves",
    "nice",
    "outstanding",
    "perfect",
    "pleasant",
    "pleased",
    "positive",
    "powerful",
    "practical",
    "quality",
    "remarkable",
    "simple",
    "straightforward",
    "superb",
    "thank",
    "thanks",
    "thankful",
    "grateful",
    "appreciate",
    "appreciated",
    "useful",
    "valuable",
    "wonderful",
    "wow",
    "satisfied",
    "satisfying",
    "motivating",
    "motivated",
    "encouraging",
    "friendly",
    "patient",
    "thorough",
    "detailed",
    "liked",
    "genius",
    "masterful",
    "solid",
    "strong",
    "smooth",
    "quick",
    "fast",
    "humorous",
    "entertaining",
    "engaging",
    "accessible",
    "honest",
    "true",
    "correct",
    "accurate",
    "complete",
    "comprehensive",
    "organized",
    "organised",
    "structured",
    "logical",
    "relevant",
    "gold",
    "gem",
    "legend",
    "hero",
    "saved",
    "saving",
    "finally",
    "understand",
    "understood",
    "confident",
    "ready",
    "excited",
    "exciting",
    "incredible",
    "unbelievable",
    "terrific",
    "marvelous",
    "marvellous",
    "splendid",
    "success",
    "successful",
    "win",
    "winning",
    "progress",
    "improved",
    "improvement",
}

#: Strong negative words score -2; every other negative word scores -1.
STRONG_NEGATIVE = {
    "hate",
    "terrible",
    "awful",
    "horrible",
    "worst",
    "useless",
}

#: Negative words scoring -1.
#: Deliberately EXCLUDED (ambiguous in comments — they usually mark a
#: help request or a question, not negative sentiment): "error", "errors",
#: "problem", "problems", "issue", "issues", "trouble", "difficulty",
#: "stuck", "lost", "long", "old", "quiet", "loud", "dark", "low", "up",
#: "give", "off", "topic", "complex", "complicated", "sleep", "dead",
#: "blocked", "quit", "cannot", "slowly", "struggle", "struggling",
#: "suffering", "pain". Those words are still caught by the theme
#: classifier (criticism / questions / audio_video) where they belong.
NEGATIVE_WORDS = {
    "hate",
    "hated",
    "hates",
    "hating",
    "terrible",
    "awful",
    "horrible",
    "worst",
    "useless",
    "bad",
    "badly",
    "boring",
    "broken",
    "confusing",
    "confused",
    "confuse",
    "confuses",
    "disappointing",
    "disappointed",
    "dumb",
    "hard",
    "stupid",
    "unclear",
    "vague",
    "waste",
    "wasted",
    "wasting",
    "wrong",
    "annoying",
    "annoyed",
    "irritating",
    "irritated",
    "poor",
    "poorly",
    "slow",
    "difficult",
    "frustrating",
    "frustrated",
    "misleading",
    "outdated",
    "incorrect",
    "inaccurate",
    "mistake",
    "mistakes",
    "sad",
    "angry",
    "mad",
    "upset",
    "fail",
    "failed",
    "failing",
    "failure",
    "sucks",
    "suck",
    "sucked",
    "dislike",
    "disliked",
    "dull",
    "bland",
    "pointless",
    "meaningless",
    "ridiculous",
    "absurd",
    "nonsense",
    "garbage",
    "trash",
    "junk",
    "crap",
    "shit",
    "damn",
    "hell",
    "silly",
    "painful",
    "misunderstood",
    "shallow",
    "incomplete",
    "missing",
    "weak",
    "worse",
    "horribly",
    "terribly",
    "awfully",
    "rushed",
    "overwhelming",
    "overwhelmed",
    "stressful",
    "stress",
    "anxious",
    "worried",
    "worry",
    "fear",
    "scared",
    "afraid",
    "doubt",
    "doubtful",
    "skeptical",
    "unreliable",
    "untrustworthy",
    "fake",
    "false",
    "lie",
    "lies",
    "lying",
    "scam",
    "clickbait",
    "spam",
    "advertisement",
    "ads",
    "repetitive",
    "repetition",
    "tired",
    "exhausted",
    "crash",
    "bug",
    "bugs",
    "glitch",
    "blurry",
    "impossible",
    "regret",
    "regretted",
    "disaster",
    "mess",
    "messy",
    "chaos",
    "chaotic",
    "disorganized",
    "disorganised",
    "unstructured",
    "rambling",
    "irrelevant",
    "flawed",
    "flaw",
    "tedious",
    "monotonous",
    "meh",
    "whatever",
    "nah",
    "nope",
    "ugh",
    "ew",
    "yuck",
    "disgusting",
    "gross",
    "nasty",
    "vile",
    "appalling",
    "atrocious",
    "dreadful",
    "abysmal",
    "pathetic",
    "lame",
    "idiotic",
    "moronic",
    "foolish",
    "obsolete",
    "deprecated",
}

#: word -> polarity (+1 / -1 / +2 / -2). Strong sets win over the base sets.
LEXICON: dict[str, float] = {}
for _word in POSITIVE_WORDS:
    LEXICON[_word] = 2.0 if _word in STRONG_POSITIVE else 1.0
for _word in NEGATIVE_WORDS:
    LEXICON[_word] = -2.0 if _word in STRONG_NEGATIVE else -1.0

NEGATIONS = {
    "not",
    "no",
    "never",
    "n't",
    "don't",
    "doesn't",
    "didn't",
    "can't",
    "won't",
    "isn't",
    "wasn't",
    "aren't",
    "couldn't",
    "shouldn't",
}

INTENSIFIERS = {
    "very",
    "extremely",
    "so",
    "really",
    "absolutely",
    "totally",
    "super",
    "incredibly",
    "truly",
    "quite",
    "pretty",
}

#: Negation flips the next N scored words (research_brief §3.1: window 3).
NEGATION_WINDOW = 3
#: Intensifier multiplier for the next scored word.
INTENSIFIER_MULTIPLIER = 1.5
#: Saturating normaliser (same shape VADER publishes — standard function).
NORMALISER = 15.0
#: Classification thresholds (VADER's published +/-0.05).
POSITIVE_THRESHOLD = 0.05
NEGATIVE_THRESHOLD = -0.05

#: Emoji map — a small explicit list, not a full emoji model.
EMOJI_POSITIVE = {"😍", "😂", "👍", "❤️", "🔥", "🙌", "👏", "😊", "🎉", "💯"}
EMOJI_NEGATIVE = {"😡", "👎", "😢", "💩", "🤮", "😤", "😠"}
EMOJI_CAP = 2

_TOKEN_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_MENTION_RE = re.compile(r"@\w+")

# ---------------------------------------------------------------------------
# Themes (fixed keyword lists, research_brief §3.2 — authored before the data)
# ---------------------------------------------------------------------------

#: theme -> keywords, in priority order. A comment may carry up to 2 themes.
THEME_KEYWORDS: dict[str, list[str]] = {
    "praise": [
        "thank",
        "thanks",
        "great",
        "amazing",
        "awesome",
        "excellent",
        "love",
        "brilliant",
        "fantastic",
        "wonderful",
        "best",
        "perfect",
        "helpful",
        "useful",
        "clear",
        "easy to follow",
        "well explained",
        "good job",
        "nice",
        "beautiful",
    ],
    "tutorial_quality": [
        "explained",
        "explanation",
        "clear",
        "unclear",
        "confusing",
        "confused",
        "understand",
        "understood",
        "step by step",
        "detailed",
        "thorough",
        "beginner friendly",
        "pace",
        "too fast",
        "too slow",
        "rushed",
    ],
    "requests": [
        "please make",
        "more videos",
        "next video",
        "part 2",
        "tutorial on",
        "cover",
        "request",
        "want more",
        "do a video",
        "can you make",
    ],
    "career": [
        "job",
        "career",
        "interview",
        "salary",
        "switch",
        "beginner",
        "start",
        "learning path",
        "roadmap",
        "get a job",
        "hired",
    ],
    "criticism": [
        "wrong",
        "incorrect",
        "mistake",
        "error",
        "outdated",
        "misleading",
        "bad",
        "terrible",
        "boring",
        "waste",
        "useless",
        "disappointed",
        "poor",
    ],
    "questions": [
        "how do",
        "how to",
        "what is",
        "why",
        "question",
        "can anyone",
        "does anyone",
        "help me",
        "stuck",
        "error",
    ],
    "audio_video": [
        "audio",
        "sound",
        "voice",
        "volume",
        "quality",
        "video quality",
        "blurry",
        "captions",
        "subtitles",
        "accent",
    ],
    "price_cost": [
        "price",
        "cost",
        "expensive",
        "free",
        "paid",
        "worth",
        "money",
        "course fee",
    ],
    "humor": ["lol", "haha", "funny", "😂", "joke", "hilarious"],
}
THEME_ORDER = list(THEME_KEYWORDS)
MAX_THEMES_PER_COMMENT = 2

#: Stopwords for the top-words/bigrams analysis (fixed list, §4.2).
STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "but",
    "if",
    "then",
    "else",
    "when",
    "while",
    "of",
    "to",
    "in",
    "on",
    "at",
    "for",
    "with",
    "by",
    "from",
    "as",
    "is",
    "am",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "shall",
    "should",
    "can",
    "could",
    "may",
    "might",
    "must",
    "i",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
    "me",
    "him",
    "her",
    "us",
    "them",
    "my",
    "your",
    "his",
    "its",
    "our",
    "their",
    "this",
    "that",
    "these",
    "those",
    "there",
    "here",
    "what",
    "which",
    "who",
    "whom",
    "whose",
    "why",
    "how",
    "all",
    "any",
    "both",
    "each",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "no",
    "nor",
    "not",
    "only",
    "own",
    "same",
    "so",
    "than",
    "too",
    "very",
    "just",
    "also",
    "about",
    "into",
    "over",
    "after",
    "before",
    "between",
    "through",
    "during",
    "under",
    "again",
    "further",
    "once",
    "out",
    "up",
    "down",
    "off",
    "don",
    "now",
    "im",
    "ive",
    "id",
    "thats",
    "theres",
    "cant",
    "dont",
    "didnt",
    "wont",
    "isnt",
    "wasnt",
    "arent",
    "video",
    "youtube",
    "channel",
    "tutorial",
    "course",
    "like",
    "really",
    "get",
    "got",
    "one",
    "much",
    "many",
    "even",
    "still",
    "way",
    "thing",
    "things",
    "lot",
}

LABELS = ("positive", "neutral", "negative")


# ---------------------------------------------------------------------------
# Sentiment scoring
# ---------------------------------------------------------------------------


def _tokens(text: str) -> list[str]:
    """Lower-cased word tokens; URLs and @mentions are stripped first."""
    cleaned = _MENTION_RE.sub(" ", _URL_RE.sub(" ", text))
    return _TOKEN_RE.findall(cleaned.lower())


def score_comment(text: str) -> tuple[float, str, int]:
    """Score one comment.

    Returns ``(compound, sentiment_class, scored_words)`` where compound
    is in (-1, +1), the class is one of ``positive`` / ``neutral`` /
    ``negative``, and ``scored_words`` counts the lexicon words matched.
    """
    if not text or not text.strip():
        return 0.0, "neutral", 0
    raw = 0.0
    scored = 0
    negation_left = 0
    intensify_next = False
    for token in _tokens(text):
        if token in NEGATIONS:
            negation_left = NEGATION_WINDOW
            continue
        if token in INTENSIFIERS:
            intensify_next = True
            continue
        polarity = LEXICON.get(token)
        if polarity is None:
            continue
        if negation_left > 0:
            polarity = -polarity
            negation_left -= 1
        if intensify_next:
            polarity *= INTENSIFIER_MULTIPLIER
            intensify_next = False
        raw += polarity
        scored += 1
    # Emoji: small explicit map, capped per comment.
    pos_emoji = sum(1 for ch in text if ch in EMOJI_POSITIVE)
    neg_emoji = sum(1 for ch in text if ch in EMOJI_NEGATIVE)
    raw += min(pos_emoji, EMOJI_CAP) - min(neg_emoji, EMOJI_CAP)
    # Exclamation: amplifies praise only, never turns a complaint positive.
    if raw > 0:
        raw += min(0.25 * text.count("!"), 0.5)
    compound = raw / math.sqrt(raw * raw + NORMALISER) if raw else 0.0
    return round(compound, 4), classify_sentiment(compound), scored


def classify_sentiment(compound: float) -> str:
    """Map a compound score to positive / neutral / negative (+/-0.05)."""
    if compound >= POSITIVE_THRESHOLD:
        return "positive"
    if compound <= NEGATIVE_THRESHOLD:
        return "negative"
    return "neutral"


# ---------------------------------------------------------------------------
# Themes
# ---------------------------------------------------------------------------


def classify_themes(text: str) -> list[str]:
    """Assign up to 2 keyword themes (in THEME_ORDER); ``other`` if none.

    The ``questions`` theme requires a ``?`` in the text.
    """
    lowered = text.lower()
    matched: list[str] = []
    for theme in THEME_ORDER:
        if theme == "questions" and "?" not in text:
            continue
        if any(keyword in lowered for keyword in THEME_KEYWORDS[theme]):
            matched.append(theme)
        if len(matched) >= MAX_THEMES_PER_COMMENT:
            break
    return matched or ["other"]


# ---------------------------------------------------------------------------
# Language heuristic
# ---------------------------------------------------------------------------


def is_non_latin(text: str) -> bool:
    """True when > 20% of the alphabetic characters are non-Latin script.

    Crude heuristic (stdlib ``unicodedata`` only), not a language
    identifier: Latin-script non-English (e.g. Spanish) is NOT caught.
    """
    cleaned = _MENTION_RE.sub(" ", _URL_RE.sub(" ", text))
    letters = [ch for ch in cleaned if ch.isalpha()]
    if not letters:
        return False
    non_latin = sum(1 for ch in letters if "LATIN" not in unicodedata.name(ch, ""))
    return non_latin / len(letters) > 0.2


# ---------------------------------------------------------------------------
# Top words / bigrams
# ---------------------------------------------------------------------------


def _content_tokens(text: str) -> list[str]:
    """Tokens with stopwords removed (for the top-words analysis)."""
    return [tok for tok in _tokens(text) if tok not in STOPWORDS]


def top_words(texts: list[str], n: int = 20) -> list[tuple[str, int]]:
    """Most common non-stopword unigrams, count desc then word asc."""
    counts: Counter[str] = Counter()
    for text in texts:
        counts.update(_content_tokens(text))
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def top_bigrams(texts: list[str], n: int = 20) -> list[tuple[str, int]]:
    """Most common non-stopword bigrams, count desc then bigram asc."""
    counts: Counter[str] = Counter()
    for text in texts:
        toks = _content_tokens(text)
        counts.update(f"{a} {b}" for a, b in itertools.pairwise(toks))
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


# ---------------------------------------------------------------------------
# Validation evaluation
# ---------------------------------------------------------------------------


def evaluate_predictions(predicted: list[str], human: list[str]) -> dict:
    """Confusion matrix + per-class precision/recall/F1 from two label lists.

    ``predicted`` and ``human`` must be parallel lists of labels from
    ``LABELS``. Returns a dict with ``confusion`` (nested true -> pred ->
    count), ``per_class`` (precision/recall/f1/support per label),
    ``accuracy``, ``macro_f1`` and ``n``.
    """
    if len(predicted) != len(human):
        raise ValueError("predicted and human label lists must align")
    confusion: dict[str, dict[str, int]] = {
        true: {pred: 0 for pred in LABELS} for true in LABELS
    }
    for pred, true in zip(predicted, human, strict=True):
        if pred not in LABELS or true not in LABELS:
            raise ValueError(f"unknown label: predicted={pred!r} human={true!r}")
        confusion[true][pred] += 1
    per_class: dict[str, dict[str, float]] = {}
    f1s: list[float] = []
    for label in LABELS:
        tp = confusion[label][label]
        fp = sum(confusion[other][label] for other in LABELS if other != label)
        fn = sum(confusion[label][other] for other in LABELS if other != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (
            2 * precision * recall / (precision + recall) if precision + recall else 0.0
        )
        f1s.append(f1)
        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": tp + fn,
        }
    n = len(human)
    correct = sum(confusion[label][label] for label in LABELS)
    return {
        "confusion": confusion,
        "per_class": per_class,
        "accuracy": round(correct / n, 4) if n else 0.0,
        "macro_f1": round(sum(f1s) / len(f1s), 4) if f1s else 0.0,
        "n": n,
    }
