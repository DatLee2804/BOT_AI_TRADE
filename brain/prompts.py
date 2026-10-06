"""Prompt Templates and Pydantic Output Schemas for Gemini 2.0 Flash."""
from typing import List
from pydantic import BaseModel, Field


class TradeDecisionSchema(BaseModel):
    """Pydantic structured output model for AI Master Quant Trader trade decision."""
    decision: str = Field(
        description="Bắt buộc là 'PASS' nếu duyệt lệnh, hoặc 'REJECT' nếu từ chối"
    )
    confidence_score: int = Field(
        ge=0,
        le=100,
        description="Chấm điểm độ tin cậy từ 0 đến 100"
    )
    key_reasons: List[str] = Field(
        description="Danh sách 2-3 lý do cốt lõi ủng hộ hoặc từ chối"
    )
    risk_warnings: str = Field(
        description="Cảnh báo các rủi ro bối cảnh ngắn hạn (như sát cản, volume yếu)"
    )


SYSTEM_PROMPT_TEMPLATE = """Bạn là Master Quant Trader cực kỳ khắt khe về quản trị rủi ro trên thị trường Vàng (XAUUSD).
Nhiệm vụ của bạn là phản biện setup kỹ thuật được cung cấp, so sánh đối chiếu với các Quy tắc Master trích xuất từ RAG.

Yêu cầu đánh giá:
1. Phải có sự đồng thuận xu hướng giữa khung thời gian lớn (H4/H1) và cấu trúc vào lệnh (M15).
2. Tỷ lệ R:R thực tế phải đạt tối thiểu 1:2.5.
3. Không chấp nhận vào lệnh nếu có dấu hiệu bẫy thanh khoản, đuổi đỉnh/đáy, hoặc RSI phân kỳ bất lợi.
4. Chỉ cấp quyết định 'PASS' khi confidence_score >= 75 và thỏa mãn tất cả quy tắc Master.
5. Nếu có bất kỳ nghi ngờ nào về rủi ro bối cảnh, hãy kiên quyết từ chối ('REJECT').

BẮT BUỘC TRẢ VỀ KẾT QUẢ ĐÚNG THEO JSON SCHEMA ĐÃ ĐỊNH NGHĨA.
"""
