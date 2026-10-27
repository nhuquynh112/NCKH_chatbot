"""Loopback-only UI harness for the unchanged Chapter 5 benchmark workers.

Never import app.main: this service has no customer routes or database startup.
The worker's database setup hook opens a COPY of a saved benchmark database in
read-only mode instead of seeding products. Model algorithms remain unchanged.
"""
import argparse
import asyncio
import csv
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import ipaddress
import io
import json
import os
import tempfile
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
from uuid import UUID, uuid4

BACKEND = Path(__file__).resolve().parent
REPOSITORY = BACKEND.parent.parent if BACKEND.parent.name in {"HT_model3B", "HT_model7B"} else BACKEND.parent
METHODS = ("B0", "B1", "B2", "P")
CASE_IDS = ("TC01", "TC11", "TC18", "TC21")
PIPELINES = {"B0": "RuleMethod", "B1": "PlainLlmMethod", "B2": "BasicRagMethod", "P": "RagMethod"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def readonly_url(path):
    return "sqlite:///file:" + Path(path).resolve().as_posix() + "?mode=ro&uri=true"


def verify_saved_database(database, corpus, timestamp):
    products = read_json(corpus / "techcare_products.json")
    expected = {p["slug"]: (float(p["price"]), p["warranty_months"], p["specifications"]) for p in products}
    stamp = datetime.fromisoformat(timestamp).astimezone(timezone.utc).replace(tzinfo=None).isoformat(sep=" ", timespec="microseconds")
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
        actual = db.execute("SELECT slug, price, warranty_months, specifications FROM products").fetchall()
        if {s: (float(p), w, json.loads(j)) for s, p, w, j in actual} != expected:
            raise ValueError("Saved product snapshot does not match the study")
        if db.execute("SELECT DISTINCT created_at, updated_at FROM products").fetchall() != [(stamp, stamp)]:
            raise ValueError("Saved snapshot timestamps differ")
        for table in ("chat_sessions", "chat_messages"):
            if db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]:
                raise ValueError("Only an empty benchmark chat database may be copied")


def prepare_context(study, work_dir, port, frontend_port):
    from dotenv import dotenv_values
    environment = os.environ.get("ENVIRONMENT", dotenv_values(BACKEND / ".env").get("ENVIRONMENT", "development"))
    if environment not in {"development", "test"}:
        raise ValueError("The local demo is disabled outside development/test")
    study, work_dir = Path(study).resolve(), Path(work_dir).resolve()
    if work_dir.is_relative_to(REPOSITORY) or work_dir.is_relative_to(study.parent):
        raise ValueError("Choose a work directory outside the project and original study")
    # No connection is opened by Settings. Pin its default away from PostgreSQL.
    os.environ.update(DATABASE_URL=readonly_url(work_dir / "unused.db"), AUTO_SEED="false", WARM_AI_ON_STARTUP="false")
    from benchmark.chapter5 import verify_study
    from benchmark.schema import load_cases
    from benchmark.protocol import method_spec
    protocol = verify_study(study)
    inputs = jsonl(study / "package/test_inputs.jsonl")
    if len(inputs) != 24 or len({row["case_id"] for row in inputs}) != 24:
        raise ValueError("Expected the unchanged 24-case input file")
    adapted = {case.id: case.model_dump() for case in load_cases(study / "inputs.adapter.json")}
    cases = {}
    for source in inputs:
        case = adapted[source["case_id"]]
        if case["question"] != source["question"] or case["history"] != source["history"] or case["history_questions"]:
            raise ValueError("Question/history differs from the original input")
        for field in ("expected_answer", "required_facts", "forbidden_claims", "expected_source", "expected_source_ids", "evidence"):
            if case.get(field) not in (None, [], {}):
                raise ValueError("The inference input must not contain answer-key fields")
        if source["case_id"] in CASE_IDS:
            cases[source["case_id"]] = {"input": deepcopy(source), "worker_case": case}
    if set(cases) != set(CASE_IDS):
        raise ValueError("Missing requested screenshot cases")
    source_db = next(iter(sorted((study / "runs").glob("**/P-1-TC01/isolated.db"))), None)
    if source_db is None:
        raise ValueError("Missing saved P/TC01 database; this harness will not seed a replacement")
    verify_saved_database(source_db, study / "corpus", protocol["snapshot_timestamp"])
    reference = jsonl(study.parent / "P_results.jsonl")[0]["identity"]
    if reference["model"] != protocol.get("chat_model", "qwen2.5:3b") or not reference.get("digest"):
        raise ValueError("Missing original base-model identity")
    out = work_dir / ("web-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
    out.mkdir(parents=True, exist_ok=False)
    shutil.copytree(study / "corpus", out / "corpus")
    shutil.copyfile(source_db, out / "frozen_products.db")
    shutil.copyfile(BACKEND / "benchmark/prompts/plain.txt", out / "plain_prompt.txt")
    (out / "sessions").mkdir()
    context = {"study": str(study), "output": str(out), "database": str(out / "frozen_products.db"),
               "database_sha256": digest(out / "frozen_products.db"), "source_database": str(source_db),
               "corpus": str(out / "corpus"), "corpus_sha256": protocol["corpus_sha256"],
               "snapshot_timestamp": protocol["snapshot_timestamp"], "expected_identity": reference,
               "plain_prompt": str(out / "plain_prompt.txt"), "plain_prompt_sha256": protocol["neutral_prompt_sha256"],
               "timeout": 90, "api_port": port, "frontend_port": frontend_port,
               "instance_id": out.name, "code_matches_original_study": True,
               "input_sha256": digest(study / "package/test_inputs.jsonl"),
               "methods": {method: method_spec(method) for method in METHODS}, "cases": cases}
    write_new(out / "demo_config.json", context)
    return context


def execute_worker(request_path, response_path):
    request = read_json(request_path)
    database, corpus = Path(request["database"]), Path(request["corpus"])
    os.environ.update(DATABASE_URL=readonly_url(database), ENVIRONMENT="test", AUTO_SEED="false", WARM_AI_ON_STARTUP="false")
    from benchmark import worker, methods
    observed = {}

    def open_existing_snapshot(corpus_path, _database_path, snapshot_timestamp=None):
        # Same read defaults as worker.seed_snapshot, without create_all/INSERT.
        from app.database import engine
        if engine.dialect.name != "sqlite" or engine.url.query.get("mode") != "ro":
            raise RuntimeError("The demo refuses any database connection except read-only SQLite")
        observed["database_engine"] = {"driver": engine.dialect.name,
            "database": engine.url.database, "mode": engine.url.query.get("mode")}
        import app.product_enrichment as enrichment
        verification = enrichment.load_verification_data(corpus_path / "product_verified_specs.json")
        enrichment.load_verification_data = lambda *args, **kwargs: verification
        import app.rag.faq_matcher as faq
        faq.load_curated_faqs.__defaults__ = (corpus_path / "faq_curated.json",)
        observed["product_database"] = "existing snapshot opened read-only; no seed"
        return engine

    original_factory = methods.build_method

    def observed_factory(method, config, prompt):
        runner = original_factory(method, config, prompt)
        observed["pipeline_class"] = type(runner).__module__ + "." + type(runner).__name__
        observed["effective_config"] = {"provider": config.CHAT_PROVIDER, "model": config.chat_model,
            "project_profile_enabled": config.USE_PROJECT_CHAT_MODEL, "embedding": config.embedding_model,
            "top_k": config.RAG_TOP_K, "threshold": config.MIN_RETRIEVAL_SCORE,
            "vector_store": config.vector_store_backend, "generation": methods.GENERATION.copy()}
        original_preflight = runner.preflight

        def checked_preflight():
            identity = original_preflight()
            if method != "B0":
                if identity.get("model") != request["expected_identity"]["model"] or identity.get("digest") != request["expected_identity"]["digest"]:
                    raise RuntimeError("Base model differs from the recorded benchmark; inference refused")
            if method in {"B2", "P"}:
                if not identity.get("semantic_enabled") or identity.get("documents") != request.get("expected_documents", 195):
                    raise RuntimeError("Matching semantic index is not ready")
                if identity["embedding_identity"]["digest"] != request["expected_identity"]["embedding_identity"]["digest"]:
                    raise RuntimeError("Embedding model differs from the recorded benchmark")
            return identity

        runner.preflight = checked_preflight
        return runner

    # Only the harness hooks change: the existing worker still calls the
    # existing factory, preflight and ask, and records its unchanged answer.
    worker.seed_snapshot = open_existing_snapshot
    methods.build_method = observed_factory
    result = worker.run_case(request)
    result.update(observed)
    result["harness_sha256"] = digest(Path(__file__).resolve())
    result["history_matches_fixture"] = result.get("history") == request["case"]["history"]
    result["database_mode"] = "not opened by B1" if request["method"] == "B1" else "read-only"
    write_new(response_path, result)


def create_demo_app(context):
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, Response
    from pydantic import BaseModel, ConfigDict, Field
    from typing import Literal
    from benchmark.schema import HistoryTurn
    from blind_review import create_systems, public_record, public_systems

    class FixedRunInput(BaseModel):
        model_config = ConfigDict(extra="forbid")
        session_id: UUID
        method: Literal["B0", "B1", "B2", "P"]
        case_id: Literal["TC01", "TC11", "TC18", "TC21"]

    class ManualRunInput(BaseModel):
        model_config = ConfigDict(extra="forbid")
        session_id: UUID
        method: Literal["B0", "B1", "B2", "P"]
        case_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
        question: str = Field(min_length=1, max_length=6000, pattern=r"\S")
        history: list[HistoryTurn] = Field(default_factory=list, max_length=40)

    class BlindRunInput(BaseModel):
        model_config = ConfigDict(extra="forbid")
        session_id: UUID
        system_id: UUID
        case_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
        question: str = Field(min_length=1, max_length=6000, pattern=r"\S")
        history: list[HistoryTurn] = Field(default_factory=list, max_length=40)

    interactive = context.get("interactive", False)
    blinded = context.get("blinded", False)
    RunInput = ManualRunInput if interactive else FixedRunInput
    app = FastAPI(title="TechCare local benchmark demo", openapi_url=None if blinded else "/openapi.json",
                  docs_url=None if blinded else "/docs", redoc_url=None if blinded else "/redoc")
    origins = {f"http://127.0.0.1:{context['frontend_port']}", f"http://localhost:{context['frontend_port']}"}
    app.add_middleware(CORSMiddleware, allow_origins=sorted(origins), allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
    gate = asyncio.Lock()
    out = Path(context["output"])

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        try:
            local_peer = ipaddress.ip_address(request.client.host).is_loopback
        except (ValueError, AttributeError):
            local_peer = False
        if not local_peer or request.url.hostname not in {"127.0.0.1", "localhost", "::1"}:
            return JSONResponse({"detail": "Local development only"}, status_code=403)
        if request.headers.get("origin") and request.headers["origin"] not in origins:
            return JSONResponse({"detail": "Origin is not the local demo frontend"}, status_code=403)
        if blinded and request.url.path == "/api/demo/runs":
            return JSONResponse({"detail": "Not available in anonymous review"}, status_code=404)
        return await call_next(request)

    def session_path(session_id):
        directory = out / "sessions" / str(session_id)
        if not (directory / "session.json").is_file():
            raise HTTPException(404, "Demo session not found")
        return directory

    @app.get("/api/demo/config")
    def configuration():
        if blinded:
            return {"instance_id": context["instance_id"], "interactive": True, "blinded": True,
                    "cases": [], "timeout_seconds": context["timeout"], "snapshot_verified": True,
                    "notice": "Mã trợ lý được xáo trộn riêng cho mỗi phiên; giữ nguyên nội dung phản hồi khi chấm."}
        return {"instance_id": context["instance_id"], "methods": [
                    {"id": method, "pipeline": PIPELINES[method], "model": None if method == "B0" else context["expected_identity"]["model"]}
                    for method in METHODS],
                "interactive": interactive,
                "cases": [] if interactive else [context["cases"][cid]["input"] for cid in CASE_IDS],
                "model": context["expected_identity"]["model"] + " · " + context["expected_identity"].get("details", {}).get("quantization_level", "chưa xác minh precision") + " · Ollama", "embedding": "nomic-embed-text · 768 chiều",
                "documents": context.get("expected_documents", 195),
                "dataset": context.get("dataset", "historical_snapshot"),
                "generation": {"temperature": 0, "context": 4096, "max_output": 384, "repeat_penalty": 1},
                "timeout_seconds": context["timeout"], "input_source": context.get("input_source") if interactive else str(Path(context["study"]) / "package/test_inputs.jsonl"),
                "output": context["output"], "snapshot_time": context["snapshot_timestamp"],
                "snapshot_verified": True, "customer_database_used": False,
                "notice": "Nhóm tự nhập câu hỏi; dùng cùng câu hỏi/lịch sử cho B0/B1/B2/P. Đây là lượt test mới, chưa được chấm điểm." if interactive else "Lượt chạy web mới trên snapshot benchmark. Không phải phát lại kết quả benchmark cũ. P+FT không thuộc bốn phương pháp chính."}

    @app.post("/api/demo/sessions")
    def new_session():
        sid = uuid4()
        folder = out / "sessions" / str(sid)
        folder.mkdir()
        record = {"session_id": str(sid), "created_at": datetime.now(timezone.utc).isoformat(), "demo_only": True}
        write_new(folder / "session.json", record)
        if blinded:
            # This file is private to the local coordinator, not an API export.
            write_new(folder / "mapping_RIENG.json", create_systems(METHODS))
            return get_session(sid)
        return {**record, "runs": []}

    @app.get("/api/demo/sessions/{session_id}")
    def get_session(session_id: UUID):
        folder = session_path(session_id)
        if blinded:
            systems = read_json(folder / "mapping_RIENG.json")
            return {**read_json(folder / "session.json"), "blinded": True, "systems": public_systems(systems),
                    "runs": [public_record(read_json(path), systems) for path in sorted(folder.glob("*/result.json"))]}
        return {**read_json(folder / "session.json"), "runs": [read_json(path) for path in sorted(folder.glob("*/result.json"))]}

    @app.get("/api/demo/sessions/{session_id}/runs/{run_id}")
    def get_run(session_id: UUID, run_id: UUID):
        path = session_path(session_id) / str(run_id) / "result.json"
        if not path.is_file():
            raise HTTPException(404, "Demo run not found")
        if blinded:
            return public_record(read_json(path), read_json(path.parent.parent / "mapping_RIENG.json"))
        return read_json(path)

    @app.get("/api/demo/sessions/{session_id}/export.csv")
    def export_session(session_id: UUID):
        folder = session_path(session_id)
        stream = io.StringIO(newline="")
        if blinded:
            systems = read_json(folder / "mapping_RIENG.json")
            fields = ["run_id", "case_id", "system_id", "system_label", "question", "history", "answer", "status", "score_0_2", "reviewer", "notes"]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for path in sorted(folder.glob("*/result.json")):
                record = public_record(read_json(path), systems)
                writer.writerow({**{key: record[key] for key in ("run_id", "case_id", "system_id", "system_label", "question")},
                                 "history": json.dumps(record["fixed_history"], ensure_ascii=False),
                                 "answer": record["result"]["answer"], "status": record["result"]["status"]})
            return Response(content=stream.getvalue().encode("utf-8-sig"), media_type="text/csv",
                            headers={"Content-Disposition": f'attachment; filename="techcare-review-{session_id}.csv"'})
        fields = ["run_id", "case_id", "method", "question", "history", "answer", "status", "mode", "llm_called", "latency_ms", "model", "digest", "sources", "score_0_2", "reviewer", "notes"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for path in sorted(folder.glob("*/result.json")):
            record = read_json(path)
            result = record["result"]
            identity = result.get("identity") or {}
            writer.writerow({"run_id": record["run_id"], "case_id": record["case_id"], "method": record["method"],
                "question": record["question"], "history": json.dumps(record["fixed_history"], ensure_ascii=False),
                "answer": result.get("answer", ""), "status": result["status"], "mode": result.get("mode"),
                "llm_called": result.get("llm_called", False), "latency_ms": result.get("latency_ms"),
                "model": identity.get("model"), "digest": identity.get("digest"),
                "sources": json.dumps(result.get("sources", []), ensure_ascii=False)})
        return Response(content=stream.getvalue().encode("utf-8-sig"), media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="techcare-{session_id}.csv"'})

    @app.post("/api/demo/runs")
    async def run_case(body: RunInput):
        folder = session_path(body.session_id)
        if gate.locked():
            raise HTTPException(409, "Another local inference is running; wait for it to finish")
        async with gate:
            if interactive:
                from comparison_demo import verify_context
                try:
                    verify_context(context)
                except (ValueError, OSError) as exc:
                    raise HTTPException(409, str(exc)) from exc
                case = {"id": body.case_id, "category": "human_test", "question": body.question,
                        "history": [turn.model_dump() for turn in body.history], "history_questions": []}
                for path in folder.glob("*/result.json"):
                    previous = read_json(path)
                    if previous["case_id"] == body.case_id and (previous["question"] != case["question"] or
                            ((not blinded or previous["method"] == body.method) and previous["fixed_history"] != case["history"])):
                        raise HTTPException(409, "Case ID already has a different question/history. Reuse the saved input or choose a new ID.")
            else:
                from benchmark.chapter5 import verify_study
                verify_study(Path(context["study"]))
                case = deepcopy(context["cases"][body.case_id]["worker_case"])
            if digest(context["database"]) != context["database_sha256"] or digest(context["plain_prompt"]) != context["plain_prompt_sha256"]:
                raise HTTPException(409, "The demo snapshot changed; restart from the frozen study")
            if any(digest(Path(context["corpus"]) / name) != h for name, h in context["corpus_sha256"].items()):
                raise HTTPException(409, "Corpus changed; inference refused")
            run_id = uuid4()
            work = folder / str(run_id)
            work.mkdir()
            request_data = {"method": body.method, "case": case,
                "corpus": context["corpus"], "database": context["database"], "timeout": context["timeout"],
                "snapshot_timestamp": context["snapshot_timestamp"], "ollama_url": "http://127.0.0.1:11434",
                "hf_url": "http://127.0.0.1:8011", "plain_prompt": Path(context["plain_prompt"]).read_text(encoding="utf-8"),
                "expected_identity": context["expected_identity"],
                "expected_documents": context.get("expected_documents", 195)}
            write_new(work / "request.json", request_data)
            started = time.perf_counter()
            command = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", str(work / "request.json"), str(work / "response.json")]
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
            try:
                process = await asyncio.to_thread(subprocess.run, command, cwd=BACKEND, env=env, capture_output=True, timeout=context["timeout"])
                (work / "worker.log").write_bytes(process.stdout + b"\n" + process.stderr)
                if process.returncode or not (work / "response.json").is_file():
                    raise RuntimeError("Worker failed; inspect the saved worker.log")
                result = read_json(work / "response.json")
            except subprocess.TimeoutExpired as exc:
                (work / "worker.log").write_bytes((exc.stdout or b"") + b"\n" + (exc.stderr or b""))
                result = {"status": "timeout", "answer": "", "error": {"type": "ProcessTimeout", "message": "Whole-case deadline exceeded"}}
            except Exception as exc:
                result = {"status": "error", "answer": "", "error": {"type": type(exc).__name__, "message": str(exc)}}
            record = {"run_id": str(run_id), "session_id": str(body.session_id), "method": body.method,
                "case_id": body.case_id, "question": request_data["case"]["question"],
                "fixed_history": request_data["case"]["history"], "created_at": datetime.now(timezone.utc).isoformat(),
                "wall_ms": (time.perf_counter() - started) * 1000, "new_web_run": True,
                "architecture": context["methods"][body.method], "result": result}
            write_new(work / "result.json", record)
            if blinded:
                status = "ok" if result["status"] == "no_rule_match" else result["status"]
                print(f"REVIEW_RUN {body.case_id} {status} run={run_id}", flush=True)
            else:
                print(f"DEMO_RUN {body.method} {body.case_id} {result['status']} pipeline={result.get('pipeline_class')} run={run_id}", flush=True)
            return record

    @app.post("/api/demo/blind/runs")
    async def run_blind_case(body: BlindRunInput):
        if not blinded or not interactive:
            raise HTTPException(404, "Anonymous review is not enabled")
        systems = read_json(session_path(body.session_id) / "mapping_RIENG.json")
        system = next((row for row in systems if row["system_id"] == str(body.system_id)), None)
        if system is None:
            raise HTTPException(404, "Anonymous system not found in this session")
        original = ManualRunInput(session_id=body.session_id, method=system["method"], case_id=body.case_id,
                                  question=body.question, history=body.history)
        return public_record(await run_case(original), systems)

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path)
    parser.add_argument("--work-dir", type=Path, default=Path(os.environ.get("CHATBOT_WORK_DIR", tempfile.gettempdir())) / "TechCare/local_web_demo")
    parser.add_argument("--port", type=int, default=8012)
    parser.add_argument("--frontend-port", type=int, default=5174)
    parser.add_argument("--worker", nargs=2, metavar=("REQUEST", "RESPONSE"))
    args = parser.parse_args()
    if args.worker:
        execute_worker(*args.worker)
        return
    if args.study is None:
        parser.error("--study is required")
    context = prepare_context(args.study, args.work_dir, args.port, args.frontend_port)
    print(json.dumps({"api": f"http://127.0.0.1:{args.port}/api/demo/config", "output": context["output"],
                      "database_mode": "copied existing benchmark snapshot, read-only; no seed"}, ensure_ascii=False), flush=True)
    import uvicorn
    uvicorn.run(create_demo_app(context), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
