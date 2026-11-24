"""Conservative checks for generated facts and operations the LLM cannot perform."""
import re
from app.rag.query_rewriter import strip_accents


def unsupported_claims(answer: str, context: str) -> list[str]:
    def facts(text):
        text = strip_accents(text.lower())
        return {(
            re.sub(r"[.,]", "", number), "dong" if unit in {"vnd", "d", "dong"} else unit
        ) for number, unit in re.findall(r"\b(\d+(?:[.,]\d+)*)\s*(vnd|dong|gb|tb|mah|wh|ghz|hz|thang|ngay|gio|phut|d|%)(?!\w)", text)}
    missing = [f"{number} {unit}" for number, unit in facts(answer) - facts(context)]
    for url in re.findall(r"https?://[^\s)]+", answer):
        if url not in context:
            missing.append("unsupported URL")
    folded = " ".join(strip_accents(answer.lower()).split())
    # Generation has no order/payment tools. Ticket creation is handled by the
    # service after routing; it remains a supported offer, unlike these actions.
    action = (
        r"\b(?:minh|toi|em|chung toi|ben em|ben minh|techcare)\s+(?:da|se|co the)\s+"
        r"(?:(?:giup|ho tro|ban|anh|chi)\s+){0,4}"
        r"(?:dat (?:hang|don)|huy don|thanh toan|hoan tien|kich hoat|cap nhat dia chi|"
        r"xac nhan (?:yeu cau|thanh toan|don hang))\b"
    )
    if re.search(action, folded):
        missing.append("unsupported order/payment action")
    if re.search(r"\bhe thong\s+se\s+(?:tu dong\s+)?tinh\s+phi\s+(?:giao hang|van chuyen)\b", folded):
        missing.append("unsupported automatic shipping calculation")
    if re.search(r"\bdat truoc\b.{0,60}\bde dam bao\s+(?:so huu|co hang|giu hang)\b", folded):
        missing.append("unsupported preorder guarantee")
    return missing
