# PROJECT STRUCTURE & MODULE RESPONSIBILITIES

AI Agent phải tuân thủ chính xác cấu trúc cây thư mục dưới đây. Không tạo các file ngoài danh sách nếu không được yêu cầu.

```text
ai_trading_bot/
├── .docs/                   # Thư mục chứa tài liệu hướng dẫn cho AI Agent
├── config/
│   ├── __init__.py
│   └── settings.py          # Load env vars, cấu hình hằng số (Spread max, Risk %, Pairs)
├── core/
│   ├── __init__.py
│   ├── mt5_loader.py        # Hàm kết nối MT5, kéo dữ liệu H4, H1, M15
│   ├── indicators.py        # Hàm tính EMA, RSI, ATR, FVG, Order Block, Entry/SL/TP
│   └── risk_engine.py       # Bộ lọc cứng: Max Spread, Giờ tin tức, Lot size
├── rag/
│   ├── __init__.py
│   ├── knowledge_base/
│   │   ├── master_rules.md  # File chứa các quy tắc cấm & kịch bản A+
│   │   └── case_studies.md  # File chứa các lệnh mẫu thắng/thua
│   └── vector_store.py      # Quản lý ChromaDB local, Embedding và Query RAG
├── brain/
│   ├── __init__.py
│   ├── prompts.py           # Pydantic Output Schema & System Prompt Templates
│   └── ai_agent.py          # Hàm gọi Gemini 2.0 Flash suy luận bối cảnh
├── interface/
│   ├── __init__.py
│   └── telegram_bot.py      # Bot Telegram gửi tin nhắn & lắng nghe nút bấm Approve
├── execution/
│   ├── __init__.py
│   ├── mt5_execution.py     # Hàm bắn lệnh Pending Order sang MT5 Terminal
│   └── journal_db.py        # SQLite Database lưu lịch sử phân tích và kết quả lệnh
├── .env                     # Lưu API Keys & MT5 Account Info
├── main.py                  # Event Loop kiểm tra nến M15 & điều phối quy trình
└── requirements.txt         # Dependencies