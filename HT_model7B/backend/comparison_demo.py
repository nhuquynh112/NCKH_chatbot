"""Local manual testing of the existing B0/B1/B2/P benchmark pipelines."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from uuid import uuid4

from local_demo import BACKEND, REPOSITORY, METHODS, create_demo_app, digest, read_json, readonly_url, verify_saved_database, write_new


def require_local_environment():
    from dotenv import dotenv_values
    environment = os.environ.get("ENVIRONMENT", dotenv_values(BACKEND / ".env").get("ENVIRONMENT", "development"))
    if environment not in {"development", "test"}:
        raise ValueError("Manual comparison is disabled outside development/test")


def verify_context(context):
    from benchmark.chapter5 import code_hashes
    if code_hashes() != context["code_sha256"] or any(digest(BACKEND / name) != value for name, value in context["harness_sha256"].items()):
        raise ValueError("Source changed during testing. Start a new test workspace; keep the old results.")


def prepare_context(work_dir, port=8012, frontend_port=5174, timeout=120, resume=None):
    require_local_environment()
    root = Path(resume if resume else work_dir).resolve()
    if root.is_relative_to(REPOSITORY):
        raise ValueError("Test output must be outside the repository")
    # No customer application startup and no connection to its configured DB.
    os.environ.update(DATABASE_URL=readonly_url(root / "unused.db"), AUTO_SEED="false", WARM_AI_ON_STARTUP="false")
    if resume:
        context = read_json(root / "demo_config.json")
        if not context.get("interactive") or Path(context["output"]).resolve() != root:
            raise ValueError("Not a saved manual comparison workspace")
        verify_context(context)
        verify_saved_database(Path(context["database"]), Path(context["corpus"]), context["snapshot_timestamp"])
        context.update(api_port=port, frontend_port=frontend_port)
        return context

    from app.config import BASELINE_CHAT_MODEL
    from app.config import settings
    from app.rag.embedding import OllamaClient
    from benchmark.chapter5 import code_hashes
    from benchmark.methods import ollama_identity
    from benchmark.protocol import method_spec
    from benchmark.run import CORPUS_FILES
    identity = ollama_identity(OllamaClient("http://127.0.0.1:11434", BASELINE_CHAT_MODEL, "nomic-embed-text"), embeddings=True)
    if identity["details"].get("quantization_level") != "F16":
        raise ValueError("This comparison requires the installed original FP16 model; no Q4 substitution")
    out = root / ("web-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
    out.mkdir(parents=True, exist_ok=False)
    corpus = out / "corpus"
    corpus.mkdir()
    for name in CORPUS_FILES:
        shutil.copyfile(settings.products_path.parent / name, corpus / name)
    shutil.copyfile(BACKEND / "benchmark/prompts/plain.txt", out / "plain_prompt.txt")
    timestamp = datetime.now(timezone.utc).isoformat()
    database = out / "frozen_products.db"
    # seed_snapshot imports an engine at module scope. Run it in a fresh process
    # whose only target is this newly created workspace, never the website DB.
    process = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--snapshot", str(corpus), str(database), timestamp],
                             cwd=BACKEND, capture_output=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=60)
    (out / "snapshot.log").write_bytes(process.stdout + b"\n" + process.stderr)
    if process.returncode:
        raise RuntimeError("Snapshot initialization failed; inspect " + str(out / "snapshot.log"))
    verify_saved_database(database, corpus, timestamp)
    from app.rag.vector_store import load_markdown_documents
    document_count = len(load_markdown_documents([
        corpus / "knowledge_base.md", corpus / "product_catalog_extended.md", corpus / "faq_curated.json",
    ]))
    (out / "sessions").mkdir()
    context = {"interactive": True, "instance_id": out.name, "output": str(out), "database": str(database),
        "database_sha256": digest(database), "corpus": str(corpus), "corpus_sha256": {name: digest(corpus / name) for name in CORPUS_FILES},
        "snapshot_timestamp": timestamp, "plain_prompt": str(out / "plain_prompt.txt"), "plain_prompt_sha256": digest(out / "plain_prompt.txt"),
        "expected_identity": identity, "expected_documents": document_count,
        "dataset": settings.products_path.parent.name, "timeout": timeout, "api_port": port, "frontend_port": frontend_port,
        "methods": {method: method_spec(method) for method in METHODS}, "cases": {},
        "code_sha256": code_hashes(), "harness_sha256": {name: digest(BACKEND / name) for name in ("local_demo.py", "comparison_demo.py")},
        "input_source": "Câu hỏi và lịch sử do nhóm nhập; lưu nguyên nội dung theo mã câu trong phiên test."}
    write_new(out / "demo_config.json", context)
    return context


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, default=Path(os.environ.get("CHATBOT_WORK_DIR", tempfile.gettempdir())) / "TechCare/comparison_test")
    parser.add_argument("--resume", type=Path, help="Resume the printed web-... workspace without overwriting previous runs")
    parser.add_argument("--port", type=int, default=8012)
    parser.add_argument("--frontend-port", type=int, default=5174)
    parser.add_argument("--timeout", type=int, default=120, choices=range(10, 121), metavar="10..120")
    parser.add_argument("--snapshot", nargs=3, metavar=("CORPUS", "DATABASE", "TIMESTAMP"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.snapshot:
        corpus, database, timestamp = args.snapshot
        corpus, database = Path(corpus).resolve(), Path(database).resolve()
        if database.exists() or database.parent != corpus.parent or database.is_relative_to(REPOSITORY):
            raise ValueError("Only a new database inside the external test workspace may be initialized")
        from benchmark.worker import seed_snapshot
        seed_snapshot(corpus, database, timestamp).dispose()
        return
    context = prepare_context(args.work_dir, args.port, args.frontend_port, args.timeout, args.resume)
    print(json.dumps({"website": f"http://127.0.0.1:{args.frontend_port}/benchmark-demo", "output": context["output"],
        "resume": f'python comparison_demo.py --resume "{context["output"]}"', "model": context["expected_identity"]["model"]}, ensure_ascii=False), flush=True)
    import uvicorn
    uvicorn.run(create_demo_app(context), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
