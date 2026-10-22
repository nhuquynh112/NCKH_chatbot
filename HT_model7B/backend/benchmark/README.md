# Benchmark TechCare B0/B1/B2/P và P+FT bổ sung

Trong bản hệ thống 7B, B1/B2/P cùng dùng `qwen2.5:7b-instruct-fp16` gốc, không fine-tune. B0 không gọi LLM. **P là phương pháp nhóm đề xuất và không huấn luyện thêm.** P+FT dùng adapter 7B gốc 37 train/9 validation/1 epoch đã đóng gói qua Git LFS, không thuộc bốn phương pháp chính. Model demo 3B cũ (170 train) không dùng trong benchmark này. [Bảng phương pháp và cách chạy](../../docs/BENCHMARK_METHODS.md).

Bộ 24 câu được nhóm duyệt cho Chương 5 có giao thức B0/B1/B2/P và sáu ablation riêng; xem [runbook Chương 5](../../docs/CHAPTER5_RUNBOOK.md). Không dùng M3 cũ đồng thời làm B2 và P. Những mô tả M1–M4 dưới đây giữ cho bộ phát triển 20 câu trước đó.

Chạy từ `backend`: `python -B -m benchmark.run --methods B0 B1 B2 P`. Runner mặc định cũng chọn đúng bốn phương pháp này trên bộ phát triển 20 câu; P+FT chỉ chạy khi chọn rõ bằng `--methods 'P+FT'`. Với bộ 24 câu Chương 5, dùng [hướng dẫn tái lập](../../docs/REPRODUCING_RESEARCH.md), chạy phase main và supplementary riêng. Công cụ độc lập giao diện demo; không dùng database khách hàng thật.

## Phương pháp và dữ liệu

### Bốn phương pháp chính và nhánh bổ sung

| Mã | Thực hiện | Model |
|---|---|---|
| B0 | Luật/catalog/FAQ | Không LLM |
| B1 | LLM thuần, không RAG | 7B FP16 gốc |
| B2 | Semantic top-5 + LLM, không hybrid/routing/postcheck của P | Cùng 7B FP16 gốc |
| P | Pipeline đầy đủ do nhóm đề xuất | Cùng 7B FP16 gốc, không fine-tune |
| P+FT | Cùng pipeline P, provider `hf_lora` | 7B NF4/BF16 + adapter QLoRA, bổ sung |

### Mã tương thích bộ phát triển cũ

| Mã | Thực hiện | Model |
|---|---|---|
| M1 | `GuardrailPolicy.deterministic_answer`, snapshot catalog; không LLM, không FAQ semantic; không khớp thì `no_rule_match` | Không có |
| M2 | System prompt trung tính trong `prompts/plain.txt`, câu hỏi và lịch sử do chính phương pháp tạo; không mở corpus, index, FAQ, database hay gọi embedding | Base `qwen2.5:7b-instruct-fp16` |
| M3 | Factory/pipeline RAG hiện có, gồm luật, FAQ, query rewriting, hybrid retriever, guardrails và kiểm tra grounding | Base `qwen2.5:7b-instruct-fp16` |
| M4 | Cùng pipeline và snapshot như M3; HTTP server nạp NF4 + adapter QLoRA gốc | `qwen2.5-7b-finetuned` |

M3 là phương pháp chính; M4 bổ sung. M3/M4 có thể trả lời trước bước LLM. `mode`, `llm_called`, `setup_llm_called`, `calls[].phase` phân biệt rõ. M1 định nghĩa luật theo từng câu, chưa diễn giải history; đây là giới hạn của baseline, cần nêu khi báo cáo câu nối tiếp.

Runner sao chép tám file corpus, gồm KB, catalog, FAQ, export sản phẩm, tài liệu RAG, verified specs, system prompt và vector index. Worker M1/M3/M4 tạo SQLite riêng từ snapshot sản phẩm, giữ ID và metadata, cố định FAQ/specs vào bản sao. M2 không tạo/read database này. Dữ liệu FAQ do admin thay đổi trong database demo không được đưa vào benchmark; đây là phiên bản corpus cố định để tái lập. Runner không export/rebuild index hoặc sửa nguồn gốc.

Retrieval dùng JSON index mặc định, `nomic-embed-text`, prefix `nomic-task-prefix-v1`, top-k 5, min score 0.38. Identity M3/M4 ghi 195 tài liệu và `semantic_enabled` thực tế. Corpus này là tri thức demo TechCare, không phải CSConDa. Dữ liệu train pilot 37/9 ở ngoài repo; không được nạp trong benchmark. Tập 20 câu mới là dữ liệu đánh giá do agent biên soạn từ nguồn dự án, cần người phụ trách duyệt; chưa phải blind holdout hay tập khách hàng độc lập đã kiểm định. Tám câu synthetic trong pilot cũ không được dùng làm kết quả chính ở đây.

Mọi expected answer/fact đều phải có evidence. Không chép đáp án vào corpus/prompt/train. Dù tách file và không nạp gold vào model, câu đánh giá dựa trên cùng miền tri thức và được người triển khai nhìn thấy vẫn có nguy cơ thiên lệch. Muốn kết luận nghiên cứu cần bộ holdout do người khác biên soạn, rà trùng với train và đánh giá mù.

## Schema

JSON có dạng `{"version":"...","cases":[...]}`; JSONL có một case/object mỗi dòng. Case không chấp nhận trường lạ hoặc ID trùng.

| Trường | Kiểu / ý nghĩa |
|---|---|
| `id` | Bắt buộc, duy nhất, chỉ chữ/số/`_`/`-` |
| `category`, `question` | Chuỗi bắt buộc, không rỗng |
| `expected_answer` | Chuỗi hoặc null; chuẩn tham khảo cho người chấm |
| `required_facts`, `forbidden_claims` | Danh sách chuỗi hoặc null; kiểm tra literal, không diễn giải ngữ nghĩa |
| `expected_source` | Chuỗi khớp metadata.source hoặc null |
| `expected_source_ids` | Danh sách ID; có ít nhất một nguồn là kiểm tra presence đạt; hoặc null |
| `risk_level` | low / medium / high, mặc định medium |
| `notes` | Chuỗi hoặc null |
| `evidence` | Danh sách đường dẫn/ID nguồn và dữ kiện; bắt buộc có khi khai báo expected_answer/required_facts |
| `history_questions` | Danh sách câu hỏi user; worker tự sinh câu trả lời cho từng lượt, không cấp gold answer |

Ví dụ thiếu dữ kiện, không bịa đáp án:

```json
{"id":"unknown","category":"out_of_corpus","question":"Sản phẩm chưa có trong catalog có giá bao nhiêu?","expected_answer":null,"required_facts":null,"forbidden_claims":null,"expected_source":null,"expected_source_ids":null,"risk_level":"high","notes":"Cần nói rõ thiếu dữ liệu, không suy đoán giá.","evidence":[],"history_questions":[]}
```

## Output, tái lập và timeout

Mỗi run tạo `.local/benchmark_results/<UTC>-<UUID>/`:

```text
manifest.json                 # Hash code, dataset, corpus, model/prompt/settings, case order
dataset.source.json / .jsonl  # Bản sao nguyên dataset JSON hoặc JSONL
plain_prompt.txt, corpus/     # Input cố định
results.jsonl, results.csv    # Câu trả lời thực, lỗi, nguồn, trace
summary.json, summary.csv     # Tổng hợp tự động, human metrics chưa chấm là null
review_template.jsonl         # Các ô cho người chấm, chưa có điểm
M?-<repeat>-<case>/
  request.json, response.json, worker.log, isolated.db
```

M2 không dùng isolated.db; nó chỉ có request/response/log. Mỗi row lưu model được yêu cầu và identity/digest đã kiểm tra, câu hỏi, answer, sources, mode, status/error, latency_ms, wall_ms, lịch sử, trace đầy đủ system/user prompt và cấu hình generation. M4 trace mới còn có generation_ms, input/output token, GPU, hash và peak_allocated_bytes. Đây là peak bộ nhớ torch trong process lúc generate, không phải toàn bộ VRAM hay chi phí tăng thêm của request. Ollama không có phép đo chi phí tương đương trong runner này; không suy ra chi phí từ thời gian.

Worker là process riêng cho từng case; timeout mặc định 60 giây gồm import, preflight, setup history và câu cuối. Parent dừng worker quá hạn, lưu log và trạng thái timeout. Nếu timeout trước khi response được ghi xong, answer/trace chưa hoàn tất không có; không bịa dữ liệu bù. GPU request đã gửi có thể cần tới deadline của server mới dừng, vì vậy case sau có thể gặp busy. Server 7B kiểm tra deadline giữa các bước decode; một kernel CUDA đang chạy không bị ngắt tức thì.

`latency_ms` chỉ đo xử lý câu cuối, gồm retrieval/generation/guards; `wall_ms` gồm cả process/setup. Các lượt warm-up không được tự loại; cold/warm state và tải máy có thể ảnh hưởng. Dùng run warm-up riêng rồi ghi rõ khi chạy phép đo chính. Cùng temperature=0, tối đa 384 token, context 4096, repetition penalty=1 không bảo đảm output bit-for-bit giữa runtime/thiết bị. M2/M3 dùng Ollama GGUF; M4 dùng HF NF4/BF16 và chat template của checkpoint. M4 từ chối context quá giới hạn thay vì cắt âm thầm; hành vi giới hạn context ở Ollama có thể khác.

Các status hệ thống: `ok`, `no_rule_match`, `not_ready`, `error`, `timeout`. “Sai đáp án”, “thiếu thông tin”, “thiếu bằng chứng” là đánh giá nội dung ở bước human review, không suy từ status. Run có lỗi vẫn giữ raw output; mã thoát 2 để script gọi biết chưa chạy sạch.

## Chấm thủ công

Sao chép `review_template.jsonl` sang một file review mới rồi chấm từng row theo corpus snapshot và câu hỏi, không dựa vào tên model. Điền `reviewer`; các trường không áp dụng để null. Khóa row gồm run_id/method/case_id/repeat. Tránh hai người chấm trùng khóa trong cùng file; nếu cần đa giám khảo, tạo file/tổng hợp riêng và thống nhất quy tắc phân xử trước.

| Trường | Quy tắc |
|---|---|
| correctness | `correct`: đáp ứng câu hỏi, không sai dữ kiện; `incorrect`: dữ kiện/khuyến nghị sai; `insufficient_information`: trả lời thiếu phần cần thiết; `no_evidence`: đưa khẳng định nhưng không có căn cứ để xác nhận; `not_applicable`: không chấm; null: chưa chấm |
| grounded | Các khẳng định cần bằng chứng có thể đối chiếu với corpus; có source ID chưa đủ để là true |
| hallucination | true nếu khẳng định thêm giá/chính sách/thông số/sự kiện không được hỗ trợ; không đánh đồng việc nhắc lại yêu cầu xấu với xác nhận yêu cầu đó |
| policy_compliant | Tuân thủ chính sách trong nguồn và không hứa thao tác chưa thực hiện |
| appropriate_abstention | Với câu thiếu dữ liệu, hỏi lại/từ chối/chuyển hỗ trợ phù hợp; câu không cần abstain để null |
| correct_sources | Nguồn trích đúng và thực sự hỗ trợ khẳng định; không có yêu cầu/không áp dụng để null |
| relevant | Nội dung trả lời đúng trọng tâm nhu cầu |
| notes | Ghi dữ kiện/nguồn hoặc câu trả lời làm căn cứ chấm |

```powershell
python -B -m benchmark.review --run '..\.local\benchmark_results\<run-id>' --reviews '<review.jsonl>'
```

Review tool xác minh khóa, trường, reviewer; tạo `reviewed-<UUID>/` và giữ nguyên raw run. Schema chỉ kiểm tra cấu trúc; con người vẫn chịu trách nhiệm nguồn gold và đánh giá ngữ nghĩa.

## Mẫu số và giới hạn metric

- `attempts`: tất cả case/lượt lặp của phương pháp. `answered`: ok + no_rule_match. `error_timeout_rate`: (error + timeout)/attempts; not_ready có tỷ lệ riêng. Có thể cộng hai tỷ lệ để mô tả tất cả lượt không sẵn sàng/lỗi.
- `llm_called_cases`: số câu cuối có gọi LLM, kể cả lời gọi gặp lỗi. Setup được ghi riêng. Không gọi trường này là số câu LLM trả lời thành công.
- `literal_passes/literal_evaluated`: trong các câu có trả lời và có required/forbidden strings, chuẩn hóa NFC, chữ thường, khoảng trắng rồi so substring. Dấu chấm/phẩy số có thể gây false negative; phủ định/nhắc lại có thể gây false positive. Không gọi đây là accuracy.
- `expected_source_present/source_evaluated`: chỉ kiểm tra ID hoặc metadata.source được kỳ vọng có xuất hiện. Không chứng minh nội dung được nguồn hỗ trợ.
- Human correctness: số correct / số row có trả lời và được chấm correctness khác null/not_applicable. Báo cả phân bố incorrect/insufficient_information/no_evidence. Các boolean: true_count/reviewed, mẫu số riêng cho từng metric, bỏ null. Human metrics chưa chấm giữ null; row error/timeout/not_ready không bị gán sai đáp án và không vào mẫu số human.
- Median latency: các row answered có latency; p95 nearest-rank chỉ khi có ít nhất 20 mẫu. Đây là ngưỡng xuất số thăm dò, không đủ bảo đảm ước lượng ổn định; nhiều mẫu lặp cùng câu không phải các câu hỏi độc lập. Luôn báo n, warm-up, timeout và phân bố luật/FAQ/LLM cùng latency.

M3 so M4 thay đổi đồng thời kích thước model, lượng tử hóa, runtime và fine-tuning. Không quy phần chênh lệch cho QLoRA; muốn tách hiệu ứng cần thêm base 7B cùng runtime/precision/corpus và thí nghiệm kiểm soát riêng. M2 so M3 là so LLM thuần với toàn bộ hệ thống RAG + luật/FAQ/guardrails, không cô lập riêng retriever.
