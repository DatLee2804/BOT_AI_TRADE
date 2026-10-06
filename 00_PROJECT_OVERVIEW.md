# PROJECT OVERVIEW: HYBRID AI TRADING BOT (XAUUSD)

## 1. Mục tiêu dự án
Xây dựng một hệ thống Trading Bot lai (Hybrid AI Trading System) kết hợp giữa:
- **Python Deterministic Logic Engine:** Tính toán chỉ báo, xác định vùng Order Block/FVG, quản lý vốn cứng.
- **RAG & LLM Brain (Google Gemini 2.0 Flash):** Phản biện bối cảnh kỹ thuật, so sánh với quy tắc Master và chấm điểm rủi ro.
- **Human-in-the-loop (Telegram UI):** Cung cấp giao diện bấm nút Approve/Reject để người dùng làm chốt chặn rủi ro cuối cùng trước khi đặt lệnh vào MT5.

## 2. Luồng dữ liệu (Dataflow Diagram)
1. `main.py` chạy vòng lặp Event Loop mỗi 10 giây.
2. Khi có nến M15 mới -> `core/mt5_loader.py` kéo dữ liệu OHLCV XAUUSD từ MT5 Terminal.
3. `core/indicators.py` tính toán EMA, RSI, ATR, tìm vùng FVG và Order Block M15/H1.
4. `core/risk_engine.py` kiểm tra các điều kiện rủi ro cứng (Spread, Giờ tin tức, Lot size).
5. Nếu thỏa mãn điều kiện cứng -> `rag/vector_store.py` trích xuất các quy tắc Master liên quan từ ChromaDB.
6. `brain/ai_agent.py` gửi Bối cảnh + Quy tắc RAG sang Gemini 2.0 Flash API (với Pydantic Structured Output) để xin đánh giá.
7. Nếu Gemini trả về `decision: "PASS"` -> `interface/telegram_bot.py` gửi thông báo kèm nút [APPROVE] / [REJECT].
8. Người dùng bấm [APPROVE] -> `execution/mt5_execution.py` gửi lệnh Pending Order (Buy/Sell Limit) sang MT5 và lưu vào `execution/journal_db.py`.

## 3. Công nghệ sử dụng (Tech Stack)
- Language: Python 3.11+
- Market API: `MetaTrader5` Python Library
- Analysis: `pandas`, `pandas-ta`, `numpy`
- Vector DB: `chromadb` (Local) + `sentence-transformers` (`all-MiniLM-L6-v2`)
- AI Model: `google-genai` (Gemini 2.0 Flash Free API)
- Communication: `python-telegram-bot`
- Database: `sqlite3`