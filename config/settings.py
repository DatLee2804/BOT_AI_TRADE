"""System Configuration module for Hybrid AI Trading Bot."""
import os
import logging
from dataclasses import dataclass
from typing import Optional
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("trading_bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("config.settings")


@dataclass
class Settings:
    """Dataclass holding all trading bot configuration parameters."""
    
    # MetaTrader 5
    MT5_ACCOUNT: int = int(os.getenv("MT5_ACCOUNT", "0"))
    MT5_PASSWORD: str = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER: str = os.getenv("MT5_SERVER", "")
    MT5_PATH: Optional[str] = os.getenv("MT5_PATH", None)
    
    # Google Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    
    # Trading Rules & Risk Management
    SYMBOL: str = os.getenv("SYMBOL", "XAUUSD")
    TIMEFRAME: str = os.getenv("TIMEFRAME", "M15")
    MAX_SPREAD_PIPS: float = float(os.getenv("MAX_SPREAD_PIPS", "2.5"))
    RISK_PERCENT: float = float(os.getenv("RISK_PERCENT", "1.0"))
    MAGIC_NUMBER: int = int(os.getenv("MAGIC_NUMBER", "888999"))
    MIN_RR_RATIO: float = float(os.getenv("MIN_RR_RATIO", "2.5"))
    ATR_MULTIPLIER_SL: float = float(os.getenv("ATR_MULTIPLIER_SL", "1.5"))
    NEWS_FILTER_MINUTES: int = int(os.getenv("NEWS_FILTER_MINUTES", "30"))
    POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", "10"))
    
    # Local Storage & Vector DB
    CHROMA_PATH: str = os.getenv("CHROMA_PATH", "./chroma_db")
    DB_PATH: str = os.getenv("DB_PATH", "trading_journal.db")

    def validate(self) -> None:
        """Validate critical configuration fields."""
        if not self.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY is missing in .env! AI Brain inference will fail if not provided.")
        if not self.TELEGRAM_BOT_TOKEN:
            logger.warning("TELEGRAM_BOT_TOKEN is missing in .env! Telegram notifications will not be sent.")
        if not self.TELEGRAM_CHAT_ID:
            logger.warning("TELEGRAM_CHAT_ID is missing in .env! Telegram notifications will not be sent.")


settings = Settings()
settings.validate()
