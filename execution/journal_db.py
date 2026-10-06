"""SQLite Journal Database for Trading Bot history, AI decisions, and executions."""
import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from config.settings import settings

logger = logging.getLogger("execution.journal_db")


class JournalDB:
    """Manages SQLite storage for trade history, decisions, and execution outcomes."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path: str = db_path or settings.DB_PATH
        self.init_db()

    @contextmanager
    def _get_connection(self):
        """Create a connection with row factory enabled and ensure proper closure."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Create the trades table schema if not already exists."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trade_id TEXT UNIQUE NOT NULL,
                        timestamp TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        trade_type TEXT NOT NULL,
                        entry_price REAL NOT NULL,
                        sl REAL NOT NULL,
                        tp REAL NOT NULL,
                        lot_size REAL NOT NULL,
                        ai_score INTEGER NOT NULL,
                        ai_reasoning TEXT,
                        status TEXT NOT NULL,
                        order_ticket INTEGER DEFAULT NULL,
                        pnl REAL DEFAULT 0.0
                    )
                """)
                conn.commit()
            logger.info(f"Journal SQLite database initialized at '{self.db_path}'.")
        except Exception as e:
            logger.error(f"Error in init_db: {str(e)}")

    def log_trade(
        self,
        trade_id: str,
        symbol: str,
        trade_type: str,
        entry_price: float,
        sl: float,
        tp: float,
        lot_size: float,
        ai_score: int,
        ai_reasoning: str,
        status: str = "PENDING"
    ) -> bool:
        """Log a newly generated trade plan upon AI decision."""
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO trades (
                        trade_id, timestamp, symbol, trade_type, entry_price, sl, tp,
                        lot_size, ai_score, ai_reasoning, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_id, now_iso, symbol, trade_type, entry_price, sl, tp,
                    lot_size, ai_score, ai_reasoning, status
                ))
                conn.commit()
            logger.info(f"Logged trade [{trade_id}] {trade_type} status={status}")
            return True
        except Exception as e:
            logger.error(f"Error in log_trade: {str(e)}")
            return False

    def update_trade_status(
        self,
        trade_id: str,
        status: str,
        order_ticket: Optional[int] = None,
        pnl: Optional[float] = None
    ) -> bool:
        """Update trade execution status (e.g. APPROVED, REJECTED, CLOSED) and ticket number."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if order_ticket is not None and pnl is not None:
                    cursor.execute("""
                        UPDATE trades
                        SET status = ?, order_ticket = ?, pnl = ?
                        WHERE trade_id = ?
                    """, (status, order_ticket, pnl, trade_id))
                elif order_ticket is not None:
                    cursor.execute("""
                        UPDATE trades
                        SET status = ?, order_ticket = ?
                        WHERE trade_id = ?
                    """, (status, order_ticket, trade_id))
                elif pnl is not None:
                    cursor.execute("""
                        UPDATE trades
                        SET status = ?, pnl = ?
                        WHERE trade_id = ?
                    """, (status, pnl, trade_id))
                else:
                    cursor.execute("""
                        UPDATE trades
                        SET status = ?
                        WHERE trade_id = ?
                    """, (status, trade_id))
                conn.commit()
            logger.info(f"Updated trade [{trade_id}] to status='{status}' (ticket={order_ticket})")
            return True
        except Exception as e:
            logger.error(f"Error in update_trade_status: {str(e)}")
            return False

    def get_trade(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve trade record by trade_id."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM trades WHERE trade_id = ?", (trade_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
            return None
        except Exception as e:
            logger.error(f"Error in get_trade: {str(e)}")
            return None

    def get_recent_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch list of most recent trade records."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,))
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error in get_recent_trades: {str(e)}")
            return []


journal_db = JournalDB()
