# file: src/strategy/intraday_breakout.py
"""
Intraday breakout strategy implementation.

This strategy tracks the highest high and lowest low of each trading
day and opens a long or short position when the current bar’s high or
low breaks those levels. It does not open both directions at the
same time and honours a configured trading session window.

IMPORTANT TIME ASSUMPTION (MT5 CSV):
- MT5 CSV timestamps for H1 candles are typically BAR OPEN times.
- The strategy spec requires evaluating signals at BAR CLOSE.
- Therefore, this strategy converts bar-open timestamps to bar-close
  timestamps by adding 1 hour before applying session filtering and
  day boundary logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import pandas as pd

from ..config.schema import Config
from ..utils.timeutils import is_in_session, parse_time_str


@dataclass
class IntradayState:
    """Holds intraday high/low levels and the current trading day date."""
    high: Optional[float] = None
    low: Optional[float] = None
    current_date: Optional[object] = None  # date


class IntradayBreakoutStrategy:
    """Intraday breakout strategy logic."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.session_start = parse_time_str(config.session.start)
        self.session_end = parse_time_str(config.session.end)

    def evaluate_bar(
        self,
        ts: pd.Timestamp,
        bar: pd.Series,
        state: IntradayState,
    ) -> Tuple[Optional[str], IntradayState]:
        """
        Evaluate a single completed H1 bar and update the intraday state.

        Parameters
        ----------
        ts : pandas.Timestamp
            Timestamp for the bar. For MT5 CSV exports this is typically the
            BAR OPEN time (start of the candle).
        bar : pandas.Series
            Row containing `open`, `high`, `low`, `close`.
        state : IntradayState
            Previous intraday high/low and current_date.

        Returns
        -------
        signal : str or None
            'long' to enter a long position, 'short' to enter a short
            position, or None if no trade should be taken.
        state : IntradayState
            Updated intraday state for subsequent bars.
        """
        # Convert BAR OPEN timestamp → BAR CLOSE timestamp (H1)
        bar_close_ts = ts + pd.Timedelta(hours=1)
        # ================= DEBUG START =================
        #print("DBG ts(open) =", ts)
        #print("DBG ts(close)=", bar_close_ts, "hour=", bar_close_ts.hour)
        #print("DBG bar keys =", list(bar.index))
        #print(
        #    "DBG bar high/low =",
        #    bar.get("high"),
        #    bar.get("low"),
        #    "| state high/low =",
        #    state.high,
        #    state.low,
        #)
        # ================= DEBUG END =================

        # Reset intraday levels if we are on a new day (based on Brussels time)
        local_date = bar_close_ts.tz_convert(self.config.data.timezone).date()
        if state.current_date != local_date:
            state.high = None
            state.low = None
            state.current_date = local_date

        # Evaluate signals using levels from previous bars (no lookahead)
        long_signal = False
        short_signal = False

        if state.high is not None and float(bar["high"]) > float(state.high):
            long_signal = True
        if state.low is not None and float(bar["low"]) < float(state.low):
            short_signal = True

        # Decide on signal (skip if both triggers)
        signal: Optional[str] = None
        if long_signal and not short_signal:
            signal = "long"
        elif short_signal and not long_signal:
            signal = "short"

        # Update intraday high and low with current bar AFTER evaluation
        if state.high is None or float(bar["high"]) > float(state.high):
            state.high = float(bar["high"])
        if state.low is None or float(bar["low"]) < float(state.low):
            state.low = float(bar["low"])

        # Only allow trades within the session window (based on bar close time)
        if not is_in_session(
            bar_close_ts,
            self.session_start,
            self.session_end,
            self.config.data.timezone,
        ):
            signal = None

        return signal, state
