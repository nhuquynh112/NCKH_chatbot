"""Prepare and lock the new study before exposing its cases to any model."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import random
import re
import shutil
import unicodedata

from controlled_study.dataset import build

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parents[1]
ARCHIVE = REPO / "outputs/pft100_20261104_7c4d29"
GENERATION = {"temperature": 0, "num_predict": 384, "num_ctx": 4096, "repeat_penalty": 1.0}
CONDITIONS = {
    "P_base": {"method": "P", "adapter": "base", "changed_component": None},
    "P_ft": {"method": "P", "adapter": "ft", "changed_component": "adapter_only"},
    "B1_base": {"method": "B1", "adapter": "base", "changed_component": "plain_LLM_no_RAG"},
    "B2_base": {"method": "B2", "adapter": "base", "changed_component": "basic_RAG"},
    "P_no_memory": {"method": "P-no-product-context", "adapter": "base", "changed_component": "product_context=False"},
    "P_no_rules": {"method": "P-no-rule-routing", "adapter": "base", "changed_component": "rule_routing=False"},
}


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def code_sha(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def normalize(text):
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return " ".join(re.findall(r"\w+", text))


def prepare(root, freeze):
    if (root / "lock.json").exists():
        raise ValueError("Study is already locked; no editing or re-freezing")
    if not root.exists():
        root.mkdir(parents=True)
        shutil.copytree(ARCHIVE / "corpus", root / "corpus")
        for name in ("frozen_products.db", "plain_prompt.txt"):
            shutil.copyfile(ARCHIVE / name, root / name)
        cases = build(root / "corpus")
        write_new(root / "cases.json", {"version": "controlled-60-v1", "author": "AI-assisted, not independently authored or reviewed",
                                       "cases": cases})
    cases = load(root / "cases.json")["cases"]
    old = load(ARCHIVE / "test_inputs.json")["cases"]
    reference = []
    sources = {}
    history_run = load(ARCHIVE / "training_run.original.json")
    for split in ("train", "validation"):
        path = BACKEND / f"models/qwen2.5-7b-ft/data/{split}.jsonl"
        require_hash = history_run["source"][split + "_sha256"]
        if sha(path) != require_hash:
            raise ValueError("Historical training data hash differs: " + split)
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        sources[split] = {"rows": len(rows), "sha256": sha(path)}
        for i, row in enumerate(rows):
            text = " ".join(turn["content"] for turn in row["messages"] if turn["role"] == "user")
            reference.append((split, row.get("source_id", str(i)), normalize(text)))
    for case in old:
        text = " ".join(case.get("history_questions", []) + [case["question"]])
        reference.append(("old_100", case["id"], normalize(text)))
    audit = []
    flags = []
    seen = set()
    for case in cases:
        text = normalize(" ".join([turn["content"] for turn in case["history"] if turn["role"] == "user"] + [case["question"]]))
        if text in seen:
            raise ValueError("Duplicate new case")
        seen.add(text)
        comparisons = []
        for split, source_id, other in reference:
            sequence = difflib.SequenceMatcher(None, text, other, autojunk=False).ratio()
            a, b = set(text.split()), set(other.split())
            jaccard = len(a & b) / len(a | b) if a | b else 0
            comparisons.append({"split": split, "source_id": source_id, "sequence": sequence,
                                "token_jaccard": jaccard, "exact": text == other})
            if text == other or sequence >= .88 or jaccard >= .80:
                flags.append({"case_id": case["id"], **comparisons[-1]})
        audit.append({"case_id": case["id"], "closest": max(comparisons, key=lambda v: max(v["sequence"], v["token_jaccard"]))})
    audit_data = {"normalization": "lowercase, accent folding, word tokens; compare full user script, not fixture assistant answers",
                  "thresholds": {"sequence": .88, "token_jaccard": .80}, "sources": sources,
                  "old_cases": len(old), "new_cases": len(cases), "flags": flags, "closest_pairs": audit,
                  "limitation": "Lexical screening is not a semantic independence proof; all cases are AI-authored and await independent review."}
    audit_path = root / "overlap_audit.json"
    if audit_path.exists():
        if load(audit_path) != audit_data:
            raise ValueError("Existing audit differs; keep it and make a new draft directory")
    else:
        write_new(audit_path, audit_data)
    if flags:
        print(json.dumps({"needs_review_before_lock": flags}, ensure_ascii=False))
        return
    if not freeze:
        print(json.dumps({"draft_cases": len(cases), "overlap_flags": 0}))
        return
    orders = [list(CONDITIONS), ["P_ft", "P_no_rules", "P_no_memory", "B2_base", "B1_base", "P_base"],
              ["B2_base", "P_base", "B1_base", "P_no_rules", "P_no_memory", "P_ft"]]
    schedule = []
    for repeat, order in enumerate(orders, 1):
        ids = [case["id"] for case in cases]
        random.Random(20261105 + repeat).shuffle(ids)
        for condition in order:
            schedule.append({"repeat": repeat, "condition": condition, "case_ids": ids})
    protocol = {"version": 1, "generation": GENERATION, "repeats": 3, "cases": 60,
                "conditions": CONDITIONS, "schedule": schedule, "top_k": 5, "min_retrieval_score": .38,
                "seed": 20261014, "order_seed": 20261105, "model_call_timeout_seconds": 120,
                "single_case_deadline_seconds": 180, "conversation_deadline_seconds": 600,
                "primary_history": "Exact same fixed role-tagged input fixture in every configuration. No generated assistant answer is passed off as measured history.",
                "rollout_case_ids": ["N25", "N29", "N33", "N37"],
                "rollout_conditions": ["P_base", "P_ft", "P_no_memory", "P_no_rules"],
                "rollout_scope": "Secondary whole-conversation timings on four preregistered H scripts; generated history is treatment-specific and not pooled with fixed-input timings.",
                "warmup": {"per_block_generations": 2, "included_in_main": False,
                           "system": "Bạn là trợ lý hỗ trợ khách hàng. Chỉ dùng dữ kiện được cung cấp.",
                           "user": "Dữ kiện: mẫu thử A giá 1000000 VND, chưa xác nhận tồn kho. Nhắc lại giá và nêu giới hạn thông tin."},
                "quality_repetition": 1, "quality_policy": "Human quality/claim labels on preregistered repetition 1; report output variation in other repetitions. Never select best answers or invent scores.",
                "paired_comparisons": {"FT": ["P_base", "P_ft"], "H1": ["P_base", "B1_base", "B2_base"],
                                       "H2": ["P_base", "P_no_memory"], "H3": ["P_base", "P_no_rules"]},
                "inference_unit": "case/family, not repeated observations; retain all repeats within paired bootstrap resamples",
                "human_review": "Two independent raters, anonymous forms, no AI quality scores. Claims: supported/contradicted/insufficient_evidence; exclude nonfactual statements explicitly.",
                "limitations": ["New exploratory AI-authored set; not an independently authored external holdout.",
                                "Lexical duplicate checks cannot exclude semantic/template overlap.",
                                "Baseline P FP16/Ollama and old human scores remain external historical system controls.",
                                "No quality, factuality, confusion, false-refusal or H1-H3 conclusion until human labels exist."]}
    write_new(root / "protocol.json", protocol)
    context = load(ARCHIVE / "context.json")
    source_hashes = {"HT_model7B/backend/" + name.replace("\\", "/"): value for name, value in context["code_sha256"].items()}
    for path in Path(__file__).parent.glob("*.py"):
        source_hashes[path.relative_to(REPO).as_posix()] = sha(path)
    input_hashes = {p.relative_to(root).as_posix(): sha(p) for p in root.rglob("*") if p.is_file()}
    canonical_sources = {name: code_sha(REPO / name) for name in source_hashes}
    write_new(root / "lock.json", {"locked_utc": datetime.now(timezone.utc).isoformat(),
                                  "before_first_new_test_generation": True, "input_sha256": input_hashes,
                                  "source_sha256": canonical_sources,
                                  "source_original_byte_sha256": source_hashes,
                                  "source_hash_policy": "SHA256 after CRLF-to-LF normalization for source only; input/data hashes remain exact bytes",
                                  "case_groups": dict(Counter(case["category"] for case in cases)),
                                  "model_profile": {key: value for key, value in load(ARCHIVE / "profile.local.json").items()
                                                    if key not in ("checkpoint_path", "adapter_path")}})
    print(json.dumps({"locked": True, "cases": len(cases), "overlap_flags": 0, "root": str(root)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args()
    prepare(args.root.resolve(), args.freeze)
