import re
import unicodedata


QUERY_REWRITE_RULES = [
    (r"\bbn\b", "bao nhiêu"),
    (r"\bbao nhieu\b", "bao nhiêu"),
    (r"\bgia\b", "giá"),
    (r"\bbh\b", "bảo hành"),
    (r"\bbao hanh\b", "bảo hành"),
    (r"\bdoi tra\b", "đổi trả"),
    (r"\bship\b", "giao hàng"),
    (r"\bvan chuyen\b", "vận chuyển"),
    (r"\bthanh toan\b", "thanh toán"),
    (r"\bck\b", "chuyển khoản"),
    (r"\bcod\b", "COD"),
    (r"\bdt\b", "điện thoại"),
    (r"\bdien thoai\b", "điện thoại"),
    (r"\blap\b", "laptop"),
    (r"\blt\b", "laptop"),
    (r"\bmay tinh bang\b", "máy tính bảng"),
    (r"\btai nghe\b", "tai nghe"),
    (r"\bchoi game\b", "chơi game"),
    (r"\bdo hoa\b", "đồ họa"),
    (r"\bmay nao\b", "máy nào"),
    (r"\bc ban\b", "có bán"),
    (r"\bc\b(?=\s+ban\b)", "có"),
    (r"\bco ban\b", "có bán"),
    (r"\bmay giat\b", "máy giặt"),
    (r"\btu lanh\b", "tủ lạnh"),
    (r"\bdieu hoa\b", "điều hòa"),
    (r"\bko\b|\bk\b|\bkh\b|\bkhong\b", "không"),
]


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


class QueryRewriter:
    def __init__(self, rules: list[tuple[str, str]] | None = None):
        self.rules = rules or QUERY_REWRITE_RULES

    def expand_for_retrieval(self, question: str) -> str:
        folded = strip_accents(question.lower())
        folded = re.sub(r"[^\w\s-]", " ", folded)
        folded = re.sub(r"\s+", " ", folded).strip()

        rewritten = folded
        for pattern, replacement in self.rules:
            rewritten = re.sub(pattern, replacement, rewritten, flags=re.IGNORECASE)

        if rewritten and rewritten != question:
            return f"{question}\n{rewritten}"
        return question
