"""
Report generation utilities.

This module turns backtest results into human‑readable artefacts:
CSV files of trades and equity curve, a JSON summary of performance
metrics and a PNG chart of the equity curve.  Having a central place
for report generation makes it easy to extend the output formats in
future (e.g. HTML reports).
"""

from __future__ import annotations

import os
import json
from typing import List
import pandas as pd
import matplotlib

# Use non‑interactive backend for environments without display
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ..execution.models import Trade
from ..execution.backtest_exec import EquityPoint
from .metrics import compute_metrics


def generate_backtest_report(
    trades: List[Trade],
    equity_curve: List[EquityPoint],
    out_dir: str = "results",
) -> None:
    """Generate report files for a backtest run.

    Creates the output directory if it does not exist and writes the
    following files:

    - `trades.csv` – detailed list of trades
    - `equity_curve.csv` – account equity after each trade
    - `summary.json` – performance metrics
    - `equity_curve.png` – line chart of the equity curve
    """
    os.makedirs(out_dir, exist_ok=True)

    # Trades CSV
    trades_data = [
        {
            'timestamp_entry': t.entry_time.isoformat(),
            'timestamp_exit': t.exit_time.isoformat(),
            'symbol': t.symbol,
            'side': t.side,
            'volume': t.volume,
            'entry': t.entry_price,
            'exit': t.exit_price,
            'pnl': t.pnl,
            'fees': t.fees,
            'reason': t.reason,
        }
        for t in trades
    ]
    df_trades = pd.DataFrame(trades_data)
    trades_path = os.path.join(out_dir, 'trades.csv')
    df_trades.to_csv(trades_path, index=False)

    # Equity curve CSV
    eq_data = [
        {
            'timestamp': pt.timestamp.isoformat(),
            'equity': pt.equity,
        }
        for pt in equity_curve
    ]
    df_eq = pd.DataFrame(eq_data)
    eq_path = os.path.join(out_dir, 'equity_curve.csv')
    df_eq.to_csv(eq_path, index=False)

    # Summary JSON
    metrics = compute_metrics(trades, equity_curve)
    summary_path = os.path.join(out_dir, 'summary.json')
    with open(summary_path, 'w', encoding='utf-8') as fh:
        json.dump(metrics, fh, indent=2, ensure_ascii=False)

    # Equity curve plot
    fig, ax = plt.subplots(figsize=(10, 4))
    if not df_eq.empty:
        ax.plot(pd.to_datetime(df_eq['timestamp']), df_eq['equity'], linewidth=1.5)
        ax.set_title('Equity Curve')
        ax.set_xlabel('Time')
        ax.set_ylabel('Equity')
        fig.autofmt_xdate()
    fig.tight_layout()
    plot_path = os.path.join(out_dir, 'equity_curve.png')
    fig.savefig(plot_path)
    plt.close(fig)