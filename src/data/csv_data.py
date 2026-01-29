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
        file_path = self.csv_dir / f"{symbol}.csv"
        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found for symbol {symbol}: {file_path}")

        # 1) Try standard CSV format: comma-separated with 'time' column
        try:
            df_std = pd.read_csv(file_path)
            if "time" in df_std.columns:
                df_std["time"] = pd.to_datetime(df_std["time"], errors="raise")
                df_std = df_std.set_index("time").sort_index()
                if df_std.index.tz is None:
                    df_std.index = df_std.index.tz_localize(self.timezone)
                else:
                    df_std.index = df_std.index.tz_convert(self.timezone)
                return df_std
        except Exception:
            pass  # fall back to MT5 format

        # --- MT5 export format: tab-separated ---
        df = pd.read_csv(file_path, sep="\t", engine="python")
        df.columns = [c.strip() for c in df.columns]

        required = ["<DATE>", "<TIME>", "<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(
                f"Unrecognized CSV format for {symbol}. Missing columns: {missing}. "
                f"Found columns: {list(df.columns)}"
            )

        # Parse datetime
        dt = df["<DATE>"].astype(str).str.strip() + " " + df["<TIME>"].astype(str).str.strip()
        ts = pd.to_datetime(dt, format="%Y.%m.%d %H:%M:%S", errors="coerce")
        if ts.isna().any():
            ts = pd.to_datetime(dt, errors="coerce")
        if ts.isna().any():
            bad = dt[ts.isna()].head(5).tolist()
            raise ValueError(f"Could not parse MT5 DATE/TIME for {symbol}. Examples: {bad}")

        # Convert OHLC to numeric (avoid index alignment issues)
        o = pd.to_numeric(df["<OPEN>"], errors="coerce").to_numpy()
        h = pd.to_numeric(df["<HIGH>"], errors="coerce").to_numpy()
        l = pd.to_numeric(df["<LOW>"], errors="coerce").to_numpy()
        c = pd.to_numeric(df["<CLOSE>"], errors="coerce").to_numpy()

        out = pd.DataFrame(
            {"open": o, "high": h, "low": l, "close": c},
            index=pd.DatetimeIndex(ts),
        ).sort_index()

        # Drop rows with invalid OHLC
        before = len(out)
        out = out.dropna(subset=["open", "high", "low", "close"])
        after = len(out)
        if after == 0:
            raise ValueError(f"After parsing, no valid OHLC rows remain for {symbol}.")
        if after < before:
            print(f"[WARN] Dropped {before - after} rows with NaN OHLC for {symbol}")

        # Localize timestamps
        out.index = out.index.tz_localize(self.timezone)

        return out
