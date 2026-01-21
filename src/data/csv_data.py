"""
CSV data loader.

This module provides a class to load historical OHLCV data from CSV
files.  The expected schema for each CSV is:

```
time,open,high,low,close,tick_volume,spread
```

Only the `time`, `open`, `high`, `low` and `close` columns are
required.  Additional columns are ignored.  The `time` column
should contain ISO‑formatted timestamps or UNIX epochs.  Timestamps
will be converted to the timezone specified in the configuration.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from ..utils.timeutils import to_timezone


class CSVDataLoader:
    """Load OHLCV data from CSV files for backtesting.

    Parameters
    ----------
    csv_dir : str
        Directory where the CSV files are located.  Each symbol’s file
        must be named `{SYMBOL}.csv`.
    timezone : str
        IANA timezone name used to localise timestamps.
    """

    def __init__(self, csv_dir: str, timezone: str) -> None:
        self.csv_dir = Path(csv_dir)
        self.timezone = timezone

    def load(self, symbol: str) -> pd.DataFrame:
        """Load historical data for the given symbol.

        Returns
        -------
        pandas.DataFrame
            DataFrame indexed by timezone‑aware `Timestamp` with
            columns `open`, `high`, `low`, `close`.  Any extra
            columns in the CSV are preserved, but may be ignored by
            the strategy.
        """
        file_path = self.csv_dir / f"{symbol}.csv"
        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found for symbol {symbol}: {file_path}")

        df = pd.read_csv(file_path, parse_dates=['time'])
        # Ensure required columns are present
        for col in ['open', 'high', 'low', 'close']:
            if col not in df.columns:
                raise ValueError(f"CSV for {symbol} is missing required column '{col}'")

        df = df.set_index('time').sort_index()

        # Localise timestamps: if naive, interpret as timezone specified in config
        if df.index.tzinfo is None or df.index.tz is None:
            df.index = df.index.tz_localize(self.timezone)
        else:
            df.index = df.index.tz_convert(self.timezone)

        return df