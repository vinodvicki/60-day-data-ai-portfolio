"""Pure turnout functions for Day 14 — Voter Turnout Analytics.

No I/O, no network — every function here is unit-tested in
``tests/test_pipeline.py``. All rates are percentages of a stated
denominator for a stated election; VEP (voting-eligible population)
turnout is the primary metric, VAP (voting-age population) turnout is
reported alongside it, never as a substitute. Descriptive only: no
model is fitted anywhere in this build, and correlations are reported
as associations, never as causes.
"""

from __future__ import annotations

import math

import pandas as pd
from scipy import stats

#: Cycle-type colours, fixed on every surface (plan §7).
PRESIDENTIAL_COLOUR = "#2e6fb7"
MIDTERM_COLOUR = "#7f8c8d"

#: Tolerance for the recompute cross-check, in percentage points (plan §3.3).
RECOMPUTE_TOLERANCE_PP = 0.05

#: Tolerance for the VEP reconciliation check, as a share of the file VEP (plan §3.2).
VEP_RECONCILIATION_TOLERANCE = 0.005


def cycle_type(year: int) -> str:
    """``presidential`` if ``year % 4 == 0``, else ``midterm`` (plan §2.0 Rule 4)."""
    return "presidential" if year % 4 == 0 else "midterm"


def _valid(value: float | None) -> float | None:
    """Return ``value`` as a float, or ``None`` when it is missing or not finite."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def vep_turnout(ballots: float | None, vep: float | None) -> float | None:
    """VEP turnout = ballots counted / VEP * 100 (primary metric, plan §4.1).

    Returns ``None`` when either input is missing or the VEP is not positive,
    so a missing numerator never yields a bogus rate.
    """
    ballots_n = _valid(ballots)
    vep_n = _valid(vep)
    if ballots_n is None or vep_n is None or vep_n <= 0:
        return None
    return ballots_n / vep_n * 100.0


def vap_turnout(ballots: float | None, vap: float | None) -> float | None:
    """VAP turnout = ballots counted / VAP * 100 (secondary metric, plan §4.1).

    Always lower than VEP turnout wherever both exist, because VAP includes
    noncitizens and ineligible felons. Returns ``None`` on missing inputs.
    """
    ballots_n = _valid(ballots)
    vap_n = _valid(vap)
    if ballots_n is None or vap_n is None or vap_n <= 0:
        return None
    return ballots_n / vap_n * 100.0


def pp_change(current: float, previous: float) -> float:
    """Percentage-point change between two rates in the same cycle type."""
    return current - previous


def recompute_vep(
    vap: float, noncitizen_pct: float, felons_total: float, overseas: float
) -> float:
    """Recompute VEP from its components (plan §3.2 rule 5).

    VEP = VAP - noncitizen VAP - ineligible felons + eligible overseas.
    A missing overseas value is passed as 0.0 by the caller (the lab does
    not apportion overseas eligible voters to states). This is a check
    only — the file's VEP is used throughout, never replaced.
    """
    overseas_n = 0.0 if math.isnan(overseas) else overseas
    return vap - vap * noncitizen_pct / 100.0 - felons_total + overseas_n


def felon_share_vap(felons_total: float | None, vap: float | None) -> float | None:
    """Ineligible-felon share of VAP, as a proportion (0–1)."""
    felons_n = _valid(felons_total)
    vap_n = _valid(vap)
    if felons_n is None or vap_n is None or vap_n <= 0:
        return None
    return felons_n / vap_n


def overseas_share_vep(overseas: float | None, vep: float | None) -> float | None:
    """Eligible-overseas share of VEP, as a proportion (0–1)."""
    overseas_n = _valid(overseas)
    vep_n = _valid(vep)
    if overseas_n is None or vep_n is None or vep_n <= 0:
        return None
    return overseas_n / vep_n


def parse_column5(value: str | None) -> tuple[str | None, float | None]:
    """Parse the ambiguous 5th column of the UF files by content (plan §3.2 rule 2).

    The header says ``VOTE_FOR_HIGHEST_OFFICE``, but for 2020/2022 rows the
    column holds a source URL, and for 2018 and earlier rows it holds the
    vote count. Returns ``(source_url, vote_count)``: a value starting with
    ``http`` is a URL, an all-digits (commas allowed) value is a vote count,
    a blank value is missing in both. A URL is never parsed as a vote count.
    """
    if value is None:
        return None, None
    text = str(value).strip()
    if text == "":
        return None, None
    if text.startswith("http"):
        return text, None
    digits = text.replace(",", "")
    if digits.isdigit():
        return None, float(digits)
    return None, None


def flag_outliers(series: pd.Series) -> pd.DataFrame:
    """Flag outliers in a VEP-turnout series (plan §2.0 Rule 3).

    A value is flagged when it lies outside the 1.5 x IQR fence or its
    |z| > 3, computed within the series passed in (the caller passes one
    cycle type at a time). Returns one row per flagged value, indexed by
    the series index, with the value, which rule(s) fired, the z-score,
    and the fence values. Flagging never drops a row — flagged rows stay
    in every chart and table.
    """
    clean = series.dropna().astype(float)
    if len(clean) < 4:
        return pd.DataFrame(
            columns=["value", "rule", "statistic_value", "lower_fence", "upper_fence"]
        )
    q1 = float(clean.quantile(0.25))
    q3 = float(clean.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    mean = float(clean.mean())
    std = float(clean.std(ddof=1))
    rows: list[dict[str, object]] = []
    index: list[object] = []
    for idx, value in clean.items():
        number = float(value)
        z = (number - mean) / std if std > 0 else 0.0
        outside = number < lower or number > upper
        extreme_z = abs(z) > 3
        if not (outside or extreme_z):
            continue
        if outside and extreme_z:
            rule = "iqr+z"
        elif outside:
            rule = "iqr"
        else:
            rule = "z"
        rows.append(
            {
                "value": number,
                "rule": rule,
                "statistic_value": z,
                "lower_fence": lower,
                "upper_fence": upper,
            }
        )
        index.append(idx)
    if not rows:
        return pd.DataFrame(
            columns=["value", "rule", "statistic_value", "lower_fence", "upper_fence"]
        )
    return pd.DataFrame(rows, index=pd.Index(index))


def skewness(series: pd.Series) -> float:
    """Fisher skewness of a VEP-turnout series (a number, not a judgement)."""
    clean = series.dropna().astype(float)
    if len(clean) < 3:
        return 0.0
    value = float(clean.skew())
    return value if math.isfinite(value) else 0.0


def correlate(x: pd.Series, y: pd.Series) -> dict[str, float | int | None]:
    """Pearson r + p and Spearman rho + p for two series (plan §4.3).

    Returns ``n`` plus the four statistics; when fewer than three paired
    observations exist, or either series is constant, the correlations are
    ``None`` (reported as "no clear association in these data", never
    hidden, never crashed on). Descriptive only — a correlation is not
    a cause.
    """
    frame = pd.DataFrame({"x": x, "y": y}).dropna()
    n = len(frame)
    result: dict[str, float | int | None] = {
        "n": n,
        "pearson_r": None,
        "pearson_p": None,
        "spearman_r": None,
        "spearman_p": None,
    }
    if n < 3:
        return result
    if frame["x"].nunique() < 2 or frame["y"].nunique() < 2:
        return result
    pearson = stats.pearsonr(
        frame["x"].to_numpy(dtype=float), frame["y"].to_numpy(dtype=float)
    )
    spearman = stats.spearmanr(
        frame["x"].to_numpy(dtype=float), frame["y"].to_numpy(dtype=float)
    )
    result["pearson_r"] = float(pearson.statistic)
    result["pearson_p"] = float(pearson.pvalue)
    result["spearman_r"] = float(spearman.statistic)
    result["spearman_p"] = float(spearman.pvalue)
    return result


def top_bottom(
    df: pd.DataFrame, column: str, n: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Top ``n`` and bottom ``n`` rows by ``column`` (plan §4.2).

    Ties break deterministically by state abbreviation, so the ranking
    is reproducible. Rank 1 is the highest value.
    """
    top = df.sort_values([column, "state_abv"], ascending=[False, True]).head(n)
    bottom = df.sort_values([column, "state_abv"], ascending=[True, True]).head(n)
    return top, bottom
