"""
Backtest execution engine.

This module contains the `BacktestEngine` class which orchestrates
loading historical data, iterating over bars, generating trading
signals, executing simulated trades with slippage and spread, and
recording performance.  The engine supports multiple symbols; it
processes each symbol independently and aggregates the results.
"""

from __future__ import annotations

from typing import List, Tuple, Optional
from dataclasses import dataclass
import pandas as pd

from ..config.schema import Config
from ..data.csv_data import CSVDataLoader
from ..strategy.intraday_breakout import IntradayBreakoutStrategy, IntradayState
from ..execution.models import Position, Trade


@dataclass
class EquityPoint:
    """Represents the account equity at a given timestamp."""
    timestamp: pd.Timestamp
    equity: float


class BacktestEngine:
    """Run backtests on historical data loaded from CSV files."""

    def __init__(self, config: Config, initial_equity: float = 100_000.0) -> None:
        self.config = config
        self.initial_equity = initial_equity
        self.data_loader = CSVDataLoader(config.data.csv_dir, config.data.timezone)
        self.strategy = IntradayBreakoutStrategy(config)

    def _compute_fees(self, volume: float) -> float:
        """Compute commission fees based on volume and configuration."""
        return self.config.costs.commission_per_lot * volume

    def run(self) -> Tuple[List[Trade], List[EquityPoint]]:
        """Execute the backtest across all configured symbols.

        Returns
        -------
        trades : list of Trade
            Completed trades including P&L and fees.
        equity_curve : list of EquityPoint
            Equity after each trade for plotting and metrics.
        """
        equity = self.initial_equity
        trades: List[Trade] = []
        equity_curve: List[EquityPoint] = []

        for symbol in self.config.symbols:
            # Load historical data for this symbol
            df = self.data_loader.load(symbol)
            # Need at least two bars to trade (current and next for entry)
            if len(df) < 2:
                continue
            # Initialise per‑symbol state
            state = IntradayState()
            position: Optional[Position] = None
            # Iterate through bars except the last one (since we need next bar’s open for entry)
            for idx in range(len(df) - 1):
                ts = df.index[idx]
                bar = df.iloc[idx]
                next_ts = df.index[idx + 1]
                next_bar = df.iloc[idx + 1]

                # If we have an open position, check for exit conditions on the current bar
                if position is not None:
                    exit_signal: Optional[str] = None
                    exit_base_price: float = 0.0
                    if position.side == 'long':
                        if bar['low'] <= position.sl_price:
                            exit_signal = 'sl'
                            exit_base_price = position.sl_price
                        elif bar['high'] >= position.tp_price:
                            exit_signal = 'tp'
                            exit_base_price = position.tp_price
                    elif position.side == 'short':
                        if bar['high'] >= position.sl_price:
                            exit_signal = 'sl'
                            exit_base_price = position.sl_price
                        elif bar['low'] <= position.tp_price:
                            exit_signal = 'tp'
                            exit_base_price = position.tp_price
                    # If exit triggered, close at the base price adjusted for spread and slippage
                    if exit_signal is not None:
                        half_spread = self.config.costs.spread / 2
                        slippage = self.config.costs.slippage
                        if position.side == 'long':
                            # Sell at bid: subtract half spread and slippage
                            exit_price = exit_base_price - half_spread - slippage
                            pnl = (exit_price - position.entry_price) * position.volume
                        else:
                            # Buy at ask: add half spread and slippage
                            exit_price = exit_base_price + half_spread + slippage
                            pnl = (position.entry_price - exit_price) * position.volume
                        fees = self._compute_fees(position.volume)
                        equity += pnl - fees
                        trade = Trade(
                            symbol=position.symbol,
                            side=position.side,
                            volume=position.volume,
                            entry_price=position.entry_price,
                            exit_price=exit_price,
                            entry_time=position.entry_time,
                            exit_time=ts,
                            pnl=pnl,
                            fees=fees,
                            reason=exit_signal,
                        )
                        trades.append(trade)
                        equity_curve.append(EquityPoint(timestamp=ts, equity=equity))
                        position = None

                # If no open position, evaluate for new entry
                if position is None:
                    signal, state = self.strategy.evaluate_bar(ts, bar, state)
                    if signal:
                        # Determine entry price at next bar open with spread and slippage
                        open_price = next_bar['open']
                        half_spread = self.config.costs.spread / 2
                        slippage = self.config.costs.slippage
                        if signal == 'long':
                            entry_price = open_price + half_spread + slippage
                            sl_price = entry_price * (1.0 - self.config.sl_pct)
                            tp_price = entry_price * (1.0 + self.config.tp_pct)
                        else:  # short
                            entry_price = open_price - half_spread - slippage
                            sl_price = entry_price * (1.0 + self.config.sl_pct)
                            tp_price = entry_price * (1.0 - self.config.tp_pct)
                        # Calculate volume in units (approximate one unit per quote currency)
                        volume = (equity * self.config.equity_pct_per_trade) / open_price
                        # Record new position
                        position = Position(
                            symbol=symbol,
                            side=signal,
                            volume=volume,
                            entry_price=entry_price,
                            sl_price=sl_price,
                            tp_price=tp_price,
                            entry_time=next_ts,
                        )
        return trades, equity_curve