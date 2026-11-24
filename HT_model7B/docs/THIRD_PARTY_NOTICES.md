# Nguồn và giấy phép — hệ thống 7B

- Model website là [Qwen2.5-7B trên Ollama](https://ollama.com/library/qwen2.5:7b-instruct-fp16), trọng số gốc không gắn adapter của nhóm. Giữ [Apache 2.0](../backend/models/qwen2.5-7b/LICENSE) và [manifest model](../backend/models/qwen2.5-7b/model_manifest.json).
- Dữ liệu sản phẩm, giá và chính sách TechCare là mô phỏng nghiên cứu. `product_verified_specs.json` giữ mức đối chiếu và URL hãng; không coi đó là tồn kho/bảng giá thời gian thực.
- Ảnh sản phẩm và thư viện giữ nguồn/giấy phép của nhà cung cấp tương ứng. Repository không tự cấp quyền sở hữu ảnh bên thứ ba.
- Hồ sơ benchmark 3B/P+FT đã lưu là bằng chứng lịch sử, không phải kết quả 7B mới. Model 3B, dữ liệu train đã chọn và giấy phép tương ứng được giữ trong [hệ thống 3B](../../HT_model3B/backend/models/techcare-support-3b-v1/README.md). CSConDa thuộc nhánh huấn luyện lịch sử đó, không được dùng để fine-tune bản 7B này.

Nhóm chưa gán giấy phép chung cho toàn bộ mã nguồn. Không áp dụng giấy phép model 7B cho trọng số 3B hoặc dữ liệu khác.
