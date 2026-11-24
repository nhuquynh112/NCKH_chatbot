import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.rag.components import RagComponents
from app.rag.query_rewriter import QueryRewriter
from app.rag.retriever import Retriever
from app.rag.vector_store import Document, SearchResult
from benchmark.chapter5 import adapt_inputs
from benchmark.methods import BasicRagMethod, RagMethod, method_settings
from benchmark.protocol import ABLATIONS, method_spec
from benchmark.worker import run_case

ROOT = Path(__file__).resolve().parents[1]


def config(method="P"):
    return method_settings(method, 30, ROOT/"rag_data", "http://127.0.0.1:11434", "http://127.0.0.1:8011")


class InputAndMethodBoundaryTests(unittest.TestCase):
    def test_24_adapter_preserves_supplied_history_and_excludes_answer_key(self):
        original={"case_id":"TC21","group":"history","family_id":"family",
                  "question":"final?","history":[{"role":"user","content":"earlier"},
                    {"role":"assistant","content":"fixed supplied answer"}],
                  "reference_answer":"DO NOT PASS THIS", "required_criteria":["gold"]}
        case=adapt_inputs([original])[0]
        self.assertEqual(case["history"], original["history"])
        self.assertEqual(case["question"], original["question"])
        self.assertIsNone(case["expected_answer"])
        self.assertIsNone(case["required_facts"])
        self.assertEqual(case["evidence"], [])
        self.assertNotIn("DO NOT PASS THIS", str(case))

    def test_fixed_history_is_not_regenerated_and_b1_never_seeds_database(self):
        history=[{"role":"user","content":"old"},{"role":"assistant","content":"fixed"}]
        runner=MagicMock(); runner.client.calls=[]; runner.client.retrieval_errors=[]
        runner.preflight.return_value={"model":"unit-test-only"}
        runner.ask.return_value={"answer":"unit-test-only","sources":[],"mode":"llm_without_rag"}
        request={"method":"B1","case":{"question":"last","history":history},
                 "corpus":str(ROOT/"rag_data"),"timeout":30,"ollama_url":"unused","hf_url":"unused","plain_prompt":"neutral"}
        with patch("benchmark.worker.seed_snapshot",side_effect=AssertionError("database accessed")), \
             patch("benchmark.methods.build_method",return_value=runner):
            result=run_case(request)
        runner.ask.assert_called_once_with("last",history)
        self.assertEqual(result["history"],history)

    def test_each_ablation_wires_exactly_one_switch_into_both_service_and_retriever(self):
        full=asdict(RagComponents())
        for method,component in ABLATIONS.items():
            spec=method_spec(method); self.assertEqual([k for k in full if spec["components"][k]!=full[k]],[component])
            runner=RagMethod(config(method),RagComponents(**spec["components"]))
            self.assertEqual(asdict(runner.chatbot.components),spec["components"])
            self.assertIs(runner.chatbot.components,runner.chatbot.retriever.components)
        self.assertEqual(method_spec("P")["components"],method_spec("P+FT")["components"])

    def test_b2_uses_vector_then_llm_without_rules_bm25_or_postcheck(self):
        runner=BasicRagMethod(config("B2")); doc=Document("unit","Unit source","Unit evidence",{})
        history=[{"role":"user","content":"prior"}]
        with patch.object(runner.store,"search",return_value=[SearchResult(.8,doc)]) as search, \
             patch.object(runner.client.client,"chat",return_value="unit answer") as chat, \
             patch("app.rag.retriever.bm25_search",side_effect=AssertionError("BM25 called")), \
             patch("app.rag.guardrails.GuardrailPolicy.deterministic_answer",side_effect=AssertionError("routing called")), \
             patch("app.rag.chat_service.unsupported_claims",side_effect=AssertionError("postcheck called")):
            response=runner.ask("question",history)
        self.assertEqual(search.call_args.args[1],5)
        self.assertIn("prior",search.call_args.args[0])
        chat.assert_called_once()
        self.assertEqual(response["mode"],"basic_rag_llm")
        self.assertEqual(response["answer"],"unit answer")


class RetrievalAblationTests(unittest.TestCase):
    def retriever(self,components=RagComponents()):
        self.lexical=Document("lexical","Warranty","warranty details",{})
        self.semantic=Document("semantic","Other","semantic details",{})
        store=MagicMock(); store.get_all_documents.return_value=[self.lexical,self.semantic]
        store.search.return_value=[SearchResult(.6,self.semantic)]
        retriever=Retriever(store,QueryRewriter(),MagicMock())
        retriever.components=components
        retriever.score_adjustment=MagicMock(side_effect=lambda q,d:.8 if d.id=="lexical" else 0.)
        self.traces=[]; retriever.trace_observer=self.traces.append
        return retriever

    def test_full_hybrid_and_disabled_ranking_really_change_selected_document(self):
        full=self.retriever()
        with patch("app.rag.retriever.bm25_search",return_value=[SearchResult(1,self.lexical)]):
            self.assertEqual(full.search("bh bn",1)[0].document.id,"lexical")
        disabled=self.retriever(RagComponents().without("domain_ranking"))
        disabled.score_adjustment=MagicMock(side_effect=AssertionError("ranking reached"))
        with patch("app.rag.retriever.bm25_search",return_value=[SearchResult(1,self.lexical)]):
            self.assertEqual(disabled.search("bh bn",1)[0].document.id,"semantic")
        disabled.score_adjustment.assert_not_called()

    def test_disabled_bm25_removes_lexical_candidates_and_retains_vector_weight(self):
        retriever=self.retriever(RagComponents().without("bm25"))
        with patch("app.rag.retriever.bm25_search",side_effect=AssertionError("BM25 reached")):
            hits=retriever.search("bh bn",5)
        self.assertEqual([h.document.id for h in hits],["semantic"])
        self.assertAlmostEqual(hits[0].score,.6*.6)
        self.assertFalse(self.traces[0]["bm25_enabled"])

    def test_disabled_query_rewriter_sends_exact_original_query(self):
        retriever=self.retriever(RagComponents().without("query_normalization"))
        retriever.query_rewriter=MagicMock(); retriever.query_rewriter.expand_for_retrieval.side_effect=AssertionError("rewrite reached")
        with patch("app.rag.retriever.bm25_search",return_value=[]): retriever.search("bh bn",5)
        retriever.vector_store.search.assert_called_once_with("bh bn",20)
        self.assertEqual(self.traces[0]["semantic_query"],"bh bn")


class ServiceAblationTests(unittest.TestCase):
    def test_disabling_rule_routing_reaches_generation_for_a_catalog_fact(self):
        question="Sạc Anker Nano 65W giá bao nhiêu?"
        for disabled in (False,True):
            runner=RagMethod(config(),RagComponents(rule_routing=not disabled))
            hit=SearchResult(1,Document("unit","Unit evidence","Catalog evidence",{}))
            with patch.object(runner.chatbot.guardrails.product_catalog,"_load_database_products",return_value=None), \
                 patch.object(runner.chatbot.retriever,"search",return_value=[hit]), \
                 patch.object(runner.client.client,"chat",return_value="unit answer") as chat:
                result=runner.ask(question,[])
            self.assertEqual(chat.call_count,1 if disabled else 0)
            self.assertEqual(result["mode"],"llm+rag" if disabled else "rule+rag")

    def test_postcheck_removal_passes_through_a_claim_previously_blocked(self):
        for enabled in (True,False):
            runner=RagMethod(config(),RagComponents(postcheck=enabled))
            hit=SearchResult(1,Document("unit","Unit evidence","No price is available.",{}))
            with patch.object(runner.chatbot.guardrails,"deterministic_answer",return_value=None), \
                 patch.object(runner.chatbot.guardrails,"should_fallback",return_value=False), \
                 patch("app.rag.chat_service.match_curated_faqs",return_value=[]), \
                 patch.object(runner.chatbot.retriever,"search",return_value=[hit]), \
                 patch.object(runner.client.client,"chat",return_value="Giá là 123.456.789 VND."):
                result=runner.ask("Giải thích một tình huống không gắn sản phẩm.",[])
            self.assertEqual(result["mode"],"fallback" if enabled else "llm+rag")
            trace=[t for t in runner.architecture_traces if t["stage"]=="postcheck"][0]
            self.assertEqual(trace["evaluated"],enabled)
            self.assertEqual(trace["blocked"],enabled)

    def test_product_context_removal_keeps_history_but_stops_structured_resolution(self):
        history=[{"role":"user","content":"Tôi đang xem AirPods Pro 2 USB-C."},
                 {"role":"assistant","content":"Bạn cần hỏi gì về mẫu này?"}]
        for enabled in (True,False):
            runner=RagMethod(config(),RagComponents(product_context=enabled))
            with patch.object(runner.chatbot.guardrails.product_catalog,"_load_database_products",return_value=None), \
                 patch.object(runner.chatbot.retriever,"search",return_value=[]):
                runner.ask("Còn bảo hành bao lâu?",history)
            trace=[t for t in runner.architecture_traces if t["stage"]=="product_context"][0]
            self.assertEqual(trace["history_messages"],2)
            self.assertEqual(bool(trace["resolved_product"]),enabled)
            self.assertEqual(trace["use_history_for_retrieval"],enabled)


if __name__=="__main__": unittest.main()
