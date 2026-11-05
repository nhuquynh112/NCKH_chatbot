"""Recompute operational results; paired human outcomes stay pending until rated."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import statistics

from controlled_study.prepare import load, sha, ARCHIVE
from controlled_study.run import verify_lock


def percentile(values, p):
    values = sorted(values)
    index = (len(values) - 1) * p
    lo = int(index)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (index - lo)


def describe(values):
    return {"n": len(values), "mean": statistics.mean(values) if values else None,
            "median": statistics.median(values) if values else None,
            "p95": percentile(values, .95) if len(values) >= 20 else None}


def successful(row):
    return row["result"]["status"] in ("ok", "no_rule_match")


def route(row):
    if row["result"].get("llm_called"):
        return "llm_attempt"
    if row["result"].get("mode") in ("rule+rag", "faq", "faq_rule", "rule"):
        return "rules_or_faq"
    return "other_without_llm"


def summary(rows):
    latencies = [r["result"]["latency_ms"] for r in rows if successful(r) and r["result"].get("latency_ms") is not None]
    calls = [c for r in rows for c in r["result"].get("calls", [])]
    final = [c for c in calls if c.get("phase") == "final"]
    generations = [c["generation_evidence"] for c in final if c.get("generation_evidence")]
    return {"attempts": len(rows), "statuses": dict(Counter(r["result"]["status"] for r in rows)),
            "error_rate": sum(not successful(r) for r in rows) / len(rows) if rows else None,
            "final_llm_attempted_cases": sum(bool(r["result"].get("llm_called")) for r in rows),
            "all_llm_request_attempts": len(calls), "final_llm_request_attempts": len(final),
            "successful_final_generations": len(generations),
            "final_generations_reaching_output_cap": sum(g.get("output_tokens", 0) >= c["generation"]["num_predict"]
                                                        for c in final if (g := c.get("generation_evidence"))),
            "input_tokens_successful_final_generations": sum(g.get("input_tokens", 0) for g in generations),
            "output_tokens_successful_final_generations": sum(g.get("output_tokens", 0) for g in generations),
            "final_pipeline_ms_successful": describe(latencies),
            "final_pipeline_ms_failed": describe([r["result"]["latency_ms"] for r in rows
                                                   if not successful(r) and r["result"].get("latency_ms") is not None]),
            "server_generation_ms_successful": describe([g["generation_ms"] for g in generations]),
            "whole_case_wall_ms_successful": describe([r["wall_ms"] for r in rows if successful(r)]),
            "whole_case_wall_ms_failed": describe([r["wall_ms"] for r in rows if not successful(r)]),
            "routes": dict(Counter(route(r) for r in rows)),
            "retrieval_error_cases": sum(bool(r["result"].get("retrieval_errors")) for r in rows)}


def paired_ci(differences, family_by_case):
    if not differences:
        return {"cases": 0, "difference_mean": None, "ci95": None}
    families = defaultdict(list)
    for case_id, difference in differences.items():
        families[family_by_case[case_id]].append(difference)
    keys = sorted(families)
    rng = random.Random(20261105)
    boot = []
    for _ in range(5000):
        values = [value for group in rng.choices(keys, k=len(keys)) for value in families[group]]
        boot.append(statistics.mean(values))
    return {"cases": len(differences), "families": len(keys),
            "difference_mean": statistics.mean(differences.values()),
            "ci95": [percentile(boot, .025), percentile(boot, .975)],
            "bootstrap_repetitions": 5000, "seed": 20261105,
            "unit": "paired case means across three repetitions, resampled by family"}


def analyze(root, allow_partial=False):
    lock = verify_lock(root)
    inventory_path = root / "evidence_inventory.json"
    if inventory_path.exists():
        for name, expected in load(inventory_path)["files"].items():
            path = (root / name).resolve()
            if not path.is_relative_to(root) or not path.is_file() or sha(path) != expected["sha256"]:
                raise ValueError("Public evidence differs from its inventory: " + name)
    manifest = load(root / "runs/manifest.json")
    if not allow_partial and manifest["status"] != "completed":
        raise ValueError("Collection incomplete; use --allow-partial only for labeled monitoring")
    records = [json.loads(line) for line in (root / "runs/results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    by_key = {(r["repeat"], r["configuration"], r["phase"], r["case_id"]): r for r in records}
    if len(by_key) != len(records):
        raise ValueError("Duplicate observation IDs")
    protocol = load(root / "protocol.json")
    cases = {r["id"]: r for r in load(root / "cases.json")["cases"]}
    expected_embedding = load(ARCHIVE / "context.json")["expected_identity"]["embedding_identity"]["digest"]
    environments = set()
    embedding_digests = set()
    generation_gpus = set()
    groups = defaultdict(list)
    repeated = defaultdict(list)
    for row in records:
        repeat, label, phase, case_id = row["repeat"], row["configuration"], row["phase"], row["case_id"]
        if not 1 <= repeat <= 3 or label not in protocol["conditions"] or case_id not in cases:
            raise ValueError("Unexpected observation")
        if phase not in ("fixed", "rollout") or (phase == "rollout" and
                (label not in protocol["rollout_conditions"] or case_id not in protocol["rollout_case_ids"])):
            raise ValueError("Unregistered phase/rollout observation")
        folder = root / "runs" / f"r{repeat}" / label / phase / case_id
        if load(folder / "record.json") != row:
            raise ValueError("Record differs from JSONL")
        request = load(folder / "request.json")
        spec = protocol["conditions"][label]
        if request["method"] != spec["method"] or request["condition"] != spec["adapter"]:
            raise ValueError("Request method/adapter differs from registration")
        identity = row["result"].get("identity")
        if successful(row) and not identity:
            raise ValueError("Successful observation has no actual runtime identity")
        if identity:
            wanted_adapter = lock["model_profile"]["adapter_sha256"] if spec["adapter"] == "ft" else None
            if (identity.get("condition") != spec["adapter"]
                    or identity.get("adapter_loaded") != (spec["adapter"] == "ft")
                    or identity.get("adapter_sha256") != wanted_adapter
                    or identity.get("checkpoint_sha256") != lock["model_profile"]["checkpoint_sha256"]
                    or identity.get("quantization") != "NF4/BF16"):
                raise ValueError("Actual model identity differs from registration")
            environments.add(json.dumps(identity.get("packages"), sort_keys=True))
            embedding = identity.get("embedding_identity")
            if embedding:
                embedding_digests.add(embedding.get("digest"))
                if embedding.get("digest") != expected_embedding:
                    raise ValueError("Embedding identity differs from source vector snapshot")
        case = cases[case_id]
        expected_history = case["history"] if phase == "fixed" else []
        expected_setup = case["history_questions"] if phase == "fixed" else case["rollout_questions"]
        if (request["case"]["history"] != expected_history or request["case"]["question"] != case["question"]
                or request["case"]["history_questions"] != expected_setup):
            raise ValueError("Input history/question differs from registration")
        if successful(row):
            actual_history = row["result"]["history"]
            if phase == "fixed" and actual_history != expected_history:
                raise ValueError("Actual fixed input history differs")
            if phase == "rollout" and (len(actual_history) != 2 * len(expected_setup)
                    or any(actual_history[2*i] != {"role": "user", "content": question}
                           or actual_history[2*i+1].get("role") != "assistant"
                           for i, question in enumerate(expected_setup))):
                raise ValueError("Rollout history roles/setup differ")
        for call in row["result"].get("calls", []):
            if call.get("generation") != protocol["generation"]:
                raise ValueError("Generation differs from registration")
            evidence = call.get("generation_evidence")
            if evidence:
                wanted_adapter = lock["model_profile"]["adapter_sha256"] if spec["adapter"] == "ft" else None
                if (evidence.get("condition") != spec["adapter"]
                        or evidence.get("adapter_loaded") != (spec["adapter"] == "ft")
                        or evidence.get("adapter_sha256") != wanted_adapter
                        or evidence.get("checkpoint_sha256") != lock["model_profile"]["checkpoint_sha256"]
                        or evidence.get("quantization") != "NF4/BF16"):
                    raise ValueError("Actual generation artifact/condition differs")
                generation_gpus.add(evidence.get("gpu"))
        groups[(label, phase, repeat)].append(row)
        if phase == "fixed":
            repeated[(label, case_id)].append(row)
    fixed = [r for r in records if r["phase"] == "fixed"]
    rollout = [r for r in records if r["phase"] == "rollout"]
    if not allow_partial and (len(fixed) != 1080 or len(rollout) != 48):
        raise ValueError("Wrong number of registered observations")
    variation = []
    for (label, case_id), rows in repeated.items():
        identities = {(r["result"]["status"], r["result"].get("answer", "")) for r in rows}
        if len(identities) > 1:
            variation.append({"configuration": label, "case_id": case_id, "unique_status_answers": len(identities)})
    prompt_checks = []
    non_llm_adapter_answer_mismatches = []
    for repeat in range(1, 4):
        for case_id in cases:
            a = by_key.get((repeat, "P_base", "fixed", case_id))
            b = by_key.get((repeat, "P_ft", "fixed", case_id))
            if not a or not b:
                continue
            def prompts(row):
                return [(c.get("system_prompt"), c.get("user_prompt"), c.get("generation"))
                        for c in row["result"].get("calls", []) if c.get("phase") == "final"]
            if not prompts(a) and not prompts(b) and a["result"].get("answer", "") != b["result"].get("answer", ""):
                non_llm_adapter_answer_mismatches.append({"repeat": repeat, "case_id": case_id})
            prompt_checks.append({"repeat": repeat, "case_id": case_id, "same": prompts(a) == prompts(b),
                                  "base_calls": len(prompts(a)), "ft_calls": len(prompts(b))})
    family = {key: value["family"] for key, value in cases.items()}
    comparisons = {}
    for left, right in (("P_base", "P_ft"), ("P_base", "B1_base"), ("P_base", "B2_base"),
                        ("P_base", "P_no_memory"), ("P_base", "P_no_rules")):
        differences = {}
        llm_differences = {}
        cost = {}
        for case_id in cases:
            a = [by_key.get((rep, left, "fixed", case_id)) for rep in range(1, 4)]
            b = [by_key.get((rep, right, "fixed", case_id)) for rep in range(1, 4)]
            if all(a) and all(b):
                cost[case_id] = statistics.mean(len(r["result"].get("calls", [])) for r in b) - statistics.mean(len(r["result"].get("calls", [])) for r in a)
                if all(successful(r) and r["result"].get("latency_ms") is not None for r in a + b):
                    differences[case_id] = statistics.mean(r["result"]["latency_ms"] for r in b) - statistics.mean(r["result"]["latency_ms"] for r in a)
                    if all(r["result"].get("llm_called") for r in a + b):
                        llm_differences[case_id] = differences[case_id]
        comparisons[right + " minus " + left] = {"final_pipeline_ms": paired_ci(differences, family),
                                                 "llm_request_attempts": paired_ci(cost, family),
                                                 "final_pipeline_ms_both_call_llm_all_three": paired_ci(llm_differences, family),
                                                 "latency_cases_without_complete_successful_pairs": len(cases) - len(differences),
                                                 "quality_and_human_hypothesis_labels": "pending"}
    return {"study_status": manifest["status"], "source_lock_sha256": sha(root / "lock.json"),
            "record_count": len(records), "fixed_attempts": len(fixed), "rollout_attempts": len(rollout),
            "runtime_package_sets": [json.loads(value) for value in sorted(environments)],
            "same_runtime_packages": len(environments) == 1,
            "embedding_digests": sorted(embedding_digests), "expected_embedding_digest": expected_embedding,
            "generation_gpus": sorted(generation_gpus),
            "error_observations": [{"repeat": r["repeat"], "configuration": r["configuration"],
                                    "phase": r["phase"], "case_id": r["case_id"],
                                    "status": r["result"]["status"], "error": r["result"].get("error")}
                                   for r in records if not successful(r)],
            "by_configuration_phase_repeat": [{"configuration": key[0], "phase": key[1], "repeat": key[2], **summary(rows)}
                                              for key, rows in sorted(groups.items())],
            "by_configuration_phase": [{"configuration": label, "phase": phase,
                                         **summary([r for r in records if r["configuration"] == label and r["phase"] == phase])}
                                        for label in protocol["conditions"] for phase in ("fixed", "rollout")
                                        if any(r["configuration"] == label and r["phase"] == phase for r in records)],
            "paired_operational_differences": comparisons, "paired_prompt_checks": prompt_checks,
            "adapter_prompt_mismatches": sum(not p["same"] for p in prompt_checks),
            "adapter_pairs_with_any_llm_attempt": sum(bool(p["base_calls"] or p["ft_calls"]) for p in prompt_checks),
            "adapter_pairs_without_llm_calls": sum(not p["base_calls"] and not p["ft_calls"] for p in prompt_checks),
            "non_llm_adapter_answer_mismatches": non_llm_adapter_answer_mismatches,
            "by_configuration_phase_route": [{"configuration": label, "phase": phase, "route": branch,
                    **summary([r for r in records if r["configuration"] == label and r["phase"] == phase and route(r) == branch])}
                    for label in protocol["conditions"] for phase in ("fixed", "rollout")
                    for branch in ("llm_attempt", "rules_or_faq", "other_without_llm")
                    if any(r["configuration"] == label and r["phase"] == phase and route(r) == branch for r in records)],
            "repeated_output_variation": variation, "primary_quality_repeat": 1,
            "human_quality_scores": None, "human_claim_labels": None,
            "H1_H2_H3_quality_conclusions": "Await two independent human raters; operational measures alone do not establish these hypotheses.",
            "limits": protocol["limitations"],
            "ci_note": "Exploratory, unadjusted 95% family bootstrap intervals; repeated runs are not independent questions."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    result = analyze(args.root.resolve(), args.allow_partial)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        with args.out.open("x", encoding="utf-8") as stream:
            stream.write(text)
        print(json.dumps({"written": str(args.out), "observations": result["record_count"], "status": result["study_status"]}))
    else:
        print(text)
