"""Website-only technical evidence admission; frozen benchmark P is unchanged."""
import re
import time

from app.config import settings as app_settings
from app.rag.chat_service import ChatService, ChatResult, create_default_chat_service
from app.rag.grounding import unsupported_claims
from app.rag.guardrails import GuardrailPolicy
from app.rag.lexical import bm25_search
from app.rag.prompt import FALLBACK_ANSWER
from app.rag.query_rewriter import strip_accents
from app.rag.vector_store import Document
from app.website_transport import WebsiteOllamaClient, emit


TECHNICAL_FALLBACK = (
    "Mình chưa có tài liệu kỹ thuật đủ liên quan để giải thích nội dung này trong dữ liệu hiện tại. "
    "Mình có thể tạo ticket để nhân viên TechCare kiểm tra và tư vấn chính xác hơn cho bạn."
)


def folded(text):
    return " ".join(re.findall(r"[a-z0-9]+", strip_accents(text.lower())))


def contains(text, phrase):
    return f" {phrase} " in f" {folded(text)} "


def technical_intent(question):
    text = folded(question)
    features = any(x in text for x in ("dac diem", "cau hinh", "tieu chi"))
    explanation = features or any(x in text for x in (
        "nghia la", "la gi", "giai thich", "khac nhau", "khac gi", "nguyen ly", "co che", "hoat dong", "khai niem",
    ))
    if not explanation:
        return None
    # These are topic labels, not canned answers. Each must be supported by
    # admitted documents. Compound identifiers cannot be reduced to just RAM.
    topics = [p for p in ("laptop do hoa", "laptop lap trinh", "laptop gaming", "laptop van phong",
                          "dien thoai chup anh", "dien thoai choi game") if contains(text, p)]
    identifiers = [p for p in ("ram", "ssd", "cpu", "gpu", "nvme", "oled", "ips", "ddr4", "ddr5", "pcie", "thunderbolt",
                              "vram", "dual channel", "single channel", "tan so quet", "bo nho")
                   if contains(text, p)]
    compounds = [folded(p) for p in re.findall(r"\b[a-z0-9]+(?:-[a-z0-9]+)+\b", strip_accents(question.lower()))]
    groups = list(dict.fromkeys(topics + compounds + identifiers))
    if not groups:
        return None
    if any(contains(text, p) for p in ("gia", "ton kho", "con hang", "bao hanh", "bao nhieu tien", "ngan sach", "dat mua", "price", "warranty")):
        return None
    return {"kind": "features" if features else "definition", "groups": groups}


def evidence_for(intent, document, limit=3000):
    if document.metadata.get("source") in {"product_catalog_extended.md", "conversation_history"}:
        return []
    # Match only text that can actually reach the prompt, using the same
    # injection-line filtering and per-document limit as context_from_hits.
    content = "\n".join(line for line in document.content.splitlines()
                        if not GuardrailPolicy.is_prompt_injection(line))[:limit]
    text = document.title + "\n" + content
    groups = [group for group in intent["groups"] if contains(text, group)]
    if not groups:
        return []
    if intent["kind"] == "definition":
        # A definition elsewhere in the chunk must not license every listed
        # spec. Require an explanatory statement about each admitted anchor.
        statements = [folded(line) for line in re.split(r"[\n.!;]+", content)
                      if "?" not in line and not folded(line).startswith("cau hoi")]
        groups = [group for group in groups if any(
            re.search(r"\b" + re.escape(group) + r"\s+(?:\w+\s+){0,4}(?:la|nghia la|duoc hieu|hoat dong)\b", line)
            for line in statements)]
    return groups


def admit_technical(intent, ranked, top_k):
    admitted, covered = [], set()
    ranked = [h for h in ranked if h.score >= .38]
    # Cover each topic before adding any second document about the same one;
    # comparisons may require multiple different documents, never one hard type.
    for group in intent["groups"]:
        match = next((h for h in ranked if group in evidence_for(intent, h.document)), None)
        if match is None:
            return []
        if match.document.id not in {h.document.id for h in admitted}:
            admitted.append(match)
        covered.update(evidence_for(intent, match.document))
    if len(admitted) > top_k or not covered.issuperset(intent["groups"]):
        return []
    return admitted


class WebsiteChatService(ChatService):
    observer = None

    def ask(self, question, top_k=4, history=None, product_id=None, session_id=None, extra_documents=None):
        question = question.strip()
        if not question:
            raise ValueError("Question must not be empty")
        started = time.perf_counter()
        with self.guardrails.product_catalog.snapshot():
            intent = technical_intent(question)
            preempt = (self.guardrails.is_prompt_injection(question) or self.guardrails.is_unrelated_request(question)
                       or self.guardrails.is_support_issue(question) or self.guardrails.is_order_lookup(question)
                       or self.guardrails.is_human_request(question) or self.guardrails.is_clearly_out_of_scope(question))
            if not intent or preempt or self.guardrails.mentioned_products(question) or product_id:
                emit("website_route", route="existing_business", preprocessing_ms=(time.perf_counter() - started) * 1000)
                return super()._ask(question, top_k, history, product_id, session_id, extra_documents)
            emit("website_route", route="technical_evidence", intent=intent,
                 preprocessing_ms=(time.perf_counter() - started) * 1000)
            search_start = time.perf_counter()
            # Keep the existing semantic/BM25 ranks available for diagnosis;
            # admission is additional and only used by this website route.
            ranked = self.retriever.search(question, top_k=max(20, top_k))
            # Do not lose a precise technical source outside semantic top-k.
            lexical = bm25_search(question, self.retriever.all_documents(), max(20, top_k))
            candidates = list(ranked)
            known = {h.document.id for h in candidates}
            candidates.extend(h for h in lexical if h.document.id not in known)
            hits = admit_technical(intent, candidates, top_k)
            emit("technical_admission", groups=intent["groups"],
                 candidates=[{"id":h.document.id,"title":h.document.title,"score":h.score,
                              "source":h.document.metadata.get("source"),"supported_groups":evidence_for(intent,h.document)} for h in candidates],
                 selected=[h.document.id for h in hits], retrieval_ms=(time.perf_counter() - search_start) * 1000)
            if not hits:
                emit("technical_context", text="", reason="no_supported_technical_evidence")
                return ChatResult(TECHNICAL_FALLBACK, [], True, "fallback")
            context_start = time.perf_counter()
            # Rank score alone never admits a document. Only covered evidence
            # reaches the prompt; no unrelated top-k padding or active SKU.
            context = self.retriever.context_from_hits(hits)
            retained = evidence_for(intent, Document("technical-context", "", context), limit=10000)
            if not set(intent["groups"]).issubset(retained):
                emit("technical_context", text="", reason="evidence_lost_after_context_limits")
                return ChatResult(TECHNICAL_FALLBACK, [], True, "fallback")
            system = self.prompt_builder.prompt_path.read_text(encoding="utf-8")
            user = f"NGỮ CẢNH KỸ THUẬT:\n{context}\n\nCÂU HỎI:\n{question}\n\nTrả lời trực tiếp theo tài liệu, không gán câu hỏi khái niệm cho một mẫu sản phẩm."
            emit("technical_context", text=context, system_prompt=system, user_prompt=user,
                 construction_ms=(time.perf_counter() - context_start) * 1000)
            # Transport errors propagate to AIService's existing unavailable
            # response, so a service outage is not described as missing data.
            answer = self.llm_client.chat(system, user)
            if not answer.strip() or unsupported_claims(answer, context):
                emit("technical_postcheck", blocked=True)
                return ChatResult(FALLBACK_ANSWER, hits, True, "fallback")
            emit("technical_postcheck", blocked=False)
            return ChatResult(answer, hits, self.guardrails.needs_human(answer, "llm+rag"), "llm+rag")


def create_website_chat_service(config=None, ensure_index=True):
    config = config or app_settings
    existing = create_default_chat_service(config, ensure_index)
    # Explicit HF/7B deployments keep their existing verified provider. This
    # patch neither changes nor substitutes the supplementary research model.
    if config.CHAT_PROVIDER != "ollama":
        return existing
    client = WebsiteOllamaClient(config.ollama_base_url, config.chat_model, config.embedding_model,
                                 max(1, config.ai_response_timeout_seconds - 9))
    existing.retriever.vector_store.embedding_client = client
    return WebsiteChatService(existing.retriever, existing.prompt_builder, client, existing.guardrails)
