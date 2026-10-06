"""AI Reasoning Agent utilizing Google Gemini 2.0 Flash SDK.
Combines technical market indicators with RAG knowledge rules and enforces Pydantic structured output.
"""
import json
import logging
from typing import Dict, Any, List, Optional

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

from config.settings import settings
from brain.prompts import TradeDecisionSchema, SYSTEM_PROMPT_TEMPLATE

logger = logging.getLogger("brain.ai_agent")


class AIAgent:
    """Evaluates trading setups using Gemini 2.0 Flash and Master Trader RAG rules."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None) -> None:
        self.api_key: str = api_key or settings.GEMINI_API_KEY
        self.model_name: str = model_name or settings.GEMINI_MODEL
        self.client: Optional[Any] = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize the Google GenAI client."""
        if genai is None:
            logger.error("Error in _init_client: google-genai library is not installed.")
            return

        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not configured in .env.")
            return

        try:
            self.client = genai.Client(api_key=self.api_key)
            logger.info(f"Gemini Client initialized successfully with model '{self.model_name}'.")
        except Exception as e:
            logger.error(f"Error in _init_client: {str(e)}")
            self.client = None

    def analyze_market_setup(
        self,
        market_data: Dict[str, Any],
        rag_rules: List[str]
    ) -> TradeDecisionSchema:
        """Submit market context and RAG rules to Gemini 2.0 Flash for structured evaluation.
        
        Args:
            market_data: Calculated trade setup parameters (Entry, SL, TP, RSI, Structure).
            rag_rules: List of relevant master rule snippets retrieved from ChromaDB.
            
        Returns:
            TradeDecisionSchema instance containing PASS/REJECT, confidence score, and rationale.
        """
        if self.client is None:
            # Attempt lazy reconnection if API key was updated
            if settings.GEMINI_API_KEY and not self.api_key:
                self.api_key = settings.GEMINI_API_KEY
            self._init_client()

        if self.client is None:
            logger.error("AI Client is unavailable. Returning safety fallback REJECT.")
            return TradeDecisionSchema(
                decision="REJECT",
                confidence_score=0,
                key_reasons=["Không thể kết nối đến Gemini AI API (Thiếu hoặc sai GEMINI_API_KEY)."],
                risk_warnings="Hệ thống AI không phản hồi, dừng toàn bộ kế hoạch vào lệnh để bảo vệ vốn."
            )

        try:
            # Construct context prompt
            rules_formatted = "\n".join([f"- {r}" for r in rag_rules]) if rag_rules else "Không có quy tắc đặc biệt."
            user_prompt = f"""### BỐI CẢNH THỊ TRƯỜNG HIỆN TẠI (XAUUSD):
- Tín hiệu đề xuất: {market_data.get('signal_type')}
- Giá thị trường hiện tại: {market_data.get('current_price')}
- Giá Entry dự kiến: {market_data.get('entry_price')}
- Stop Loss: {market_data.get('sl_price')}
- Take Profit: {market_data.get('tp_price')}
- Tỷ lệ Risk : Reward: 1:{market_data.get('rr_ratio')}
- Khoảng cách rủi ro: {market_data.get('risk_pips')} pips (ATR M15: {market_data.get('atr')})
- Cấu trúc kích hoạt: {market_data.get('structure')}
- Xu hướng H4: {market_data.get('h4_trend')} | Xu hướng H1: {market_data.get('h1_trend')}
- Chỉ số RSI M15: {market_data.get('rsi_m15')} | RSI H1: {market_data.get('rsi_h1')}

### CÁC QUY TẮC MASTER TRÍCH XUẤT TỪ RAG DATABASE:
{rules_formatted}

Hãy phản biện setup trên cực kỳ nghiêm ngặt và trả về JSON theo đúng định dạng TradeDecisionSchema."""

            # Call Gemini 2.0 Flash with Pydantic Structured Output
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT_TEMPLATE,
                    response_mime_type="application/json",
                    response_schema=TradeDecisionSchema,
                    temperature=0.1,
                )
            )

            if hasattr(response, "parsed") and response.parsed is not None:
                decision_obj: TradeDecisionSchema = response.parsed
                logger.info(
                    f"Gemini Decision: {decision_obj.decision} | Score: {decision_obj.confidence_score}/100 | "
                    f"Reasons: {decision_obj.key_reasons}"
                )
                return decision_obj

            # If response.parsed is raw text or dict
            raw_text = response.text or "{}"
            parsed_json = json.loads(raw_text)
            return TradeDecisionSchema(**parsed_json)

        except Exception as e:
            logger.error(f"Error in analyze_market_setup: {str(e)}")
            return TradeDecisionSchema(
                decision="REJECT",
                confidence_score=0,
                key_reasons=[f"Lỗi xử lý phản biện AI: {str(e)}"],
                risk_warnings="Không thể hoàn tất phản biện AI, tự động từ chối lệnh."
            )


ai_agent = AIAgent()
