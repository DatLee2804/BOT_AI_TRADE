"""MetaTrader 5 Order Execution Module.
Handles pending order creation (BUY_LIMIT / SELL_LIMIT) upon Telegram user approval.
"""
import logging
from typing import Dict, Any, Optional

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from config.settings import settings
from core.mt5_loader import mt5_loader
from execution.journal_db import journal_db

logger = logging.getLogger("execution.mt5_execution")


class MT5ExecutionEngine:
    """Sends orders to MT5 terminal and records outcomes in JournalDB."""

    def __init__(self, magic_number: Optional[int] = None) -> None:
        self.magic_number: int = magic_number or settings.MAGIC_NUMBER

    def execute_pending_order(self, trade_setup: Dict[str, Any]) -> Optional[int]:
        """Place pending order on MT5 terminal after user approval.
        
        Args:
            trade_setup: Dict containing trade parameters:
                - trade_id: str
                - symbol: str
                - signal_type: 'BUY_LIMIT' or 'SELL_LIMIT'
                - entry_price: float
                - sl_price: float
                - tp_price: float
                - lot_size: float
                
        Returns:
            Order ticket number if successful, None otherwise.
        """
        trade_id = trade_setup.get("trade_id", "unknown")
        symbol = trade_setup.get("symbol", settings.SYMBOL)
        signal_type = trade_setup.get("signal_type", "")
        entry_price = float(trade_setup.get("entry_price", 0.0))
        sl_price = float(trade_setup.get("sl_price", 0.0))
        tp_price = float(trade_setup.get("tp_price", 0.0))
        lot_size = float(trade_setup.get("lot_size", 0.01))

        if mt5 is None:
            logger.error("Error in execute_pending_order: MetaTrader5 module not installed.")
            return None

        if not mt5_loader.ensure_connected():
            logger.error(f"Error in execute_pending_order: MT5 is disconnected. Cannot place trade [{trade_id}].")
            return None

        try:
            # Map order type
            if signal_type == "BUY_LIMIT":
                order_type = mt5.ORDER_TYPE_BUY_LIMIT
            elif signal_type == "SELL_LIMIT":
                order_type = mt5.ORDER_TYPE_SELL_LIMIT
            else:
                logger.error(f"Error in execute_pending_order: Unsupported signal_type '{signal_type}'.")
                return None

            # Verify symbol is available and select it in market watch
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"Symbol {symbol} not found in MT5.")
                return None
            if not symbol_info.visible:
                if not mt5.symbol_select(symbol, True):
                    logger.error(f"Failed to select symbol {symbol} into Market Watch.")
                    return None

            # Determine appropriate filling mode
            filling_mode = mt5.ORDER_FILLING_IOC
            if symbol_info.filling_mode & 1:  # FOK
                filling_mode = mt5.ORDER_FILLING_FOK
            elif symbol_info.filling_mode & 2:  # IOC
                filling_mode = mt5.ORDER_FILLING_IOC
            else:
                filling_mode = mt5.ORDER_FILLING_RETURN

            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": lot_size,
                "type": order_type,
                "price": entry_price,
                "sl": sl_price,
                "tp": tp_price,
                "deviation": 20,
                "magic": self.magic_number,
                "comment": f"AI_BOT_{trade_id[:8]}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }

            logger.info(f"Sending pending order request to MT5: {request}")
            result = mt5.order_send(request)

            if result is None:
                logger.error(f"mt5.order_send returned None. Error: {mt5.last_error()}")
                return None

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"mt5.order_send failed: retcode={result.retcode}, comment='{result.comment}'")
                return None

            order_ticket = result.order
            logger.info(f"Order placed successfully! Ticket #{order_ticket} on {symbol} @ {entry_price}")

            # Update journal record
            journal_db.update_trade_status(trade_id=trade_id, status="APPROVED", order_ticket=order_ticket)
            return order_ticket

        except Exception as e:
            logger.error(f"Error in execute_pending_order: {str(e)}")
            return None


mt5_execution = MT5ExecutionEngine()
