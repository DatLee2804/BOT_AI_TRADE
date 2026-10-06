---

### File 5: `04_TELEGRAM_EXECUTION.md`

```markdown
# TECHNICAL SPECIFICATION: TELEGRAM & EXECUTION (`interface/` & `execution/`)

Module chịu trách nhiệm tương tác người dùng, vào lệnh thực tế và lưu trữ lịch sử.

## 1. `interface/telegram_bot.py`
- Sử dụng thư viện `python-telegram-bot`.
- Hàm `send_trade_signal(trade_setup, ai_analysis)`:
  - Soạn tin nhắn HTML định dạng đẹp:
    ```text
    🤖 AI MASTER TRADE PLAN (XAUUSD)
    • Lệnh: BUY LIMIT @ 2645.50
    • SL: 2640.00 | TP: 2660.00 (RR 1:2.9)
    • Khối lượng: 0.15 Lots (Risk 1%)
    • Điểm AI đánh giá: 85/100
    • Lý do AI: Hợp lưu H1 Uptrend, FVG M15 test lại Demand H1.
    • Cảnh báo: Chú ý biến động phiên Âu.
    ```
  - Gửi kèm `InlineKeyboardMarkup` chứa 2 nút:
    - `[✅ APPROVE]` (callback_data: `approve_{trade_id}`)
    - `[❌ REJECT]` (callback_data: `reject_{trade_id}`)

## 2. `execution/mt5_execution.py`
- Lắng nghe sự kiện người dùng bấm `APPROVE` từ Telegram.
- Trích xuất thông số `trade_setup` tương ứng và gọi hàm `mt5.order_send()`:
  - `action`: `mt5.TRADE_ACTION_PENDING`
  - `type`: `mt5.ORDER_TYPE_BUY_LIMIT` hoặc `SELL_LIMIT`
  - `price`, `sl`, `tp`, `volume` chuẩn xác từ Setup.
  - `magic`: 888999 (ID riêng nhận biết lệnh từ Bot).

## 3. `execution/journal_db.py`
- Khởi tạo cơ sở dữ liệu `trading_journal.db` dạng SQLite.
- Tạo bảng `trades`:
  - `id`, `timestamp`, `symbol`, `trade_type`, `entry_price`, `sl`, `tp`, `lot_size`, `ai_score`, `ai_reasoning`, `status` (`PENDING`, `APPROVED`, `REJECTED`, `CLOSED`), `pnl`.
- Hàm `log_trade()`: Lưu lịch sử ngay khi AI ra quyết định và khi lệnh được duyệt/đóng.