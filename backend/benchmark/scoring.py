"""Literal objective checks plus separately denominated human judgments; no semantic accuracy proxy."""
from collections import Counter
import math
import statistics
import unicodedata


def normalize(text):
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def objective_checks(case, result):
    if result["status"] not in {"ok", "no_rule_match"}:
        return {"evaluated":False, "all_literal_checks_passed":None}
    answer = normalize(result["answer"])
    required, forbidden = case.get("required_facts") or [], case.get("forbidden_claims") or []
    missing = [s for s in required if normalize(s) not in answer]
    found = [s for s in forbidden if normalize(s) in answer]
    ids = {source["id"] for source in result["sources"]}
    expected_ids = case.get("expected_source_ids") or []
    source_match = bool(ids.intersection(expected_ids)) if expected_ids else None
    if case.get("expected_source"):
        source_match = any(s.get("metadata", {}).get("source") == case["expected_source"] for s in result["sources"]) or bool(source_match)
    return {"evaluated":bool(required or forbidden or source_match is not None),
            "missing_literal_facts":missing, "forbidden_literal_matches":found,
            "expected_source_present":source_match,
            "all_literal_checks_passed":not missing and not found if required or forbidden else None,
            "interpretation":"Literal strings and citation presence only; human review required for correctness and grounding."}


def summarize(rows, reviews=()):
    out = []
    review_map = {(r["run_id"],r["method"],r["case_id"],r.get("repeat",1)):r for r in reviews}
    for method in sorted({r["method"] for r in rows}):
        group = [r for r in rows if r["method"] == method]
        answered = [r for r in group if r["status"] in {"ok", "no_rule_match"}]
        times = sorted(r["latency_ms"] for r in answered if r.get("latency_ms") is not None)
        literal = [r["objective"]["all_literal_checks_passed"] for r in answered if r["objective"].get("all_literal_checks_passed") is not None]
        citations = [r["objective"]["expected_source_present"] for r in answered if r["objective"].get("expected_source_present") is not None]
        statuses = Counter(r["status"] for r in group)
        reviewed = [review_map[(r["run_id"],method,r["case_id"],r["repeat"])] for r in answered
                    if (r["run_id"],method,r["case_id"],r["repeat"]) in review_map]
        human = {}
        correct = [r["correctness"] for r in reviewed if r.get("correctness") and r["correctness"] != "not_applicable"]
        human["correctness"] = {"counts":dict(Counter(correct)),"reviewed":len(correct),
                                 "correct_rate":correct.count("correct")/len(correct) if correct else None}
        for key in ("grounded","hallucination","policy_compliant","appropriate_abstention","correct_sources","relevant"):
            values = [r[key] for r in reviewed if r.get(key) is not None]
            human[key] = {"reviewed":len(values),"true_count":sum(values),"rate":sum(values)/len(values) if values else None}
        out.append({"method":method,"attempts":len(group),"answered":len(answered),"statuses":dict(statuses),
                    "error_timeout_rate":(statuses["error"]+statuses["timeout"])/len(group),
                    "not_ready_rate":statuses["not_ready"]/len(group),
                    "llm_called_cases":sum(bool(r.get("llm_called")) for r in group),
                    "literal_passes":sum(literal),"literal_evaluated":len(literal),
                    "expected_source_present":sum(citations),"source_evaluated":len(citations),
                    "latency_samples":len(times),"median_ms":statistics.median(times) if times else None,
                    "p95_ms":times[math.ceil(.95*len(times))-1] if len(times)>=20 else None,
                    "human":human})
    return out
