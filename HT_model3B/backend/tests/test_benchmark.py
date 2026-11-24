import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from app.config import Settings
from benchmark.methods import method_settings, PlainLlmMethod, RuleMethod, RagMethod
from benchmark.schema import Case, load_cases
from benchmark.scoring import objective_checks, summarize

ROOT = Path(__file__).resolve().parents[1]


class BenchmarkIsolationTests(unittest.TestCase):
    def settings(self, method):
        return method_settings(method,20,ROOT/"rag_data","http://127.0.0.1:11434","http://127.0.0.1:8011")

    def test_m2_m3_force_original_3b_and_m4_selects_adapter(self):
        for method in ("M2","M3"):
            c = self.settings(method)
            self.assertEqual(c.chat_model,"qwen2.5:3b")
            self.assertFalse(c.USE_PROJECT_CHAT_MODEL)
        self.assertEqual(self.settings("M4").chat_model,"qwen2.5-7b-finetuned")

    def test_m2_does_not_read_any_rag_source_or_call_embeddings(self):
        c = self.settings("M2")
        with patch("pathlib.Path.read_text",side_effect=AssertionError("RAG file read")), \
             patch("app.rag.embedding.OllamaClient.embed",side_effect=AssertionError("embedding")), \
             patch("app.rag.embedding.OllamaClient.chat",return_value="unit test answer") as chat:
            method = PlainLlmMethod(c,"neutral system")
            response = method.ask("question",[{"role":"user","content":"earlier user question"}])
        self.assertEqual(response["sources"],[])
        self.assertEqual(chat.call_args.args,("neutral system","user: earlier user question\n\nquestion"))

    def test_m1_never_calls_model(self):
        with patch("app.rag.embedding.OllamaClient.chat",side_effect=AssertionError("LLM called")):
            method = RuleMethod(self.settings("M1"))
            with patch.object(method.policy.product_catalog,"load_products",return_value=()):
                result = method.ask("xin chào",[])
        self.assertEqual(result["mode"],"rule")
        self.assertIsNone(method.client)

    def test_m3_uses_existing_rag_factory_and_retriever(self):
        from app.rag.chat_service import create_default_chat_service
        with patch("app.rag.chat_service.create_default_chat_service", wraps=create_default_chat_service) as factory:
            method = RagMethod(self.settings("M3"))
        factory.assert_called_once()
        self.assertEqual(len(method.chatbot.retriever.all_documents()),195)
        self.assertEqual(method.chatbot.llm_client.chat_model,"qwen2.5:3b")

    def test_missing_index_uses_explicit_lexical_mode(self):
        c = self.settings("M3")
        c.LEGACY_VECTOR_INDEX_PATH = ROOT/"does-not-exist-vector-index.json"
        method = RagMethod(c)
        self.assertFalse(method.chatbot.retriever.semantic_enabled)

    def test_m4_unavailable_fails_preflight(self):
        c = self.settings("M4")
        c.HF_LORA_BASE_URL = "http://127.0.0.1:1"
        method = RagMethod(c)
        with patch("app.rag.embedding.OllamaClient.chat",side_effect=AssertionError("fallback model")):
            with self.assertRaises(Exception):
                method.preflight()


class DatasetAndMetricTests(unittest.TestCase):
    def test_history_generation_is_not_counted_as_final_answer_generation(self):
        from benchmark.worker import run_case
        runner = MagicMock()
        runner.client.calls = []
        runner.client.retrieval_errors = []
        runner.preflight.return_value = {"model":"unit-test-only"}

        def ask(question, history):
            if question == "setup":
                runner.client.calls.append({"error":None})
            return {"answer":"unit-test-only", "sources":[], "mode":"faq"}

        runner.ask.side_effect = ask
        request = {"method":"M2", "case":{"question":"final", "history_questions":["setup"]},
                   "corpus":str(ROOT/"rag_data"), "timeout":20, "ollama_url":"unused",
                   "hf_url":"unused", "plain_prompt":"neutral"}
        with patch("benchmark.methods.build_method",return_value=runner):
            result = run_case(request)
        self.assertFalse(result["llm_called"])
        self.assertTrue(result["setup_llm_called"])
        self.assertEqual(result["calls"][0]["phase"],"setup")

    def test_dataset_valid_and_gold_is_sourced(self):
        cases = load_cases(ROOT/"benchmark/datasets/techcare_v1.json")
        self.assertEqual(len(cases),20)
        self.assertTrue(any(c.history_questions for c in cases))
        with self.assertRaises(ValueError):
            Case(id="bad",category="price",question="price?",expected_answer="invented")

    def test_null_fields_are_supported(self):
        case = Case(id="unknown",category="unknown",question="what?",expected_answer=None,
                    required_facts=None,forbidden_claims=None,expected_source=None,expected_source_ids=None,notes=None)
        self.assertIsNone(case.required_facts)

    def test_errors_not_counted_as_wrong_answers_or_literal_passes(self):
        row = {"run_id":"run","method":"M4","case_id":"x","repeat":1,"status":"not_ready", "latency_ms":None}
        row["objective"] = objective_checks({"required_facts":["x"]},row)
        summary = summarize([row])[0]
        self.assertEqual(summary["not_ready_rate"],1)
        self.assertEqual(summary["literal_evaluated"],0)
        self.assertIsNone(summary["human"]["correctness"]["correct_rate"])

    def test_p95_requires_twenty_samples_and_human_metrics_have_denominators(self):
        row = {"run_id":"run","method":"M2","case_id":"x","repeat":1,"status":"ok","latency_ms":10,
               "objective":{"all_literal_checks_passed":True},"llm_called":True}
        s = summarize([row],[{"run_id":"run","method":"M2","case_id":"x","repeat":1,"correctness":"incorrect","grounded":False}])[0]
        self.assertIsNone(s["p95_ms"])
        self.assertEqual(s["human"]["correctness"]["correct_rate"],0)
        self.assertEqual(s["human"]["grounded"]["reviewed"],1)
        self.assertNotIn("accuracy",s)


if __name__ == "__main__":
    unittest.main()
