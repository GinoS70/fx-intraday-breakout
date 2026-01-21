import os
import sys
import pandas as pd

# Ensure the project root (one level above `tests`) is on sys.path so that
# `src` can be imported when running tests directly via `python`.
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config.schema import Config
from src.strategy.intraday_breakout import IntradayBreakoutStrategy, IntradayState

import unittest


class TestIntradayLevels(unittest.TestCase):
    def test_intraday_levels_reset_at_midnight(self) -> None:
        # Create a minimal configuration
        cfg = Config(symbols=["TEST"], timeframe="H1")
        strategy = IntradayBreakoutStrategy(cfg)
        state = IntradayState()

        # First bar on day 1
        ts1 = pd.Timestamp("2024-01-01 05:00", tz=cfg.data.timezone)
        bar1 = pd.Series({"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5})
        signal1, state = strategy.evaluate_bar(ts1, bar1, state)
        self.assertTrue(state.high == 2.0 and state.low == 0.5)

        # Second bar on next day – intraday levels should reset
        ts2 = pd.Timestamp("2024-01-02 05:00", tz=cfg.data.timezone)
        bar2 = pd.Series({"open": 1.0, "high": 1.5, "low": 0.6, "close": 1.2})
        signal2, state = strategy.evaluate_bar(ts2, bar2, state)
        # After reset, intraday high/low are equal to this bar’s high/low
        self.assertEqual(state.high, 1.5)
        self.assertEqual(state.low, 0.6)


if __name__ == '__main__':
    unittest.main()