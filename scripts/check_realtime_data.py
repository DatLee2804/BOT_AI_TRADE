"""Script to test live connection to MetaTrader 5 and pull real-time XAUUSD data."""
import sys
import os
from datetime import datetime, timezone
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import MetaTrader5 as mt5
except ImportError:
    print("[ERROR] Thư viện MetaTrader5 chưa được cài đặt!")
    sys.exit(1)

from config.settings import settings


def find_installed_mt5_paths():
    """Find installed MT5 paths on the system."""
    candidates = [
        r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe",
        r"C:\Program Files\BCR MT5\terminal64.exe",
        r"C:\Program Files\MetaTrader 5\terminal64.exe",
    ]
    return [p for p in candidates if os.path.exists(p)]


def main():
    print("=" * 70)
    print("🔍 KIỂM TRA KẾT NỐI VÀ LẤY DỮ LIỆU XAUUSD REALTIME TỪ MT5")
    print("=" * 70)

    # 1. Initialize MT5
    installed = find_installed_mt5_paths()
    init_path = settings.MT5_PATH if settings.MT5_PATH and os.path.exists(settings.MT5_PATH) else (installed[0] if installed else None)

    print(f"\n[1] Đang kết nối tới MT5 Terminal...")
    if init_path:
        print(f"    -> Đường dẫn Terminal: {init_path}")
        connected = mt5.initialize(path=init_path)
    else:
        connected = mt5.initialize()

    if not connected:
        print(f"[FAIL] Không thể khởi động MT5! Lỗi: {mt5.last_error()}")
        print("\n💡 HƯỚNG DẪN:")
        print("  1. Hãy mở sẵn ứng dụng MetaTrader 5 trên máy tính và đăng nhập vào tài khoản.")
        print("  2. Sau đó chạy lại script này.")
        return

    print("    -> Kết nối MT5 Terminal thành công! ✅")

    # 2. Account info
    terminal_info = mt5.terminal_info()
    account_info = mt5.account_info()

    if terminal_info:
        print(f"    -> Terminal: {terminal_info.name} (Build {terminal_info.build})")
        print(f"    -> Kết nối mạng: {'Đã kết nối' if terminal_info.connected else 'Chưa kết nối broker'}")

    if account_info:
        print(f"    -> Tài khoản: #{account_info.login} ({account_info.name})")
        print(f"    -> Server: {account_info.server}")
        print(f"    -> Số dư (Balance): ${account_info.balance:.2f} {account_info.currency}")
        print(f"    -> Đòn bẩy (Leverage): 1:{account_info.leverage}")
    else:
        print("    -> [Lưu ý] Chưa đăng nhập tài khoản giao dịch trong MT5.")

    # 3. Find Gold Symbol
    target_symbol = settings.SYMBOL
    symbols = mt5.symbols_get()
    all_symbol_names = [s.name for s in symbols] if symbols else []

    # Find exact or similar symbol (e.g. XAUUSD, XAUUSDm, XAUUSD.m, GOLD)
    gold_matches = [s for s in all_symbol_names if "XAU" in s.upper() or "GOLD" in s.upper()]
    print(f"\n[2] Các mã Vàng tìm thấy trên sàn ({len(gold_matches)} mã): {gold_matches}")

    # Prioritize XAUUSD variations: XAUUSD, XAUUSDm, XAUUSD.m, XAUUSD247m, GOLD
    candidate_symbols = [target_symbol, f"{target_symbol}m", f"{target_symbol}.m", f"{target_symbol}247m", "GOLD", "GOLDm"]
    matched_symbol = None
    for cand in candidate_symbols:
        if cand in all_symbol_names:
            matched_symbol = cand
            break

    if not matched_symbol and len(gold_matches) > 0:
        # Avoid crypto cross pairs like BTCXAU
        xau_usd_likes = [s for s in gold_matches if "USD" in s.upper()]
        matched_symbol = xau_usd_likes[0] if xau_usd_likes else gold_matches[0]

    if matched_symbol:
        print(f"    -> Đã chọn chuẩn xác cặp Vàng/USD: '{matched_symbol}'")
    else:
        print(f"[FAIL] Không tìm thấy mã XAUUSD hoặc GOLD trên sàn này!")
        mt5.shutdown()
        return

    # Select symbol in Market Watch
    if not mt5.symbol_select(matched_symbol, True):
        print(f"[WARN] Không thể đưa {matched_symbol} vào Market Watch.")

    sym_info = mt5.symbol_info(matched_symbol)
    if not sym_info:
        print(f"[FAIL] Không lấy được thông tin symbol {matched_symbol}!")
        mt5.shutdown()
        return

    print(f"\n[3] THÔNG SỐ CỦA CẶP {matched_symbol}:")
    print(f"    • Digits: {sym_info.digits}")
    print(f"    • Point: {sym_info.point}")
    print(f"    • Contract Size: {sym_info.trade_contract_size}")
    print(f"    • Min Lot: {sym_info.volume_min} | Step: {sym_info.volume_step} | Max: {sym_info.volume_max}")

    # 4. Real-time Tick
    tick = mt5.symbol_info_tick(matched_symbol)
    if tick:
        tick_time = datetime.fromtimestamp(tick.time, timezone.utc)
        spread_price = tick.ask - tick.bid
        pip_size = 0.10 if "XAU" in matched_symbol.upper() or "GOLD" in matched_symbol.upper() else (sym_info.point * 10)
        spread_pips = spread_price / pip_size if pip_size > 0 else (spread_price / sym_info.point)

        print(f"\n[4] ⚡ GIÁ THỜI GIAN THẬT (LIVE TICK):")
        print(f"    • Thời gian Tick (UTC): {tick_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"    • Giá Mua (Ask):  {tick.ask:.{sym_info.digits}f}")
        print(f"    • Giá Bán (Bid):  {tick.bid:.{sym_info.digits}f}")
        print(f"    • Giá Cuối (Last): {tick.last:.{sym_info.digits}f}")
        print(f"    • Spread:         {spread_price:.{sym_info.digits}f} (${spread_price:.2f}) ~ {spread_pips:.2f} pips")
    else:
        print("[WARN] Chưa có tick thời gian thật (có thể ngoài giờ giao dịch hoặc MT5 chưa có mạng).")

    # 5. Fetch OHLCV candles
    timeframes = [
        ("M15", mt5.TIMEFRAME_M15),
        ("H1", mt5.TIMEFRAME_H1),
        ("H4", mt5.TIMEFRAME_H4),
    ]

    print(f"\n[5] 📊 DỮ LIỆU NẾN THỜI GIAN THẬT TỪ SÀN:")
    for tf_name, tf_const in timeframes:
        rates = mt5.copy_rates_from_pos(matched_symbol, tf_const, 0, 5)
        if rates is not None and len(rates) > 0:
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            print(f"\n--- 5 Nến {tf_name} gần nhất của {matched_symbol} ---")
            for _, row in df.iterrows():
                print(f"  [{row['time']}] O: {row['open']:.2f} | H: {row['high']:.2f} | L: {row['low']:.2f} | C: {row['close']:.2f} | Vol: {row['tick_volume']}")
        else:
            print(f"  [!] Chưa kéo được nến {tf_name}. Lỗi: {mt5.last_error()}")

    print("\n" + "=" * 70)
    print("✅ HOÀN TẤT KIỂM TRA DỮ LIỆU THỜI GIAN THẬT")
    print("=" * 70)
    mt5.shutdown()


if __name__ == "__main__":
    main()
