"""Verify the archived run and recompute latency without inference or a GPU."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import statistics
import sys


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def percentile(values, fraction):
    values = sorted(values)
    position = (len(values) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def timings(values):
    return {"n": len(values), "mean_ms": statistics.mean(values) if values else None,
            "median_ms": statistics.median(values) if values else None,
            "p95_ms": percentile(values, .95) if len(values) >= 20 else None}


def summarize(records):
    good = [r for r in records if r["result"]["status"] in ("ok", "no_rule_match")]
    return {"attempts": len(records),
            "statuses": dict(Counter(r["result"]["status"] for r in records)),
            "error_timeout_not_ready_rate": (len(records) - len(good)) / len(records),
            "final_llm_called_cases": sum(bool(r["result"].get("llm_called")) for r in records),
            "setup_llm_called_cases": sum(bool(r["result"].get("setup_llm_called")) for r in records),
            "retrieval_error_cases": sum(bool(r["result"].get("retrieval_errors")) for r in records),
            "final_pipeline_latency_successful": timings([r["result"]["latency_ms"] for r in good
                                                         if r["result"].get("latency_ms") is not None]),
            "whole_case_wall_successful": timings([r["wall_ms"] for r in good])}


def compare(actual, expected, name):
    if isinstance(expected, dict):
        require(set(actual) == set(expected), name + ": keys differ")
        for key in expected:
            compare(actual[key], expected[key], name + "." + key)
    elif isinstance(expected, float):
        require(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-6), name + ": differs")
    else:
        require(actual == expected, name + ": differs")


def verify_ratings(path, by_id):
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise ValueError("Optional ratings check needs: python -m pip install openpyxl") from exc
    sheet = load_workbook(path, data_only=False)["Phieu_cham"]
    seen = set()
    scores = []
    for row in range(9, 109):
        anonymous_id, case_id, history, question, answer, status = [sheet.cell(row, c).value for c in range(1, 7)]
        require(case_id in by_id and case_id not in seen, f"{path.name}: invalid/duplicate ID at row {row}")
        seen.add(case_id)
        record = by_id[case_id]
        expected_id = "K" + hashlib.sha256(("supplementary-20261104|" + case_id).encode()).hexdigest()[:12]
        expected_history = "\n\n".join(t["role"] + ": " + t["content"] for t in record["actual_history"])
        require((anonymous_id, question, answer or "", status, history or "") ==
                (expected_id, record["question"], record["result"].get("answer", ""),
                 record["result"]["status"], expected_history), f"{path.name}: content mismatch for {case_id}")
        score = sheet.cell(row, 8).value
        require(score is None or (not isinstance(score, bool) and score in (0, 1, 2)), f"{case_id}: invalid score")
        scores.append(score)
    return {"file": path.name, "sha256": sha256(path), "matched_cases": len(seen),
            "score_counts": dict(Counter("blank" if v is None else str(v) for v in scores))}


def verify(root, ratings):
    bundle = read_json(root / "bundle_manifest.json")
    for item in bundle["files"] + bundle.get("package_helpers", []):
        path = (root / item["path"]).resolve()
        require(path.is_relative_to(root), "Unsafe inventory path")
        require(path.stat().st_size == item["bytes"] and sha256(path) == item["sha256"],
                "Integrity mismatch: " + item["path"])
    context = read_json(root / "context.json")
    main = root / "runs/main"
    manifest = read_json(main / "manifest.json")
    health = read_json(main / "runtime_health.json")
    require(manifest["status"] == "completed" and manifest["rows"] == 100, "Incomplete run")
    require(health["status"] == "ready" and health["adapter_loaded"], "Adapter was not ready")
    for key, value in context["supplementary_identity"].items():
        require(health[key] == value, "Model identity mismatch: " + key)
    require(sha256(root / "test_inputs.json") == context["test_input_sha256"], "Input hash mismatch")
    require(sha256(root / "frozen_products.db") == context["database_sha256"], "Database hash mismatch")
    require(sha256(root / "plain_prompt.txt") == context["plain_prompt_sha256"], "Prompt hash mismatch")
    for name, digest in context["corpus_sha256"].items():
        require(sha256(root / "corpus" / name) == digest, "Corpus mismatch: " + name)
    snapshot = root / "source_snapshot/HT_model7B/backend"
    for name, digest in {**context["code_sha256"], **context["harness_sha256"]}.items():
        require(sha256(snapshot / name.replace("\\", "/")) == digest, "Code mismatch: " + name)
    for key, name in (("parent", "run_pft.py"), ("worker", "worker_pft.py")):
        require(sha256(root / name) == manifest["harness_sha256"][key], "Collector mismatch: " + name)
    cases = read_json(root / "test_inputs.json")["cases"]
    require({c["id"]: c for c in cases} == context["test_cases"], "Input cases differ from context")
    records = [json.loads(line) for line in (main / "results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    by_id = {r["case_id"]: r for r in records}
    require(len(records) == len(by_id) == 100 and set(by_id) == set(context["test_cases"]), "Wrong case set")
    verified_calls = history_pairs = prompt_calls = 0
    for record in records:
        case_id = record["case_id"]
        case = context["test_cases"][case_id]
        folder = main / case_id
        result = record["result"]
        require(read_json(folder / "record.json") == record, case_id + ": record differs")
        require(read_json(folder / "response.json") == result, case_id + ": response differs")
        require(read_json(folder / "request.json")["case"] == case, case_id + ": request differs")
        require(record["question"] == case["question"] and record["history_questions"] == case["history_questions"], case_id + ": input differs")
        history = record["actual_history"]
        require([t["role"] for t in history] == ["user", "assistant"] * len(case["history_questions"]), case_id + ": roles differ")
        for index, question in enumerate(case["history_questions"], 1):
            step = read_json(folder / f"setup-{index:02}-completed.json")
            require(history[2 * index - 2] == {"role": "user", "content": question} and
                    history[2 * index - 1] == {"role": "assistant", "content": step["answer"]}, case_id + ": setup differs")
            history_pairs += 1
        for call in result.get("calls", []):
            require(call["generation"] == manifest["generation"], case_id + ": generation differs")
            prompt_calls += int(call.get("system_prompt") is not None and call.get("user_prompt") is not None)
            if call.get("generation_evidence"):
                for key in ("model", "adapter_sha256", "checkpoint_sha256"):
                    require(call["generation_evidence"][key] == health[key], case_id + ": generation identity differs")
                verified_calls += 1
    with (main / "results.csv").open(encoding="utf-8-sig", newline="") as stream:
        csv_rows = list(csv.DictReader(stream))
    require(len(csv_rows) == 100, "CSV row count differs")
    for row in csv_rows:
        record = by_id[row["case_id"]]
        require((row["question"], row["answer"], row["status"], json.loads(row["history"])) ==
                (record["question"], record["result"].get("answer", ""), record["result"]["status"], record["actual_history"]), "CSV differs: " + row["case_id"])
    db = sqlite3.connect((root / "frozen_products.db").as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        require(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLite integrity failure")
        counts = {name: db.execute('SELECT COUNT(*) FROM "' + name + '"').fetchone()[0]
                  for name in ("products", "admins", "chat_messages", "chat_sessions", "tickets", "faqs")}
        require(counts["products"] == 150 and sum(v for k, v in counts.items() if k != "products") == 0, "Unexpected snapshot rows")
    finally:
        db.close()
    controls = [json.loads(line) for line in (root / "controls_400.original.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    control = {r["case_id"]: r for r in controls if r["method"] == "P"}
    require(set(control) == set(by_id), "P control case set differs")
    for case_id in by_id:
        require(control[case_id]["question"] == by_id[case_id]["question"] and control[case_id]["history_questions"] == by_id[case_id]["history_questions"], case_id + ": P input differs")
    saved = read_json(root / "published/statistics.json")
    calculated = summarize(records)
    compare(calculated, saved["P_FT"], "P_FT")
    compare(summarize(list(control.values())), saved["P_control"], "P_control")
    common = [key for key in by_id if by_id[key]["result"]["status"] in ("ok", "no_rule_match")
              and control[key]["result"]["status"] in ("ok", "no_rule_match")]
    common_llm = [key for key in common if by_id[key]["result"].get("llm_called") and control[key]["result"].get("llm_called")]
    for label, keys in (("paired_completed", common), ("paired_final_llm_completed", common_llm)):
        compare(summarize([by_id[k] for k in keys]), saved[label]["P_FT"], label + ".P_FT")
        compare(summarize([control[k] for k in keys]), saved[label]["P_control"], label + ".P_control")
    diagnostic = read_json(root / "S47_context_diagnostic.json")
    require(diagnostic["source_error"] == by_id["S47"]["result"]["error"], "S47 diagnostic differs")
    return {"verified": True, "bundle_id": bundle["bundle_id"], "source_git_head": bundle["source_git_head"],
            "case_groups": dict(Counter(c["id"][0] for c in cases)), "model": health,
            "successful_generations_with_identity": verified_calls, "logged_prompt_calls": prompt_calls,
            "verified_setup_history_pairs": history_pairs, "P_FT": calculated,
            "paired_completed_cases": len(common), "paired_final_llm_completed_cases": len(common_llm),
            "S47": diagnostic, "ratings": [verify_ratings(p, by_id) for p in ratings],
            "latency_definition": "Successful final pipeline only; setup excluded. Whole-case wall includes setup. p95 linear interpolation at (n-1)*0.95; omitted below 20 samples.",
            "quality_scores": "Not inferred. No regrading or kappa calculation in this script."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--ratings", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path, help="Optional NEW JSON file outside the evidence folder")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.out:
        require(not args.out.resolve().is_relative_to(root), "Write summaries outside the immutable bundle")
        require(not args.out.exists(), "Output already exists; refusing to overwrite")
    result = verify(root, args.ratings)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        with args.out.open("x", encoding="utf-8") as stream:
            stream.write(text)
    print(text)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        print("Verification failed: " + str(error), file=sys.stderr)
        sys.exit(2)
