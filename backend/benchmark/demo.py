"""Start an isolated UI demo of P using a frozen Chapter 5 snapshot; no live database."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from uuid import uuid4


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study",type=Path,required=True)
    parser.add_argument("--port",type=int,default=8012)
    parser.add_argument("--frontend-port",type=int,default=5174)
    args=parser.parse_args(); study=args.study.resolve()
    backend=Path(__file__).resolve().parents[1]
    out=backend.parent/".local"/("ui-demo-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid4().hex[:6])
    out.mkdir(parents=True,exist_ok=False)
    corpus=study/"corpus"; database=out/"demo.db"
    # Set the isolated database before importing ANY module that creates Settings/engine.
    os.environ.update(DATABASE_URL="sqlite:///"+database.as_posix(),ENVIRONMENT="test",
        AUTO_SEED="false",WARM_AI_ON_STARTUP="false",CHAT_PROVIDER="ollama",
        CHAT_MODEL="qwen2.5:3b",USE_PROJECT_CHAT_MODEL="false",VECTOR_STORE_BACKEND="json",
        RAG_TOP_K="5",MIN_RETRIEVAL_SCORE="0.38",EMBEDDING_MODEL="nomic-embed-text",
        OLLAMA_BASE_URL="http://127.0.0.1:11434",
        CORS_ORIGINS=f"http://localhost:{args.frontend_port},http://127.0.0.1:{args.frontend_port}")
    for key,name in {"KNOWLEDGE_BASE_PATH":"knowledge_base.md","PRODUCT_CATALOG_PATH":"product_catalog_extended.md",
        "CURATED_FAQ_PATH":"faq_curated.json","PRODUCTS_PATH":"techcare_products.json",
        "RAG_DOCUMENTS_PATH":"techcare_rag_documents.json","PROMPT_PATH":"system_prompt.txt",
        "LEGACY_VECTOR_INDEX_PATH":"vector_index.json"}.items(): os.environ[key]=str(corpus/name)
    from benchmark.chapter5 import verify_study
    protocol=verify_study(study)
    from benchmark.worker import seed_snapshot
    engine=seed_snapshot(corpus,database,protocol["snapshot_timestamp"])
    from app.database import SessionLocal
    from app.models import FAQ
    with SessionLocal() as db:
        for row in json.loads((corpus/"faq_curated.json").read_text(encoding="utf-8"))["faqs"]:
            db.add(FAQ(question=row["question"],answer=row["answer"],category=row["category"],keywords=row.get("triggers",[])))
        db.commit()
    engine.dispose()
    identity={"purpose":"Isolated manual UI demo of P; not a benchmark run", "study":str(study),
              "database":str(database),"model":"qwen2.5:3b","api_port":args.port,"frontend_port":args.frontend_port}
    (out/"demo_config.json").write_text(json.dumps(identity,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(identity,ensure_ascii=False),flush=True)
    print(f"Frontend terminal: $env:VITE_API_BASE_URL='http://127.0.0.1:{args.port}/api'",flush=True)
    print(f"Then: npm run dev -- --host 127.0.0.1 --port {args.frontend_port} --strictPort",flush=True)
    import uvicorn
    uvicorn.run("app.main:app",host="127.0.0.1",port=args.port)


if __name__=="__main__": main()
