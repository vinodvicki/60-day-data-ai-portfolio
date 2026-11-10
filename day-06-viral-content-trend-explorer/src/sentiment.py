"""Rule-based sentiment scorer for Day 6 (copied verbatim from Day 5).

Copied verbatim from Day 5's src/sentiment.py (Victor's own code, copied
within his repo, not re-derived and not re-tuned — plan.md §4.2). Day 5's
theme functions (classify_themes, top_words, top_bigrams) and the
validation evaluator are NOT copied: themes are Day 5's scope.

An original, transparent lexicon model — VADER-*style* in shape only
(a word-polarity sum with negation and intensifier handling, normalised
to [-1, +1]). The lexicon was authored for this project; it is NOT the
VADER lexicon, no NLTK download, no pretrained model, no paid API.
Every word, weight and rule lives in this one file so any reader can
audit the full model.

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

import math
import re
import unicodedata

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
