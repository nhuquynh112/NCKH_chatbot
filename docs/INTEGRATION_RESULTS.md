# Kết quả tích hợp 7B và chuẩn bị benchmark

Ngày thực hiện: 15/10/2026, nhánh `chatbot-v1`. **Đã xác minh thử nghiệm 7B** và đã chạy inference với adapter gốc qua dịch vụ mới. Không huấn luyện lại. Model demo mặc định vẫn do profile 3B hiện có chọn; bật 7B bằng `CHAT_PROVIDER=hf_lora` theo [hướng dẫn](MODELS_AND_BENCHMARK.md).

## Phạm vi và cấu trúc

Trước:

```text
backend/
  app/                  # API, nghiệp vụ, AIService, RAG
  rag_data/             # Tri thức và index demo
  models/               # Gói 3B đã được lưu từ trước
  training/             # Code huấn luyện đã có
  tests/                # 105 unit tests cũ
frontend/
BaoCao/
README.md, DATASET_CANDIDATES.md, CHATBOT_IMPROVEMENTS.md, ...
D:/NCKH/Codex/           # Cache/runtime/run huấn luyện bên ngoài repo
```

Sau: giữ nguyên toàn bộ vị trí cũ, bổ sung:

```text
backend/
  app/model_client.py
  model_serving/
    server.py
    profiles/qwen25_7b.json
  benchmark/
    methods.py, schema.py, worker.py, run.py, scoring.py, review.py
    prompts/plain.txt
    datasets/techcare_v1.json
    README.md
  tests/test_model_serving.py, test_benchmark.py
  .env.example
docs/INTEGRATION_PLAN.md, MODELS_AND_BENCHMARK.md, INTEGRATION_RESULTS.md
.local/                 # Bị Git bỏ qua
  integration-7b-20261015/   # Log, database thử và bằng chứng API
  benchmark_results/        # Mỗi run UTC+UUID, không ghi đè
```

| Tệp/nhóm | Thay đổi và lý do |
|---|---|
| `backend/app/config.py` | Provider/URL 7B và tên model tập trung; giữ cách chọn profile 3B |
| `backend/app/model_client.py` (mới) | HTTP client kiểm tra đúng identity/hash; embedding vẫn qua Ollama; lỗi 7B không fallback 3B |
| `backend/app/rag/chat_service.py` | Dùng client factory, chuyển lỗi ModelNotReady lên AIService; không đổi retriever/guardrail |
| `backend/app/main.py` | Warm-up/readiness dùng provider đã chọn, giữ trường API hiện có |
| `backend/app/services/ai_service.py` | Kiểm tra readiness 7B và thông báo ai_unavailable rõ ràng, giữ luồng ticket |
| `backend/model_serving/` (mới) | Profile provenance, server loopback nạp trực tiếp checkpoint NF4 và adapter PEFT |
| `backend/benchmark/` (mới) | Bốn phương pháp, snapshot, schema 20 câu, trace, timeout, CSV/JSONL, rubric/review |
| Hai file test mới | 19 test cho model/pipeline, hash, timeout, M2 không RAG, M4 không fallback, schema/metric |
| `backend/.env.example` | Ví dụ provider; file mẫu trước đó bị quy tắc `.env.*` bỏ qua, nay được phép theo dõi |
| `.gitignore` | Bỏ qua `.local/`, benchmark_results và weights mới; giữ các tệp LFS đã được theo dõi |
| `README.md`, `docs/` | Kế hoạch, cách chạy, nguồn artifact, kết quả và giới hạn |

Không di chuyển/xóa tệp. Không commit, push hoặc đổi branch. Không sửa `.env`, schema/migration/database thật, router/schema API, auth, frontend, requirements/lockfile, RAG corpus/index/prompt gốc, training code, weights 3B hoặc artifact 7B gốc. Các báo cáo nghiên cứu cũ được giữ nguyên; hồi quy lần này xuất sang `.local/`.

`BaoCao/BaoCao_Chatbox.docx` đã có thay đổi từ trước. Trong quá trình làm việc, trạng thái Git còn xuất hiện các tệp `BaoCao/BAO_CAO_1_*` từ hoạt động ngoài tác vụ này; không sửa, di chuyển hoặc dọn chúng. File khóa Word có thể xuất hiện/biến mất theo ứng dụng Word.

## Bằng chứng pilot gốc

| Nội dung xác minh | Giá trị | File gốc |
|---|---|---|
| Model nền | `unsloth/Qwen2.5-7B-Instruct-bnb-4bit`, revision `bdd404162d94997f390efbfa660eb3f21cbbc81d` | `D:/NCKH/Codex/training_runs/csconda_7b_epoch1_20261014/run.json`, checkpoint manifest trong cache |
| Train/validation | 37/9, 1 epoch, 10 bước | `run.json`: source, training_metrics, log_history |
| Thời điểm bắt đầu | 14/10/2026 09:53:28 UTC, tức 16:53:28 Việt Nam | `run.json`: started_utc |
| Thời gian tối ưu | training_seconds 20.344 giây; Trainer train_runtime 20.1266 giây, không gồm toàn bộ nạp model/đánh giá | `run.json` |
| Cấu hình | QLoRA NF4, BF16; rank 8, alpha 16, q_proj/v_proj, LR 5e-5, max length 512; 2.523.136 tham số trainable | `run.json`, `adapter/adapter_config.json` |
| Validation loss | 3.723275 → 3.675476 | `run.json`: validation_before/after |
| 8 câu synthetic | 6/8 trước và sau theo tiêu chí tự động; không chứng minh hiệu quả tổng quát | `run.json`, `controlled_benchmark.json` trong cùng run |
| Log thô | Tiến trình train/đánh giá | `D:/NCKH/Codex/evaluation_artifacts/qlora_epoch1.log` |
| Dữ liệu đã chuẩn bị | 46 cặp được giữ: 12 đáp án nguồn nguyên bản, 34 đáp án biên tập; chia nhóm 37/9 | `D:/NCKH/Codex/training_cache/csconda_prepared_grouped` |

Thông tin này phù hợp với `DATASET_CANDIDATES.md`, phần lịch sử model trong `README.md` và `CHATBOT_IMPROVEMENTS.md`: 7B là pilot riêng, model demo trước đây chọn 3B đã train. Lần này thêm khả năng chọn 7B qua provider riêng, không sửa lại kết quả lịch sử để gọi nó là model đã triển khai từ trước.

Server dùng `adapter_model.safetensors` (~10 MB), không dùng `adapter-f16.gguf` đã bị Ollama từ chối. Base weights có 5.547.254.622 byte. Hash được đối chiếu đầy đủ khi nạp server và kiểm tra lại bằng code cuối cùng ở [artifact_verification.json](../.local/integration-7b-20261015/artifact_verification.json). Hash đầy đủ, đường dẫn và lệnh xác minh nằm trong [hướng dẫn model](MODELS_AND_BENCHMARK.md#artifact-gốc-và-kiểm-tra-identity).

Nguồn RAG hiện có gồm 195 đoạn/tài liệu được lập chỉ mục: 112 đoạn KB + 53 sản phẩm + 30 FAQ. Đây không phải 195 tệp nguồn. Dữ liệu CSConDa dùng cho train, corpus TechCare dùng retrieval, và 20 câu đánh giá mới nằm ở ba vị trí riêng. Không thêm gold answers vào corpus hoặc train.

## Kiểm thử đã chạy

Các đường dẫn dưới đây là output thật ở checkout này; `.local/` không được đưa vào Git.

| Kiểm tra | Trạng thái | Bằng chứng |
|---|---|---|
| Syntax/import/schema | PASS | 60 file Python parse được; dataset 20 case hợp lệ; [syntax.json](../.local/integration-7b-20261015/syntax.json), unit log |
| Unit test toàn bộ | PASS — 124/124 | [unit-complete.log](../.local/integration-7b-20261015/unit-complete.log), gồm 105 test cũ + 19 test mới |
| Provider/pipeline mới | PASS — 19/19 | [unit-new.log](../.local/integration-7b-20261015/unit-new.log); M2 không đọc RAG/embedding, M3 factory hiện có, M4 sai identity/thiếu server không fallback, index thiếu dùng lexical, timeout rõ |
| Hồi quy catalog/API | PASS — 225/225, API 5/5, đồng thời 16/16 | [regression.log](../.local/integration-7b-20261015/regression.log), [báo cáo lần chạy](../.local/integration-7b-20261015/EVALUATION_REPORT.md) |
| FAQ/RAG cũ, online | PASS — 32/32 | [quality-online.log](../.local/integration-7b-20261015/quality-online.log), JSON trong evaluation_artifacts; generative_cases=0 |
| FAQ/RAG cũ, offline | PASS — 32/32 | [quality-offline.log](../.local/integration-7b-20261015/quality-offline.log); semantic bị gián đoạn, pipeline dùng BM25; generative_cases=0 |
| API 7B thật, lịch sử/ticket | PASS | [api_smoke.json](../.local/integration-7b-20261015/api_smoke.json): ready đúng model/hash; HTTP 201, intent llm+rag, phản hồi khoảng 20,7 giây; 4 message lưu được, yêu cầu nhân viên tạo ticket |
| API khi 7B ngừng | PASS | [api_unavailable.json](../.local/integration-7b-20261015/api_unavailable.json): ready degraded, giữ tên 7B, intent ai_unavailable và tạo ticket |
| Runner khi 7B ngừng | PASS cho xử lý lỗi | [run not_ready](../.local/benchmark_results/20261015T124606Z-332db843/results.jsonl), mã thoát 2; không phải kết quả chất lượng M4 |
| Frontend lint | PASS | [frontend-lint.log](../.local/integration-7b-20261015/frontend-lint.log) |
| Frontend production build | PASS | [frontend-build.log](../.local/integration-7b-20261015/frontend-build.log), output riêng trong `.local/` |
| Benchmark M1–M4 | PASS về vận hành — 80 lượt, không error/timeout/not_ready | Hai run và [đối chiếu snapshot](../.local/integration-7b-20261015/benchmark-comparison.json) bên dưới; M1 có 6 no_rule_match |
| Xuất review và giữ raw output | PASS | [review-export.log](../.local/integration-7b-20261015/review-export.log); xuất thử template chưa chấm, các human metrics vẫn null |
| Trình duyệt và thao tác UI đầy đủ | CHƯA KIỂM TRA — cần kiểm tra thủ công | Không suy ra UI hoạt động từ lint/build hoặc API |
| Chất lượng ngữ nghĩa benchmark | CHƯA CHẤM | Các human metrics vẫn null; có review_template và rubric |

Unit log có cảnh báo deprecation TestClient/httpx và hai kết nối SQLite chưa đóng khi process test kết thúc; test vẫn đạt. Không nâng dependencies hoặc sửa test cũ để bỏ cảnh báo. Một lần chạy unit trong sandbox bị dừng khi không tiến triển; kết quả dùng ở bảng là lần chạy hoàn chỉnh ngoài sandbox trên database thử riêng.

Bước duyệt quyền từng bị gián đoạn do hạn mức, sau đó hoạt động lại. Một lệnh đánh giá bị từ chối vì chưa khai báo DATABASE_URL ngay trong lệnh; đã bổ sung SQLite riêng và chạy lại thành công. Các lỗi môi trường này không được tính là lỗi model hoặc PASS của một lệnh chưa chạy.

## Kết quả benchmark mới

M4: [run 20261015T124023Z-45f1b972](../.local/benchmark_results/20261015T124023Z-45f1b972/summary.json). Bộ chính M1/M2/M3: [run 20261015T125100Z-bf09b9fd](../.local/benchmark_results/20261015T125100Z-bf09b9fd/summary.json). Cả hai run hoàn tất, không lỗi retrieval. M2/M3 có identity đúng base `qwen2.5:3b`; M3/M4 dùng semantic index 195 tài liệu. Dataset, corpus, code, prompt, thứ tự case, generation settings, số lượt lặp và timeout khớp nhau; corpus gốc sau kiểm thử vẫn khớp hash snapshot. Xem [đối chiếu bằng máy](../.local/integration-7b-20261015/benchmark-comparison.json).

| Phương pháp | Trạng thái 20 câu | Câu cuối gọi LLM | Median pipeline (ms) | p95 pipeline (ms, n=20) |
|---|---|---:|---:|---:|
| M1 | 14 ok; 6 no_rule_match | 0 | 21,1 | 31,7 |
| M2 | 20 ok | 20 | 739,3 | 3.495,6 |
| M3 | 20 ok | 4 | 55,5 | 1.354,9 |
| M4 | 20 ok | 4 | 54,3 | 7.673,3 |

Đây là thống kê vận hành, không phải tỷ lệ đáp án đúng. Cả bốn phương pháp có error_timeout_rate=0 và not_ready_rate=0 trong hai run này. Kiểm tra literal đạt lần lượt 6/7, 1/7, 7/7, 7/7; không gọi là accuracy. M3/M4 có nguồn kỳ vọng xuất hiện ở 4/6 câu có tiêu chí source presence, chưa chứng minh nguồn đúng về ngữ nghĩa. M1/M2 không xuất nguồn RAG nên số source presence bằng 0 là hệ quả thiết kế, cần diễn giải riêng. Tất cả human metrics chưa chấm là null.

M4 chạy trước, sau đó dừng GPU server và thực hiện kiểm tra hồi quy rồi chạy M1/M2/M3. Cold/warm state chưa được kiểm soát; bảng latency chỉ dùng thăm dò, chưa đủ làm kết luận hiệu năng công bằng. Một lần chạy 20 câu cũng chưa đủ để p95 ổn định.

M4 có 4 câu cuối gọi LLM và 1 lời gọi LLM ở lượt setup lịch sử. Trace generation ghi đúng hai hash, `NF4/BF16`, GPU RTX 3060, token count và peak allocated torch khoảng 8,3 GiB. Các câu còn lại không được tính thành “7B sinh câu trả lời”. Bộ smoke 3 câu chạy trước đó nằm riêng tại `20261015T075634Z-0ec3d1cc`; không gộp vào benchmark 20 câu.

## Việc người phụ trách cần làm

1. Bật provider theo [hướng dẫn](MODELS_AND_BENCHMARK.md), khởi động lại backend và server 7B khi muốn demo. Các dịch vụ test trên cổng 8002/8011 được dọn sau kiểm tra; cấu hình `.env` mặc định không tự đổi.
2. Kiểm tra UI thật: đăng nhập, tạo phiên, câu sinh LLM, xem nguồn, tải lại lịch sử, yêu cầu nhân viên và ticket, thử model ngừng. Không dùng database thật để chạy bộ kiểm thử tự động.
3. Duyệt 20 case và nguồn expected answer; chấm mù output bằng `review_template.jsonl`, ghi reviewer/notes rồi chạy `python -B -m benchmark.review`. Không biến kết quả literal thành accuracy.
4. Nếu cần kết luận nghiên cứu, bổ sung holdout độc lập, thêm lượt lặp/warm-up và báo mẫu số. M4 thay đổi đồng thời model size, lượng tử hóa, runtime và fine-tuning; không thể quy khác biệt M3–M4 chỉ cho QLoRA. Muốn cô lập cần base 7B cùng runtime/precision.

Benchmark 20 câu là bộ phát triển do agent biên soạn, không phải dữ liệu khách hàng thật. M3/M4 so sánh toàn pipeline có luật/FAQ/guardrails; median thấp có thể chủ yếu phản ánh các nhánh trả lời nhanh. Chỉ bốn câu cuối có sinh LLM trong M4 nên không dùng p95 toàn pipeline làm p95 riêng của model 7B. Có nguồn trích dẫn không tự chứng minh nội dung có căn cứ: ví dụ API smoke RAM/SSD lấy cả nguồn FAQ ít liên quan, cần người chấm đánh giá `correct_sources` và `grounded` riêng.
