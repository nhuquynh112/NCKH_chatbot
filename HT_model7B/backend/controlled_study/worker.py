"""Apply only registered component/provider substitutions to original benchmark methods."""
import argparse
import json
import os
from pathlib import Path
import time


def execute(request):
    database = Path(request["database"]).resolve()
    corpus = Path(request["corpus"]).resolve()
    os.environ.update(DATABASE_URL="sqlite:///file:" + database.as_posix() + "?mode=ro&immutable=1&uri=true",
                      ENVIRONMENT="test", AUTO_SEED="false", WARM_AI_ON_STARTUP="false",
                      PYTHONDONTWRITEBYTECODE="1")
    from app.config import Settings
    from app.model_client import HfLoraClient, ModelNotReady
    from benchmark import worker, methods
    from controlled_study.server import MODEL

    class ControlledSettings(Settings):
        @property
        def chat_model(self):
            return MODEL

    class ControlledClient(HfLoraClient):
        def _verify_identity(self, state):
            expected_adapter = self.profile["adapter_sha256"] if request["condition"] == "ft" else None
            if (state.get("status") != "ready" or state.get("model") != MODEL
                    or state.get("condition") != request["condition"]
                    or state.get("adapter_loaded") != (request["condition"] == "ft")
                    or state.get("adapter_sha256") != expected_adapter
                    or state.get("checkpoint_sha256") != self.profile["checkpoint_sha256"]
                    or state.get("quantization") != "NF4/BF16"):
                raise ModelNotReady("Controlled runtime identity mismatch")

        def chat(self, system_prompt, user_prompt):
            answer = super().chat(system_prompt, user_prompt)
            self._generation_metadata.set({**self.last_generation_metadata,
                                           "condition": request["condition"],
                                           "adapter_loaded": request["condition"] == "ft"})
            return answer

    journal = Path(request["journal_dir"]) if request.get("journal_dir") else None

    class JournalClient(methods.TracedClient):
        phase = "final"

        def chat(self, system_prompt, user_prompt):
            number = len(self.calls) + 1
            if journal:
                with (journal / f"call-{number:02}-started.json").open("x", encoding="utf-8") as stream:
                    json.dump({"phase": self.phase, "system_prompt": system_prompt,
                               "user_prompt": user_prompt, "generation": methods.GENERATION.copy()},
                              stream, ensure_ascii=False, indent=2)
            try:
                return super().chat(system_prompt, user_prompt)
            finally:
                if journal:
                    with (journal / f"call-{number:02}-completed.json").open("x", encoding="utf-8") as stream:
                        json.dump({**self.calls[-1], "phase": self.phase}, stream, ensure_ascii=False, indent=2)

    old_settings = methods.method_settings
    old_factory = methods.build_method

    def settings(*args):
        original = old_settings(*args)
        values = original.model_dump()
        values.update(CHAT_PROVIDER="hf_lora", USE_PROJECT_CHAT_MODEL=False)
        return ControlledSettings(_env_file=None, **values)

    def factory(method, config, prompt):
        runner = old_factory(method, config, prompt)
        runner.client = JournalClient(ControlledClient(config))
        if isinstance(runner, methods.RagMethod):
            runner.chatbot.llm_client = runner.client
            runner.chatbot.retriever.vector_store.embedding_client = runner.client
        elif isinstance(runner, methods.BasicRagMethod):
            runner.store.embedding_client = runner.client

            def preflight():
                if not runner.store.is_current(runner.documents):
                    raise RuntimeError("B2 requires the exact current semantic index")
                embeddings = methods.OllamaClient(config.ollama_base_url, "nomic-embed-text:latest", "nomic-embed-text")
                return {**runner.client.identity(), "embedding_identity": methods.ollama_identity(embeddings),
                        "documents": len(runner.documents), "semantic_enabled": True,
                        "retriever": "raw semantic cosine only", "top_k": config.RAG_TOP_K}

            runner.preflight = preflight
        else:
            runner.preflight = runner.client.identity
        original_ask = runner.ask
        ask_count = 0

        def ask(question, history):
            nonlocal ask_count
            runner.client.phase = "setup" if ask_count < len(request["case"].get("history_questions", [])) else "final"
            ask_count += 1
            return original_ask(question, history)

        runner.ask = ask
        return runner

    def frozen_snapshot(*args, **kwargs):
        from app.database import engine
        import app.product_enrichment as enrichment
        import app.rag.faq_matcher as faq
        assert engine.url.query.get("mode") == "ro"
        verification = enrichment.load_verification_data(corpus / "product_verified_specs.json")
        enrichment.load_verification_data = lambda *a, **kw: verification
        faq.load_curated_faqs.__defaults__ = (corpus / "faq_curated.json",)
        return engine

    methods.method_settings = settings
    methods.build_method = factory
    worker.seed_snapshot = frozen_snapshot
    started = time.perf_counter()
    result = worker.run_case(request)
    result["whole_worker_ms"] = (time.perf_counter() - started) * 1000
    result["study_condition"] = request["condition"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    result = execute(request)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
