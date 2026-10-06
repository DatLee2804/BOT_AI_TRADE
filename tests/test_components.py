"""Comprehensive test suite for Hybrid AI Trading Bot components."""
import os
import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from config.settings import settings
from core.indicators import (
    technical_analyzer,
    calculate_basic_indicators,
    calculate_trade_setup_h1,
)
from core.risk_engine import risk_engine
from brain.prompts import TradeDecisionSchema
from execution.journal_db import JournalDB


class TestTradingBotComponents(unittest.TestCase):
    """Unit and functional tests for the trading bot modules."""

    def setUp(self) -> None:
        # Create synthetic H1 DataFrame
        np.random.seed(42)
        base_price = 2650.0
        n_bars = 60

        def create_df(trend_bias=0.1):
            prices = [base_price]
            for _ in range(n_bars - 1):
                change = np.random.normal(trend_bias, 0.8)
                prices.append(prices[-1] + change)

            data = []
            now = datetime.now()
            for i, p in enumerate(prices):
                high = p + abs(np.random.normal(0.5, 0.2))
                low = p - abs(np.random.normal(0.5, 0.2))
                open_p = p - np.random.normal(0.1, 0.2)
                close_p = p + np.random.normal(0.1, 0.2)
                data.append({
                    "time": now - timedelta(hours=(n_bars - i)),
                    "open": round(open_p, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "close": round(close_p, 2),
                    "tick_volume": int(np.random.randint(50, 500))
                })
            return pd.DataFrame(data)

        self.df_h1 = create_df(trend_bias=0.3)

    def test_settings_loaded(self) -> None:
        """Verify config values."""
        self.assertTrue(settings.SYMBOL.startswith("XAUUSD"))
        self.assertGreaterEqual(settings.MIN_RR_RATIO, 2.5)
        self.assertEqual(settings.MAGIC_NUMBER, 888999)

    def test_technical_indicators(self) -> None:
        """Verify EMA, RSI, ATR calculations."""
        df_ind = calculate_basic_indicators(self.df_h1)
        self.assertIn("ema_20", df_ind.columns)
        self.assertIn("ema_50", df_ind.columns)
        self.assertIn("ema_200", df_ind.columns)
        self.assertIn("rsi", df_ind.columns)
        self.assertIn("atr", df_ind.columns)

        # Verify values are valid floats
        self.assertFalse(np.isnan(df_ind["rsi"].iloc[-1]))
        self.assertGreater(df_ind["atr"].iloc[-1], 0)

    def test_trade_setup_calculation(self) -> None:
        """Verify calculate_trade_setup generates valid setup."""
        df = self.df_h1.copy()
        # Inject Bullish Engulfing pattern at iloc[-2]
        df.loc[len(df) - 3, "open"] = 2660.0
        df.loc[len(df) - 3, "close"] = 2652.0
        df.loc[len(df) - 3, "high"] = 2661.0
        df.loc[len(df) - 3, "low"] = 2651.0

        df.loc[len(df) - 2, "open"] = 2652.0
        df.loc[len(df) - 2, "close"] = 2662.0
        df.loc[len(df) - 2, "high"] = 2663.0
        df.loc[len(df) - 2, "low"] = 2651.5

        setup = calculate_trade_setup_h1(df_h1=df, min_rr=2.5, atr_mult=1.5)
        self.assertIsNotNone(setup)
        self.assertIn("signal_type", setup)
        self.assertIn("entry_price", setup)
        self.assertIn("sl_price", setup)
        self.assertIn("tp_price", setup)
        self.assertGreaterEqual(setup["rr_ratio"], 2.5)

    def test_risk_engine_position_sizing(self) -> None:
        """Verify lot sizing formula."""
        # Account balance = 10,000, Risk = 1% ($100), SL = 20 pips ($2.00 on XAU)
        # Pip value on standard gold lot = $10.00
        # Lot = 100 / (20 * 10) = 0.50 lots
        lot = risk_engine.calculate_position_size(
            account_balance=10000.0,
            risk_percent=1.0,
            sl_pips=20.0,
            symbol="XAUUSDm"
        )
        self.assertAlmostEqual(lot, 0.50, places=2)

    def test_journal_db(self) -> None:
        """Verify SQLite journal logging and updates."""
        test_db_path = "test_trading_journal.db"
        if os.path.exists(test_db_path):
            os.remove(test_db_path)

        test_db = JournalDB(test_db_path)
        trade_id = "TEST_TRD_001"
        ok = test_db.log_trade(
            trade_id=trade_id,
            symbol="XAUUSDm",
            trade_type="BUY_LIMIT",
            entry_price=2652.50,
            sl=2648.00,
            tp=2665.00,
            lot_size=0.15,
            ai_score=88,
            ai_reasoning="A+ Confluence setup",
            status="PENDING"
        )
        self.assertTrue(ok)

        trade = test_db.get_trade(trade_id)
        self.assertIsNotNone(trade)
        self.assertEqual(trade["entry_price"], 2652.50)

        # Update status
        test_db.update_trade_status(trade_id=trade_id, status="APPROVED", order_ticket=999888)
        updated = test_db.get_trade(trade_id)
        self.assertEqual(updated["status"], "APPROVED")
        self.assertEqual(updated["order_ticket"], 999888)

        # Clean up test db file
        if os.path.exists(test_db_path):
            os.remove(test_db_path)

    def test_pydantic_schema(self) -> None:
        """Verify TradeDecisionSchema validation."""
        data = {
            "decision": "PASS",
            "confidence_score": 85,
            "key_reasons": ["Confluence H1/H4", "H1 Bullish Reversal at Support"],
            "risk_warnings": "Chú ý phiên London mở cửa"
        }
        model = TradeDecisionSchema(**data)
        self.assertEqual(model.decision, "PASS")
        self.assertEqual(model.confidence_score, 85)


if __name__ == "__main__":
    unittest.main()
