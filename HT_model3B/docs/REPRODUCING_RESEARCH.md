# Tái lập nghiên cứu trên máy khác

## Đọc kết quả đã lưu

Bộ câu hỏi gốc được sao chép nguyên byte vào `backend/benchmark/datasets/chapter5_24/`: 24 input, answer key tách riêng, hướng dẫn chấm và hai nguồn catalog/FAQ. Không đổi câu hỏi hay lịch sử. `approval_record.json` trích xác nhận đã có từ protocol gốc, không phải một phê duyệt mới. Manifest gốc vẫn giữ trạng thái lịch sử của nó.

[Bằng chứng đóng gói](research/chapter5-24/README.md) chứa 96 raw responses B0/B1/B2/P, 24 phản hồi P+FT 7B, bảng tổng hợp và điểm **AI sơ bộ**. Chúng được sao chép từ lần chạy 16/10, không được tính lại khi đóng gói. Chưa thay thế việc nhóm duyệt điểm hoặc hai người chấm độc lập. Model demo 3B đã train không được dùng thay base 3B trong phép so sánh này.

## Tạo một study mới

Cần Ollama với `qwen2.5:3b` và `nomic-embed-text`, cùng môi trường backend đã cài. Từ thư mục gốc project:

```powershell
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
$researchWork = Join-Path $env:TEMP ('TechCareStudy-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $researchWork | Out-Null
$study = Join-Path $researchWork 'study'
$env:DATABASE_URL = 'sqlite:///' + (Join-Path $researchWork 'controller.db').Replace('\','/')
$env:ENVIRONMENT='test'
$env:WARM_AI_ON_STARTUP='false'
Set-Location backend
& .\.venv\Scripts\python.exe -B -m benchmark.chapter5 prepare --package '.\benchmark\datasets\chapter5_24' --study $study --approval-record '.\benchmark\datasets\chapter5_24\approval_record.json'
& .\.venv\Scripts\python.exe -B -m benchmark.chapter5 run --study $study --phase smoke --methods B0 B1 B2 P --timeout 60
& .\.venv\Scripts\python.exe -B -m benchmark.chapter5 run --study $study --phase main --methods B0 B1 B2 P --timeout 60
& .\.venv\Scripts\python.exe -B -m benchmark.chapter5 collect --study $study
```

Mỗi study/run là mới, hash code/corpus/prompt/model được ghi lại. Code, byte xuống dòng, runtime và trạng thái máy khác có thể tạo kết quả khác; không gắn kết quả mới vào bảng của lần chạy cũ. Giữ nguyên K=5, ngưỡng 0,38 và generation settings đã định nghĩa. Chạy smoke thành công trước main. Không đưa answer key vào prompt, RAG hoặc train.

Sáu ablation và các giới hạn diễn giải giữ ở [giao thức Chương 5](CHAPTER5_RUNBOOK.md). Phải smoke các biến thể trước phase ablation. Đóng gói release không chạy lại hoặc thay số liệu mục 5.6.

## P+FT 7B là thí nghiệm bổ sung

Không chép checkpoint vào repo. Giữ profile gốc ở `backend/model_serving/profiles/qwen25_7b.json`, hash checkpoint/adapter và mã serving. Máy khác cần nhận artifact gốc hợp lệ cùng manifest/run.json và runtime GPU tương thích; bản clone riêng lẻ chưa đủ để chạy P+FT. Server yêu cầu CUDA/BF16 và ít nhất 9 GiB VRAM trống, do đó không phải cấu hình demo cho laptop RTX 3050 6 GB.

Để đổi đường dẫn, tạo một bản sao profile **ngoài repo**, chỉ sửa `checkpoint_path` và `adapter_path`, giữ nguyên repo/revision/hash/model. Chạy từ `backend` bằng Python môi trường GPU riêng:

```powershell
# $gpuPython: đường dẫn Python GPU đã cài và kiểm tra trên máy của bạn.
# $gpuProfile: JSON profile riêng trỏ đúng artifact gốc.
& $gpuPython -B -m model_serving.server --profile $gpuProfile --check-only
& $gpuPython -B -m model_serving.server --profile $gpuProfile --port 8011
```

Đối chiếu `/health` đúng identity và ready rồi mới chạy smoke/supplementary `P+FT` như [hướng dẫn](MODELS_AND_BENCHMARK.md). Không fallback model khác nếu thiếu artifact. P so P+FT thay đồng thời kích thước, runtime, lượng tử hóa và fine-tuning; không quy toàn bộ chênh lệch cho QLoRA.

## Demo giao diện của benchmark

[Harness web](LOCAL_BENCHMARK_DEMO.md) dùng snapshot và database đã chạy của study gốc; nó chủ ý không seed một database thay thế. File benchmark raw không tự trở thành lịch sử khách hàng trên website. Khi thiếu snapshot/identity/source hash, demo sẽ báo lỗi; không tạo phản hồi giả hoặc đổi nhãn từ kết quả khác.
