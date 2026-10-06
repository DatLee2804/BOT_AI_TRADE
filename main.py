"""Main Entrypoint and Orchestration Engine for Hybrid AI Trading Bot (XAUUSD).
Coordinates MT5 data fetching, deterministic analysis, RAG retrieval, Gemini AI inference,
and Telegram Human-in-the-Loop execution.
"""
import sys
import time
import uuid
import signal
import asyncio
import logging
from typing import Optional, Dict, Any

from config.settings import settings
from core.mt5_loader import mt5_loader
from core.indicators import technical_analyzer
from core.risk_engine import risk_engine
from rag.vector_store import vector_store
from brain.ai_agent import ai_agent
from interface.telegram_bot import telegram_bot
from execution.journal_db import journal_db

logger = logging.getLogger("main")


class HybridAITradingBot:
    """Main Orchestrator for the Hybrid AI Trading System."""

    def __init__(self) -> None:
        self.is_running: bool = False
        self.last_candle_time: Optional[str] = None

    def initialize_system(self) -> bool:
        """Initialize all subsystems: DB, RAG Vector Store, MT5, and Telegram."""
        logger.info("Initializing Hybrid AI Trading Bot...")

        # 1. Initialize SQLite Journal DB
        journal_db.init_db()

        # 2. Initialize RAG Vector Store & Index Knowledge Base
        vector_store.init_vector_store()

        # 3. Connect to MetaTrader 5
        if not mt5_loader.connect():
            logger.warning("MT5 could not be connected immediately. Will attempt reconnection in main loop.")

        # 4. Initialize Telegram Bot
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            telegram_bot.init_bot()
        else:
            logger.warning("Telegram Bot token/chat_id not fully configured in .env.")

        logger.info("All subsystems initialized.")
        return True

    async def process_market_cycle(self) -> None:
        """Execute one complete market evaluation cycle."""
        symbol = settings.SYMBOL
        tf_m15 = settings.TIMEFRAME

        # 1. Fetch OHLCV data for H1 (Primary), H4 and M15 (Context)
        df_h1 = mt5_loader.get_ohlcv(symbol, "H1", n_bars=100)
        df_h4 = mt5_loader.get_ohlcv(symbol, "H4", n_bars=100)
        df_m15 = mt5_loader.get_ohlcv(symbol, "M15", n_bars=100)

        if df_h1 is None or len(df_h1) < 20:
            logger.debug(f"Waiting for H1 market data for {symbol}...")
            return

        current_candle_time = str(df_h1["time"].iloc[-1])
        if current_candle_time == self.last_candle_time:
            logger.debug(f"H1 Candle {current_candle_time} already evaluated. Standing by...")
            return

        logger.info(f"New H1 candle detected [{current_candle_time}]. Evaluating Price Action setup...")
        self.last_candle_time = current_candle_time

        # 2. H1 Market Structure Channel & Candlestick Reversal Calculation
        setup: Optional[Dict[str, Any]] = technical_analyzer.calculate_trade_setup_h1(
            df_h1=df_h1,
            min_rr=settings.MIN_RR_RATIO,
            atr_mult=settings.ATR_MULTIPLIER_SL,
        )

        if setup is None:
            logger.info("No valid H1 Price Action setup (Channel + Reversal confirmation) on current bar.")
            return

        logger.info(
            f"Potential Setup Found: {setup['signal_type']} @ {setup['entry_price']} "
            f"| Structure: {setup['structure']} | Pattern: {setup['pattern']} | RR: 1:{setup['rr_ratio']}"
        )

        # 3. Hard Risk Engine Filters (Spread & Economic News)
        if not risk_engine.check_spread(symbol=symbol, max_allowed_pips=settings.MAX_SPREAD_PIPS):
            logger.warning(f"Spread filter failed for {symbol}. Trade skipped.")
            return

        if not risk_engine.check_news_filter(buffer_minutes=settings.NEWS_FILTER_MINUTES):
            logger.warning("Red News Event filter active! Trade skipped for capital protection.")
            return

        # Calculate position size
        balance = 10000.0  # Default fallback balance
        try:
            if mt5_loader.is_connected and mt5_loader.mt5 is not None:
                acc = mt5_loader.mt5.account_info()
                if acc:
                    balance = acc.balance
        except Exception:
            pass

        lot_size = risk_engine.calculate_position_size(
            account_balance=balance,
            risk_percent=settings.RISK_PERCENT,
            sl_pips=setup["risk_pips"],
            symbol=symbol,
        )
        setup["lot_size"] = lot_size
        setup["risk_percent"] = settings.RISK_PERCENT
        setup["symbol"] = symbol

        # 4. RAG Knowledge Base Retrieval
        market_context_query = (
            f"{setup['signal_type']} on {symbol}. Structure: {setup['structure']}. "
            f"Pattern: {setup['pattern']}. H1 Trend: {setup['h1_trend']}, RSI H1: {setup.get('rsi_h1', 50)}."
        )
        relevant_rules = vector_store.query_relevant_rules(market_context_query, top_k=3)

        # 5. Gemini 2.0 Flash AI Evaluation
        logger.info("Requesting Gemini 2.0 Flash inference...")
        ai_decision = ai_agent.analyze_market_setup(
            market_data=setup,
            rag_rules=relevant_rules,
        )

        logger.info(f"AI Decision: {ai_decision.decision} (Confidence: {ai_decision.confidence_score}/100)")

        # 6. Action based on AI Decision
        trade_id = f"TRD_{uuid.uuid4().hex[:8].upper()}"
        setup["trade_id"] = trade_id

        # Log AI analysis to Journal DB
        journal_db.log_trade(
            trade_id=trade_id,
            symbol=symbol,
            trade_type=setup["signal_type"],
            entry_price=setup["entry_price"],
            sl=setup["sl_price"],
            tp=setup["tp_price"],
            lot_size=lot_size,
            ai_score=ai_decision.confidence_score,
            ai_reasoning="; ".join(ai_decision.key_reasons),
            status="PENDING" if ai_decision.decision.upper() == "PASS" else "REJECTED_BY_AI",
        )

        # 7. Telegram Human-In-The-Loop Interface
        if ai_decision.decision.upper() == "PASS":
            logger.info(f"Setup APPROVED by AI! Transmitting to Telegram for human confirmation...")
            await telegram_bot.send_trade_signal(trade_setup=setup, ai_analysis=ai_decision)
        else:
            logger.info(f"Setup rejected by AI. Reasons: {ai_decision.key_reasons}")

    async def run(self) -> None:
        """Start the main asynchronous event loop."""
        self.is_running = True
        self.initialize_system()

        # Start Telegram polling if available
        if telegram_bot.application:
            await telegram_bot.application.initialize()
            await telegram_bot.application.start()
            await telegram_bot.application.updater.start_polling()
            logger.info("Telegram interactive polling started.")

        logger.info(f"Trading bot loop running. Polling every {settings.POLL_INTERVAL_SECONDS} seconds...")

        try:
            while self.is_running:
                try:
                    await self.process_market_cycle()
                except Exception as cycle_err:
                    logger.error(f"Error in process_market_cycle: {str(cycle_err)}")

                await asyncio.sleep(settings.POLL_INTERVAL_SECONDS)

        except asyncio.CancelledError:
            logger.info("Main loop cancelled. Initiating graceful shutdown...")
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Gracefully stop bot services."""
        logger.info("Shutting down Bot services...")
        self.is_running = False
        if telegram_bot.application and telegram_bot.application.updater.running:
            await telegram_bot.application.updater.stop()
            await telegram_bot.application.stop()
            await telegram_bot.application.shutdown()
        mt5_loader.shutdown()
        logger.info("Bot shutdown complete.")


def handle_exit(bot: HybridAITradingBot) -> None:
    """Handle termination signals."""
    bot.is_running = False


async def main() -> None:
    bot = HybridAITradingBot()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: handle_exit(bot))
        except NotImplementedError:
            # Signal handling on Windows
            pass
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot manually terminated by user.")
