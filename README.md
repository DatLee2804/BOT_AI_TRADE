# HYBRID AI TRADING BOT (XAUUSD) 🤖📈

Hệ thống Bot Giao dịch Vàng tự động kết hợp giữa **Python Deterministic Logic Engine**, **Local RAG + Google Gemini 2.0 Flash**, và cơ chế **Human-in-the-loop qua Telegram**.

---

## 🏗️ Kiến trúc hệ thống & Luồng xử lý

```text
[MT5 Terminal] ──(OHLCV M15/H1/H4)──> [core/mt5_loader.py]
                                               │
                                               ▼
                                      [core/indicators.py] (EMA, RSI, ATR, FVG, OB)
                                               │
                                               ▼
                                     [core/risk_engine.py] (Spread, Red News, Lot Size)
                                               │
                                               ▼ (Thỏa mãn bộ lọc)
   [ChromaDB Local RAG] ──(Master Rules)──> [brain/ai_agent.py] (Gemini 2.0 Flash)
                                               │
                                               ▼ (AI PASS >= 75 Điểm)
                                    [interface/telegram_bot.py]
                                        [✅ APPROVE]  [❌ REJECT]
                                               │ (Bấm APPROVE)
                                               ▼
                                   [execution/mt5_execution.py] ──> [Bắn lệnh MT5]
                                               │
                                               ▼
                                    [execution/journal_db.py] (SQLite)
```

---

## 📁 Cấu trúc thư mục chuẩn

```text
BOT_AI_PYTHON/
├── .docs/                   # Tài liệu thiết kế hệ thống
├── config/                  # Load cấu hình và biến môi trường
│   ├── __init__.py
│   └── settings.py
├── core/                    # Engine tính toán số học & MT5 loader
│   ├── __init__.py
│   ├── mt5_loader.py        # Kết nối MT5, kéo nến M15, H1, H4
│   ├── indicators.py        # Tính EMA, RSI, ATR, FVG, Order Block, RR >= 1:2.5
│   └── risk_engine.py       # Lọc Spread, lọc tin tức đỏ, tính Lot Size
├── rag/                     # RAG Vector Store & Tri thức giao dịch
│   ├── __init__.py
│   ├── knowledge_base/
│   │   ├── master_rules.md  # Quy tắc cấm & kịch bản lệnh A+
│   │   └── case_studies.md  # Lịch sử các lệnh thắng/thua mẫu
│   └── vector_store.py      # ChromaDB Local + SentenceTransformers all-MiniLM-L6-v2
├── brain/                   # AI Brain phản biện và chấm điểm
│   ├── __init__.py
│   ├── prompts.py           # Pydantic Structured Output Schema & System Prompt
│   └── ai_agent.py          # Google GenAI SDK (Gemini 2.0 Flash)
├── interface/               # Giao diện người dùng
│   ├── __init__.py
│   └── telegram_bot.py      # Gửi tín hiệu HTML kèm nút Approve / Reject
├── execution/               # Thực thi lệnh và ghi nhật ký
│   ├── __init__.py
│   ├── mt5_execution.py     # Đặt lệnh Pending Order (Buy/Sell Limit) vào MT5
│   └── journal_db.py        # SQLite Database lưu trữ lịch sử lệnh
├── tests/                   # Bộ kiểm thử tự động (13 tests OK)
├── .env                     # File cấu hình thông số & API Keys
├── .env.example             # File mẫu hướng dẫn điền cấu hình
├── main.py                  # Vòng lặp điều phối chính (Event Loop 10s)
└── requirements.txt         # Danh sách thư viện phụ thuộc
```

---

## 🚀 Hướng dẫn cài đặt & Khởi chạy

### 1. Kích hoạt môi trường ảo:
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Cấu hình file `.env`:
Mở file `.env` và điền các thông tin:
```env
# MetaTrader 5
MT5_ACCOUNT=12345678
MT5_PASSWORD=mat_khau_mt5
MT5_SERVER=TenServerBroker-Demo
MT5_PATH=C:\Program Files\MetaTrader 5\terminal64.exe

# Google Gemini API
GEMINI_API_KEY=AIzaSy...

# Telegram Bot
TELEGRAM_BOT_TOKEN=123456789:ABCdef...
TELEGRAM_CHAT_ID=987654321

# Trading Parameters
SYMBOL=XAUUSD
TIMEFRAME=M15
MAX_SPREAD_PIPS=2.5
RISK_PERCENT=1.0
MAGIC_NUMBER=888999
MIN_RR_RATIO=2.5
```

### 3. Chạy kiểm thử hệ thống:
```powershell
.\.venv\Scripts\python.exe -m unittest discover tests
```

### 4. Khởi chạy Bot giao dịch:
```powershell
.\.venv\Scripts\python.exe main.py
```
# BOT_AI_TRADE
