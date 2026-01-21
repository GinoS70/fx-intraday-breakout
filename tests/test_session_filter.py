import os
import sys
import pandas as pd

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config.schema import Config
from src.strategy.intraday_breakout import IntradayBreakoutStrategy, IntradayState

import unittest


class TestSessionFilter(unittest.TestCase):
    def test_session_filter_outside_hours(self) -> None:
        cfg = Config(symbols=["TEST"], timeframe="H1")
        # Restrict session to 06:00–20:00
        cfg.session.start = "06:00"
        cfg.session.end = "20:00"
        strategy = IntradayBreakoutStrategy(cfg)
        state = IntradayState()
        # Set previous high/low to ensure there would be a signal if not for the session filter
        state.high = 1.0
        state.low = 1.0
        state.current_date = pd.Timestamp("2024-01-01", tz=cfg.data.timezone).date()
        # Bar ends at 22:00, outside session end
        ts = pd.Timestamp("2024-01-01 22:00", tz=cfg.data.timezone)
        bar = pd.Series({"open": 1.0, "high": 1.5, "low": 0.5, "close": 1.2})
        signal, _ = strategy.evaluate_bar(ts, bar, state)
        self.assertIsNone(signal, "Trades should not be taken outside the configured session")


if __name__ == '__main__':
    unittest.main()