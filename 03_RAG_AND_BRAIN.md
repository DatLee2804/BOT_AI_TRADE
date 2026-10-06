# TECHNICAL SPECIFICATION: RAG & BRAIN ENGINE (`rag/` & `brain/`)

Module này chịu trách nhiệm so sánh tri thức và thực hiện suy luận bối cảnh thông qua Gemini API.

## 1. `rag/vector_store.py`
- Sử dụng `chromadb.PersistentClient(path="./chroma_db")`.
- Sử dụng mô hình `sentence-transformers/all-MiniLM-L6-v2` để embed dữ liệu hoàn toàn Local.
- Hàm `init_vector_store()`: Tự động đọc tất cả file `.md` trong `rag/knowledge_base/`, chia nhỏ đoạn văn (chunking) và lưu vào ChromaDB collection `"master_knowledge"`.
- Hàm `query_relevant_rules(market_context_text, top_k=3)`: Trích xuất các quy tắc giao dịch liên quan nhất với bối cảnh giá hiện tại.

## 2. `brain/prompts.py`
- Sử dụng `pydantic` định nghĩa cấu trúc JSON bắt buộc đầu ra:
```python
from pydantic import BaseModel, Field

class TradeDecisionSchema(BaseModel):
    decision: str = Field(description="Bắt buộc là 'PASS' nếu duyệt lệnh, hoặc 'REJECT' nếu từ chối")
    confidence_score: int = Field(description="Chấm điểm độ tin cậy từ 0 đến 100")
    key_reasons: list[str] = Field(description="Danh sách 2-3 lý do cốt lõi ủng hộ hoặc từ chối")
    risk_warnings: str = Field(description="Cảnh báo các rủi ro bối cảnh ngắn hạn (như sát cản, volume yếu)")

## 3. `brain/ai_agent.py`
Khởi tạo Client bằng SDK google-genai với model gemini-2.0-flash.

Ghép System Prompt:

Đóng vai: "Bạn là Master Quant Trader cực kỳ khắt khe về quản trị rủi ro."

Nhập vào: Bối cảnh kỹ thuật hiện tại (Data từ Step 1) + Quy tắc RAG trích xuất từ ChromaDB.

Bắt buộc trả về đúng định dạng JSON Schema TradeDecisionSchema.

Hàm analyze_market_setup(market_data, rag_rules) -> Trả về instance của TradeDecisionSchema.