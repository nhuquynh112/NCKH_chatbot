# Hồ sơ thực thi P+FT trên 100 ca ngày 04/11/2026

Hồ sơ gốc được dẫn ở nguồn [29]. Đây là lượt đã tạo phản hồi để chấm, không phải lượt chạy mới. Các file lịch sử được sao chép nguyên byte; `bundle_manifest.json` lưu SHA-256, kích thước, xuất xứ và danh sách loại trừ. Quy tắc `.gitattributes` giữ nguyên xuống dòng khi clone trên Windows/Linux.

## Kiểm chứng và tính lại độ trễ

Từ thư mục gốc repository, dùng Python 3.11 trở lên, không cần GPU, Ollama hoặc dependencies backend:

```powershell
python -B outputs/pft100_20261104_7c4d29/verify_and_summarize.py
```

Lệnh kiểm tra hash các file, snapshot, mã nguồn, 100 request/response/record, lịch sử và vai trò hội thoại, prompt/generation identity, CSV và đối chứng P; sau đó tính lại trung vị, trung bình, p95 và tỷ lệ lỗi. Nó đối chiếu số đo với `published/statistics.json`, không sửa file hoặc tự suy ra điểm chất lượng. Thành công trả `verified: true` và mã thoát 0; sai dữ liệu trả mã 2.

Để đối chiếu phiếu chấm theo mã ca (cần thêm `openpyxl`):

```powershell
python -m pip install openpyxl
python -B outputs/pft100_20261104_7c4d29/verify_and_summarize.py --ratings outputs/cham_bo_sung_100_20261104/Phieu_R1.xlsx --ratings outputs/cham_bo_sung_100_20261104/Phieu_R2.xlsx
```

`--ratings` kiểm tra nguyên văn câu hỏi, phản hồi cuối, trạng thái và lịch sử, rồi đếm điểm đã có. Không ghép theo thứ tự dòng, không sửa điểm, không thay câu trả lời. Bản R1 ở commit `7a096cb40c8f9a970d183e2a20dc2e6eb652f1b2` có 100 điểm; R2 ở commit đó là phiếu trống sau đổi tên. Khi dùng R2 đã chấm ở nơi khác, truyền đường dẫn tới đúng bản đó. Nếu có khác biệt định dạng/nội dung, script báo rõ mã ca để đối chiếu thủ công, không tự sửa hay hợp thức hóa khác biệt.

Có thể thêm `--out D:/NCKH/Codex/doi_chieu_pft_20261105.json` để lưu JSON vào một file **chưa tồn tại**, ngoài thư mục hồ sơ. Trên máy khác chọn đường dẫn xuất phù hợp. Không ghi đè kết quả cũ.

## Nội dung và nguồn của lượt chạy

- `runs/main/manifest.json`: thời điểm UTC, tham số, timeout, hash collector và corpus; lượt chính từ 04:57:36 tới 05:19:00 UTC ngày 04/11/2026.
- `runs/main/runtime_health.json`: bản ghi dịch vụ `ready`, `adapter_loaded=true`, RTX 3060, NF4/BF16, phiên bản package và định danh model.
- `runs/main/results.jsonl`, `results.csv`: 100 kết quả gốc. Các thư mục S/O/H/T chứa request, response, record, log worker, lịch sử thiết lập; prompt, nguồn truy xuất và trace nằm trong response/record.
- `runs/smoke/`: S01, S31 và H01; giữ riêng, không trộn vào 100 ca chính.
- `test_inputs.json`: đúng 100 ca v4.0-draft; nội dung tương ứng `HT_model7B/docs/evaluation/blind_60_20261023/benchmark_input.json` ở nguồn mã lưu.
- `corpus/`, `frozen_products.db`, `plain_prompt.txt`: snapshot 150 sản phẩm/299 tài liệu của đối chứng P. Database chỉ có dữ liệu sản phẩm; bảng admin, chat, ticket và FAQ trống. Đây là snapshot nghiên cứu, không phải database chạy website.
- `controls_400.original.jsonl`: bản gốc các kết quả B0/B1/B2/P trước đó; script chỉ chọn 100 ca P làm đối chứng. Mỗi phương pháp sinh lịch sử thiết lập riêng từ cùng kịch bản user.
- `source_snapshot/HT_model7B/backend/`: 61 file pipeline/server và 4 file harness khớp hash trong context. Nguồn nền: commit `ddec788897f5e5a69e594d0de31aca7fa39ce140`; collector quan sát bên ngoài nằm ở `run_pft.py` và `worker_pft.py`.
- `published/`: bản xuất cuối cùng gồm CSV, đối chiếu P/P+FT, thống kê và báo cáo nghiên cứu. `publication_v1/` là bản xuất cũ được giữ theo lịch sử, không dùng làm số liệu cuối cùng.
- `server.stderr.log`, `main.log`, `smoke.log` và log từng ca giữ nguyên cả lỗi; `S47_context_diagnostic.json` chỉ chẩn đoán token, không sinh phản hồi thay thế.

Loại khỏi bản công bố: `grading/` (workspace tạo phiếu, bản xem trước, cache và ánh xạ điều phối riêng), `server.pid` và các SQLite sidecar. Không sửa hoặc xóa các file này ở thư mục nguồn. Hai phiếu dùng chấm được quản lý riêng tại `outputs/cham_bo_sung_100_20261104/`.

## Model và lệnh thu thập lịch sử

P+FT dùng `unsloth/Qwen2.5-7B-Instruct-bnb-4bit`, revision `bdd404162d94997f390efbfa660eb3f21cbbc81d`, qua Transformers/PEFT và adapter đã huấn luyện trước đó (37 train, 9 validation, một epoch). Adapter SHA-256 `b7650bf5a6a4eb02b902bb9a5758d178c3e4f32c5329013ca7c819045d8008b7`; checkpoint SHA-256 `99b85155b7bb40344d8c3938c8ec1147b27028804bca5d2e5559cb8e6533747d`. Không huấn luyện thêm ở lượt này.

Checkpoint và weights không nằm trong thư mục hồ sơ này. Adapter cùng hash được quản lý bằng Git LFS ở nhánh `benmark-chatbot`, commit `de48b9e8fa91f052d925284cef95eb6c0a7ef3e8`, file `HT_model7B/backend/models/qwen2.5-7b-ft/run/adapter/adapter_model.safetensors`. Bản cấu hình và provenance lịch sử nằm trong `profile.local.json`, `training_run.original.json` và `artifact_verification.json`.

Các lệnh dưới đây ghi lại cách thu thập trên máy Windows gốc, **không cần chạy để kiểm chứng hồ sơ**. Đường dẫn tuyệt đối trong script/profile là dữ liệu lịch sử, không phải cấu hình mặc định sau clone. Harness từ chối dùng lại thư mục `runs/smoke` hoặc `runs/main` đã tồn tại.

```powershell
Set-Location D:/NCKH/2026_Chatbot/Code/NCKH_chatbot/HT_model7B/backend
& D:/NCKH/Codex/.venv-training/Scripts/python.exe -X utf8 -B -u -m model_serving.server --profile D:/NCKH/Codex/pft100_20261104_7c4d29/profile.local.json --port 8011
# Sau khi /health báo ready và adapter_loaded=true, terminal khác:
& C:/Python314/python.exe -X utf8 -B -u D:/NCKH/Codex/pft100_20261104_7c4d29/run_pft.py smoke
& C:/Python314/python.exe -X utf8 -B -u D:/NCKH/Codex/pft100_20261104_7c4d29/run_pft.py main
```

`prepare_pft.py`, `publish_pft.py` và `diagnose_S47.py` được lưu nguyên bản để kiểm toán; không chạy chúng để ghi lại dữ liệu trong hồ sơ. Muốn thực nghiệm mới phải tạo run riêng và xác minh checkpoint, adapter, GPU và snapshot; điểm cũ không tự áp dụng cho phản hồi mới.

## Cách đọc thống kê

Giữ cả 100 ca khi tính tỷ lệ lỗi: 99 `ok`, S47 `error` (1%). S47 có 3.758 token đầu vào cộng 384 token đầu ra, vượt 4.096; không có câu trả lời thay thế. Có 35 ca thử gọi LLM ở lượt cuối, 34 hoàn tất; 76 lần sinh có bằng chứng model identity nếu tính cả các lượt thiết lập hội thoại.

Độ trễ lượt cuối chỉ tổng hợp các ca `ok`/`no_rule_match` có latency, gồm cả nhánh luật/FAQ. Trên 99 ca: trung vị 274,6201 ms, trung bình 4.934,5879 ms, p95 16.216,16968 ms. P95 nội suy tuyến tính tại `(n-1)*0.95`; không báo p95 khi ít hơn 20 mẫu. `whole_case_wall_successful` tính cả thiết lập lịch sử và overhead subprocess, không được gọi là độ trễ sinh LLM. Lỗi và smoke không bị gộp vào mẫu latency thành công.

P+FT NF4/BF16 và P FP16/Ollama khác precision, runtime và ngày thu thập; so sánh chỉ mang tính mô tả, không cô lập tác động fine-tuning. Bằng chứng thực thi, trùng văn bản hoặc nhánh định tuyến không phải điểm chất lượng hay tỷ lệ phát biểu ngoài nguồn. Phiếu R1/R2 và điểm benchmark cũ được giữ riêng; hồ sơ này không tính lại kappa.
