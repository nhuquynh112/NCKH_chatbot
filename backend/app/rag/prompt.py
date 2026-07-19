from pathlib import Path
import unicodedata


FALLBACK_ANSWER = (
    "Mình chưa có đủ thông tin để xác nhận nội dung này trong dữ liệu hiện tại. "
    "Mình có thể tạo ticket để nhân viên TechCare kiểm tra và tư vấn chính xác hơn cho bạn."
)


class PromptBuilder:
    def __init__(self, prompt_path: Path):
        self.prompt_path = prompt_path

    def system_prompt(self) -> str:
        return (
            self.prompt_path.read_text(encoding="utf-8")
            + "\n\n"
            + self._conversation_memory_rules()
        )

    def _conversation_memory_rules(self) -> str:
        return """QUY TẮC BẮT BUỘC VỀ BỘ NHỚ HỘI THOẠI:
- Conversation History xác định sản phẩm đang được khách hỏi tiếp.
- Nếu prompt có mục ACTIVE PRODUCT FROM CONVERSATION HISTORY, sản phẩm đó là sản phẩm DUY NHẤT cho mọi câu hỏi tiếp theo.
- Follow-up questions gồm: giá bao nhiêu, bảo hành, máy này, mẫu này, còn màu nào, cấu hình, pin, màn hình, chơi game, lập trình, đồ họa, văn phòng, còn hàng, đánh giá, so sánh mẫu này, how much, warranty, this one, can it play games.
- Khi ACTIVE PRODUCT đã tồn tại, bạn MUST answer strictly according to that active product.
- Bạn MUST NOT switch to another product.
- Bạn MUST NOT invent another laptop, phone, accessory, SKU, price, warranty, color, or specification.
- Bạn MUST NOT recommend another product while answering follow-up questions.
- Bạn MUST NOT mention another product name while answering follow-up questions.
- Bạn MUST NOT compare with another product unless the user explicitly asks for comparison.
- Nếu active product không phải lựa chọn tốt nhất cho nhu cầu, chỉ nói giới hạn của active product. Không tự đề xuất sản phẩm thay thế.
- Nếu RAG Context chứa nhiều sản phẩm, sản phẩm trong ACTIVE PRODUCT FROM CONVERSATION HISTORY luôn có ưu tiên cao nhất.
- Retriever products are supplementary knowledge only. Ignore unrelated retrieved products unless the user explicitly asks for another model or comparison.
- Nếu khách hỏi 'Còn mẫu khác không?' hoặc yêu cầu mẫu khác rõ ràng, bạn có thể đề xuất một sản phẩm khác. Sau khi đề xuất, sản phẩm mới đó sẽ trở thành active product trong lượt sau qua Conversation History."""

    def recent_history(
        self,
        history: list[dict] | None,
        current_question: str | None = None,
    ) -> list[dict[str, str]]:
        if not history:
            return []

        messages: list[dict[str, str]] = []
        for item in history[-6:]:
            role = str(item.get("role", "")).lower().strip()
            content = str(item.get("content", "")).strip()
            if role not in {"user", "assistant"} or not content:
                continue
            messages.append({"role": role, "content": content})

        if (
            current_question
            and messages
            and messages[-1]["role"] == "user"
            and messages[-1]["content"].strip() == current_question.strip()
        ):
            messages = messages[:-1]

        return messages[-6:]

    def conversation_history(self, history: list[dict] | None) -> str:
        messages = self.recent_history(history)
        if not messages:
            return ""

        lines: list[str] = []
        for message in messages:
            role = "User" if message["role"] == "user" else "Assistant"
            lines.append(f"{role}:\n{message['content']}")
        return "\n\n".join(lines)

    def is_context_dependent(self, question: str) -> bool:
        folded = self._strip_accents(question.lower())
        phrases = [
            "do bao nhieu",
            "may do",
            "may nay",
            "mau do",
            "mau nay",
            "mau khac",
            "con mau khac",
            "cai do",
            "san pham do",
            "bao nhieu tien",
            "gia bao nhieu",
            "bao hanh",
            "bao hanh bao lau",
            "cau hinh",
            "pin",
            "man hinh",
            "choi game",
            "lap trinh",
            "do hoa",
            "van phong",
            "con hang",
            "danh gia",
            "so voi",
            "mau truoc",
            "loai nao hon",
            "how much",
            "price",
            "warranty",
            "how long is the warranty",
            "this one",
            "that one",
            "what about this one",
            "can this one",
            "can it",
            "play games",
            "any other model",
            "another model",
            "other model",
        ]
        return any(phrase in folded for phrase in phrases)

    def _strip_accents(self, text: str) -> str:
        text = text.replace("đ", "d").replace("Đ", "D")
        normalized = unicodedata.normalize("NFD", text)
        return "".join(
            char for char in normalized if unicodedata.category(char) != "Mn"
        )

    def question_for_retrieval(self, question: str, history: list[dict] | None) -> str:
        formatted_history = self.conversation_history(history)
        if not formatted_history:
            return question
        return (
            "Conversation History\n"
            f"{formatted_history}\n\n"
            "Current User Question\n"
            f"{question}"
        )

    def user_prompt(
        self,
        question: str,
        context: str,
        history: list[dict] | None = None,
        active_product: dict | None = None,
    ) -> str:
        formatted_history = self.conversation_history(history)
        active_product_text = self.active_product_context(active_product)
        if not formatted_history:
            return f"""NGỮ CẢNH:
{context}

CÂU HỎI KHÁCH HÀNG:
{question}

Hãy trả lời theo đúng nguyên tắc. Nếu khách chỉ hỏi tư vấn hoặc hỏi giá sản phẩm, không tự thêm phần bảo hành/ticket trừ khi khách hỏi về lỗi, bảo hành, đổi trả hoặc hỗ trợ kỹ thuật."""

        if not active_product_text:
            return f"""Conversation History
{formatted_history}

Current User Question
{question}

NGỮ CẢNH:
{context}

Hãy trả lời theo đúng nguyên tắc. Nếu khách chỉ hỏi tư vấn hoặc hỏi giá sản phẩm, không tự thêm phần bảo hành/ticket trừ khi khách hỏi về lỗi, bảo hành, đổi trả hoặc hỗ trợ kỹ thuật."""

        return f"""Conversation History
{formatted_history}

ACTIVE PRODUCT FROM CONVERSATION HISTORY
{active_product_text}

Current User Question
{question}

RAG Context
{context}

MANDATORY ANSWER RULES
- You MUST answer only about the ACTIVE PRODUCT above.
- You MUST NOT replace the active product with another product from RAG Context.
- You MUST ignore unrelated retrieved products unless the user explicitly asks for comparison or another model.
- You MUST NOT mention another product name while answering follow-up questions.
- You MUST NOT invent another product, price, warranty, color, or specification.
- If the active product is not ideal for the user's need, explain the limitation of the active product only. Do not suggest an alternative product unless the user explicitly asks for another model.
- If the answer is unavailable for the active product, say that the current data does not contain that detail for the active product and offer to create a ticket.
- Do not recommend another product for follow-up questions such as price, warranty, battery, screen, configuration, office work, programming, graphics, or gaming.

Hãy trả lời theo đúng nguyên tắc. Nếu khách chỉ hỏi tư vấn hoặc hỏi giá sản phẩm, không tự thêm phần bảo hành/ticket trừ khi khách hỏi về lỗi, bảo hành, đổi trả hoặc hỗ trợ kỹ thuật."""

    def active_product_context(self, product: dict | None) -> str:
        if not product:
            return ""

        lines = [
            f"Name: {product.get('name', '')}",
            f"SKU: {product.get('sku', '')}",
            f"Category: {product.get('category', '')}",
            f"Price: {product.get('price', '')}",
            f"Warranty: {product.get('warranty', '')}",
            f"Known details: {product.get('use_case', '')}",
        ]
        return "\n".join(line for line in lines if not line.endswith(": "))
