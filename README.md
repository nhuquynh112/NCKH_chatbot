# Chatbot hỗ trợ chăm sóc khách hàng cho website TechCare Electronics

Bản hiện tại nằm trong **`HT_model7B`**, sử dụng **Qwen2.5-7B-Instruct FP16 gốc** qua Ollama (`qwen2.5:7b-instruct-fp16`), **không fine-tune và không nạp adapter**. Embedding dùng `nomic-embed-text`.

Hệ thống hỗ trợ hỏi đáp sản phẩm, giá, bảo hành và chính sách bằng luật nghiệp vụ, catalog/FAQ hoặc RAG kết hợp LLM. Website có danh mục sản phẩm, lịch sử hội thoại, ticket hỗ trợ và trang quản trị. Cập nhật sản phẩm là cập nhật dữ liệu và chỉ mục RAG, không phải huấn luyện lại LLM.

## Cấu trúc chính

| Thư mục | Nội dung |
|---|---|
| `HT_model7B/backend` | FastAPI, SQLite, chatbot/RAG và bộ so sánh bốn phương pháp |
| `HT_model7B/backend/rag_data_150` | Catalog 151 sản phẩm, FAQ, nguồn và chỉ mục RAG hiện tại |
| `HT_model7B/frontend` | React/Vite, giao diện website và ảnh sản phẩm |
| `HT_model7B/docs` | Hướng dẫn chạy, test và tái lập nghiên cứu |
| `HT_model3B` | Bản lưu lịch sử, có cấu hình/model riêng; không phải bản chạy hiện tại |
| `BaoCao` | Tài liệu báo cáo của nhóm |

## Chuẩn bị một lần

Cần Git/Git LFS, Python, Node.js và Ollama. Môi trường đã kiểm tra: Python 3.14.3, Node.js 24.14.0; Vite yêu cầu Node `^20.19.0 || >=22.12.0`.

```powershell
git lfs install
git clone --branch chatbotv1-demo https://github.com/nhuquynh112/NCKH_chatbot.git
Set-Location NCKH_chatbot
python -m venv HT_model7B\backend\.venv
& .\HT_model7B\backend\.venv\Scripts\python.exe -m pip install -r .\HT_model7B\backend\requirements.txt
Set-Location HT_model7B\frontend
npm.cmd ci
Set-Location ..\..
ollama pull qwen2.5:7b-instruct-fp16
ollama pull nomic-embed-text
```

Model 7B FP16 khoảng 15,24 GB được Ollama quản lý ngoài Git. Git LFS trong repository phục vụ trọng số của bản lưu 3B. Không cần cài Transformers/PEFT hoặc tải checkpoint thử nghiệm để chạy bản 7B.

## Chạy website bình thường

Sau khi đã cài thư viện, giữ Ollama hoạt động. Terminal backend tại gốc repository:

```powershell
Set-Location HT_model7B\backend
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal frontend mới tại gốc repository:

```powershell
Set-Location HT_model7B\frontend
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Mở [website](http://127.0.0.1:5173/products), [hội thoại](http://127.0.0.1:5173/faqs), [API docs](http://127.0.0.1:8000/docs) và [readiness](http://127.0.0.1:8000/ready). `/ready` cần báo `status: ready`, `ai: ok`, `chat_model: qwen2.5:7b-instruct-fp16`.

Backend tự tạo SQLite `HT_model7B/backend/techcare.db`, bảng và dữ liệu mẫu khi trống; không cần tạo database thủ công hoặc khai báo đường dẫn trên máy tác giả. Không cần `.env` cho cấu hình mặc định; nếu tùy chỉnh thì dùng `backend/.env.example`. Giữ database, `.env` và lịch sử phát sinh ngoài Git.

## Chạy web test B0/B1/B2/P

Backend tại `HT_model7B/backend`:

```powershell
& .\.venv\Scripts\python.exe comparison_demo.py --work-dir D:\TechCareTest
```

Frontend tại `HT_model7B/frontend`:

```powershell
npm.cmd run test:methods
```

Mở [web test](http://127.0.0.1:5174/benchmark-demo). Chọn B0, B1, B2 hoặc P, nhập cùng câu hỏi/lịch sử rồi xuất CSV để nhóm chấm. B0 dùng luật; B1 dùng 7B không RAG; B2 dùng RAG cơ bản; P dùng pipeline đề xuất với cùng 7B gốc. P+FT không thuộc bốn phương pháp chính.

Kết quả test được lưu riêng ngoài repository và ngoài lịch sử khách hàng. Hai người có thể chạy trên hai máy với cùng commit, corpus, model và bộ câu hỏi/lịch sử. Không cập nhật code hoặc đổi dữ liệu giữa một lượt chấm. Các bản sửa giao tiếp của website bình thường được tách khỏi pipeline P benchmark; không coi hai luồng là cùng một cấu hình. Xem [hướng dẫn test đầy đủ](HT_model7B/docs/TEST_4_PHUONG_PHAP.md).

## Dữ liệu và giới hạn

Catalog hiện tại có 151 sản phẩm và 300 tài liệu trong chỉ mục, lấy nguồn tham khảo từ các link CellphoneS do nhóm chọn, thu thập ngày 23/10/2026. Giá là snapshot phục vụ demo; dữ kiện do nhà bán lẻ công bố chưa được đối chiếu toàn bộ với hãng. Chính sách TechCare và các luồng nghiệp vụ là dữ liệu nghiên cứu. Kho `rag_data` và kết quả cũ được giữ riêng, không dùng để tuyên bố kết quả của catalog mới.

Để chạy lại bản 3B, dùng đường dẫn `HT_model3B` tương ứng và đọc [hướng dẫn 3B](HT_model3B/README.md). Trọng số 3B cũ vẫn được Git LFS quản lý. Cấu hình/lịch sử cá nhân có sẵn được giữ cùng bản 3B và bị Git bỏ qua; không sao chép `.env` đó sang bản 7B.

Nếu kết nối lỗi, kiểm tra Ollama/model đã sẵn sàng và các cổng 8000/5173 (website) hoặc 8012/5174 (test). Khi sửa code backend cần dừng và mở lại tiến trình Uvicorn. Corpus kỹ thuật và thuật toán tư vấn còn giới hạn; đổi model không tự sửa các luật sai. FP16 có thể dùng cả CPU/RAM khi thiếu VRAM; chưa kiểm thử laptop RTX 3050 và chưa phải hệ thống production.

[Hướng dẫn 7B và cập nhật catalog](HT_model7B/README.md) · [Giấy phép và nguồn bên thứ ba](HT_model7B/docs/THIRD_PARTY_NOTICES.md).
