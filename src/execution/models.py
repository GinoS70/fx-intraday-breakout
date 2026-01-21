"""
Order, position and trade models.

These dataclasses represent the objects passed between the strategy
and execution engines.  Keeping them in a separate module improves
readability and makes unit testing easier.
"""

from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass
class Position:
    """Represents an open position on a given symbol."""
    symbol: str
    side: str  # 'long' or 'short'
    volume: float
    entry_price: float
    sl_price: float
    tp_price: float
    entry_time: pd.Timestamp


@dataclass
class Trade:
    """Represents a completed trade."""
    symbol: str
    side: str
    volume: float
    entry_price: float
    exit_price: float
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    pnl: float
    fees: float
    reason: str  # 'tp' or 'sl'