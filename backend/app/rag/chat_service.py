from dataclasses import dataclass
import logging
import re

from app.config import Settings, settings as app_settings
from app.rag.chroma_store import ChromaVectorStore
from app.rag.embedding import OllamaClient
from app.rag.guardrails import GuardrailPolicy, ProductCatalog
from app.rag.json_store import JsonVectorStore
from app.rag.prompt import FALLBACK_ANSWER, PromptBuilder
from app.rag.query_rewriter import QueryRewriter, strip_accents
from app.rag.retriever import Retriever
from app.rag.vector_store import (
    Document,
    SearchResult,
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
        extra_documents: list[dict] | None = None,
    ) -> ChatResult:
        question = question.strip()
        if not question:
            raise ValueError("Question must not be empty")

        recent_history = self.prompt_builder.recent_history(
            history,
            current_question=question,
        )
        recommendation_candidates = self._recommendation_candidates_from_history(
            recent_history
        )
        shown_recommendations = self._all_recommendation_candidates_from_history(
            recent_history
        )
        recommendation_refinement = (
            len(recommendation_candidates) >= 2
            and self.guardrails.is_recommendation_refinement(question)
        )
        alternative_request = (
            bool(shown_recommendations)
            and self.guardrails.is_alternative_request(question)
        )
        current_category = self.guardrails.find_category(question)
        history_category = self._latest_category_from_history(recent_history)
        budget_category_refinement = (
            self.guardrails.extract_budget(question) is not None
            and current_category is None
            and history_category is not None
        )
        explicit_category_query = (
            current_category is not None
            and (
                self.guardrails.is_category_availability_question(question)
                or self.guardrails.is_recommendation_question(question)
                or self.guardrails.extract_budget(question) is not None
            )
        )
        use_history_for_retrieval = (
            bool(recent_history)
            and (
                self.prompt_builder.is_context_dependent(question)
                or recommendation_refinement
                or budget_category_refinement
            )
        )
        # A product named in the current message must always beat page/history
        # context. Conversely, an explicit unknown model must not be silently
        # rewritten to the product page the customer opened earlier.
        current_products = self.guardrails.mentioned_products(question)
        explicit_unknown_product = (
            self.guardrails.is_unknown_product_availability_question(question)
            or self.guardrails.looks_like_unknown_model(question)
            or (
                self.guardrails.has_availability_phrase(question)
                and self.guardrails.is_clearly_out_of_scope(question)
            )
        )
        if current_products:
            resolved_product = current_products[0]
        elif explicit_unknown_product:
            resolved_product = None
        elif (
            recommendation_refinement
            or budget_category_refinement
            or explicit_category_query
        ):
            # A refinement such as "máy mạnh", "chơi mượt và pin trâu"
            # applies to the recommendation set, not the last product printed.
            resolved_product = None
        else:
            resolved_product = self._resolve_product_from_history(
                question,
                recent_history,
                product_id,
            )
        retrieval_question = (
            self._question_with_resolved_product(question, resolved_product)
            if resolved_product
            else self.prompt_builder.question_for_retrieval(question, recent_history)
        )
        # An explicit category in the current turn (e.g. "điện thoại dưới
        # 10tr") must not inherit a product name from old assistant messages.
        guardrail_question = (
            retrieval_question
            if use_history_for_retrieval and not explicit_category_query
            else question
        )

        if alternative_request:
            direct_answer = self.guardrails.recommendation_answer(
                guardrail_question,
                current_question=question,
                excluded=shown_recommendations,
                alternative=True,
            )
        elif recommendation_refinement:
            direct_answer = self.guardrails.recommendation_answer(
                guardrail_question,
                candidates=recommendation_candidates,
                current_question=question,
            )
        elif budget_category_refinement:
            direct_answer = self.guardrails.recommendation_answer(
                f"{question}\nDanh mục đang tư vấn: {history_category}",
                current_question=question,
            )
        else:
            direct_answer = (
                self.guardrails.product_fact_answer(question, resolved_product)
                if resolved_product
                else None
            )
        if not direct_answer:
            direct_answer = self.guardrails.deterministic_answer(guardrail_question)
        if direct_answer:
            hide_sources = (
                "https://www.google.com/" in direct_answer
                or self.guardrails.is_greeting(question)
                or self.guardrails.is_prompt_injection(question)
                or self.guardrails.is_unrelated_request(question)
                or self.guardrails.is_too_vague_for_rag(question)
                or self.guardrails.is_order_lookup(question)
                or self.guardrails.is_support_issue(question)
            )
            hits = (
                []
                if hide_sources
                else self.retriever.direct_source_hits(guardrail_question, [])
            )
            if recommendation_refinement or alternative_request:
                source_candidates = (
                    self.guardrails.mentioned_products(direct_answer)
                    if alternative_request
                    else recommendation_candidates
                )
                candidate_hits = [
                    self._product_search_result(product)
                    for product in source_candidates
                ]
                deduplicated_hits: list[SearchResult] = []
                seen_document_ids: set[str] = set()
                for hit in [*candidate_hits, *hits]:
                    if hit.document.id in seen_document_ids:
                        continue
                    seen_document_ids.add(hit.document.id)
                    deduplicated_hits.append(hit)
                hits = deduplicated_hits
            source_product = resolved_product or self.guardrails.mentioned_known_product(
                guardrail_question
            )
            if source_product:
                hits = [*self._verified_source_hits(source_product), *hits]
            logger.info("Answered question with deterministic guardrail")
            return ChatResult(
                answer=direct_answer,
                sources=hits,
                needs_human=self.guardrails.needs_human(direct_answer, "rule+rag"),
                mode="rule+rag",
            )

        search_question = retrieval_question if use_history_for_retrieval else question
        hits = self.retriever.search(search_question, top_k=top_k)
        if extra_documents:
            extra_hits = [
                SearchResult(
                    score=float(item.get("score", 1.0)),
                    document=Document(
                        id=str(item["id"]),
                        title=str(item["title"]),
                        content=str(item["content"]),
                        metadata={
                            str(key): str(value)
                            for key, value in (item.get("metadata") or {}).items()
                        },
                    ),
                )
                for item in extra_documents
            ]
            hits = sorted([*extra_hits, *hits], key=lambda hit: hit.score, reverse=True)[:top_k]
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

    def _verified_source_hits(self, product: dict) -> list[SearchResult]:
        hits: list[SearchResult] = []
        for index, source in enumerate(product.get("source_urls") or [], start=1):
            title = str(source.get("title") or "").strip()
            url = str(source.get("url") or "").strip()
            if not title or not url:
                continue
            hits.append(
                SearchResult(
                    score=1.0,
                    document=Document(
                        id=f"official-{product.get('slug') or product.get('sku')}-{index}",
                        title=title,
                        content=f"Nguồn hãng cho {product.get('name', '')}",
                        metadata={
                            "source": "official_manufacturer",
                            "url": url,
                            "verified_at": str(product.get("verified_at") or ""),
                        },
                    ),
                )
            )
        return hits

    def _resolve_product_from_history(
        self,
        question: str,
        history: list[dict[str, str]],
        product_id: int | None = None,
    ) -> dict | None:
        page_product = self.guardrails.product_by_id(product_id)
        if page_product:
            return page_product

        if not history or not self.prompt_builder.is_context_dependent(question):
            return None

        return (
            self._latest_product_by_role(history, "assistant")
            or self._latest_product_by_role(history, "user")
            or self._latest_product_in_messages(history)
        )

    def _recommendation_candidates_from_history(
        self,
        history: list[dict[str, str]],
    ) -> list[dict]:
        """Return the latest multi-product recommendation shown to the user."""
        for message in reversed(history):
            if message.get("role") != "assistant":
                continue
            products = self.guardrails.mentioned_products(message.get("content", ""))
            if len(products) >= 2:
                return products
        return []

    def _all_recommendation_candidates_from_history(
        self,
        history: list[dict[str, str]],
    ) -> list[dict]:
        """Collect every product recently shown so alternatives do not repeat."""
        products: list[dict] = []
        seen: set[str] = set()
        for message in reversed(history):
            if message.get("role") != "assistant":
                continue
            for product in self.guardrails.mentioned_products(message.get("content", "")):
                key = self._compact_text(product.get("sku") or product.get("name", ""))
                if not key or key in seen:
                    continue
                seen.add(key)
                products.append(product)
        return products

    def _latest_category_from_history(
        self,
        history: list[dict[str, str]],
    ) -> str | None:
        for role in ("user", "assistant"):
            for message in reversed(history):
                if message.get("role") != role:
                    continue
                category = self.guardrails.find_category(message.get("content", ""))
                if category:
                    return category
        return None

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
        matches: list[tuple[int, int, dict]] = []
        folded_text = self._fold_text(text)
        compact_text = self._compact_text(text)

        for product in self._known_product_candidates():
            positions: list[tuple[int, int]] = []
            for term in self._product_terms(product):
                folded_term = self._fold_text(term)
                compact_term = self._compact_text(term)
                if len(compact_term) < 4:
                    continue

                folded_index = folded_text.rfind(folded_term)
                if folded_index >= 0:
                    positions.append((folded_index, len(folded_term)))

                compact_index = compact_text.rfind(compact_term)
                if compact_index >= 0:
                    positions.append((compact_index, len(compact_term)))

            if positions:
                best_position, best_length = max(positions, key=lambda item: (item[0], item[1]))
                matches.append((best_position, best_length, product))

        if not matches:
            return None
        # When names overlap ("iPhone 17" and "iPhone 17 Pro"), prefer the
        # longer, more specific term at the latest position.
        matches.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return matches[0][2]

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
        if document.metadata.get("source") != "product_catalog_extended.md":
            return None
        title = document.title.strip()
        if not title:
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
    vector_store = _create_vector_store(config, llm_client)
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
        documents = load_markdown_documents(config.knowledge_paths)
        if not retriever.vector_store.is_current(documents):
            logger.warning("RAG index is missing or stale; rebuilding it from current data")
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

    vector_store = _create_vector_store(config, llm_client)

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


def _create_vector_store(config: Settings, llm_client: OllamaClient):
    if config.vector_store_backend == "json":
        return JsonVectorStore(config.legacy_vector_index_path, llm_client)

    chroma_store = ChromaVectorStore(
        persist_dir=config.chroma_persist_dir,
        collection_name=config.collection_name,
        embedding_client=llm_client,
    )
    if config.vector_store_backend == "chroma":
        return chroma_store

    if chroma_store.is_available():
        return chroma_store
    logger.warning("ChromaDB is unavailable; using the portable JSON vector store")
    return JsonVectorStore(config.legacy_vector_index_path, llm_client)
