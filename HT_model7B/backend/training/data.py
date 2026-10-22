"""Review gates, reproducible sampling and assistant-only training labels."""
from collections import defaultdict
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import random
import re
import unicodedata

SOURCE = "ura-hcmut/Vietnamese-Customer-Support-QA"
SEED = 20261014
SYSTEM = (
    "Bạn là trợ lý chăm sóc khách hàng. Trả lời tiếng Việt ngắn gọn, lịch sự, "
    "hỏi lại khi thiếu thông tin. Chỉ dùng dữ kiện được cung cấp; không tự bịa "
    "giá, chính sách, tồn kho hay kết quả thao tác. Không xin mật khẩu hoặc OTP."
)


def normalized(text):
    value = unicodedata.normalize("NFD", str(text).lower().replace("đ", "d"))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", "".join(
        c for c in value if unicodedata.category(c) != "Mn"
    )).split())


def fingerprint(question):
    return hashlib.sha256(normalized(question).encode("utf-8")).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_jsonl(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n"
                                 for row in rows), encoding="utf-8")


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8-sig").splitlines()
            if line.strip()]


def risk_flags(question, answer):
    """Flags are a triage aid, never automatic permission to train."""
    text = f"{question}\n{answer}"
    folded = normalized(text)
    flags = []
    if not str(question).strip() or not str(answer).strip():
        flags.append("empty")
    if re.search(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}|https?://|www\.", text):
        flags.append("contact_or_url")
    if re.search(r"(?<!\w)(?:\+84|0)(?:[ .-]?\d){8,10}(?!\w)", text):
        flags.append("possible_phone")
    if re.search(r"\b(?:otp|password|mat khau|so the|cvv)\b", folded):
        flags.append("credential_content")
    if re.search(r"\b(?:doopage|zalo|shopee|tiktok|facebook|lazada|youtube|fanpage|oa|api|crm)\b", folded):
        flags.append("other_business_or_software")
    if re.search(r"\d[\d.,]*\s*(?:k\b|trieu|tr\b|vnd|dong|%|ngay|thang|nam)", folded):
        flags.append("numeric_policy")
    if re.search(r"\b(?:bao gia|goi phi|mien phi|chuyen khoan|bao hanh|hoan tien|khuyen mai|gia han)\b", folded):
        flags.append("business_policy")
    if re.search(r"\b(?:da huy|da tao|da cap nhat|da hoan|da gui|da chuyen|da xu ly|goi lai)\b", normalized(answer)):
        flags.append("unsupported_action_claim")
    if re.search(r"\b(?:bo qua quy tac|system prompt|ignore previous|jailbreak)\b", folded):
        flags.append("instruction_attack")
    return flags


def survey_rows(rows, limit=200, seed=SEED):
    """Round-robin types, one normalized question per sample, train split only."""
    if not 1 <= limit <= 200:
        raise ValueError("The approved survey is limited to 200 source train rows")
    buckets = defaultdict(list)
    for index, row in enumerate(rows):
        if not all(isinstance(row.get(key), str) for key in ("question", "answer", "type")):
            raise ValueError("Unexpected CSConDa schema; expected question/answer/type strings")
        buckets[row["type"].strip().lower()].append((index, row))
    rng = random.Random(seed)
    for group in buckets.values():
        rng.shuffle(group)
    seen, result = set(), []
    while len(result) < limit and any(buckets.values()):
        for kind in sorted(buckets):
            while buckets[kind]:
                index, row = buckets[kind].pop()
                key = fingerprint(row["question"])
                if key in seen:
                    continue
                seen.add(key)
                result.append({
                    "id": f"train:{index}", "source_split": "train", "question_sha256": key,
                    "question": row["question"].strip(), "answer": row["answer"].strip(),
                    "type": row["type"], "flags": risk_flags(row["question"], row["answer"]),
                    "decision": "pending", "review_note": "",
                })
                break
            if len(result) >= limit:
                break
    return result


def reviewed_examples(review, original_survey):
    """Explicit review of original pairs; rewrites require separate provenance."""
    originals = {row["id"]: row for row in original_survey}
    if len(originals) != len(original_survey):
        raise ValueError("Duplicate IDs in original survey")
    if len(review) != len(originals) or {row["id"] for row in review} != set(originals):
        raise ValueError("Review must account for every surveyed row exactly once")
    seen, examples = set(), []
    for row in review:
        if row["source_split"] != "train":
            raise ValueError("Only source train samples may be used")
        original = originals[row["id"]]
        if any(row[key] != original[key] for key in ("question", "answer", "type", "question_sha256")):
            raise ValueError("Source text was changed; do not silently call a rewrite real data")
        if row["decision"] not in {"include", "exclude", "rewrite"} or not row.get("review_note", "").strip():
            raise ValueError("Every row needs an include/exclude decision and a review note")
        if row["decision"] == "exclude":
            continue
        answer = row.get("edited_answer", "") if row["decision"] == "rewrite" else row["answer"]
        if not answer.strip():
            raise ValueError("Edited answer is empty")
        flags = risk_flags(row["question"], answer)
        if flags:
            raise ValueError(f"Included row {row['id']} has unresolved safety/domain flags: {flags}")
        key = fingerprint(row["question"])
        if key in seen:
            raise ValueError("Duplicate question in reviewed data")
        seen.add(key)
        examples.append({"source_id": row["id"], "question_sha256": key,
                         "scenario_group": row.get("scenario_group", ""), "evaluation_fold": row.get("evaluation_fold", ""),
                         "answer_origin": "agent_edited_source_pair" if row["decision"] == "rewrite" else "original_human_source_answer",
                         "source_pair_sha256": hashlib.sha256((row["question"] + "\n" + row["answer"]).encode("utf-8")).hexdigest(), "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": row["question"]},
            {"role": "assistant", "content": answer},
        ]})
    return examples


def split_examples(examples, seed=SEED):
    """Validation comes from approved train rows, never CSConDa's official test."""
    if len(examples) < 20:
        raise ValueError("Fewer than 20 approved pairs: insufficient for this pilot")
    if all(row.get("scenario_group") and row.get("evaluation_fold") in {"train","validation"} for row in examples):
        train = [row for row in examples if row["evaluation_fold"] == "train"]
        validation = [row for row in examples if row["evaluation_fold"] == "validation"]
        if {row["scenario_group"] for row in train} & {row["scenario_group"] for row in validation}:
            raise ValueError("Scenario family overlaps train and validation")
        if len(train) < 10 or len(validation) < 4:
            raise ValueError("Insufficient train or validation examples")
        return train, validation
    examples = sorted(examples, key=lambda row: row["question_sha256"])
    random.Random(seed).shuffle(examples)
    validation_count = max(4, round(len(examples) * 0.2))
    return examples[validation_count:], examples[:validation_count]


def encode_example(example, tokenizer, max_length):
    messages = example["messages"]
    if [row["role"] for row in messages] != ["system", "user", "assistant"]:
        raise ValueError("Expected exactly system/user/assistant")
    prefix = tokenizer.apply_chat_template(messages[:-1], tokenize=True, add_generation_prompt=True)
    full = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=False)
    if isinstance(prefix, Mapping):
        prefix, full = prefix["input_ids"], full["input_ids"]
    if hasattr(prefix, "tolist"):
        prefix, full = prefix.tolist(), full.tolist()
    if full[:len(prefix)] != prefix:
        raise ValueError("Chat template prefix is not token-aligned; refusing incorrect label masking")
    if len(full) > max_length:
        raise ValueError("Sequence exceeds limit; exclude/review it instead of truncating the answer")
    if len(full) <= len(prefix):
        raise ValueError("No assistant tokens to train")
    return {"input_ids": full, "attention_mask": [1] * len(full),
            "labels": [-100] * len(prefix) + full[len(prefix):]}


class AssistantCollator:
    def __init__(self, pad_token_id):
        self.pad_token_id = pad_token_id

    def __call__(self, rows):
        import torch
        longest = max(len(row["input_ids"]) for row in rows)
        output = {key: [] for key in ("input_ids", "attention_mask", "labels")}
        for row in rows:
            count = longest - len(row["input_ids"])
            output["input_ids"].append(row["input_ids"] + [self.pad_token_id] * count)
            output["attention_mask"].append(row["attention_mask"] + [0] * count)
            output["labels"].append(row["labels"] + [-100] * count)
        return {key: torch.tensor(value, dtype=torch.long) for key, value in output.items()}
