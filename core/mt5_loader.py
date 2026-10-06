"""MetaTrader 5 Data Loader Module.
Responsible for connecting to MT5 terminal and fetching OHLCV candle data.
"""
import os
import logging
from typing import Optional, Dict, Any
import pandas as pd
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from config.settings import settings

logger = logging.getLogger("core.mt5_loader")

# Mapping of string timeframes to MetaTrader 5 constants
TIMEFRAME_MAP = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 16385,
    "H4": 16388,
    "D1": 16408,
}
if mt5 is not None:
    TIMEFRAME_MAP = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }


class MT5Loader:
    """Manages connection to MetaTrader 5 and pulls market data."""

    def __init__(self) -> None:
        self.is_connected: bool = False

    def connect(self) -> bool:
        """Connect to MT5 terminal using configuration parameters."""
        if mt5 is None:
            logger.error("Error in connect: MetaTrader5 library is not installed.")
            return False

        try:
            init_kwargs: Dict[str, Any] = {}
            if settings.MT5_PATH and os.path.exists(settings.MT5_PATH):
                init_kwargs["path"] = settings.MT5_PATH

            if not mt5.initialize(**init_kwargs):
                if not mt5.initialize():
                    logger.error(f"Error in connect: mt5.initialize() failed: {mt5.last_error()}")
                    self.is_connected = False
                    return False

            # Only call login if real, non-placeholder credentials are provided
            has_explicit_creds = (
                settings.MT5_ACCOUNT > 0
                and settings.MT5_ACCOUNT != 12345678
                and bool(settings.MT5_PASSWORD)
                and settings.MT5_PASSWORD != "your_mt5_password_here"
                and bool(settings.MT5_SERVER)
                and settings.MT5_SERVER != "YourBroker-Demo"
            )
            if has_explicit_creds:
                authorized = mt5.login(
                    login=settings.MT5_ACCOUNT,
                    password=settings.MT5_PASSWORD,
                    server=settings.MT5_SERVER,
                )
                if not authorized:
                    logger.error(f"Error in connect: mt5.login() failed: {mt5.last_error()}")
                    self.is_connected = False
                    return False

            account_info = mt5.account_info()
            if account_info:
                logger.info(f"MT5 Connected successfully. Account: {account_info.login}, Server: {account_info.server}, Balance: {account_info.balance}")
            else:
                logger.info("MT5 initialized successfully in local terminal session.")

            self.is_connected = True
            return True

        except Exception as e:
            logger.error(f"Error in connect: {str(e)}")
            self.is_connected = False
            return False

    def ensure_connected(self) -> bool:
        """Verify connection and reconnect if needed."""
        if not self.is_connected:
            return self.connect()
        return True

    def resolve_symbol(self, symbol: str) -> str:
        """Resolve actual broker symbol matching suffix (e.g. XAUUSD -> XAUUSDm)."""
        if mt5 is None or not self.ensure_connected():
            return symbol
        try:
            candidates = [symbol, f"{symbol}m", f"{symbol}.m", f"{symbol}247m", f"{symbol}_i"]
            for cand in candidates:
                info = mt5.symbol_info(cand)
                if info is not None:
                    if not info.visible:
                        mt5.symbol_select(cand, True)
                    return cand
        except Exception as e:
            logger.error(f"Error in resolve_symbol: {str(e)}")
        return symbol

    def get_ohlcv(self, symbol: str, timeframe: str, n_bars: int = 100) -> Optional[pd.DataFrame]:
        """Fetch OHLCV candle data for a given symbol and timeframe.
        
        Args:
            symbol: Trading pair symbol (e.g., 'XAUUSD').
            timeframe: Timeframe string ('M15', 'H1', 'H4', etc.).
            n_bars: Number of recent bars to retrieve.
            
        Returns:
            DataFrame with columns [time, open, high, low, close, tick_volume] or None.
        """
        if not self.ensure_connected():
            logger.error(f"Error in get_ohlcv: Cannot fetch data because MT5 is disconnected.")
            return None

        try:
            actual_symbol = self.resolve_symbol(symbol)
            tf_const = TIMEFRAME_MAP.get(timeframe.upper())
            if tf_const is None:
                logger.error(f"Error in get_ohlcv: Unsupported timeframe {timeframe}")
                return None

            rates = mt5.copy_rates_from_pos(actual_symbol, tf_const, 0, n_bars)
            if rates is None or len(rates) == 0:
                logger.warning(f"Warning in get_ohlcv: No data returned for {symbol} on {timeframe}. Error: {mt5.last_error()}")
                return None

            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            
            # Select required columns: [time, open, high, low, close, tick_volume]
            required_cols = ["time", "open", "high", "low", "close", "tick_volume"]
            df = df[[col for col in required_cols if col in df.columns]].copy()
            return df

        except Exception as e:
            logger.error(f"Error in get_ohlcv: {str(e)}")
            return None

    def get_symbol_info_tick(self, symbol: str):
        """Fetch current tick for the symbol."""
        if not self.ensure_connected():
            return None
        try:
            return mt5.symbol_info_tick(symbol)
        except Exception as e:
            logger.error(f"Error in get_symbol_info_tick: {str(e)}")
            return None

    def shutdown(self) -> None:
        """Gracefully disconnect from MT5."""
        try:
            if mt5 is not None:
                mt5.shutdown()
            self.is_connected = False
            logger.info("MT5 connection shutdown successfully.")
        except Exception as e:
            logger.error(f"Error in shutdown: {str(e)}")


mt5_loader = MT5Loader()
