"""Explicit method boundaries. Importing M2 does not import any RAG service/data."""
import json
from pathlib import Path
import time
import urllib.request

from app.config import Settings, BASELINE_CHAT_MODEL
from app.rag.embedding import OllamaClient
from app.rag.components import RagComponents
from benchmark.protocol import method_spec

ROOT = Path(__file__).resolve().parents[1]
GENERATION = {"temperature": 0, "num_predict": 384, "num_ctx": 4096, "repeat_penalty": 1.0}


def method_settings(method, timeout, corpus, ollama_url, hf_url):
    config = Settings(_env_file=None, ENVIRONMENT="test", CHAT_PROVIDER=method_spec(method)["provider"],
                      CHAT_MODEL=BASELINE_CHAT_MODEL, USE_PROJECT_CHAT_MODEL=False,
                      OLLAMA_BASE_URL=ollama_url, HF_LORA_BASE_URL=hf_url,
                      AI_RESPONSE_TIMEOUT_SECONDS=timeout + 9, WARM_AI_ON_STARTUP=False,
                      VECTOR_STORE_BACKEND="json", EMBEDDING_MODEL="nomic-embed-text",
                      RAG_TOP_K=5, MIN_RETRIEVAL_SCORE=0.38,
                      KNOWLEDGE_BASE_PATH=corpus / "knowledge_base.md",
                      PRODUCT_CATALOG_PATH=corpus / "product_catalog_extended.md",
                      CURATED_FAQ_PATH=corpus / "faq_curated.json",
                      PRODUCTS_PATH=corpus / "techcare_products.json",
                      RAG_DOCUMENTS_PATH=corpus / "techcare_rag_documents.json",
                      LEGACY_VECTOR_INDEX_PATH=corpus / "vector_index.json",
                      PROMPT_PATH=corpus / "system_prompt.txt")
    return config


def ollama_identity(client, embeddings=False):
    with urllib.request.urlopen(client.base_url + "/api/tags", timeout=3) as response:
        tags = json.load(response)["models"]
    by_name = {m["name"]:m for m in tags}
    if client.chat_model not in by_name:
        raise RuntimeError(f"Requested model is not installed: {client.chat_model}")
    if embeddings and not any(n.split(":")[0] == client.embedding_model for n in by_name):
        raise RuntimeError("Embedding model is not installed")
    model = by_name[client.chat_model]
    identity = {"model": model["name"], "digest": model.get("digest"), "details":model.get("details")}
    if embeddings:
        embedding = next(m for n,m in by_name.items() if n.split(":")[0] == client.embedding_model)
        identity["embedding_identity"] = {k:embedding.get(k) for k in ("name","digest","details")}
    return identity


class TracedClient:
    def __init__(self, client):
        self.client = client
        self.calls = []
        self.retrieval_errors = []

    def __getattr__(self, name):
        return getattr(self.client, name)

    def chat(self, system_prompt, user_prompt):
        call = {"model": self.client.chat_model, "system_prompt":system_prompt,
                "user_prompt":user_prompt, "generation":GENERATION.copy(), "error":None}
        started = time.perf_counter()
        self.calls.append(call)
        try:
            call["answer"] = self.client.chat(system_prompt, user_prompt)
            call["generation_evidence"] = getattr(self.client, "last_generation_metadata", None)
            return call["answer"]
        except Exception as exc:
            call["error"] = {"type":type(exc).__name__,"message":str(exc)}
            raise
        finally:
            call["latency_ms"] = (time.perf_counter()-started)*1000

    def embed_query(self, text):
        try:
            return self.client.embed_query(text)
        except Exception as exc:
            self.retrieval_errors.append({"type":type(exc).__name__, "message":str(exc)})
            raise


class PlainLlmMethod:
    def __init__(self, config, prompt):
        self.config = config
        self.client = TracedClient(OllamaClient(config.ollama_base_url, BASELINE_CHAT_MODEL,
                                              config.embedding_model, config.ai_response_timeout_seconds-9))
        self.prompt = prompt

    def preflight(self):
        return ollama_identity(self.client.client)  # Never requires or calls embedding/RAG.

    def ask(self, question, history):
        user = "\n".join(f"{m['role']}: {m['content']}" for m in history)
        user = (user + "\n\n" if user else "") + question
        return {"answer":self.client.chat(self.prompt, user), "sources":[], "mode":"llm_without_rag"}


class RuleMethod:
    def __init__(self, config, curated_faq_rules=False):
        from app.rag.guardrails import GuardrailPolicy, ProductCatalog
        self.policy = GuardrailPolicy(ProductCatalog(config.rag_documents_path, config.products_path), config.min_retrieval_score)
        self.client = None
        self.curated_faq_rules = curated_faq_rules

    def preflight(self):
        return {"model":None, "rules":"app.rag.guardrails.GuardrailPolicy.deterministic_answer",
                "curated_faq_rules": self.curated_faq_rules}

    def ask(self, question, history):
        with self.policy.product_catalog.snapshot():
            answer = self.policy.deterministic_answer(question)
        if not answer and self.curated_faq_rules:
            from app.rag.faq_matcher import match_curated_faqs
            faqs = match_curated_faqs(question)
            if faqs:
                return {"answer":"\n\n".join(f["answer"] for f in faqs), "mode":"faq_rule",
                        "sources":[{"id":"curated-"+f["id"], "title":f["question"], "score":1.0,
                                    "content":f["answer"], "metadata":{"source":"faq_curated.json"}} for f in faqs]}
        return {"answer":answer or "Không có quy tắc phù hợp; cần nhân viên hỗ trợ.",
                "sources":[], "mode":"rule" if answer else "no_rule_match"}


class RagMethod:
    def __init__(self, config, components=None):
        from app.rag.chat_service import create_default_chat_service
        self.config = config
        self.chatbot = create_default_chat_service(config)
        self.chatbot.components = components or RagComponents()
        self.chatbot.retriever.components = self.chatbot.components
        self.retrieval_traces = []
        self.architecture_traces = []
        self.chatbot.retriever.trace_observer = self.retrieval_traces.append
        self.chatbot.trace_observer = self.architecture_traces.append
        self.client = TracedClient(self.chatbot.llm_client)
        self.chatbot.llm_client = self.client
        self.chatbot.retriever.vector_store.embedding_client = self.client

    def preflight(self):
        if self.config.CHAT_PROVIDER == "hf_lora":
            identity = self.client.identity()
            embeddings = OllamaClient(self.config.ollama_base_url, "nomic-embed-text:latest", "nomic-embed-text")
            identity = {**identity, "embedding_identity":ollama_identity(embeddings)}
        else:
            identity = ollama_identity(self.client.client, embeddings=True)
        return {**identity, "semantic_enabled":self.chatbot.retriever.semantic_enabled,
                "documents":len(self.chatbot.retriever.all_documents()),
                "top_k":self.config.RAG_TOP_K,"min_retrieval_score":self.config.MIN_RETRIEVAL_SCORE,
                "vector_store":self.config.vector_store_backend, "embedding_model":self.config.embedding_model}

    def ask(self, question, history):
        result = self.chatbot.ask(question, self.config.RAG_TOP_K, history)
        return {"answer":result.answer, "mode":result.mode,"needs_human":result.needs_human,
                "sources":[{"id":s.document.id,"title":s.document.title,"score":s.score,
                            "content":s.document.content, "metadata":s.document.metadata} for s in result.sources]}


class BasicRagMethod:
    """B2: raw semantic retrieval + shared PromptBuilder + LLM, without P routing or checks."""
    def __init__(self, config):
        from app.rag.json_store import JsonVectorStore
        from app.rag.prompt import PromptBuilder
        from app.rag.vector_store import load_markdown_documents
        self.config = config
        self.client = TracedClient(OllamaClient(config.ollama_base_url, BASELINE_CHAT_MODEL,
                                               config.embedding_model, config.ai_response_timeout_seconds-9))
        self.store = JsonVectorStore(config.legacy_vector_index_path, self.client)
        self.documents = load_markdown_documents(config.knowledge_paths)
        self.prompt_builder = PromptBuilder(config.prompt_path)
        self.retrieval_traces = []
        self.architecture_traces = []

    def preflight(self):
        if not self.store.is_current(self.documents):
            raise RuntimeError("B2 requires the matching semantic index; no lexical substitution")
        return {**ollama_identity(self.client.client, embeddings=True),
                "documents":len(self.documents), "semantic_enabled":True,
                "retriever":"raw semantic cosine only", "top_k":self.config.RAG_TOP_K,
                "embedding_model":self.config.embedding_model, "vector_store":"json"}

    def ask(self, question, history):
        from app.rag.retriever import Retriever
        recent = self.prompt_builder.recent_history(history, current_question=question)
        query = self.prompt_builder.question_for_retrieval(question, recent)
        hits = self.store.search(query, self.config.RAG_TOP_K)
        self.retrieval_traces.append({"question":question,"semantic_query":query,
            "semantic_enabled":True,"bm25_enabled":False,"domain_ranking_enabled":False,
            "candidates":[{"id":h.document.id,"title":h.document.title,"vector_score":h.score,
                "final_score":h.score,"content":h.document.content,"metadata":h.document.metadata} for h in hits],
            "selected_ids":[h.document.id for h in hits]})
        # Share context size/injection filtering and the prompt template, but always call the LLM.
        context = Retriever.context_from_hits(hits)
        answer = self.client.chat(self.prompt_builder.system_prompt(),
                                  self.prompt_builder.user_prompt(question, context, recent))
        return {"answer":answer, "mode":"basic_rag_llm", "needs_human":None,
                "sources":[{"id":h.document.id,"title":h.document.title,"score":h.score,
                            "content":h.document.content,"metadata":h.document.metadata} for h in hits]}


def build_method(method, config, prompt):
    spec = method_spec(method)
    if spec["kind"] == "plain":
        return PlainLlmMethod(config, prompt)
    if spec["kind"] == "rules":
        return RuleMethod(config, spec["curated_faq_rules"])
    if spec["kind"] == "basic_rag":
        return BasicRagMethod(config)
    if spec["kind"] == "proposed":
        return RagMethod(config, RagComponents(**spec["components"]))
    raise ValueError(f"Unknown method: {method}")
