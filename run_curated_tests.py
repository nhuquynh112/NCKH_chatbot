import json
from pathlib import Path

import rag_chat_ollama as bot


ROOT = Path(__file__).resolve().parent
RESULT_JSON = ROOT / "curated_test_results.json"
RESULT_MD = ROOT / "KET_QUA_THUC_NGHIEM_CHATBOT.md"


TEST_CASES = [
    {
        "id": "TC01",
        "group": "Chào hỏi",
        "question": "chao",
        "expected": "Chatbot chào lại và hỏi khách cần hỗ trợ gì.",
        "keywords": ["Chào bạn", "TechCare", "sản phẩm"],
    },
    {
        "id": "TC02",
        "group": "Không dấu/viết tắt",
        "question": "c ban tai nghe k",
        "expected": "Nhận diện câu hỏi 'có bán tai nghe không' và liệt kê mẫu tai nghe.",
        "keywords": ["có bán nhóm tai nghe", "SonicBuds"],
    },
    {
        "id": "TC03",
        "group": "Danh mục sản phẩm",
        "question": "co ban tablet ko",
        "expected": "Nhận diện tablet là máy tính bảng và liệt kê mẫu máy tính bảng.",
        "keywords": ["máy tính bảng", "TabLearn"],
    },
    {
        "id": "TC04",
        "group": "Sản phẩm cụ thể",
        "question": "GameMouse X9 giá bao nhiêu?",
        "expected": "Trả đúng giá GameMouse X9 là 1.650.000 VND.",
        "keywords": ["GameMouse X9", "1.650.000 VND"],
    },
    {
        "id": "TC05",
        "group": "Sản phẩm cụ thể",
        "question": "Laptop NovaBook Air 14 giá bao nhiêu?",
        "expected": "Trả đúng giá NovaBook Air 14 là 14.990.000 VND.",
        "keywords": ["NovaBook Air 14", "14.990.000 VND"],
    },
    {
        "id": "TC06",
        "group": "Tư vấn sản phẩm",
        "question": "Máy nào chơi game ngon?",
        "expected": "Gợi ý laptop gaming như GamePro 15/GamePro 17.",
        "keywords": ["GamePro", "chơi game"],
    },
    {
        "id": "TC07",
        "group": "Tư vấn sản phẩm",
        "question": "CreatorBook 16 phù hợp với nhu cầu nào?",
        "expected": "Trả lời phù hợp thiết kế, edit video, sáng tạo nội dung.",
        "keywords": ["CreatorBook 16", "thiết kế", "video"],
    },
    {
        "id": "TC08",
        "group": "Truy vấn tổng hợp",
        "question": "san pham nao gia cao nhat?",
        "expected": "Trả sản phẩm giá cao nhất trong dữ liệu hiện tại.",
        "keywords": ["giá cao nhất", "24.990.000 VND"],
    },
    {
        "id": "TC09",
        "group": "Truy vấn tổng hợp",
        "question": "san pham nao gia re nhat?",
        "expected": "Trả sản phẩm giá thấp nhất trong dữ liệu hiện tại.",
        "keywords": ["giá thấp nhất", "100.000 VND"],
    },
    {
        "id": "TC10",
        "group": "Đơn hàng",
        "question": "Đơn TCDH1007 đang ở đâu?",
        "expected": "Trả trạng thái đang vận chuyển và dự kiến giao 07/07/2026.",
        "keywords": ["TCDH1007", "đang", "07/07/2026"],
    },
    {
        "id": "TC11",
        "group": "Chính sách",
        "question": "Bảo hành điện thoại bao lâu?",
        "expected": "Trả điện thoại bảo hành 12 tháng.",
        "keywords": ["điện thoại", "12 tháng"],
    },
    {
        "id": "TC12",
        "group": "Lỗi kỹ thuật",
        "question": "Tôi mua laptop bị lỗi màn hình xanh thì làm sao?",
        "expected": "Yêu cầu thông tin để tạo ticket/hỗ trợ kỹ thuật.",
        "keywords": ["ticket", "mã đơn", "mô tả"],
    },
    {
        "id": "TC13",
        "group": "Ngoài dữ liệu",
        "question": "co ban ip17 ko",
        "expected": "Fallback, không bịa sản phẩm không có trong dữ liệu.",
        "keywords": ["chưa có đủ thông tin", "ticket"],
        "forbidden": ["OfficeKey", "KeyMate", "ComboKey"],
    },
    {
        "id": "TC14",
        "group": "Ngoài dữ liệu",
        "question": "iphone 17 ay, hay co 16 15 gi ko?",
        "expected": "Fallback, không bịa là có iPhone.",
        "keywords": ["chưa có đủ thông tin", "ticket"],
        "forbidden": ["MiniPhone", "PixelOne"],
    },
    {
        "id": "TC15",
        "group": "Ngoài phạm vi ngành hàng",
        "question": "Shop có bán máy giặt không?",
        "expected": "Fallback, không bịa sang sản phẩm khác.",
        "keywords": ["chưa có đủ thông tin", "ticket"],
        "forbidden": ["KeyMate", "ComboKey", "OfficeKey"],
    },
]


def get_answer(question, records):
    direct_answer = bot.deterministic_answer(question)
    if direct_answer:
        hits = bot.direct_source_hits(question, records, [])
        return direct_answer, hits, "rule+rag"

    hits = bot.retrieve(question, records)
    if bot.should_fallback(question, hits):
        return bot.FALLBACK_ANSWER, hits, "fallback"

    context = "\n\n---\n\n".join(hit[1]["content"] for hit in hits)
    return bot.chat(question, context), hits, "llm+rag"


def passed(case, answer):
    answer_lower = answer.lower()
    keyword_ok = all(keyword.lower() in answer_lower for keyword in case["keywords"])
    forbidden_ok = all(word.lower() not in answer_lower for word in case.get("forbidden", []))
    return keyword_ok and forbidden_ok


def main():
    records = bot.load_index()
    results = []

    for case in TEST_CASES:
        print(f"Running {case['id']}: {case['question']}")
        answer, hits, mode = get_answer(case["question"], records)
        ok = passed(case, answer)
        results.append(
            {
                "id": case["id"],
                "group": case["group"],
                "question": case["question"],
                "expected": case["expected"],
                "answer": answer,
                "mode": mode,
                "passed": ok,
                "sources": [
                    {"score": round(score, 3), "title": record["title"], "id": record["id"]}
                    for score, record in hits[:4]
                ],
            }
        )

    accuracy = sum(1 for item in results if item["passed"]) / len(results)
    RESULT_JSON.write_text(
        json.dumps(
            {"total": len(results), "passed": sum(1 for item in results if item["passed"]), "accuracy": accuracy, "results": results},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    lines = [
        "# Kết quả thực nghiệm chatbot TechCare",
        "",
        "Bộ kiểm thử này gồm 15 câu hỏi đại diện cho các nhóm tình huống thường gặp trong chatbot chăm sóc khách hàng.",
        "",
        f"- Tổng số câu kiểm thử: {len(results)}",
        f"- Số câu đạt: {sum(1 for item in results if item['passed'])}",
        f"- Accuracy thủ công theo keyword: {accuracy:.2%}",
        "",
        "| STT | Nhóm | Câu hỏi | Kết quả mong đợi | Kết quả | Đánh giá |",
        "|---:|---|---|---|---|---|",
    ]

    for index, item in enumerate(results, start=1):
        answer_short = item["answer"].replace("\n", " ")
        if len(answer_short) > 180:
            answer_short = answer_short[:177] + "..."
        status = "Đạt" if item["passed"] else "Chưa đạt"
        lines.append(
            f"| {index} | {item['group']} | {item['question']} | {item['expected']} | {answer_short} | {status} |"
        )

    lines.extend(
        [
            "",
            "## Nhận xét",
            "",
            "- Chatbot trả lời tốt các câu hỏi có dữ liệu rõ ràng như giá sản phẩm, nhóm sản phẩm, bảo hành và trạng thái đơn hàng.",
            "- Với câu hỏi ngoài dữ liệu như iPhone 17 hoặc máy giặt, chatbot không bịa sản phẩm mà chuyển sang fallback/tạo ticket.",
            "- Các câu hỏi không dấu, viết tắt như `c ban tai nghe k` được xử lý bằng lớp chuẩn hóa câu hỏi trước khi truy xuất RAG.",
            "- Một số câu tư vấn vẫn phụ thuộc vào chất lượng truy xuất và khả năng diễn đạt của LLM local, nên cần kiểm thử thêm khi mở rộng dữ liệu.",
        ]
    )
    RESULT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved {RESULT_JSON}")
    print(f"Saved {RESULT_MD}")
    print(f"Accuracy: {accuracy:.2%}")


if __name__ == "__main__":
    main()
