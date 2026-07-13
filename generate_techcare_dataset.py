import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


PRODUCTS = [
    {
        "sku": "TC-LT-001",
        "name": "Laptop NovaBook Air 14",
        "category": "laptop",
        "price": "14.990.000 VND",
        "warranty": "24 tháng",
        "short": "Intel Core i5 thế hệ 13, RAM 16GB, SSD 512GB, màn hình 14 inch Full HD, pin 7-9 giờ",
        "use": "sinh viên, nhân viên văn phòng, học online, Word, Excel, PowerPoint, lập trình cơ bản và thiết kế nhẹ",
    },
    {
        "sku": "TC-LT-002",
        "name": "Laptop GamePro 15",
        "category": "laptop",
        "price": "24.990.000 VND",
        "warranty": "24 tháng",
        "short": "AMD Ryzen 7, RAM 16GB, SSD 1TB, GPU RTX 4060, màn hình 15.6 inch 144Hz",
        "use": "chơi game, đồ họa 2D/3D, render video và học ngành kỹ thuật",
    },
    {
        "sku": "TC-LT-003",
        "name": "Laptop EduBook 13",
        "category": "laptop",
        "price": "9.990.000 VND",
        "warranty": "18 tháng",
        "short": "Intel Core i3, RAM 8GB, SSD 256GB, màn hình 13.3 inch Full HD, nặng 1.18kg",
        "use": "học sinh, sinh viên cần máy gọn nhẹ để học online, làm bài tập, duyệt web, Word và Excel cơ bản",
    },
    {
        "sku": "TC-PH-004",
        "name": "Điện thoại PixelOne A55",
        "category": "điện thoại",
        "price": "7.990.000 VND",
        "warranty": "12 tháng",
        "short": "màn hình AMOLED 6.5 inch 120Hz, RAM 8GB, bộ nhớ 128GB, camera 64MP, pin 5000mAh",
        "use": "chụp ảnh, dùng mạng xã hội, xem phim và chơi game nhẹ",
    },
    {
        "sku": "TC-PH-005",
        "name": "Điện thoại PixelOne Pro X",
        "category": "điện thoại",
        "price": "15.990.000 VND",
        "warranty": "12 tháng",
        "short": "màn hình OLED 6.7 inch 120Hz, RAM 12GB, bộ nhớ 256GB, camera 108MP, tele 3x",
        "use": "người cần camera tốt, hiệu năng cao, bộ nhớ lớn và dùng lâu dài",
    },
    {
        "sku": "TC-TB-006",
        "name": "Máy tính bảng TabLearn 11",
        "category": "máy tính bảng",
        "price": "8.490.000 VND",
        "warranty": "12 tháng",
        "short": "màn hình 11 inch 2K, RAM 8GB, bộ nhớ 128GB, hỗ trợ bút cảm ứng, pin 8000mAh",
        "use": "ghi chú, học online, đọc tài liệu, xem video và làm việc nhẹ",
    },
    {
        "sku": "TC-HP-007",
        "name": "Tai nghe SonicBuds Pro",
        "category": "tai nghe",
        "price": "1.990.000 VND",
        "warranty": "12 tháng",
        "short": "true wireless, chống ồn chủ động ANC, xuyên âm, IPX4, pin 7 giờ và 28 giờ với hộp sạc",
        "use": "học online, nghe nhạc, gọi điện và di chuyển ngoài đường",
    },
    {
        "sku": "TC-HP-008",
        "name": "Tai nghe SonicBuds Lite",
        "category": "tai nghe",
        "price": "790.000 VND",
        "warranty": "12 tháng",
        "short": "true wireless, mic đàm thoại, IPX4, pin 5 giờ và 20 giờ với hộp sạc, không có ANC",
        "use": "nghe gọi cơ bản, học online và ngân sách tiết kiệm",
    },
    {
        "sku": "TC-WA-009",
        "name": "Đồng hồ FitWatch S2",
        "category": "đồng hồ thông minh",
        "price": "2.490.000 VND",
        "warranty": "12 tháng",
        "short": "đo nhịp tim, SpO2, theo dõi giấc ngủ, 100 chế độ luyện tập, pin 7 ngày, chống nước 5ATM",
        "use": "theo dõi sức khỏe, luyện tập và nhận thông báo điện thoại",
    },
    {
        "sku": "TC-PB-010",
        "name": "Sạc dự phòng VoltPack 20K",
        "category": "sạc dự phòng",
        "price": "890.000 VND",
        "warranty": "12 tháng",
        "short": "20.000mAh, USB-C Power Delivery 30W, sạc nhanh điện thoại, máy tính bảng và một số laptop mỏng nhẹ",
        "use": "người cần pin dự phòng dung lượng cao khi đi học, đi làm hoặc du lịch",
    },
]


POLICIES = [
    {
        "id": "policy_warranty",
        "title": "Chính sách bảo hành",
        "questions": [
            "Bảo hành sản phẩm ở TechCare như thế nào?",
            "Laptop được bảo hành bao lâu?",
            "Điện thoại bảo hành mấy tháng?",
            "Tai nghe có được bảo hành không?",
            "Sản phẩm bị lỗi phần cứng thì xử lý sao?",
        ],
        "answer": "Laptop NovaBook Air 14 và GamePro 15 bảo hành 24 tháng, EduBook 13 bảo hành 18 tháng. Điện thoại, máy tính bảng, tai nghe, đồng hồ thông minh và sạc dự phòng bảo hành 12 tháng. Khi cần bảo hành, khách cung cấp mã đơn hàng, số điện thoại mua hàng, tên sản phẩm, mô tả lỗi và hình ảnh/video nếu có.",
    },
    {
        "id": "policy_return",
        "title": "Chính sách đổi trả",
        "questions": [
            "Shop có cho đổi trả không?",
            "Mua về không ưng có đổi được không?",
            "Sản phẩm lỗi trong 7 ngày đầu thì sao?",
            "Đổi trả cần điều kiện gì?",
            "Nếu máy bị lỗi do nhà sản xuất thì xử lý thế nào?",
        ],
        "answer": "TechCare hỗ trợ đổi trả trong 7 ngày kể từ ngày nhận hàng nếu sản phẩm còn đầy đủ hộp, phụ kiện, hóa đơn, chưa trầy xước, chưa vô nước và chưa kích hoạt bảo hành điện tử nếu sản phẩm yêu cầu kích hoạt. Nếu lỗi do nhà sản xuất trong 7 ngày đầu, TechCare hỗ trợ đổi mới cùng model nếu còn hàng.",
    },
    {
        "id": "policy_shipping",
        "title": "Chính sách giao hàng",
        "questions": [
            "Giao hàng mất bao lâu?",
            "Shop có giao toàn quốc không?",
            "Phí ship laptop là bao nhiêu?",
            "Đơn bao nhiêu thì được miễn phí giao hàng?",
            "Ở tỉnh thì bao lâu nhận được hàng?",
        ],
        "answer": "TechCare giao hàng toàn quốc. Nội thành TP.HCM và Hà Nội thường nhận trong 1-2 ngày làm việc. Các tỉnh thành khác thường nhận trong 3-5 ngày làm việc. Phí giao hàng tiêu chuẩn là 30.000 VND cho phụ kiện và 50.000 VND cho laptop, điện thoại, máy tính bảng. Đơn từ 5.000.000 VND được miễn phí giao hàng tiêu chuẩn.",
    },
    {
        "id": "policy_payment",
        "title": "Chính sách thanh toán",
        "questions": [
            "Shop hỗ trợ thanh toán bằng cách nào?",
            "Có thanh toán COD không?",
            "Thanh toán online bị trừ tiền nhưng đơn chưa xác nhận thì sao?",
            "Có thanh toán qua Momo không?",
            "Đơn giá trị cao nên thanh toán kiểu gì?",
        ],
        "answer": "TechCare hỗ trợ COD, chuyển khoản ngân hàng, thẻ ATM nội địa, Visa/Mastercard và ví điện tử Momo. Nếu thanh toán online bị trừ tiền nhưng đơn chưa xác nhận, khách cung cấp số điện thoại đặt hàng, mã giao dịch và ảnh chụp biên lai để nhân viên kiểm tra trong 24 giờ làm việc.",
    },
    {
        "id": "policy_ticket",
        "title": "Quy trình tạo ticket",
        "questions": [
            "Khi nào cần tạo ticket?",
            "Muốn gặp nhân viên thì làm sao?",
            "Tôi cần hỗ trợ kỹ thuật thì cung cấp gì?",
            "Tạo ticket cần thông tin nào?",
            "Bao lâu thì nhân viên phản hồi ticket?",
        ],
        "answer": "Chatbot nên tạo ticket khi khách cần kiểm tra đơn hàng, lỗi kỹ thuật, bảo hành, đổi trả, hoàn tiền, thanh toán lỗi, tư vấn cấu hình chi tiết hoặc câu hỏi vượt ngoài dữ liệu RAG. Thông tin cần có: họ tên, số điện thoại, email nếu có, mã đơn hàng nếu có, tên sản phẩm, số serial nếu có, vấn đề cần hỗ trợ và hình ảnh/video minh chứng. SLA phản hồi là trong 24 giờ làm việc.",
    },
]


ORDERS = [
    {
        "code": "TCDH1001",
        "status": "đã giao thành công ngày 05/07/2026",
        "items": "1 Laptop NovaBook Air 14 màu bạc",
    },
    {
        "code": "TCDH1007",
        "status": "đang vận chuyển, dự kiến giao trong ngày 07/07/2026",
        "items": "1 Tai nghe SonicBuds Pro màu đen",
    },
    {
        "code": "TCDH1012",
        "status": "đang chờ xác nhận thanh toán online, nhân viên cần kiểm tra giao dịch trước khi đóng gói",
        "items": "1 Điện thoại PixelOne Pro X màu xanh",
    },
    {
        "code": "TCDH1020",
        "status": "đang đóng gói tại kho TP.HCM",
        "items": "1 Sạc dự phòng VoltPack 20K",
    },
    {
        "code": "TCDH1028",
        "status": "giao không thành công lần 1 vì không liên hệ được người nhận",
        "items": "1 Máy tính bảng TabLearn 11",
    },
]


def add_pair(pairs, intent, question, answer, source_ids, requires_handoff=False, suggested_action="answer", entities=None):
    pairs.append(
        {
            "id": f"qa_{len(pairs) + 1:04d}",
            "intent": intent,
            "question": question,
            "answer": answer,
            "source_ids": source_ids,
            "language": "vi",
            "requires_handoff": requires_handoff,
            "entities": entities or {},
            "suggested_action": suggested_action,
            "channel": "website_chat",
        }
    )


def build_pairs():
    pairs = []

    price_templates = [
        "{name} giá bao nhiêu?",
        "Cho mình hỏi giá {name} với",
        "{name} hiện đang bán giá nào?",
        "Sản phẩm {name} bao nhiêu tiền?",
        "Báo giá giúp mình {name}",
    ]
    spec_templates = [
        "{name} cấu hình thế nào?",
        "Thông số chính của {name} là gì?",
        "{name} có điểm gì nổi bật?",
        "Mô tả nhanh giúp mình {name}",
        "{name} phù hợp với nhu cầu nào?",
    ]
    warranty_templates = [
        "{name} bảo hành bao lâu?",
        "Thời gian bảo hành của {name} là mấy tháng?",
        "Mua {name} thì được bảo hành như thế nào?",
    ]

    for product in PRODUCTS:
        for question in price_templates:
            add_pair(
                pairs,
                "product_price",
                question.format(**product),
                f"{product['name']} hiện có giá niêm yết {product['price']}. Giá thực tế có thể thay đổi nếu áp dụng voucher hoặc chương trình khuyến mãi.",
                [product["sku"]],
                entities={"sku": product["sku"], "product": product["name"], "category": product["category"]},
            )
        for question in spec_templates:
            add_pair(
                pairs,
                "product_info",
                question.format(**product),
                f"{product['name']} có thông tin chính: {product['short']}. Sản phẩm phù hợp với nhu cầu {product['use']}.",
                [product["sku"]],
                entities={"sku": product["sku"], "product": product["name"], "category": product["category"]},
            )
        for question in warranty_templates:
            add_pair(
                pairs,
                "product_warranty",
                question.format(**product),
                f"{product['name']} được bảo hành {product['warranty']}. Nếu cần bảo hành, bạn vui lòng cung cấp mã đơn hàng, số điện thoại mua hàng, mô tả lỗi và hình ảnh/video nếu có.",
                [product["sku"], "policy_warranty"],
                entities={"sku": product["sku"], "product": product["name"], "category": product["category"]},
            )

    recommendation_cases = [
        (
            "Mình là sinh viên, cần laptop học online và làm Word Excel thì chọn máy nào?",
            "Nếu ngân sách khoảng 15 triệu, bạn nên chọn Laptop NovaBook Air 14 vì có RAM 16GB, SSD 512GB, pin 7-9 giờ và phù hợp học online, Word, Excel. Nếu muốn tiết kiệm hơn khoảng 10 triệu, EduBook 13 phù hợp nhu cầu cơ bản.",
        ),
        (
            "Máy nào chơi game ngon?",
            "Với nhu cầu chơi game, TechCare gợi ý Laptop GamePro 15 vì máy có AMD Ryzen 7, RAM 16GB, SSD 1TB, GPU RTX 4060 và màn hình 144Hz.",
        ),
        (
            "Mình cần laptop để render video thì nên mua gì?",
            "Bạn nên chọn Laptop GamePro 15 vì sản phẩm phù hợp đồ họa 2D/3D, render video, chơi game và học ngành kỹ thuật.",
        ),
        (
            "Tai nghe nào có chống ồn để học online ở quán cafe?",
            "Bạn nên chọn SonicBuds Pro vì tai nghe có chống ồn chủ động ANC, chế độ xuyên âm, mic đàm thoại và pin tối đa 28 giờ khi dùng hộp sạc.",
        ),
        (
            "Điện thoại nào chụp ảnh tốt hơn?",
            "Nếu cần camera tốt hơn và hiệu năng cao, bạn nên chọn PixelOne Pro X vì máy có camera chính 108MP, camera tele 3x, RAM 12GB và bộ nhớ 256GB.",
        ),
        (
            "Mình cần máy tính bảng để ghi chú học online thì có mẫu nào?",
            "Bạn có thể chọn TabLearn 11 vì máy có màn hình 11 inch 2K, RAM 8GB, bộ nhớ 128GB, hỗ trợ bút cảm ứng và pin 8000mAh.",
        ),
        (
            "Tai nghe giá rẻ thì nên chọn mẫu nào?",
            "Nếu cần tai nghe cơ bản với ngân sách tiết kiệm, bạn có thể chọn SonicBuds Lite. Mẫu này có mic đàm thoại, chống nước IPX4 và pin tối đa 20 giờ với hộp sạc.",
        ),
        (
            "Có sạc dự phòng nào sạc nhanh không?",
            "Bạn có thể chọn VoltPack 20K vì sản phẩm có dung lượng 20.000mAh, cổng USB-C Power Delivery 30W và hỗ trợ sạc nhanh cho điện thoại, máy tính bảng.",
        ),
    ]
    for question, answer in recommendation_cases:
        add_pair(pairs, "recommendation", question, answer, ["recommendation"], entities={"topic": "recommendation"})

    for policy in POLICIES:
        for question in policy["questions"]:
            add_pair(pairs, policy["id"], question, policy["answer"], [policy["id"]], entities={"topic": policy["title"]})

    for order in ORDERS:
        questions = [
            f"Đơn {order['code']} đang ở đâu?",
            f"Kiểm tra giúp mình đơn hàng {order['code']}",
            f"Tình trạng đơn {order['code']} thế nào?",
            f"Đơn hàng {order['code']} giao chưa?",
        ]
        for question in questions:
            add_pair(
                pairs,
                "order_lookup",
                question,
                f"Mã đơn {order['code']} hiện {order['status']}, gồm {order['items']}.",
                [f"order_{order['code']}"],
                entities={"order_code": order["code"]},
            )

    issue_templates = [
        "Laptop của mình bị màn hình xanh thì làm sao?",
        "Máy mới mua bị nóng bất thường",
        "Điện thoại sạc không vào pin",
        "Tai nghe một bên không nghe được",
        "Laptop bị lỗi bàn phím sau vài ngày sử dụng",
        "Máy bị vô nước có được bảo hành không?",
        "Sản phẩm giao tới bị trầy xước",
        "Mình muốn hoàn tiền vì sản phẩm bị lỗi",
        "Đơn hàng giao sai sản phẩm",
        "Thanh toán rồi nhưng chưa thấy xác nhận đơn",
    ]
    ticket_answer = "Mình cần tạo ticket để nhân viên kiểm tra. Bạn vui lòng cung cấp họ tên, số điện thoại, mã đơn hàng, tên sản phẩm, mô tả lỗi và hình ảnh/video minh chứng nếu có. Nhân viên TechCare sẽ phản hồi trong 24 giờ làm việc."
    for question in issue_templates:
        add_pair(
            pairs,
            "support_ticket",
            question,
            ticket_answer,
            ["policy_ticket", "policy_warranty"],
            requires_handoff=True,
            suggested_action="create_ticket",
            entities={"topic": "technical_support"},
        )

    fallback_questions = [
        "Shop có bán máy giặt không?",
        "TechCare có sửa tủ lạnh không?",
        "Có bán điều hòa không?",
        "Mình muốn mua xe máy điện",
        "Shop có bán bàn ghế gaming không?",
        "Có dịch vụ lắp camera tại nhà không?",
        "Có bán linh kiện mainboard rời không?",
        "Có nhận unlock điện thoại không?",
        "Có bán máy ảnh chuyên nghiệp không?",
        "Có thay pin laptop tại nhà không?",
    ]
    fallback_answer = "Mình chưa có đủ thông tin để xác nhận nội dung này trong dữ liệu hiện tại. Mình có thể tạo ticket để nhân viên TechCare kiểm tra và tư vấn chính xác hơn cho bạn."
    for question in fallback_questions:
        add_pair(
            pairs,
            "fallback",
            question,
            fallback_answer,
            ["policy_ticket"],
            requires_handoff=True,
            suggested_action="handoff",
            entities={"topic": "out_of_scope"},
        )

    # Tạo thêm biến thể tự nhiên để đạt quy mô dataset dùng cho fine-tuning thử nghiệm.
    expanded = list(pairs)
    prefixes = ["Ad ơi, ", "Cho mình hỏi ", "Mình cần biết ", "Bạn tư vấn giúp mình: ", "Shop ơi, "]
    for pair in pairs:
        if len(expanded) >= 620:
            break
        for prefix in prefixes:
            if len(expanded) >= 620:
                break
            new_pair = dict(pair)
            new_pair["id"] = f"qa_{len(expanded) + 1:04d}"
            new_pair["question"] = prefix + pair["question"][0].lower() + pair["question"][1:]
            expanded.append(new_pair)

    return expanded


def build_rag_documents():
    docs = []
    for product in PRODUCTS:
        docs.append(
            {
                "id": product["sku"],
                "type": "product",
                "title": product["name"],
                "content": f"{product['name']} mã {product['sku']} thuộc nhóm {product['category']}. Giá niêm yết {product['price']}. Thông tin chính: {product['short']}. Phù hợp với nhu cầu {product['use']}. Bảo hành {product['warranty']}.",
                "metadata": {"sku": product["sku"], "category": product["category"], "source": "synthetic_catalog"},
            }
        )
    for policy in POLICIES:
        docs.append(
            {
                "id": policy["id"],
                "type": "policy",
                "title": policy["title"],
                "content": policy["answer"],
                "metadata": {"source": "synthetic_policy"},
            }
        )
    for order in ORDERS:
        docs.append(
            {
                "id": f"order_{order['code']}",
                "type": "order",
                "title": f"Đơn hàng {order['code']}",
                "content": f"Mã đơn {order['code']}: {order['status']}, gồm {order['items']}.",
                "metadata": {"source": "synthetic_order", "order_code": order["code"]},
            }
        )
    return docs


def write_outputs():
    pairs = build_pairs()
    docs = build_rag_documents()

    (ROOT / "techcare_chatbot_dataset.json").write_text(
        json.dumps(
            {
                "metadata": {
                    "name": "TechCare Electronics customer support chatbot dataset",
                    "language": "vi",
                    "domain": "thiết bị điện tử",
                    "qa_count": len(pairs),
                    "rag_document_count": len(docs),
                    "note": "Dữ liệu tổng hợp phục vụ học tập/nghiên cứu, không phải dữ liệu doanh nghiệp thật.",
                },
                "rag_documents": docs,
                "qa_pairs": pairs,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    (ROOT / "techcare_rag_documents.json").write_text(
        json.dumps(docs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with (ROOT / "techcare_train_pairs.jsonl").open("w", encoding="utf-8") as f:
        for pair in pairs:
            record = {
                "messages": [
                    {
                        "role": "system",
                        "content": "Bạn là chatbot chăm sóc khách hàng của TechCare Electronics. Trả lời lịch sự, đúng dữ liệu, không bịa.",
                    },
                    {"role": "user", "content": pair["question"]},
                    {"role": "assistant", "content": pair["answer"]},
                ],
                "metadata": {
                    "id": pair["id"],
                    "intent": pair["intent"],
                    "source_ids": pair["source_ids"],
                    "requires_handoff": pair["requires_handoff"],
                },
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    with (ROOT / "techcare_qa_pairs.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "intent",
                "question",
                "answer",
                "source_ids",
                "requires_handoff",
                "suggested_action",
            ],
        )
        writer.writeheader()
        for pair in pairs:
            writer.writerow(
                {
                    "id": pair["id"],
                    "intent": pair["intent"],
                    "question": pair["question"],
                    "answer": pair["answer"],
                    "source_ids": ", ".join(pair["source_ids"]),
                    "requires_handoff": pair["requires_handoff"],
                    "suggested_action": pair["suggested_action"],
                }
            )

    eval_pairs = pairs[:80] + [p for p in pairs if p["intent"] in {"support_ticket", "fallback", "order_lookup"}][:40]
    (ROOT / "techcare_eval_120.json").write_text(
        json.dumps(eval_pairs[:120], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = f"""# Dataset TechCare Electronics

Bộ dữ liệu này là dữ liệu tổng hợp phục vụ demo chatbot chăm sóc khách hàng cho website bán thiết bị điện tử.

## Quy mô

- Số cặp hỏi đáp: {len(pairs)}
- Số tài liệu RAG: {len(docs)}
- Ngôn ngữ: tiếng Việt
- Chủ đề: thiết bị điện tử, chăm sóc khách hàng, tư vấn sản phẩm, bảo hành, đổi trả, giao hàng, thanh toán, ticket

## File sinh ra

- `techcare_chatbot_dataset.json`: file đầy đủ gồm metadata, tài liệu RAG và Q/A pairs.
- `techcare_rag_documents.json`: tài liệu đưa vào vector database như ChromaDB/FAISS.
- `techcare_train_pairs.jsonl`: dữ liệu dạng messages, dùng để thử nghiệm fine-tuning/instruction tuning.
- `techcare_qa_pairs.csv`: bảng hỏi đáp mở bằng Excel.
- `techcare_eval_120.json`: 120 mẫu dùng để đánh giá chatbot.

## Ghi chú cho báo cáo

Dataset được tự tạo theo miền thiết bị điện tử, gồm hơn 200 mẫu hỏi đáp như yêu cầu đề tài. Dataset này có thể dùng để thử nghiệm fine-tuning nhẹ hoặc dùng làm bộ đánh giá cho mô hình RAG. Trong demo hiện tại, hệ thống ưu tiên RAG vì dễ cập nhật dữ liệu và phù hợp với chatbot chăm sóc khách hàng thực tế.
"""
    (ROOT / "DATASET_TECHCARE.md").write_text(summary, encoding="utf-8")

    print(f"Generated {len(pairs)} QA pairs and {len(docs)} RAG documents.")


if __name__ == "__main__":
    write_outputs()
