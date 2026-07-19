from typing import Protocol

from app.rag.guardrails import GuardrailPolicy
from app.rag.query_rewriter import QueryRewriter, strip_accents
from app.rag.vector_store import Document, SearchResult


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
        return self.vector_store.get_all_documents()

    def search(self, question: str, top_k: int) -> list[SearchResult]:
        retrieval_question = self.query_rewriter.expand_for_retrieval(question)
        raw_hits = self.vector_store.search(retrieval_question, max(top_k * 4, top_k))
        adjusted = [
            SearchResult(
                score=hit.score + self.score_adjustment(question, hit.document),
                document=hit.document,
            )
            for hit in raw_hits
        ]
        adjusted.sort(key=lambda item: item.score, reverse=True)
        return adjusted[:top_k]

    def direct_source_hits(
        self, question: str, default_hits: list[SearchResult] | None = None
    ) -> list[SearchResult]:
        documents = self.vector_store.get_all_documents()
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

        for token in question_lower.replace("?", " ").replace(",", " ").split():
            if len(token) >= 5 and token in title_lower:
                adjustment += 0.03

        return adjustment

    @staticmethod
    def context_from_hits(hits: list[SearchResult]) -> str:
        return "\n\n---\n\n".join(hit.document.content for hit in hits)
