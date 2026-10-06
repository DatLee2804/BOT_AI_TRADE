"""Risk Management Engine Module.
Performs hard validation checks: Realtime Spread, Economic News Filter, and Lot Size Calculation.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
try:
    import requests
except ImportError:
    requests = None

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from config.settings import settings

logger = logging.getLogger("core.risk_engine")


class RiskEngine:
    """Deterministic hard risk filter and position sizing calculator."""

    def __init__(self) -> None:
        self.cached_news: List[Dict[str, Any]] = []
        self.last_news_fetch: Optional[datetime] = None

    def check_spread(self, symbol: str = "XAUUSD", max_allowed_pips: Optional[float] = None) -> bool:
        """Check real-time spread from MT5 terminal.
        
        Args:
            symbol: Trading pair symbol.
            max_allowed_pips: Maximum permitted spread in pips (e.g., 2.5 pips = $0.25 on gold).
            
        Returns:
            True if spread is within safe threshold, False otherwise.
        """
        max_pips = max_allowed_pips if max_allowed_pips is not None else settings.MAX_SPREAD_PIPS

        if mt5 is None:
            logger.warning("MT5 module not imported. Spread check defaulted to True.")
            return True

        try:
            tick = mt5.symbol_info_tick(symbol)
            symbol_info = mt5.symbol_info(symbol)

            if tick is None or symbol_info is None:
                logger.warning(f"Could not retrieve tick or symbol info for {symbol}. Spread check failed.")
                return False

            point = symbol_info.point
            # On Gold (XAUUSD), 1 pip = 0.10 (10 points) or 0.01 depending on broker digits
            # Digits == 2: point = 0.01, 1 pip = 0.10 = 10 points
            # Digits == 3: point = 0.001, 1 pip = 0.10 = 100 points
            pip_size = 0.10 if "XAU" in symbol.upper() or "GOLD" in symbol.upper() else (point * 10)
            
            raw_spread_price = tick.ask - tick.bid
            current_spread_pips = raw_spread_price / pip_size if pip_size > 0 else (raw_spread_price / point)

            logger.info(f"[{symbol}] Realtime Ask: {tick.ask}, Bid: {tick.bid} | Spread: {current_spread_pips:.2f} pips (Max: {max_pips:.2f})")

            if current_spread_pips > max_pips:
                logger.warning(f"Spread {current_spread_pips:.2f} exceeds max allowed {max_pips:.2f} pips!")
                return False

            return True

        except Exception as e:
            logger.error(f"Error in check_spread: {str(e)}")
            return False

    def check_news_filter(self, buffer_minutes: Optional[int] = None) -> bool:
        """Check economic calendar for high impact (Red) news events.
        
        If current time is within `buffer_minutes` before or after major USD news (NFP, CPI, FOMC, Rate Decision),
        trading is halted.
        
        Returns:
            True if safe to trade, False if high impact news is imminent or occurring.
        """
        buf_min = buffer_minutes if buffer_minutes is not None else settings.NEWS_FILTER_MINUTES

        try:
            # Refresh economic news cache if older than 1 hour or empty
            now_utc = datetime.now(timezone.utc)
            if not self.cached_news or (self.last_news_fetch and (now_utc - self.last_news_fetch).total_seconds() > 3600):
                self._fetch_economic_calendar()

            # Inspect high-impact USD events
            high_impact_keywords = ["nfp", "non-farm", "cpi", "fomc", "fed interest rate", "unemployment", "pce"]
            buffer_delta = timedelta(minutes=buf_min)

            for event in self.cached_news:
                event_title = event.get("title", "").lower()
                event_currency = event.get("currency", "").upper()
                event_impact = event.get("impact", "").lower()
                event_time_utc = event.get("time_utc")

                if event_currency == "USD" and (event_impact in ["high", "red"] or any(k in event_title for k in high_impact_keywords)):
                    if isinstance(event_time_utc, datetime):
                        time_diff = abs(now_utc - event_time_utc)
                        if time_diff <= buffer_delta:
                            logger.warning(
                                f"High impact news detected: '{event.get('title')}' at {event_time_utc.isoformat()}. "
                                f"Time diff: {time_diff.total_seconds() / 60:.1f} mins (Buffer: {buf_min}m). Trading blocked!"
                            )
                            return False

            return True

        except Exception as e:
            logger.error(f"Error in check_news_filter: {str(e)}")
            return True  # Fallback to allow trade if calendar API is temporarily unreachable

    def _fetch_economic_calendar(self) -> None:
        """Fetch economic calendar events from public economic endpoint or fallback."""
        if requests is None:
            logger.warning("requests library is not installed yet.")
            return

        try:
            # ForexFactory or investing free json feed
            url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                events = resp.json()
                parsed = []
                for ev in events:
                    # Expected format: "2026-10-06T08:30:00-04:00"
                    ev_date_str = ev.get("date")
                    if ev_date_str:
                        dt = datetime.fromisoformat(ev_date_str).astimezone(timezone.utc)
                        parsed.append({
                            "title": ev.get("title", ""),
                            "currency": ev.get("country", ""),
                            "impact": ev.get("impact", ""),
                            "time_utc": dt
                        })
                self.cached_news = parsed
                self.last_news_fetch = datetime.now(timezone.utc)
                logger.info(f"Loaded {len(parsed)} economic calendar events for this week.")
            else:
                logger.warning(f"Could not fetch economic calendar, status: {resp.status_code}")
        except Exception as e:
            logger.error(f"Error in _fetch_economic_calendar: {str(e)}")

    def calculate_position_size(
        self,
        account_balance: float,
        risk_percent: float,
        sl_pips: float,
        symbol: str = "XAUUSD"
    ) -> float:
        """Calculate position size (lots) based on risk percentage and stop loss distance.
        
        Formula: Lot_Size = (Account_Balance * Risk_Percent / 100) / (SL_Pips * Pip_Value)
        
        Args:
            account_balance: Current account balance (e.g. $10,000).
            risk_percent: Risk percentage per trade (e.g. 1.0 for 1%).
            sl_pips: Stop Loss distance in pips.
            symbol: Symbol name.
            
        Returns:
            Calculated lot size rounded to step lot (usually 0.01).
        """
        try:
            if sl_pips <= 0:
                logger.warning("SL pips must be positive. Defaulting to 0.01 lot.")
                return 0.01

            risk_amount = account_balance * (risk_percent / 100.0)

            # On XAUUSD (Standard 100 oz contract), 1 pip (0.10) for 1 lot = $10.00
            # Pip value per 1 standard lot:
            pip_value = 10.0
            min_lot = 0.01
            max_lot = 50.0
            lot_step = 0.01

            if mt5 is not None:
                sym_info = mt5.symbol_info(symbol)
                if sym_info:
                    min_lot = sym_info.volume_min
                    max_lot = sym_info.volume_max
                    lot_step = sym_info.volume_step
                    # Point and contract size calculation
                    pip_size = 0.10 if "XAU" in symbol.upper() else (sym_info.point * 10)
                    if sym_info.trade_contract_size > 0:
                        pip_value = sym_info.trade_contract_size * pip_size

            # Position size calculation
            raw_lot = risk_amount / (sl_pips * pip_value)

            # Round to lot_step
            steps = round(raw_lot / lot_step)
            calculated_lot = round(steps * lot_step, 2)

            # Clamp between min_lot and max_lot
            final_lot = max(min_lot, min(calculated_lot, max_lot))

            logger.info(
                f"Position Size Sizing: Balance=${account_balance:.2f} | Risk={risk_percent}% (${risk_amount:.2f}) "
                f"| SL={sl_pips:.1f} pips -> Lot Size = {final_lot}"
            )
            return final_lot

        except Exception as e:
            logger.error(f"Error in calculate_position_size: {str(e)}")
            return 0.01


risk_engine = RiskEngine()
