"""H1 Price Action Channel & Market Structure Indicator Engine.
Computes Swing Points, Market Structure Channels (Dow Theory), Candlestick Reversal Patterns,
EMAs, RSI, ATR, and generates H1 Trade Setups for Gemini AI validation.
"""
import logging
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
import numpy as np

try:
    import pandas_ta as ta
except ImportError:
    ta = None

logger = logging.getLogger("core.indicators")


def calculate_basic_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate baseline technical indicators (EMA 20, 50, 200, RSI 14, ATR 14)."""
    df = df.copy()
    try:
        if ta is not None:
            df["ema_20"] = ta.ema(df["close"], length=20)
            df["ema_50"] = ta.ema(df["close"], length=50)
            df["ema_200"] = ta.ema(df["close"], length=200)
            df["rsi"] = ta.rsi(df["close"], length=14)
            df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
        else:
            # Pure pandas fallback
            df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()
            df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
            df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()
            
            delta = df["close"].diff()
            gain = delta.clip(lower=0)
            loss = -1 * delta.clip(upper=0)
            avg_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
            rs = avg_gain / (avg_loss + 1e-9)
            df["rsi"] = 100 - (100 / (1 + rs))

            high_low = df["high"] - df["low"]
            high_close = (df["high"] - df["close"].shift()).abs()
            low_close = (df["low"] - df["close"].shift()).abs()
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df["atr"] = tr.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()

    except Exception as e:
        logger.error(f"Error in calculate_basic_indicators: {str(e)}")

    return df


def find_swing_points(df: pd.DataFrame, window: int = 3) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Identify raw Swing High / Swing Low points.
    A candle is a Swing High if its high exceeds 'window' bars to the left and right.
    """
    swing_highs: List[Dict[str, Any]] = []
    swing_lows: List[Dict[str, Any]] = []

    if len(df) < (window * 2 + 1):
        return swing_highs, swing_lows

    has_time = "time" in df.columns

    for i in range(window, len(df) - window):
        try:
            curr_high = float(df["high"].iloc[i])
            curr_low = float(df["low"].iloc[i])
            bar_time = str(df["time"].iloc[i]) if has_time else str(i)

            # Swing High
            is_high = all(curr_high > float(df["high"].iloc[i - j]) for j in range(1, window + 1)) and \
                      all(curr_high > float(df["high"].iloc[i + j]) for j in range(1, window + 1))
            if is_high:
                swing_highs.append({"index": i, "price": curr_high, "time": bar_time})

            # Swing Low
            is_low = all(curr_low < float(df["low"].iloc[i - j]) for j in range(1, window + 1)) and \
                     all(curr_low < float(df["low"].iloc[i + j]) for j in range(1, window + 1))
            if is_low:
                swing_lows.append({"index": i, "price": curr_low, "time": bar_time})

        except Exception as e:
            logger.error(f"Error checking swing point at index {i}: {str(e)}")

    return swing_highs, swing_lows


def analyze_market_structure_h1(df_h1: pd.DataFrame) -> Dict[str, Any]:
    """Determine Market Structure Channel (Uptrend/Downtrend Channel or Sideway) based on Swing Points."""
    swing_highs, swing_lows = find_swing_points(df_h1, window=3)

    # Safe fallback if not enough swing points are confirmed yet
    recent_low = float(df_h1["low"].iloc[-20:].min()) if len(df_h1) >= 20 else float(df_h1["low"].min())
    recent_high = float(df_h1["high"].iloc[-20:].max()) if len(df_h1) >= 20 else float(df_h1["high"].max())

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return {
            "market_structure": "SIDEWAY",
            "last_support": recent_low,
            "last_resistance": recent_high,
            "prev_support": recent_low,
            "prev_resistance": recent_high,
            "details": "Chưa đủ dữ liệu swing points để dựng kênh giá."
        }

    # Extract 2 most recent swing highs and lows
    sh1, sh2 = swing_highs[-2]["price"], swing_highs[-1]["price"]
    sl1, sl2 = swing_lows[-2]["price"], swing_lows[-1]["price"]

    # Market structure channel logic
    if sh2 > sh1 and sl2 > sl1:
        structure = "UPTREND_CHANNEL"  # Higher High (HH) + Higher Low (HL)
    elif sh2 < sh1 and sl2 < sl1:
        structure = "DOWNTREND_CHANNEL"  # Lower High (LH) + Lower Low (LL)
    else:
        structure = "SIDEWAY"  # Range bound / accumulation

    return {
        "market_structure": structure,
        "last_support": sl2,
        "last_resistance": sh2,
        "prev_support": sl1,
        "prev_resistance": sh1,
        "details": f"SH: {sh1:.2f} -> {sh2:.2f} | SL: {sl1:.2f} -> {sl2:.2f}"
    }


def detect_reversal_patterns(df: pd.DataFrame) -> Optional[str]:
    """Detect reversal candlestick patterns on the most recently closed candle:
    - Bullish Engulfing / Bullish Pinbar -> 'BULLISH_REVERSAL'
    - Bearish Engulfing / Bearish Pinbar -> 'BEARISH_REVERSAL'
    Uses the completed closed candle (iloc[-2]) compared against iloc[-3] to avoid false intra-bar noise.
    """
    if len(df) < 3:
        return None

    # In live data, iloc[-1] is active forming candle, iloc[-2] is the completed closed candle
    c_prev = df.iloc[-3]
    c_closed = df.iloc[-2]

    o_prev, c_prev_val = float(c_prev["open"]), float(c_prev["close"])
    o_curr, c_curr_val = float(c_closed["open"]), float(c_closed["close"])
    h_curr, l_curr = float(c_closed["high"]), float(c_closed["low"])

    # 1. Bullish Engulfing: previous bar bearish, closed bar bullish covering previous body
    if c_prev_val < o_prev and c_curr_val > o_curr:
        if c_curr_val >= o_prev and o_curr <= (c_prev_val + 0.1):
            return "BULLISH_REVERSAL"

    # 2. Bearish Engulfing: previous bar bullish, closed bar bearish covering previous body
    if c_prev_val > o_prev and c_curr_val < o_curr:
        if c_curr_val <= o_prev and o_curr >= (c_prev_val - 0.1):
            return "BEARISH_REVERSAL"

    # 3. Pinbar Detection
    body = abs(c_curr_val - o_curr)
    body = max(body, 0.05)
    lower_wick = min(o_curr, c_curr_val) - l_curr
    upper_wick = h_curr - max(o_curr, c_curr_val)

    # Bullish Pinbar: long bottom tail >= 2x body and > upper wick
    if lower_wick >= 2.0 * body and lower_wick > (upper_wick * 1.5):
        return "BULLISH_REVERSAL"

    # Bearish Pinbar: long upper tail >= 2x body and > lower wick
    if upper_wick >= 2.0 * body and upper_wick > (lower_wick * 1.5):
        return "BEARISH_REVERSAL"

    return None


def calculate_trade_setup_h1(
    df_h1: pd.DataFrame,
    min_rr: float = 2.5,
    atr_mult: float = 1.5
) -> Optional[Dict[str, Any]]:
    """Synthesize H1 Market Structure and Candlestick Reversal patterns into a structured Trade Setup."""
    if len(df_h1) < 20:
        logger.warning("Insufficient H1 bars to calculate trade setup.")
        return None

    df_ind = calculate_basic_indicators(df_h1)
    structure_info = analyze_market_structure_h1(df_ind)
    reversal_pattern = detect_reversal_patterns(df_ind)

    current_price = float(df_ind["close"].iloc[-1])
    atr_val = float(df_ind["atr"].iloc[-1]) if "atr" in df_ind.columns and not np.isnan(df_ind["atr"].iloc[-1]) else 2.5
    atr_val = max(atr_val, 1.0)
    structure = structure_info["market_structure"]

    rsi_val = float(df_ind["rsi"].iloc[-1]) if "rsi" in df_ind.columns and not np.isnan(df_ind["rsi"].iloc[-1]) else 50.0

    setup: Optional[Dict[str, Any]] = None

    # BUY SCENARIO: Uptrend Channel or Sideway at Support + Bullish Reversal pattern
    if structure in ["UPTREND_CHANNEL", "SIDEWAY"] and reversal_pattern == "BULLISH_REVERSAL":
        entry = current_price
        sl = round(structure_info["last_support"] - (atr_mult * atr_val), 2)
        risk = max(entry - sl, 1.0)
        tp = round(entry + (min_rr * risk), 2)
        rr_actual = round((tp - entry) / risk, 2)

        setup = {
            "signal_type": "BUY_LIMIT",
            "type": "BUY_LIMIT",
            "entry_price": round(entry, 2),
            "entry": round(entry, 2),
            "sl_price": sl,
            "sl": sl,
            "tp_price": tp,
            "tp": tp,
            "rr_ratio": rr_actual,
            "risk_pips": round(risk * 10, 1),
            "current_price": round(current_price, 2),
            "market_structure": structure,
            "structure": structure,
            "pattern": reversal_pattern,
            "h1_trend": structure,
            "rsi_h1": round(rsi_val, 1),
            "atr": round(atr_val, 2),
        }

    # SELL SCENARIO: Downtrend Channel or Sideway at Resistance + Bearish Reversal pattern
    elif structure in ["DOWNTREND_CHANNEL", "SIDEWAY"] and reversal_pattern == "BEARISH_REVERSAL":
        entry = current_price
        sl = round(structure_info["last_resistance"] + (atr_mult * atr_val), 2)
        risk = max(sl - entry, 1.0)
        tp = round(entry - (min_rr * risk), 2)
        rr_actual = round((entry - tp) / risk, 2)

        setup = {
            "signal_type": "SELL_LIMIT",
            "type": "SELL_LIMIT",
            "entry_price": round(entry, 2),
            "entry": round(entry, 2),
            "sl_price": sl,
            "sl": sl,
            "tp_price": tp,
            "tp": tp,
            "rr_ratio": rr_actual,
            "risk_pips": round(risk * 10, 1),
            "current_price": round(current_price, 2),
            "market_structure": structure,
            "structure": structure,
            "pattern": reversal_pattern,
            "h1_trend": structure,
            "rsi_h1": round(rsi_val, 1),
            "atr": round(atr_val, 2),
        }

    return setup


class TechnicalAnalyzer:
    """Wrapper class providing object-oriented access to H1 price action indicators."""

    @staticmethod
    def calculate_basic_indicators(df: pd.DataFrame) -> pd.DataFrame:
        return calculate_basic_indicators(df)

    @staticmethod
    def find_swing_points(df: pd.DataFrame, window: int = 3) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        return find_swing_points(df, window)

    @staticmethod
    def analyze_market_structure_h1(df_h1: pd.DataFrame) -> Dict[str, Any]:
        return analyze_market_structure_h1(df_h1)

    @staticmethod
    def detect_reversal_patterns(df: pd.DataFrame) -> Optional[str]:
        return detect_reversal_patterns(df)

    @staticmethod
    def calculate_trade_setup(
        df_h1: pd.DataFrame,
        df_m15: Optional[pd.DataFrame] = None,
        df_h4: Optional[pd.DataFrame] = None,
        min_rr: float = 2.5,
        atr_mult: float = 1.5,
    ) -> Optional[Dict[str, Any]]:
        """Unified entrypoint for trade setup calculation."""
        return calculate_trade_setup_h1(df_h1=df_h1, min_rr=min_rr, atr_mult=atr_mult)

    @staticmethod
    def calculate_trade_setup_h1(
        df_h1: pd.DataFrame,
        min_rr: float = 2.5,
        atr_mult: float = 1.5,
    ) -> Optional[Dict[str, Any]]:
        return calculate_trade_setup_h1(df_h1=df_h1, min_rr=min_rr, atr_mult=atr_mult)


technical_analyzer = TechnicalAnalyzer()