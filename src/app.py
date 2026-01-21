"""
Application entry point.

This module defines a simple command‑line interface for running the
trading program in different modes (backtest, paper, live).  It
leverages the modules under `src/` to load configuration, execute
backtests, connect to MetaTrader 5 and generate reports.
"""

from __future__ import annotations

import argparse
import logging
from typing import List, Optional

from .config.schema import load_config
from .execution.backtest_exec import BacktestEngine
from .execution.mt5_exec import MT5Engine
from .reporting.report import generate_backtest_report


def _setup_logging(verbose: bool) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )


def main(argv: Optional[List[str]] = None) -> None:
    """Parse command‑line arguments and dispatch to the appropriate mode."""
    parser = argparse.ArgumentParser(description="FX Trading Program")
    parser.add_argument('mode', choices=['backtest', 'paper', 'live'], help="Operating mode")
    parser.add_argument('--config', default='config.yaml', help="Path to configuration YAML file")
    parser.add_argument('-v', '--verbose', action='store_true', help="Enable debug logging")
    args = parser.parse_args(argv)

    _setup_logging(args.verbose)

    config = load_config(args.config)
    # Override mode from CLI if provided
    config.mode = args.mode

    if args.mode == 'backtest':
        logging.info("Running backtest...")
        engine = BacktestEngine(config)
        trades, equity_curve = engine.run()
        generate_backtest_report(trades, equity_curve, out_dir='results')
        logging.info("Backtest complete. Results saved to the 'results' directory.")
    else:
        # Paper or live trading via MT5
        live_flag = args.mode == 'live'
        logging.info("Starting %s trading via MetaTrader 5...", 'live' if live_flag else 'paper')
        engine = MT5Engine(config, live=live_flag)
        engine.run()


if __name__ == '__main__':
    main()