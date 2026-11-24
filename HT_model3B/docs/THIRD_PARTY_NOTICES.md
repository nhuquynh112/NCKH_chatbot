# Nguồn và giấy phép

Tài liệu này chỉ dẫn tới các thông báo giấy phép đã kèm theo, không thay thế điều khoản gốc.

| Thành phần | Nguồn và thông báo đi kèm |
|---|---|
| Model demo 3B | Built with Qwen. [Qwen Research License](../backend/models/techcare-support-3b-v1/LICENSE); giữ cả phần LICENSE trong `backend/rag_data/Modelfile.techcare3b`. Không gán Apache/MIT cho trọng số 3B. |
| Checkpoint 3B dùng để train | `unsloth/Qwen2.5-3B-Instruct-bnb-4bit`, revision ghi trong `model_profile.json` và `evidence/checkpoint_manifest.json`. |
| CSConDa | [Vietnamese Customer Support QA](https://huggingface.co/datasets/ura-hcmut/Vietnamese-Customer-Support-QA). Bản dữ liệu chọn lọc giữ [Apache 2.0](../backend/models/techcare-support-3b-v1/data/LICENSE), nhãn nguồn/chỉnh sửa và provenance. Không phát hành lại toàn bộ dataset tải về. Tham khảo bài CSConDa, DOI `10.1007/978-3-032-10202-7_33`. |
| Tri thức TechCare | Catalog, FAQ, giá và chính sách là dữ liệu mô phỏng nghiên cứu. Thông số đối chiếu và URL hãng nằm trong `product_verified_specs.json`; không được dùng như bảng giá hay cam kết của doanh nghiệp có thật. |
| Ảnh sản phẩm | Giữ URL nguồn/ảnh từ bản dự án gốc. Repository không tự cấp quyền sở hữu các ảnh bên thứ ba; cần kiểm tra quyền sử dụng trước khi triển khai thương mại. |
| Ảnh chatbot | Ảnh chụp giao diện local thật, ngày 16/10/2026; không phải nội dung sinh giả. |
| Thư viện | Giữ dependency/lockfile của Python và npm; giấy phép từng thư viện thuộc nhà cung cấp tương ứng. |

Repository hiện chưa có tuyên bố giấy phép chung của nhóm cho toàn bộ mã nguồn. Không tự gán một giấy phép mới khi đóng gói. Nhóm cần lựa chọn và bổ sung nếu muốn cấp quyền sử dụng mã nguồn cụ thể. Giấy phép của model và dữ liệu vẫn phải được tuân thủ độc lập.
