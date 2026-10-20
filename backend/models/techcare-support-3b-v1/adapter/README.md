---
base_model: unsloth/Qwen2.5-3B-Instruct-bnb-4bit
library_name: peft
pipeline_tag: text-generation
tags:
- lora
- transformers
---

# TechCare support 3B — adapter nghiên cứu

Built with Qwen. Adapter QLoRA của `techcare-support:3b-v1`, mục tiêu tiếng Việt. Giữ nguyên trọng số đã xác nhận; website gọi GGUF hoàn chỉnh qua Ollama, không nạp adapter trực tiếp.

- Base: `unsloth/Qwen2.5-3B-Instruct-bnb-4bit`, revision `2672b588848527e456d320c11926c794539f47d5`.
- LoRA rank 16, all-linear; 2 epoch, learning rate 1e-4, sequence 512.
- Dữ liệu: 170 train, 9 validation; CSConDa được duyệt/lọc và ví dụ tổng hợp, giữ nhãn nguồn/chỉnh sửa.
- Trọng số: [Qwen Research License](../LICENSE). Dữ liệu có [thông báo riêng](../data/LICENSE).
- Metadata base dùng repo/revision nguồn để portable, không thay trọng số.

Đọc [model card đầy đủ](../README.md), `../evidence/run.json`, `../evidence/checkpoint_manifest.json` và mã `backend/training` trước khi tái tạo. Môi trường GPU tách khỏi FastAPI; dùng GGUF không cần PEFT/Transformers.

Kết quả synthetic không chứng minh độ chính xác khách thật. Model có thể lặp prompt hoặc suy đoán; giá/bảo hành phải lấy từ catalog/FAQ/RAG và kiểm tra tại tầng ứng dụng. Không dùng nội dung model làm chính sách cửa hàng thật.