> Bản 3B được giữ trước khi chuyển 7B. Chạy các lệnh dưới đây trong `HT_model3B`; model website vẫn là `techcare-support:3b-v1` đã fine-tune từ trước.

# Chatbot hỗ trợ chăm sóc khách hàng cho website TechCare Electronics

Đề tài xây dựng chatbot trả lời khách hàng dựa trên dữ liệu sản phẩm, FAQ và tài liệu của hệ thống. Dữ liệu giá, sản phẩm, chính sách và hội thoại mẫu phục vụ nghiên cứu; đây là bản demo local, chưa phải hệ thống production.

## Chức năng và công nghệ

- Website sản phẩm, chat widget và trang hỏi đáp; lưu và mở lại lịch sử hội thoại.
- Trả lời bằng luật/catalog/FAQ hoặc RAG kết hợp LLM; tiếp nhận yêu cầu qua ticket và giao diện quản trị FAQ/ticket.
- React/Vite, FastAPI, SQLAlchemy; SQLite mặc định, PostgreSQL tùy chọn.
- Ollama chạy model demo `techcare-support:3b-v1` (Qwen2.5-3B đã fine-tune), embedding `nomic-embed-text`. RAG truy xuất hybrid semantic/BM25 từ chỉ mục JSON. Một số câu được trả lời bằng luật trước khi gọi LLM.

## Cấu trúc

```text
backend/app/           API, nghiệp vụ hội thoại, RAG, quản trị
backend/rag_data/      FAQ, catalog, tài liệu, prompt, profile và chỉ mục
backend/models/        Model 3B, giấy phép, nguồn dữ liệu và mã tái tạo
backend/tests/         Kiểm thử backend
backend/benchmark/     Phương pháp và bộ test nghiên cứu
backend/model_serving/ Serving 7B bổ sung, không cần cho website demo
backend/training/      Mã huấn luyện, dùng môi trường GPU riêng
frontend/              Website React/Vite
docs/                 Hướng dẫn và bằng chứng nghiên cứu
../BaoCao/             Tài liệu báo cáo gốc ở thư mục repository
```

## Cài đặt trên Windows PowerShell

Cần [Python](https://www.python.org/downloads/windows/), [Node.js](https://nodejs.org/), [Git](https://git-scm.com/download/win), [Git LFS](https://git-lfs.com/) và [Ollama](https://ollama.com/download/windows). Môi trường kiểm tra: Python 3.14.3, Node.js 24.14.0, npm 11.9.0, Git LFS 3.6.1, Ollama 0.40.6. Vite yêu cầu Node `^20.19.0 || >=22.12.0`. Chưa kiểm thử trên laptop RTX 3050.

```powershell
git lfs install
git clone --branch chatbotv1-demo https://github.com/nhuquynh112/NCKH_chatbot.git
Set-Location NCKH_chatbot\HT_model3B
git lfs pull
python -m venv backend\.venv
& .\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
```

Mở ứng dụng Ollama trước, sau đó cài model từ GGUF đi kèm và tải embedding:

```powershell
.\install_trained_model.ps1
ollama pull nomic-embed-text
ollama list
```

Installer kiểm tra SHA256 rồi import model local, không huấn luyện. GGUF khoảng 1,93 GB và adapter khoảng 120 MB được quản lý bằng Git LFS. Nếu tải về chỉ có pointer nhỏ, chạy lại `git lfs pull`; nếu lỗi quota/quyền truy cập, liên hệ chủ repo. Không có nguồn tải trọng số thay thế được công bố. Có thể chỉ kiểm tra file bằng `.\install_trained_model.ps1 -VerifyOnly`.

## Chạy demo

Giữ Ollama hoạt động. Terminal thứ nhất, từ gốc project:

```powershell
Set-Location backend
& .\.venv\Scripts\python.exe run.py
```

Không cần tạo `.env` cho demo mặc định. Backend tự tạo `backend/techcare.db`, tạo bảng và nạp sản phẩm/FAQ khi bảng tương ứng trống. Các lần khởi động sau giữ dữ liệu đã có. Database cần cho sản phẩm/FAQ, lịch sử chat, ticket và quản trị; kho tài liệu/chỉ mục RAG nằm riêng trong `rag_data/`. Không tự tải model hoặc rebuild chỉ mục khi khởi động.

Nếu cần tùy chỉnh, sao chép `backend/.env.example` thành `backend/.env` **khi file chưa tồn tại**. Biến môi trường terminal ưu tiên hơn `.env`; kiểm tra cấu hình cũ nếu dùng lại máy phát triển. Không sao chép `.env` cá nhân sang máy khác. [Chi tiết cấu hình và dữ liệu](docs/README.md).

Terminal thứ hai, từ gốc project:

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

| Nội dung | Địa chỉ |
|---|---|
| Website / hỏi đáp | http://127.0.0.1:5173/products / http://127.0.0.1:5173/faqs |
| Quản trị | http://127.0.0.1:5173/admin/login |
| API docs | http://127.0.0.1:8000/docs |
| Health / readiness | http://127.0.0.1:8000/health / http://127.0.0.1:8000/ready |

Tài khoản `admin / admin123` chỉ dành cho demo local. `/ready` cần có `chat_model: techcare-support:3b-v1`, `ai: ok`; HTTP 200 với `status: degraded` chưa phải AI sẵn sàng. Endpoint này chưa kiểm tra embedding/index; cần thử thêm câu RAG, không chỉ câu FAQ.

### Lỗi thường gặp

- PowerShell chặn script: dùng `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install_trained_model.ps1` từ gốc project.
- Model chưa sẵn sàng: kiểm tra Ollama, `ollama list`, installer và `/ready`. Câu đầu có thể chậm khi nạp model.
- Không kết nối API: kiểm tra backend cổng 8000; frontend mặc định gọi `http://localhost:8000/api`. Khi đổi địa chỉ/cổng, đặt `VITE_API_BASE_URL` và `CORS_ORIGINS` tương ứng.
- Thiếu/cũ chỉ mục sau khi duyệt thay đổi tài liệu: từ `backend` chạy `& .\.venv\Scripts\python.exe rebuild_rag.py` khi Ollama/embedding đang chạy, rồi khởi động lại backend. Không cần làm bước này mỗi lần chạy.

## Phạm vi và tài liệu thêm

Corpus kỹ thuật còn thiếu; chatbot có thể báo thiếu thông tin và tạo ticket. Chất lượng và tốc độ phụ thuộc tài liệu, CPU/GPU, VRAM và độ dài hội thoại. Không cam kết hiệu năng trên máy chưa thử.

`npm ci` hiện có cảnh báo bảo mật trong chuỗi dependency Tailwind phục vụ build. Chưa nâng Tailwind major trong bản demo này; cần rà soát trước khi triển khai công khai.

- [Cấu hình, cập nhật dữ liệu, kiểm thử và đổi model](docs/README.md).
- [Tái lập nghiên cứu](docs/REPRODUCING_RESEARCH.md): B0/B1/B2/P dùng base 3B; P+FT 7B là thử nghiệm bổ sung, không phải model website. Điểm AI sơ bộ cần nhóm duyệt.
- [Demo bốn phương pháp](docs/LOCAL_BENCHMARK_DEMO.md): cần snapshot study và source hash phù hợp; bản clone không đủ để mở lại phiên benchmark cũ.
- [Model 3B và nguồn](backend/models/techcare-support-3b-v1/README.md), [thông báo giấy phép](docs/THIRD_PARTY_NOTICES.md). Giữ nguyên giấy phép model/dataset; nhóm chưa gán giấy phép chung cho toàn bộ mã nguồn.

Không đưa `.env`, database phát sinh, log hoặc thông tin khách hàng lên Git. Cấu hình production có kiểm tra secret, mật khẩu admin và CORS riêng; không dùng tài khoản demo để triển khai công khai.
