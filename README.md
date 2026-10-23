# TechCare Chatbot — hai phiên bản model

Repository chứa hai bản hệ thống tách riêng để chạy và so sánh:

| Thư mục | Model website mặc định | Vai trò |
|---|---|---|
| [HT_model3B](HT_model3B/README.md) | `techcare-support:3b-v1` đã fine-tune từ trước | Giữ hệ thống 3B trước khi chuyển; benchmark lịch sử B1/B2/P dùng `qwen2.5:3b` gốc |
| [HT_model7B](HT_model7B/README.md) | `qwen2.5:7b-instruct-fp16` gốc qua Ollama | Bản mới, trọng số FP16; B1/B2/P cùng dùng 7B, không fine-tune |
| BaoCao | — | Báo cáo Word gốc, không thuộc code ứng dụng |

Mỗi bản có `backend/`, `frontend/`, `docs/` và script kiểm thử riêng. Bản 7B hiện dùng catalog 151 sản phẩm trong `backend/rag_data_150/`, gồm ảnh và nguồn CellphoneS; `rag_data/` và kết quả nghiên cứu cũ được giữ nguyên. Không trộn kết quả giữa hai corpus. Chỉ chạy một bản mỗi lần với cổng mặc định 8000/5173.

## Lấy source

```powershell
git lfs install
git clone --branch chatbotv1-demo https://github.com/nhuquynh112/NCKH_chatbot.git
Set-Location NCKH_chatbot
```

Git LFS dùng cho trọng số 3B được lưu trữ. Model 7B FP16 khoảng 15 GB tải riêng bằng Ollama theo hướng dẫn dưới đây. FP16 vượt VRAM 12 GB nếu nạp toàn bộ lên GPU; Ollama có thể chia tải sang RAM và chạy chậm hơn bản Q4. Chưa kiểm thử laptop RTX 3050.

## Chạy bản 7B

Để nhóm **test 50 câu trên web lần lượt B0/B1/B2/P**, dùng [hướng dẫn bốn phương pháp](HT_model7B/docs/TEST_4_PHUONG_PHAP.md). Chế độ chạy độc lập trên 8012/5174, có câu hỏi tự nhập, lưu kết quả và xuất CSV; không cần snapshot riêng của máy tác giả. Hai người có thể chạy trên hai máy với cùng phiên bản code, corpus và bộ câu hỏi/lịch sử; mỗi máy lưu kết quả riêng.

Cần Python, Node.js và Ollama. Cài dependencies theo [README 7B](HT_model7B/README.md); model 7B nằm trong kho Ollama, không được chép trọng số vào Git:

```powershell
ollama pull qwen2.5:7b-instruct-fp16
ollama pull nomic-embed-text
```

Sau khi đã cài thư viện, giữ Ollama hoạt động. Terminal backend tại gốc repository:

```powershell
Set-Location HT_model7B\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal frontend mới tại gốc repository:

```powershell
Set-Location HT_model7B\frontend
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Mở http://127.0.0.1:5173/products, API docs http://127.0.0.1:8000/docs và readiness http://127.0.0.1:8000/ready. Bản 7B dùng SQLite riêng tại `HT_model7B/backend/techcare.db`, tự tạo bảng và dữ liệu demo khi trống; không cần `.env`.

Để chạy lại bản 3B, dùng đường dẫn `HT_model3B` tương ứng và đọc [hướng dẫn 3B](HT_model3B/README.md). Trọng số 3B cũ vẫn được Git LFS quản lý. Cấu hình/lịch sử cá nhân có sẵn được giữ cùng bản 3B và bị Git bỏ qua; không sao chép `.env` đó sang bản 7B.

Dữ liệu sản phẩm/chính sách là mô phỏng nghiên cứu. Hiệu năng phụ thuộc phần cứng; chưa kiểm thử trên laptop RTX 3050. Bản 7B vẫn giữ các luật nghiệp vụ hiện có, nên đổi model không tự sửa các lỗi lọc hãng hoặc nguồn tham khảo trong luật.
