import re
from typing import Protocol

from app.rag.guardrails import GuardrailPolicy
from app.rag.query_rewriter import QueryRewriter, strip_accents
from app.rag.vector_store import Document, SearchResult
from app.rag.embedding import OllamaError
from app.rag.lexical import bm25_search
from app.rag.components import RagComponents
import logging

logger = logging.getLogger(__name__)


class VectorStore(Protocol):
    def build_index(
        self,
        documents: list[Document],
        embeddings_by_id: dict[str, list[float]] | None = None,
    ) -> None:
        ...

    def get_all_documents(self) -> list[Document]:
        ...

    def search(self, query: str, top_k: int) -> list[SearchResult]:
        ...

    def count(self) -> int:
        ...

    def is_current(self, documents: list[Document]) -> bool:
        ...


class Retriever:
    def __init__(
        self,
        vector_store: VectorStore,
        query_rewriter: QueryRewriter,
        guardrails: GuardrailPolicy,
    ):
        self.vector_store = vector_store
        self.query_rewriter = query_rewriter
        self.guardrails = guardrails
        self.source_documents: list[Document] | None = None
        self.semantic_enabled = True
        self.components = RagComponents()
        self.trace_observer = None

    def ensure_index(self, documents: list[Document]) -> None:
        if self.vector_store.count() == 0:
            self.rebuild_index(documents)

    def rebuild_index(
        self,
        documents: list[Document],
        embeddings_by_id: dict[str, list[float]] | None = None,
    ) -> None:
        self.vector_store.build_index(documents, embeddings_by_id=embeddings_by_id)

    def all_documents(self) -> list[Document]:
        return self.source_documents if self.source_documents is not None else self.vector_store.get_all_documents()

    def search(self, question: str, top_k: int) -> list[SearchResult]:
        retrieval_question = (self.query_rewriter.expand_for_retrieval(question)
                              if self.components.query_normalization else question)
        documents = self.all_documents()
        lexical = (bm25_search(question, documents, max(top_k * 4, top_k))
                   if self.components.bm25 else [])
        semantic = []
        if self.semantic_enabled:
            try:
                semantic = self.vector_store.search(retrieval_question, max(top_k * 4, top_k))
            except OllamaError:
                logger.warning("Semantic retrieval unavailable; using current BM25 documents")
        semantic_scores = {hit.document.id:hit.score for hit in semantic}
        lexical_scores = {hit.document.id:hit.score / (hit.score + 3.0) for hit in lexical}
        candidates = {hit.document.id:hit.document for hit in [*semantic, *lexical]}
        raw_hits = [SearchResult(
            score=.60 * max(0., semantic_scores.get(key, 0.)) + .40 * lexical_scores.get(key, 0.),
            document=document,
        ) for key, document in candidates.items()]
        adjustments = {hit.document.id: self.score_adjustment(question, hit.document)
                       if self.components.domain_ranking else 0.0 for hit in raw_hits}
        adjusted = [
            SearchResult(
                score=max(0.0, min(1.0, hit.score + adjustments[hit.document.id])),
                document=hit.document,
            )
            for hit in raw_hits
        ]
        adjusted.sort(key=lambda item: item.score, reverse=True)
        if self.trace_observer:
            self.trace_observer({"question": question, "semantic_query": retrieval_question,
                "semantic_enabled": self.semantic_enabled,
                "bm25_enabled": self.components.bm25,
                "domain_ranking_enabled": self.components.domain_ranking,
                "candidates": [{"id": hit.document.id, "title": hit.document.title,
                    "metadata": hit.document.metadata, "content": hit.document.content,
                    "vector_score": semantic_scores.get(hit.document.id),
                    "bm25_score": next((x.score for x in lexical if x.document.id == hit.document.id), None),
                    "hybrid_score": next(x.score for x in raw_hits if x.document.id == hit.document.id),
                    "domain_adjustment": adjustments[hit.document.id], "final_score": hit.score}
                    for hit in adjusted], "selected_ids": [h.document.id for h in adjusted[:top_k]]})
        return adjusted[:top_k]

    def direct_source_hits(
        self, question: str, default_hits: list[SearchResult] | None = None
    ) -> list[SearchResult]:
        documents = self.all_documents()
        default_hits = default_hits or []

        if self.guardrails.is_support_issue(question):
            hits = [
                SearchResult(1.0, doc)
                for doc in documents
                if any(
                    keyword in doc.title.lower()
                    for keyword in [
                        "quy trình tạo ticket",
                        "chính sách bảo hành",
                        "chính sách đổi trả",
                    ]
                )
            ]
            if hits:
                return hits[:4]

        if self.guardrails.is_order_lookup(question):
            hits = [
                SearchResult(1.0, doc)
                for doc in documents
                if any(
                    keyword in strip_accents(doc.title.lower())
                    for keyword in ["kiem tra don hang", "quy trinh tao ticket"]
                )
            ]
            if hits:
                return hits[:4]

        known_product = self.guardrails.mentioned_known_product(question)
        if known_product:
            name = re.sub(
                r"[^a-z0-9]+", "", strip_accents(known_product["name"].lower())
            )
            hits = [
                SearchResult(1.0, doc)
                for doc in documents
                if name in re.sub(
                    r"[^a-z0-9]+", "", strip_accents(doc.title.lower())
                )
                or re.sub(
                    r"[^a-z0-9]+", "", strip_accents(doc.title.lower())
                ) in name
            ]
            if hits:
                return hits[:1]

        if self.guardrails.is_greeting(question) or self.guardrails.is_too_vague_for_rag(question):
            return [
                SearchResult(1.0, doc)
                for doc in documents
                if any(
                    keyword in doc.title.lower()
                    for keyword in ["hồ sơ doanh nghiệp", "techcare electronics"]
                )
            ][:1]

        if self.guardrails.is_unknown_product_availability_question(question):
            hits = [
                SearchResult(1.0, doc)
                for doc in documents
                if any(keyword in doc.title.lower() for keyword in ["quy trình tạo ticket", "catalog"])
            ]
            if hits:
                return hits[:4]

        category = self.guardrails.find_category(question)
        if category:
            category_folded = strip_accents(category.lower())
            hits = [
                SearchResult(1.0, doc)
                for doc in documents
                if category_folded in strip_accents(doc.title.lower())
                or f"nhom {category_folded}" in strip_accents(doc.content.lower())
                or f"nhóm {category}" in doc.content.lower()
            ]
            if hits:
                return hits[:4]

        answer = self.guardrails.deterministic_answer(question)
        if answer:
            answer_folded = strip_accents(answer.lower())
            hits = [
                SearchResult(1.0, doc)
                for doc in documents
                if strip_accents(doc.title.lower()) in answer_folded
            ]
            if hits:
                return hits[:4]

        return default_hits

    def score_adjustment(self, question: str, document: Document) -> float:
        question_lower = question.lower()
        title_lower = document.title.lower()
        content_lower = document.content.lower()
        text = title_lower + " " + content_lower
        adjustment = 0.0

        # Small multilingual embedding models can confuse nearby policies (for
        # example refund vs warranty). Exact lexical overlap keeps the matching
        # FAQ/section title ahead of merely semantically similar documents.
        folded_question = strip_accents(question_lower)
        if "bao lau" in folded_question:
            folded_question += " thoi gian"
        folded_title = strip_accents(title_lower)
        folded_content = strip_accents(content_lower)
        stop_words = {
            "cua", "cho", "toi", "minh", "ban", "shop", "techcare", "la",
            "co", "khong", "duoc", "nhung", "nao", "gi", "ve", "the",
        }
        query_tokens = {
            token
            for token in folded_question.replace("?", " ").replace(",", " ").split()
            if len(token) >= 2 and token not in stop_words
        }
        if query_tokens:
            title_overlap = sum(token in folded_title for token in query_tokens)
            content_overlap = sum(token in folded_content for token in query_tokens)
            adjustment += 0.45 * title_overlap / len(query_tokens)
            adjustment += 0.12 * content_overlap / len(query_tokens)

        topics = [
            "hoan tien", "bao hanh", "doi tra", "giao hang", "phi giao hang",
            "thanh toan", "tra gop", "hoa don", "voucher", "kiem tra hang",
            "huy don hang",
        ]
        for topic in (item for item in topics if item in folded_question):
            if topic in folded_title:
                adjustment += 0.45
            elif topic in folded_content:
                adjustment += 0.20

        recommendation_words = [
            "chơi game", "gaming", "render", "đồ họa", "do hoa",
            "học online", "hoc online", "sinh viên", "sinh vien",
            "văn phòng", "van phong", "tư vấn", "tu van",
            "phù hợp", "phu hop",
        ]
        policy_words = [
            "bảo hành", "bao hanh", "đổi trả", "doi tra",
            "giao hàng", "giao hang", "thanh toán", "thanh toan",
            "ticket", "đơn", "don",
        ]

        if any(word in question_lower for word in recommendation_words):
            if any(word in text for word in ["game", "gaming", "render", "đồ họa", "do hoa", "rtx", "gpu", "tư vấn", "tu van", "phù hợp", "phu hop"]):
                adjustment += 0.12
            if any(word in title_lower for word in ["chính sách", "lưu ý", "ticket", "bảo hành", "đổi trả", "giao hàng", "thanh toán"]):
                adjustment -= 0.14

        asks_game_laptop = any(
            word in question_lower
            for word in ["máy nào", "may nao", "laptop nào", "laptop nao"]
        ) and any(
            word in question_lower
            for word in ["chơi game", "choi game", "gaming", "game ngon"]
        )
        if asks_game_laptop:
            if any(word in text for word in ["laptop", "gpu", "rtx", "gamepro", "creatorbook"]):
                adjustment += 0.35
            if any(word in title_lower for word in ["chính sách", "lưu ý", "ticket", "giao hàng", "thanh toán", "đổi trả", "bảo hành"]):
                adjustment -= 0.35
            if any(word in text for word in ["chuột", "chuot", "bàn phím", "ban phim", "tai nghe"]):
                adjustment -= 0.18

        if any(word in question_lower for word in policy_words):
            if any(word in title_lower for word in ["chính sách", "giao hàng", "thanh toán", "ticket", "trạng thái", "đơn hàng"]):
                adjustment += 0.10

        for token in folded_question.replace("?", " ").replace(",", " ").split():
            if len(token) >= 5 and token in folded_title:
                adjustment += 0.03

        return adjustment

    @staticmethod
    def context_from_hits(hits: list[SearchResult]) -> str:
        # Bound prompt size and discard weak tail hits. Metadata remains
        # outside generation, so a model cannot forge the source panel.
        blocks = []
        remaining = 10000
        for hit in hits:
            if hit.score < .38 or remaining <= 0:
                continue
            content = "\n".join(line for line in hit.document.content.splitlines()
                                if not GuardrailPolicy.is_prompt_injection(line))
            block = f"Tài liệu: {hit.document.title}\n{content[:3000]}"
            blocks.append(block[:remaining])
            remaining -= len(block) + 9
        return "\n\n---\n\n".join(blocks)
