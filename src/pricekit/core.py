"""Small, dependency-free price and risk calculations.

Everything here is a pure function: same input, same output, no I/O.
That is deliberate — pure functions are trivial to test, and a fast,
deterministic test suite is what makes CI pleasant instead of annoying.
"""

from __future__ import annotations

from collections.abc import Sequence


def sma(values: Sequence[float], window: int) -> list[float]:
    """Simple moving average.

    Returns one value per full window, so the output is
    ``len(values) - window + 1`` items long.
    """
    if window <= 0:
        raise ValueError("window must be positive")
    if window > len(values):
        raise ValueError("window is longer than the series")

    out: list[float] = []
    running = sum(values[:window])
    out.append(running / window)
    for i in range(window, len(values)):
        running += values[i] - values[i - window]
        out.append(running / window)
    return out


def returns(prices: Sequence[float]) -> list[float]:
    """Simple period-over-period returns as decimals (0.01 == 1%)."""
    if len(prices) < 2:
        raise ValueError("need at least two prices")
    if any(p <= 0 for p in prices):
        raise ValueError("prices must be positive")

    return [(prices[i] / prices[i - 1]) - 1.0 for i in range(1, len(prices))]


def max_drawdown(equity: Sequence[float]) -> float:
    """Largest peak-to-trough decline, as a positive decimal.

    A flat or monotonically rising curve has a drawdown of 0.0.
    """
    if not equity:
        raise ValueError("equity curve is empty")

    peak = equity[0]
    worst = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak > 0:
            decline = (peak - value) / peak
            worst = max(worst, decline)
    return worst


def position_size(
    account_equity: float,
    risk_pct: float,
    entry: float,
    stop: float,
) -> int:
    """Whole-share size such that a stop-out costs about ``risk_pct`` of equity.

    ``risk_pct`` is a decimal: 0.01 means one percent.
    """
    if account_equity <= 0:
        raise ValueError("account_equity must be positive")
    if not 0 < risk_pct < 1:
        raise ValueError("risk_pct must be between 0 and 1")
    if entry <= 0 or stop <= 0:
        raise ValueError("entry and stop must be positive")
    if entry == stop:
        raise ValueError("entry and stop must differ")

    risk_per_share = abs(entry - stop)
    return int(account_equity * risk_pct // risk_per_share)


def summarize(prices: Sequence[float]) -> dict[str, float]:
    """Roll the whole module up into one report dictionary."""
    rets = returns(prices)
    return {
        "count": float(len(prices)),
        "first": float(prices[0]),
        "last": float(prices[-1]),
        "total_return": (prices[-1] / prices[0]) - 1.0,
        "best_period": max(rets),
        "worst_period": min(rets),
        "max_drawdown": max_drawdown(prices),
    }
