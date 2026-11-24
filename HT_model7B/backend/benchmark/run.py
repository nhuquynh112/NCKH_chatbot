"""Repeatable M1-M4 benchmark with subprocess isolation and immutable per-run output."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from uuid import uuid4

from benchmark.schema import load_cases, HumanReview
from benchmark.scoring import objective_checks, summarize
from app.config import BASELINE_CHAT_MODEL, HF_LORA_MODEL
from benchmark.protocol import METHOD_NAMES, method_spec

ROOT = Path(__file__).resolve().parents[1]
CORPUS_FILES = ["knowledge_base.md","product_catalog_extended.md","faq_curated.json","techcare_products.json",
                "techcare_rag_documents.json","product_verified_specs.json","system_prompt.txt","vector_index.json"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def export_tables(directory, rows, reviews=()):
    summary = summarize(rows, reviews)
    write_json(directory / "summary.json", summary)
    with (directory / "results.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["run_id","method","model","case_id","category","repeat","status","mode","llm_called","latency_ms","answer","sources","error","objective"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(row.get(k),ensure_ascii=False) if isinstance(row.get(k),(dict,list)) else row.get(k) for k in fields})
    with (directory / "summary.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["method","attempts","answered","error_timeout_rate","not_ready_rate","llm_called_cases","literal_passes","literal_evaluated","median_ms","p95_ms"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k:r[k] for k in fields} for r in summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "benchmark/datasets/techcare_v1.json")
    parser.add_argument("--methods", nargs="+", choices=METHOD_NAMES, default=["M1","M2","M3","M4"])
    parser.add_argument("--corpus", type=Path, default=ROOT/"rag_data")
    parser.add_argument("--study-manifest", type=Path)
    parser.add_argument("--snapshot-timestamp", help="Freeze technical Product timestamps in isolated databases")
    parser.add_argument("--dataset-role", default="Agent-authored development suite, awaiting human validation; not a blind holdout.")
    parser.add_argument("--case-ids", nargs="+")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=60, help="Whole-case subprocess deadline, including history and setup")
    parser.add_argument("--output-root", type=Path, default=ROOT.parent / ".local/benchmark_results")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--hf-url", default="http://127.0.0.1:8011")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    cases = load_cases(args.dataset.resolve())
    if args.case_ids:
        missing = set(args.case_ids)-{c.id for c in cases}
        if missing: parser.error(f"Unknown case IDs: {sorted(missing)}")
        cases = [c for c in cases if c.id in args.case_ids]
    if args.validate_only:
        print(json.dumps({"status":"valid","cases":len(cases),"dataset_sha256":digest(args.dataset)}))
        return
    if not 1 <= args.repeats <= 100 or not 10 <= args.timeout <= 120:
        parser.error("Use 1-100 repeats and a 10-120 second case deadline")
    if len(set(args.methods)) != len(args.methods): parser.error("Methods must be unique")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    directory = args.output_root.resolve() / run_id
    directory.mkdir(parents=True, exist_ok=False)
    corpus = directory / "corpus"
    corpus.mkdir()
    for name in CORPUS_FILES:
        shutil.copyfile(args.corpus.resolve() / name, corpus / name)
    shutil.copyfile(args.dataset, directory / ("dataset.source" + args.dataset.suffix))
    plain_prompt = (ROOT / "benchmark/prompts/plain.txt").read_text(encoding="utf-8")
    (directory / "plain_prompt.txt").write_text(plain_prompt,encoding="utf-8")
    manifest = {"run_id":run_id,"started_utc":datetime.now(timezone.utc).isoformat(),
                "methods":args.methods,"case_order":[c.id for c in cases],"repeats":args.repeats,
                "chat_model":BASELINE_CHAT_MODEL,
                "method_specs":{m:method_spec(m) for m in args.methods},
                "timeout_seconds":args.timeout,"dataset_sha256":digest(args.dataset),
                "corpus_sha256":{p.name:digest(p) for p in corpus.iterdir()},
                "plain_prompt_sha256":digest(directory / "plain_prompt.txt"),
                "code_sha256":{str(p.relative_to(ROOT)):digest(p) for d in [ROOT/"app",ROOT/"benchmark",ROOT/"model_serving"] for p in sorted(d.rglob("*.py"))},
                "python":sys.version,"ollama_url":args.ollama_url,"hf_url":args.hf_url,
                "generation":{"temperature":0,"max_new_tokens":384,"context":4096,"repeat_penalty":1.0},
                "dataset_role":args.dataset_role,
                "study_manifest_sha256":digest(args.study_manifest) if args.study_manifest else None,
                "snapshot_timestamp":args.snapshot_timestamp,
                "warmup":"No discarded warm-up; cold/warm state is not controlled. Use a separate warm-up run and report it.",
                "metric_limits":"Literal checks are not semantic accuracy. Human metrics remain null until reviewed. p95 needs >=20 successful latency samples.",
                "resource_measurement":"M4 records torch process peak allocated VRAM per generation; not whole-GPU usage or incremental request cost. Other methods: unavailable.","status":"running"}
    write_json(directory / "manifest.json", manifest)
    rows = []
    with (directory / "results.jsonl").open("x",encoding="utf-8") as results, (directory / "review_template.jsonl").open("x",encoding="utf-8") as review:
        for method in args.methods:
            for repeat in range(1,args.repeats+1):
                for case in cases:
                    work = directory / f"{method}-{repeat}-{case.id}"
                    work.mkdir()
                    request = {"method":method,"case":case.model_dump(),"corpus":str(corpus),
                               "database":str(work / "isolated.db"),"timeout":args.timeout,
                               "snapshot_timestamp":args.snapshot_timestamp,
                               "ollama_url":args.ollama_url,"hf_url":args.hf_url,"plain_prompt":plain_prompt}
                    write_json(work / "request.json", request)
                    started = time.perf_counter()
                    env = {**os.environ,"PYTHONDONTWRITEBYTECODE":"1","PYTHONIOENCODING":"utf-8",
                           "ENVIRONMENT":"test","WARM_AI_ON_STARTUP":"false"}
                    try:
                        proc = subprocess.run([sys.executable,"-B","-m","benchmark.worker",str(work/"request.json"),str(work/"response.json")],
                                              cwd=ROOT, env=env, capture_output=True,timeout=args.timeout)
                        (work / "worker.log").write_bytes(proc.stdout + b"\n" + proc.stderr)
                        if proc.returncode or not (work/"response.json").exists():
                            raise RuntimeError(f"Worker exited {proc.returncode}; see worker.log")
                        result = json.loads((work/"response.json").read_text(encoding="utf-8"))
                    except subprocess.TimeoutExpired as exc:
                        (work / "worker.log").write_bytes((exc.stdout or b"")+b"\n"+(exc.stderr or b""))
                        result = {"status":"timeout","answer":"","sources":[],"latency_ms":None,"error":{"type":"ProcessTimeout","message":"Whole-case deadline exceeded; worker terminated"}}
                    except Exception as exc:
                        result = {"status":"error","answer":"","sources":[],"latency_ms":None,"error":{"type":type(exc).__name__,"message":str(exc)}}
                    row = {**result,"run_id":run_id,"method":method,"case_id":case.id,"category":case.category,
                           "question":case.question,"repeat":repeat,"wall_ms":(time.perf_counter()-started)*1000,
                           "model":None if method_spec(method)["kind"]=="rules" else HF_LORA_MODEL if method_spec(method)["provider"]=="hf_lora" else BASELINE_CHAT_MODEL,
                           "architecture":method_spec(method),
                           "config_ref":"manifest.json","review_status":"unreviewed"}
                    row["objective"] = objective_checks(case.model_dump(), row)
                    rows.append(row)
                    results.write(json.dumps(row,ensure_ascii=False)+"\n"); results.flush()
                    review.write(HumanReview(run_id=run_id,method=method,case_id=case.id,repeat=repeat).model_dump_json()+"\n"); review.flush()
                    print(f"{method} {case.id} {row['status']} mode={row.get('mode')} llm={row.get('llm_called',False)}",flush=True)
    export_tables(directory, rows)
    manifest.update(status="completed",finished_utc=datetime.now(timezone.utc).isoformat(),rows=len(rows))
    write_json(directory / "manifest.json", manifest)
    print(directory,flush=True)
    if any(row["status"] in {"error","timeout","not_ready"} for row in rows):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
