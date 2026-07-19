from functools import lru_cache
import json
import re
from pathlib import Path

from app.rag.prompt import FALLBACK_ANSWER
from app.rag.query_rewriter import strip_accents
from app.rag.vector_store import SearchResult


OUT_OF_SCOPE_KEYWORDS = [
    "máy giặt",
    "may giat",
    "tủ lạnh",
    "tu lanh",
    "điều hòa",
    "dieu hoa",
    "xe máy",
    "xe may",
    "bàn ghế",
    "ban ghe",
    "máy ảnh",
    "may anh",
    "unlock",
]

CATEGORY_KEYWORDS = {
    "laptop": ["laptop", "may tinh xach tay"],
    "điện thoại": ["dien thoai", "dt", "phone"],
    "máy tính bảng": ["may tinh bang", "tablet"],
    "tai nghe": ["tai nghe", "earbud", "headphone"],
    "đồng hồ thông minh": ["dong ho", "smartwatch", "fitwatch"],
    "sạc dự phòng": ["sac du phong", "pin du phong", "powerbank"],
    "bàn phím": ["ban phim", "keyboard"],
    "chuột": ["chuot", "mouse"],
    "màn hình": ["man hinh", "monitor"],
    "phụ kiện": ["phu kien", "hub", "cap", "adapter", "webcam", "micro"],
}

GREETING_PATTERNS = [
    "xin chao",
    "chao",
    "hello",
    "hi",
    "helo",
    "alo",
    "chao ban",
    "choa ban",
    "hey",
]


def parse_price(price_text: str) -> int:
    digits = re.sub(r"\D", "", price_text)
    return int(digits) if digits else 0


def repair_mojibake(text: str) -> str:
    try:
        return text.encode("latin1").decode("utf-8")
    except UnicodeError:
        return text


def canonical_text(text: str) -> str:
    return strip_accents(repair_mojibake(text).lower())


class ProductCatalog:
    def __init__(self, rag_documents_path: Path, products_path: Path):
        self.rag_documents_path = rag_documents_path
        self.products_path = products_path

    @lru_cache(maxsize=1)
    def load_products(self) -> tuple[dict, ...]:
        products: list[dict] = []
        if self.rag_documents_path.exists():
            docs = json.loads(self.rag_documents_path.read_text(encoding="utf-8"))
            for doc in docs:
                if doc.get("type") != "product":
                    continue
                products.append(self._product_from_rag_document(doc))

        if self.products_path.exists():
            products.extend(
                json.loads(self.products_path.read_text(encoding="utf-8"))
            )
        return tuple(products)

    def _product_from_rag_document(self, doc: dict) -> dict:
        content = doc.get("content", "")
        price_match = re.search(r"(\d{1,3}(?:\.\d{3})+ VND)", content)
        metadata = doc.get("metadata", {})
        return {
            "sku": doc.get("id", ""),
            "name": doc.get("title", ""),
            "category": metadata.get("category", ""),
            "price": price_match.group(1) if price_match else "",
            "use_case": content,
        }


class GuardrailPolicy:
    def __init__(self, product_catalog: ProductCatalog, min_retrieval_score: float):
        self.product_catalog = product_catalog
        self.min_retrieval_score = min_retrieval_score

    def find_category(self, question: str) -> str | None:
        folded = strip_accents(question.lower())
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in folded for keyword in keywords):
                return category
        return None

    def deterministic_answer(self, question: str) -> str | None:
        folded = strip_accents(question.lower())

        if self.is_greeting(question):
            return (
                "Chào bạn, mình là chatbot hỗ trợ khách hàng của TechCare Electronics. "
                "Bạn cần hỏi về sản phẩm, giá bán, bảo hành, giao hàng hay kiểm tra đơn hàng ạ?"
            )

        if self.is_too_vague_for_rag(question):
            return (
                "Mình chưa hiểu rõ bạn cần hỗ trợ nội dung gì. "
                "Bạn có thể hỏi cụ thể hơn, ví dụ: 'laptop nào chơi game ngon', 'tai nghe nào có chống ồn', hoặc 'đơn TCDH1007 đang ở đâu'."
            )

        if self.is_unknown_product_availability_question(question):
            return (
                "Mình chưa có đủ thông tin để xác nhận sản phẩm này có trong dữ liệu TechCare hiện tại. "
                "Bạn có thể cho mình tên sản phẩm chính xác hơn, hoặc mình sẽ tạo ticket để nhân viên kiểm tra giúp bạn."
            )

        if self.is_support_issue(question):
            return (
                "Mình sẽ tạo ticket để nhân viên kỹ thuật kiểm tra trường hợp này. "
                "Bạn vui lòng cung cấp mã đơn hàng, số điện thoại mua hàng, tên sản phẩm, mô tả lỗi cụ thể "
                "và hình ảnh/video minh chứng nếu có. Nhân viên TechCare sẽ phản hồi trong tối đa 24 giờ làm việc."
            )

        known_product = self.mentioned_known_product(question)
        if self.has_availability_phrase(question) and known_product is not None:
            return (
                f"Có. TechCare có bán {known_product['name']} ({known_product['sku']}), "
                f"giá niêm yết {known_product['price']}, thuộc nhóm {known_product['category']}. "
                f"Sản phẩm này phù hợp với nhu cầu {known_product.get('use_case', 'sử dụng hằng ngày')}."
            )

        if self.is_category_availability_question(question) or self.is_category_followup(question):
            category = self.find_category(question)
            products = self.products_by_category(category)
            if not products:
                return None
            names = ", ".join(f"{item['name']} ({item['price']})" for item in products[:5])
            return (
                f"Có. TechCare có bán nhóm {category}. Một số mẫu hiện có: {names}. "
                "Bạn muốn mình tư vấn mẫu giá tốt, mẫu cao cấp hay mẫu phù hợp nhu cầu cụ thể?"
            )

        if self.is_price_extreme_question(question):
            products = list(self.product_catalog.load_products())
            if "re nhat" in folded or "gia re nhat" in folded:
                product = min(products, key=lambda item: parse_price(item["price"]))
                return (
                    f"Sản phẩm có giá thấp nhất trong dữ liệu hiện tại là {product['name']} "
                    f"({product['sku']}), giá {product['price']}, thuộc nhóm {product['category']}."
                )
            product = max(products, key=lambda item: parse_price(item["price"]))
            return (
                f"Sản phẩm có giá cao nhất trong dữ liệu hiện tại là {product['name']} "
                f"({product['sku']}), giá {product['price']}, thuộc nhóm {product['category']}. "
                f"Sản phẩm này phù hợp với nhu cầu {product.get('use_case', 'cao cấp')}."
            )

        return None

    def mentioned_known_product(self, question: str) -> dict | None:
        folded = strip_accents(question.lower())
        compact = re.sub(r"[^a-z0-9]+", "", folded)
        for product in self.product_catalog.load_products():
            name_folded = strip_accents(product["name"].lower())
            name_compact = re.sub(r"[^a-z0-9]+", "", name_folded)
            sku_compact = re.sub(r"[^a-z0-9]+", "", product["sku"].lower())
            if name_compact and name_compact in compact:
                return product
            if sku_compact and sku_compact in compact:
                return product
        return None

    def products_by_category(self, category: str | None) -> list[dict]:
        category_key = canonical_text(category or "")
        return [
            product
            for product in self.product_catalog.load_products()
            if canonical_text(product["category"]) == category_key
        ]

    def has_availability_phrase(self, question: str) -> bool:
        folded = strip_accents(question.lower())
        return any(
            phrase in folded
            for phrase in [
                "co ban",
                "c ban",
                "shop ban",
                "ban khong",
                "ban ko",
                "ban k",
                "co hang",
                "co san pham",
                "con hang",
            ]
        )

    def is_unknown_product_availability_question(self, question: str) -> bool:
        if self.mentioned_known_product(question) is not None:
            return False
        folded = strip_accents(question.lower())
        product_like_words = ["iphone", "ip", "samsung", "oppo", "xiaomi", "airpod", "ipad", "macbook", "sony", "lg"]
        if any(word in folded for word in product_like_words):
            return True
        if self.find_category(question) is not None:
            return False
        asks_availability = self.has_availability_phrase(question) or any(word in folded for word in product_like_words)
        has_model_number = bool(re.search(r"\b\d{2}\b|\b\d{2,3}[a-z]?\b", folded))
        return asks_availability and (has_model_number or any(word in folded for word in product_like_words))

    def is_greeting(self, question: str) -> bool:
        folded = strip_accents(question.lower())
        folded = re.sub(r"[^\w\s]", " ", folded)
        folded = re.sub(r"\s+", " ", folded).strip()
        return folded in GREETING_PATTERNS

    def is_too_vague_for_rag(self, question: str) -> bool:
        folded = strip_accents(question.lower())
        folded = re.sub(r"[^\w\s-]", " ", folded)
        tokens = [token for token in folded.split() if token]
        useful_terms = {"gia", "bao", "nhieu", "mua", "co", "laptop", "dien", "thoai", "tablet", "tai", "nghe", "chuot", "phim", "sac", "pin", "don", "bh", "hanh", "ship", "game"}
        return not self.is_greeting(question) and len(tokens) <= 2 and not any(token in useful_terms for token in tokens)

    def is_category_availability_question(self, question: str) -> bool:
        return self.has_availability_phrase(question) and self.find_category(question) is not None

    def is_category_followup(self, question: str) -> bool:
        folded = strip_accents(question.lower())
        tokens = [token for token in re.sub(r"[^\w\s]", " ", folded).split() if token]
        return len(tokens) <= 4 and self.find_category(question) is not None

    def is_price_extreme_question(self, question: str) -> bool:
        folded = strip_accents(question.lower())
        asks_product = any(phrase in folded for phrase in ["san pham", "mon nao", "mat hang", "hang nao"])
        asks_extreme = any(phrase in folded for phrase in ["gia cao nhat", "dat nhat", "mac nhat", "gia re nhat", "re nhat"])
        return asks_product and asks_extreme

    def is_support_issue(self, question: str) -> bool:
        folded = strip_accents(question.lower())
        patterns = [r"\bloi\b", r"\bbi loi\b", r"\bhong\b", r"\bbi hong\b", r"khong len", r"man hinh xanh", r"sac khong vao", r"nong bat thuong", r"vo nuoc", r"roi vo", r"hoan tien", r"khieu nai", r"giao sai"]
        return any(re.search(pattern, folded) for pattern in patterns)

    def should_fallback(self, question: str, hits: list[SearchResult]) -> bool:
        if self.is_clearly_out_of_scope(question) or self.is_short_noisy_question(question):
            return True
        if not hits:
            return True
        return hits[0].score < self.min_retrieval_score

    def is_clearly_out_of_scope(self, question: str) -> bool:
        question_lower = question.lower()
        folded = strip_accents(question_lower)
        return any(keyword in question_lower or keyword in folded for keyword in OUT_OF_SCOPE_KEYWORDS)

    def is_short_noisy_question(self, question: str) -> bool:
        folded = strip_accents(question.lower())
        folded = re.sub(r"[^\w\s-]", " ", folded)
        tokens = [token for token in folded.split() if token]
        known_words = {"gia", "bh", "ship", "cod", "laptop", "dt", "phone", "tai", "nghe", "chuot", "ban", "phim"}
        return len(tokens) <= 2 and not any(char.isdigit() for char in folded) and not any(token in known_words for token in tokens)

    def needs_human(self, answer: str, mode: str) -> bool:
        folded = strip_accents(answer.lower())
        return mode == "fallback" or "ticket" in folded or answer == FALLBACK_ANSWER
