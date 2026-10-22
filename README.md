# TechCare Chatbot — benchmark B0/B1/B2/P và P+FT

Nhánh `benmark-chatbot` dùng **`HT_model7B` làm hệ thống nghiên cứu chính**. Bốn phương pháp chính là B0/B1/B2/P; **P không fine-tune**. P+FT là nhánh fine-tune 7B bổ sung, không gộp vào bốn phương pháp chính. Xem [bảng phương pháp, dữ liệu và cách chạy P+FT](HT_model7B/docs/BENCHMARK_METHODS.md).

| Phương pháp | Cách trả lời | Fine-tune thêm bởi nhóm |
|---|---|---|
| B0 | Luật/catalog/FAQ, không LLM | Không |
| B1 | Qwen2.5-7B-Instruct FP16 gốc, không RAG | Không |
| B2 | Cùng model gốc + RAG cơ bản | Không |
| P | Cùng model gốc + pipeline RAG nhóm đề xuất | Không |
| P+FT (bổ sung) | Pipeline P + adapter QLoRA 7B, NF4/BF16 | 37 train, 9 validation, 1 epoch |

Đổi model nền từ 3B gốc sang 7B gốc không phải huấn luyện. Corpus RAG và bộ test không phải tập train. Số **170 mẫu train** thuộc model demo 3B cũ, không phải P hoặc P+FT 7B.

Các thư mục trong repository:

| Thư mục | Model website mặc định | Vai trò |
|---|---|---|
| [HT_model7B](HT_model7B/README.md) | `qwen2.5:7b-instruct-fp16` gốc qua Ollama | Bản chính; bốn phương pháp và P+FT bổ sung có adapter riêng |
| [HT_model3B](HT_model3B/README.md) | `techcare-support:3b-v1` đã fine-tune từ trước | Lưu trữ demo cũ, không dùng làm P hoặc làm model nền cho benchmark mới |
| BaoCao | — | Báo cáo Word gốc, không thuộc code ứng dụng |

Mỗi bản có `backend/`, `frontend/`, `docs/` và script kiểm thử riêng. Dữ liệu/prompt/cấu hình truy xuất của phép so sánh được giữ nguyên; kết quả 3B đã lưu không phải kết quả 7B. Chỉ chạy một bản mỗi lần với cổng mặc định 8000/5173.

## Lấy source

```powershell
git lfs install
$env:GIT_LFS_SKIP_SMUDGE='1'
git clone --branch benmark-chatbot https://github.com/nhuquynh112/NCKH_chatbot.git
Remove-Item Env:GIT_LFS_SKIP_SMUDGE
Set-Location NCKH_chatbot
```

Clone này bỏ qua tải trọng số LFS để chạy bốn phương pháp chính bằng model Ollama tải riêng. Adapter P+FT gốc khoảng 10 MB được đóng gói qua Git LFS; tải khi cần bằng lệnh trong [hướng dẫn P+FT](HT_model7B/docs/BENCHMARK_METHODS.md). Trọng số 3B cũ chỉ cần khi tái lập demo cũ.

Model 7B FP16 khoảng 15 GB tải riêng bằng Ollama theo hướng dẫn dưới đây. FP16 vượt VRAM 12 GB nếu nạp toàn bộ lên GPU; Ollama có thể chia tải sang RAM và chạy chậm hơn bản Q4. Chưa kiểm thử laptop RTX 3050.

## Chạy bản 7B

Để nhóm **test 50 câu trên web lần lượt B0/B1/B2/P**, dùng [hướng dẫn bốn phương pháp](HT_model7B/docs/TEST_4_PHUONG_PHAP.md). Chế độ chạy độc lập trên 8012/5174, có câu hỏi tự nhập, lưu kết quả và xuất CSV; không cần snapshot riêng của máy tác giả.

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
