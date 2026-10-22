"""Freeze the approved 24-case package, execute controlled runs, and export Chapter 5 tables."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import shutil
import sqlite3
import statistics
import subprocess
import sys
from uuid import uuid4

from app.config import BASELINE_CHAT_MODEL
from benchmark.protocol import ABLATIONS, METHOD_NAMES, method_spec
from benchmark.run import CORPUS_FILES, ROOT, digest, write_json
from benchmark.schema import Case

MAIN = ["B0", "B1", "B2", "P"]
SMOKE_IDS = ["TC05", "TC11", "TC23"]
ERRORS = {"error", "timeout", "not_ready"}


def jsonl(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8-sig").splitlines() if s.strip()]


def code_hashes():
    return {str(p.relative_to(ROOT)):digest(p)
            for d in [ROOT/"app", ROOT/"benchmark", ROOT/"model_serving"]
            for p in sorted(d.rglob("*.py"))}


def validate_package(package):
    inputs, keys = jsonl(package/"test_inputs.jsonl"), jsonl(package/"answer_key.jsonl")
    manifest = json.loads((package/"manifest.json").read_text(encoding="utf-8-sig"))
    if len(inputs) != 24 or len(keys) != 24 or len({r["case_id"] for r in inputs}) != 24:
        raise ValueError("Expected exactly 24 unique input/key rows")
    fields = ("case_id", "group", "family_id", "question", "history")
    if any({k:r[k] for k in fields} != {k:t[k] for k in fields} for r,t in zip(inputs, keys)):
        raise ValueError("Input and answer key order/content do not agree")
    sources = {}
    for name, expected in manifest["sources"].items():
        source = package/"sources"/name
        if digest(source) != expected:
            raise ValueError(f"Package source hash mismatch: {name}")
        sources[name] = json.loads(source.read_text(encoding="utf-8-sig"))
    for row in keys:
        if not row["required_criteria"] or not row["source_refs"]:
            raise ValueError(f"Missing criteria/source evidence: {row['case_id']}")
        for ref in row["source_refs"]:
            path, selector = ref.split("#")
            source = sources[Path(path).name]
            field,value = selector.split("=",1)
            records = source if field == "slug" else source["faqs"]
            key = "slug" if field == "slug" else "id"
            if sum(r.get(key) == value for r in records) != 1:
                raise ValueError(f"Unresolved/ambiguous source reference: {ref}")
    return inputs, keys, manifest


def adapt_inputs(inputs):
    # Never place reference answers, source labels or scoring criteria in worker inputs.
    return [Case(id=r["case_id"],category=r["group"],question=r["question"],
                 history=r["history"],family_id=r["family_id"]).model_dump() for r in inputs]


def prepare(package, study, approval):
    inputs, keys, original_manifest = validate_package(package)
    confirmation = json.loads(approval.read_text(encoding="utf-8"))["approval"]
    if not confirmation.get("text") or not confirmation.get("source"):
        raise ValueError("A recorded user approval is required; original package is marked unreviewed")
    # Stop before authoring a snapshot if its truth differs from the approved package.
    equivalence = {}
    for name in original_manifest["sources"]:
        a,b = package/"sources"/name, ROOT/"rag_data"/name
        same = json.loads(a.read_text(encoding="utf-8-sig")) == json.loads(b.read_text(encoding="utf-8-sig"))
        equivalence[name] = {"json_content_equal":same,"byte_equal":a.read_bytes()==b.read_bytes(),
                            "line_ending_normalized_equal":a.read_bytes().replace(b"\r\n",b"\n")==b.read_bytes().replace(b"\r\n",b"\n")}
        if not same:
            raise ValueError(f"Knowledge data differs from approved truth: {name}; review/version required")
    study.mkdir(parents=True, exist_ok=False)
    shutil.copytree(package,study/"package")
    corpus = study/"corpus"; corpus.mkdir()
    for name in CORPUS_FILES:
        shutil.copyfile(ROOT/"rag_data"/name,corpus/name)
    for name in original_manifest["sources"]:
        shutil.copyfile(package/"sources"/name,corpus/name)
    write_json(study/"inputs.adapter.json", {"version":"approved24-schema-adapter-v1", "cases":adapt_inputs(inputs)})
    snapshot_timestamp=datetime.now(timezone.utc).isoformat()
    protocol = {"version":"chapter5-approved24-v3", "created_utc":snapshot_timestamp,
        "chat_model":BASELINE_CHAT_MODEL,
        "snapshot_timestamp":snapshot_timestamp,
        "timestamp_role":"Technical database snapshot creation time, identical across workers; not manufacturer verification time or a new business fact.",
        "approval":confirmation,"original_manifest":original_manifest,"source_equivalence":equivalence,
        "original_package":str(package),"package_sha256":{str(p.relative_to(study/"package")):digest(p) for p in (study/"package").rglob("*") if p.is_file()},
        "adapted_inputs_sha256":digest(study/"inputs.adapter.json"),
        "corpus_sha256":{p.name:digest(p) for p in corpus.iterdir()},"code_sha256":code_hashes(),
        "neutral_prompt_sha256":digest(ROOT/"benchmark/prompts/plain.txt"),
        "methods":{m:method_spec(m) for m in MAIN+["P+FT"]+list(ABLATIONS)},
        "smoke_ids":SMOKE_IDS,"case_order":[r["case_id"] for r in inputs],
        "counts":{"cases":24,"single_turn":20,"fixed_history":4,"families":len({r['family_id'] for r in inputs})},
        "retrieval":{"top_k":5,"threshold":0.38,"hybrid_vector_weight":0.60,"bm25_weight":0.40,"bm25_scale":3},
        "generation":{"temperature":0,"num_ctx":4096,"num_predict":384,"repeat_penalty":1},
        "scope":"Approved small pilot; authorship/independence not established by approval. Fixed supplied history, score final turn only.",
        "semantic_review":"NOT_REVIEWED; human 0-2 rubric, two independent blinded reviewers required",
        "P_FT_limits":"Historical supplementary 7B QLoRA NF4/BF16 is not part of the original-weight 7B main comparison. Weights, precision and runtime differ; no isolated fine-tuning causal claim.",
        "warmup":"Three disclosed smoke cases per method before full runs; no balanced discarded warm-up. Desktop/background GPU load is uncontrolled.",
        "retrieval_metrics":"Recall/MRR NOT_REVIEWED: package labels logical source records, not exhaustive relevant chunk IDs.",
        "interactions":["Disabling BM25 retains 0.60 vector weight and threshold; no re-normalization.",
                        "Routing can bypass retrieval/postcheck; disabled components may not be reached on some cases.",
                        "Product-context ablation removes structured current/history/page resolution, history recommendation/budget state, priority/context injection; catalog truth, generic history and direct rules remain.",
                        "No-rule variant disables direct catalog/FAQ/intent responses; retrieval admission, context filtering and postcheck remain.",
                        "Query-normalization ablation disables QueryRewriter only; BM25 tokenization and intent folding remain.",
                        "Latency cold/warm state and desktop load are not fully controlled; one 24-case pass is exploratory."]}
    write_json(study/"protocol.json",protocol)
    for rel in protocol["code_sha256"]:
        target=study/"code_snapshot"/rel; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/rel,target)
    print(study,flush=True)


def verify_study(study):
    protocol=json.loads((study/"protocol.json").read_text(encoding="utf-8"))
    checks={"code":code_hashes()==protocol["code_sha256"],
            "inputs":digest(study/"inputs.adapter.json")==protocol["adapted_inputs_sha256"],
            "neutral_prompt":digest(ROOT/"benchmark/prompts/plain.txt")==protocol["neutral_prompt_sha256"],
            "corpus":all(digest(study/"corpus"/p)==h for p,h in protocol["corpus_sha256"].items()),
            "package":all(digest(study/"package"/p)==h for p,h in protocol["package_sha256"].items())}
    if not all(checks.values()):
        raise ValueError(f"Frozen study changed: {checks}. Create a new version; rerun affected methods.")
    return protocol


def validate_rows(study, rows, directory=None):
    expected={r["case_id"]:r for r in jsonl(study/"package/test_inputs.jsonl")}
    protocol=json.loads((study/"protocol.json").read_text(encoding="utf-8"))
    products=json.loads((study/"corpus/techcare_products.json").read_text(encoding="utf-8"))
    expected_products={r["slug"]:(float(r["price"]),r["warranty_months"],r["specifications"]) for r in products}
    stamp=datetime.fromisoformat(protocol["snapshot_timestamp"]).astimezone(timezone.utc).replace(tzinfo=None).isoformat(sep=" ",timespec="microseconds")
    diagnostics=[]
    for row in rows:
        case=expected[row["case_id"]]; method=row["method"]; spec=method_spec(method)
        checks={"input_question":row["question"]==case["question"],
                "fixed_history":row.get("history")==case["history"],
                "architecture":row.get("architecture")==spec,
                "no_system_error":row["status"] not in ERRORS}
        checks["snapshot_timestamp"]=row.get("snapshot_timestamp")==protocol["snapshot_timestamp"]
        if directory is not None and spec["kind"]!="plain":
            database=directory/f"{method}-{row['repeat']}-{row['case_id']}"/"isolated.db"
            if database.exists():
                with sqlite3.connect(database.as_uri()+"?mode=ro",uri=True) as db:
                    dates=db.execute("SELECT DISTINCT created_at, updated_at FROM products").fetchall()
                    actual=db.execute("SELECT slug, price, warranty_months, specifications FROM products").fetchall()
                checks["database_fixed_timestamps"]=dates==[(stamp,stamp)]
                checks["database_product_truth"]={s:(float(p),w,json.loads(j)) for s,p,w,j in actual}==expected_products
            else:
                checks["database_product_truth"]=False
        if row["status"] not in ERRORS:
            if spec["kind"]=="rules": checks["no_llm"]=not row.get("calls")
            elif spec["kind"]=="plain":
                checks.update(no_rag=not row["sources"] and not row.get("retrieval_traces"),
                              one_final_call=len(row.get("calls",[]))==1)
            elif spec["kind"]=="basic_rag":
                checks.update(one_final_call=len(row.get("calls",[]))==1,
                              semantic_only=bool(row.get("retrieval_traces")) and all(not t["bm25_enabled"] and not t["domain_ranking_enabled"] for t in row["retrieval_traces"]))
            if spec["kind"]!="rules":
                checks["model"]=row.get("identity",{}).get("model")==("qwen2.5-7b-finetuned" if spec["provider"]=="hf_lora" else protocol.get("chat_model", "qwen2.5:3b"))
            if spec["kind"]=="proposed":
                for trace in row.get("retrieval_traces",[]):
                    checks["trace_bm25"]=trace["bm25_enabled"]==spec["components"]["bm25"]
                    checks["trace_ranking"]=trace["domain_ranking_enabled"]==spec["components"]["domain_ranking"]
                    if not spec["components"]["query_normalization"]:
                        checks["trace_query"]=trace["semantic_query"]==trace["question"]
                for trace in row.get("architecture_traces",[]):
                    component="postcheck" if trace["stage"]=="postcheck" else "product_context"
                    checks["trace_"+component]=trace["enabled"]==spec["components"][component]
                if not spec["components"]["rule_routing"]:
                    checks["direct_routes_disabled"]=row.get("mode") not in {"rule+rag","faq","clarification"}
        diagnostics.append({"method":method,"case_id":row["case_id"],"checks":checks,"passed":all(checks.values())})
    return diagnostics


def run(study, phase, methods, timeout):
    protocol=verify_study(study)
    allowed=set(MAIN) if phase=="main" else set(["P"]+list(ABLATIONS)) if phase=="ablation" else {"P+FT"} if phase=="supplementary" else set(protocol["methods"])
    if not set(methods).issubset(allowed): raise ValueError(f"Invalid methods for {phase}")
    if phase!="smoke":
        passed=set()
        for p in (study/"runs/smoke").glob("*/protocol_validation.json"):
            diagnostics=json.loads(p.read_text(encoding="utf-8"))
            for method in methods:
                found=[r for r in diagnostics if r["method"]==method]
                if {r["case_id"] for r in found}==set(SMOKE_IDS) and all(r["passed"] for r in found): passed.add(method)
        if passed!=set(methods): raise ValueError(f"Missing passing smoke checks: {set(methods)-passed}")
    output=study/"runs"/phase; before=set(output.glob("*"))
    command=[sys.executable,"-B","-m","benchmark.run","--dataset",str(study/"inputs.adapter.json"),
             "--corpus",str(study/"corpus"),"--study-manifest",str(study/"protocol.json"),
             "--snapshot-timestamp",protocol["snapshot_timestamp"],
             "--dataset-role",protocol["scope"],"--methods",*methods,"--timeout",str(timeout),"--output-root",str(output)]
    if phase=="smoke": command.extend(["--case-ids",*SMOKE_IDS])
    logs=study/"logs"; logs.mkdir(exist_ok=True)
    log=logs/(phase+"-"+uuid4().hex[:8]+".log")
    with log.open("x",encoding="utf-8") as stream:
        proc=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8")
        for line in proc.stdout:
            stream.write(line); stream.flush(); print(line,end="",flush=True)
        code=proc.wait()
    new=set(output.glob("*"))-before
    if len(new)!=1: raise RuntimeError("Could not identify exactly one new run")
    directory=new.pop()
    diagnostics=validate_rows(study,jsonl(directory/"results.jsonl"),directory)
    write_json(directory/"protocol_validation.json",diagnostics)
    verify_study(study)
    if code or not all(r["passed"] for r in diagnostics): raise SystemExit(code or 2)


def collect(study):
    verify_study(study)
    all_rows=[]; entries=[]
    for phase in ("main","ablation","supplementary"):
        for directory in sorted((study/"runs"/phase).glob("*")):
            if not (directory/"summary.json").exists(): continue
            manifest=json.loads((directory/"manifest.json").read_text(encoding="utf-8"))
            if manifest["study_manifest_sha256"]!=digest(study/"protocol.json"): raise ValueError("Mixed protocol versions")
            rows=jsonl(directory/"results.jsonl")
            for summary in json.loads((directory/"summary.json").read_text(encoding="utf-8")):
                group=[r for r in rows if r["method"]==summary["method"]]
                times=[r["latency_ms"] for r in group if r["status"] not in ERRORS and r.get("latency_ms") is not None]
                mode_stats={}
                for mode in {r.get("mode") for r in group}:
                    values=[r["latency_ms"] for r in group if r.get("mode")==mode and r["status"] not in ERRORS and r.get("latency_ms") is not None]
                    mode_stats[str(mode)]={"samples":len(values),"median_ms":statistics.median(values) if values else None,
                                           "mean_ms":statistics.mean(values) if values else None}
                entries.append({"phase":phase,"run_id":manifest["run_id"],"run_path":str(directory),
                    **{k:v for k,v in summary.items() if k!="human"},"mode_counts":dict(Counter(r.get("mode") for r in group)),
                    "mean_ms":statistics.mean(times) if times else None,"latency_by_mode":mode_stats,
                    "retrieval_exposed_cases":sum(bool(r.get("retrieval_traces")) for r in group),
                    "postcheck_reached_cases":sum(any(t["stage"]=="postcheck" for t in r.get("architecture_traces",[])) for r in group),
                    "method_status":"PASS" if len(group)==24 and not any(r["status"] in ERRORS for r in group) else "FAIL",
                    "semantic_status":"NOT_REVIEWED","full_2_point_rate":None,"mean_score_0_2":None,
                    "unsupported_claim_rate":None,"recall_at_5":None,"mrr":None,"score_denominator":24,
                    "model_identities":list({json.dumps(r.get("identity"),sort_keys=True) for r in group})})
            all_rows.extend(rows)
    destination=study/("analysis-"+uuid4().hex[:8]); destination.mkdir()
    main_p=next((e for e in entries if e["phase"]=="main" and e["method"]=="P"),None)
    ablation_p=next((e for e in entries if e["phase"]=="ablation" and e["method"]=="P"),None)
    for entry in entries:
        control=ablation_p if entry["phase"]=="ablation" else main_p
        entry["delta_median_ms_vs_P"]=entry["median_ms"]-control["median_ms"] if control and entry["median_ms"] is not None else None
        entry["delta_llm_cases_vs_P"]=entry["llm_called_cases"]-control["llm_called_cases"] if control else None
        entry["delta_mean_score_vs_P"]=None
    write_json(destination/"tables.json",entries)
    import csv
    with (destination/"tables.csv").open("x",encoding="utf-8-sig",newline="") as f:
        fields=["phase","method","method_status","attempts","statuses","llm_called_cases","retrieval_exposed_cases","postcheck_reached_cases","median_ms","mean_ms","p95_ms","error_timeout_rate","not_ready_rate","semantic_status","full_2_point_rate","mean_score_0_2","unsupported_claim_rate","score_denominator","delta_median_ms_vs_P","delta_llm_cases_vs_P","delta_mean_score_vs_P","run_id"]
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
        for row in entries: writer.writerow({k:json.dumps(row.get(k),ensure_ascii=False) if isinstance(row.get(k),dict) else row.get(k) for k in fields})
    keys={r["case_id"]:r for r in jsonl(study/"package/answer_key.jsonl")}
    blinded=[]; mapping=[]
    for row in all_rows:
        blind=uuid4().hex[:16]; key=keys[row["case_id"]]
        blinded.append({"blind_id":blind,"case_id":row["case_id"],"group":row["category"],
            "question":row["question"],"history":row.get("history"),"answer":row["answer"],
            "sources":row["sources"],"system_status":row["status"],"error":row.get("error"),
            **{k:key[k] for k in ("reference_answer","required_criteria","source_refs","critical_errors")},
            "reviewer":None,"score_0_2":None,"unsupported_claim":None,"notes":None})
        mapping.append({"blind_id":blind,**{k:row[k] for k in ("run_id","method","case_id","repeat")}})
    random.Random(20261015).shuffle(blinded)
    with (destination/"blinded_review_template.jsonl").open("x",encoding="utf-8") as f:
        for item in blinded: f.write(json.dumps(item,ensure_ascii=False)+"\n")
    with (destination/"blinded_review_template.csv").open("x",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(blinded[0]) if blinded else ["blind_id"])
        writer.writeheader()
        for item in blinded:
            writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in item.items()})
    write_json(destination/"review_mapping_private.json",mapping)
    write_json(destination/"collection.json",{"created_utc":datetime.now(timezone.utc).isoformat(),"rows":len(all_rows),
        "semantic_status":"NOT_REVIEWED","rubric":"0/1/2; errors count 0 when reviewed; 2 independent blinded reviewers; no automatic keyword scoring",
        "latency_delta":"variant median minus P median in the same ablation batch; descriptive, not causal",
        "limits":"24 cases / 23 families, fixed supplied history. No semantic scores or retrieval qrels inferred from source presence."})
    print(destination,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__); commands=parser.add_subparsers(dest="command",required=True)
    p=commands.add_parser("prepare"); p.add_argument("--package",type=Path,required=True); p.add_argument("--study",type=Path,required=True); p.add_argument("--approval-record",type=Path,required=True)
    p=commands.add_parser("run"); p.add_argument("--study",type=Path,required=True); p.add_argument("--phase",choices=["smoke","main","ablation","supplementary"],required=True); p.add_argument("--methods",nargs="+",choices=METHOD_NAMES,required=True); p.add_argument("--timeout",type=float,default=60)
    p=commands.add_parser("collect"); p.add_argument("--study",type=Path,required=True)
    args=parser.parse_args(); args.study=args.study.resolve()
    if args.command=="prepare": prepare(args.package.resolve(),args.study,args.approval_record.resolve())
    elif args.command=="run": run(args.study,args.phase,args.methods,args.timeout)
    else: collect(args.study)


if __name__=="__main__": main()
