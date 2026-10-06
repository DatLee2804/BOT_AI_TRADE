"""Unit test for H1 Price Action Channel and Reversal Patterns Indicator Engine."""
import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from core.indicators import (
    technical_analyzer,
    calculate_basic_indicators,
    find_swing_points,
    analyze_market_structure_h1,
    detect_reversal_patterns,
    calculate_trade_setup_h1,
)


class TestIndicators(unittest.TestCase):
    """Test EMA, RSI, ATR, Swing Points, Market Structure, and Reversal Patterns."""

    def setUp(self) -> None:
        np.random.seed(42)
        base_price = 2650.0
        n_bars = 60

        def create_df(trend_bias=0.2):
            prices = [base_price]
            for _ in range(n_bars - 1):
                change = np.random.normal(trend_bias, 0.5)
                prices.append(prices[-1] + change)

            data = []
            now = datetime.now()
            for i, p in enumerate(prices):
                high = p + abs(np.random.normal(0.6, 0.2))
                low = p - abs(np.random.normal(0.6, 0.2))
                open_p = p - np.random.normal(0.1, 0.2)
                close_p = p + np.random.normal(0.1, 0.2)
                data.append({
                    "time": now - timedelta(hours=(n_bars - i)),
                    "open": round(open_p, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "close": round(close_p, 2),
                    "tick_volume": int(np.random.randint(100, 1000))
                })
            return pd.DataFrame(data)

        self.df_h1 = create_df(trend_bias=0.3)

    def test_indicators_math(self) -> None:
        """Verify EMA, RSI, ATR calculations."""
        df_ind = calculate_basic_indicators(self.df_h1)
        self.assertIn("ema_20", df_ind.columns)
        self.assertIn("ema_50", df_ind.columns)
        self.assertIn("ema_200", df_ind.columns)
        self.assertIn("rsi", df_ind.columns)
        self.assertIn("atr", df_ind.columns)

        self.assertFalse(np.isnan(df_ind["rsi"].iloc[-1]))
        self.assertGreater(df_ind["atr"].iloc[-1], 0)
        self.assertGreater(df_ind["ema_20"].iloc[-1], 0)

    def test_swing_points_and_structure(self) -> None:
        """Verify Swing points identification and market structure analysis."""
        highs, lows = find_swing_points(self.df_h1, window=3)
        self.assertIsInstance(highs, list)
        self.assertIsInstance(lows, list)

        structure = analyze_market_structure_h1(self.df_h1)
        self.assertIn("market_structure", structure)
        self.assertIn("last_support", structure)
        self.assertIn("last_resistance", structure)
        self.assertIn(structure["market_structure"], ["UPTREND_CHANNEL", "DOWNTREND_CHANNEL", "SIDEWAY"])

    def test_reversal_pattern_detection(self) -> None:
        """Inject Bullish Engulfing candle and verify detection."""
        df = self.df_h1.copy()
        # Set iloc[-3] as bearish red candle
        df.loc[len(df) - 3, "open"] = 2660.0
        df.loc[len(df) - 3, "close"] = 2652.0
        df.loc[len(df) - 3, "high"] = 2661.0
        df.loc[len(df) - 3, "low"] = 2651.0

        # Set iloc[-2] as bullish engulfing green candle covering iloc[-3]
        df.loc[len(df) - 2, "open"] = 2652.0
        df.loc[len(df) - 2, "close"] = 2662.0
        df.loc[len(df) - 2, "high"] = 2663.0
        df.loc[len(df) - 2, "low"] = 2651.5

        pattern = detect_reversal_patterns(df)
        self.assertEqual(pattern, "BULLISH_REVERSAL")

    def test_trade_setup_calculation_h1(self) -> None:
        """Verify calculate_trade_setup_h1 produces complete setup with RR >= 1:2.5."""
        df = self.df_h1.copy()
        # Inject Bullish Engulfing at the end
        df.loc[len(df) - 3, "open"] = 2660.0
        df.loc[len(df) - 3, "close"] = 2652.0
        df.loc[len(df) - 3, "high"] = 2661.0
        df.loc[len(df) - 3, "low"] = 2651.0

        df.loc[len(df) - 2, "open"] = 2652.0
        df.loc[len(df) - 2, "close"] = 2662.0
        df.loc[len(df) - 2, "high"] = 2663.0
        df.loc[len(df) - 2, "low"] = 2651.5

        setup = calculate_trade_setup_h1(df, min_rr=2.5, atr_mult=1.5)
        self.assertIsNotNone(setup)
        self.assertIn("signal_type", setup)
        self.assertEqual(setup["signal_type"], "BUY_LIMIT")
        self.assertIn("entry_price", setup)
        self.assertIn("sl_price", setup)
        self.assertIn("tp_price", setup)
        self.assertGreaterEqual(setup["rr_ratio"], 2.5)


if __name__ == "__main__":
    unittest.main()
