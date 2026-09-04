"""pricekit - a tiny package that exists to give CI something real to do."""

from pricekit.core import (
    max_drawdown,
    position_size,
    returns,
    sma,
    summarize,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "max_drawdown",
    "position_size",
    "returns",
    "sma",
    "summarize",
]
