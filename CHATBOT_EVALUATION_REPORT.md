# Báo cáo đánh giá chatbot — 14/10/2026

Đã chạy thực tế trên nhánh `frontend-chat-integration`: Windows, Python 3.14, RTX 3060 12 GB, RAM khoảng 15,9 GiB. AI chỉ gọi Ollama local; database kiểm thử là SQLite riêng, không phải PostgreSQL của người dùng.

## Kết quả pipeline trên cùng bộ cố định

32 tình huống được thiết lập trước khi sửa implementation. Phiên bản baseline đã chạy khi Ollama được bật; có file riêng cho lần đầu dịch vụ gián đoạn, không dùng lần đó làm so sánh chính. Sau sửa tái tạo hai FAQ seed ban đầu trong DB tạm bằng `--legacy-faqs`.

| Chỉ số | Trước | Sau | Ollama bị ngắt |
|---|---:|---:|---:|
| Đạt tiêu chí có đáp án chuẩn | 21/32 | 32/32 | 32/32 |
| Lỗi HTTP/API trong bộ 32 câu | 0 | 0 | 0 |
| Trường hợp chứa mẫu trả lời bị cấm | 4/32 | 0/32 | 0/32 |
| Retrieval Hit@5 | 10/11 | 11/11 | 11/11 |
| Latency trung vị API, ms | 453.76 | 98.92 | 97.64 |
| Latency P95 API, ms | 25268.92 | 159.67 | 302.02 |
| Câu được LLM sinh câu trả lời | 2/32 | 0/32 | 0/32 |

Hit@5 tính trên 11 câu có nguồn tham chiếu: tìm ít nhất một tiêu đề phù hợp trong top 5, không phải Recall@k toàn bộ nhiều tài liệu liên quan. P95 dùng nearest-rank `ceil(0.95*n)`. API latency đo TestClient, gồm đọc/ghi DB, router và AI; không gồm đường truyền browser, thời gian truy xuất kiểm tra thêm không cộng vào latency câu trả lời.

**32/32 sau sửa là kết quả pipeline luật/FAQ trên tập phát triển nhỏ, không phải LLM chính xác 100%.** Mẫu cấm gồm cam kết không có căn cứ, biến thể sai và vi phạm yêu cầu chặn; không đồng nhất chỉ số này với tỷ lệ hallucination toàn diện. Không có LLM-as-judge/cloud evaluator.

## Theo nhóm câu hỏi

| Nhóm | Trước | Sau |
|---|---:|---:|
| faq | 8/15 | 15/15 |
| facts | 2/4 | 4/4 |
| comparison | 1/1 | 1/1 |
| budget | 2/2 | 2/2 |
| multi_turn | 1/1 | 1/1 |
| safety | 1/2 | 2/2 |
| scope | 1/1 | 1/1 |
| unknown | 1/1 | 1/1 |
| privacy | 1/1 | 1/1 |
| order | 1/1 | 1/1 |
| support | 1/2 | 2/2 |
| missing | 1/1 | 1/1 |

## Hồi quy và độ ổn định

- Unit test ban đầu: **100/100 đạt**; lượt cuối sau tích hợp 3B đã train đạt **105/105**. Giữ các test cũ và bổ sung lỗi mới.
- Hồi quy cũ: **225/225**, API **5/5**, tải **16/16**. Chi tiết latency/nhóm ở `backend/EVALUATION_REPORT.md`; 16 lượt tải là các session khác nhau, không phải thử tải dài hạn hoặc cùng một session.
- Frontend lint đúng source/config và production build hoàn tất. Không thay bố cục/giao diện.
- Các test mới bao gồm DB lỗi→503, model timeout, index thiếu/cũ/khác model, giá/bảo hành DB, catalog active trống, FAQ live/suppression, OTP/phone, ticket status riêng tư, so sánh, ngân sách/phụ kiện, injection trước giá và lọc context.
- Rebuild thực tế: 195 tài liệu, vector 768 chiều; Nomic prefix query/document; JSON signature kiểm tra tương thích. Không đổi embedding model, không thêm package runtime.

## Benchmark LLM độc lập

So sánh Qwen 2.5 3B và ứng viên 7B Q4_K_M đã tải, cùng 8 ngữ cảnh tổng hợp, temperature 0, context 4096, output tối đa 384, socket 25 giây; warm-up trước phép đo. Đây là thử prompt A/B trực tiếp, tách khỏi luật/FAQ và hàng rào ở pipeline. Model chính trong cấu hình vẫn là 3B.

| Model/prompt | Đạt kiểm tra từ khóa | Latency trung vị | Lỗi request |
|---|---:|---:|---:|
| qwen2.5:3b / original | 6/8 | 2816.24 ms | 0 |
| qwen2.5:3b / improved | 6/8 | 2790.43 ms | 0 |
| qwen2.5:7b / original | 6/8 | 3287.80 ms | 0 |
| qwen2.5:7b / improved | 6/8 | 3381.45 ms | 0 |

Bản prompt dài ban đầu chỉ đạt 5/8; đã lưu cả kết quả đó tại `model_benchmark_initial.json` và `model_benchmark_long_prompt.json`, rồi chọn bản rút gọn. Không có bằng chứng prompt đơn thuần làm model mạnh hơn. Qwen 3B vẫn thất bại khi context chứa chỉ dẫn giả; Qwen 7B trả đúng giá ở câu đó và đưa đủ giá khi so sánh. 7B mất điểm ở việc không hỏi địa chỉ giao hàng và không dùng đúng từ khóa 'chưa', dù không tự tạo phí/voucher. Đây là khác biệt có giá trị, chưa phải đánh giá toàn diện trên khách thật.

Ứng viên [Qwen 2.5 7B Q4_K_M](https://ollama.com/library/qwen2.5:7b) tải thành công sau một lần lỗi mạng IPv6. Cùng prompt mới, trung vị khoảng 3,38 giây so với 2,79 giây của 3B, chậm hơn khoảng 21%. Giữ Qwen 3B cho buổi demo với router/FAQ/fallback đã kiểm thử; 7B là lựa chọn thử thêm cho câu phức tạp khi nhóm duyệt đổi model chính. Phép đo này thực hiện trước fine-tuning; pilot GPU dùng checkpoint NF4 riêng và không được gộp với phép đo Ollama Q4_K_M.

### Tài nguyên local thực đo

Ảnh chụp `/api/ps` sau benchmark, context 4096; đây là bộ nhớ model do Ollama báo, không phải VRAM peak của toàn máy. RTX 3060 có 12.288 MiB; snapshot tổng GPU sau thử hai model khoảng 9.060 MiB, có cả model embedding, các model giữ trong cache và ứng dụng khác.

| Model | VRAM được Ollama báo | Context |
|---|---:|---:|
| qwen2.5:3b | 2.01 GiB | 4096 |
| nomic-embed-text:latest | 0.31 GiB | 2048 |
| qwen2.5:7b | 4.43 GiB | 4096 |

## Bằng chứng và tái tạo

File JSON/log và công cụ benchmark đã được chuyển ra `D:\NCKH\Codex\evaluation_artifacts` theo yêu cầu giữ repo gọn; tên file bên dưới giữ nguyên. Database thử và build thử không cần thiết đã xóa. Báo cáo này và fixture/test cần thiết được giữ trong repo.

- `backend/evaluation_cases.json`: câu hỏi, từ khóa đúng/sai, nhóm, setup hội thoại và nguồn tham chiếu, cố định trước sửa.
- SHA256 fixture chung: `f6de9bbc7e5d7c71904142f95a5d6931e15dab3f141eaecc037a140b9cba1649`.
- `baseline_online_quality.json`, `after_quality.json`, `offline_quality.json`: toàn bộ câu hỏi, đáp án, mode, latency, lỗi, nguồn truy xuất.
- `baseline_report.md`: kết quả 225 câu trước sửa; `backend/EVALUATION_REPORT.md`: kết quả sau sửa.
- `model_benchmark.json`: câu trả lời model và token/duration từ Ollama. Các file initial/long_prompt giữ thử nghiệm chưa tốt.
- `final_workflow.log`: unit, hồi quy, hai phép đánh giá, lint/build cuối. Log có cảnh báo deprecation TestClient và ResourceWarning SQLite trong môi trường Python 3.14; không có test thất bại.
- Chạy từ repo: `.\run_tests.ps1`. Xem `CHATBOT_IMPROVEMENTS.md` để chạy backend/frontend/rebuild và xem phạm vi an toàn dữ liệu.

## Giới hạn cần nêu trong báo cáo khoa học

Tập 32 câu là tập phát triển đã dùng tối ưu, không phải holdout độc lập. Cần thêm bộ người thử thật, câu hỏi chưa nhìn trước và chấm đúng dữ kiện/bám nguồn/độ tự nhiên theo rubric. Chưa đo mức hài lòng, hallucination toàn diện, mở rộng dài hạn hoặc Chroma. Confidence/score trong API là heuristic, không phải xác suất đúng đã hiệu chuẩn.

Không có live stock/order/transport integration. Chính sách TechCare là mô phỏng và còn sản phẩm thiếu SKU. Thời gian phản hồi rất thấp sau sửa chủ yếu do giảm gọi LLM; không suy rộng sang câu cần model sinh tự do. Tác động của FAQ mới, prefix, index và hybrid được đo cùng nhau, chưa có ablation để quy lợi ích riêng cho từng kỹ thuật. Các phép đo bên trên thực hiện trước fine-tuning; giai đoạn 3B đã train được ghi riêng dưới đây. Nguồn dataset tại `DATASET_CANDIDATES.md`.

## Huấn luyện GPU và tích hợp 3B

Đã hoàn tất QLoRA trên RTX 3060: 170 train gồm 37 mẫu CSConDa đã lọc và 133 ví dụ tổng hợp có ngữ cảnh; giữ 9 validation CSConDa. Tập test chính thức 1.500 dòng không dùng cho train, RAG hoặc chọn cấu hình. Trong 46 mẫu CSConDa giữ lại trước khi chia, 12 đáp án nguyên bản và 34 đáp án được agent biên tập. Dữ liệu tổng hợp có giá thay đổi theo ngữ cảnh, chỉ dùng nghiên cứu.

Checkpoint NF4 3B được xác minh hash, revision `2672b588848527e456d320c11926c794539f47d5`. LoRA rank 16 trên all-linear, 29.933.568 tham số học, LR 1e-4, 2 epoch, batch 1 và tích lũy 4, BF16, sequence 512. Thời gian **riêng giai đoạn tối ưu 360,474 giây**, không gồm tải, benchmark và đóng gói. Peak GPU allocated **4,54 GiB**. Validation loss **3,464113 → 2,077344**; loss giảm không tương đương tăng accuracy 40%.

Ollama 0.40.4 từ chối import LoRA adapter trực tiếp. Adapter được gộp vào checkpoint đã dequantize, xuất GGUF F16 rồi Q4_K_M bằng llama.cpp. Bản chạy được là **`techcare-support:3b-v1`**, GGUF **1.929.902.496 byte**, SHA256 `87710c00e7b1da9c873d2ba0ddc89e89eb24075f81ebfba55ed527832ecc3b18`. Giấy phép upstream 3B là Qwen Research License và được giữ trong Modelfile.

### Giữ cả cấu hình chưa tốt và cách điều chỉnh

| Giai đoạn | Base 3B | 3B đã train | Phạm vi |
|---|---:|---:|---|
| NF4 trong Transformers trước và sau train | 5/8 | 6/8 | 8 câu phát triển, cùng precision |
| Ollama với prompt cũ và repeat penalty 1.1 | 4/8 | 4/8 | 8 câu phát triển |
| Cấu hình đầu trên test tổng hợp ban đầu | 18/21 | 12/21 | Không chọn cấu hình này |
| Prompt đồng bộ với train và repeat penalty 1.0 | 5/8 | 6/8 | Chọn cấu hình trên 8 câu phát triển |
| Cấu hình đã chọn trên 12 câu tổng hợp mới | 10/12 | 12/12 | Đóng băng trước khi chọn cấu hình |

Bản đầu từ chối cả dữ kiện có sẵn. Chẩn đoán trên 8 câu phát triển dẫn tới prompt ngắn tương thích với train và bỏ hình phạt nhắc lại dữ kiện. Tập 21 câu đã được xem nên không gọi việc thử lại tập đó là holdout độc lập. Tập mới 12 câu có SHA256 `994297f21596b6a985b8d834edb48607f113c9a6d6b9820a4e7f947e9ed7989f`, được đóng băng trước khi quyết định cấu hình. Hai model dùng cùng prompt có quy tắc bộ nhớ, temperature 0, context 4096, output 384, repeat penalty 1.0.

| Kết quả raw Ollama trên 12 câu mới | Base 3B | 3B đã train |
|---|---:|---:|
| Đạt tiêu chí dữ kiện và nội dung tự động | 10/12 | 12/12 |
| Latency trung vị sinh câu trả lời | 2611,255 ms | 2683,595 ms |
| VRAM snapshot khi chạy context 4096 | 2,01 GiB | 2,01 GiB |

Ví dụ base bỏ giá và tự nêu giao trong 2–3 ngày; bản đã train nêu giá/bảo hành trong ngữ cảnh và giữ tồn kho chưa xác nhận. Base tính giảm 50% từ mã không được duyệt; bản đã train từ chối xác nhận ưu đãi. Đối chiếu đáp án vẫn thấy câu hỏi bổ sung thừa, diễn đạt lặp và câu đơn hàng hỏi nhầm thông tin mẫu. Các luồng này trong ứng dụng được ưu tiên xử lý bằng luật/FAQ và chuyển nhân viên.

**12/12 là kiểm tra tự động trên 12 ví dụ tổng hợp do agent tạo, không phải độ chính xác 100% hay khảo sát khách thật.** Nhóm cần chấm độc lập độ đúng, đủ ý và tự nhiên. Base Ollama Q4 và bản đã train từ NF4 rồi chuyển Q4 có đường lượng tử hóa khác nhau; so sánh triển khai này chưa tách riêng tác động của fine-tuning và lượng tử hóa. Latency là một lượt đo trên máy bàn, không phải số đo RTX 3050.

### Xác minh ứng dụng sau khi chọn model

`model_profile.json` chọn model đã train, giữ tag base và `.env`. Đã ghi nhận lời gọi Ollama thật từ luồng **LLM + RAG**, dùng ngữ cảnh kiểm thử về RAM dual-channel, và chạy ba luồng API riêng gồm giá sản phẩm, FAQ nhiều ý và chuyển nhân viên. Database thử riêng. Backend thật cũng đã khởi động và `/ready` trả `database: ok`, `ai: ok`, `chat_model: techcare-support:3b-v1`.

Quy trình cuối: **105/105 unit**, **225/225 hồi quy**, API **5/5**, tải **16/16**, frontend lint/build đều đạt. Bộ pipeline cố định đạt **32/32 online và offline**, Hit@5 **11/11**; vẫn **0/32 câu sinh LLM**. Lượt này có latency online median **333,27 ms**, P95 **494,74 ms**; offline median **337,465 ms**, P95 **461,66 ms**. Không ghi đè số đo trước đó hoặc quy biến động tốc độ pipeline cho fine-tuning.

Bằng chứng chính được đóng gói tại `backend/models/techcare-support-3b-v1/evidence/{run.json,ollama_benchmark.json,config_diagnosis.json,fresh_12_benchmark.json,integration_check.json}`; GGUF, adapter và dữ liệu trong cùng thư mục model, mã huấn luyện ở `backend/training`. Log `evaluation_artifacts/trained_3b_final_workflow.log`, `trained3b_quality.json`, `trained3b-offline_quality.json` vẫn ở `D:\NCKH\Codex`. Đường dẫn tuyệt đối trong bản ghi thí nghiệm giữ vị trí ban đầu để bảo toàn provenance; vị trí cài hiện tại dùng `model_profile.json`. Dense merge và GGUF F16 là trung gian có thể tạo lại.

Pilot 7B riêng: 37 train, 9 validation, rank 8 q/v, một epoch, tối ưu 20,344 giây, peak 8,65 GiB; loss 3,723275 → 3,675476. Kiểm tra 8 câu cùng mô hình/precision đạt **6/8 trước và sau**. Các cấu hình/dataset khác nhau nên không so trực tiếp thời gian train 7B với 3B. Không nâng 7B làm model chính.
