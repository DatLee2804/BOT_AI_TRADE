### File 3: `02_CORE_ENGINE.md`

```markdown
# TECHNICAL SPECIFICATION: CORE ENGINE (`core/`)

Module `core/` chịu trách nhiệm toàn bộ về tính toán số học, tuyệt đối KHÔNG gọi AI ở module này.

## 1. `core/mt5_loader.py`
- Kết nối tới MT5 bằng `mt5.initialize()`. Sử dụng thông tin từ `config/settings.py`.
- Hàm `get_ohlcv(symbol, timeframe, n_bars)`: Kéo dữ liệu nến H4, H1, M15 và trả về dưới dạng `pandas.DataFrame` gồm các cột `[time, open, high, low, close, tick_volume]`.

## 2. `core/indicators.py`
- Sử dụng `pandas_ta` để tính toán:
  - EMA 20, EMA 50, EMA 200 trên các khung H4, H1, M15.
  - RSI (14) trên khung H1 và M15.
  - ATR (14) trên khung M15 để làm căn cứ tính Stop Loss.
- Thuật toán phát hiện **Fair Value Gap (FVG)** khung M15:
  - Bullish FVG: `Low[i] > High[i-2]` (Vùng FVG từ `High[i-2]` đến `Low[i]`).
  - Bearish FVG: `High[i] < Low[i-2]` (Vùng FVG từ `Low[i]` đến `High[i-2]`).
- Thuật toán xác định **Order Block (OB)** M15:
  - Vùng nến giảm cuối cùng trước một nhịp tăng phá đỉnh (CHOCH/BOS) gần nhất.
- Hàm `calculate_trade_setup()`:
  - Tính vị trí Entry = Vùng biên FVG/OB M15.
  - Tính SL = `Đáy OB/FVG - (1.5 * ATR)`.
  - Tính TP = Theo tỷ lệ R:R tối thiểu 1:2.5 hoặc đỉnh gần nhất.
  - Trả về 1 `dict` đầy đủ các thông số thực số học (float).

## 3. `core/risk_engine.py`
- Hàm `check_spread(symbol, max_allowed_pip)`: Lấy spread real-time từ MT5, nếu `spread > max_allowed` -> Trả về `False`.
- Hàm `check_news_filter()`: Kiểm tra lịch kinh tế (mockup hoặc cào từ API tin tức), nếu cách tin đỏ (NFP, CPI, FOMC) <= 30 phút -> Trả về `False`.
- Hàm `calculate_position_size(account_balance, risk_percent, sl_pips, symbol)`:
  - Công thức: `Lot_Size = (Account_Balance * Risk_Percent) / (SL_Pips * Pip_Value)`.
  - Làm tròn lot size theo bước khối lượng quy định của sàn (thường là 0.01).