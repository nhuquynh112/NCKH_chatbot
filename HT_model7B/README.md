# Chatbot TechCare — phiên bản Qwen2.5-7B gốc

Bản này chuyển model chat sang `qwen2.5:7b-instruct-fp16` qua Ollama, không fine-tune. Bản 3B trước khi chuyển được giữ ở `../HT_model3B`. Model 7B là Qwen2.5 Instruct chính thức với trọng số FP16 (Ollama ghi `F16`), không chuyển ngược từ Q4; embedding vẫn là `nomic-embed-text`.

Website React/Vite gọi FastAPI. Chatbot trả lời bằng luật/catalog/FAQ hoặc RAG hybrid semantic/BM25 + LLM; có lịch sử hội thoại, ticket và quản trị FAQ/ticket. Sản phẩm/giá/chính sách là dữ liệu mô phỏng nghiên cứu.

Website có lớp xử lý giao tiếp riêng, gồm tư vấn điện thoại chung theo ngân sách và xử lý lời góp ý sau danh sách gợi ý. Lớp này ưu tiên smartphone có thông tin Android/iOS trong catalog, không mặc định chọn máy phổ thông rẻ nhất. Các yêu cầu thông số cụ thể vẫn đi qua luồng nghiệp vụ hiện có. Pipeline P của benchmark vẫn dùng factory gốc, không nhận bản sửa website này; không trộn kết quả giữa hai luồng. Sửa code backend cần khởi động lại Uvicorn để nhận thay đổi.

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

Không cần `.env` cho demo mặc định. Backend tự tạo SQLite `backend/techcare.db`, bảng và 150 sản phẩm/30 FAQ khi bảng trống; các lần sau giữ dữ liệu đã có. Database cần cho sản phẩm/FAQ, lịch sử, ticket và quản trị. Kho đang dùng là `backend/rag_data_150/`; `backend/rag_data/` giữ nguyên làm corpus lịch sử. Nếu tùy chỉnh, sao chép `backend/.env.example` khi chưa có `.env`; không dùng file cấu hình cá nhân của bản 3B. Biến môi trường terminal ưu tiên hơn default.

Catalog mới lấy từ 151 link CellphoneS do nhóm chọn, thu thập ngày 23/10/2026; bản hiện tại còn 150 sản phẩm sau khi loại mẫu có thông số không nhất quán. Chỉ mục hiện có 299 tài liệu. Thông số được ghi là do nhà bán lẻ công bố, chưa mặc định đã đối chiếu hãng. Giá được dùng làm giá demo tại thời điểm thu thập; điều kiện bảo hành của nguồn không tự động trở thành chính sách TechCare. Ảnh và nguồn xem trên trang chi tiết; danh sách nguồn/phiên bản và mẫu bị loại nằm trong `rag_data_150/catalog_manifest.json` và `product_verified_specs.json`.

Máy đã có database catalog cũ cần dừng backend và đồng bộ **một lần**, từ thư mục backend. Bản sao database được lưu ngoài repository; sản phẩm cũ chỉ bị ẩn, không xóa lịch sử/ticket:

```powershell
& .\.venv\Scripts\python.exe sync_catalog.py --replace-active --backup-dir D:\TechCareBackup
```

Khi pull catalog và chỉ mục đã đóng gói, chỉ cần lệnh đồng bộ trên rồi mở lại backend; không cần dựng lại chỉ mục. Khi nhóm tự chỉnh dữ liệu sản phẩm, xuất lại và rebuild embedding/index bằng `export_rag.py` và `rebuild_rag.py` (cùng Python của `.venv`). Các script mặc định ghi vào `rag_data_150`, không train LLM; embedding dùng `nomic-embed-text`.

## So sánh nghiên cứu

Nhóm muốn tự nhập 50 câu và chạy **từng phương pháp trên web**: xem [TEST_4_PHUONG_PHAP.md](docs/TEST_4_PHUONG_PHAP.md). Backend dùng `python comparison_demo.py`, frontend dùng `npm.cmd run test:methods`; kết quả mới tách khỏi lịch sử khách hàng và benchmark cũ.

| Phương pháp | Model của lượt chạy mới |
|---|---|
| B0 | Luật, không gọi LLM |
| B1 | `qwen2.5:7b-instruct-fp16`, không RAG |
| B2 | `qwen2.5:7b-instruct-fp16`, RAG cơ bản |
| P | `qwen2.5:7b-instruct-fp16`, pipeline đề xuất |

Giữ nguyên thuật toán, prompt và generation settings: temperature 0, context 4096, output 384, repeat_penalty 1; K=5, threshold 0,38. Lượt test web mới dùng snapshot `rag_data_150` cho B0/B2/P; B1 không đọc corpus. Cùng một lượt so sánh phải giữ nguyên corpus và câu hỏi/lịch sử. Không so trực tiếp số liệu catalog mới với benchmark 24 câu trên catalog cũ. Mỗi study mới ghi model trong protocol/manifest và identity/digest thực tế trong kết quả. Bản vá website có sẵn không được dùng thay pipeline P trong benchmark. P+FT chỉ là thử nghiệm lịch sử, không thuộc phép so sánh 7B gốc này.

[Kết quả 3B đã đóng gói](docs/research/chapter5-24/README.md) được giữ nguyên; chưa được gọi là kết quả 7B. Lượt smoke 7B Q4 trước khi đổi precision cũng không phải kết quả FP16. [Hướng dẫn tái lập](docs/REPRODUCING_RESEARCH.md) tạo study mới và không ghi đè lượt cũ. Không train hoặc nạp đáp án test vào RAG.

## Kiểm thử và giới hạn

Từ `HT_model7B`, khi đã cài dependencies backend/frontend và có Ollama:

```powershell
.\run_tests.ps1
```

Runner dùng DB thử và lưu output ngoài project. [Cấu hình và cập nhật dữ liệu](docs/README.md), [demo bốn phương pháp](docs/LOCAL_BENCHMARK_DEMO.md), [giấy phép](docs/THIRD_PARTY_NOTICES.md).

Unit tests có kiểm tra catalog 150 sản phẩm mới. Các script đánh giá với câu hỏi/đáp án cố định cũ được runner giữ trên corpus `rag_data`; chúng là kiểm tra hồi quy, không phải điểm chất lượng của lượt test 50 câu mới.

Corpus kỹ thuật còn thiếu; có fallback/ticket khi thiếu bằng chứng. Các lỗi trong luật lọc sản phẩm không tự biến mất khi đổi model. Chưa đo hiệu năng laptop RTX 3050; không cam kết chạy hoàn toàn trên GPU 6 GB. npm còn cảnh báo dependency Tailwind cần rà soát trước triển khai công khai. Đây là bản nghiên cứu local, chưa phải production.
