"""Analyze real human ratings only; never infer missing scores or claim labels."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from controlled_study.analyze import paired_ci
from controlled_study.prepare import load, sha
from controlled_study.run import verify_lock


CLAIM_TYPES = {"business_fact", "non_factual"}
GROUNDING = {"supported", "contradicted", "insufficient_evidence"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def explicit_label(value):
    if isinstance(value, str) and value.strip() in ("0", "1", "2"):
        return int(value.strip())
    if isinstance(value, str) and value.strip().upper() == "NA":
        return "NA"
    return value


def read_rater(path, mapping, observations):
    from openpyxl import load_workbook
    workbook = load_workbook(path, data_only=False)
    main = workbook["Phieu_cham"]
    scores = {}
    rows = {}
    for row in range(9, 369):
        values = [main.cell(row, col).value for col in range(1, 13)]
        anonymous_id = values[0]
        require(anonymous_id in mapping and anonymous_id not in rows, f"{path.name}: invalid/duplicate ID at row {row}")
        meta = mapping[anonymous_id]
        original = observations[(meta["configuration"], meta["case_id"])]
        history = "\n\n".join(t["role"] + ": " + t["content"] for t in original["input_history"])
        require((values[1], values[2], values[3] or "", values[4] or "", values[5]) ==
                (original["case_id"], original["question"], history,
                 original["result"].get("answer", ""), original["result"]["status"]), f"{path.name}: content changed at {anonymous_id}")
        require(hashlib.sha256((values[6] or "").encode()).hexdigest() == meta["rubric_sha256"],
                f"{path.name}: rubric changed at {anonymous_id}")
        quality, wrong, topic, refusal = [explicit_label(v) for v in values[7:11]]
        require(quality is None or (not isinstance(quality, bool) and quality in (0, 1, 2)), "Invalid quality score")
        for value in (wrong, topic, refusal):
            require(value is None or value == "NA" or (not isinstance(value, bool) and value in (0, 1)), "Invalid binary/NA label")
        metric = lambda value: value if value in (0, 1) and not isinstance(value, bool) else None
        rows[anonymous_id] = {"case_id": meta["case_id"], "configuration": meta["configuration"],
                              "has_response": bool(original["result"].get("answer", "").strip()),
                              "quality": quality, "wrong_product": metric(wrong),
                              "correct_topic_switch": metric(topic), "false_refusal": metric(refusal),
                              "notes": values[11]}
        scores[(meta["configuration"], meta["case_id"])] = rows[anonymous_id]
    require(set(rows) == set(mapping), "Missing review observations")
    claims = defaultdict(list)
    incomplete_claims = 0
    sheet = workbook["Phat_bieu"]
    for row in range(9, sheet.max_row + 1):
        anonymous_id, case_id, candidate, claim, kind, label, evidence, note = [sheet.cell(row, col).value for col in range(1, 9)]
        if all(value is None for value in (anonymous_id, case_id, candidate, claim, kind, label, evidence, note)):
            continue
        require(anonymous_id in mapping and case_id == mapping[anonymous_id]["case_id"], "Invalid claim identity")
        if not rows[anonymous_id]["has_response"]:
            require(not claim and kind in (None, "non_factual") and label is None and not evidence,
                    "An absent response cannot supply factual claims")
            continue
        require(kind is None or kind in CLAIM_TYPES, "Invalid claim type")
        require(label is None or label in GROUNDING, "Invalid grounding label")
        require(kind != "non_factual" or label is None, "Non-factual text must not receive a grounding label")
        complete = kind == "non_factual" or (kind == "business_fact" and bool(claim) and label in GROUNDING and bool(evidence))
        incomplete_claims += int(not complete)
        claims[anonymous_id].append({"type": kind, "label": label, "claim": claim,
                                     "evidence": evidence, "complete": complete})
    for anonymous_id, row in rows.items():
        annotations = claims.get(anonymous_id, [])
        facts = [claim for claim in annotations if claim["complete"] and claim["type"] == "business_fact"]
        row["claim_review_complete"] = bool(annotations) and all(c["complete"] for c in annotations)
        row["business_claims"] = len(facts)
        row["grounding_counts"] = dict(Counter(c["label"] for c in facts))
        row["outside_source_claims"] = sum(c["label"] in ("contradicted", "insufficient_evidence") for c in facts)
        row["outside_source_rate"] = (row["outside_source_claims"] / len(facts)
                                      if facts and row["claim_review_complete"] else None)
    return {"file": path.name, "sha256": sha(path), "quality_rated": sum(v["quality"] is not None for v in rows.values()),
            "quality_counts": dict(Counter(str(v["quality"]) for v in rows.values())),
            "incomplete_claim_rows": incomplete_claims, "rows": scores}


def weighted_kappa(pairs):
    if not pairs:
        return None
    n = len(pairs)
    a = Counter(x for x, _ in pairs)
    b = Counter(y for _, y in pairs)
    observed = sum(1 - abs(x - y) / 2 for x, y in pairs) / n
    expected = sum((1 - abs(x - y) / 2) * a[x] * b[y] / n ** 2 for x in range(3) for y in range(3))
    return (observed - expected) / (1 - expected) if expected < 1 else None


def analyze(root, paths, mapping_path):
    verify_lock(root)
    commitment = load(root / "review/mapping_commitment.json")
    require(sha(mapping_path) == commitment["private_mapping_sha256"], "Mapping differs from its public hash commitment")
    mapping = load(mapping_path)["observations"]
    require(len(mapping) == 360, "Mapping must contain exactly 360 primary observations")
    records = [json.loads(line) for line in (root / "runs/results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    observations = {(r["configuration"], r["case_id"]): r for r in records if r["repeat"] == 1 and r["phase"] == "fixed"}
    require(len(observations) == 360, "Primary responses incomplete")
    cases = {r["id"]: r for r in load(root / "cases.json")["cases"]}
    family = {key: case["family"] for key, case in cases.items()}
    reports = []
    raters = [read_rater(path, mapping, observations) for path in paths]
    configurations = load(root / "protocol.json")["conditions"]
    for rater in raters:
        rows = rater["rows"]
        report = {key: value for key, value in rater.items() if key != "rows"}
        report["configuration_quality"] = {}
        report["configuration_human_metrics"] = {}
        for configuration in configurations:
            quality = [rows[(configuration, case_id)]["quality"] for case_id in cases]
            complete = all(value is not None for value in quality)
            report["configuration_quality"][configuration] = {"rated": sum(v is not None for v in quality),
                "mean_0_2": sum(quality) / 60 if complete else None,
                "pass_2_rate": quality.count(2) / 60 if complete else None}
            selected = [rows[(configuration, case_id)] for case_id in cases]
            reviewed = [row for row in selected if row["claim_review_complete"]]
            grounded = Counter()
            for row in reviewed:
                grounded.update(row["grounding_counts"])
            facts = sum(grounded.values())
            outside = grounded["contradicted"] + grounded["insufficient_evidence"]
            metrics = {"claims": {
                "responses": len(selected), "fully_reviewed_responses": len(reviewed),
                "pending_responses": sum(row["has_response"] and not row["claim_review_complete"] for row in selected),
                "unavailable_without_response": sum(not row["has_response"] for row in selected),
                "fully_reviewed_responses_without_business_facts": sum(row["business_claims"] == 0 for row in reviewed),
                "business_claims_in_fully_reviewed_responses": facts,
                "grounding_counts_in_fully_reviewed_responses": dict(grounded),
                "outside_source_claim_rate": outside / facts if facts else None,
                "note": "Pooled claim rate on fully human-reviewed responses only. No-factual-claim responses do not enter its denominator. Paired differences below use per-response rates, a different estimand."}}
            for metric in ("wrong_product", "correct_topic_switch", "false_refusal"):
                applicable = [row for row in selected
                              if (cases[row["case_id"]]["category"] == "H" if metric != "false_refusal"
                                  else cases[row["case_id"]]["category"] != "T")]
                values = [row[metric] for row in applicable if row[metric] is not None]
                metrics[metric] = {"applicable_cases": len(applicable), "rated_cases": len(values),
                                   "missing_or_NA": len(applicable) - len(values),
                                   "ones": sum(values), "rate_among_rated": sum(values) / len(values) if values else None}
            report["configuration_human_metrics"][configuration] = metrics
        comparisons = {}
        for left, right in (("P_base", "P_ft"), ("P_base", "B1_base"), ("P_base", "B2_base"),
                            ("P_base", "P_no_memory"), ("P_base", "P_no_rules")):
            metrics = {}
            for metric in ("quality", "wrong_product", "correct_topic_switch", "false_refusal", "outside_source_rate"):
                applicable = list(cases)
                if metric == "wrong_product":
                    applicable = [key for key in cases if cases[key]["category"] == "H"]
                if metric == "correct_topic_switch":
                    applicable = [key for key in cases if cases[key]["category"] == "H"]
                if metric == "false_refusal":
                    applicable = [key for key in cases if cases[key]["category"] != "T"]
                differences = {}
                for key in applicable:
                    a, b = rows[(left, key)][metric], rows[(right, key)][metric]
                    if a is not None and b is not None:
                        differences[key] = b - a
                metric_report = paired_ci(differences, family)
                metric_report.update(expected_applicable_cases=len(applicable), paired_rated_cases=len(differences),
                                     missing_or_no_business_claims=len(applicable) - len(differences),
                                     unit="paired primary responses from repetition 1, resampled by case family; no repeated responses counted as new questions",
                                     interpretation="right minus left; conditional on paired human labels, not an automatic system score")
                if metric == "quality" and len(differences) != 60:
                    metric_report.update(difference_mean=None, ci95=None, status="pending complete quality ratings")
                metrics[metric] = metric_report
            comparisons[right + " minus " + left] = metrics
        report["paired_human_differences"] = comparisons
        adapter_llm_cases = [key for key in cases
                             if all(observations[(label, key)]["result"].get("llm_called")
                                    for label in ("P_base", "P_ft"))]
        subset = {key: rows[("P_ft", key)]["quality"] - rows[("P_base", key)]["quality"]
                  for key in adapter_llm_cases
                  if all(rows[(label, key)]["quality"] is not None for label in ("P_base", "P_ft"))}
        subset_report = paired_ci(subset, family)
        subset_report.update(expected_cases=len(adapter_llm_cases), paired_rated_cases=len(subset),
                             case_ids=adapter_llm_cases,
                             unit="paired primary responses in repetition 1; family bootstrap",
                             scope="Exploratory subgroup, not a replacement for the preregistered full-pipeline quality outcome: both original pipelines attempted a final LLM call")
        if len(subset) != len(adapter_llm_cases):
            subset_report.update(difference_mean=None, ci95=None, status="pending subgroup quality ratings")
        report["exploratory_adapter_quality_both_call_llm"] = subset_report
        reports.append(report)
    agreement = None
    if len(raters) == 2:
        common = [key for key in observations if all(r["rows"][key]["quality"] is not None for r in raters)]
        pairs = [(raters[0]["rows"][key]["quality"], raters[1]["rows"][key]["quality"]) for key in common]
        agreement = {"paired_rated": len(pairs), "expected": 360,
                     "exact_agreement": sum(a == b for a, b in pairs) / len(pairs) if pairs else None,
                     "linear_weighted_kappa": weighted_kappa(pairs) if len(pairs) == 360 else None,
                     "status": "complete" if len(pairs) == 360 else "pending",
                     "scope": "New 360 primary responses only; never combined with old 400/100 ratings."}
    return {"raters": reports, "quality_agreement": agreement,
            "mapping_sha256": sha(mapping_path), "automatic_scores_created": False,
            "note": "Incomplete claims remain pending. No-factual-claim responses have undefined factual error rates, not zero. CIs exploratory/unadjusted; no H1-H3 conclusion is generated automatically."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--rater", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.root.resolve(), args.rater, args.mapping)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"output": str(args.out), "raters": len(args.rater), "automatic_scores_created": False}))
