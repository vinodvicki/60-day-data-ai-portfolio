"""Statistical comparisons (Day 15) — pure functions, no I/O.

- Topic x outlet: chi-square test of independence, with the plan §4.3
  sparse-cell rule: if any expected cell count is below 5, collapse
  the topics into the 4 largest topics by corpus count plus "All other
  topics" and re-check; if any expected cell is still below 5, run
  chi-square on the full table but report a permutation p-value
  (10,000 label shuffles, seed 42) alongside the asymptotic p-value,
  and state which p-value the conclusion rests on.
- Sentiment across outlets: Shapiro-Wilk normality per outlet; if
  every outlet's p > 0.05, one-way ANOVA, otherwise Kruskal-Wallis.
  Pairwise differences only with a stated correction (Tukey HSD after
  ANOVA; pairwise Mann-Whitney U with Bonferroni correction after
  Kruskal-Wallis). Never report uncorrected pairwise p-values as
  findings.

A significant result is reported only as "the distribution of topics /
the average language tone differs across outlets in this corpus and
window" — never as evidence about an outlet's fairness, accuracy or
intent, and never as a ranking of any kind.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

SPARSE_EXPECTED_MIN: float = 5.0
N_PERMUTATIONS: int = 10000
PERMUTATION_SEED: int = 42


def bootstrap_ci(
    values: pd.Series, n_resamples: int = 1000, seed: int = 42
) -> tuple[float, float]:
    """Percentile bootstrap 95% CI for the mean (seed 42)."""
    arr = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    means = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        sample = rng.choice(arr, size=len(arr), replace=True)
        means[i] = float(np.mean(sample))
    low, high = np.percentile(means, [2.5, 97.5])
    return (float(low), float(high))


def _chi2_on_table(values: np.ndarray) -> tuple[float, float, int, float]:
    """Chi-square on a counts array; returns (chi2, p, dof, min_expected)."""
    chi2, p, dof, expected = scipy_stats.chi2_contingency(values, correction=False)
    return float(chi2), float(p), int(dof), float(expected.min())


def _collapse_table(table: pd.DataFrame) -> pd.DataFrame:
    """Collapse to the 4 largest topics by corpus count + Other."""
    totals = table.sum(axis=0).sort_values(ascending=False)
    keep = list(totals.index[:4])
    rest = [c for c in table.columns if c not in keep]
    collapsed = table[keep].copy()
    collapsed["All other topics"] = table[rest].sum(axis=1) if rest else 0
    return collapsed


def chi_square_topic_outlet(table: pd.DataFrame) -> dict[str, object]:
    """Chi-square test of independence on a topic x outlet table.

    ``table`` has outlets as rows and topics as columns (article
    counts). All-zero outlet rows and all-zero topic columns are
    excluded from the test and recorded (an outlet with no usable
    articles in the window contributes no information to the test).
    Applies the plan §4.3 sparse-cell rule.
    """
    working = table.loc[table.sum(axis=1) > 0, table.sum(axis=0) > 0].copy()
    excluded_outlets = [str(i) for i in table.index if table.loc[i].sum() == 0]
    excluded_topics = [str(c) for c in table.columns if table[c].sum() == 0]
    if working.shape[0] < 2 or working.shape[1] < 2:
        return {
            "test": "chi-square (not run)",
            "chi2": None,
            "df": None,
            "p_value": None,
            "min_expected": None,
            "sparse": None,
            "collapsed": False,
            "collapsed_chi2": None,
            "collapsed_df": None,
            "collapsed_p_value": None,
            "collapsed_min_expected": None,
            "permutation_p_value": None,
            "conclusion_basis": "not run — fewer than 2 outlets or topics with data",
            "excluded_outlets": excluded_outlets,
            "excluded_topics": excluded_topics,
            "n_outlets_tested": int(working.shape[0]),
            "n_topics_tested": int(working.shape[1]),
        }
    chi2, p_value, dof, min_expected = _chi2_on_table(working.to_numpy(dtype=float))
    sparse = min_expected < SPARSE_EXPECTED_MIN
    result: dict[str, object] = {
        "test": "chi-square test of independence",
        "chi2": chi2,
        "df": dof,
        "p_value": p_value,
        "min_expected": min_expected,
        "sparse": sparse,
        "collapsed": False,
        "collapsed_chi2": None,
        "collapsed_df": None,
        "collapsed_p_value": None,
        "collapsed_min_expected": None,
        "permutation_p_value": None,
        "conclusion_basis": "asymptotic p-value",
        "excluded_outlets": excluded_outlets,
        "excluded_topics": excluded_topics,
        "n_outlets_tested": int(working.shape[0]),
        "n_topics_tested": int(working.shape[1]),
    }
    if not sparse:
        return result
    collapsed = _collapse_table(working)
    c_chi2, c_p, c_dof, c_min = _chi2_on_table(collapsed.to_numpy(dtype=float))
    result["collapsed"] = True
    result["collapsed_chi2"] = c_chi2
    result["collapsed_df"] = c_dof
    result["collapsed_p_value"] = c_p
    result["collapsed_min_expected"] = c_min
    if c_min >= SPARSE_EXPECTED_MIN:
        result["conclusion_basis"] = (
            "asymptotic p-value on the collapsed table "
            "(4 largest topics + All other topics)"
        )
        return result
    perm_p = permutation_pvalue(working)
    result["permutation_p_value"] = perm_p
    result["conclusion_basis"] = (
        "permutation p-value (10,000 shuffles, seed 42) on the full table; "
        "the asymptotic p-value is reported alongside but the conclusion "
        "rests on the permutation p-value"
    )
    return result


def permutation_pvalue(
    table: pd.DataFrame, n_permutations: int = N_PERMUTATIONS, seed: int = 42
) -> float:
    """Permutation p-value for independence on a counts table.

    Outlet labels are shuffled across articles (row totals and column
    totals are preserved in expectation by the shuffle of the
    article-level labels); the p-value is the share of shuffled tables
    whose chi-square statistic is at least the observed one.
    """
    values = table.to_numpy(dtype=float)
    observed, _, _, _ = _chi2_on_table(values)
    row_totals = values.sum(axis=1)
    col_totals = values.sum(axis=0)
    n_total = int(values.sum())
    if n_total == 0:
        return 1.0
    outlet_labels = np.repeat(np.arange(len(row_totals)), row_totals.astype(int))
    topic_labels = np.repeat(np.arange(len(col_totals)), col_totals.astype(int))
    rng = np.random.default_rng(seed)
    n_ge = 0
    expected = np.outer(row_totals, col_totals) / n_total
    for _ in range(n_permutations):
        shuffled = rng.permutation(topic_labels)
        perm_table = np.zeros_like(values)
        np.add.at(perm_table, (outlet_labels, shuffled), 1.0)
        with np.errstate(divide="ignore", invalid="ignore"):
            terms = np.where(
                expected > 0,
                (perm_table - expected) ** 2 / np.where(expected > 0, expected, 1.0),
                0.0,
            )
        perm_chi2 = float(terms.sum())
        if perm_chi2 >= observed:
            n_ge += 1
    return float(n_ge / n_permutations)


def sentiment_test_by_outlet(df: pd.DataFrame) -> dict[str, object]:
    """ANOVA or Kruskal-Wallis on VADER compound by outlet.

    Normality is tested per outlet with Shapiro-Wilk (outlets with
    fewer than 3 articles cannot be tested and are excluded from the
    test, recorded in ``excluded_outlets``). If every tested outlet
    has Shapiro p > 0.05, one-way ANOVA is used; otherwise
    Kruskal-Wallis.
    """
    groups: dict[str, pd.Series] = {}
    normality: dict[str, dict[str, float | int]] = {}
    excluded: list[str] = []
    for outlet, group in df.groupby("outlet"):
        scores = pd.to_numeric(group["vader_compound"], errors="coerce").dropna()
        if len(scores) < 3:
            excluded.append(str(outlet))
            continue
        groups[str(outlet)] = scores
        stat, p_value = scipy_stats.shapiro(scores.to_numpy(dtype=float))
        normality[str(outlet)] = {
            "n": len(scores),
            "W": float(stat),
            "p_value": float(p_value),
        }
    if len(groups) < 2:
        return {
            "test": "not run",
            "statistic": None,
            "p_value": None,
            "why": "fewer than 2 outlets with 3+ articles",
            "normality": normality,
            "excluded_outlets": excluded,
            "outlets_tested": sorted(groups),
        }
    all_normal = all(info["p_value"] > 0.05 for info in normality.values())
    arrays = [g.to_numpy(dtype=float) for g in groups.values()]
    if all_normal:
        stat, p_value = scipy_stats.f_oneway(*arrays)
        return {
            "test": "one-way ANOVA",
            "statistic": float(stat),
            "p_value": float(p_value),
            "why": "Shapiro-Wilk p > 0.05 for every tested outlet",
            "normality": normality,
            "excluded_outlets": excluded,
            "outlets_tested": sorted(groups),
        }
    stat, p_value = scipy_stats.kruskal(*arrays)
    return {
        "test": "Kruskal-Wallis",
        "statistic": float(stat),
        "p_value": float(p_value),
        "why": "at least one outlet failed Shapiro-Wilk normality (p <= 0.05)",
        "normality": normality,
        "excluded_outlets": excluded,
        "outlets_tested": sorted(groups),
    }


def pairwise_tests(df: pd.DataFrame, method: str) -> pd.DataFrame:
    """Corrected pairwise outlet differences; corrected p-values only.

    ``method`` is ``"tukey"`` (Tukey HSD, after ANOVA) or ``"dunn"``
    (pairwise Mann-Whitney U with Bonferroni correction, after
    Kruskal-Wallis). Outlets with fewer than 3 articles are excluded.
    """
    outlets: list[str] = []
    groups: dict[str, np.ndarray] = {}
    for outlet, group in df.groupby("outlet"):
        scores = pd.to_numeric(group["vader_compound"], errors="coerce").dropna()
        if len(scores) >= 3:
            outlets.append(str(outlet))
            groups[str(outlet)] = scores.to_numpy(dtype=float)
    outlets.sort()
    rows: list[dict[str, object]] = []
    pairs = list(itertools.combinations(outlets, 2))
    if method == "tukey":
        result = scipy_stats.tukey_hsd(*[groups[o] for o in outlets])
        pvalues = np.asarray(result.pvalue, dtype=float)
        index = {o: i for i, o in enumerate(outlets)}
        for a, b in pairs:
            i, j = index[a], index[b]
            rows.append(
                {
                    "outlet_a": a,
                    "outlet_b": b,
                    "mean_diff": float(groups[a].mean() - groups[b].mean()),
                    "p_value": float(pvalues[i, j]),
                    "corrected": True,
                    "method": "Tukey HSD",
                }
            )
    elif method == "dunn":
        m = len(pairs)
        for a, b in pairs:
            _, p_raw = scipy_stats.mannwhitneyu(
                groups[a], groups[b], alternative="two-sided"
            )
            p_adj = min(float(p_raw) * m, 1.0)
            rows.append(
                {
                    "outlet_a": a,
                    "outlet_b": b,
                    "mean_diff": float(groups[a].mean() - groups[b].mean()),
                    "p_value": p_adj,
                    "corrected": True,
                    "method": "Mann-Whitney U with Bonferroni correction",
                }
            )
    else:
        raise ValueError(f"Unknown pairwise method: {method!r}")
    return pd.DataFrame(
        rows,
        columns=["outlet_a", "outlet_b", "mean_diff", "p_value", "corrected", "method"],
    )
