# Chạy demo 7B và benchmark M1–M4

Đọc [schema, rubric benchmark](../backend/benchmark/README.md) và [hướng dẫn tái lập](REPRODUCING_RESEARCH.md). Tích hợp này dùng lại adapter đã train ngày 14/10/2026; không huấn luyện mới, merge hoặc chuyển đổi weights.

## Môi trường và lựa chọn model

Backend ứng dụng dùng `backend/requirements.txt`; frontend dùng `frontend/package-lock.json`. Giữ môi trường hiện có nếu đã cài. Với môi trường ứng dụng mới, chạy `python -m venv .venv`, kích hoạt rồi `pip install -r requirements.txt` trong `backend`; chạy `npm ci` trong `frontend`. Không cài thư viện GPU vào môi trường web.

Runtime GPU từng được dùng: Python 3.14, torch 2.14.1+cu126, Transformers 5.19.0, PEFT 0.21.2, bitsandbytes 0.50.2. Đã nạp NF4/BF16 trên RTX 3060 12 GiB. Không cài/nâng cấp dependency trong lần tích hợp này. Máy khác cần kiểm tra runtime tương thích riêng; không coi Python >=3.11 của backend là cam kết chạy được runtime GPU này.

| Cấu hình backend | Model chat thực tế |
|---|---|
| Mặc định `CHAT_PROVIDER=ollama`, `USE_PROJECT_CHAT_MODEL=true` | Profile hiện có chọn `techcare-support:3b-v1` |
| `CHAT_PROVIDER=ollama`, `CHAT_MODEL=qwen2.5:3b`, `USE_PROJECT_CHAT_MODEL=false` | Base 3B; benchmark M2/M3 khóa lựa chọn này |
| `CHAT_PROVIDER=hf_lora`, `HF_LORA_BASE_URL=http://127.0.0.1:8011` | Adapter 7B đã xác minh; alias nội bộ `qwen2.5-7b-finetuned` |

Alias 7B là tên giao thức của server mới, không phải model Ollama đã import. `CHAT_PROVIDER` chọn đường gọi; chỉ đặt `CHAT_MODEL` thành alias 7B sẽ không chuyển provider. Khởi động lại backend sau khi đổi biến môi trường vì AIService giữ chatbot trong cache. `.env` hiện có không bị sửa.

## Artifact gốc và kiểm tra identity

Artifact 7B không có trong bản clone. Cần nhận bản gốc hợp lệ và đặt theo cấu trúc dưới đây hoặc dùng profile riêng ngoài Git. `$gpuPython` là đường dẫn Python GPU đã cài trên máy của bạn.

Profile nhỏ nằm tại `backend/model_serving/profiles/qwen25_7b.json` và tham chiếu:

- Checkpoint: `artifacts/qwen25_7b/checkpoint` (tương đối với `backend`), repo `unsloth/Qwen2.5-7B-Instruct-bnb-4bit`, revision `bdd404162d94997f390efbfa660eb3f21cbbc81d`.
- Adapter: `artifacts/qwen25_7b/run/adapter/adapter_model.safetensors`.
- Provenance: `run.json` tại thư mục run trên; checkpoint có `checkpoint_manifest.json`.

SHA256 checkpoint `model.safetensors`:

```text
99b85155b7bb40344d8c3938c8ec1147b27028804bca5d2e5559cb8e6533747d
```

SHA256 adapter:

```text
b7650bf5a6a4eb02b902bb9a5758d178c3e4f32c5329013ca7c819045d8008b7
```

Server kiểm tra trạng thái completed, repo/revision trong run và manifest, kiến trúc LoRA rank 8 q/v, kích thước/hash từng file checkpoint và hash adapter. Sau đó nạp local-only bằng Transformers/PEFT, xác nhận 4-bit, adapter active, weights trên CUDA, rồi mới báo `ready`. Client web kiểm tra model và hai hash trong health/generation; sai identity hoặc lỗi server sẽ báo 7B chưa sẵn sàng, không gọi model 3B thay thế.

Đối chiếu mà không nạp GPU, từ `backend`:

```powershell
& $gpuPython -B -m model_serving.server --check-only
```

Lệnh đọc lại checkpoint hơn 5 GB nên có thể mất vài phút. Nếu chuyển thư mục artifact, tạo bản sao profile nhỏ ngoài Git và truyền `--profile <đường-dẫn>`; chỉ đổi đường dẫn, giữ model/revision/hash. Client vẫn khóa identity gốc. Không sửa hoặc ghi đè artifact huấn luyện.

## Khởi động demo 7B

Mở terminal GPU, vào thư mục `backend`. Kiểm tra `ollama ps` và `nvidia-smi`. Server cần ít nhất 9 GiB VRAM trống lúc nạp; dừng model chat Ollama đang chiếm VRAM bằng `ollama stop <tag-đang-chạy>` nếu cần. Ollama vẫn cần hoạt động để chạy embedding `nomic-embed-text` đã có trên máy.

```powershell
# Chạy từ backend; $gpuPython là Python của môi trường GPU riêng.
& $gpuPython -B -u -m model_serving.server
```

Ở terminal khác:

```powershell
Invoke-RestMethod http://127.0.0.1:8011/health
```

Chờ `status=ready`, `adapter_loaded=true`, `active_adapters=[default]`, model/hash đúng profile. `loading` chưa phải sẵn sàng. `not_ready` có trường `error` để chẩn đoán. Server chỉ bind loopback và chỉ cho một lượt generate đồng thời.

Khởi động backend bằng môi trường web đã có, trong `backend`:

```powershell
$env:CHAT_PROVIDER='hf_lora'
$env:HF_LORA_BASE_URL='http://127.0.0.1:8011'
$env:WARM_AI_ON_STARTUP='false'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend, terminal riêng trong `frontend`:

```powershell
npm run dev
```

Mở `http://localhost:5173`. `/ready` ở backend phải có `chat_model=qwen2.5-7b-finetuned` và `ai=ok`. Câu giá/FAQ có thể trả lời bằng luật dù chọn 7B. Để kiểm tra có sinh thật, dùng câu giải thích như “Giải thích dễ hiểu vai trò của RAM và SSD khi lựa chọn máy tính cho công việc.”, kiểm tra `intent=llm+rag` và request `/generate` ở log server. Benchmark còn ghi hash identity và trace prompt cho từng lượt gọi.

Timeout demo giữ nguyên: axios 30 giây, AIService mặc định 25 giây, lời gọi generate dành 16 giây để chừa thời gian retrieval/xử lý. Câu dài hoặc lượt đầu có thể hết hạn và tạo ticket; không tăng riêng timeout backend vượt frontend rồi coi demo đã ổn. Benchmark dùng thời hạn riêng, không đại diện trực tiếp cho latency người dùng trên trình duyệt.

Đổi lại base 3B trong terminal khởi động backend:

```powershell
$env:CHAT_PROVIDER='ollama'
$env:CHAT_MODEL='qwen2.5:3b'
$env:USE_PROJECT_CHAT_MODEL='false'
```

Muốn khôi phục lựa chọn profile 3B đã train, đặt `USE_PROJECT_CHAT_MODEL=true`. Dừng server 7B bằng Ctrl+C khi kết thúc để giải phóng VRAM; runner benchmark không tự tắt dịch vụ của người dùng.

## Chạy benchmark

Từ `backend`, dùng Python môi trường web, không phải Python GPU. Runner gọi HTTP tới các dịch vụ. Tách hai pha trên RTX 3060 để model 7B thường trú không tranh VRAM với Ollama 3B.

Pha chính, khi server 7B đã dừng và Ollama có `qwen2.5:3b`, `nomic-embed-text`:

```powershell
python -B -m benchmark.run --validate-only
python -B -m benchmark.run --methods M1 M2 M3 --timeout 60
```

Pha bổ sung: giải phóng model chat 3B, khởi động server 7B như trên, chờ ready:

```powershell
python -B -m benchmark.run --methods M4 --timeout 60
```

Từng phương pháp hoặc tập con:

```powershell
python -B -m benchmark.run --methods M2 --case-ids product-price proof-of-purchase
python -B -m benchmark.run --methods M3 --repeats 3 --timeout 60
python -B -m benchmark.run --methods M4 --dataset benchmark/datasets/techcare_v1.json
```

Mặc định dùng 20 case trong `benchmark/datasets/techcare_v1.json`. `--case-ids` giữ thứ tự trong dataset. Có thể dùng JSONL cùng schema. Mỗi run có thư mục UTC+UUID mới tại `.local/benchmark_results/`, không ghi đè lần trước. So sánh hai pha chỉ khi `dataset_sha256`, toàn bộ `corpus_sha256`, thứ tự case và generation config trùng nhau. Ghi riêng warm-up, các lần lặp và môi trường; không trộn lần thử lỗi vào mẫu latency thành công.

Mã thoát 0: không có lỗi hệ thống (M1 vẫn có thể no_rule_match); mã 2: có error/timeout/not_ready. Mã 0 không có nghĩa câu trả lời đúng. M4 thiếu server/adapter sẽ ghi not_ready, không tạo câu trả lời giả. Các output JSONL/CSV và hướng dẫn chấm nằm trong [README benchmark](../backend/benchmark/README.md).

## Lỗi thường gặp và kiểm tra thủ công

- `Need at least 9 GiB free VRAM`: xem `nvidia-smi`, dừng các model chat đang chiếm VRAM rồi khởi động lại server. Không tự giảm độ chính xác hoặc đổi checkpoint.
- Sai hash/revision, thiếu artifact: kiểm tra đường dẫn/profile và bản gốc. Không bỏ qua kiểm tra hash để ép ready.
- `7B busy`, timeout, vượt context 4096: xem log model và giới hạn request. Không có fallback sang 3B; pipeline vẫn có luật/FAQ, nhưng chế độ hf_lora kiểm tra readiness trước khi xử lý AI.
- Ollama/embedding gián đoạn: M3/M4 có kiểm tra dịch vụ trước case; nếu mất kết nối trong retrieval, trace ghi `retrieval_errors`, pipeline cũ có thể dùng lexical. Index JSON thiếu/cũ cũng ghi `semantic_enabled=false`. Không gọi kết quả đó là cùng cấu hình semantic đang hoạt động.
- `WinError 10013` trong sandbox: phân biệt hạn chế môi trường với dịch vụ thực sự dừng. Không đổi model để che lỗi.
- UI cần kiểm tra trực tiếp: đăng nhập admin, tạo phiên chat, giải thích qua 7B, tải lại lịch sử, mở nguồn, yêu cầu nhân viên/ticket, thử server 7B ngừng. Lint/build và API smoke không thay thế kiểm tra trình duyệt.

Không đưa `.env`, `.local/`, cache, weights mới hoặc dữ liệu khách hàng vào Git. Các weights 3B đã được theo dõi trước đó được giữ nguyên; `.gitignore` mới không xóa chúng khỏi lịch sử.
