import argparse
from functools import lru_cache
import json
import math
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:11434"
CHAT_MODEL = "qwen2.5:3b"
EMBED_MODEL = "nomic-embed-text"
APP_VERSION = "v2.1-guardrails"
ROOT = Path(__file__).resolve().parent
KB_PATH = ROOT / "knowledge_base.md"
EXTRA_KB_PATHS = [ROOT / "product_catalog_extended.md"]
PROMPT_PATH = ROOT / "system_prompt.txt"
INDEX_PATH = ROOT / "vector_index.json"
PRODUCTS_PATH = ROOT / "techcare_products_100.json"
MIN_RETRIEVAL_SCORE = 0.55
FALLBACK_ANSWER = (
    "Mình chưa có đủ thông tin để xác nhận nội dung này trong dữ liệu hiện tại. "
    "Mình có thể tạo ticket để nhân viên TechCare kiểm tra và tư vấn chính xác hơn cho bạn."
)
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
CORE_PRODUCTS = [
    {
        "sku": "TC-LT-001",
        "name": "Laptop NovaBook Air 14",
        "category": "laptop",
        "price": "14.990.000 VND",
        "use_case": "học tập, văn phòng, học online, Word, Excel, PowerPoint và lập trình cơ bản",
    },
    {
        "sku": "TC-LT-002",
        "name": "Laptop GamePro 15",
        "category": "laptop",
        "price": "24.990.000 VND",
        "use_case": "chơi game, đồ họa 2D/3D, render video và học ngành kỹ thuật",
    },
    {
        "sku": "TC-LT-003",
        "name": "Laptop EduBook 13",
        "category": "laptop",
        "price": "9.990.000 VND",
        "use_case": "học online, làm bài tập, duyệt web, Word và Excel cơ bản",
    },
    {
        "sku": "TC-PH-004",
        "name": "Điện thoại PixelOne A55",
        "category": "điện thoại",
        "price": "7.990.000 VND",
        "use_case": "chụp ảnh, mạng xã hội, xem phim và chơi game nhẹ",
    },
    {
        "sku": "TC-PH-005",
        "name": "Điện thoại PixelOne Pro X",
        "category": "điện thoại",
        "price": "15.990.000 VND",
        "use_case": "camera tốt, hiệu năng cao và dùng lâu dài",
    },
    {
        "sku": "TC-TB-006",
        "name": "Máy tính bảng TabLearn 11",
        "category": "máy tính bảng",
        "price": "8.490.000 VND",
        "use_case": "ghi chú, học online, đọc tài liệu, xem video và làm việc nhẹ",
    },
    {
        "sku": "TC-HP-007",
        "name": "Tai nghe SonicBuds Pro",
        "category": "tai nghe",
        "price": "1.990.000 VND",
        "use_case": "học online, nghe nhạc, gọi điện và di chuyển ngoài đường",
    },
    {
        "sku": "TC-HP-008",
        "name": "Tai nghe SonicBuds Lite",
        "category": "tai nghe",
        "price": "790.000 VND",
        "use_case": "nghe gọi cơ bản và ngân sách tiết kiệm",
    },
    {
        "sku": "TC-WA-009",
        "name": "Đồng hồ FitWatch S2",
        "category": "đồng hồ thông minh",
        "price": "2.490.000 VND",
        "use_case": "theo dõi sức khỏe, luyện tập và nhận thông báo điện thoại",
    },
    {
        "sku": "TC-PB-010",
        "name": "Sạc dự phòng VoltPack 20K",
        "category": "sạc dự phòng",
        "price": "890.000 VND",
        "use_case": "pin dự phòng dung lượng cao khi đi học, đi làm hoặc du lịch",
    },
]


def ollama_post(path, payload):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SystemExit(
            "Không kết nối được Ollama. Hãy mở Ollama và kiểm tra model đã pull chưa."
        ) from exc


def embed(text):
    result = ollama_post("/api/embeddings", {"model": EMBED_MODEL, "prompt": text})
    return result["embedding"]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def split_markdown_sections(text):
    sections = []
    current_title = "Tong quan"
    current_lines = []

    for line in text.splitlines():
        if line.startswith("# "):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line.lstrip("# ").strip()
            current_lines = [line]
        elif line.startswith("## "):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line.lstrip("# ").strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))

    return [item for item in sections if item[1]]


def build_index():
    parts = [KB_PATH.read_text(encoding="utf-8")]
    for path in EXTRA_KB_PATHS:
        if path.exists():
            parts.append(path.read_text(encoding="utf-8"))
    text = "\n\n".join(parts)
    sections = split_markdown_sections(text)
    records = []

    print(f"Creating embeddings for {len(sections)} data sections...")
    for idx, (title, content) in enumerate(sections, start=1):
        records.append(
            {
                "id": f"doc_{idx:03d}",
                "title": title,
                "content": content,
                "embedding": embed(content),
            }
        )

    INDEX_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Created index: {INDEX_PATH}")


def load_index():
    if not INDEX_PATH.exists():
        build_index()
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def parse_price(price_text):
    digits = re.sub(r"\D", "", price_text)
    return int(digits) if digits else 0


@lru_cache(maxsize=1)
def load_products():
    products = list(CORE_PRODUCTS)
    if PRODUCTS_PATH.exists():
        products.extend(json.loads(PRODUCTS_PATH.read_text(encoding="utf-8")))
    return products


def find_category(question):
    folded = strip_accents(question.lower())
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in folded for keyword in keywords):
            return category
    return None


def has_availability_phrase(question):
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


def mentioned_known_product(question):
    folded = strip_accents(question.lower())
    compact = re.sub(r"[^a-z0-9]+", "", folded)
    for product in load_products():
        name_folded = strip_accents(product["name"].lower())
        name_compact = re.sub(r"[^a-z0-9]+", "", name_folded)
        sku_compact = re.sub(r"[^a-z0-9]+", "", product["sku"].lower())
        if name_compact and name_compact in compact:
            return product
        if sku_compact and sku_compact in compact:
            return product
    return None


def is_unknown_product_availability_question(question):
    if mentioned_known_product(question) is not None:
        return False

    folded = strip_accents(question.lower())
    product_like_words = [
        "iphone",
        "ip",
        "samsung",
        "oppo",
        "xiaomi",
        "airpod",
        "ipad",
        "macbook",
        "sony",
        "lg",
    ]
    if any(word in folded for word in product_like_words):
        return True

    if find_category(question) is not None:
        return False

    asks_availability = has_availability_phrase(question) or any(word in folded for word in product_like_words)
    has_model_number = bool(re.search(r"\b\d{2}\b|\b\d{2,3}[a-z]?\b", folded))
    return asks_availability and (has_model_number or any(word in folded for word in product_like_words))


def is_greeting(question):
    folded = strip_accents(question.lower())
    folded = re.sub(r"[^\w\s]", " ", folded)
    folded = re.sub(r"\s+", " ", folded).strip()
    return folded in GREETING_PATTERNS


def is_too_vague_for_rag(question):
    folded = strip_accents(question.lower())
    folded = re.sub(r"[^\w\s-]", " ", folded)
    tokens = [token for token in folded.split() if token]
    if is_greeting(question):
        return False
    useful_terms = {
        "gia",
        "bao",
        "nhieu",
        "mua",
        "co",
        "laptop",
        "dien",
        "thoai",
        "tablet",
        "tai",
        "nghe",
        "chuot",
        "phim",
        "sac",
        "pin",
        "don",
        "bh",
        "bao",
        "hanh",
        "ship",
        "game",
    }
    return len(tokens) <= 2 and not any(token in useful_terms for token in tokens)


def products_by_category(category):
    return [product for product in load_products() if product["category"] == category]


def is_category_availability_question(question):
    return has_availability_phrase(question) and find_category(question) is not None


def is_category_followup(question):
    folded = strip_accents(question.lower())
    tokens = [token for token in re.sub(r"[^\w\s]", " ", folded).split() if token]
    return len(tokens) <= 4 and find_category(question) is not None


def is_price_extreme_question(question):
    folded = strip_accents(question.lower())
    asks_product = any(phrase in folded for phrase in ["san pham", "mon nao", "mat hang", "hang nao"])
    asks_extreme = any(phrase in folded for phrase in ["gia cao nhat", "dat nhat", "mac nhat", "gia re nhat", "re nhat"])
    return asks_product and asks_extreme


def is_support_issue(question):
    folded = strip_accents(question.lower())
    issue_patterns = [
        r"\bloi\b",
        r"\bbi loi\b",
        r"\bhong\b",
        r"\bbi hong\b",
        r"khong len",
        r"man hinh xanh",
        r"sac khong vao",
        r"nong bat thuong",
        r"vo nuoc",
        r"roi vo",
        r"hoan tien",
        r"khieu nai",
        r"giao sai",
    ]
    return any(re.search(pattern, folded) for pattern in issue_patterns)


def deterministic_answer(question):
    folded = strip_accents(question.lower())

    if is_greeting(question):
        return (
            "Chào bạn, mình là chatbot hỗ trợ khách hàng của TechCare Electronics. "
            "Bạn cần hỏi về sản phẩm, giá bán, bảo hành, giao hàng hay kiểm tra đơn hàng ạ?"
        )

    if is_too_vague_for_rag(question):
        return (
            "Mình chưa hiểu rõ bạn cần hỗ trợ nội dung gì. "
            "Bạn có thể hỏi cụ thể hơn, ví dụ: 'laptop nào chơi game ngon', 'tai nghe nào có chống ồn', hoặc 'đơn TCDH1007 đang ở đâu'."
        )

    if is_unknown_product_availability_question(question):
        return (
            "Mình chưa có đủ thông tin để xác nhận sản phẩm này có trong dữ liệu TechCare hiện tại. "
            "Bạn có thể cho mình tên sản phẩm chính xác hơn, hoặc mình sẽ tạo ticket để nhân viên kiểm tra giúp bạn."
        )

    if is_support_issue(question):
        return (
            "Mình sẽ tạo ticket để nhân viên kỹ thuật kiểm tra trường hợp này. "
            "Bạn vui lòng cung cấp mã đơn hàng, số điện thoại mua hàng, tên sản phẩm, mô tả lỗi cụ thể "
            "và hình ảnh/video minh chứng nếu có. Nhân viên TechCare sẽ phản hồi trong tối đa 24 giờ làm việc."
        )

    known_product = mentioned_known_product(question)
    if has_availability_phrase(question) and known_product is not None:
        return (
            f"Có. TechCare có bán {known_product['name']} ({known_product['sku']}), "
            f"giá niêm yết {known_product['price']}, thuộc nhóm {known_product['category']}. "
            f"Sản phẩm này phù hợp với nhu cầu {known_product.get('use_case', 'sử dụng hằng ngày')}."
        )

    if is_category_availability_question(question) or is_category_followup(question):
        category = find_category(question)
        products = products_by_category(category)
        if not products:
            return None
        examples = products[:5]
        names = ", ".join(f"{item['name']} ({item['price']})" for item in examples)
        return (
            f"Có. TechCare có bán nhóm {category}. Một số mẫu hiện có: {names}. "
            "Bạn muốn mình tư vấn mẫu giá tốt, mẫu cao cấp hay mẫu phù hợp nhu cầu cụ thể?"
        )

    if is_price_extreme_question(question):
        products = load_products()
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


def direct_source_hits(question, records, default_hits):
    if is_support_issue(question):
        filtered = [
            (1.0, record)
            for record in records
            if any(keyword in record["title"].lower() for keyword in ["quy trình tạo ticket", "chính sách bảo hành", "chính sách đổi trả"])
        ]
        if filtered:
            return filtered[:4]

    if is_greeting(question) or is_too_vague_for_rag(question):
        filtered = [
            (1.0, record)
            for record in records
            if any(keyword in record["title"].lower() for keyword in ["hồ sơ doanh nghiệp", "techcare electronics"])
        ]
        return filtered[:1]

    if is_unknown_product_availability_question(question):
        filtered = [
            (1.0, record)
            for record in records
            if any(keyword in record["title"].lower() for keyword in ["quy trình tạo ticket", "catalog"])
        ]
        if filtered:
            return filtered[:4]

    category = find_category(question)
    if category:
        category_folded = strip_accents(category.lower())
        filtered = [
            (1.0, record)
            for record in records
            if category_folded in strip_accents(record["title"].lower())
            or f"nhom {category_folded}" in strip_accents(record["content"].lower())
            or f"nhóm {category}" in record["content"].lower()
        ]
        if filtered:
            return filtered[:4]

    answer = deterministic_answer(question)
    if answer:
        answer_folded = strip_accents(answer.lower())
        filtered = [
            (1.0, record)
            for record in records
            if strip_accents(record["title"].lower()) in answer_folded
        ]
        if filtered:
            return filtered[:4]

    return default_hits


def score_adjustment(question, record):
    question_lower = question.lower()
    title_lower = record["title"].lower()
    content_lower = record["content"].lower()
    text = title_lower + " " + content_lower
    adjustment = 0.0

    recommendation_words = [
        "chơi game",
        "gaming",
        "render",
        "đồ họa",
        "do hoa",
        "học online",
        "hoc online",
        "sinh viên",
        "sinh vien",
        "văn phòng",
        "van phong",
        "tư vấn",
        "tu van",
        "phù hợp",
        "phu hop",
    ]
    policy_words = [
        "bảo hành",
        "bao hanh",
        "đổi trả",
        "doi tra",
        "giao hàng",
        "giao hang",
        "thanh toán",
        "thanh toan",
        "ticket",
        "đơn",
        "don",
    ]

    if any(word in question_lower for word in recommendation_words):
        if any(word in text for word in ["game", "gaming", "render", "đồ họa", "do hoa", "rtx", "gpu", "tư vấn", "tu van", "phù hợp", "phu hop"]):
            adjustment += 0.12
        if any(word in title_lower for word in ["chính sách", "lưu ý", "ticket", "bảo hành", "đổi trả", "giao hàng", "thanh toán"]):
            adjustment -= 0.14

    if any(word in question_lower for word in ["máy nào", "may nao", "laptop nào", "laptop nao"]) and any(
        word in question_lower for word in ["chơi game", "choi game", "gaming", "game ngon"]
    ):
        if any(word in text for word in ["laptop", "gpu", "rtx", "gamepro", "creatorbook"]):
            adjustment += 0.35
        if any(word in title_lower for word in ["chính sách", "lưu ý", "ticket", "giao hàng", "thanh toán", "đổi trả", "bảo hành"]):
            adjustment -= 0.35
        if any(word in text for word in ["chuột", "chuot", "bàn phím", "ban phim", "tai nghe"]):
            adjustment -= 0.18

    if any(word in question_lower for word in policy_words):
        if any(word in title_lower for word in ["chính sách", "giao hàng", "thanh toán", "ticket", "trạng thái", "đơn hàng"]):
            adjustment += 0.10

    for token in question_lower.replace("?", " ").replace(",", " ").split():
        if len(token) >= 5 and token in title_lower:
            adjustment += 0.03

    return adjustment


def retrieve(question, records, top_k=4):
    retrieval_question = expand_question_for_retrieval(question)
    q_embedding = embed(retrieval_question)
    scored = []
    for record in records:
        base_score = cosine(q_embedding, record["embedding"])
        scored.append((base_score + score_adjustment(question, record), record))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[:top_k]


def strip_accents(text):
    normalized = unicodedata.normalize("NFD", text)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def expand_question_for_retrieval(question):
    folded = strip_accents(question.lower())
    folded = re.sub(r"[^\w\s-]", " ", folded)
    folded = re.sub(r"\s+", " ", folded).strip()

    rewritten = folded
    for pattern, replacement in QUERY_REWRITE_RULES:
        rewritten = re.sub(pattern, replacement, rewritten, flags=re.IGNORECASE)

    # Giữ cả câu gốc và câu đã chuẩn hóa để embedding bắt được tên riêng/SKU.
    if rewritten and rewritten != question:
        return f"{question}\n{rewritten}"
    return question


def is_clearly_out_of_scope(question):
    question_lower = question.lower()
    folded = strip_accents(question_lower)
    return any(keyword in question_lower or keyword in folded for keyword in OUT_OF_SCOPE_KEYWORDS)


def is_short_noisy_question(question):
    folded = strip_accents(question.lower())
    folded = re.sub(r"[^\w\s-]", " ", folded)
    tokens = [token for token in folded.split() if token]
    if len(tokens) <= 2 and not any(char.isdigit() for char in folded):
        known_words = {
            "gia",
            "bh",
            "ship",
            "cod",
            "laptop",
            "dt",
            "phone",
            "tai",
            "nghe",
            "chuot",
            "ban",
            "phim",
        }
        return not any(token in known_words for token in tokens)
    return False


def should_fallback(question, hits):
    if is_clearly_out_of_scope(question):
        return True
    if is_short_noisy_question(question):
        return True
    if not hits:
        return True
    best_score = hits[0][0]
    return best_score < MIN_RETRIEVAL_SCORE


def chat(question, context):
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    user_prompt = f"""NGỮ CẢNH:
{context}

CÂU HỎI KHÁCH HÀNG:
{question}

Hãy trả lời theo đúng nguyên tắc. Nếu khách chỉ hỏi tư vấn hoặc hỏi giá sản phẩm, không tự thêm phần bảo hành/ticket trừ khi khách hỏi về lỗi, bảo hành, đổi trả hoặc hỗ trợ kỹ thuật."""

    result = ollama_post(
        "/api/chat",
        {
            "model": CHAT_MODEL,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {"temperature": 0.2},
        },
    )
    return result["message"]["content"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="Rebuild vector index")
    args = parser.parse_args()

    if args.build:
        build_index()
        return

    records = load_index()
    print(f"TechCare Electronics RAG chatbot {APP_VERSION}. Gõ 'exit' để thoát.")

    while True:
        question = input("\nKhách hàng: ").strip()
        if question.lower() in {"exit", "quit", "q"}:
            break
        if not question:
            continue

        direct_answer = deterministic_answer(question)
        if direct_answer:
            answer = direct_answer
            hits = direct_source_hits(question, records, [])
        else:
            hits = retrieve(question, records)
            if should_fallback(question, hits):
                answer = FALLBACK_ANSWER
            else:
                context = "\n\n---\n\n".join(hit[1]["content"] for hit in hits)
                answer = chat(question, context)

        print("\nChatbot:")
        print(answer)
        print("\nNguồn RAG:")
        for score, record in hits:
            print(f"- {record['id']} | {score:.3f} | {record['title']}")


if __name__ == "__main__":
    main()
