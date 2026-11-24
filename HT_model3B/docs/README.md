# Hướng dẫn cấu hình và tài liệu

[README gốc](../README.md) hướng dẫn chạy website. `backend/run.py` chuyển thư mục làm việc về `backend` rồi chạy Uvicorn, để `.env` và đường dẫn SQLite tương đối luôn được đọc tại đúng checkout.

## Cấu hình demo

Các giá trị dưới đây đã có default trong `app/config.py`; không cần export trong terminal. `.env` là tùy chọn, biến môi trường tiến trình ưu tiên hơn `.env`.

| Biến | Mặc định / tác dụng |
|---|---|
| DATABASE_URL | SQLite `backend/techcare.db`, tính từ vị trí source; không phụ thuộc ổ đĩa máy phát triển |
| ENVIRONMENT | development; không bỏ xác thực admin |
| AUTO_SEED | true; chỉ nạp sản phẩm/FAQ khi bảng tương ứng trống |
| CHAT_PROVIDER / CHAT_MODEL | ollama / qwen2.5:3b |
| USE_PROJECT_CHAT_MODEL | true; profile đổi base 3B thành `techcare-support:3b-v1` |
| OLLAMA_BASE_URL | http://localhost:11434 |
| WARM_AI_ON_STARTUP | true; warm-up dịch vụ đã cài, không tải trọng số |
| CORS_ORIGINS | localhost và 127.0.0.1 cổng 5173/4173 |

`PYTHONDONTWRITEBYTECODE` là tùy chọn của Python, không phải điều kiện chạy chatbot. Muốn dùng PostgreSQL, đặt URL SQLAlchemy hợp lệ trong `.env`, tự chuẩn bị dịch vụ và driver đã có trong requirements; SQLite đủ cho demo. Không đổi URL của database đang dùng nếu chưa sao lưu và hiểu rằng lịch sử/ticket không tự chuyển theo.

## Database và RAG

`app/main.py` tạo bảng qua SQLAlchemy rồi gọi `seed.py` nếu bật `AUTO_SEED`. Database mới có 53 sản phẩm và 30 FAQ. Dữ liệu đã có không bị xóa hoặc seed lại mỗi lần khởi động.

SQLite có quyền ghi dùng chế độ WAL để các lượt đọc và ghi hội thoại đồng thời ít chặn nhau; snapshot nghiên cứu mở chỉ đọc giữ nguyên chế độ gốc. Các file `techcare.db-wal`/`techcare.db-shm` cũng là dữ liệu runtime bị Git bỏ qua; không sao chép riêng file database khi ứng dụng đang ghi.

Database lưu sản phẩm, FAQ, phiên/tin nhắn hội thoại và ticket. API chat cần database để xác thực phiên và lưu kết quả. Catalog runtime ưu tiên sản phẩm trong database, FAQ quản trị cũng đọc từ database. Tài khoản admin/JWT đọc từ cấu hình. Đổi database làm website thấy dữ liệu/phiên/ticket của database mới; không thể bỏ dependency này để chạy đầy đủ website.

RAG có kho tài liệu và chỉ mục JSON riêng trong `backend/rag_data/`. Sau khi duyệt cập nhật sản phẩm/FAQ, từ `backend`:

```powershell
& .\.venv\Scripts\python.exe export_rag.py
& .\.venv\Scripts\python.exe rebuild_rag.py
```

Export đọc dữ liệu active từ database; rebuild cần Ollama/embedding và cập nhật chỉ mục. Khởi động lại backend sau rebuild. Không đưa answer key hay chính sách của doanh nghiệp khác vào tri thức demo. `sync_verified_products.py` có sửa dữ liệu, chỉ dùng sau khi duyệt.

## Kiểm thử và đổi model

Từ gốc project, khi đã cài backend/frontend và có Ollama:

```powershell
.\run_tests.ps1
```

Runner dùng database thử riêng; log/phản hồi mới nằm ngoài repository tại Temp hoặc `-WorkDir <thư-mục-ngoài-repo>`. Bao gồm backend unit/integration, regression API, FAQ online/offline, frontend lint/build. Các test luật/mock không thay thế đánh giá chất lượng LLM thật.

Chuyển về base 3B: tải `ollama pull qwen2.5:3b`, đặt `CHAT_MODEL=qwen2.5:3b` và `USE_PROJECT_CHAT_MODEL=false` trong cấu hình riêng rồi khởi động lại backend. Bỏ override để về model demo; không cần train.

## Tài liệu nghiên cứu

- [Tái lập nghiên cứu trên máy khác](REPRODUCING_RESEARCH.md).
- [Giao thức Chương 5](CHAPTER5_RUNBOOK.md), [bằng chứng 24 câu](research/chapter5-24/README.md).
- [Demo web bốn phương pháp](LOCAL_BENCHMARK_DEMO.md).
- [Serving 7B bổ sung](MODELS_AND_BENCHMARK.md), [schema/rubric benchmark](../backend/benchmark/README.md).
- [Model demo 3B](../backend/models/techcare-support-3b-v1/README.md), [giấy phép và nguồn](THIRD_PARTY_NOTICES.md).
- [Đối chiếu thông số gốc](history/PRODUCT_DATA_AUDIT.md): giữ vì dataset benchmark M1–M4 tham chiếu tài liệu này; không phải hướng dẫn chạy hiện hành.

Các đường dẫn máy gốc trong manifest/raw evidence chỉ ghi provenance, không phải cấu hình chạy website.
