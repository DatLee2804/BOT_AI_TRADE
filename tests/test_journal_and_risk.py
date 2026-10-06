"""Unit test for SQLite Journal and Risk Engine Calculations."""
import os
import unittest
from core.risk_engine import risk_engine
from execution.journal_db import JournalDB


class TestJournalAndRisk(unittest.TestCase):
    """Test SQLite Journal DB and Risk position sizing."""

    def test_risk_engine_position_sizing(self) -> None:
        """Verify lot sizing formula: Lot = (Balance * Risk%) / (SL_pips * Pip_Value)."""
        # Account balance = 10,000, Risk = 1% ($100), SL = 20 pips ($2.00 on XAU)
        # Pip value on standard gold lot = $10.00
        # Expected: 100 / (20 * 10) = 0.50 lots
        lot = risk_engine.calculate_position_size(
            account_balance=10000.0,
            risk_percent=1.0,
            sl_pips=20.0,
            symbol="XAUUSD"
        )
        self.assertAlmostEqual(lot, 0.50, places=2)

        # Extreme case: Small balance $500, Risk 1% ($5), SL 30 pips -> rounds to 0.02 lot
        small_lot = risk_engine.calculate_position_size(
            account_balance=500.0,
            risk_percent=1.0,
            sl_pips=30.0,
            symbol="XAUUSD"
        )
        self.assertEqual(small_lot, 0.02)

    def test_journal_db_lifecycle(self) -> None:
        """Test SQLite trade journal logging, querying, and updating."""
        test_db_path = "test_lifecycle_journal.db"
        if os.path.exists(test_db_path):
            os.remove(test_db_path)

        db = JournalDB(db_path=test_db_path)
        trade_id = "TRD_UNIT_TEST_123"

        # 1. Insert trade
        success = db.log_trade(
            trade_id=trade_id,
            symbol="XAUUSD",
            trade_type="BUY_LIMIT",
            entry_price=2645.50,
            sl=2640.00,
            tp=2660.00,
            lot_size=0.15,
            ai_score=85,
            ai_reasoning="H1 Uptrend + M15 FVG Retest",
            status="PENDING"
        )
        self.assertTrue(success)

        # 2. Retrieve trade
        rec = db.get_trade(trade_id)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["trade_type"], "BUY_LIMIT")
        self.assertEqual(rec["entry_price"], 2645.50)
        self.assertEqual(rec["status"], "PENDING")

        # 3. Update status upon approval
        db.update_trade_status(trade_id=trade_id, status="APPROVED", order_ticket=777888)
        updated_rec = db.get_trade(trade_id)
        self.assertEqual(updated_rec["status"], "APPROVED")
        self.assertEqual(updated_rec["order_ticket"], 777888)

        # 4. Clean up
        if os.path.exists(test_db_path):
            os.remove(test_db_path)


if __name__ == "__main__":
    unittest.main()
