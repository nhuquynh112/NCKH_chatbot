# Giao thức Chương 5 — bộ 24 câu được nhóm duyệt

Đọc kết quả ở [CHAPTER5_EXPERIMENTS_24.md](CHAPTER5_EXPERIMENTS_24.md) và thao tác chụp ảnh ở [DEMO_UI_CHAPTER5.md](DEMO_UI_CHAPTER5.md). Bộ này tách khỏi benchmark M1–M4 trên 20 câu cũ. Không đổi nhãn M3 cũ thành hai baseline: trước tác vụ này chưa có B2 riêng; B2 đã được hiện thực và kiểm tra trước khi chạy bộ 24 câu.

Nguồn giao thức: `D:/NCKH/2026_Chatbot/BaoCao_15_10/BaoCao.docx`, mục 4.2–4.6, 5.2–5.3 và 5.6.1. Tệp trong `De_Cuong_20_10` là mẫu trống, không có thiết kế 5.5/5.6.1. Báo cáo Word trong repo là bản cũ với cấu trúc mục 5.5 khác. Không sửa các tệp Word này.

## Dữ liệu và sự phê duyệt

Bộ gốc: `D:/NCKH/2026_Chatbot/BoTest_Chatbot_Nho_24Cau/BoTest_Chatbot_Nho_24Cau`. Manifest gốc ghi chưa được duyệt; người dùng đã xác nhận trực tiếp trong chat: **“Đã duyệt cả câu hỏi và đáp án; dùng nguyên bản”**. Ghi nhận này nằm trong audit và protocol mới, không sửa manifest gốc để che lịch sử.

Có 24 ca: 20 câu đơn và 4 câu có lịch sử cố định. TC01/TC05 cùng family, nên có 23 family. Giữ nguyên câu hỏi, thứ tự, lịch sử và answer key. Không tự sinh lại các lượt assistant của bốn ca lịch sử. Đây chưa phải phép đo hội thoại chạy tự do.

Hai nguồn chuẩn là catalog 53 sản phẩm và FAQ 30 mục. Tất cả source_refs trong answer key được kiểm tra tìm đúng một bản ghi. Hash catalog giữa package và repo khác do xuống dòng LF/CRLF; nội dung JSON và byte sau chuẩn hóa xuống dòng trùng nhau. Snapshot dùng đúng byte package cho hai nguồn này, giữ nguyên các file corpus/index khác. Index vẫn được kiểm tra current với tài liệu đã nạp; không rebuild hoặc bổ sung gold answers vào index.

Schema adapter chỉ đổi tên trường để dùng runner: case_id → id, group → category, giữ nguyên question/history/family_id. Mọi expected_answer, required_facts và expected_source trong input worker đều null; answer_key riêng cho người chấm. Các history assistant đã có là một phần input được duyệt, không được coi là đáp án mới do phương pháp sinh.

## Định nghĩa phương pháp

| Nhãn | Hiện thực | Những bước được dùng |
|---|---|---|
| B0 | GuardrailPolicy + matcher FAQ bằng luật | Đọc catalog/FAQ chuẩn; không vector/LLM; không khớp ghi no_rule_match; baseline luật không giải quyết history bằng mô hình |
| B1 | PlainLlmMethod | Base Qwen2.5-3B; prompt trung tính và history cố định; không KB/catalog/FAQ/vector/embedding |
| B2 | BasicRagMethod mới | Base 3B; raw semantic cosine top-5, ghép history vào query theo mẫu chung, PromptBuilder + LLM; không QueryRewriter/BM25/điều chỉnh miền/catalog routing/quản lý active product/postcheck; luôn thử gọi LLM |
| P | RagMethod và factory hiện có | Base 3B; sáu thành phần đều bật; giữ luật, FAQ, catalog, hybrid retrieval, fallback và prompt hiện hành |
| P+FT | Cùng RagMethod và sáu thành phần của P | Adapter 7B gốc đã xác minh qua HF NF4/BF16; chạy riêng |

B1/B2/P khóa `qwen2.5:3b`, `USE_PROJECT_CHAT_MODEL=false`, không lấy `techcare-support:3b-v1` từ profile demo. P+FT khóa alias, checkpoint revision và hash adapter đã xác minh; không thay bằng Ollama base 7B hoặc fallback 3B.

B2/P chia sẻ file system prompt, PromptBuilder, giới hạn context và generation settings. B2 không có structured active-product field. P có thể thêm ngữ cảnh sản phẩm theo thành phần quản lý sản phẩm; đó là khác biệt đã định nghĩa, không phải sửa prompt giữa các phương pháp. B1 dùng prompt trung tính của đối chứng không RAG; prompt thực tế từng lần gọi được lưu trong calls.

## Sáu phép loại bỏ thành phần

`RagComponents` mặc định bật tất cả, không đổi cấu hình demo. Mỗi ablation đổi đúng một boolean so với P; ChatService và Retriever nhận cùng đối tượng cấu hình.

| Biến thể | Phạm vi thật sự bị tắt | Phần vẫn giữ / tương tác |
|---|---|---|
| P-no-query-normalization | QueryRewriter trước semantic search | BM25 tokenizer và chuẩn hóa nhận diện ý định vẫn giữ; không gọi đây là loại mọi chuẩn hóa trong hệ thống |
| P-no-bm25 | Gọi BM25, ứng viên chỉ từ BM25, đóng góp từ vựng | Giữ hệ số vector 0,60, domain adjustment và ngưỡng 0,38; không chuẩn hóa lại trọng số; có tương tác thang điểm/fallback |
| P-no-domain-ranking | Toàn bộ score_adjustment | Giữ hybrid 0,60/0,40 và thứ tự top-k sau hợp nhất |
| P-no-product-context | Structured resolution từ câu hiện tại/page/history, trạng thái gợi ý/ngân sách lịch sử, ưu tiên/lọc/inject active-product context | Giữ catalog chuẩn, nhận diện sản phẩm trong luật trực tiếp và history thô cho LLM; đây là một nhóm cơ chế phụ thuộc nhau, không phải bỏ toàn bộ dữ liệu sản phẩm |
| P-no-postcheck | Lời gọi unsupported_claims sau sinh | Giữ lọc context, routing, admission/fallback trước sinh và system prompt; câu trả lời bằng luật không đi qua postcheck |
| P-no-rule-routing | Trả lời trực tiếp bằng luật/catalog/FAQ và các nhánh clarification trước sinh | Giữ quản lý ngữ cảnh, retrieval, admission theo phạm vi/điểm, lọc context và postcheck; vì vậy không bảo đảm mọi câu đều gọi LLM |

Router có thể trả lời trước retrieval. Vì vậy một ablation retrieval không tác động lên những câu đi thẳng qua luật/FAQ; phải báo số ca thật sự tới retrieval/postcheck, không kết luận thành phần vô ích chỉ vì cả batch giống nhau. Product-context là một can thiệp nhóm; các kết quả có tương tác với routing và prompt field, không diễn giải như tác động nhân quả độc lập của từng hook.

Giữ K=5, ngưỡng 0,38, hệ số 0,60/0,40, temperature=0, context 4096, output tối đa 384 và repeat_penalty=1. Không khảo sát lại K/threshold trên bộ đã duyệt để tối ưu kết quả. Nếu sửa lỗi làm thay đổi code/prompt/corpus, tạo study version mới và chạy lại các phần liên quan.

## Lệnh tái lập

Tất cả lệnh dưới đây chạy trong `backend` bằng Python của môi trường ứng dụng. Runtime GPU chỉ dùng khi khởi động server 7B.

Study dùng cho bảng kết quả chính là **v2**. V1 được giữ nguyên nhưng loại khỏi bảng chính do timestamp kỹ thuật của database chưa cố định. V2 dùng thời điểm tạo snapshot cho created_at/updated_at của mọi bản ghi thử; đây không phải ngày xác minh hãng mới. Controller kiểm tra trực tiếp timestamp và giá/bảo hành/spec của cả 53 bản ghi trong mỗi worker.

Study đã khóa ở:

```text
D:/NCKH/2026_Chatbot/Code/NCKH_chatbot/.local/chapter5-24-20261015T145015Z/study-v2
```

Tạo study mới (đường dẫn đích phải chưa tồn tại), không sửa study cũ:

```powershell
python -B -m benchmark.chapter5 prepare --package 'D:\NCKH\2026_Chatbot\BoTest_Chatbot_Nho_24Cau\BoTest_Chatbot_Nho_24Cau' --study '<study-v3>' --approval-record '..\.local\chapter5-24-20261015T145015Z\audit\initial.json'
```

Trong terminal chạy thử, đặt database dự phòng tách khỏi database ứng dụng:

```powershell
$env:DATABASE_URL='sqlite:///D:/NCKH/2026_Chatbot/Code/NCKH_chatbot/.local/chapter5-24-20261015T145015Z/controller-only.db'
$env:ENVIRONMENT='test'
$env:WARM_AI_ON_STARTUP='false'
$study='..\.local\chapter5-24-20261015T145015Z\study-v2'
python -B -m benchmark.chapter5 run --study $study --phase smoke --methods B0 B1 B2 P P-no-query-normalization P-no-bm25 P-no-domain-ranking P-no-product-context P-no-postcheck P-no-rule-routing --timeout 60
python -B -m benchmark.chapter5 run --study $study --phase main --methods B0 B1 B2 P --timeout 60
python -B -m benchmark.chapter5 run --study $study --phase ablation --methods P P-no-query-normalization P-no-bm25 P-no-domain-ranking P-no-product-context P-no-postcheck P-no-rule-routing --timeout 60
```

Smoke dùng đúng ba case đã khóa trước chạy: TC05 (không dấu), TC11 (thiếu căn cứ biến thể), TC23 (history ANC). Controller chỉ cho chạy main/ablation sau khi smoke đúng model, input/history, routing và cấu hình đã đạt. Unit test với nguồn giả được ghi là unit; kết quả benchmark luôn là model thật.

P+FT: xem [cách khởi động server](MODELS_AND_BENCHMARK.md). Kiểm tra `ollama ps`, dừng model chat 3B đang chiếm VRAM nếu cần, chờ `/health` có đúng identity và ready. Không tự tắt server/dịch vụ không thuộc phiên thử.

```powershell
python -B -m benchmark.chapter5 run --study $study --phase smoke --methods 'P+FT' --timeout 60
python -B -m benchmark.chapter5 run --study $study --phase supplementary --methods 'P+FT' --timeout 60
python -B -m benchmark.chapter5 collect --study $study
```

Mỗi lần run tạo thư mục UTC+UUID, raw JSONL/CSV, manifest, request/response/worker log và protocol_validation. Mỗi worker có database riêng. Controller chặn khi hash code, input, corpus hoặc prompt đổi. Những lỗi vận hành được giữ nguyên; không lấy số hoàn tất làm số đúng.

## Chấm và metric

`collect` tạo một thư mục analysis mới, tables.json/csv và mẫu chấm mù JSONL/CSV. Cấp một bản trống riêng cho mỗi người chấm cùng package nguồn; **không cấp review_mapping_private.json**. Có thể suy ra phần nào phương pháp từ cách viết/nguồn nên che nhãn không bảo đảm mù hoàn toàn. Template gồm nhiều phase; đối chiếu khóa riêng từng row, không gộp hai lượt P thành một câu trả lời.

Theo hướng dẫn gốc: 2 điểm đáp ứng đủ tiêu chí, không lỗi nghiêm trọng; 1 đúng một phần và không sai/bịa dữ kiện cốt lõi; 0 sai cốt lõi, sai đối tượng, bịa cam kết, từ chối sai hoặc lỗi không có phản hồi. Mỗi người tự chấm toàn câu, kể cả nội dung thêm; sau đó xử lý bất đồng. Chưa chấm thì mọi điểm/tỷ lệ nội dung giữ null/NOT_REVIEWED, kể cả khi hệ thống đã chạy hết.

- Tỷ lệ đạt đủ: số ca 2 điểm / 24, công bố cả số đếm.
- Điểm trung bình: tổng điểm / 24, thang 0–2. Khi đã chấm, lỗi/timeout không phản hồi nhận 0 theo rubric; ghi riêng số lỗi.
- Phát biểu ngoài nguồn: số ca được chấm unsupported_claim=true / 24; đồng thời báo mẫu số các ca có phản hồi được chấm để không che lỗi không trả lời. null không được coi là false.
- Error/timeout và not_ready: số lượt thuộc trạng thái / tổng lượt của phương pháp. no_rule_match riêng, không tự coi là đúng/sai ngữ nghĩa.
- Latency: median/mean trên lượt thành công, p95 nearest-rank khi có ít nhất 20 mẫu; báo n, mode và số lỗi. latency_ms gồm xử lý câu cuối, không gồm import/seed process; wall_ms có phần đó. Đây chưa phải latency đầu cuối trình duyệt/API.
- Tỷ lệ gọi LLM: đếm calls thật của câu cuối / 24; không suy từ mode. History cố định không sinh setup answer.
- Delta ablation: median biến thể − median P trong cùng batch ablation; số ca gọi LLM biến thể − P. Delta chất lượng bằng điểm/tỷ lệ biến thể − P sau chấm; hiện để null. Không diễn giải delta latency của một lượt chạy như bằng chứng nhân quả.
- Recall@5/MRR cần gán nhãn đầy đủ chunk liên quan. Package chỉ có source_refs tới bản ghi catalog/FAQ, chưa có qrels ở mức chunk; giữ NOT_REVIEWED, không thay bằng kiểm tra URL/ID xuất hiện.

24 case/23 family nhỏ, nguồn tác giả và mức độc lập chưa được xác nhận bằng việc nhóm duyệt. overlap_check chỉ kiểm tra chuỗi trong một phần dữ liệu đã đóng gói. Muốn suy luận thống kê cần đánh giá ghép cặp theo family/đơn vị hội thoại và nhãn đáng tin cậy; chưa chấm thì không chạy McNemar hoặc điền p-value. P+FT thay cả kích thước, runtime và lượng tử hóa so với P nên không cô lập hiệu quả fine-tuning.
