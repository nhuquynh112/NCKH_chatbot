# Hồ sơ thực nghiệm Chương 5 — bộ TechCare 24 câu

Hồ sơ này dành cho mục **5.5 so sánh B0/B1/B2/P** và **5.6.1 loại bỏ thành phần**. P+FT 7B được trình bày riêng. Cấu hình/lệnh tái lập ở [CHAPTER5_RUNBOOK.md](CHAPTER5_RUNBOOK.md); cách tự chạy UI và chụp ảnh ở [DEMO_UI_CHAPTER5.md](DEMO_UI_CHAPTER5.md).

## Trạng thái và phạm vi bằng chứng

PASS trong hồ sơ là chạy đúng giao thức và không lỗi hệ thống, không phải đáp án được chấm đúng. Điểm 0–2, tỷ lệ đạt đủ tiêu chí và phát biểu không được nguồn hỗ trợ chưa có người chấm thì để null/NOT_REVIEWED. Không dùng số lượt hoàn tất hoặc keyword matching làm accuracy.

Study dùng cho bảng chính: [.local/chapter5-24-20261015T145015Z/study-v2](../.local/chapter5-24-20261015T145015Z/study-v2/protocol.json). Thời điểm tạo snapshot kỹ thuật: `2026-10-15T15:26:00.959466+00:00`. Mỗi worker dùng database riêng; created_at/updated_at của catalog được cố định theo timestamp này, không phải xác nhận mới từ nhà sản xuất.

V1 được giữ nguyên nhưng không dùng cho bảng chính vì timestamp database khi đó sinh lại theo từng worker. Đã lưu [lý do chuyển version](../.local/chapter5-24-20261015T145015Z/audit/v1_superseded.json), raw output và source code v1. V2 chạy lại smoke và các phương pháp liên quan; không đổi câu hỏi, đáp án, system prompt hoặc nội dung corpus để làm tăng điểm.

Đây là benchmark tại lớp dịch vụ AI/RAG, không đo toàn bộ HTTP/UI. P dùng factory hiện có, corpus cố định và các luật/FAQ biên tập; không lấy FAQ quản trị đang thay đổi từ database ứng dụng thật. Demo UI có thêm tầng nghiệp vụ, lưu lịch sử và bảng FAQ được nạp từ cùng snapshot; routing có thể khác ở tầng FAQ nghiệp vụ. Ảnh UI không thay thế raw outputs của benchmark.

## Audit đề cương, dữ liệu và Git

- Bản `D:/NCKH/2026_Chatbot/BaoCao_15_10/BaoCao.docx` có đúng mục 5.5/5.6.1 và mô tả sáu thành phần. Đã lưu [trích xuất các đoạn liên quan và hash](../.local/chapter5-24-20261015T145015Z/audit/current_outline_sections.json). Tệp trong De_Cuong_20_10 là mẫu trống; Word trong repo là bản cũ có cấu trúc mục khác.
- [HEAD](../.local/chapter5-24-20261015T145015Z/audit/git-head.txt) là `1cef995f95b3b315037e2102fd82488e621e0370`, nhánh `chatbot-v1`; working tree đã có thay đổi trước khi làm. Source code thực nghiệm được khóa bằng hash và sao chép vào `study-v2/code_snapshot/`, không giả định HEAD chứa toàn bộ thay đổi chưa commit.
- Không sửa các Word của người dùng, `.env`, database thật, frontend, API contract/auth/schema, checkpoint/adapter hoặc dữ liệu huấn luyện. Các thay đổi thực nghiệm nằm ở component switches, benchmark/worker/controller, test và tài liệu. Không commit/push/đổi nhánh.
- Bộ gốc tại `D:/NCKH/2026_Chatbot/BoTest_Chatbot_Nho_24Cau/BoTest_Chatbot_Nho_24Cau`. Manifest ban đầu ghi chưa duyệt; người dùng xác nhận trực tiếp **“Đã duyệt cả câu hỏi và đáp án; dùng nguyên bản”**. [Audit ban đầu](../.local/chapter5-24-20261015T145015Z/audit/initial.json) và protocol lưu xác nhận, không sửa lịch sử manifest gốc.
- Có 24 ca duy nhất: 20 câu đơn, 4 ca history cố định, 23 family vì TC01/TC05 cùng họ diễn đạt. Input và answer key khớp câu hỏi, thứ tự, group, family và history. Tất cả source_refs phân giải được tới đúng một bản ghi.
- Catalog package khác byte repo vì LF/CRLF; nội dung JSON và byte sau chuẩn hóa xuống dòng bằng nhau. Corpus mới giữ đúng byte nguồn được duyệt. FAQ giống cả byte. Không điều chỉnh đáp án chuẩn theo output của model.
- [Kiểm tra trùng mới](../.local/chapter5-24-20261015T145015Z/audit/overlap_recheck.json): 6 JSONL có sẵn, 246 user messages, không có câu hiện tại trùng chuỗi sau chuẩn hóa. Phép kiểm tra này có cả một số tệp phát triển/đánh giá đã đóng gói; không chứng nhận sạch gần trùng ngữ nghĩa, không xác nhận độc lập tác giả và không thay đánh giá holdout.

`test_inputs.jsonl` chỉ được chuyển schema, giữ nguyên question/history. `answer_key.jsonl` và tiêu chí chấm nằm ngoài input worker/prompt/RAG. Các lượt assistant có sẵn trong history là input được duyệt; chỉ chấm lượt cuối, không sinh lại history cho từng phương pháp.

## Cấu hình thực tế

| Thành phần | Giá trị đã khóa / nguồn |
|---|---|
| Mô hình chính B1/B2/P/ablation | Base `qwen2.5:3b`, Q4_K_M, digest `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b` |
| Embedding | `nomic-embed-text:latest`, F16, digest `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f` |
| Runtime chính | Ollama 0.40.4; Python và từng model identity được lưu trong run manifest/raw rows |
| Máy | Intel i5-10400F, 6 nhân/12 luồng; RAM 17.072.328.704 byte (~15,9 GiB); RTX 3060 12.288 MiB, driver 617.14; Windows |
| Nguồn | 53 sản phẩm, 30 FAQ; index 195 đoạn = 112 KB + 53 catalog + 30 FAQ; không phải 195 tệp |
| RAG | JSON index, Nomic task prefix, top-k=5, ngưỡng 0,38; P hybrid 0,60 vector + 0,40 BM25/(BM25+3), cộng điều chỉnh miền |
| Generation | temperature=0, num_ctx=4096, num_predict tối đa 384, repeat_penalty=1; greedy; thời hạn worker 60 giây |
| History | Dùng nguyên 4 history được cấp; các history đều nằm trong giới hạn 6 tin của PromptBuilder |
| Prompt | B1 trung tính; B2/P dùng cùng file system prompt và PromptBuilder. Structured product field chỉ có khi thành phần đó của P hoạt động |
| Warm-up | Ba ca smoke công bố trước mỗi phương pháp; không có warm-up cân bằng riêng. Desktop/background load chưa được kiểm soát hoàn toàn |

[Runtime ban đầu](../.local/chapter5-24-20261015T145015Z/audit/runtime_initial.json) và [CPU/RAM/OS](../.local/chapter5-24-20261015T145015Z/audit/host.json) là log đọc thật. Từng run lưu hash input, corpus, source code, prompt, model digest, generation config và timestamp. Controller kiểm tra cả 53 bản ghi giá/bảo hành/spec và timestamp trong database của từng worker.

## 5.5 — So sánh bốn phương pháp

| Nhãn | Đường chạy thật |
|---|---|
| B0 | Luật catalog + matcher FAQ, không LLM/vector; không khớp ghi no_rule_match; nhận history nhưng baseline luật không giải quyết history bằng mô hình |
| B1 | LLM 3B với câu hỏi/history, không đọc KB/catalog/FAQ/index hoặc gọi embedding |
| B2 | RAG cơ bản mới: semantic cosine top-5 → shared prompt → LLM; không BM25, domain ranking, active-product management, direct routing hay postcheck |
| P | Factory và pipeline hiện có, sáu thành phần đều bật, base 3B; luật/FAQ có thể trả lời trước LLM |

B2 chưa tồn tại riêng trước tác vụ này; thiếu sót đã được báo trước khi chạy chính thức. Không dùng M3 cũ dưới cả hai nhãn B2 và P. B2/P giữ cùng nguồn nhưng khác kiến trúc được định nghĩa; B2 luôn thử sinh, P có routing/admission. Đây là so sánh toàn hệ thống, không cô lập riêng retriever.

<!-- MAIN_TABLE -->

## 5.6.1 — Loại bỏ thành phần

Mỗi biến thể đổi một boolean trong `RagComponents`; ChatService và Retriever nhận cùng cấu hình. Unit test xác minh các lời gọi thật sự bị bỏ qua và những khác biệt hành vi tối thiểu. Trace thực nghiệm lưu raw vector score, BM25 score, hybrid score, domain adjustment, top-k, structured product resolution và bước postcheck.

| Biến thể | Phần bỏ | Ranh giới cần lưu ý |
|---|---|---|
| P đầy đủ | Không có | Đối chứng chạy lại trong batch ablation |
| P-no-query-normalization | QueryRewriter trước semantic search | BM25 tokenizer và intent folding vẫn giữ |
| P-no-bm25 | Nhánh BM25 và đóng góp/ứng viên chỉ từ nhánh này | Giữ 0,60 vector và ngưỡng 0,38, không renormalize; có tương tác thang điểm |
| P-no-domain-ranking | score_adjustment | Hybrid vẫn giữ |
| P-no-product-context | Structured product resolution, state gợi ý/ngân sách lịch sử, ưu tiên/lọc/inject active product | Một nhóm cơ chế phụ thuộc nhau; giữ catalog thật, luật trực tiếp và history thô cho LLM |
| P-no-postcheck | unsupported_claims sau sinh | Giữ các guard trước sinh và system prompt |
| P-no-rule-routing | Direct intent/catalog/FAQ/clarification responses | Giữ product context, retrieval admission, context filtering và postcheck |

<!-- ABLATION_TABLE -->

Chênh lệch median = median biến thể − median P trong batch ablation, không phải median của các hiệu ghép cặp. Chênh số gọi LLM = số của biến thể − số của P. Delta chất lượng chỉ tính sau khi chấm cùng 24 case, hiện null. Bảng là mô tả một lượt chạy; không diễn giải như tác động nhân quả độc lập hoặc kết luận thống kê.

Một thành phần có thể không được chạm tới khi router đã trả lời. Phải đọc số ca tới retrieval/generation/postcheck cùng kết quả; không coi output giống nhau là bằng chứng thành phần không có tác dụng. Cờ product-context là một can thiệp nhóm, không tách riêng tác dụng từng hook; bỏ BM25 thay phân bố điểm trước fallback.

## P+FT 7B — bổ sung

Nhiệm vụ này quy định P+FT là **7B**. Trong bản báo cáo Word, mục QLoRA cũ chủ yếu mô tả mô hình 3B với 170 mẫu/2 epoch; không được trộn các số đó vào nhánh 7B 37 train/9 validation/1 epoch.

7B dùng checkpoint `unsloth/Qwen2.5-7B-Instruct-bnb-4bit`, revision `bdd404162d94997f390efbfa660eb3f21cbbc81d` và adapter gốc tại `D:/NCKH/Codex/training_runs/csconda_7b_epoch1_20261014/adapter`. Không merge/chuyển đổi/train lại. Client kiểm tra checkpoint hash `99b85155b7bb40344d8c3938c8ec1147b27028804bca5d2e5559cb8e6533747d` và adapter hash `b7650bf5a6a4eb02b902bb9a5758d178c3e4f32c5329013ca7c819045d8008b7`.

<!-- FT_TABLE -->

P+FT giữ cùng pipeline/corpus/case/prompt/settings nhưng đổi đồng thời kích thước model, weights, NF4/BF16, runtime và chat template so với Ollama 3B Q4_K_M. Vì vậy đây không phải ablation cô lập fine-tuning. Không sử dụng 8 synthetic cases pilot hoặc benchmark 20 câu cũ làm số liệu cho bảng 24 câu này.

## Metric còn chờ chấm

Hai người chấm độc lập, không biết nhãn phương pháp, theo rubric gốc: 2 đủ tiêu chí/không lỗi nghiêm trọng; 1 đúng một phần, không sai/bịa cốt lõi; 0 sai cốt lõi/sai đối tượng/bịa cam kết/từ chối sai hoặc không có phản hồi do lỗi. Sau đó giải quyết bất đồng. Không coi null là 0 hoặc false khi chưa chấm.

- Số ca 2 điểm / 24; điểm trung bình = tổng điểm / 24, thang 0–2.
- Số ca unsupported_claim=true / 24; đồng thời báo mẫu số các phản hồi thực tế được chấm. Chấm cả các phát biểu thêm ngoài câu hỏi.
- Nguồn đúng/bám nguồn, tuân thủ chính sách, độ phù hợp, hỏi lại/chuyển tiếp đúng và từ chối nhầm: chưa có nhãn nội dung đáng tin cậy, NOT_REVIEWED.
- Recall@5/MRR: chưa có qrels đầy đủ ở mức chunk; source_refs tới bản ghi không thay cho tập chunk liên quan. Không lấy source presence làm chất lượng retrieval.
- McNemar, CI bootstrap, kappa và p-value: chưa tính khi không có nhãn độc lập. Nếu tính sau, cần ghép cặp và gom family TC01/TC05, không coi 24 case là 24 quan sát độc lập hoàn toàn.

<!-- REVIEW_OUTPUT -->

## Kiểm thử, lỗi và giới hạn

| Kiểm tra | Trạng thái | Bằng chứng |
|---|---|---|
| Unit toàn bộ sau thêm component switches | PASS — 134/134 | [unit-all.log](../.local/chapter5-24-20261015T145015Z/unit-all.log), gồm 10 test Chương 5 mới |
| Worker/model/schema sau sửa timestamp v2 | PASS — 29/29 | [unit-v2.log](../.local/chapter5-24-20261015T145015Z/unit-v2.log) |
| Hồi quy hội thoại | PASS — 225/225 | [regression.log](../.local/chapter5-24-20261015T145015Z/regression.log) |
| Input và quyền API | PASS — 4 kiểm tra | [regression-report.md](../.local/chapter5-24-20261015T145015Z/regression-report.md) |
| Tải API đồng thời lần đầu | FAIL — 11/16; toàn job API 4/5 | Cùng log trên ghi OperationalError; chưa xác định chắc nguyên nhân gốc |
| Chạy riêng phần chẩn đoán tải | PASS — 16/16 | [concurrency-diagnostic.json](../.local/chapter5-24-20261015T145015Z/concurrency-diagnostic.json); không tái hiện lỗi, không sửa/nới test; không tuyên bố lỗi đã được khắc phục |
| Smoke v2 | PASS — 30/30 xác nhận giao thức | [smoke log](../.local/chapter5-24-20261015T145015Z/smoke-v2-driver.log), validation JSON trong run |
| UI trên trình duyệt, ảnh minh chứng | NOT_REVIEWED — người dùng tự thao tác | [Checklist và câu hỏi có nguồn](DEMO_UI_CHAPTER5.md); không suy UI PASS từ API/unit |
| Chất lượng ngữ nghĩa | NOT_REVIEWED | Không điền số đúng/accuracy/hallucination từ keyword hoặc status ok |

<!-- FINAL_CHECKS -->

Latency ở đây là xử lý câu cuối trong worker sau import/seed/preflight, không gồm toàn bộ API, trình duyệt hoặc ghi lịch sử/ticket. p95 nearest-rank trên 24 mẫu là ước lượng thăm dò, chưa ổn định; cần đọc mode, số lời gọi LLM và lỗi cùng số đo. Máy đang chạy desktop, cold/warm và tải nền chưa được kiểm soát hoàn toàn. Peak VRAM torch của 7B nếu có không phải tổng VRAM hay chi phí tăng thêm của một request, và không có phép đo chi phí tương đương đáng tin cậy cho mọi phương pháp.

Bộ nhỏ được nhóm duyệt không tự trở thành holdout độc lập. Người triển khai đã đọc câu hỏi để chuẩn bị adapter schema/giao thức; ba ca smoke cũng thuộc bộ này. Không sửa prompt/luật theo lỗi nội dung giữa các phương pháp. Khi dùng kết quả này để cải tiến hệ thống, coi bộ 24 câu là DEV và tạo một test khóa mới cho kết luận tiếp theo.
