# Audit và kế hoạch tích hợp 7B / benchmark

Ngày kiểm tra: 15/10/2026. Nhánh hiện tại: `chatbot-v1`.

## Trạng thái trước sửa

- Working tree có thay đổi của người dùng ở `BaoCao/BaoCao_Chatbox.docx` và file khóa Word `BaoCao/~$oCao_Chatbox.docx`. Không sửa hai tệp này.
- Frontend gọi `/api/chat/*` qua axios; router kiểm tra visitor rồi gọi business ChatService, AIService, RAG ChatService và OllamaClient.
- RAG đọc KB, catalog và FAQ; JSON index gồm 195 đoạn. Product/FAQ database là dữ liệu nghiệp vụ. Profile mặc định chọn 3B đã train.
- 7B ở ngoài repo: `D:/NCKH/Codex/training_runs/csconda_7b_epoch1_20261014`. Checkpoint NF4 ở `D:/NCKH/Codex/training_cache/qwen25_7b_nf4`.
- Runtime GPU có Python 3.14, torch 2.14.1+cu126, Transformers 5.19.0, PEFT 0.21.2, bitsandbytes 0.50.2, RTX 3060 12 GiB. Kiểm tra ban đầu trong sandbox bị chặn localhost; kiểm tra ngoài sandbox xác nhận Ollama đang hoạt động và có đủ model 3B nền, 3B đã train, 7B nền, embedding. Không coi lỗi sandbox là bằng chứng dịch vụ đã dừng.
- Adapter GGUF từng bị Ollama từ chối. Dùng dịch vụ Transformers/PEFT riêng nạp checkpoint và adapter gốc; không cần merge, tải weights hoặc cài thêm runtime.

## Phạm vi dự kiến

| Nhóm | Tệp/thư mục | Lý do |
|---|---|---|
| Sửa tối thiểu | `backend/app/config.py`, `backend/app/main.py`, `backend/app/rag/chat_service.py`, `backend/app/services/ai_service.py` | Chọn provider bằng cấu hình, readiness và báo lỗi rõ cho 7B |
| Thêm | `backend/app/model_client.py` | Kết nối HTTP tới adapter server, giữ embedding qua Ollama |
| Thêm | `backend/model_serving/` | Profile có provenance, server nạp adapter trực tiếp, hướng dẫn runtime |
| Thêm | `backend/benchmark/` | M1–M4, schema, dataset đánh giá, runner, scoring khách quan và review thủ công |
| Thêm | `backend/tests/test_model_serving.py`, `backend/tests/test_benchmark.py` | Kiểm tra model/pipeline, lỗi và tính độc lập M2 |
| Thêm/cập nhật | `docs/`, `README.md`, `backend/.env.example`, `.gitignore` | Hướng dẫn, audit, trạng thái xác minh và bỏ qua output cục bộ |
| Giữ nguyên vị trí | `backend/app`, `frontend`, `backend/rag_data`, `backend/training`, `backend/models`, tài liệu cũ | Tránh phá import và đường dẫn; bảo tồn bằng chứng nghiên cứu |
| Không di chuyển | Mọi tệp hiện có | Cấu trúc hiện tại đã phân tách ứng dụng; bổ sung thư mục là đủ |

## Trình tự

1. Thêm provider/server và kiểm tra đơn vị; giữ API contract.
2. Thêm benchmark tách dataset huấn luyện, RAG và đánh giá. M2/M3 khóa model gốc `qwen2.5:3b`; M4 kiểm tra identity và readiness, không fallback model.
3. Chạy hồi quy trên database thử riêng, lint/build frontend, kiểm tra model thật và API. Không suy ra frontend đã dùng được từ build.
4. Ghi kết quả PASS/FAIL/BLOCKED cùng đường dẫn log, giới hạn phép đo và hướng dẫn kiểm tra thủ công.

Kết quả mới nằm trong `.local/` (Git bỏ qua), mỗi lần chạy có thư mục riêng. Không commit/push/đổi nhánh, không sửa artifact gốc, `.env`, database thật hoặc báo cáo Word.
