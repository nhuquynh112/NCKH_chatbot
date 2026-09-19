# TechCare Electronics — chatbot chăm sóc khách hàng

Ứng dụng demo gồm website bán thiết bị công nghệ, chatbox AI/RAG, lưu lịch sử hội thoại, tự tạo ticket khi không đủ dữ liệu và trang quản trị FAQ/ticket.

## Yêu cầu

- Python 3.11 trở lên
- Node.js 20 trở lên
- [Ollama](https://ollama.com/) với hai model `qwen2.5:3b` và `nomic-embed-text`

## Chạy nhanh trên Windows

Mở terminal thứ nhất:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
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

Script sẽ chạy unit test backend, một bộ đánh giá chatbot tổng hợp, kiểm tra API/tải đồng thời, frontend lint và production build. Hoặc chạy thủ công:

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe evaluate_chatbot.py

cd ..\frontend
npm run lint
npm run build
```

`evaluate_chatbot.py` là file đánh giá duy nhất. Nó kiểm tra toàn bộ 53 sản phẩm, giá và bảo hành, câu có dấu/không dấu/sai chính tả, nhiều cách ghi ngân sách, tư vấn nhiều lượt, sản phẩm ngoài catalog, câu ngoài phạm vi, Việt–Anh, prompt-injection, giới hạn đầu vào, quyền riêng tư phiên chat và 16 yêu cầu API đồng thời. Kết quả duy nhất nằm tại `backend/EVALUATION_REPORT.md`.

Đây là kiểm thử hồi quy trên dữ liệu TechCare, không phải cam kết rằng chatbot đúng 100% với mọi câu ngoài đời. Muốn dùng cho khách thật, quản trị viên phải cập nhật giá, sản phẩm active, thông số và chính sách trong database/FAQ; chatbot sẽ từ chối suy đoán trường dữ liệu chưa có.

## Kiến trúc trả lời

1. Lớp luật xử lý các dữ kiện cần chính xác tuyệt đối: giá, bảo hành, so sánh, ngân sách, tra cứu đơn và sự cố kỹ thuật.
   Danh mục sản phẩm đang hoạt động được đọc trực tiếp từ bảng `products`; file JSON chỉ là dữ liệu dự phòng khi database chưa sẵn sàng.
2. Retriever tìm ngữ cảnh trong Knowledge Base và catalog đồng bộ từ website.
3. Ollama diễn đạt câu trả lời dựa trên ngữ cảnh; không có dữ liệu thì fallback và tạo ticket.
4. Chỉ mục JSON là mặc định để demo chạy ổn định. Có thể cài `requirements-chroma.txt` và đặt `VECTOR_STORE_BACKEND=chroma` để dùng ChromaDB.
5. Với model không có trong catalog, chatbot không đoán giá hoặc tồn kho mà tạo link tìm kiếm Google và Google Shopping theo tên sản phẩm. Giao diện tự hiển thị các URL này thành liên kết mở ở tab mới và kèm cảnh báo TechCare không xác minh nguồn bán bên ngoài.
6. Tin nhắn có số điện thoại được che bớt trong lịch sử. Mật khẩu, OTP, CVV/CVC và số thẻ bị thay bằng nhãn đã ẩn, không được chuyển vào RAG hay tự động tạo ticket.
7. Các yêu cầu tiết lộ prompt hệ thống, khóa truy cập hoặc bỏ qua quy tắc an toàn được chặn ở lớp luật trước khi gọi mô hình.
8. Lời gọi AI có thời gian chờ tối đa; nếu Ollama treo hoặc mất kết nối, hệ thống trả lời an toàn và chuyển ticket thay vì để giao diện chờ vô hạn. Endpoint `/ready` cho biết riêng trạng thái database và Ollama.
9. Mọi thao tác đọc, gửi, sửa hoặc xóa phiên chat đều phải có `X-Visitor-ID` trùng với chủ phiên; quản trị viên có JWT hợp lệ vẫn xem được hội thoại gắn với ticket.
10. Endpoint đăng nhập và tạo phiên/tin nhắn có giới hạn tần suất. Endpoint tạo ticket trực tiếp chỉ dành cho quản trị viên; chatbot nội bộ vẫn tự tạo ticket khi thật sự cần.

## Dữ liệu và lưu ý demo

- `backend/seed.py` là dữ liệu khởi tạo website.
- `backend/rag_data/product_verified_specs.json` là lớp hiệu chỉnh thông số có nguồn hãng và ngày đối chiếu; file này cũng được áp dụng khi tạo database mới.
- `backend/PRODUCT_DATA_AUDIT.md` ghi tỷ lệ bao phủ và các sản phẩm còn cần SKU/part number.
- `backend/rag_data/techcare_products.json` và `product_catalog_extended.md` là bản xuất dùng cho chatbot.
- Giá, mô tả và tồn kho trong đề tài là dữ liệu mô phỏng phục vụ nghiên cứu, không phải cam kết bán hàng thực tế.
- Sau khi duyệt thay đổi catalog/knowledge base, chạy trong thư mục `backend`:

```powershell
python sync_verified_products.py
python export_rag.py
python rebuild_rag.py
```

Không nhập tự động kết quả Google vào catalog. Google chỉ giúp tìm nguồn; thông số dùng để tư vấn phải được đối chiếu với trang hãng và lưu URL nguồn.

Tài khoản quản trị mặc định phục vụ demo: `admin` / `admin123`. Hãy đổi các biến tương ứng trong `.env` trước khi triển khai thật.

Khi triển khai thật, đặt `ENVIRONMENT=production`, `AUTO_SEED=false`, một `SECRET_KEY` riêng dài tối thiểu 32 ký tự, mật khẩu quản trị dài tối thiểu 12 ký tự và `CORS_ORIGINS` đúng tên miền website. Backend sẽ từ chối khởi động ở chế độ production nếu còn cấu hình demo không an toàn.
