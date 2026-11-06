"""Day 2 — Crypto Risk & Volatility Analyzer: pure metric functions.

No I/O, no network. Every function takes plain Series / DataFrames and
returns plain values, so the notebook and the Streamlit app import them
instead of re-implementing them.

Conventions (plan.md §4, copied verbatim from the research brief):
- Simple (arithmetic) daily returns, never log returns.
- Annualisation x sqrt(365) (crypto trades every day), never sqrt(252).
- Risk-free rate 0% for Sharpe / Sortino.
- VaR / CVaR are one-day historical figures on daily returns:
  VaR 95% = 5th percentile, CVaR 95% = mean of returns <= VaR.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

ANNUALISATION = np.sqrt(365)
WINDOW = 30


def daily_returns(prices: pd.Series) -> pd.Series:
    """Simple daily returns r_t = price_t / price_{t-1} - 1.

    First element is NaN (no prior day). Index is preserved.
    """
    prices = pd.Series(prices, dtype=float)
    return prices / prices.shift(1) - 1


def drawdown_series(prices: pd.Series) -> pd.Series:
    """Drawdown dd_t = price_t / running_max(price_0..price_t) - 1 (<= 0)."""
    prices = pd.Series(prices, dtype=float)
    running_max = prices.cummax()
    return prices / running_max - 1


def max_drawdown_info(prices: pd.Series, dates: pd.Series) -> dict:
    """Max-drawdown episode for one coin.

    Returns max drawdown, peak / trough dates and prices, peak-to-trough
    days, recovery days (days from trough until the price first closes at
    or above the peak price again; None when it never recovers within the
    window), recovery status, and the longest underwater period (longest
    run of consecutive days with drawdown < 0).
    """
    prices = pd.Series(prices, dtype=float).reset_index(drop=True)
    dates = pd.to_datetime(pd.Series(dates).reset_index(drop=True))
    dd = drawdown_series(prices)
    trough_idx = int(dd.idxmin())
    peak_price = float(prices.cummax().iloc[trough_idx])
    peak_idx = int(prices.iloc[: trough_idx + 1].idxmax())
    trough_price = float(prices.iloc[trough_idx])
    peak_date = dates.iloc[peak_idx]
    trough_date = dates.iloc[trough_idx]
    peak_to_trough_days = int((trough_date - peak_date).days)

    after = prices.iloc[trough_idx + 1 :]
    recovered = after[after >= peak_price]
    if len(recovered):
        # Index was reset above, so the label is the position.
        recovery_date = dates.iloc[int(recovered.index[0])]
        recovery_days = int((recovery_date - trough_date).days)
        recovered_by_end = True
    else:
        recovery_days = int((dates.iloc[-1] - trough_date).days)
        recovered_by_end = False

    # Longest run of consecutive days with dd < 0.
    underwater = (dd < 0).astype(int)
    longest = 0
    current = 0
    for value in underwater:
        current = current + 1 if value else 0
        longest = max(longest, current)

    return {
        "max_drawdown": float(dd.iloc[trough_idx]),
        "peak_date": peak_date.strftime("%Y-%m-%d"),
        "peak_price": peak_price,
        "trough_date": trough_date.strftime("%Y-%m-%d"),
        "trough_price": trough_price,
        "peak_to_trough_days": peak_to_trough_days,
        "recovery_days": recovery_days,
        "recovered_by_end": recovered_by_end,
        "longest_underwater_days": int(longest),
    }


def rolling_volatility(returns: pd.Series, window: int = WINDOW) -> pd.Series:
    """Rolling annualised volatility: std(r_{t-window+1}..r_t) x sqrt(365).

    Sample standard deviation (ddof=1, pandas default). The first
    window - 1 values are NaN (a 30-day window needs 30 returns).
    """
    returns = pd.Series(returns, dtype=float)
    return returns.rolling(window).std(ddof=1) * ANNUALISATION


def return_correlations(returns_df: pd.DataFrame) -> dict:
    """Pairwise Pearson correlations of daily returns.

    ``returns_df`` is a date-indexed frame with one column per coin.
    Returns the 3x3 full-window matrix (as a DataFrame) and the three
    latest-90-day pairwise values (returns on the last 90 calendar days
    of the window).
    """
    full = returns_df.corr()
    latest = returns_df.tail(90).corr()
    coins = list(returns_df.columns)
    pairs: dict[str, float] = {}
    for i, a in enumerate(coins):
        for b in coins[i + 1 :]:
            pairs[f"{a}-{b}"] = float(latest.loc[a, b])
    return {"full": full, "latest_90d": pairs}


def sharpe_ratio(returns: pd.Series) -> float:
    """Annualised Sharpe = mean(r) / std(r) x sqrt(365), risk-free rate 0%."""
    returns = pd.Series(returns, dtype=float).dropna()
    if len(returns) == 0 or returns.std(ddof=1) == 0:
        return float("nan")
    return float(returns.mean() / returns.std(ddof=1) * ANNUALISATION)


def sortino_ratio(returns: pd.Series) -> float:
    """Annualised Sortino = mean(r) / downside_deviation x sqrt(365).

    Downside deviation = sqrt(mean(min(r_t, 0)^2)) over the full window
    (target / minimum acceptable return = 0). Risk-free rate 0%.
    """
    returns = pd.Series(returns, dtype=float).dropna()
    if len(returns) == 0:
        return float("nan")
    downside = np.sqrt(np.mean(np.minimum(returns.to_numpy(), 0.0) ** 2))
    if downside == 0:
        return float("nan")
    return float(returns.mean() / downside * ANNUALISATION)


def var_cvar_95(returns: pd.Series) -> dict[str, float]:
    """Historical one-day VaR 95% and CVaR 95% on daily returns.

    VaR 95% = 5th percentile of daily returns (linear interpolation,
    numpy/pandas default). CVaR 95% = mean of daily returns at or below
    VaR. CVaR is always <= VaR.
    """
    returns = pd.Series(returns, dtype=float).dropna()
    var = float(np.percentile(returns.to_numpy(), 5))
    tail = returns[returns <= var]
    cvar = float(tail.mean()) if len(tail) else float("nan")
    return {"var_95": var, "cvar_95": cvar}
