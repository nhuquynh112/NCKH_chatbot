"""Reproducible end-to-end benchmark on a disposable database; no cloud AI."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import tempfile
import time

from evaluation_paths import artifact_directory, temporary_directory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="after")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--legacy-faqs", action="store_true", help="Reproduce the existing database's two original seed FAQs in the disposable database")
    args = parser.parse_args()
    if not args.label.replace("_", "").replace("-", "").isalnum():
        parser.error("Label must only contain letters, numbers, '-' or '_'")
    root = Path(__file__).resolve().parent
    fixture = root / "evaluation_cases.json"
    cases = json.loads(fixture.read_text(encoding="utf-8"))["cases"]
    with tempfile.TemporaryDirectory(prefix="techcare-quality-", dir=temporary_directory()) as tmp:
        os.environ["DATABASE_URL"] = "sqlite:///" + (Path(tmp) / "test.db").as_posix()
        os.environ["ENVIRONMENT"] = "test"
        os.environ["WARM_AI_ON_STARTUP"] = "false"
        if args.offline:
            os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:1"
        from fastapi.testclient import TestClient
        from app.main import app
        from app.services.ai_service import AIService
        from app.rag.guardrails import canonical_text, parse_price
        from app.rag.chat_service import create_default_chat_service
        if args.legacy_faqs:
            from app.database import SessionLocal
            from app.models import FAQ
            from app.rag.faq_matcher import LEGACY_UNVERIFIED_ANSWERS
            with SessionLocal() as db:
                # DATABASE_URL above is always an isolated temporary file.
                db.query(FAQ).delete()
                for answer in LEGACY_UNVERIFIED_ANSWERS:
                    question = "Cửa hàng có hỗ trợ trả góp không?" if "trả góp" in answer else "Chính sách đổi trả của TechCare như thế nào?"
                    db.add(FAQ(question=question, answer=answer, category="Demo"))
                db.commit()

        results = []
        with TestClient(app) as client:
            AIService._chatbot = create_default_chat_service()
            for case in cases:
                visitor = "quality-" + case["id"]
                headers = {"X-Visitor-ID": visitor}
                session = client.post("/api/chat/sessions", headers=headers, json={"visitor_id": visitor}).json()["data"]["id"]
                for setup in case.get("setup", []):
                    client.post("/api/chat/messages", headers=headers, json={"session_id": session, "content": setup})
                started = time.perf_counter()
                response = client.post("/api/chat/messages", headers=headers, json={"session_id": session, "content": case["question"]})
                elapsed = (time.perf_counter() - started) * 1000
                payload = response.json().get("data") or {}
                message = payload.get("message") or {}
                answer = message.get("content", "")
                folded = canonical_text(answer)
                missing = [s for s in case.get("required", []) if canonical_text(s) not in folded]
                invented = [s for s in case.get("forbidden", []) if canonical_text(s) in folded]
                failures = ["missing: " + s for s in missing] + ["forbidden: " + s for s in invented]
                if response.status_code != 201:
                    failures.append("API: " + str(response.status_code))
                if "ticket" in case and payload.get("ticket_created") != case["ticket"]:
                    failures.append("incorrect ticket decision")
                chatbot = AIService._chatbot
                if "max_product_price" in case and chatbot:
                    products = chatbot.guardrails.mentioned_products(answer)
                    if not products or any(parse_price(p["price"]) > case["max_product_price"] for p in products):
                        failures.append("product exceeds budget or missing recommendation")
                retrieval = None
                retrieval_error = None
                if case.get("retrieval_any") and chatbot:
                    try:
                        hits = chatbot.retriever.search(case["question"], top_k=5)
                        titles = [h.document.title for h in hits]
                        retrieval = any(canonical_text(expected) in canonical_text(title) for expected in case["retrieval_any"] for title in titles)
                    except Exception as exc:
                        titles = []
                        retrieval_error = type(exc).__name__
                else:
                    titles = []
                result = {"id":case["id"], "group":case["group"], "question":case["question"], "answer":answer,
                          "mode":message.get("intent"), "ms":round(elapsed, 2), "status":response.status_code,
                          "passed":not failures, "failures":failures, "forbidden_claims":invented,
                          "retrieval_at_5":retrieval, "retrieval_titles":titles, "retrieval_error":retrieval_error}
                results.append(result)
                print(f"{case['id']} {'PASS' if not failures else 'FAIL'} {elapsed:.0f}ms {failures}", flush=True)
        timings = sorted(r["ms"] for r in results)
        retrieved = [r for r in results if r["retrieval_at_5"] is not None]
        summary = {"label":args.label, "offline":args.offline, "legacy_faqs":args.legacy_faqs, "fixture_sha256":hashlib.sha256(fixture.read_bytes()).hexdigest(),
                   "cases":len(results), "passed":sum(r["passed"] for r in results),
                   "api_errors":sum(r["status"] != 201 for r in results),
                   "forbidden_claim_cases":sum(bool(r["forbidden_claims"]) for r in results),
                   "retrieval_hit_at_5":sum(r["retrieval_at_5"] for r in retrieved), "retrieval_cases":len(retrieved),
                   "median_ms":statistics.median(timings), "p95_ms":timings[math.ceil(.95 * len(timings)) - 1],
                   "generative_cases":sum(r["mode"] == "llm+rag" for r in results)}
        output = artifact_directory() / (args.label + "_quality.json")
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps({"summary":summary, "results":results}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False), flush=True)
        # Close pooled SQLite connections before Windows removes the temporary directory.
        from app.database import engine
        engine.dispose()
        return 0 if summary["passed"] == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
