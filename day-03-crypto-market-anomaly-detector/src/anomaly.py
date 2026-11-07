"""Day 3 — Crypto Market Anomaly Detector: pure anomaly-model module.

No I/O, no network. Every function takes plain DataFrames / Series and
returns plain values, so the pipeline, notebook and Streamlit app import
them instead of re-implementing them.

Conventions (plan.md §4, copied verbatim from the research brief):
- Simple (arithmetic) daily returns, never log returns.
- Trailing 30-day windows EXCLUDING today for all z-scores — a centred
  or full-window z-score would leak future information into "today".
- Rules: R1 |return_z| >= 3; R2 volume_z >= 3 AND volume_ratio >= 2;
  R3 |return_z| >= 2 AND volume_z >= 2.
- Severity: High = R1 or R2 with |z| >= 4, or R1+R2 together;
  Medium = any single rule at threshold; Low = R3 only.
- Isolation Forest: sklearn, random_state=42, n_estimators=200,
  contamination set from the observed baseline flag rate; five features
  standardised per coin (no cross-coin scaling).
- Injected-anomaly evaluation tolerance: +/-1 day.
- Injected anomalies (§4.4 as amended 2026-11-07): magnitudes are
  built from the trailing 30-day window ending the day before the
  injection (price spike +4.0σ_ret, volume surge 5.0× trailing mean
  volume, joint shock +3.0σ_ret and 5.0× trailing mean volume), with a
  mandatory harness self-check that each plant clears its target
  rule's bar on the injected frame; precision counts a flag as a true
  positive if it matches an injection or a clean-data flag.
- Thresholds are fixed by the plan before evaluation runs; a miss is
  reported and diagnosed, never tuned away.
- Ethics guard: flagged days are "unusual patterns requiring
  investigation" — never presented as proven manipulation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

WINDOW = 30
FEATURE_COLUMNS = [
    "daily_return",
    "abs_return",
    "log_volume_ratio",
    "vol_30d_ann",
    "drawdown",
]
INJECTION_TYPES = ("price_spike", "volume_surge", "joint_shock")


def compute_features(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Add the §4.1 features, per coin, on the cleaned daily frame.

    Input columns: date, coin, price, market_cap, volume.
    Adds: daily_return, abs_return, volume_ratio, log_volume_ratio,
    vol_30d_ann, drawdown, return_z, volume_z, vol_regime.
    First daily_return per coin is NaN; first 31 return_z per coin are
    NaN (30-day trailing window plus the first day's missing return);
    volume_z needs 30 prior log-volume-ratio values, which themselves
    need a 30-day volume window, so the first 60 volume_z per coin are
    NaN; first 30 vol_30d_ann per coin are NaN.
    """
    df = daily_df.sort_values(["coin", "date"]).copy()
    frames = []
    for _coin, g in df.groupby("coin", sort=True):
        g = g.sort_values("date").reset_index(drop=True)
        price = g["price"].astype(float)
        volume = g["volume"].astype(float)
        daily_return = price / price.shift(1) - 1
        g["daily_return"] = daily_return
        g["abs_return"] = daily_return.abs()
        # Today's volume vs its own trailing 30-day mean, excluding today.
        trailing_vol = volume.shift(1).rolling(WINDOW).mean()
        g["volume_ratio"] = volume / trailing_vol
        g["log_volume_ratio"] = np.log(g["volume_ratio"])
        g["vol_30d_ann"] = daily_return.rolling(WINDOW).std(ddof=1) * np.sqrt(365)
        g["drawdown"] = price / price.cummax() - 1
        # Trailing z-scores: mean/std of the 30 days BEFORE today.
        prior_ret = daily_return.shift(1)
        ret_mean = prior_ret.rolling(WINDOW).mean()
        ret_std = prior_ret.rolling(WINDOW).std(ddof=1)
        g["return_z"] = (daily_return - ret_mean) / ret_std
        prior_lvr = g["log_volume_ratio"].shift(1)
        vol_mean = prior_lvr.rolling(WINDOW).mean()
        vol_std = prior_lvr.rolling(WINDOW).std(ddof=1)
        g["volume_z"] = (g["log_volume_ratio"] - vol_mean) / vol_std
        g["vol_regime"] = g["vol_30d_ann"] / g["vol_30d_ann"].median()
        frames.append(g)
    out = pd.concat(frames, ignore_index=True)
    return out[
        [
            "date",
            "coin",
            "price",
            "market_cap",
            "volume",
            "daily_return",
            "abs_return",
            "volume_ratio",
            "log_volume_ratio",
            "vol_30d_ann",
            "drawdown",
            "return_z",
            "volume_z",
            "vol_regime",
        ]
    ]


def apply_rules(featured_df: pd.DataFrame) -> pd.DataFrame:
    """Apply baseline rules R1–R3 (§4.2) to a featured frame.

    Adds: rules_triggered (e.g. "R1+R3", "" when no rule fires),
    severity ("High" / "Medium" / "Low", "" when unflagged),
    baseline_flagged (bool). Warm-up rows (NaN z-scores) never flag.
    """
    df = featured_df.copy()
    rz = df["return_z"]
    vz = df["volume_z"]
    r1 = rz.abs() >= 3
    r2 = (vz >= 3) & (df["volume_ratio"] >= 2)
    r3 = (rz.abs() >= 2) & (vz >= 2)
    df["rules_triggered"] = ""
    both = r1 & r2
    df.loc[r1, "rules_triggered"] = df.loc[r1, "rules_triggered"] + "R1"
    df.loc[r2, "rules_triggered"] = df.loc[r2, "rules_triggered"] + "+R2"
    df.loc[r3, "rules_triggered"] = df.loc[r3, "rules_triggered"] + "+R3"
    df["rules_triggered"] = df["rules_triggered"].str.lstrip("+")
    df["baseline_flagged"] = r1 | r2 | r3
    severity = pd.Series("", index=df.index, dtype=object)
    high = df["baseline_flagged"] & (
        both | ((r1) & (rz.abs() >= 4)) | ((r2) & (vz >= 4))
    )
    low = df["baseline_flagged"] & r3 & ~r1 & ~r2
    severity[high] = "High"
    severity[low] = "Low"
    medium = df["baseline_flagged"] & ~high & ~low
    severity[medium] = "Medium"
    df["severity"] = severity
    return df


def fit_isolation_forest(
    featured_df: pd.DataFrame,
    contamination: float,
    random_state: int = 42,
    n_estimators: int = 200,
) -> tuple[dict[str, IsolationForest], pd.DataFrame]:
    """Fit one Isolation Forest per coin on the 5 §4.3 features.

    Features are standardised with each coin's own mean/std (no
    cross-coin scaling). Rows with any missing feature (warm-up rows)
    are not scored: isolation_forest_score is NaN and is_anomaly False.
    Adds: isolation_forest_score (decision function; lower = more
    anomalous) and is_anomaly (bool). Returns ({coin: model}, frame).
    """
    df = featured_df.copy()
    df["isolation_forest_score"] = np.nan
    df["is_anomaly"] = False
    models: dict[str, IsolationForest] = {}
    for coin, g in df.groupby("coin", sort=True):
        idx = g.index
        complete = g[FEATURE_COLUMNS].dropna()
        if len(complete) == 0:
            continue
        mean = complete.mean()
        std = complete.std(ddof=1).replace(0, np.nan)
        scaled = (complete - mean) / std
        scaled = scaled.fillna(0.0)
        model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=n_estimators,
        )
        model.fit(scaled)
        models[coin] = model
        scores = model.decision_function(scaled)
        df.loc[complete.index, "isolation_forest_score"] = scores
        preds = model.predict(scaled)
        df.loc[complete.index, "is_anomaly"] = preds == -1
        df.loc[idx.difference(complete.index), "is_anomaly"] = False
    return models, df


def run_detection(
    featured_df: pd.DataFrame,
    random_state: int = 42,
    n_estimators: int = 200,
) -> tuple[pd.DataFrame, float]:
    """Rules + forest on a featured frame, contamination from the baseline.

    Returns (flagged frame with rules, severity, forest score and
    is_anomaly columns, contamination actually used). The contamination
    is the baseline flag rate over post-warm-up rows (rows with a
    return_z); it is 0.03 if the baseline flags nothing.
    """
    df = apply_rules(featured_df)
    flaggable = df["return_z"].notna()
    baseline_rate = float(df.loc[flaggable, "baseline_flagged"].mean())
    contamination = baseline_rate if baseline_rate > 0 else 0.03
    _models, df = fit_isolation_forest(
        df,
        contamination=contamination,
        random_state=random_state,
        n_estimators=n_estimators,
    )
    return df, contamination


def generate_explanation(row: pd.Series) -> str:
    """One plain-language sentence for a flagged day, from its numbers only.

    No causal claims, no mention of manipulation. Forest-only flags say
    so explicitly (§4.6).
    """
    coin = str(row["coin"]).capitalize()
    date = str(row["date"])[:10]
    ret = float(row["daily_return"])
    direction = "rose" if ret >= 0 else "fell"
    rz = float(row["return_z"]) if pd.notna(row["return_z"]) else float("nan")
    vr = float(row["volume_ratio"]) if pd.notna(row["volume_ratio"]) else float("nan")
    rules = str(row.get("rules_triggered", "") or "")
    if not rules:
        vol = (
            float(row["vol_30d_ann"]) if pd.notna(row["vol_30d_ann"]) else float("nan")
        )
        return (
            f"{coin} {direction} {abs(ret) * 100:.1f}% on {date} — flagged by the "
            f"Isolation Forest only (return z = {rz:.1f}, volume "
            f"{vr:.1f}x its 30-day average, 30-day volatility "
            f"{vol * 100:.0f}% annualised); no single rule crossed its "
            f"threshold, but the combination was jointly unusual."
        )
    parts = (
        f"{coin} {direction} {abs(ret) * 100:.1f}% on {date} "
        f"(return z = {rz:.1f}) while volume ran {vr:.1f}x its 30-day "
        f"average"
    )
    if "R1" in rules.split("+"):
        parts += " — a sharp price move well outside its recent range"
    elif "R2" in rules.split("+"):
        parts += " — unusually heavy trading"
    elif "R3" in rules.split("+"):
        parts += " — a moderate price move with a moderate volume surge"
    if "R3" in rules.split("+") and (
        "R1" in rules.split("+") or "R2" in rules.split("+")
    ):
        parts += " and a joint price-volume shock"
    return parts + "."


def build_timeline(featured_df: pd.DataFrame) -> pd.DataFrame:
    """Union of baseline + forest flags on the REAL data (§4.6 fields).

    One row per flagged day, sorted by date then coin. Expects a frame
    that has already been through apply_rules + fit_isolation_forest.
    """
    df = featured_df.copy()
    flagged = df[df["baseline_flagged"] | df["is_anomaly"]].copy()
    flagged["flagged_by"] = np.where(
        flagged["baseline_flagged"] & flagged["is_anomaly"],
        "both",
        np.where(flagged["baseline_flagged"], "baseline", "forest"),
    )
    # Forest-only rows carry no rule and no severity tier: severity
    # describes the rule outcome, so forest-only flags are Low.
    flagged.loc[flagged["rules_triggered"] == "", "severity"] = "Low"
    flagged["explanation"] = flagged.apply(generate_explanation, axis=1)
    cols = [
        "date",
        "coin",
        "price",
        "daily_return",
        "volume",
        "volume_ratio",
        "return_z",
        "volume_z",
        "vol_30d_ann",
        "vol_regime",
        "drawdown",
        "rules_triggered",
        "isolation_forest_score",
        "flagged_by",
        "severity",
        "explanation",
    ]
    out = flagged[cols].sort_values(["date", "coin"]).reset_index(drop=True)
    return out


def inject_anomalies(
    daily_df: pd.DataFrame, n: int = 30, seed: int = 42
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Inject ~30 known anomalies into a COPY of the daily frame (§4.4b,
    as amended 2026-11-07).

    Operates on the pre-feature frame (date, coin, price, market_cap,
    volume); the caller recomputes features on the returned copy. The
    input frame is never modified. Injections are spread across the
    three coins (10 each) and across the year (at most one per calendar
    month per coin), with 10 of each type overall. Magnitudes are
    computed from the trailing 30-day window ending the day *before*
    the injection date, per coin, on the frame under construction
    (earlier injections already applied, months processed in
    chronological order) — the same windows the detector's own
    trailing z-scores use (§4.1), so a plant's return is 4.0× / 3.0×
    the trailing std the detector will see:

    - price_spike: set ``price[t]`` so the day's simple return equals
      +4.0 × σ_ret (market cap scaled by the same factor); the next
      day's price is untouched, so the return reverses the day after.
    - volume_surge: set ``volume[t]`` = 5.0 × mean(volume[t−30 … t−1]).
      No price change.
    - joint_shock: set ``price[t]`` so the day's return equals
      +3.0 × σ_ret and ``volume[t]`` = 5.0 × mean(volume[t−30 … t−1]).

    Returns (injected copy, labels frame with date, coin, type,
    magnitude, construction). ``magnitude`` is the realised return
    (decimal) for price_spike / joint_shock and the volume multiple
    (5.0) for volume_surge; ``construction`` records how the plant was
    built (``4.0x trailing return std`` / ``5.0x trailing mean volume``
    / ``3.0x trailing return std + 5.0x trailing mean volume``).

    Harness self-check (mandatory, §4.4 amendment): after injection,
    features are recomputed on the injected frame and every plant must
    clear its target rule's bar — price spike ``|return_z| ≥ 3``;
    volume surge ``volume_z ≥ 3`` and ``volume_ratio ≥ 2``; joint
    shock ``|return_z| ≥ 2`` and ``volume_z ≥ 2``. If any plant fails,
    this raises AssertionError: a planted anomaly that is not
    anomalous relative to history is a harness bug, not a detector
    miss, and must never silently enter the evaluation.
    """
    rng = np.random.default_rng(seed)
    injected = daily_df.copy()
    labels = []
    coins = sorted(daily_df["coin"].unique())
    per_coin = n // len(coins)
    # Type counts per coin, rotated so the totals are 10 of each type.
    type_plans = {
        0: ["price_spike"] * 4 + ["volume_surge"] * 3 + ["joint_shock"] * 3,
        1: ["price_spike"] * 3 + ["volume_surge"] * 4 + ["joint_shock"] * 3,
        2: ["price_spike"] * 3 + ["volume_surge"] * 3 + ["joint_shock"] * 4,
    }
    constructions = {
        "price_spike": "4.0x trailing return std",
        "volume_surge": "5.0x trailing mean volume",
        "joint_shock": "3.0x trailing return std + 5.0x trailing mean volume",
    }
    for ci, coin in enumerate(coins):
        g = injected[injected["coin"] == coin].sort_values("date")
        positions = np.arange(len(g))
        # Eligible positions: after the 30-day warm-up, not the last day
        # (a price spike needs the following day to reverse).
        eligible = positions[(positions >= 35) & (positions <= len(g) - 2)]
        dates = pd.to_datetime(g["date"])
        # One injection per calendar month: pick per_coin distinct
        # months from the eligible range, then one random day in each.
        months = sorted({str(dates.iloc[p])[:7] for p in eligible})
        chosen_months = sorted(
            rng.choice(months, size=min(per_coin, len(months)), replace=False)
        )
        types = type_plans[ci % len(type_plans)]
        for bi, month in enumerate(chosen_months):
            in_month = [p for p in eligible if str(dates.iloc[p])[:7] == month]
            pos = int(rng.choice(in_month))
            row_idx = g.index[pos]
            date = str(g.loc[row_idx, "date"])[:10]
            kind = types[bi % len(types)]
            # Trailing 30-day window ending the day before the
            # injection, on the frame under construction (the same
            # window the detector's trailing z-scores will use).
            work = (
                injected[injected["coin"] == coin]
                .sort_values("date")
                .reset_index(drop=True)
            )
            price = work["price"].astype(float)
            volume = work["volume"].astype(float)
            daily_ret = price / price.shift(1) - 1
            sigma_ret = daily_ret.iloc[pos - WINDOW : pos].std(ddof=1)
            mean_vol = volume.iloc[pos - WINDOW : pos].mean()
            if kind == "price_spike":
                target_ret = 4.0 * sigma_ret
                new_price = float(price.iloc[pos - 1]) * (1 + target_ret)
                ratio = new_price / float(work["price"].iloc[pos])
                injected.loc[row_idx, "price"] = new_price
                injected.loc[row_idx, "market_cap"] *= ratio
                magnitude = target_ret
            elif kind == "volume_surge":
                injected.loc[row_idx, "volume"] = 5.0 * mean_vol
                magnitude = 5.0
            else:  # joint_shock
                target_ret = 3.0 * sigma_ret
                new_price = float(price.iloc[pos - 1]) * (1 + target_ret)
                ratio = new_price / float(work["price"].iloc[pos])
                injected.loc[row_idx, "price"] = new_price
                injected.loc[row_idx, "market_cap"] *= ratio
                injected.loc[row_idx, "volume"] = 5.0 * mean_vol
                magnitude = target_ret
            labels.append(
                {
                    "date": date,
                    "coin": coin,
                    "type": kind,
                    "magnitude": magnitude,
                    "construction": constructions[kind],
                }
            )
    labels_df = (
        pd.DataFrame(labels).sort_values(["date", "coin"]).reset_index(drop=True)
    )
    # Mandatory harness self-check: every plant must clear its target
    # rule's bar on the injected frame. Fails loudly otherwise.
    featured = compute_features(
        injected[["date", "coin", "price", "market_cap", "volume"]]
    )
    for _, lab in labels_df.iterrows():
        row = featured[
            (featured["coin"] == lab["coin"]) & (featured["date"] == lab["date"])
        ]
        assert (
            len(row) == 1
        ), f"injected {lab['type']} {lab['coin']} {lab['date']} not found"
        row = row.iloc[0]
        rz = row["return_z"]
        vz = row["volume_z"]
        vr = row["volume_ratio"]
        if lab["type"] == "price_spike":
            ok = pd.notna(rz) and abs(rz) >= 3
            detail = f"|return_z|={abs(rz):.2f} (bar >= 3)"
        elif lab["type"] == "volume_surge":
            ok = pd.notna(vz) and vz >= 3 and pd.notna(vr) and vr >= 2
            detail = f"volume_z={vz:.2f} (bar >= 3), volume_ratio={vr:.2f} (bar >= 2)"
        else:  # joint_shock
            ok = pd.notna(rz) and abs(rz) >= 2 and pd.notna(vz) and vz >= 2
            detail = (
                f"|return_z|={abs(rz):.2f} (bar >= 2), volume_z={vz:.2f} (bar >= 2)"
            )
        assert ok, (
            f"HARNESS BUG: injected {lab['type']} {lab['coin']} {lab['date']} "
            f"does not clear its target rule's bar on the injected frame: {detail}"
        )
    return injected, labels_df


def evaluate(
    detected_df: pd.DataFrame,
    injected_df: pd.DataFrame,
    tolerance_days: int = 1,
    clean_flags: pd.DataFrame | None = None,
) -> dict:
    """Precision / recall / F1 per method vs injected labels (±1 day).

    detected_df: a flagged frame with date, coin, baseline_flagged and
    is_anomaly columns (e.g. the injected run's run_detection output).
    A flag within tolerance_days of an injected date for the same coin
    counts as detecting that injection. Also returns per-type recall
    (union method) and the baseline-vs-forest Jaccard overlap.

    Precision rule (§4.4 amendment, 2026-11-07): a flag counts as a
    true positive if it matches (same coin, ±1 day) an injected
    anomaly OR a flag the detector also raises on the clean
    (uninjected) data — ``clean_flags`` (date, coin), the clean-run
    flag set (the committed ``anomaly_timeline.csv`` set). A flag
    counts as a false positive only if it matches neither. Precision
    is therefore TP flags ÷ all flags; recall is unchanged (matched
    injections ÷ n_injected). ``tp`` stays the matched-injection count
    (the recall numerator); ``tp_flags`` is the flag-level true
    positive count used for precision. When ``clean_flags`` is None,
    the old rule applies (any flag matching no injection is a false
    positive) so existing callers without a clean run keep working.
    """
    detected = detected_df.copy()
    detected["date"] = pd.to_datetime(detected["date"])
    injected = injected_df.copy()
    injected["date"] = pd.to_datetime(injected["date"])
    n_injected = len(injected)
    clean: list = []
    if clean_flags is not None:
        clean_df = clean_flags.copy()
        clean_df["date"] = pd.to_datetime(clean_df["date"])
        clean = [(d, c) for d, c in zip(clean_df["date"], clean_df["coin"])]

    def _matches(fd, fc, targets) -> bool:
        return any(
            fc == tc and abs((fd - td).days) <= tolerance_days for td, tc in targets
        )

    def _flags(mask: pd.Series) -> pd.DataFrame:
        return detected[mask][["date", "coin"]].drop_duplicates()

    methods = {
        "baseline": _flags(detected["baseline_flagged"]),
        "forest": _flags(detected["is_anomaly"]),
        "union": _flags(detected["baseline_flagged"] | detected["is_anomaly"]),
    }
    result: dict = {
        "n_injected": n_injected,
        "tolerance_days": tolerance_days,
        "n_clean_flags": len(clean),
    }
    # Jaccard overlap on exact dates (baseline vs forest, same run).
    base_set = {
        (str(d.date()), c)
        for d, c in zip(methods["baseline"]["date"], methods["baseline"]["coin"])
    }
    forest_set = {
        (str(d.date()), c)
        for d, c in zip(methods["forest"]["date"], methods["forest"]["coin"])
    }
    union_set = base_set | forest_set
    result["n_baseline"] = len(base_set)
    result["n_forest"] = len(forest_set)
    result["n_union"] = len(union_set)
    result["n_both"] = len(base_set & forest_set)
    result["jaccard"] = (
        len(base_set & forest_set) / len(union_set) if union_set else 0.0
    )
    injection_targets = [(d, c) for d, c in zip(injected["date"], injected["coin"])]
    for name, flags in methods.items():
        flag_list = [(d, c) for d, c in zip(flags["date"], flags["coin"])]
        matched_injections: set[int] = set()
        tp_flags = 0
        for fd, fc in flag_list:
            hit_injection = False
            for i, (td, tc) in enumerate(injection_targets):
                if fc == tc and abs((fd - td).days) <= tolerance_days:
                    matched_injections.add(i)
                    hit_injection = True
            # Amended precision rule: a flag matching an injection OR
            # a clean-data flag is a true positive; only a flag
            # matching neither is a false positive.
            if hit_injection or _matches(fd, fc, clean):
                tp_flags += 1
        tp = len(matched_injections)
        fp = len(flag_list) - tp_flags
        fn = n_injected - tp
        precision = tp_flags / (tp_flags + fp) if (tp_flags + fp) > 0 else 0.0
        recall = tp / n_injected if n_injected else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        result[name] = {
            "tp": tp,
            "tp_flags": tp_flags,
            "fp": fp,
            "fn": fn,
            "n_flags": len(flag_list),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    # Per-type recall (union method).
    union_flags = methods["union"]
    per_type: dict[str, float] = {}
    for kind, group in injected.groupby("type"):
        found = 0
        for _, inj in group.iterrows():
            near = union_flags[
                (union_flags["coin"] == inj["coin"])
                & ((union_flags["date"] - inj["date"]).abs().dt.days <= tolerance_days)
            ]
            if len(near):
                found += 1
        per_type[str(kind)] = found / len(group) if len(group) else 0.0
    result["per_type_recall"] = per_type
    return result
