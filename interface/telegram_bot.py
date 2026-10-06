"""Telegram Bot Interface Module.
Sends AI Trade Plans with Approve/Reject interactive buttons and executes approved orders.
"""
import logging
import asyncio
from typing import Dict, Any, Optional

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        CallbackQueryHandler,
        ContextTypes,
    )
except ImportError:
    Update = None
    InlineKeyboardButton = None
    InlineKeyboardMarkup = None
    Application = None
    CommandHandler = None
    CallbackQueryHandler = None
    ContextTypes = None

from config.settings import settings
from execution.mt5_execution import mt5_execution
from execution.journal_db import journal_db

logger = logging.getLogger("interface.telegram_bot")


class TelegramBotManager:
    """Manages Telegram Bot messaging and interactive inline approval workflows."""

    def __init__(self) -> None:
        self.token: str = settings.TELEGRAM_BOT_TOKEN
        self.chat_id: str = settings.TELEGRAM_CHAT_ID
        self.application: Optional[Any] = None
        self.pending_trades: Dict[str, Dict[str, Any]] = {}

    def init_bot(self) -> bool:
        """Initialize the Telegram Bot Application."""
        if Application is None:
            logger.error("Error in init_bot: python-telegram-bot library is not installed.")
            return False

        if not self.token or not self.chat_id:
            logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing in config.")
            return False

        try:
            self.application = Application.builder().token(self.token).build()
            self.application.add_handler(CommandHandler("start", self._cmd_start))
            self.application.add_handler(CommandHandler("status", self._cmd_status))
            self.application.add_handler(CallbackQueryHandler(self._handle_callback))
            logger.info("Telegram Bot Application initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Error in init_bot: {str(e)}")
            return False

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        try:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "🤖 <b>AI Quant Trading Bot</b> đang chạy!\n"
                    "Hệ thống sẽ tự động quét nến M15 và gửi tín hiệu kèm nút bấm phê duyệt.",
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Error in _cmd_start: {str(e)}")

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        try:
            if update.effective_message:
                recent = journal_db.get_recent_trades(limit=5)
                msg = f"📊 <b>BÁO CÁO HOẠT ĐỘNG BOT:</b>\n"
                msg += f"• Cặp theo dõi: {settings.SYMBOL} ({settings.TIMEFRAME})\n"
                msg += f"• Lệnh gần nhất ({len(recent)}):\n"
                for t in recent:
                    msg += f"  - [{t.get('status')}] {t.get('trade_type')} @ {t.get('entry_price')} (Score: {t.get('ai_score')})\n"
                await update.effective_message.reply_text(msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error in _cmd_status: {str(e)}")

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle interactive [APPROVE] and [REJECT] button clicks."""
        query = update.callback_query
        if not query or not query.data:
            return

        await query.answer()
        data = query.data

        try:
            if data.startswith("approve_"):
                trade_id = data.replace("approve_", "")
                trade_setup = self.pending_trades.get(trade_id)

                if not trade_setup:
                    # Check database if in memory cache missed
                    db_trade = journal_db.get_trade(trade_id)
                    if db_trade:
                        trade_setup = db_trade

                if trade_setup:
                    ticket = mt5_execution.execute_pending_order(trade_setup)
                    if ticket:
                        await query.edit_message_caption(
                            caption=f"{query.message.caption or query.message.text}\n\n"
                                    f"✅ <b>ĐÃ PHÊ DUYỆT & GỬI LỆNH THÀNH CÔNG!</b>\n"
                                    f"• Mã lệnh MT5 Ticket: <code>#{ticket}</code>",
                            parse_mode="HTML"
                        ) if query.message.caption else await query.edit_message_text(
                            text=f"{query.message.text}\n\n"
                                 f"✅ <b>ĐÃ PHÊ DUYỆT & GỬI LỆNH THÀNH CÔNG!</b>\n"
                                 f"• Mã lệnh MT5 Ticket: <code>#{ticket}</code>",
                            parse_mode="HTML"
                        )
                    else:
                        await query.edit_message_text(
                            text=f"{query.message.text}\n\n❌ <b>LỖI KHI BẮN LỆNH SANG MT5!</b> Kiểm tra log terminal.",
                            parse_mode="HTML"
                        )
                else:
                    await query.edit_message_text(
                        text=f"{query.message.text}\n\n⚠️ Kế hoạch đã hết hạn hoặc không tìm thấy dữ liệu.",
                        parse_mode="HTML"
                    )

            elif data.startswith("reject_"):
                trade_id = data.replace("reject_", "")
                journal_db.update_trade_status(trade_id=trade_id, status="REJECTED")
                if trade_id in self.pending_trades:
                    del self.pending_trades[trade_id]

                await query.edit_message_text(
                    text=f"{query.message.text}\n\n❌ <b>BẠN ĐÃ TỪ CHỐI KẾ HOẠCH NÀY.</b>",
                    parse_mode="HTML"
                )

        except Exception as e:
            logger.error(f"Error in _handle_callback: {str(e)}")

    async def send_trade_signal(
        self,
        trade_setup: Dict[str, Any],
        ai_analysis: Any
    ) -> bool:
        """Send formatted HTML trade plan with Approve and Reject buttons."""
        trade_id = trade_setup.get("trade_id", "")
        self.pending_trades[trade_id] = trade_setup

        if not self.application and not self.init_bot():
            logger.warning("Telegram Bot is not active. Trade plan logged but not transmitted.")
            return False

        try:
            reasons_str = "\n".join([f"  • {r}" for r in ai_analysis.key_reasons])
            message_text = (
                f"🤖 <b>AI MASTER TRADE PLAN ({trade_setup.get('symbol', 'XAUUSD')})</b>\n\n"
                f"• <b>Lệnh:</b> <code>{trade_setup.get('signal_type')}</code> @ <b>{trade_setup.get('entry_price')}</b>\n"
                f"• <b>SL:</b> {trade_setup.get('sl_price')} | <b>TP:</b> {trade_setup.get('tp_price')} "
                f"(RR 1:{trade_setup.get('rr_ratio')})\n"
                f"• <b>Khối lượng:</b> {trade_setup.get('lot_size')} Lots (Risk {trade_setup.get('risk_percent', 1.0)}%)\n"
                f"• <b>Điểm AI đánh giá:</b> <b>{ai_analysis.confidence_score}/100</b>\n"
                f"• <b>Lý do AI:</b>\n{reasons_str}\n"
                f"• <b>Cảnh báo:</b> <i>{ai_analysis.risk_warnings}</i>"
            )

            keyboard = [
                [
                    InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{trade_id}"),
                    InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{trade_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text=message_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            logger.info(f"Telegram trade signal sent successfully for trade [{trade_id}].")
            return True

        except Exception as e:
            logger.error(f"Error in send_trade_signal: {str(e)}")
            return False


telegram_bot = TelegramBotManager()
