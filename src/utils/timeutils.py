"""
Timezone and trading session utilities.

This module centralises all timezone handling and session calculations.
The trading engine uses these helpers to determine when a new trading
day begins and whether the current bar falls within the permitted
trading session.
"""

from __future__ import annotations

from datetime import time
from typing import Optional
import pandas as pd


def parse_time_str(ts: str) -> time:
    """Parse a `HH:MM` string into a `datetime.time` object.

    Parameters
    ----------
    ts : str
        A string in 24‑hour format such as ``"06:30"``.

    Returns
    -------
    datetime.time
        The corresponding time.
    """
    hour, minute = map(int, ts.split(":"))
    return time(hour=hour, minute=minute)


def to_timezone(ts: pd.Timestamp, tz_name: str) -> pd.Timestamp:
    """Convert a `pandas.Timestamp` to the specified timezone.

    If the timestamp is naive, it is assumed to be in UTC before
    conversion.  If it already has a timezone, it will be converted.
    """
    if not isinstance(ts, pd.Timestamp):
        ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert(tz_name)


def is_new_day(prev_ts: Optional[pd.Timestamp], current_ts: pd.Timestamp, tz_name: str) -> bool:
    """Return `True` if `current_ts` belongs to a different day than `prev_ts`.

    Both timestamps are compared in the provided timezone.  If
    `prev_ts` is `None`, it is considered a new day.
    """
    if prev_ts is None:
        return True
    prev_local = to_timezone(prev_ts, tz_name)
    curr_local = to_timezone(current_ts, tz_name)
    return prev_local.date() != curr_local.date()


def is_in_session(ts: pd.Timestamp, session_start: time, session_end: time, tz_name: str) -> bool:
    """Check whether `ts` is within the trading session.

    The timestamp is converted to the given timezone and its time
    component is compared to the start and end times.  The end time
    is exclusive: the bar whose close time equals the session end is
    considered outside the session.
    """
    local_ts = to_timezone(ts, tz_name)
    current_time = local_ts.timetz()
    return (session_start <= current_time < session_end)