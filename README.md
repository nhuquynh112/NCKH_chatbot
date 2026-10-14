# TechCare Electronics — chatbot chăm sóc khách hàng

Ứng dụng demo gồm website bán thiết bị công nghệ, chatbox AI/RAG, lưu lịch sử hội thoại, tự tạo ticket khi không đủ dữ liệu và trang quản trị FAQ/ticket.

## Yêu cầu

- Python 3.11 trở lên
- Node.js 20 trở lên
- [Ollama](https://ollama.com/) với `techcare-support:3b-v1` (3B đã fine-tune) và `nomic-embed-text`; giữ `qwen2.5:3b` để so sánh hoặc quay lại bản gốc.

## Bản 3B đã train và chuyển sang laptop

Bản `techcare-support:3b-v1` đã được cài trên máy bàn, dùng làm model chính qua `backend/rag_data/model_profile.json`, không thay `.env`. QLoRA chạy trên RTX 3060 với 170 mẫu, 2 epoch. Model đã xác nhận, adapter, dữ liệu đã lọc và kết quả cần cho đề tài nằm trong `backend/models/techcare-support-3b-v1`; mã huấn luyện ở `backend/training`. Môi trường GPU, cache, log và thử nghiệm chưa chọn vẫn ở `D:\NCKH\Codex`.

Sao chép cả project sang laptop hoặc clone với Git LFS rồi chạy từ thư mục gốc project:

```powershell
git lfs pull
.\install_trained_model.ps1
ollama pull nomic-embed-text
```

File model khoảng 1,93 GB. Script đối chiếu SHA256, import local và giữ file tạm ngoài project. Nếu laptop không có ổ D, truyền thêm `-WorkDir "$env:TEMP\TechCare"`. Khởi động lại backend sau khi cài. `/ready` phải có `chat_model: techcare-support:3b-v1` và `ai: ok`.

Các file GGUF và safetensors được quản lý bằng [Git LFS](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage), vì vượt giới hạn file Git thông thường. Cài Git LFS trước khi clone/push; sau clone chạy `git lfs pull` để lấy trọng số. Khi sao chép project trực tiếp, không cần bước tải LFS. Xem README trong thư mục model để tái tạo huấn luyện.

Để quay lại model gốc, cài `qwen2.5:3b`, đặt `$env:USE_PROJECT_CHAT_MODEL='false'` trong terminal chạy backend rồi khởi động lại. Model tuỳ chỉnh khác trong `CHAT_MODEL` vẫn được ưu tiên. Bản 3B tuân theo **Qwen Research License**, được giữ trong Modelfile; dữ liệu giá/chính sách vẫn là mô phỏng nghiên cứu.

## Chạy nhanh trên Windows

Mở terminal thứ nhất:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
..\install_trained_model.ps1
python rebuild_rag.py
uvicorn app.main:app --reload
```

Mở terminal thứ hai:

```powershell
cd frontend
npm install
npm run dev
```

Truy cập `http://localhost:5173`. API docs ở `http://localhost:8000/docs`.

Nếu project đang có `backend/.env` trỏ tới PostgreSQL thì cấu hình đó vẫn được ưu tiên. Muốn chạy bản demo độc lập, sao chép `.env.example` thành `.env` hoặc đổi `DATABASE_URL` sang SQLite như ví dụ.

Mặc định dự án dùng SQLite tại `backend/techcare.db` và tự nạp dữ liệu mẫu, nên không cần Docker/PostgreSQL. Nếu muốn dùng PostgreSQL, đặt lại `DATABASE_URL` trong `backend/.env` rồi chạy `python seed.py`.

## Chạy kiểm thử

Từ thư mục gốc dự án, cách đơn giản nhất:

```powershell
.\run_tests.ps1
```

Script dùng database kiểm thử riêng để chạy unit test backend, hồi quy catalog/API/tải đồng thời, bộ FAQ/RAG cố định, tình huống Ollama gián đoạn, frontend lint và production build. Database tạm, cache và kết quả nằm ngoài repo tại `D:\NCKH\Codex`; có thể đổi bằng `-WorkDir` hoặc `CHATBOT_WORK_DIR`. Xem [cải tiến và cách demo](CHATBOT_IMPROVEMENTS.md), [audit](CHATBOT_AUDIT.md), [kết quả đo](CHATBOT_EVALUATION_REPORT.md) và [nguồn dataset](DATASET_CANDIDATES.md).

`evaluate_chatbot.py` giữ 225 tình huống hồi quy, kiểm tra 53 sản phẩm và 16 yêu cầu API đồng thời; kết quả ở `backend/EVALUATION_REPORT.md`. `evaluate_quality.py` dùng 32 câu cố định có FAQ/paraphrase, nhiều lượt, thiếu dữ liệu và bảo mật. Model 3B đã xác nhận, dữ liệu chọn lọc và bằng chứng chính được giữ cùng project; thử nghiệm, checkpoint nguồn/cache và log nằm tại `D:\NCKH\Codex`. Báo cáo tổng hợp ở `CHATBOT_EVALUATION_REPORT.md`. Tỷ lệ đạt tiêu chí của pipeline luật/FAQ không phải độ chính xác LLM.

Đây là kiểm thử hồi quy trên dữ liệu TechCare, không phải cam kết rằng chatbot đúng 100% với mọi câu ngoài đời. Muốn dùng cho khách thật, quản trị viên phải cập nhật giá, sản phẩm active, thông số và chính sách trong database/FAQ; chatbot sẽ từ chối suy đoán trường dữ liệu chưa có.

## Kiến trúc trả lời

1. Lớp luật xử lý các dữ kiện cần chính xác tuyệt đối: giá, bảo hành, so sánh, ngân sách, tra cứu đơn và sự cố kỹ thuật.
   Danh mục sản phẩm đang hoạt động được đọc trực tiếp từ bảng `products`; file JSON chỉ là dữ liệu dự phòng khi database chưa sẵn sàng.
2. FAQ quản trị phù hợp và 30 FAQ biên tập được ưu tiên; retriever kết hợp semantic và BM25 tìm ngữ cảnh trong Knowledge Base, catalog và FAQ. FAQ vô hiệu hóa không được hồi sinh từ bản biên tập cùng câu hỏi.
3. Ollama diễn đạt câu trả lời dựa trên ngữ cảnh; không có dữ liệu thì fallback và tạo ticket.
4. Chỉ mục JSON là mặc định để demo chạy ổn định. Có thể cài `requirements-chroma.txt` và đặt `VECTOR_STORE_BACKEND=chroma` để dùng ChromaDB.
5. Với model không có trong catalog, chatbot không đoán giá hoặc tồn kho mà tạo link tìm kiếm Google và Google Shopping theo tên sản phẩm. Giao diện tự hiển thị các URL này thành liên kết mở ở tab mới và kèm cảnh báo TechCare không xác minh nguồn bán bên ngoài.
6. Tin nhắn có số điện thoại được che bớt trong lịch sử. Mật khẩu, OTP, CVV/CVC và số thẻ bị thay bằng nhãn đã ẩn, không được chuyển vào RAG hay tự động tạo ticket.
7. Các yêu cầu tiết lộ prompt hệ thống, khóa truy cập hoặc bỏ qua quy tắc an toàn được chặn ở lớp luật trước khi gọi mô hình.
8. Lời gọi AI có thời gian chờ tối đa; nếu Ollama treo hoặc mất kết nối, hệ thống trả lời an toàn và chuyển ticket thay vì để giao diện chờ vô hạn. Endpoint `/ready` cho biết riêng trạng thái database và Ollama.
9. Mọi thao tác đọc, gửi, sửa hoặc xóa phiên chat đều phải có `X-Visitor-ID` trùng với chủ phiên; quản trị viên có JWT hợp lệ vẫn xem được hội thoại gắn với ticket.
10. Endpoint đăng nhập và tạo phiên/tin nhắn có giới hạn tần suất. Endpoint tạo ticket trực tiếp chỉ dành cho quản trị viên; chatbot nội bộ vẫn tự tạo ticket khi thật sự cần.
11. Giá/thông số cần chính xác lấy catalog, không lấy FAQ giá cũ. Yêu cầu gặp nhân viên và tra trạng thái ticket trong phiên chat được xử lý bằng dữ liệu nghiệp vụ. Index thiếu/cũ dùng nguồn lexical mới; chạy rebuild và khởi động lại backend để dùng semantic.

## Dữ liệu và lưu ý demo

- `backend/seed.py` là dữ liệu khởi tạo website.
- `backend/rag_data/product_verified_specs.json` là lớp hiệu chỉnh thông số có nguồn hãng và ngày đối chiếu; file này cũng được áp dụng khi tạo database mới.
- `backend/PRODUCT_DATA_AUDIT.md` ghi tỷ lệ bao phủ và các sản phẩm còn cần SKU/part number.
- `backend/rag_data/techcare_products.json` và `product_catalog_extended.md` là bản xuất dùng cho chatbot; `faq_curated.json` là 30 FAQ gốc cho demo, không phải dữ liệu đã fine-tune.
- Giá, mô tả và tồn kho trong đề tài là dữ liệu mô phỏng phục vụ nghiên cứu, không phải cam kết bán hàng thực tế.
- Sau khi duyệt thay đổi catalog/knowledge base, chạy trong thư mục `backend`:

```powershell
python export_rag.py
python rebuild_rag.py
```

`sync_verified_products.py` là thao tác cập nhật database, chỉ chạy khi nhóm đã duyệt thay đổi thông số. Các cải tiến không cần chạy script này, không thay `.env` hoặc dữ liệu khách hàng. CSConDa đã được duyệt, lọc và dùng cho pilot; model chính hiện là bản 3B đã train. Thử nghiệm 7B được giữ làm bằng chứng riêng trong báo cáo đánh giá.

Không nhập tự động kết quả Google vào catalog. Google chỉ giúp tìm nguồn; thông số dùng để tư vấn phải được đối chiếu với trang hãng và lưu URL nguồn.

Tài khoản quản trị mặc định phục vụ demo: `admin` / `admin123`. Hãy đổi các biến tương ứng trong `.env` trước khi triển khai thật.

Khi triển khai thật, đặt `ENVIRONMENT=production`, `AUTO_SEED=false`, một `SECRET_KEY` riêng dài tối thiểu 32 ký tự, mật khẩu quản trị dài tối thiểu 12 ký tự và `CORS_ORIGINS` đúng tên miền website. Backend sẽ từ chối khởi động ở chế độ production nếu còn cấu hình demo không an toàn.
