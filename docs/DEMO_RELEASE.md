# Bản demo báo cáo nhóm – 20/10/2026

Mục tiêu của bản này là quay video, chia sẻ GitHub với giảng viên và nhận góp ý. Dữ liệu sản phẩm/chính sách là mô phỏng nghiên cứu. Không coi bản demo là hệ thống production hoặc công bố độ chính xác trên khách hàng thật.

## Thành phần được đóng gói

- `backend/`: FastAPI, nghiệp vụ hội thoại/FAQ/ticket, RAG, test, mã benchmark và serving bổ sung.
- `frontend/`: React/Vite, trang sản phẩm, chat widget, quản trị và giao diện nghiên cứu local.
- `docs/`: hướng dẫn và bằng chứng; sáu báo cáo lịch sử giữ trong `docs/history/`; bộ kết quả nghiên cứu giữ trong `docs/research/`.
- `backend/models/techcare-support-3b-v1/`: GGUF và adapter thật qua Git LFS, model card, giấy phép, provenance và dữ liệu đã có.
- Script cấp gốc: `install_trained_model.ps1`, `run_tests.ps1`, `docker-compose.yml`.
- `BaoCao/` giữ các Word đã theo dõi từ trước. File Word đang sửa trên máy tác giả không được đưa vào commit release.

Cache, `.env`, database, log, virtual environment, `node_modules`, `.local/` và các file thử bị Git bỏ qua. File template React/Vite không dùng và báo cáo rỗng đã được loại khỏi cây Git; không di chuyển module được import. Không xóa dữ liệu người dùng.

Website dùng `techcare-support:3b-v1`, embedding `nomic-embed-text`, index 195 đoạn. Câu hỏi nghiệp vụ có thể trả bằng rule/catalog/FAQ; câu kỹ thuật chung chỉ đưa bằng chứng phù hợp vào LLM. Thiếu tài liệu thì fallback/ticket. Không train lại, đổi model hoặc sửa thuật toán B0/B1/B2/P/P+FT trong lượt chốt này.

## Kiểm tra release

Kiểm tra cuối bằng `run_tests.ps1`, log ở `D:\NCKH\Codex\final_demo_release_20261020_4d2c9a\tests-20261020T134441Z-536c5525`, ngoài repo:

| Kiểm tra | Kết quả |
|---|---|
| Backend unit/integration | 163/163 |
| Hồi quy hội thoại/catalog | 225/225 |
| API / concurrent | 5/5 / 16/16 |
| FAQ online / offline | 32/32 / 32/32; `generative_cases=0` |
| Frontend lint / build | Đạt / đạt |
| Smoke HTTP thật | Frontend/API docs/products/readiness/CORS đạt; 4 lượt giá, lịch sử, LLM+RAG thật và fallback/ticket đạt |
| Model/LFS | `techcare-support:3b-v1`; GGUF đúng kích thước/SHA256; LFS fsck đạt, GGUF và adapter vẫn có filter LFS |
| README | 40 link nội bộ tồn tại, 5 URL tải phần mềm trả HTTP 200; 8 khối PowerShell không lỗi cú pháp |

Smoke lưu nguyên phản hồi tại `smoke_http_verified.json` trong thư mục log trên; không đưa vào các bảng benchmark lịch sử. Đây là smoke HTTP và kiểm tra build, chưa thay thế chạy thử mọi thao tác bằng trình duyệt.

Lượt unit đầu gặp lỗi đóng kết nối của HTTP fixture 7B trên Windows. Chỉ sửa fixture đọc hết POST body và chờ thread kết thúc; không sửa thuật toán/client 7B để vượt test. Lượt smoke đầu dùng nhầm `/api/products/`; router/frontend thực tế dùng `/api/products`, harness đã được chỉnh đúng và chạy lại. Giữ riêng log các lượt đầu, không che lỗi hoặc ghi đè kết quả cũ.

Artifact nghiên cứu giữ nguyên byte, gồm CRLF và khoảng trắng trong ô CSV nhiều dòng. `.gitattributes` chấp nhận CRLF gốc và không kiểm tra style whitespace cho CSV snapshot; không format lại dữ liệu để làm sạch diff. Hash bản staged được đối chiếu với manifest nguồn. Mã nguồn và tài liệu khác vẫn kiểm tra whitespace bình thường.

## Quay video trên máy hiện tại

Các lệnh này dùng Python đã được kiểm thử trên máy tác giả và SQLite demo riêng ngoài repo. Không sửa `backend/.env` đang trỏ tới database khác. Khởi động Ollama; nếu backend/frontend đang chạy đúng các cổng dưới đây thì dùng phiên đang chạy, không khởi động trùng cổng.

Terminal PowerShell 1:

```powershell
Set-Location 'D:\NCKH\2026_Chatbot\Code\NCKH_chatbot\backend'
$env:DATABASE_URL='sqlite:///D:/NCKH/Codex/final_demo_release_20261020_4d2c9a/video_demo.db'
$env:ENVIRONMENT='development'
$env:AUTO_SEED='true'
$env:CHAT_PROVIDER='ollama'
$env:CHAT_MODEL='qwen2.5:3b'
$env:USE_PROJECT_CHAT_MODEL='true'
$env:OLLAMA_BASE_URL='http://localhost:11434'
$env:WARM_AI_ON_STARTUP='true'
$env:CORS_ORIGINS='http://127.0.0.1:5173,http://localhost:5173'
$env:PYTHONDONTWRITEBYTECODE='1'
& 'C:\Python314\python.exe' -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

App chỉ seed khi bảng demo tương ứng còn trống. Không rebuild index hoặc import lại model để quay mỗi video. Model mặc định vẫn do profile chọn; biến `CHAT_MODEL` ở trên là base tag để profile ánh xạ sang `techcare-support:3b-v1`.

Terminal PowerShell 2:

```powershell
Set-Location 'D:\NCKH\2026_Chatbot\Code\NCKH_chatbot\frontend'
$env:VITE_API_BASE_URL='http://127.0.0.1:8000/api'
$env:VITE_BENCHMARK_DEMO='false'
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Mở `http://127.0.0.1:5173/products`, API docs `http://127.0.0.1:8000/docs`, readiness `http://127.0.0.1:8000/ready`. JSON readiness phải báo đúng model; nó không tự kiểm tra khả năng sinh token. Có thể dùng cửa sổ ẩn danh để có phiên quay mới mà không xóa lịch sử trình duyệt cũ.

Gợi ý quay bốn bước trên chat widget hoặc trang `/faqs`:

1. Hỏi `Sạc Anker Nano 65W giá bao nhiêu?` rồi `Mẫu đó bảo hành bao lâu?` để minh họa giá và lịch sử sản phẩm.
2. Tạo đoạn chat mới, hỏi `Trong tài liệu, laptop đồ họa có những đặc điểm kỹ thuật nào?` để minh họa LLM + RAG thật.
3. Tạo đoạn chat mới, hỏi `RAM dual-channel nghĩa là gì?` để minh họa thiếu bằng chứng và chuyển hỗ trợ, không trả lời nhầm Pixel.
4. Mở quản trị local nếu cần minh họa ticket/FAQ; không quay mật khẩu, thông tin liên hệ cá nhân hoặc nội dung `.env`.

Dừng mỗi terminal bằng Ctrl+C sau khi quay. Máy mới dùng hướng dẫn clone/LFS/venv trong [README](../README.md); đường dẫn Python/ổ D ở trên chỉ dành cho máy tác giả.

## Giới hạn đã công bố

- Corpus chưa có định nghĩa dual-channel/NVMe/OLED đủ để giải thích; bản này giữ fallback an toàn, không bổ sung câu trả lời mẫu để vượt test.
- Chỉ có số đo trên desktop RTX 3060 12 GB; chưa thử laptop RTX 3050 và chưa kiểm tra full cold-start ở mọi môi trường. Cần chờ model nạp trước khi quay.
- [Báo cáo RAG](LLM_RAG_INVESTIGATION_20261020.md) có các ca API/model thật; các bộ test luật/FAQ không phải benchmark chất lượng sinh tổng quát.
- Study benchmark 16/10 khóa source hash. Sau bản vá website, study cũ phải chạy bằng runtime snapshot gốc ngoài repo, hoặc tạo study mới và lưu kết quả riêng. Không đổi hash để chạy lẫn hoặc đưa kết quả website vào bảng P cũ. Clone không chứa toàn bộ database snapshot cũ; xem [hướng dẫn benchmark demo](LOCAL_BENCHMARK_DEMO.md).
- P+FT 7B là bổ sung và không cần cho website; trọng số gốc 7B vẫn ở ngoài repo.
- Các cảnh báo dependency công cụ build và cảnh báo thư viện test có thể còn; không tự nâng major framework sát buổi báo cáo. Không mở dev server ra Internet.
- Tải LFS lần đầu cần mạng và dung lượng/quota GitHub phù hợp. Kiểm tra cài model sạch ở máy khác và Docker runtime chưa hoàn tất trong bản demo này.

Các báo cáo điều tra/đóng gói trước đó giữ nguyên nhận định theo phạm vi lúc viết. Quyết định chốt demo hiện tại dựa trên yêu cầu quay video của nhóm, không nâng trạng thái thành production-ready.
