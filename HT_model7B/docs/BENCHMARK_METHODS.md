# Bốn phương pháp chính và P+FT bổ sung

Nhánh GitHub: `benmark-chatbot`. Hệ thống chính: `HT_model7B`.

| Mã | Phương pháp | Model trong lượt chạy mới | Huấn luyện thêm |
|---|---|---|---|
| B0 | Luật/catalog/FAQ | Không dùng LLM | Không |
| B1 | LLM thuần, không RAG | `qwen2.5:7b-instruct-fp16` gốc | Không |
| B2 | RAG cơ bản, semantic top-5 + LLM | Cùng model gốc như B1 | Không |
| P | Pipeline RAG nhóm đề xuất: xử lý truy vấn, hybrid semantic/BM25, xếp hạng miền, ngữ cảnh sản phẩm, kiểm tra đầu ra, luật/FAQ | Cùng model gốc như B1 | Không |
| P+FT | Cùng pipeline P + adapter QLoRA | Base `unsloth/Qwen2.5-7B-Instruct-bnb-4bit` + adapter 7B đã xác minh, NF4/BF16 | 37 train, 9 validation, 1 epoch |

**P là phương pháp chính của nhóm và không fine-tune.** Đổi 3B gốc sang 7B gốc là thay model nền. Corpus/index RAG phục vụ truy xuất, không cập nhật trọng số. Bộ test dùng đánh giá, không đưa vào train hoặc nạp đáp án vào RAG.

`techcare-support:3b-v1` là model demo cũ, đã fine-tune với 170 train/9 validation. Nó chỉ được lưu ở `HT_model3B`, không dùng trong B1/B2/P của benchmark mới và không phải adapter P+FT 7B.

Mã M1/M2/M3/M4 chỉ giữ tương thích bộ phát triển cũ: M1 = luật, M2 = LLM thuần, M3 = pipeline đầy đủ, M4 = fine-tune 7B bổ sung. Bộ cũ không có RAG cơ bản B2 riêng, nên không đổi nhãn M1–M4 thành bốn phương pháp chính mới.

## Chạy bốn phương pháp chính

Thử câu hỏi trên web và xuất CSV theo [TEST_4_PHUONG_PHAP.md](TEST_4_PHUONG_PHAP.md). Benchmark kiểm soát trên bộ 24 câu theo [REPRODUCING_RESEARCH.md](REPRODUCING_RESEARCH.md). Cả giao diện và runner mặc định chỉ chọn B0/B1/B2/P. Lệnh `python -B -m benchmark.run` mặc định dùng bộ phát triển 20 câu; không gọi kết quả đó là bộ 24 câu Chương 5.

## Chuẩn bị P+FT đã tinh chỉnh

Adapter gốc được đóng gói tại `backend/models/qwen2.5-7b-ft/run/adapter`, kèm `run.json` tóm tắt metadata 37 train/9 validation/1 epoch, giấy phép và manifest checkpoint. Mẫu dữ liệu và log hội thoại huấn luyện không phát hành lên GitHub. Trọng số không được train lại, merge hoặc chuyển đổi. SHA256 adapter: `b7650bf5a6a4eb02b902bb9a5758d178c3e4f32c5329013ca7c819045d8008b7`.

Từ gốc repository, tải riêng adapter qua Git LFS:

```powershell
git lfs pull --include="HT_model7B/backend/models/qwen2.5-7b-ft/run/adapter/adapter_model.safetensors"
Set-Location HT_model7B\backend
```

Checkpoint nền tải từ Hugging Face đúng revision, không dùng model Ollama FP16 làm base cho adapter. Dùng Python của môi trường GPU đã cài các thư viện nêu trong [hướng dẫn serving](MODELS_AND_BENCHMARK.md); `$gpuPython` là đường dẫn Python đó:

```powershell
& $gpuPython -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='unsloth/Qwen2.5-7B-Instruct-bnb-4bit', revision='bdd404162d94997f390efbfa660eb3f21cbbc81d', local_dir='artifacts/qwen25_7b/checkpoint')"
Copy-Item -LiteralPath models\qwen2.5-7b-ft\checkpoint_manifest.json -Destination artifacts\qwen25_7b\checkpoint\checkpoint_manifest.json
& $gpuPython -B -m model_serving.server --check-only
& $gpuPython -B -m model_serving.server --port 8011
```

Checkpoint khoảng 5,55 GB, không đóng gói vào Git. `--check-only` kiểm tra hash checkpoint, adapter và metadata trước khi nạp GPU. Metadata adapter gốc còn đường dẫn base trên máy huấn luyện; server nạp base/adapter từ profile hiện tại, không dùng đường dẫn cũ đó. Bản tóm tắt run ghi hash log gốc để đối chiếu, không thay thế việc kiểm tra toàn bộ dữ liệu/lượt train tại máy tác giả.

Server gốc yêu cầu CUDA/BF16 và ít nhất 9 GiB VRAM trống lúc nạp. Cấu hình này không chạy trên GPU 6 GB theo cơ chế serving hiện tại. Thiếu model/bộ nhớ phải ghi lỗi, không đổi sang model khác.

## Chạy P+FT riêng

Với study mới đã chuẩn bị theo hướng dẫn tái lập, mở terminal backend thứ hai, giữ `$study` là đường dẫn study đó. Giữ Ollama phục vụ embedding và bảo đảm server 8011 có `/health` đúng model/hash, `status=ready`, `adapter_loaded=true`:

```powershell
python -B -m benchmark.chapter5 run --study $study --phase smoke --methods 'P+FT' --timeout 60
python -B -m benchmark.chapter5 run --study $study --phase supplementary --methods 'P+FT' --timeout 60
python -B -m benchmark.chapter5 collect --study $study
```

Chạy tuần tự và giải phóng model chat Ollama nếu đang chiếm VRAM trước khi nạp server adapter. Không gộp P+FT vào phase `main`; giao diện test bốn phương pháp chỉ dành cho B0/B1/B2/P.

## Đọc kết quả đúng phạm vi

Kết quả đóng gói ngày 16/10 dùng B1/B2/P base 3B gốc và P+FT 7B; chúng là kết quả lịch sử. Study mới dùng base 7B FP16 và ghi kết quả mới riêng. Không đổi nhãn, ghi đè hoặc ghép số đo giữa hai study. P/P+FT khác trọng số, precision và runtime; phép so sánh không cô lập riêng tác động của fine-tuning. Điểm AI đã lưu chỉ là sơ bộ, cần người chấm kiểm tra.
