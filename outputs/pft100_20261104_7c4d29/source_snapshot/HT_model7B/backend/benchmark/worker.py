"""One isolated case; parent enforces a wall-clock deadline by terminating this process."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import time
import traceback


def is_timeout(error):
    message = str(error).lower()
    return any(term in message for term in ("timeout", "timed out", "deadline"))


def seed_snapshot(corpus, database, snapshot_timestamp=None):
    os.environ.update(DATABASE_URL="sqlite:///" + database.as_posix(), ENVIRONMENT="test",
                      AUTO_SEED="false", WARM_AI_ON_STARTUP="false")
    from app.database import Base, engine, SessionLocal
    from app.models import Product
    from app.product_enrichment import load_verification_data
    # Freeze both default-argument readers against the copied verified specs.
    import app.product_enrichment as enrichment
    verification = load_verification_data(corpus / "product_verified_specs.json")
    enrichment.load_verification_data = lambda *args, **kwargs: verification
    Base.metadata.create_all(bind=engine)
    fields = set(Product.__table__.columns.keys())
    frozen_time = datetime.fromisoformat(snapshot_timestamp) if snapshot_timestamp else None
    with SessionLocal() as db:
        rows = json.loads((corpus / "techcare_products.json").read_text(encoding="utf-8"))
        for row in rows:
            values = {**{k:v for k,v in row.items() if k in fields}, "is_active":True}
            if frozen_time is not None:
                values.update(created_at=frozen_time, updated_at=frozen_time)
            db.add(Product(**values))
        db.commit()
    # FAQ matcher has a module-level default path; pin it before importing the service.
    import app.rag.faq_matcher as faq
    faq.load_curated_faqs.__defaults__ = (corpus / "faq_curated.json",)
    return engine


def run_case(request):
    case, method = request["case"], request["method"]
    corpus = Path(request["corpus"])
    engine = None
    result = {"status":"not_ready", "answer":"", "sources":[], "mode":None,
              "error":None,"calls":[], "history":[], "latency_ms":None,
              "retrieval_errors":[], "identity":None, "llm_called":False,
              "setup_llm_called":False,"snapshot_timestamp":request.get("snapshot_timestamp")}
    final_call_start = None
    try:
        if method not in {"M2", "B1"}:
            engine = seed_snapshot(corpus, Path(request["database"]), request.get("snapshot_timestamp"))
        from benchmark.methods import method_settings, build_method
        config = method_settings(method, request["timeout"], corpus, request["ollama_url"], request["hf_url"])
        runner = build_method(method, config, request["plain_prompt"])
        result["identity"] = runner.preflight()
        result["status"] = "ok"
        history = [dict(turn) for turn in case.get("history", [])]
        for question in case.get("history_questions", []):
            response = runner.ask(question, history)
            history.extend([{"role":"user","content":question},{"role":"assistant","content":response["answer"]}])
        result["history"] = history
        final_call_start = len(runner.client.calls) if runner.client else 0
        start = time.perf_counter()
        try:
            result.update(runner.ask(case["question"], history))
        finally:
            result["latency_ms"] = (time.perf_counter()-start)*1000
        if result["mode"] == "no_rule_match":
            result["status"] = "no_rule_match"
        if runner.client:
            result["calls"] = runner.client.calls
            result["retrieval_errors"] = runner.client.retrieval_errors
            errors = [c["error"] for c in runner.client.calls if c["error"]]
            if errors:
                result["status"] = "timeout" if is_timeout(errors[-1]) else "error"
                result["error"] = errors[-1]
    except Exception as exc:
        if result["status"] == "ok":
            result["status"] = "timeout" if isinstance(exc, TimeoutError) or is_timeout(exc) else "error"
        result["error"] = {"type":type(exc).__name__,"message":str(exc)}
        result["traceback"] = traceback.format_exc()
    finally:
        if "runner" in locals() and runner.client:
            result["calls"] = runner.client.calls
            result["retrieval_errors"] = runner.client.retrieval_errors
        if "runner" in locals():
            result["retrieval_traces"] = getattr(runner, "retrieval_traces", [])
            result["architecture_traces"] = getattr(runner, "architecture_traces", [])
        for index, call in enumerate(result["calls"]):
            call["phase"] = "final" if final_call_start is not None and index >= final_call_start else "setup"
        result["llm_called"] = any(c["phase"] == "final" for c in result["calls"])
        result["setup_llm_called"] = any(c["phase"] == "setup" for c in result["calls"])
        if engine:
            engine.dispose()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = run_case(json.loads(args.request.read_text(encoding="utf-8")))
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
