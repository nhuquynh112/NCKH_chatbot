from dataclasses import dataclass
import logging

from app.config import Settings, settings as app_settings
from app.rag.chroma_store import ChromaVectorStore
from app.rag.embedding import OllamaClient
from app.rag.guardrails import GuardrailPolicy, ProductCatalog
from app.rag.prompt import FALLBACK_ANSWER, PromptBuilder
from app.rag.query_rewriter import QueryRewriter
from app.rag.retriever import Retriever
from app.rag.vector_store import (
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

    def ask(self, question: str, top_k: int = 4, product_id: int | None = None,
    session_id: str | None = None,) -> ChatResult:
        question = question.strip()
        if not question:
            raise ValueError("Question must not be empty")

        direct_answer = self.guardrails.deterministic_answer(question)
        if direct_answer:
            hits = self.retriever.direct_source_hits(question, [])
            logger.info("Answered question with deterministic guardrail")
            return ChatResult(
                answer=direct_answer,
                sources=hits,
                needs_human=self.guardrails.needs_human(direct_answer, "rule+rag"),
                mode="rule+rag",
            )

        hits = self.retriever.search(question, top_k=top_k)
        if self.guardrails.should_fallback(question, hits):
            logger.info("Answered question with fallback")
            return ChatResult(
                answer=FALLBACK_ANSWER,
                sources=hits,
                needs_human=True,
                mode="fallback",
            )

        context = self.retriever.context_from_hits(hits)
        answer = self.llm_client.chat(
            self.prompt_builder.system_prompt(),
            self.prompt_builder.user_prompt(question, context),
        )
        logger.info("Answered question with LLM + RAG")
        return ChatResult(
            answer=answer,
            sources=hits,
            needs_human=self.guardrails.needs_human(answer, "llm+rag"),
            mode="llm+rag",
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
