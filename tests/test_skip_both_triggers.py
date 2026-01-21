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


class TestSkipBothTriggers(unittest.TestCase):
    def test_skip_both_triggers(self) -> None:
        cfg = Config(symbols=["TEST"], timeframe="H1")
        strategy = IntradayBreakoutStrategy(cfg)
        state = IntradayState()
        # Initialise state to have a high and low
        state.high = 1.0
        state.low = 1.0
        state.current_date = pd.Timestamp("2024-01-01", tz=cfg.data.timezone).date()
        ts = pd.Timestamp("2024-01-01 10:00", tz=cfg.data.timezone)
        # Bar with high above and low below previous intraday levels
        bar = pd.Series({"open": 1.0, "high": 1.5, "low": 0.5, "close": 1.2})
        signal, new_state = strategy.evaluate_bar(ts, bar, state)
        self.assertIsNone(signal, "When both long and short signals trigger, strategy should skip the trade")


if __name__ == '__main__':
    unittest.main()