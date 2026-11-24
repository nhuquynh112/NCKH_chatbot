"""Conservative first-party FAQ matching. Never rank on answer text alone."""
from __future__ import annotations

import json
from pathlib import Path
import re
from functools import lru_cache

from app.rag.query_rewriter import QueryRewriter, strip_accents


DEFAULT_FAQ_PATH = Path(__file__).resolve().parents[2] / "rag_data" / "faq_curated.json"
STOP = {"co", "khong", "ko", "k", "a", "ah", "oi", "la", "gi", "j", "nao", "the", "toi", "minh", "ban", "shop", "cua", "ve", "cho", "techcare", "ho", "tro", "hang", "vay", "duoc", "hay", "va"}
LEGACY_UNVERIFIED_ANSWERS = {
    "Chào bạn, TechCare hỗ trợ trả góp 0% qua thẻ tín dụng và qua các công ty tài chính như Home Credit, HD Saison. Thủ tục rất đơn giản và duyệt nhanh trong 15 phút.",
    "Tất cả sản phẩm lỗi do nhà sản xuất sẽ được 1 ĐỔI 1 miễn phí trong 30 ngày đầu tiên. Các tháng tiếp theo áp dụng chính sách bảo hành của hãng.",
}


@lru_cache(maxsize=4096)
def normalize(text: str) -> str:
    expanded = QueryRewriter().expand_for_retrieval(text).split("\n")[-1]
    folded = strip_accents(expanded.lower())
    aliases = {"tien ve": "hoan tien", "tien lai": "lai suat", "phi ship": "phi giao hang", "phi van chuyen": "phi giao hang", "kiem hang": "kiem tra hang", "mo hop": "kiem tra hang", "ship ve tinh": "giao hang tinh", "tinh sao": "tinh the nao", "may ngay": "bao lau", "tra tien": "thanh toan", "nghi chu nhat": "gio lam viec chu nhat"}
    for old, new in aliases.items():
        folded = folded.replace(old, new)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%]+", " ", folded)).strip()


def tokens(text: str) -> set[str]:
    return {t for t in normalize(text).split() if len(t) > 1 and t not in STOP}


def rank_admin_faqs(question: str, faqs) -> list[dict]:
    query = normalize(question)
    query_tokens = tokens(question)
    ranked = []
    for faq in faqs:
        # Exact fingerprints of the original unverified demo seed, not a
        # general override of administrator policy. Leave database rows intact.
        if faq.answer in LEGACY_UNVERIFIED_ANSWERS:
            continue
        title = normalize(faq.question)
        title_tokens = tokens(faq.question)
        keyword_tokens = tokens(" ".join(faq.keywords or []))
        shared = query_tokens & (title_tokens | keyword_tokens)
        coverage = len(shared) / max(1, len(query_tokens))
        title_coverage = len(query_tokens & title_tokens) / max(1, len(title_tokens))
        exact = query == title
        score = 1.0 if exact else .7 * coverage + .3 * title_coverage
        if not exact and (len(shared) < 2 or coverage < .55):
            continue
        ranked.append({"id":f"faq-{faq.id}", "title":faq.question, "answer":faq.answer,
                       "content":f"Câu hỏi: {faq.question}\nCâu trả lời: {faq.answer}",
                       "exact":exact, "direct":exact or (coverage >= .8 and title_coverage >= .6),
                       "score":score, "metadata":{"source":"faq_database", "category":faq.category}})
    ranked.sort(key=lambda row: (row["exact"], row["score"]), reverse=True)
    if len(ranked) > 1 and not ranked[0]["exact"] and ranked[0]["score"] - ranked[1]["score"] < .12:
        for row in ranked:
            row["direct"] = False
    return ranked[:3]


def load_curated_faqs(path: Path = DEFAULT_FAQ_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["faqs"] if path.exists() else []


def match_curated_faqs(question: str, faqs: list[dict] | None = None) -> list[dict]:
    query = normalize(question)
    matched = []
    for faq in faqs if faqs is not None else load_curated_faqs():
        exact = query in [normalize(v) for v in [faq["question"], *faq.get("variants", [])]]
        triggers = [normalize(v) for v in faq.get("triggers", [])]
        lengths = [len(t.split()) for t in triggers if re.search(r"\b" + re.escape(t) + r"\b", query)]
        if not exact and not lengths:
            continue
        if any(re.search(r"\b" + re.escape(normalize(v)) + r"\b", query) for v in faq.get("exclude", [])):
            continue
        matched.append((100 if exact else max(lengths), faq))
    matched.sort(key=lambda row: row[0], reverse=True)
    # Answer at most one FAQ per subject, but allow fees + delivery duration.
    selected = []
    subjects = set()
    for _, faq in matched:
        subject = faq.get("subject", faq["id"])
        if subject not in subjects:
            selected.append(faq)
            subjects.add(subject)
    return selected[:3]
