import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config.schema import Config

import unittest


class TestStopLossTakeProfit(unittest.TestCase):
    def test_stop_loss_and_take_profit_calculation(self) -> None:
        """Verify that SL and TP are computed correctly relative to entry price."""
        cfg = Config(symbols=["TEST"], timeframe="H1")
        # Set risk parameters to 10 % for easier arithmetic
        cfg.sl_pct = 0.1
        cfg.tp_pct = 0.1
        # Use zero spread and slippage for the test
        cfg.costs.spread = 0.0
        cfg.costs.slippage = 0.0
        open_price = 10.0
        half_spread = cfg.costs.spread / 2
        slippage = cfg.costs.slippage
        # Long position
        entry_price_long = open_price + half_spread + slippage
        sl_long = entry_price_long * (1.0 - cfg.sl_pct)
        tp_long = entry_price_long * (1.0 + cfg.tp_pct)
        self.assertAlmostEqual(entry_price_long, 10.0, msg="Entry price mismatch for long")
        self.assertAlmostEqual(sl_long, 9.0, msg=f"Expected SL=9.0, got {sl_long}")
        self.assertAlmostEqual(tp_long, 11.0, msg=f"Expected TP=11.0, got {tp_long}")
        # Short position
        entry_price_short = open_price - half_spread - slippage
        sl_short = entry_price_short * (1.0 + cfg.sl_pct)
        tp_short = entry_price_short * (1.0 - cfg.tp_pct)
        self.assertAlmostEqual(entry_price_short, 10.0, msg="Entry price mismatch for short")
        self.assertAlmostEqual(sl_short, 11.0, msg=f"Expected SL=11.0, got {sl_short}")
        self.assertAlmostEqual(tp_short, 9.0, msg=f"Expected TP=9.0, got {tp_short}")


if __name__ == '__main__':
    unittest.main()