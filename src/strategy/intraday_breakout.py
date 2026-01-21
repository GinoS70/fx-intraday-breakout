"""
Intraday breakout strategy implementation.

This strategy tracks the highest high and lowest low of each trading
day and opens a long or short position when the current bar’s high or
low breaks those levels.  It does not open both directions at the
same time and honours a configured trading session window.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
import pandas as pd

from ..config.schema import Config
from ..utils.timeutils import parse_time_str, is_in_session


@dataclass
class IntradayState:
    """Holds intraday high/low levels and last processed date."""
    high: Optional[float] = None
    low: Optional[float] = None
    current_date: Optional[pd.Timestamp.date] = None


class IntradayBreakoutStrategy:
    """Generate trading signals based on intraday breakout logic."""

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
        """Evaluate a single bar and update the intraday state.

        Parameters
        ----------
        ts : pandas.Timestamp
            The timestamp of the bar (bar close).
        bar : pandas.Series
            A row containing `open`, `high`, `low`, `close`.
        state : IntradayState
            Previous intraday high/low and date.

        Returns
        -------
        signal : str or None
            `'long'` to enter a long position, `'short'` for a short,
            or `None` if no trade should be taken.
        state : IntradayState
            Updated intraday state for subsequent bars.
        """
        # Reset intraday levels if we are on a new day
        local_date = ts.tz_convert(self.config.data.timezone).date()
        if state.current_date != local_date:
            state.high = None
            state.low = None
            state.current_date = local_date

        # Evaluate signals using levels from previous bars
        long_signal = False
        short_signal = False
        if state.high is not None and bar['high'] > state.high:
            long_signal = True
        if state.low is not None and bar['low'] < state.low:
            short_signal = True
        # Decide on signal (skip if both triggers)
        signal: Optional[str] = None
        if long_signal and not short_signal:
            signal = 'long'
        elif short_signal and not long_signal:
            signal = 'short'

        # Update intraday high and low with current bar
        if state.high is None or bar['high'] > state.high:
            state.high = float(bar['high'])
        if state.low is None or bar['low'] < state.low:
            state.low = float(bar['low'])

        # Only allow trades within the session window
        if not is_in_session(ts, self.session_start, self.session_end, self.config.data.timezone):
            signal = None

        return signal, state