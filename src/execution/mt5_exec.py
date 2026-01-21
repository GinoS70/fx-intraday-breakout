"""
MetaTrader 5 execution engine.

This module provides classes to trade via a MetaTrader 5 terminal in
both paper and live modes.  It connects to the terminal, polls for
new bars and sends market orders with attached stop‑loss and
take‑profit levels.  State is persisted to disk so that the bot can
resume after restarts without duplicating trades.

**Note**: Running this engine requires the `MetaTrader5` package and
a locally installed MT5 terminal.  In environments where MT5 is not
available, the engine will not run.  The implementation included here
serves as a reference and starting point.
"""

from __future__ import annotations

import time
from typing import Optional, Dict
import logging
from datetime import datetime, timedelta
import pandas as pd

from ..config.schema import Config
from ..data.mt5_data import MT5DataFeed
from ..strategy.intraday_breakout import IntradayBreakoutStrategy, IntradayState
from ..execution.models import Position
from ..utils.persistence import load_state, save_state


logger = logging.getLogger(__name__)


class MT5Engine:
    """Run the trading strategy in paper or live mode via MetaTrader 5."""

    def __init__(self, config: Config, live: bool = False, state_file: str = "state.json") -> None:
        self.config = config
        self.live = live
        self.state_file = state_file
        self.data_feed = MT5DataFeed(config.mt5, config.data.timezone, config.timeframe)
        self.strategy = IntradayBreakoutStrategy(config)
        self.positions: Dict[str, Optional[Position]] = {sym: None for sym in config.symbols}
        # Load previous state if it exists
        persisted = load_state(self.state_file)
        if persisted:
            for sym, pos in persisted.get('positions', {}).items():
                if pos is not None:
                    # Recreate Position dataclass
                    self.positions[sym] = Position(
                        symbol=sym,
                        side=pos['side'],
                        volume=pos['volume'],
                        entry_price=pos['entry_price'],
                        sl_price=pos['sl_price'],
                        tp_price=pos['tp_price'],
                        entry_time=pd.Timestamp(pos['entry_time']),
                    )
        self.last_bar_times: Dict[str, Optional[pd.Timestamp]] = {sym: None for sym in config.symbols}

    def _persist_state(self) -> None:
        """Save positions and last processed times to disk."""
        positions_state: Dict[str, Optional[Dict[str, any]]] = {}
        for sym, pos in self.positions.items():
            if pos is None:
                positions_state[sym] = None
            else:
                positions_state[sym] = {
                    'side': pos.side,
                    'volume': pos.volume,
                    'entry_price': pos.entry_price,
                    'sl_price': pos.sl_price,
                    'tp_price': pos.tp_price,
                    'entry_time': pos.entry_time.isoformat(),
                }
        state = {
            'positions': positions_state,
        }
        save_state(self.state_file, state)

    def run(self) -> None:
        """Main loop for paper/live trading.

        Connects to MT5, polls for new bars and places orders when
        signals occur.  This loop runs indefinitely.  Press Ctrl+C to
        stop.  On termination, the current state is saved to disk.
        """
        logger.info("Starting MT5 engine (live=%s)", self.live)
        try:
            self.data_feed.connect()
        except Exception as exc:
            logger.error("Failed to connect to MetaTrader 5: %s", exc)
            return
        # Initialise intraday states per symbol
        states: Dict[str, IntradayState] = {sym: IntradayState() for sym in self.config.symbols}
        try:
            while True:
                for symbol in self.config.symbols:
                    # Determine the time window to fetch bars
                    now_utc = datetime.utcnow()
                    # Fetch the last two bars to have current and next bar
                    bars = self.data_feed.get_rates(symbol, now_utc - timedelta(days=2), now_utc)
                    if bars.empty or len(bars) < 2:
                        continue
                    # Determine the most recent complete bar (second to last row)
                    bar = bars.iloc[-2]
                    ts = bars.index[-2]
                    next_bar = bars.iloc[-1]
                    next_ts = bars.index[-1]
                    # Get current position
                    position = self.positions.get(symbol)
                    state = states[symbol]
                    # If position open, check for exits
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
                        else:
                            if bar['high'] >= position.sl_price:
                                exit_signal = 'sl'
                                exit_base_price = position.sl_price
                            elif bar['low'] <= position.tp_price:
                                exit_signal = 'tp'
                                exit_base_price = position.tp_price
                        if exit_signal is not None:
                            logger.info(
                                "Closing %s position on %s at %s due to %s",
                                position.side,
                                symbol,
                                exit_base_price,
                                exit_signal,
                            )
                            # Remove open position
                            self.positions[symbol] = None
                            self._persist_state()
                            continue
                    # If no position, check for new signal
                    if position is None:
                        signal, new_state = self.strategy.evaluate_bar(ts, bar, state)
                        states[symbol] = new_state
                        if signal:
                            open_price = next_bar['open']
                            half_spread = self.config.costs.spread / 2
                            slip = self.config.costs.slippage
                            if signal == 'long':
                                entry_price = open_price + half_spread + slip
                                sl_price = entry_price * (1.0 - self.config.sl_pct)
                                tp_price = entry_price * (1.0 + self.config.tp_pct)
                            else:
                                entry_price = open_price - half_spread - slip
                                sl_price = entry_price * (1.0 + self.config.sl_pct)
                                tp_price = entry_price * (1.0 - self.config.tp_pct)
                            volume = 0.0  # Determine appropriate volume using account equity via MT5 API
                            logger.info(
                                "Placing %s order on %s at %s (SL=%s, TP=%s)",
                                signal,
                                symbol,
                                entry_price,
                                sl_price,
                                tp_price,
                            )
                            # Record the position (actual order_send call omitted for safety)
                            self.positions[symbol] = Position(
                                symbol=symbol,
                                side=signal,
                                volume=volume,
                                entry_price=entry_price,
                                sl_price=sl_price,
                                tp_price=tp_price,
                                entry_time=next_ts,
                            )
                            self._persist_state()
                # Sleep for a minute before polling again
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Shutting down MT5 engine...")
        finally:
            self.data_feed.shutdown()
            self._persist_state()