"""Export repetition-1 observations for blind human review without assigning any grades."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re
import secrets
import zipfile

from controlled_study.prepare import load, write_new, sha
from controlled_study.run import verify_lock


def chunks(text, size=700):
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


def build(root, private_dir):
    verify_lock(root)
    public_path = root / "review/review_payload.json"
    if public_path.exists():
        raise ValueError("Review payload exists; do not rerandomize or overwrite")
    cases = {case["id"]: case for case in load(root / "cases.json")["cases"]}
    records = [json.loads(line) for line in (root / "runs/results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    primary = [r for r in records if r["repeat"] == 1 and r["phase"] == "fixed"]
    if len(primary) != 360:
        raise ValueError("Need all 360 preregistered primary observations before exporting review forms")
    if len({(r["configuration"], r["case_id"]) for r in primary}) != 360:
        raise ValueError("Duplicate primary observations")
    private_dir.mkdir(parents=True, exist_ok=False)
    observations = {}
    rows = []
    statements = []
    for record in primary:
        case = cases[record["case_id"]]
        anonymous_id = "C" + secrets.token_hex(6)
        while anonymous_id in observations:
            anonymous_id = "C" + secrets.token_hex(6)
        history = "\n\n".join(t["role"] + ": " + t["content"] for t in record["input_history"])
        reference = case["required_points"] + "\nNguồn: snapshot corpus/ đã khóa; xem Nguon_tham_chieu theo mã ca."
        if case["reference_products"]:
            reference += "\n" + "\n".join(
                p["name"] + "; giá " + str(int(p["price"])) + " VND; bảo hành "
                + (str(p["warranty_months"]) + " tháng" if p.get("warranty_months") else "chưa xác nhận")
                for p in case["reference_products"])
        if record["result"]["status"] not in ("ok", "no_rule_match"):
            reference += "\nLỗi thực thi được giữ nguyên; theo rubric chất lượng là 0, người chấm tự nhập điểm."
        answer = record["result"].get("answer", "")
        rows.append([anonymous_id, case["id"], record["question"], history, answer,
                     record["result"]["status"], reference, None,
                     None if case["category"] == "H" else "NA",
                     None if case["category"] == "H" else "NA",
                     "NA" if case["category"] == "T" else None, None])
        observations[anonymous_id] = {"case_id": case["id"], "configuration": record["configuration"],
                                      "repeat": 1, "phase": "fixed",
                                      "rubric_sha256": hashlib.sha256(reference.encode()).hexdigest(),
                                      "response_sha256": hashlib.sha256(answer.encode()).hexdigest()}
        # This is a reading aid, not automatic atomic-claim annotation or grading.
        segments = []
        for line in answer.splitlines():
            if line.strip():
                segments.extend(re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ỵ])", line))
        for segment in segments or [""]:
            for part in chunks(segment):
                statements.append([anonymous_id, case["id"], part, None, None, None, None, None])
    histories = []
    references = []
    for case in cases.values():
        if case["history"]:
            for i, turn in enumerate(case["history"], 1):
                histories.append([case["id"], i, turn["role"], turn["content"], case["history_origin"]])
            histories.append([case["id"], len(case["history"]) + 1, "user (câu cuối)", case["question"], "Câu gửi để đo; fixture đầu vào giống nhau cho mọi cấu hình."])
        for product in case["reference_products"]:
            text = json.dumps(product, ensure_ascii=False, indent=2)
            for i, part in enumerate(chunks(text), 1):
                references.append([case["id"], product["name"], f"product:{product['id']}/part:{i}", part,
                                   "corpus/techcare_products.json (snapshot; URL chỉ là xuất xứ)"])
        references.append([case["id"], "Tiêu chí ca", case["id"], case["required_points"], "cases.json; không được đưa vào model"])
    faqs = load(root / "corpus/faq_curated.json")["faqs"]
    for faq in faqs:
        for i, part in enumerate(chunks(faq["answer"]), 1):
            references.append(["CHUNG", faq["question"], f"faq:{faq['id']}/part:{i}", part,
                               "corpus/faq_curated.json; chính sách mô phỏng TechCare"])
    random.SystemRandom().shuffle(rows)
    random.SystemRandom().shuffle(statements)
    order_seeds = [secrets.randbits(64), secrets.randbits(64)]
    orders = []
    for seed in order_seeds:
        ids = [row[0] for row in rows]
        random.Random(seed).shuffle(ids)
        orders.append(ids)
    mapping = {"schema_version": 1, "purpose": "Coordinator only; keep from raters until grading closes",
               "study": root.name, "order_seeds": order_seeds, "observations": observations}
    write_new(private_dir / "mapping_private.json", mapping)
    payload = {"study": root.name, "primary_repeat": 1, "observations": 360, "cases": 60,
               "rows": rows, "statements": statements, "histories": histories, "references": references,
               "orders": orders, "columns": ["Mã chấm", "Mã ca", "Câu hỏi", "Lịch sử đầu vào", "Phản hồi",
                           "Trạng thái", "Tiêu chí/nguồn", "Điểm 0–2", "Nhầm SP 0/1", "Đổi chủ đề đúng 0/1",
                           "Từ chối nhầm 0/1", "Lý do"],
               "input_policy": "Only two humans assign scores and claim labels. NA is preregistered metric applicability, not a grade.",
               "claim_policy": "Column C is a heuristic reading aid. Human splits/merges atomic statements into column D and assigns E/F with evidence G; no automatic labels.",
               "scoring": {"quality": {"2": "Đáp ứng đầy đủ tiêu chí, đúng dữ kiện/phạm vi và có xử lý thiếu thông tin phù hợp",
                                       "1": "Đúng một phần nhưng thiếu ý hoặc chưa đủ đáp ứng tiêu chí",
                                       "0": "Sai, không đáp ứng hoặc lỗi thực thi không có phản hồi"},
                           "wrong_product": "1 = nhầm sản phẩm, 0 = không nhầm; chỉ 16 ca H",
                           "correct_topic_switch": "Chấm nhóm H: 1 = chuyển đúng, 0 = chuyển sai; người chấm chọn NA nếu ca không yêu cầu chuyển chủ đề",
                           "false_refusal": "1 = từ chối nhầm yêu cầu có thể hỗ trợ, 0 = không; NA ở nhóm T",
                           "claim_type": ["business_fact", "non_factual"],
                           "grounding": ["supported", "contradicted", "insufficient_evidence"]}}
    public_path.parent.mkdir(exist_ok=True)
    write_new(public_path, payload)
    write_new(public_path.parent / "mapping_commitment.json",
              {"schema_version": 1, "observations": 360, "primary_repeat": 1,
               "private_mapping_sha256": sha(private_dir / "mapping_private.json"),
               "public_mapping": False,
               "note": "Coordinator retains the mapping outside Git until both independent human ratings are complete. This commits to the assignment without exposing method labels."})
    source_files = [path for path in sorted((root / "corpus").iterdir())
                    if path.name not in ("system_prompt.txt", "vector_index.json")]
    with zipfile.ZipFile(public_path.parent / "Nguon_cham.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in source_files:
            archive.write(path, "corpus/" + path.name)
    write_new(public_path.parent / "Nguon_cham_sha256.json",
              {"scope": "Complete business source snapshot for human review; not method-specific retrieved context",
               "files": {path.name: sha(path) for path in source_files}})
    print(json.dumps({"payload": str(public_path), "private_mapping": str(private_dir / 'mapping_private.json'),
                      "primary_rows": len(rows), "claim_reading_aid_rows": len(statements),
                      "all_quality_scores_blank": all(row[7] is None for row in rows),
                      "all_claim_labels_blank": all(row[4] is None and row[5] is None for row in statements)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path, required=True)
    args = parser.parse_args()
    build(args.root.resolve(), args.private_dir.resolve())
