"""
MetaTrader 5 data feed.

This module wraps the `MetaTrader5` Python package to fetch historical
rates for live and paper trading.  If the package is not installed
or initialisation fails, the code raises a clear exception.  Users
can skip installing MetaTrader5 when running offline backtests.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
import pandas as pd

from ..config.schema import MT5Config

# Attempt to import MetaTrader5.  If unavailable, mt5 will be None.
try:
    import MetaTrader5 as mt5  # type: ignore
except ImportError:
    mt5 = None  # Will be checked at runtime


class MT5DataFeed:
    """Handle connection to MetaTrader 5 and retrieval of rates."""

    def __init__(self, config: MT5Config, timezone: str, timeframe: str = "H1") -> None:
        self.config = config
        self.timezone = timezone
        self.timeframe = timeframe
        self._connected = False

    def connect(self) -> None:
        """Initialise the MetaTrader 5 terminal.

        Raises
        ------
        RuntimeError
            If the MetaTrader5 package is not installed or initialisation fails.
        """
        if mt5 is None:
            raise RuntimeError(
                "MetaTrader5 package is not installed.  Install it with 'pip install MetaTrader5' to use paper or live trading."
            )
        # Initialise
        if not mt5.initialize(path=self.config.path, login=self.config.login, password=self.config.password, server=self.config.server):
            raise RuntimeError(f"MT5 initialisation failed: {mt5.last_error()}")
        self._connected = True

    def shutdown(self) -> None:
        """Shutdown the MT5 connection if it was opened."""
        if mt5 and self._connected:
            mt5.shutdown()
            self._connected = False

    def _get_mt5_timeframe(self) -> int:
        """Map a timeframe string to the MetaTrader5 timeframe constant."""
        if mt5 is None:
            raise RuntimeError("MetaTrader5 package is not installed.")
        timeframe_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1,
        }
        tf = timeframe_map.get(self.timeframe.upper())
        if tf is None:
            raise ValueError(f"Unsupported timeframe for MT5: {self.timeframe}")
        return tf

    def get_rates(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Retrieve historical rates between `start` and `end`.

        Parameters
        ----------
        symbol : str
            Instrument symbol (e.g. ``"EURUSD"``).
        start, end : datetime
            Start and end datetimes in UTC.  Returned DataFrame is
            index‑aware in the configured timezone.

        Returns
        -------
        pandas.DataFrame
            DataFrame with columns ``open``, ``high``, ``low``, ``close`` and
            index of timezone‑aware ``Timestamp``.
        """
        if not self._connected:
            raise RuntimeError("MT5DataFeed is not connected.  Call connect() before requesting data.")
        tf = self._get_mt5_timeframe()
        utc_from = start
        utc_to = end
        rates = mt5.copy_rates_range(symbol, tf, utc_from, utc_to)
        if rates is None or len(rates) == 0:
            return pd.DataFrame()
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
        df = df.rename(columns={'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close'})
        df = df.set_index('time').sort_index()
        # Convert to configured timezone
        df.index = df.index.tz_convert(self.timezone)
        return df[['open', 'high', 'low', 'close']]