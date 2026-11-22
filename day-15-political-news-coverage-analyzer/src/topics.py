"""Frozen topic dictionary and attention-share helpers (Day 15).

The topic dictionary is frozen in plan §4.1. It must not be tuned after
seeing results. The same dictionary is printed verbatim in README.md;
a test asserts the two are byte-identical.

Matching is on lowercased ``title + " " + description``. One hit is
counted per keyword occurrence per topic (a keyword appearing twice
counts twice). Assignment: the topic with the most hits wins; ties go
to the topic whose keyword appears earliest in the text; zero hits
means ``Other``. ``Other`` has no keywords — it is the fallback only.
"""

from __future__ import annotations

import math

# Frozen topic dictionary (plan §4.1, verbatim). Do not edit.
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "Economy": [
        "economy",
        "economic",
        "inflation",
        "jobs",
        "unemployment",
        "wages",
        "market",
        "stock",
        "recession",
        "gdp",
        "interest rate",
        "federal reserve",
        "trade",
        "tariff",
        "deficit",
        "budget",
        "consumer price",
        "mortgage",
    ],
    "Healthcare": [
        "health",
        "healthcare",
        "hospital",
        "doctor",
        "medicare",
        "medicaid",
        "vaccine",
        "disease",
        "drug",
        "pharmaceutical",
        "insurance",
        "clinic",
        "patient",
        "mental health",
    ],
    "Immigration": [
        "immigration",
        "immigrant",
        "migrant",
        "border",
        "asylum",
        "deportation",
        "visa",
        "citizenship",
        "refugee",
        "customs",
    ],
    "Climate/Energy": [
        "climate",
        "energy",
        "carbon",
        "emission",
        "renewable",
        "solar",
        "wind power",
        "oil",
        "gas price",
        "electric vehicle",
        "wildfire",
        "hurricane",
        "drought",
        "environment",
    ],
    "Foreign policy": [
        "foreign policy",
        "ukraine",
        "russia",
        "china",
        "taiwan",
        "middle east",
        "israel",
        "gaza",
        "nato",
        "diplomacy",
        "sanction",
        "war",
        "military",
        "defense",
        "treaty",
        "summit",
    ],
    "Elections & campaigns": [
        "election",
        "campaign",
        "vote",
        "voter",
        "candidate",
        "polling",
        "poll",
        "ballot",
        "primary",
        "democrat",
        "republican",
        "congress",
        "senate",
        "house of representatives",
        "governor",
        "president",
        "white house",
    ],
    "Crime & justice": [
        "crime",
        "police",
        "court",
        "trial",
        "justice",
        "prison",
        "shooting",
        "murder",
        "arrest",
        "lawsuit",
        "supreme court",
        "judge",
        "gun",
        "fentanyl",
    ],
    "Technology & AI": [
        "technology",
        "artificial intelligence",
        "ai",
        "tech",
        "cybersecurity",
        "cyberattack",
        "data breach",
        "social media",
        "smartphone",
        "semiconductor",
        "robot",
        "algorithm",
    ],
    "Education": [
        "education",
        "school",
        "teacher",
        "student",
        "college",
        "university",
        "tuition",
        "curriculum",
        "classroom",
        "graduation",
        "childcare",
    ],
    "Other": [],
}

TOPICS: list[str] = list(TOPIC_KEYWORDS)

Z_95: float = 1.96


def assign_topic(text: str) -> str:
    """Assign a topic to ``text`` using the frozen keyword dictionary.

    Matching is on the lowercased text; keywords match as substrings.
    The topic with the most keyword hits wins; ties go to the topic
    whose keyword appears earliest in the text; zero hits means
    ``Other``.
    """
    lowered = text.lower()
    best_topic = "Other"
    best_hits = 0
    best_position: int | None = None
    for topic, keywords in TOPIC_KEYWORDS.items():
        if not keywords:
            continue
        hits = 0
        first_position: int | None = None
        for keyword in keywords:
            count = lowered.count(keyword)
            hits += count
            position = lowered.find(keyword)
            if position >= 0 and (first_position is None or position < first_position):
                first_position = position
        if hits == 0:
            continue
        if hits > best_hits or (
            hits == best_hits
            and best_position is not None
            and first_position is not None
            and first_position < best_position
        ):
            best_topic = topic
            best_hits = hits
            best_position = first_position
    return best_topic


def attention_share(count: int, total: int) -> float:
    """Within-outlet attention share in percent (0.0 when total is 0)."""
    if total <= 0:
        return 0.0
    return count / total * 100.0


def wilson_ci(k: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson 95% confidence interval for a share, in percent (0-100).

    Returns ``(0.0, 0.0)`` when ``n`` is 0 (no articles, no share).
    """
    if n <= 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1.0 + z * z / n
    centre = p + z * z / (2.0 * n)
    margin = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))
    low = (centre - margin) / denom * 100.0
    high = (centre + margin) / denom * 100.0
    return (max(0.0, low), min(100.0, high))
