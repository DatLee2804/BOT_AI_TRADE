# CODE STANDARDS & DEVELOPMENT GUIDELINES

Antigravity AI Agent phải tuân thủ nghiêm ngặt các quy tắc lập trình sau khi sinh code:

1. **Type Hinting:** Tất cả các hàm Python bắt buộc phải có Type Annotations rõ ràng.
   - Ví dụ: `def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:`
2. **Error Handling & Logging:**
   - Tất cả các thao tác gọi API ngoài (MT5, Gemini API, Telegram API, SQLite) bắt buộc phải bọc trong khối `try...except`.
   - Log lỗi chi tiết ra console dạng `logging.error(f"Error in {func_name}: {str(e)}")`. Không để ứng dụng bị crash đột ngột.
3. **Environment Variables:**
   - Không được hard-code bất kỳ Token, Password hay API Key nào trong source code.
   - Luôn dùng `python-dotenv` để load từ file `.env`.
4. **Clean Code & Modular:**
   - Mỗi file đảm nhận duy nhất một trách nhiệm (Single Responsibility Principle).
   - Không viết các file quá 300 dòng code. Chia nhỏ thành các hàm bổ trợ nếu cần.