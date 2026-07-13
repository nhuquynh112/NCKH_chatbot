import argparse
import json
from pathlib import Path

from rag_chat_ollama import chat, load_index, retrieve


ROOT = Path(__file__).resolve().parent
EVAL_PATH = ROOT / "techcare_eval_120.json"
RESULT_PATH = ROOT / "evaluation_results.json"


def compact_sources(hits):
    return [
        {
            "score": round(score, 4),
            "id": record["id"],
            "title": record["title"],
        }
        for score, record in hits
    ]


def rough_match(expected, answer):
    expected_tokens = [
        token.strip(".,:;!?()[]{}").lower()
        for token in expected.split()
        if len(token.strip(".,:;!?()[]{}")) >= 4
    ]
    if not expected_tokens:
        return False
    answer_lower = answer.lower()
    hits = sum(1 for token in expected_tokens[:12] if token in answer_lower)
    return hits / min(len(expected_tokens), 12) >= 0.35


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Số câu đánh giá muốn chạy")
    args = parser.parse_args()

    eval_items = json.loads(EVAL_PATH.read_text(encoding="utf-8"))[: args.limit]
    records = load_index()
    results = []

    for index, item in enumerate(eval_items, start=1):
        question = item["question"]
        expected = item["answer"]
        print(f"[{index}/{len(eval_items)}] {question}")

        hits = retrieve(question, records)
        context = "\n\n---\n\n".join(hit[1]["content"] for hit in hits)
        answer = chat(question, context)

        results.append(
            {
                "id": item["id"],
                "intent": item["intent"],
                "question": question,
                "expected": expected,
                "actual": answer,
                "rough_match": rough_match(expected, answer),
                "sources": compact_sources(hits),
            }
        )

    accuracy = sum(1 for result in results if result["rough_match"]) / len(results) if results else 0
    output = {
        "total": len(results),
        "rough_accuracy": round(accuracy, 4),
        "note": "rough_match chỉ là chấm tự động tương đối; báo cáo cuối nên kiểm tra thủ công thêm.",
        "results": results,
    }
    RESULT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved results to {RESULT_PATH}")
    print(f"Rough accuracy: {accuracy:.2%}")


if __name__ == "__main__":
    main()
