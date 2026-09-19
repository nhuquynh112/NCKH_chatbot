import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote_plus

from app.product_enrichment import merge_verified_product
from app.rag.prompt import FALLBACK_ANSWER
from app.rag.query_rewriter import strip_accents
from app.rag.vector_store import SearchResult


logger = logging.getLogger(__name__)


COMMON_CHAT_TYPOS = [
    (r"\biphon\b|\biphnoe\b", "iphone"),
    (r"\bsamsumg\b|\bsam sung\b", "samsung"),
    (r"\bxiaomii\b|\bxiaom\b", "xiaomi"),
    (r"\bairpodss\b", "airpods"),
    (r"\bmacbok\b|\bmackbook\b", "macbook"),
    (r"\blap\s*top\b|\blaptpo\b", "laptop"),
    (r"\btai\s+nge\b", "tai nghe"),
    (r"\bgmaing\b", "gaming"),
    (r"\bbnhiêu\b|\bbnhieu\b", "bao nhieu"),
]


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

UNRELATED_REQUEST_PATTERNS = [
    r"\bthoi tiet\b",
    r"\bdu bao thoi tiet\b",
    r"\btroi (?:co )?(?:mua|nang|lanh|nong)\b",
    r"\bviet (?:cho (?:toi|minh) )?(?:mot )?(?:bai )?tho\b",
    r"\btruyen cuoi\b",
    r"\bnau (?:an|pho|bun|com)\b",
    r"\bcach (?:nau|lam) (?:pho|bun|com|banh)\b",
    r"\bbong da\b",
    r"\bty so\b",
    r"\bti so\b",
    r"\btong thong\b",
    r"\bchinh tri\b",
    r"\bchung khoan\b",
    r"\bco phieu\b",
    r"\bgia vang\b",
    r"\bty gia\b",
    r"\bgiai (?:bai )?(?:toan|tich phan|dao ham)\b",
    r"\btich phan\b",
    r"\bviet code game\b",
    r"\b(?:viet|code) (?:code )?(?:python|java|javascript|c\+\+|csharp)\b",
    r"\bdich .*(?:tieng anh|tieng viet|sang anh|sang viet)\b",
    r"\bviet (?:email|thu) (?:xin viec|ung tuyen)\b",
    r"\b(?:lam|viet) (?:mot )?bai van\b",
    r"\bcong thuc nau\b",
    r"\bnau (?:ga|thit|ca|rau)\b",
    r"\bran san moi\b",
    r"\btu vi\b",
    r"\bxem boi\b",
]

CATEGORY_KEYWORDS = {
    "laptop": ["laptop", "may tinh xach tay", "macbook"],
    "điện thoại": ["dien thoai", "dt", "phone", "iphone", "galaxy s", "pixel"],
    "máy tính bảng": ["may tinh bang", "tablet", "ipad", "galaxy tab"],
    "tai nghe": ["tai nghe", "earbud", "headphone", "airpod", "galaxy buds"],
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
    folded = strip_accents(repair_mojibake(text).lower())
    for pattern, replacement in COMMON_CHAT_TYPOS:
        folded = re.sub(pattern, replacement, folded, flags=re.IGNORECASE)
    return folded


class ProductCatalog:
    def __init__(self, rag_documents_path: Path, products_path: Path):
        self.rag_documents_path = rag_documents_path
        self.products_path = products_path

    def load_products(self) -> tuple[dict, ...]:
        # The live Product table is the source of truth. It is intentionally
        # queried on each request so admin price/active-status changes are
        # visible to the chatbot immediately without rebuilding the RAG index.
        products = self._load_database_products()

        # Exported files keep the evaluator and first startup usable before the
        # database exists, but are never preferred over live store data.
        if not products and self.products_path.exists():
            raw_products = json.loads(self.products_path.read_text(encoding="utf-8"))
            products.extend(self._normalize_product(item) for item in raw_products)
        elif not products and self.rag_documents_path.exists():
            docs = json.loads(self.rag_documents_path.read_text(encoding="utf-8"))
            products.extend(
                self._product_from_rag_document(doc)
                for doc in docs
                if doc.get("type") == "product"
            )

        deduplicated: dict[str, dict] = {}
        for product in products:
            key = re.sub(r"[^a-z0-9]+", "", canonical_text(product["name"]))
            if key:
                deduplicated[key] = product
        return tuple(deduplicated.values())

    def _load_database_products(self) -> list[dict]:
        try:
            from app.database import SessionLocal
            from app.models import Product

            with SessionLocal() as db:
                rows = (
                    db.query(Product)
                    .filter(Product.is_active.is_(True))
                    .order_by(Product.id.asc())
                    .all()
                )
                return [
                    self._normalize_product(
                        merge_verified_product({
                            "id": row.id,
                            "slug": row.slug,
                            "name": row.name,
                            "brand": row.brand,
                            "category": row.category,
                            "price": float(row.price),
                            "description": row.description,
                            "warranty_months": row.warranty_months,
                            "specifications": row.specifications,
                            "updated_at": row.updated_at,
                        })
                    )
                    for row in rows
                ]
        except Exception as exc:  # File fallback also supports standalone tools.
            logger.debug("Live product database unavailable; using exported catalog: %s", exc)
            return []

    def _normalize_product(self, product: dict) -> dict:
        product_id = product.get("id")
        sku = product.get("sku") or product.get("slug")
        if not sku and product_id is not None:
            sku = f"SP-{int(product_id):03d}"
        specifications = product.get("specifications") or product.get("specs") or {}
        if isinstance(specifications, dict):
            # Dữ liệu từ website và nguồn đối chiếu có thể dùng hai tên cho
            # cùng một trường (ví dụ `Storage` và `Bộ nhớ`). Gộp chúng để câu
            # trả lời không lặp thông số và ưu tiên nhãn tiếng Việt nhất quán.
            spec_aliases = {
                "storage": ("bo nho", "Bộ nhớ"),
                "bo nho": ("bo nho", "Bộ nhớ"),
                "dung luong": ("bo nho", "Bộ nhớ"),
                "display": ("man hinh", "Màn hình"),
                "screen": ("man hinh", "Màn hình"),
                "man hinh": ("man hinh", "Màn hình"),
                "battery": ("pin", "Pin"),
                "pin": ("pin", "Pin"),
                "processor": ("chip", "Chip"),
                "cpu": ("chip", "Chip"),
                "chip": ("chip", "Chip"),
            }
            normalized_specs: dict[str, tuple[str, object]] = {}
            for key, value in specifications.items():
                folded_key = canonical_text(str(key)).strip()
                semantic_key, display_key = spec_aliases.get(
                    folded_key, (folded_key, str(key))
                )
                # Giá trị được cập nhật sau thường đến từ nguồn xác minh mới
                # hơn; giữ thứ tự ban đầu nhưng lấy giá trị mới nhất.
                normalized_specs[semantic_key] = (display_key, value)
            specs_text = ", ".join(
                f"{display_key}: {value}"
                for display_key, value in normalized_specs.values()
            )
        else:
            specs_text = str(specifications)
        description = str(product.get("description") or product.get("use_case") or "").strip().rstrip(".")
        price_value = product.get("price", 0)
        if isinstance(price_value, (int, float)):
            price = f"{int(price_value):,}".replace(",", ".") + " VND"
        else:
            price = str(price_value)
        warranty_value = product.get("warranty_months")
        warranty = (
            f"{warranty_value} tháng"
            if warranty_value is not None
            else str(product.get("warranty") or "")
        )
        return {
            "id": product_id,
            "slug": str(product.get("slug") or sku or ""),
            "sku": str(sku or product.get("name", "")),
            "name": str(product.get("name", "")),
            "brand": str(product.get("brand") or ""),
            "category": str(product.get("category") or ""),
            "price": price,
            "specs": specs_text,
            "description": description,
            "use_case": " — ".join(part for part in [description, specs_text] if part),
            "warranty": warranty,
            "updated_at": product.get("updated_at"),
            "verified_at": product.get("verified_at"),
            "verification_status": product.get(
                "verification_status", "store_catalog_only"
            ),
            "verification_note": str(product.get("verification_note") or ""),
            "source_urls": product.get("source_urls") or [],
        }

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
        folded = canonical_text(question)
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in folded for keyword in keywords):
                return category
        return None

    def deterministic_answer(self, question: str) -> str | None:
        folded = canonical_text(question)

        if self.is_greeting(question):
            return (
                "Chào bạn, mình là chatbot hỗ trợ khách hàng của TechCare Electronics. "
                "Bạn cần hỏi về sản phẩm, giá bán, bảo hành, giao hàng hay kiểm tra đơn hàng ạ?"
            )

        if self.is_prompt_injection(question):
            return (
                "Mình không thể cung cấp chỉ dẫn nội bộ, prompt hệ thống, khóa truy cập hoặc làm theo "
                "yêu cầu bỏ qua quy tắc an toàn. Mình vẫn có thể hỗ trợ bạn về sản phẩm, giá, "
                "bảo hành, giao hàng và đơn hàng của TechCare."
            )

        if self.is_unrelated_request(question):
            return (
                "Xin lỗi, mình chỉ hỗ trợ các nội dung thuộc TechCare như sản phẩm công nghệ, "
                "giá bán, tư vấn mua hàng, bảo hành, giao hàng, đơn hàng và hỗ trợ kỹ thuật. "
                "Mình chưa thể hỗ trợ câu hỏi này; bạn có thể hỏi mình về điện thoại, laptop, "
                "tai nghe hoặc dịch vụ của TechCare nhé."
            )

        if self.is_too_vague_for_rag(question):
            return (
                "Mình chưa hiểu rõ bạn cần hỗ trợ nội dung gì. "
                "Bạn có thể hỏi cụ thể hơn, ví dụ: 'laptop nào chơi game ngon', 'tai nghe nào có chống ồn', hoặc 'đơn TCDH1007 đang ở đâu'."
            )

        order_code = self.extract_order_code(question)
        if self.is_order_lookup(question):
            code_text = f" mã {order_code}" if order_code else ""
            return (
                f"Mình đã ghi nhận yêu cầu kiểm tra đơn hàng{code_text}. "
                "Bản demo hiện chưa kết nối dữ liệu vận chuyển theo thời gian thực, nên mình không đoán trạng thái đơn. "
                "Mình sẽ tạo ticket để nhân viên kiểm tra; bạn vui lòng cung cấp thêm số điện thoại đặt hàng nếu chưa có trong phiên chat."
            )

        if self.is_support_issue(question):
            return (
                "Mình sẽ tạo ticket để nhân viên kỹ thuật kiểm tra trường hợp này. "
                "Bạn vui lòng cung cấp mã đơn hàng, số điện thoại mua hàng, tên sản phẩm, mô tả lỗi cụ thể "
                "và hình ảnh/video minh chứng nếu có. Nhân viên TechCare sẽ phản hồi trong tối đa 24 giờ làm việc."
            )

        policy_answer = self.policy_faq_answer(folded)
        if policy_answer:
            return policy_answer

        if "cod" in folded and any(
            phrase in folded for phrase in ["la gi", "the nao", "nghia la"]
        ):
            return (
                "COD là hình thức thanh toán khi nhận hàng. Tại TechCare, khách hàng có thể "
                "kiểm tra ngoại quan sản phẩm trước khi thanh toán theo chính sách của đơn vị vận chuyển; "
                "một số khu vực xa có thể không hỗ trợ COD."
            )

        if "hoan tien" in folded:
            if any(
                phrase in folded
                for phrase in ["bao lau", "thoi gian", "may ngay", "khi nao nhan"]
            ):
                return (
                    "Thời gian hoàn tiền tùy phương thức thanh toán: tiền mặt theo thỏa thuận "
                    "tại cửa hàng; chuyển khoản từ 3 đến 7 ngày làm việc; thẻ ngân hàng theo "
                    "thời gian xử lý của ngân hàng phát hành."
                )
            if any(
                phrase in folded
                for phrase in ["khi nao", "truong hop nao", "dieu kien"]
            ):
                return (
                    "TechCare xem xét hoàn tiền khi đơn hàng bị hủy, hết hàng, không thể giao "
                    "hàng hoặc sản phẩm đủ điều kiện đổi trả theo chính sách."
                )

        asks_working_hours = any(
            phrase in folded for phrase in ["gio lam viec", "gio mo cua", "may gio"]
        )
        asks_contact = any(
            phrase in folded for phrase in ["kenh lien he", "lien he", "hotline"]
        )
        if asks_working_hours or asks_contact:
            parts: list[str] = []
            if asks_working_hours:
                parts.append(
                    "TechCare làm việc từ Thứ Hai đến Chủ Nhật, 08:00–21:30; "
                    "giờ hoạt động ngày lễ có thể thay đổi theo thông báo của cửa hàng."
                )
            if asks_contact:
                parts.append(
                    "Các kênh hỗ trợ gồm chat trực tuyến trên website, hotline chăm sóc khách hàng, "
                    "email hỗ trợ, Fanpage Facebook và Zalo Official Account. "
                    "Knowledge Base hiện chưa công bố số hotline hoặc địa chỉ email cụ thể nên mình không tự suy đoán."
                )
            return " ".join(parts)

        mentioned_products = self.mentioned_products(question)
        if len(mentioned_products) >= 2 and self.is_comparison_question(question):
            return self.comparison_answer(mentioned_products[:2])

        known_product = mentioned_products[0] if mentioned_products else None
        if known_product is not None:
            answer = self.product_fact_answer(question, known_product)
            if answer:
                return answer

        if "bao hanh" in folded:
            category = self.find_category(question)
            products = self.products_by_category(category)
            if products:
                durations = sorted(
                    {product["warranty"] for product in products if product.get("warranty")}
                )
                if len(durations) == 1:
                    return (
                        f"Các sản phẩm {category} trong danh mục hiện tại có thời hạn bảo hành {durations[0]}. "
                        "Thời gian xử lý một yêu cầu bảo hành là thông tin khác và thường phụ thuộc hãng."
                    )
                return (
                    f"Thời hạn bảo hành của nhóm {category} tùy mẫu, hiện gồm: {', '.join(durations)}. "
                    "Bạn gửi tên model cụ thể để mình trả lời chính xác."
                )

        if self.has_availability_phrase(question) and self.is_clearly_out_of_scope(question):
            return self.external_product_answer(question)

        if self.is_unknown_product_availability_question(question):
            return self.external_product_answer(question)

        if self.looks_like_unknown_model(question):
            return self.external_product_answer(question)

        if self.is_recommendation_question(question):
            answer = self.recommendation_answer(question)
            if answer:
                return answer

        if self.is_category_availability_question(question) or self.is_category_followup(question):
            category = self.find_category(question)
            products = self.products_by_category(category)
            if not products:
                return None
            names = ", ".join(f"{item['name']} ({item['price']})" for item in products[:5])
            return (
                f"Có. TechCare có bán nhóm {category}. Một số mẫu: {names}."
            )

        if self.is_price_extreme_question(question):
            products = [
                product
                for product in self.product_catalog.load_products()
                if parse_price(product["price"]) > 0
            ]
            if not products:
                return None
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

    @staticmethod
    def policy_faq_answer(folded: str) -> str | None:
        """Answer stable store policies without making the customer wait for the LLM."""
        if "cod" in folded and any(
            phrase in folded for phrase in ["la gi", "the nao", "nghia la"]
        ):
            return (
                "COD là hình thức thanh toán khi nhận hàng. Khách được kiểm tra ngoại quan "
                "theo chính sách của đơn vị vận chuyển; một số khu vực xa có thể không hỗ trợ COD."
            )
        if any(phrase in folded for phrase in ["cach thanh toan", "phuong thuc thanh toan"]):
            return (
                "TechCare hỗ trợ tiền mặt tại cửa hàng, COD, chuyển khoản ngân hàng, mã QR, "
                "thẻ ATM nội địa, Visa, MasterCard và ví điện tử khi chương trình áp dụng."
            )
        if "tra gop" in folded and any(
            phrase in folded for phrase in ["giay to", "ho so", "can gi", "chuan bi"]
        ):
            return (
                "Hồ sơ trả góp có thể cần CCCD/CMND còn hiệu lực, số điện thoại chính chủ "
                "và giấy tờ bổ sung theo yêu cầu của đơn vị tài chính."
            )
        if "tra gop" in folded:
            return (
                "Có. TechCare hỗ trợ trả góp qua công ty tài chính, thẻ tín dụng và chương trình "
                "của ngân hàng. Điều kiện và ưu đãi phụ thuộc sản phẩm, đơn vị duyệt và từng thời điểm."
            )
        if "hoa don" in folded or re.search(r"\bvat\b", folded):
            return (
                "Có. TechCare hỗ trợ xuất hóa đơn VAT; bạn cần cung cấp đầy đủ thông tin "
                "doanh nghiệp hoặc cá nhân khi đặt hàng."
            )
        if "giao hang" in folded and "toan quoc" in folded:
            return (
                "Có. TechCare hỗ trợ giao hàng trên toàn quốc; một số khu vực đặc biệt có thể "
                "phát sinh thêm thời gian vận chuyển."
            )
        if any(phrase in folded for phrase in ["noi thanh", "trong thanh pho"]):
            return (
                "Giao hàng nội thành thường trong ngày hoặc từ 1 đến 2 ngày làm việc, "
                "tùy lượng đơn hàng và địa chỉ nhận."
            )
        # Check shipping fees before "giao hang tinh": once accents are
        # stripped, Vietnamese "tính thế nào" can look like "tỉnh".
        if any(phrase in folded for phrase in ["phi giao hang", "phi ship", "ship bao nhieu"]):
            return (
                "Phí giao hàng được tính theo địa chỉ nhận, trọng lượng/kích thước kiện hàng "
                "và chính sách của đơn vị vận chuyển; mức phí sẽ được báo trước khi xác nhận đơn."
            )
        if "giao hang" in folded and any(
            phrase in folded for phrase in ["giao hang tinh", "giao tinh", "ngoai tinh", "o tinh"]
        ):
            return (
                "Giao hàng tỉnh thường từ 3 đến 7 ngày làm việc, phụ thuộc địa điểm nhận "
                "và đơn vị vận chuyển."
            )
        if "kiem tra" in folded and any(
            phrase in folded for phrase in ["truoc khi nhan", "truoc khi thanh toan", "kiem hang"]
        ):
            return (
                "Bạn được kiểm tra ngoại quan sản phẩm theo chính sách của đơn vị vận chuyển. "
                "Việc dùng thử trước khi thanh toán chỉ thực hiện khi đơn vị vận chuyển cho phép."
            )
        if "bao hanh" in folded and any(
            phrase in folded for phrase in ["quy trinh", "cac buoc", "lam the nao"]
        ):
            return (
                "Quy trình bảo hành: liên hệ TechCare, nhân viên tiếp nhận, kiểm tra điều kiện, "
                "chuyển trung tâm bảo hành và thông báo kết quả cho khách hàng."
            )
        if "bao hanh" in folded and any(
            phrase in folded for phrase in ["khong duoc", "tu choi", "truong hop nao khong"]
        ):
            return (
                "Sản phẩm có thể không được bảo hành nếu bị rơi vỡ, vào nước, can thiệp phần cứng, "
                "thiếu phụ kiện hoặc không đáp ứng điều kiện của hãng."
            )
        if "bao hanh" in folded and any(
            phrase in folded for phrase in ["dieu kien", "duoc bao hanh"]
        ):
            return (
                "Sản phẩm được xem xét bảo hành khi còn thời hạn, lỗi thuộc nhà sản xuất, "
                "không rơi vỡ/vào nước/can thiệp phần cứng và đáp ứng điều kiện của hãng."
            )
        if "doi tra" in folded and any(
            phrase in folded for phrase in ["can giu", "giu nhung gi", "dieu kien"]
        ):
            return (
                "Khi yêu cầu đổi trả, bạn cần giữ sản phẩm, hộp, đầy đủ phụ kiện, quà tặng "
                "và chứng từ mua hàng; sản phẩm phải đáp ứng điều kiện đổi trả."
            )
        if "khuyen mai" in folded:
            return (
                "Các chương trình khuyến mãi của TechCare có thể gồm giảm giá trực tiếp, tặng phụ kiện, voucher, combo "
                "hoặc Flash Sale. Chương trình thực tế phụ thuộc từng thời điểm."
            )
        if "voucher" in folded and "het han" in folded:
            return "Không. Voucher hết hạn không còn hiệu lực và chatbot không thể tự gia hạn voucher."
        if "diem" in folded and any(
            phrase in folded for phrase in ["thanh vien", "tich diem", "diem thuong", "dung the nao"]
        ):
            return (
                "Một số đơn hàng đủ điều kiện sẽ được tích điểm; điểm thưởng được sử dụng "
                "trong các chương trình khuyến mãi theo quy định."
            )
        if "thanh vien" in folded:
            return (
                "Tùy hạng thành viên, quyền lợi có thể gồm voucher sinh nhật, ưu đãi mua hàng "
                "và tích điểm theo chương trình hiện hành."
            )
        return None

    def external_product_answer(self, question: str) -> str:
        search_query = self.external_search_query(question)
        search_url = f"https://www.google.com/search?q={quote_plus(search_query)}"
        shopping_url = f"https://www.google.com/search?tbm=shop&q={quote_plus(search_query)}"
        return (
            "Mình chưa tìm thấy sản phẩm này trong danh mục TechCare nên không thể xác nhận giá hoặc nơi bán. "
            "Bạn có thể tham khảo nguồn bên ngoài:\n"
            f"- Google: {search_url}\n"
            f"- Google Shopping: {shopping_url}\n"
            "Lưu ý: đây là liên kết tham khảo bên ngoài; TechCare không xác minh giá, tồn kho "
            "hay độ uy tín của các bên bán trong kết quả."
        )

    def external_search_query(self, question: str) -> str:
        cleaned = re.sub(
            r"\b(shop|techcare|cửa hàng|cua hang)\b",
            " ",
            question,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\b(?:có|co|c)\s+(?:bán|ban)\b|\b(?:bán|ban)\s+(?:không|khong|ko|k)\b",
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\bip\s*([0-9]+(?:\s*(?:pro|max|plus))?)\b",
            r"iPhone \1",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\b(giá|gia)\s+bao\s+nhiêu\b|\bbao\s+nhiêu\s+tiền\b|"
            r"\b(còn|con)\s+hàng\b|\b(có|co)\s+(?:không|khong|ko|k)\b|"
            r"\b(không|khong|ko|k)\b|\b(có|co)\b",
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"[^\w\s+.-]", " ", cleaned, flags=re.UNICODE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return f"mua {cleaned} tại Việt Nam" if cleaned else "thiết bị công nghệ tại Việt Nam"

    def looks_like_unknown_model(self, question: str) -> bool:
        if self.mentioned_known_product(question) is not None:
            return False
        folded = canonical_text(question)
        asks_product_fact = any(
            term in folded
            for term in [
                "gia bao nhieu", "bao nhieu tien", "bao hanh", "cau hinh",
                "con hang", "co khong", "co ban", "gia",
            ]
        )
        product_lines = [
            "iphone", "samsung", "galaxy", "oppo", "xiaomi", "redmi",
            "airpod", "ipad", "macbook", "pixel", "sony", "nintendo",
            "playstation", "rtx", "thinkpad", "vivobook", "zenbook",
            "legion", "victus", "predator", "alienware",
        ]
        has_model_number = any(character.isdigit() for character in folded)
        return (
            asks_product_fact
            and has_model_number
            and any(line in folded for line in product_lines)
        )

    def product_by_id(self, product_id: int | None) -> dict | None:
        if product_id is None:
            return None
        for product in self.product_catalog.load_products():
            if product.get("id") == product_id:
                return product
        return None

    def mentioned_products(self, question: str) -> list[dict]:
        compact = re.sub(r"[^a-z0-9]+", "", canonical_text(question))
        candidates: list[tuple[int, int, int, dict]] = []
        for product in self.product_catalog.load_products():
            terms = [*self.product_aliases(product), product.get("sku", "")]
            best_match: tuple[int, int, int, dict] | None = None
            for term in terms:
                term_compact = re.sub(r"[^a-z0-9]+", "", canonical_text(term))
                if len(term_compact) < 4:
                    continue
                start = compact.find(term_compact)
                if start < 0:
                    continue
                candidate = (start, start + len(term_compact), len(term_compact), product)
                if best_match is None or candidate[2] > best_match[2]:
                    best_match = candidate
            if best_match:
                candidates.append(best_match)

        # A long model name often contains a shorter model name, e.g.
        # "Samsung Galaxy S25 Ultra" also contains "Samsung Galaxy S25".
        # Keep the most specific mention for each text span, then preserve the
        # order in which the customer named the products.
        selected: list[tuple[int, int, int, dict]] = []
        for candidate in sorted(candidates, key=lambda item: item[2], reverse=True):
            start, end, _, _ = candidate
            overlaps = any(start < chosen_end and end > chosen_start for chosen_start, chosen_end, _, _ in selected)
            if not overlaps:
                selected.append(candidate)
        selected.sort(key=lambda item: item[0])
        return [product for _, _, _, product in selected]

    def product_aliases(self, product: dict) -> list[str]:
        name = product.get("name", "")
        aliases = [name]
        removable_suffixes = [
            r"\s+\d+\s*(?:gb|tb)\b.*$",
            r"\s+\d+(?:\.\d+)?\s*inch\b.*$",
            r"\s+(?:usb[- ]?c|wifi)\b.*$",
        ]
        for pattern in removable_suffixes:
            alias = re.sub(pattern, "", name, flags=re.IGNORECASE).strip()
            if alias and alias != name:
                aliases.append(alias)

        folded_name = canonical_text(name)
        iphone_match = re.search(
            r"\biphone\s+(\d+)(?:\s+(pro|max|plus))?",
            folded_name,
        )
        if iphone_match:
            model = " ".join(part for part in iphone_match.groups() if part)
            aliases.extend([f"ip {model}", f"ip{model.replace(' ', '')}"])

        samsung_match = re.search(
            r"\bgalaxy\s+(s\d+)(?:\s+(ultra|plus))?",
            folded_name,
        )
        if samsung_match:
            model = " ".join(part for part in samsung_match.groups() if part)
            aliases.extend(
                [
                    f"galaxy {model}",
                    f"samsung {model}",
                    f"ss {model}",
                    f"ss{model.replace(' ', '')}",
                ]
            )

        xiaomi_match = re.search(r"\bxiaomi\s+(\d+[a-z]?)\b", folded_name)
        if xiaomi_match:
            model = xiaomi_match.group(1)
            aliases.extend([f"mi {model}", f"xm {model}", f"xm{model}"])

        # Customers often omit the year/CPU/RAM and identify a gaming laptop
        # by family + GPU, e.g. "asus tuf 4050".
        family_patterns = [
            "asus tuf", "asus rog", "lenovo loq", "lenovo legion",
            "hp victus", "hp omen", "acer nitro", "acer predator",
            "msi katana", "msi raider", "dell alienware",
            "gigabyte g5", "gigabyte aorus",
        ]
        gpu_match = re.search(r"\brtx\s*(\d{4})\b", folded_name)
        for family in family_patterns:
            if family not in folded_name:
                continue
            aliases.append(family)
            if gpu_match:
                aliases.append(f"{family} {gpu_match.group(1)}")
        return aliases

    def product_fact_answer(self, question: str, product: dict) -> str | None:
        folded = canonical_text(question)
        name = product["name"]
        freshness = self.product_freshness_note(product)
        asks_availability = self.has_availability_phrase(question)
        asks_specific_spec = any(
            term in folded
            for term in [
                "ram", "chip", "cpu", "ssd", "bo nho", "storage", "dung luong",
                "memory", "processor", "gpu", "graphics", "card do hoa", "man hinh", "screen",
                "display", "hz", "pin", "battery", "thoi luong", "camera",
                "chup anh", "quay video", "mau gi", "mau nao", "mau sac",
            ]
        )
        asks_price = any(
            term in folded for term in ["gia", "bao tien", "price", "how much", "cost"]
        ) or (
            "bao nhieu" in folded and not asks_specific_spec
        )
        asks_warranty = any(
            term in folded for term in ["bao hanh", "warranty"]
        ) or bool(re.search(r"\bbh\b", folded))
        asks_general_specs = any(
            term in folded
            for term in ["thong so", "cau hinh", "spec", "specification", "configuration"]
        )
        asks_gaming = any(
            term in folded
            for term in ["choi game", "gaming", "game ok", "chien game", "play game"]
        )
        requested_specs = [
            ("RAM", ["ram"], ["ram"]),
            ("chip/CPU", ["chip", "cpu", "vi xu ly", "processor"], ["chip", "cpu", "processor"]),
            ("GPU", ["gpu", "graphics", "card do hoa"], ["gpu", "card do hoa"]),
            ("bộ nhớ", ["ssd", "bo nho", "storage", "memory", "dung luong"], ["ssd", "bo nho", "storage"]),
            ("màn hình", ["man hinh", "screen", "display", "hz"], ["man hinh", "display", "screen"]),
            ("pin", ["pin", "battery", "thoi luong"], ["pin", "battery"]),
            ("camera", ["camera", "chup anh", "chup hinh", "quay video", "quay phim"], ["camera"]),
            ("màu sắc", ["mau gi", "mau nao", "mau sac"], ["mau", "color"]),
        ]
        asked_spec_groups = [
            (label, evidence_terms)
            for label, question_terms, evidence_terms in requested_specs
            if any(term in folded for term in question_terms)
        ]
        # "Cấu hình và RAM" is one specification request, not two separate
        # intents. Avoid repeating the complete configuration in that case.
        effective_general_specs = asks_general_specs and not asked_spec_groups
        intent_count = sum(
            [
                asks_availability,
                asks_price,
                asks_warranty,
                effective_general_specs,
                asks_gaming,
            ]
        ) + len(asked_spec_groups)

        if intent_count > 1:
            parts: list[str] = []
            if asks_availability:
                parts.append("đang được TechCare niêm yết")
            if asks_price:
                parts.append(f"giá {product['price']}")
            if asks_warranty:
                parts.append(f"bảo hành {product['warranty']}")
            if effective_general_specs:
                if product.get("specs"):
                    parts.append(f"thông số chính: {product['specs']}")
                else:
                    parts.append("catalog chưa có thông số chi tiết")

            missing_labels: list[str] = []
            for label, evidence_terms in asked_spec_groups:
                matching_specs = self.spec_values(product.get("specs", ""), evidence_terms)
                if matching_specs:
                    parts.extend(matching_specs)
                else:
                    missing_labels.append(label)
            if missing_labels:
                parts.append(f"chưa có dữ liệu {', '.join(missing_labels)}")
            if asks_gaming:
                known_details = ", ".join(
                    detail
                    for detail in [product.get("description", ""), product.get("specs", "")]
                    if detail
                )
                parts.append(
                    "phù hợp chơi game theo cấu hình đang có"
                    + (f" ({known_details})" if known_details else "")
                )

            verification_note = freshness if (asked_spec_groups or effective_general_specs) else ""
            variant_note = self.variant_warning(product) if asked_spec_groups else ""
            return f"{name}: {'; '.join(parts)}.{verification_note}{variant_note}"

        if asks_availability:
            return (
                f"TechCare đang niêm yết {name} với giá {product['price']}."
                f"{freshness}"
            )
        if asks_price:
            return (
                f"{name} có giá niêm yết {product['price']} trong dữ liệu TechCare hiện tại."
                f"{freshness} Giá thực tế có thể thay đổi theo chương trình bán hàng."
            )
        if asks_warranty:
            return (
                f"{name} được bảo hành {product['warranty']} theo thông tin trong danh mục TechCare."
                f"{freshness} Điều kiện áp dụng vẫn phụ thuộc chính sách bảo hành."
            )
        if asks_general_specs:
            if product.get("specs"):
                return (
                    f"Thông số chính của {name}: {product['specs']}."
                    f"{freshness}{self.variant_warning(product)}"
                )
        if asks_gaming:
            known_details = ", ".join(
                part
                for part in [product.get("description", ""), product.get("specs", "")]
                if part
            )
            return (
                f"{name} phù hợp chơi game dựa trên cấu hình TechCare đang có: {known_details}. "
                "Tuy nhiên catalog chưa có kết quả benchmark, FPS, nhiệt độ và thời lượng pin khi chơi, "
                "nên mình không khẳng định các con số đó."
            )

        known_details = canonical_text(
            f"{product.get('description', '')} {product.get('specs', '')}"
        )
        if asked_spec_groups:
            matching_values: list[str] = []
            missing_labels: list[str] = []
            for label, evidence_terms in asked_spec_groups:
                matching_specs = self.spec_values(product.get("specs", ""), evidence_terms)
                if matching_specs:
                    matching_values.extend(matching_specs)
                elif any(term in known_details for term in evidence_terms):
                    matching_values.append(
                        f"{label}: {product.get('description', '')}; {product.get('specs', '')}"
                    )
                else:
                    missing_labels.append(label)

            if matching_values:
                missing_note = (
                    f" Dữ liệu hiện chưa có {', '.join(missing_labels)}."
                    if missing_labels
                    else ""
                )
                return (
                    f"{name}: {', '.join(matching_values)}."
                    f"{missing_note}{freshness}{self.variant_warning(product)}"
                )
            label_text = ", ".join(missing_labels)
            return (
                f"Dữ liệu TechCare hiện chưa có thông tin {label_text} của {name}, nên mình không tự suy đoán. "
                "Bạn có thể yêu cầu nhân viên xác minh nếu thông tin này ảnh hưởng quyết định mua."
            )

        if any(term in folded for term in ["phu hop", "dung de", "co tot", "danh gia", "nhu cau", "tu van", "chong on", "anc"]):
            details = product.get("description") or product.get("use_case")
            return f"{name}: {details}. Giá niêm yết {product['price']}."
        return None

    @staticmethod
    def spec_values(specs: str, labels: list[str]) -> list[str]:
        """Extract only requested labelled specs instead of dumping the full catalog row."""
        values: list[str] = []
        pattern = re.compile(
            r"(?:^|,\s*)([^,:]{1,40}):\s*(.*?)(?=,\s*[^,:]{1,40}:|$)",
            flags=re.IGNORECASE,
        )
        for match in pattern.finditer(str(specs or "")):
            raw_label = match.group(1).strip()
            value = match.group(2).strip()
            folded_label = canonical_text(raw_label)
            if value and any(label in folded_label for label in labels):
                values.append(f"{raw_label}: {value}")
        return values

    @staticmethod
    def product_freshness_note(product: dict) -> str:
        verified_at = product.get("verified_at")
        if verified_at:
            try:
                verified_text = datetime.fromisoformat(str(verified_at)).strftime("%d/%m/%Y")
            except ValueError:
                verified_text = str(verified_at)
            return f" Thông số đã đối chiếu nguồn hãng ngày {verified_text}."
        value = product.get("updated_at")
        if not value:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return ""
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            vietnam_time = value.astimezone(timezone(timedelta(hours=7)))
            return f" Cập nhật catalog: {vietnam_time.strftime('%d/%m/%Y %H:%M')} (GMT+7)."
        return ""

    @staticmethod
    def variant_warning(product: dict) -> str:
        status = product.get("verification_status")
        if status == "official_verified_family":
            return " Một số chi tiết có thể thay đổi theo mã SKU/khu vực; cần đối chiếu mã máy khi chốt đơn."
        if status == "store_catalog_only":
            return " Tên catalog chưa có mã SKU/part number nên đây là cấu hình cửa hàng khai báo, chưa phải toàn bộ thông số hãng."
        return ""

    def is_comparison_question(self, question: str) -> bool:
        folded = canonical_text(question)
        return any(term in folded for term in ["so sanh", "so voi", "khac nhau", "chon may nao", "tot hon"])

    def comparison_answer(self, products: list[dict]) -> str:
        first, second = products[:2]
        first_price = parse_price(first["price"])
        second_price = parse_price(second["price"])
        if first_price == second_price:
            price_note = "Hai sản phẩm có cùng mức giá trong danh mục."
        else:
            cheaper = first if first_price < second_price else second
            difference = abs(first_price - second_price)
            difference_text = f"{difference:,}".replace(",", ".") + " VND"
            price_note = f"{cheaper['name']} rẻ hơn {difference_text}."
        return (
            f"So sánh nhanh:\n"
            f"- {first['name']}: {first['price']}; bảo hành {first['warranty']}; {first.get('specs') or first.get('description')}.\n"
            f"- {second['name']}: {second['price']}; bảo hành {second['warranty']}; {second.get('specs') or second.get('description')}.\n"
            f"{price_note} Bạn cho mình biết nhu cầu và ngân sách để mình chốt lựa chọn phù hợp hơn nhé."
        )

    def is_recommendation_question(self, question: str) -> bool:
        folded = canonical_text(question)
        if self.find_category(question) and self.extract_budget(question) is not None:
            return True
        return any(
            term in folded
            for term in [
                "tu van", "goi y", "nen mua", "nen chon", "phu hop", "may nao",
                "loai nao", "choi game", "gaming", "van phong", "hoc tap", "lap trinh",
                "chien game", "game ngon", "lam viec", "hoc online", "do hoa", "chup anh",
                "chup hinh", "quay phim", "nghe nhac", "chong on", "ngan sach", "duoi", "tam gia", "tro xuong",
                "khong qua", "toi da", "tro lai", "quay dau", "khoang gia",
                "choi muot", "may manh", "pin trau", "pin lau", "muon may", "uu tien",
                "recommend", "suggest", "which one", "office work", "study", "play game",
            ]
        )

    def is_recommendation_refinement(self, question: str) -> bool:
        folded = canonical_text(question)
        return any(
            term in folded
            for term in [
                "may nao", "loai nao", "may manh", "choi muot", "pin trau",
                "pin lau", "pin tot", "muon may", "uu tien", "tot hon",
                "phu hop hon", "mau khac", "con mau khac", "re nhat",
                "gia tot nhat", "tiet kiem nhat", "chup hinh", "quay phim",
                "stronger", "best battery", "which one", "cheapest",
            ]
        )

    def is_alternative_request(self, question: str) -> bool:
        folded = canonical_text(question)
        return any(
            term in folded
            for term in [
                "mau khac", "con mau khac", "loai khac", "san pham khac",
                "goi y them", "lua chon khac",
                "another model", "other model", "other option",
            ]
        )

    def recommendation_answer(
        self,
        question: str,
        candidates: list[dict] | None = None,
        current_question: str | None = None,
        excluded: list[dict] | None = None,
        alternative: bool = False,
    ) -> str | None:
        products = list(candidates) if candidates else list(self.product_catalog.load_products())
        if excluded:
            excluded_keys = {
                canonical_text(str(item.get("sku") or item.get("name") or ""))
                for item in excluded
            }
            products = [
                item for item in products
                if canonical_text(str(item.get("sku") or item.get("name") or ""))
                not in excluded_keys
            ]
        # Prefer an explicit category from the current turn. For short
        # follow-ups, recover it from the combined context or the previous
        # recommendation set. This prevents "còn mẫu khác" from falling back
        # to the cheapest product in the entire catalog.
        category = self.find_category(current_question or "") or self.find_category(question)
        if category is None:
            context_products = candidates or excluded or []
            context_categories = {
                self.find_category(str(product.get("category") or ""))
                for product in context_products
            }
            context_categories.discard(None)
            if len(context_categories) == 1:
                category = next(iter(context_categories))
        if category:
            category_key = canonical_text(category)
            category_products = [
                product
                for product in products
                if category_key in canonical_text(product["category"])
                or canonical_text(product["category"]) in category_key
            ]
            if category_products:
                products = category_products
            elif alternative:
                return f"Hiện mình chưa còn mẫu {category} khác trong danh mục để gợi ý."

        # In a follow-up, the combined context also contains prices printed by
        # the bot. Only the current user message is allowed to define a budget.
        budget = self.extract_budget(current_question or question)
        if budget:
            within_budget = [product for product in products if 0 < parse_price(product["price"]) <= budget]
            if within_budget:
                products = within_budget
            else:
                priced_products = [
                    product for product in products if parse_price(product["price"]) > 0
                ]
                if not priced_products:
                    return None
                nearest = min(priced_products, key=lambda item: parse_price(item["price"]))
                difference = parse_price(nearest["price"]) - budget
                budget_text = f"{budget:,}".replace(",", ".") + " VND"
                difference_text = f"{difference:,}".replace(",", ".") + " VND"
                category_text = category or "sản phẩm phù hợp"
                return (
                    f"Hiện TechCare chưa có {category_text} nào giá từ {budget_text} trở xuống. "
                    f"Mẫu gần ngân sách nhất là {nearest['name']} ({nearest['price']}), "
                    f"cao hơn {difference_text}."
                )

        folded = canonical_text(question)
        current_folded = canonical_text(current_question or question)
        intent_terms: list[str] = []
        intent_groups = {
            "gaming": ["choi game", "gaming", "choi muot", "chien game", "game ngon", "fps", "rtx", "rog", "tuf", "alienware", "legion", "loq", "aorus"],
            "văn phòng/học tập": ["van phong", "hoc tap", "sinh vien", "lam viec", "hoc online", "mong nhe", "office"],
            "lập trình": ["lap trinh", "ram", "ssd", "core i5", "core i7", "ryzen"],
            "đồ họa": ["do hoa", "thiet ke", "render", "rtx", "proart", "gpu"],
            "chụp ảnh": ["chup anh", "chup hinh", "camera", "quay phim", "quay video", "pixel", "ultra", "pro"],
            "pin lâu": ["pin trau", "pin lau", "thoi luong pin", "pin tot", "mah", "wh"],
            "chống ồn": ["chong on", "anc", "pro"],
        }
        matched_intent = "nhu cầu của bạn"
        for label, terms in intent_groups.items():
            if any(term in current_folded for term in terms):
                matched_intent = label
                intent_terms = terms
                break
        if not intent_terms:
            for label, terms in intent_groups.items():
                if any(term in folded for term in terms[:3]):
                    matched_intent = label
                    intent_terms = terms
                    break

        performance_priority = any(
            term in current_folded
            for term in [
                "choi muot", "chien game", "play game", "may manh",
                "hieu nang", "fps cao", "cau hinh manh",
            ]
        )
        battery_priority = any(
            term in current_folded
            for term in ["pin trau", "pin lau", "pin tot", "thoi luong pin"]
        )
        cheapest_priority = any(
            term in current_folded
            for term in ["re nhat", "gia tot nhat", "tiet kiem nhat"]
        )

        if cheapest_priority and products:
            lowest_price = min(parse_price(product["price"]) for product in products)
            cheapest = [
                product for product in products
                if parse_price(product["price"]) == lowest_price
            ]
            names = " và ".join(product["name"] for product in cheapest)
            return (
                f"Rẻ nhất trong các mẫu vừa gợi ý là {names}, giá {cheapest[0]['price']}."
            )

        def performance_score(product: dict) -> int:
            haystack = canonical_text(
                " ".join(
                    [product.get("name", ""), product.get("description", ""), product.get("specs", "")]
                )
            )
            score = 0
            gpu_match = re.search(r"rtx\s*(\d{4})", haystack)
            if gpu_match:
                score += int(gpu_match.group(1)) * 100
            ram_match = re.search(r"ram\s*:?\s*(\d+)\s*gb", haystack)
            if ram_match:
                score += int(ram_match.group(1)) * 20
            if any(term in haystack for term in ["core i9", "ryzen 9", "core ultra 9"]):
                score += 500
            elif any(term in haystack for term in ["core i7", "ryzen 7", "core ultra 7"]):
                score += 300
            return score

        def battery_score(product: dict) -> int:
            haystack = canonical_text(
                f"{product.get('description', '')} {product.get('specs', '')}"
            )
            mah = [int(value) for value in re.findall(r"\b(\d{3,5})\s*mah\b", haystack)]
            wh = [int(value) for value in re.findall(r"\b(\d{2,3})\s*wh\b", haystack)]
            hours = [int(value) for value in re.findall(r"\b(?:toi da\s*)?(\d{1,3})\s*gio\b", haystack)]
            if mah:
                return max(mah) * 100
            if wh:
                return max(wh) * 100
            if hours:
                return max(hours)
            return 0

        def rank(product: dict) -> tuple[int, int, int, int]:
            haystack = canonical_text(
                " ".join(
                    [product.get("name", ""), product.get("description", ""), product.get("specs", "")]
                )
            )
            relevance = sum(1 for term in intent_terms if term in haystack)
            performance = performance_score(product) if performance_priority else 0
            battery = battery_score(product) if battery_priority else 0
            return (-relevance, -performance, -battery, parse_price(product["price"]))

        candidates = sorted(products, key=rank)[:3]
        if not candidates:
            return None
        budget_text = (
            f" trong ngân sách tối đa {budget:,} VND".replace(",", ".") if budget else ""
        )
        intro = "Một số mẫu khác" if alternative else f"Mình gợi ý {len(candidates)} lựa chọn"
        lines = [f"{intro} cho {matched_intent}{budget_text}:"]
        for product in candidates:
            spec_parts = [
                part.strip()
                for part in str(product.get("specs") or "").split(",")
                if any(
                    key in canonical_text(part)
                    for key in ["chip", "cpu", "gpu", "ram", "ssd", "man hinh"]
                )
            ][:4]
            reason = "; ".join(spec_parts) or product.get("description") or product.get("use_case")
            lines.append(f"- {product['name']} — {product['price']}: {reason}.")
        if performance_priority and candidates:
            lines.append(
                f"Nếu ưu tiên chơi mượt/hiệu năng, {candidates[0]['name']} là mẫu mạnh nhất "
                "trong các lựa chọn trên dựa trên cấu hình CPU, GPU và RAM đang có."
            )
        if battery_priority:
            battery_evidence = [
                product
                for product in candidates
                if re.search(
                    r"\b\d+\s*wh\b|\bpin\s*:",
                    canonical_text(f"{product.get('description', '')} {product.get('specs', '')}"),
                )
            ]
            if not battery_evidence:
                lines.append(
                    "Về pin, catalog chưa có dung lượng pin hoặc kết quả sử dụng thực tế của "
                    "các mẫu này, nên mình chưa khẳng định mẫu nào “pin trâu”."
                )
        return "\n".join(lines)

    def extract_budget(self, question: str) -> int | None:
        folded = canonical_text(question)
        amounts: list[int] = []

        # Common chat notation: 10tr5 = 10.5 million, 10tr500 = 10.5 million.
        for match in re.finditer(r"\b(\d+)\s*(?:tr|m)(\d{1,3})\b", folded):
            major = int(match.group(1))
            suffix = match.group(2)
            divisor = 10 ** len(suffix)
            amounts.append(int((major + int(suffix) / divisor) * 1_000_000))

        for match in re.finditer(
            r"(\d+(?:[.,]\d+)?)\s*(?:trieu|tr|million|m|cu)\b",
            folded,
        ):
            amounts.append(
                int(float(match.group(1).replace(",", ".")) * 1_000_000)
            )

        compact_money = folded.replace(".", "").replace(",", "")
        amounts.extend(
            int(match.group(1))
            for match in re.finditer(r"\b(\d{5,9})\b", compact_money)
        )
        return max(amounts) if amounts else None

    def extract_order_code(self, question: str) -> str | None:
        match = re.search(r"\b(?:TC)?DH[-_ ]?\d{4,}\b", question, flags=re.IGNORECASE)
        return re.sub(r"[-_ ]", "", match.group(0)).upper() if match else None

    def is_order_lookup(self, question: str) -> bool:
        folded = canonical_text(question)
        has_order = self.extract_order_code(question) is not None or "don hang" in folded
        asks_status = any(term in folded for term in ["o dau", "trang thai", "kiem tra", "tra cuu", "giao chua", "khi nao giao"])
        return has_order and asks_status

    def mentioned_known_product(self, question: str) -> dict | None:
        products = self.mentioned_products(question)
        return products[0] if products else None

    def products_by_category(self, category: str | None) -> list[dict]:
        category_key = canonical_text(category or "")
        products: list[dict] = []
        accessory_subcategories = {
            "chuot": ["chuot", "mouse"],
            "ban phim": ["ban phim", "keyboard"],
            "sac du phong": ["sac du phong", "powerbank", "pin du phong"],
        }
        for product in self.product_catalog.load_products():
            product_category = canonical_text(product["category"])
            product_text = canonical_text(
                f"{product['name']} {product.get('description', '')} {product.get('specs', '')}"
            )
            if product_category == category_key:
                products.append(product)
            elif category_key == "phu kien" and product_category in {
                "phu kien", "sac du phong", "ban phim", "chuot"
            }:
                products.append(product)
            elif category_key == "dong ho thong minh" and "dong ho" in product_category:
                products.append(product)
            elif category_key in accessory_subcategories and any(
                term in product_text for term in accessory_subcategories[category_key]
            ):
                products.append(product)
        return products

    def has_availability_phrase(self, question: str) -> bool:
        folded = canonical_text(question)
        if any(
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
                "do you sell",
                "available",
                "in stock",
            ]
        ):
            return True
        # Natural phrasing often omits the verb "bán": "shop có iPhone 17
        # không?". Match only when a product family follows "có" directly so
        # feature questions such as "Xiaomi 15 có pin trâu không" stay factual.
        return bool(
            re.search(
                r"\bco\s+(?:ban\s+)?(?:iphone|samsung|galaxy|xiaomi|redmi|pixel|"
                r"macbook|ipad|airpods|dell|asus|lenovo|hp|acer|msi|gigabyte)\b",
                folded,
            )
        )

    def is_unknown_product_availability_question(self, question: str) -> bool:
        if self.mentioned_known_product(question) is not None:
            return False
        folded = canonical_text(question)
        product_like_words = [
            "iphone", "ip", "samsung", "galaxy", "oppo", "xiaomi", "redmi",
            "airpod", "ipad", "macbook", "pixel", "sony", "lg", "nintendo",
            "playstation",
        ]
        asks_availability = self.has_availability_phrase(question) or bool(
            re.search(r"\bco (?:khong|ko|k)\b", folded)
        )
        has_model_number = any(character.isdigit() for character in folded)
        if asks_availability and has_model_number and any(word in folded for word in product_like_words):
            return True
        if self.find_category(question) is not None:
            return False
        # If the customer explicitly asks whether an unrecognised item is sold
        # and it is not one of our known categories, never let the LLM invent
        # stock information. Offer safe external search links instead.
        return asks_availability

    def is_greeting(self, question: str) -> bool:
        folded = canonical_text(question)
        folded = re.sub(r"[^\w\s]", " ", folded)
        folded = re.sub(r"\s+", " ", folded).strip()
        return folded in GREETING_PATTERNS

    def is_too_vague_for_rag(self, question: str) -> bool:
        folded = canonical_text(question)
        folded = re.sub(r"[^\w\s-]", " ", folded)
        tokens = [token for token in folded.split() if token]
        useful_terms = {"gia", "bao", "nhieu", "mua", "co", "laptop", "dien", "thoai", "tablet", "tai", "nghe", "chuot", "phim", "sac", "pin", "don", "bh", "hanh", "ship", "game"}
        return not self.is_greeting(question) and len(tokens) <= 2 and not any(token in useful_terms for token in tokens)

    def is_category_availability_question(self, question: str) -> bool:
        return self.has_availability_phrase(question) and self.find_category(question) is not None

    def is_category_followup(self, question: str) -> bool:
        folded = canonical_text(question)
        tokens = [token for token in re.sub(r"[^\w\s]", " ", folded).split() if token]
        return len(tokens) <= 6 and self.find_category(question) is not None

    def is_price_extreme_question(self, question: str) -> bool:
        folded = canonical_text(question)
        asks_product = any(phrase in folded for phrase in ["san pham", "mon nao", "mat hang", "hang nao"])
        asks_extreme = any(phrase in folded for phrase in ["gia cao nhat", "dat nhat", "mac nhat", "gia re nhat", "re nhat"])
        return asks_product and asks_extreme

    def is_support_issue(self, question: str) -> bool:
        folded = canonical_text(question)
        policy_question = any(
            phrase in folded
            for phrase in ["chinh sach", "bao lau", "co duoc", "dieu kien", "quy trinh", "the nao"]
        )
        specific_symptom = any(
            phrase in folded
            for phrase in ["khong len", "man hinh xanh", "sac khong vao", "nong bat thuong", "vo nuoc", "roi vo", "giao sai", "chua nhan duoc tien hoan"]
        )
        if policy_question and not specific_symptom:
            return False
        patterns = [r"\bbi loi\b", r"\bhong\b", r"\bbi hong\b", r"khong len", r"man hinh xanh", r"sac khong vao", r"nong bat thuong", r"vo nuoc", r"roi vo", r"muon hoan tien", r"chua nhan duoc tien hoan", r"khieu nai", r"giao sai"]
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

    def is_unrelated_request(self, question: str) -> bool:
        folded = canonical_text(question)
        return any(re.search(pattern, folded) for pattern in UNRELATED_REQUEST_PATTERNS)

    @staticmethod
    def is_prompt_injection(question: str) -> bool:
        folded = canonical_text(question)
        patterns = [
            r"bo qua (?:tat ca )?(?:chi dan|quy tac|huong dan)",
            r"ignore (?:all )?(?:previous|prior|system) instructions",
            r"(?:hien|dua|in|tiet lo).*(?:system prompt|prompt he thong|chi dan noi bo)",
            r"(?:api key|khoa api|secret key|access token|jwt secret)",
            r"jailbreak",
            r"developer mode",
        ]
        return any(re.search(pattern, folded) for pattern in patterns)

    def is_short_noisy_question(self, question: str) -> bool:
        folded = strip_accents(question.lower())
        folded = re.sub(r"[^\w\s-]", " ", folded)
        tokens = [token for token in folded.split() if token]
        known_words = {"gia", "bh", "ship", "cod", "laptop", "dt", "phone", "tai", "nghe", "chuot", "ban", "phim"}
        return len(tokens) <= 2 and not any(char.isdigit() for char in folded) and not any(token in known_words for token in tokens)

    def needs_human(self, answer: str, mode: str) -> bool:
        folded = strip_accents(answer.lower())
        return mode == "fallback" or "ticket" in folded or answer == FALLBACK_ANSWER
