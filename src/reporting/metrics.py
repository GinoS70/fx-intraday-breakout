"""
Performance metrics calculations.

This module provides helpers to compute common performance statistics
from a list of trades and an equity curve.  These metrics are used
both for backtesting reports and for monitoring live trading
performance.
"""

from __future__ import annotations

from typing import List, Tuple
import math

from ..execution.models import Trade
from ..execution.backtest_exec import EquityPoint


def compute_metrics(trades: List[Trade], equity_curve: List[EquityPoint]) -> dict:
    """Compute a set of summary statistics for the backtest.

    Parameters
    ----------
    trades : list of Trade
        Completed trades containing P&L and fee information.
    equity_curve : list of EquityPoint
        Timestamped equity values after each trade.

    Returns
    -------
    dict
        Dictionary of performance metrics.
    """
    if not equity_curve:
        return {
            'total_return': 0.0,
            'max_drawdown': 0.0,
            'sharpe': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'avg_trade': 0.0,
            'exposure_time': 0.0,
            'num_trades': 0,
        }

    starting_equity = equity_curve[0].equity if equity_curve else 0.0
    ending_equity = equity_curve[-1].equity
    total_return = (ending_equity - starting_equity) / starting_equity if starting_equity else 0.0

    # Compute drawdown
    max_equity = starting_equity
    max_drawdown = 0.0
    for point in equity_curve:
        if point.equity > max_equity:
            max_equity = point.equity
        drawdown = (max_equity - point.equity) / max_equity if max_equity else 0.0
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    # Compute trade returns and Sharpe ratio
    returns: List[float] = []
    for trade in trades:
        notional = trade.entry_price * trade.volume
        if notional != 0:
            returns.append(trade.pnl / notional)
    if returns:
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        sharpe = (mean_ret / std_dev) * math.sqrt(len(returns)) if std_dev > 0 else 0.0
    else:
        sharpe = 0.0

    # Win rate and profit factor
    wins = [t.pnl for t in trades if t.pnl > 0]
    losses = [t.pnl for t in trades if t.pnl < 0]
    win_rate = len(wins) / len(trades) if trades else 0.0
    gross_profit = sum(wins)
    gross_loss = -sum(losses) if losses else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

    avg_trade = sum(t.pnl for t in trades) / len(trades) if trades else 0.0

    # Exposure time: not implemented in backtest; set to 0.0 as placeholder
    exposure_time = 0.0

    return {
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'sharpe': sharpe,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'avg_trade': avg_trade,
        'exposure_time': exposure_time,
        'num_trades': len(trades),
    }