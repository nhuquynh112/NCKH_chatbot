# Model 3B đã train cho chatbot TechCare

Built with Qwen. Đây là model nghiên cứu dùng cùng catalog, FAQ, RAG và lớp kiểm tra dữ kiện của website; xem giấy phép Qwen Research License trong `LICENSE`.

- `techcare-support-3b-v1-Q4_K_M.gguf`: model hoàn chỉnh được chatbot dùng qua Ollama, 1.929.902.496 byte, SHA256 `87710c00e7b1da9c873d2ba0ddc89e89eb24075f81ebfba55ed527832ecc3b18`.
- `adapter/`: adapter gốc đã train, tokenizer và metadata để tái tạo. Trọng số adapter giữ nguyên; metadata base được đổi từ đường dẫn máy bàn sang repo/revision nguồn để có thể mang sang máy khác.
- `data/`: 170 train, 9 validation, test tổng hợp ban đầu 21 câu và test mới 12 câu, kèm manifest. Không chứa toàn bộ dữ liệu CSConDa tải về hoặc test chính thức 1.500 dòng.
- `evidence/`: kết quả train, cả cấu hình chạy đầu chưa tốt và cấu hình được chọn, đối chiếu nguồn checkpoint/dataset, kiểm tra RAG/API và trạng thái ứng dụng thật. Đường dẫn tuyệt đối trong các bản ghi gốc phản ánh nơi chạy thí nghiệm lúc đó, không phải đường dẫn cài hiện tại.

Từ thư mục gốc project chạy `install_trained_model.ps1` để import model. Sau khi clone GitHub cần `git lfs pull`; khi sao chép project trực tiếp cần giữ cả file trọng số thực, không chỉ LFS pointer. `.gitattributes` quản lý GGUF và safetensors bằng Git LFS.

## Tái tạo huấn luyện

Mã nguồn ở `backend/training`. Dùng môi trường GPU riêng; không cài thư viện huấn luyện vào môi trường FastAPI. Cấu hình đã chạy: Windows, Python 3.14, torch 2.14.1+cu126, Transformers 5.19.0, PEFT 0.21.2, bitsandbytes 0.50.2. Danh sách đầy đủ ở `requirements-lock.txt`.

Checkpoint nguồn là `unsloth/Qwen2.5-3B-Instruct-bnb-4bit`, revision `2672b588848527e456d320c11926c794539f47d5`. Giữ checkpoint/cache tại `D:\NCKH\Codex\training_cache\qwen25_3b_nf4` hoặc đặt `CHATBOT_WORK_DIR` riêng. Manifest file nguồn có trong `evidence/checkpoint_manifest.json`; script xác minh từng hash trước khi train. Nếu tải lại checkpoint, sao chép manifest đó vào thư mục checkpoint đã tải.

Trên máy bàn hiện tại, từ thư mục `backend`:

```powershell
& 'D:\NCKH\Codex\.venv-training\Scripts\python.exe' -m training.train_qlora --run-dir 'D:\NCKH\Codex\training_runs\reproduce_3b'
& 'D:\NCKH\Codex\.venv-training\Scripts\python.exe' -m training.merge_export --run-dir 'D:\NCKH\Codex\training_runs\reproduce_3b'
```

`--run-dir` phải mới để giữ bằng chứng của từng lượt. Mặc định dùng dữ liệu trong project, 2 epoch, rank 16 all-linear, LR 1e-4 và sequence 512. Có thể truyền `--checkpoint`/`--data` để đổi vị trí file, nhưng thay dữ liệu/cấu hình tạo ra thí nghiệm mới. GGUF F16, bản merge, log và model thử mới chỉ giữ trong thư mục làm việc bên ngoài cho đến khi được chọn.

Sau merge, công cụ llama.cpp chuyển `merged_dense` sang F16 GGUF rồi lượng tử hóa Q4_K_M. Lượt đã xác nhận dùng source llama.cpp commit `318a471a6295e53bfce7ca96ae0cf26071cbdd6e`, công cụ quantize b11612. Bộ công cụ/môi trường tải về thuộc cache thí nghiệm, không kèm vào project. Luôn đánh giá GGUF cuối trước khi thay model chính.

## Dữ liệu và giới hạn kết quả

37 train CSConDa đã lọc cộng 133 ví dụ tổng hợp; 9 validation giữ theo nhóm tình huống. Trong 46 mẫu CSConDa chấp nhận, 12 đáp án nguyên bản và 34 đáp án được agent biên tập; nhãn nguồn được giữ trong từng dòng. CSConDa công bố Apache 2.0, nguồn [Vietnamese Customer Support QA](https://huggingface.co/datasets/ura-hcmut/Vietnamese-Customer-Support-QA), revision `ae8232e93a2ce4edb15560f6ef8e52f38ce1733d`; cần trích dẫn bài CSConDa, DOI `10.1007/978-3-032-10202-7_33`. Quyết định duyệt từng mẫu và file nguồn đầy đủ vẫn ở thư mục làm việc ban đầu.

Giá/chính sách trong ví dụ tổng hợp là mô phỏng, không đưa ngược vào database bán hàng. Test chính thức CSConDa không dùng cho train, RAG hoặc chọn cấu hình. Trên 12 câu tổng hợp mới, base đạt 10/12 và bản đã train 12/12 theo tiêu chí tự động; đây không phải độ chính xác trên khách thật. Báo cáo đầy đủ ở [docs/history/CHATBOT_EVALUATION_REPORT.md](../../../docs/history/CHATBOT_EVALUATION_REPORT.md).
