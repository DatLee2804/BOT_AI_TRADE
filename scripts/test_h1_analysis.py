"""Test H1 Price Action Analysis on Live MT5 Exness Data."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from config.settings import settings
from core.mt5_loader import mt5_loader
from core.indicators import (
    calculate_basic_indicators,
    find_swing_points,
    analyze_market_structure_h1,
    detect_reversal_patterns,
    calculate_trade_setup_h1,
)


def main():
    print("=" * 70)
    print("📈 KIỂM TRA PHÂN TÍCH H1 PRICE ACTION TRÊN DỮ LIỆU SÀN EXNESS")
    print("=" * 70)

    symbol = settings.SYMBOL
    print(f"\n[1] Kéo 100 nến H1 của {symbol}...")
    df_h1 = mt5_loader.get_ohlcv(symbol, "H1", n_bars=100)

    if df_h1 is None or len(df_h1) < 20:
        print(f"[FAIL] Không lấy được dữ liệu nến H1 cho {symbol}!")
        mt5_loader.shutdown()
        return

    print(f"    -> Đã lấy thành công {len(df_h1)} nến H1.")
    latest_bar = df_h1.iloc[-1]
    closed_bar = df_h1.iloc[-2]
    print(f"    -> Nến vừa đóng [H1]: {closed_bar.get('time')} | O:{closed_bar['open']} H:{closed_bar['high']} L:{closed_bar['low']} C:{closed_bar['close']}")
    print(f"    -> Nến đang chạy [H1]: {latest_bar.get('time')} | Giá hiện tại: {latest_bar['close']}")

    # 2. Indicators
    df_ind = calculate_basic_indicators(df_h1)
    print(f"\n[2] CHỈ BÁO KỸ THUẬT H1:")
    print(f"    • EMA 20:  {df_ind['ema_20'].iloc[-1]:.2f}")
    print(f"    • EMA 50:  {df_ind['ema_50'].iloc[-1]:.2f}")
    print(f"    • EMA 200: {df_ind['ema_200'].iloc[-1]:.2f}")
    print(f"    • RSI (14): {df_ind['rsi'].iloc[-1]:.1f}")
    print(f"    • ATR (14): {df_ind['atr'].iloc[-1]:.2f}")

    # 3. Market Structure
    highs, lows = find_swing_points(df_h1, window=3)
    structure_info = analyze_market_structure_h1(df_h1)
    print(f"\n[3] CẤU TRÚC KÊNH GIÁ (MARKET STRUCTURE H1):")
    print(f"    • Trạng thái kênh giá: {structure_info['market_structure']}")
    print(f"    • Hỗ trợ gần nhất (Support / Đáy):    {structure_info['last_support']:.2f}")
    print(f"    • Kháng cự gần nhất (Resistance / Đỉnh): {structure_info['last_resistance']:.2f}")
    print(f"    • Tổng số đỉnh Swing High tìm thấy: {len(highs)}")
    print(f"    • Tổng số đáy Swing Low tìm thấy:  {len(lows)}")
    if len(highs) >= 2:
        print(f"    • 2 Đỉnh gần nhất: {highs[-2]['price']:.2f} -> {highs[-1]['price']:.2f}")
    if len(lows) >= 2:
        print(f"    • 2 Đáy gần nhất:  {lows[-2]['price']:.2f} -> {lows[-1]['price']:.2f}")

    # 4. Candlestick Reversal Pattern
    pattern = detect_reversal_patterns(df_ind)
    print(f"\n[4] MÔ HÌNH NẾN ĐẢO CHIỀU (REVERSAL PATTERN):")
    print(f"    • Tín hiệu nến vừa đóng: {pattern if pattern else 'Không có mô hình đảo chiều đặc biệt'}")

    # 5. Trade setup
    setup = calculate_trade_setup_h1(df_h1, min_rr=2.5, atr_mult=1.5)
    print(f"\n[5] KẾ HOẠCH GIAO DỊCH (SETUP):")
    if setup:
        print(f"    🎯 TÌM THẤY SETUP ĐẠT CHUẨN!")
        print(f"    • Lệnh: {setup['signal_type']} @ {setup['entry_price']}")
        print(f"    • Stop Loss: {setup['sl_price']} | Take Profit: {setup['tp_price']}")
        print(f"    • Tỷ lệ R:R: 1:{setup['rr_ratio']}")
        print(f"    • Rủi ro: {setup['risk_pips']} pips")
    else:
        print(f"    ⏳ Chưa thỏa mãn đồng thời (Kênh giá + Nến đảo chiều tại cản). Đang kiên nhẫn chờ thời cơ theo đúng Master Rules.")

    print("\n" + "=" * 70)
    mt5_loader.shutdown()


if __name__ == "__main__":
    main()
