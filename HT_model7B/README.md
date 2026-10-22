# Chatbot TechCare — phiên bản Qwen2.5-7B gốc

Bản này chuyển model chat sang `qwen2.5:7b-instruct-fp16` qua Ollama, không fine-tune. Bản 3B trước khi chuyển được giữ ở `../HT_model3B`. Model 7B là Qwen2.5 Instruct chính thức với trọng số FP16 (Ollama ghi `F16`), không chuyển ngược từ Q4; embedding vẫn là `nomic-embed-text`.

Website React/Vite gọi FastAPI. Chatbot trả lời bằng luật/catalog/FAQ hoặc RAG hybrid semantic/BM25 + LLM; có lịch sử hội thoại, ticket và quản trị FAQ/ticket. Sản phẩm/giá/chính sách là dữ liệu mô phỏng nghiên cứu.

## Cài đặt

Cần Python, Node.js và Ollama. Môi trường dùng kiểm tra: Python 3.14.3, Node.js 24.14.0; Vite yêu cầu Node `^20.19.0 || >=22.12.0`. Từ thư mục `HT_model7B`:

```powershell
python -m venv backend\.venv
& .\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
ollama pull qwen2.5:7b-instruct-fp16
ollama pull nomic-embed-text
```

Mở Ollama trước khi dùng. Trọng số 7B FP16 khoảng 15 GB được Ollama quản lý ngoài Git; thông tin phiên bản và giấy phép ở [model manifest](backend/models/qwen2.5-7b/model_manifest.json) và [hướng dẫn model](backend/models/qwen2.5-7b/README.md). Không cần cài adapter, Transformers hoặc PEFT để chạy website. Trọng số đã vượt VRAM 12 GB, chưa tính KV cache; máy ít VRAM cần chia tải sang RAM, có thể chậm hoặc gặp timeout. FP16 không phải cấu hình giảm bộ nhớ so với Q4_K_M.

## Chạy website

Terminal backend, từ `HT_model7B`:

```powershell
Set-Location backend
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Có thể dùng `& .\.venv\Scripts\python.exe run.py` thay lệnh Uvicorn. Nếu đã cài dependencies cho `python` đang dùng, có thể chạy trực tiếp `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.

Terminal frontend mới, từ `HT_model7B`:

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

- Website: http://127.0.0.1:5173/products; hội thoại: http://127.0.0.1:5173/faqs.
- Quản trị: http://127.0.0.1:5173/admin/login (`admin / admin123`, chỉ dùng local).
- API docs: http://127.0.0.1:8000/docs; readiness: http://127.0.0.1:8000/ready.

`/ready` cần có `chat_model: qwen2.5:7b-instruct-fp16`, `ai: ok`, `status: ready`. Readiness chưa kiểm tra embedding/index; cần thử thêm câu RAG thực tế. Dừng bản 3B trước nếu đang dùng các cổng này.

Không cần `.env` cho demo mặc định. Backend tự tạo SQLite `backend/techcare.db`, bảng và 53 sản phẩm/30 FAQ khi bảng trống; các lần sau giữ dữ liệu đã có. Database cần cho sản phẩm/FAQ, lịch sử, ticket và quản trị; kho RAG nằm riêng ở `backend/rag_data/`. Nếu tùy chỉnh, sao chép `backend/.env.example` khi chưa có `.env`; không dùng file cấu hình cá nhân của bản 3B. Biến môi trường terminal ưu tiên hơn default.

## So sánh nghiên cứu

Đây là bản chính của nhánh `benmark-chatbot`. [Bảng phương pháp và P+FT](docs/BENCHMARK_METHODS.md) phân biệt rõ model gốc, corpus RAG, dữ liệu fine-tune và dữ liệu đánh giá. Model demo cũ `techcare-support:3b-v1` không thuộc phép so sánh này.

Nhóm muốn tự nhập 50 câu và chạy **từng phương pháp trên web**: xem [TEST_4_PHUONG_PHAP.md](docs/TEST_4_PHUONG_PHAP.md). Backend dùng `python comparison_demo.py`, frontend dùng `npm.cmd run test:methods`; kết quả mới tách khỏi lịch sử khách hàng và benchmark cũ.

| Phương pháp | Model của lượt chạy mới |
|---|---|
| B0 | Luật, không gọi LLM |
| B1 | `qwen2.5:7b-instruct-fp16`, không RAG |
| B2 | `qwen2.5:7b-instruct-fp16`, RAG cơ bản |
| P | `qwen2.5:7b-instruct-fp16`, pipeline đề xuất |

Giữ nguyên thuật toán, dữ liệu, câu hỏi/lịch sử, prompt và generation settings: temperature 0, context 4096, output 384, repeat_penalty 1; K=5, threshold 0,38. Mỗi study mới ghi model trong protocol/manifest và identity/digest thực tế trong kết quả. Bản vá website có sẵn không được dùng thay pipeline P trong benchmark. P+FT là thử nghiệm bổ sung, không thuộc bốn phương pháp chính: [adapter QLoRA 7B gốc](backend/models/qwen2.5-7b-ft/README.md) đã đóng gói cùng hồ sơ 37 train/9 validation/1 epoch. Không huấn luyện mới trong lần đóng gói này.

[Kết quả 3B đã đóng gói](docs/research/chapter5-24/README.md) được giữ nguyên; chưa được gọi là kết quả 7B. Lượt smoke 7B Q4 trước khi đổi precision cũng không phải kết quả FP16. [Hướng dẫn tái lập](docs/REPRODUCING_RESEARCH.md) tạo study mới và không ghi đè lượt cũ. Không train hoặc nạp đáp án test vào RAG.

## Kiểm thử và giới hạn

Từ `HT_model7B`, khi đã cài dependencies backend/frontend và có Ollama:

```powershell
.\run_tests.ps1
```

Runner dùng DB thử và lưu output ngoài project. [Cấu hình và cập nhật dữ liệu](docs/README.md), [demo bốn phương pháp](docs/LOCAL_BENCHMARK_DEMO.md), [giấy phép](docs/THIRD_PARTY_NOTICES.md).

Corpus kỹ thuật còn thiếu; có fallback/ticket khi thiếu bằng chứng. Các lỗi trong luật lọc sản phẩm không tự biến mất khi đổi model. Chưa đo hiệu năng laptop RTX 3050; không cam kết chạy hoàn toàn trên GPU 6 GB. npm còn cảnh báo dependency Tailwind cần rà soát trước triển khai công khai. Đây là bản nghiên cứu local, chưa phải production.
