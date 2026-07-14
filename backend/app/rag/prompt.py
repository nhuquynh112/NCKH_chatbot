from pathlib import Path


FALLBACK_ANSWER = (
    "Mình chưa có đủ thông tin để xác nhận nội dung này trong dữ liệu hiện tại. "
    "Mình có thể tạo ticket để nhân viên TechCare kiểm tra và tư vấn chính xác hơn cho bạn."
)


class PromptBuilder:
    def __init__(self, prompt_path: Path):
        self.prompt_path = prompt_path

    def system_prompt(self) -> str:
        return self.prompt_path.read_text(encoding="utf-8")

    def user_prompt(self, question: str, context: str) -> str:
        return f"""NGỮ CẢNH:
{context}

CÂU HỎI KHÁCH HÀNG:
{question}

Hãy trả lời theo đúng nguyên tắc. Nếu khách chỉ hỏi tư vấn hoặc hỏi giá sản phẩm, không tự thêm phần bảo hành/ticket trừ khi khách hỏi về lỗi, bảo hành, đổi trả hoặc hỗ trợ kỹ thuật."""
