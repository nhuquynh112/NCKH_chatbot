from dataclasses import dataclass
import logging
import re

from app.config import Settings, settings as app_settings
from app.rag.chroma_store import ChromaVectorStore
from app.rag.embedding import OllamaClient
from app.rag.guardrails import GuardrailPolicy, ProductCatalog
from app.rag.prompt import FALLBACK_ANSWER, PromptBuilder
from app.rag.query_rewriter import QueryRewriter, strip_accents
from app.rag.retriever import Retriever
from app.rag.vector_store import (
    Document,
    SearchResult,
    load_legacy_vector_index,
    load_markdown_documents,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatResult:
    answer: str
    sources: list[SearchResult]
    needs_human: bool
    mode: str


class ChatService:
    def __init__(
        self,
        retriever: Retriever,
        prompt_builder: PromptBuilder,
        llm_client: OllamaClient,
        guardrails: GuardrailPolicy,
    ):
        self.retriever = retriever
        self.prompt_builder = prompt_builder
        self.llm_client = llm_client
        self.guardrails = guardrails

    def ask(
        self,
        question: str,
        top_k: int = 4,
        history: list[dict] | None = None,
        product_id: int | None = None,
        session_id: str | None = None,
    ) -> ChatResult:
        question = question.strip()
        if not question:
            raise ValueError("Question must not be empty")

        recent_history = self.prompt_builder.recent_history(
            history,
            current_question=question,
        )
        use_history_for_retrieval = (
            bool(recent_history)
            and self.prompt_builder.is_context_dependent(question)
        )
        resolved_product = self._resolve_product_from_history(
            question,
            recent_history,
        )
        retrieval_question = (
            self._question_with_resolved_product(question, resolved_product)
            if resolved_product
            else self.prompt_builder.question_for_retrieval(question, recent_history)
        )
        guardrail_question = retrieval_question if use_history_for_retrieval else question

        direct_answer = self.guardrails.deterministic_answer(guardrail_question)
        if direct_answer:
            hits = self.retriever.direct_source_hits(guardrail_question, [])
            logger.info("Answered question with deterministic guardrail")
            return ChatResult(
                answer=direct_answer,
                sources=hits,
                needs_human=self.guardrails.needs_human(direct_answer, "rule+rag"),
                mode="rule+rag",
            )

        search_question = retrieval_question if use_history_for_retrieval else question
        hits = self.retriever.search(search_question, top_k=top_k)
        if resolved_product:
            hits = self._prioritize_active_product_hits(hits, resolved_product)
        if self.guardrails.should_fallback(search_question, hits):
            logger.info("Answered question with fallback")
            return ChatResult(
                answer=FALLBACK_ANSWER,
                sources=hits,
                needs_human=True,
                mode="fallback",
            )

        context_hits = (
            self._active_product_context_hits(hits, resolved_product)
            if resolved_product
            else hits
        )
        context = self.retriever.context_from_hits(context_hits)
        answer = self.llm_client.chat(
            self.prompt_builder.system_prompt(),
            self.prompt_builder.user_prompt(
                question,
                context,
                recent_history,
                active_product=resolved_product,
            ),
        )
        logger.info("Answered question with LLM + RAG")
        return ChatResult(
            answer=answer,
            sources=hits,
            needs_human=self.guardrails.needs_human(answer, "llm+rag"),
            mode="llm+rag",
        )

    def _resolve_product_from_history(
        self,
        question: str,
        history: list[dict[str, str]],
    ) -> dict | None:
        if not history or not self.prompt_builder.is_context_dependent(question):
            return None

        return (
            self._latest_product_by_role(history, "assistant")
            or self._latest_product_by_role(history, "user")
            or self._latest_product_in_messages(history)
        )

    def _latest_product_by_role(
        self,
        history: list[dict[str, str]],
        role: str,
    ) -> dict | None:
        for message in reversed(history):
            if message.get("role") != role:
                continue
            product = self._latest_product_in_text(message.get("content", ""))
            if product:
                return product
        return None

    def _latest_product_in_messages(
        self,
        history: list[dict[str, str]],
    ) -> dict | None:
        for message in reversed(history):
            product = self._latest_product_in_text(message.get("content", ""))
            if product:
                return product
        return None

    def _latest_product_in_text(self, text: str) -> dict | None:
        matches: list[tuple[int, dict]] = []
        folded_text = self._fold_text(text)
        compact_text = self._compact_text(text)

        for product in self._known_product_candidates():
            positions: list[int] = []
            for term in self._product_terms(product):
                folded_term = self._fold_text(term)
                compact_term = self._compact_text(term)
                if len(compact_term) < 4:
                    continue

                folded_index = folded_text.rfind(folded_term)
                if folded_index >= 0:
                    positions.append(folded_index)

                compact_index = compact_text.rfind(compact_term)
                if compact_index >= 0:
                    positions.append(compact_index)

            if positions:
                matches.append((max(positions), product))

        if not matches:
            return None
        matches.sort(key=lambda item: item[0], reverse=True)
        return matches[0][1]

    def _known_product_candidates(self) -> list[dict]:
        candidates: list[dict] = []
        seen: set[str] = set()

        for product in self.guardrails.product_catalog.load_products():
            self._append_product_candidate(candidates, seen, product)

        for document in self.retriever.all_documents():
            product = self._product_from_document(document)
            if product:
                self._append_product_candidate(candidates, seen, product)

        return candidates

    def _append_product_candidate(
        self,
        candidates: list[dict],
        seen: set[str],
        product: dict,
    ) -> None:
        key = self._compact_text(product.get("sku") or product.get("name", ""))
        if not key or key in seen:
            return
        seen.add(key)
        candidates.append(product)

    def _product_from_document(self, document: Document) -> dict | None:
        title = document.title.strip()
        if not title:
            return None
        if self._fold_text(title) in {"gioi thieu", "cau hoi thuong gap"}:
            return None

        price = self._first_match(
            document.content,
            [
                r"Giá(?: niêm yết| bán)?[:\s]+([0-9.,]+\s*VNĐ?)",
                r"giá\s+([0-9.,]+\s*VNĐ?)",
            ],
        )
        warranty = self._first_match(
            document.content,
            [
                r"Bảo hành[:\s]+([^\n.]+)",
                r"bảo hành(?: chính hãng)?\s+([0-9]+\s+tháng)",
            ],
        )
        category = self._first_match(
            document.content,
            [r"Danh mục[:\s]+([^\n]+)", r"thuộc nhóm\s+([^.\n]+)"],
        )

        return {
            "sku": document.metadata.get("sku") or document.id,
            "name": self._clean_product_title(title),
            "category": category or document.metadata.get("category", ""),
            "price": price or "",
            "warranty": warranty or "",
            "use_case": document.content,
        }

    def _clean_product_title(self, title: str) -> str:
        return re.sub(r"\s+-\s+[A-Z0-9-]+$", "", title).strip()

    def _first_match(self, text: str, patterns: list[str]) -> str:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _product_terms(self, product: dict) -> list[str]:
        name = product.get("name", "")
        sku = product.get("sku", "")
        terms = [name, sku]

        storage_alias = re.sub(r"\s+\d+\s*(gb|tb)\b.*$", "", name, flags=re.IGNORECASE)
        if storage_alias and storage_alias != name:
            terms.append(storage_alias)

        sku_suffix = re.sub(r"\s+-\s+[A-Z0-9-]+$", "", name).strip()
        if sku_suffix and sku_suffix != name:
            terms.append(sku_suffix)

        return [term for term in terms if term]

    def _fold_text(self, text: str) -> str:
        text = text.replace("đ", "d").replace("Đ", "D")
        return strip_accents(text.lower())

    def _compact_text(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", self._fold_text(text))

    def _question_with_resolved_product(self, question: str, product: dict) -> str:
        return (
            f"{question}\n"
            "Sản phẩm được nhắc tới trong lịch sử hội thoại:\n"
            f"{product['name']} ({product['sku']}), "
            f"nhóm {product['category']}, giá {product['price']}.\n"
            f"{product.get('use_case', '')}"
        )

    def _product_context(self, product: dict) -> str:
        return (
            "Sản phẩm được xác định từ lịch sử hội thoại:\n"
            f"- Tên: {product['name']}\n"
            f"- SKU: {product['sku']}\n"
            f"- Nhóm: {product['category']}\n"
            f"- Giá: {product['price']}\n"
            f"- Mô tả/nhu cầu phù hợp: {product.get('use_case', '')}"
        )

    def _prioritize_active_product_hits(
        self,
        hits: list[SearchResult],
        product: dict,
    ) -> list[SearchResult]:
        active_hit = self._product_search_result(product)
        matching_hits: list[SearchResult] = []
        unrelated_hits: list[SearchResult] = []

        for hit in hits:
            if self._hit_matches_product(hit, product):
                matching_hits.append(
                    SearchResult(
                        score=max(hit.score, 0.99),
                        document=hit.document,
                    )
                )
            else:
                unrelated_hits.append(
                    SearchResult(
                        score=min(hit.score, 0.2),
                        document=hit.document,
                    )
                )

        matching_hits.sort(key=lambda item: item.score, reverse=True)
        unrelated_hits.sort(key=lambda item: item.score, reverse=True)
        return [active_hit, *matching_hits, *unrelated_hits]

    def _active_product_context_hits(
        self,
        hits: list[SearchResult],
        product: dict,
    ) -> list[SearchResult]:
        return [
            hit
            for hit in hits
            if hit.document.metadata.get("type") == "resolved_product_reference"
            or self._hit_matches_product(hit, product)
        ]

    def _hit_matches_product(self, hit: SearchResult, product: dict) -> bool:
        text = f"{hit.document.title}\n{hit.document.content}"
        compact_text = self._compact_text(text)
        for term in self._product_terms(product):
            compact_term = self._compact_text(term)
            if len(compact_term) >= 4 and compact_term in compact_text:
                return True
        return False

    def _product_search_result(self, product: dict) -> SearchResult:
        return SearchResult(
            score=1.0,
            document=Document(
                id=product["sku"],
                title=product["name"],
                content=self._product_context(product),
                metadata={
                    "source": "conversation_history",
                    "type": "resolved_product_reference",
                },
            ),
        )


def create_default_chat_service(
    config: Settings | None = None,
    ensure_index: bool = True,
) -> ChatService:
    config = config or app_settings
    llm_client = OllamaClient(
        base_url=config.ollama_base_url,
        chat_model=config.chat_model,
        embedding_model=config.embedding_model,
    )
    vector_store = ChromaVectorStore(
        persist_dir=config.chroma_persist_dir,
        collection_name=config.collection_name,
        embedding_client=llm_client,
    )
    guardrails = GuardrailPolicy(
        product_catalog=ProductCatalog(
            rag_documents_path=config.rag_documents_path,
            products_path=config.products_path,
        ),
        min_retrieval_score=config.min_retrieval_score,
    )
    retriever = Retriever(
        vector_store=vector_store,
        query_rewriter=QueryRewriter(),
        guardrails=guardrails,
    )
    if ensure_index:
        if retriever.vector_store.count() == 0:
            if config.legacy_vector_index_path.exists():
                documents, embeddings_by_id = load_legacy_vector_index(
                    config.legacy_vector_index_path
                )
                retriever.rebuild_index(documents, embeddings_by_id=embeddings_by_id)
            else:
                documents = load_markdown_documents(config.knowledge_paths)
                retriever.rebuild_index(documents)

    return ChatService(
        retriever=retriever,
        prompt_builder=PromptBuilder(config.prompt_path),
        llm_client=llm_client,
        guardrails=guardrails,
    )

def rebuild_index(config: Settings | None = None):

    config = config or app_settings

    llm_client = OllamaClient(
        base_url=config.ollama_base_url,
        chat_model=config.chat_model,
        embedding_model=config.embedding_model,
    )

    vector_store = ChromaVectorStore(
        persist_dir=config.chroma_persist_dir,
        collection_name=config.collection_name,
        embedding_client=llm_client,
    )

    guardrails = GuardrailPolicy(
        product_catalog=ProductCatalog(
            rag_documents_path=config.rag_documents_path,
            products_path=config.products_path,
        ),
        min_retrieval_score=config.min_retrieval_score,
    )

    retriever = Retriever(
        vector_store=vector_store,
        query_rewriter=QueryRewriter(),
        guardrails=guardrails,
    )

    print("Loading documents...")

    documents = load_markdown_documents(config.knowledge_paths)

    retriever.rebuild_index(documents)

    print(f"Indexed {len(documents)} documents successfully.")
