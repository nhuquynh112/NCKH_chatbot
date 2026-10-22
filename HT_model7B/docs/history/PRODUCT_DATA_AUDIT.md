# KIỂM TOÁN DỮ LIỆU SẢN PHẨM TECHCARE

Ngày đối chiếu: 16/09/2026

## Kết quả

- Tổng sản phẩm active: **53**.
- Có nguồn chính thức của hãng: **47/53 (88,68%)**.
- Đã xác minh đúng biến thể/cấu hình đủ để trả lời trực tiếp: **25**.
- Đã đối chiếu theo dòng sản phẩm nhưng vẫn cần mã SKU/part number khi chốt đơn: **22**.
- Chưa thể ghép với một trang hãng duy nhất vì tên catalog quá chung: **6**.

Thông số đã xác minh nằm tại `rag_data/product_verified_specs.json`. Mỗi mục lưu trạng thái xác minh, ngày kiểm tra và URL nguồn. Script `sync_verified_products.py` đồng bộ các sửa đổi đã duyệt vào database.

## Sáu sản phẩm cần bổ sung mã hàng

| Slug               | Tên hiện tại       | Dữ liệu còn thiếu để xác minh đúng biến thể                                                     |
| ------------------ | ------------------ | ----------------------------------------------------------------------------------------------- |
| `anker-nano-65w`   | Sạc Anker Nano 65W | Mã model/part number; Anker có nhiều bộ sạc Nano 65W với số cổng khác nhau.                     |
| `rog-strix-g16`    | ASUS ROG Strix G16 | Mã G614 đầy đủ; cấu hình i7-14650HX/RTX 4060 không đủ xác định màn hình và công suất GPU.       |
| `legion-5`         | Lenovo Legion 5    | Mã MTM; tên Ryzen 9/RTX 4070 xuất hiện ở nhiều đời/khu vực.                                     |
| `hp-pavilion-15`   | HP Pavilion 15     | Product number dạng `xx-xxxxxx`; “Core i5/16GB/512GB” có rất nhiều biến thể màn hình và CPU.    |
| `gigabyte-g5`      | Gigabyte G5        | Hậu tố model (KF/MF/GD...) để xác định CPU, GPU, màn hình và pin.                               |
| `gigabyte-aorus15` | Gigabyte Aorus 15  | Mã model; trang hãng tìm được bản Core Ultra 7, không khớp khai báo Core Ultra 9 trong catalog. |

Với sáu mục này, chatbot vẫn có thể trả lời giá, bảo hành và cấu hình mà cửa hàng đã nhập; nhưng khi khách hỏi chi tiết chưa có, bot phải nói rõ cần mã SKU thay vì suy đoán.

## Các sửa lỗi nổi bật

- `iPhone 17 128GB` được sửa thành `iPhone 17 256GB`; Apple không công bố bản 128GB.
- Giá iPhone 17/17 Pro được cập nhật theo trang Apple Việt Nam tại ngày đối chiếu; giao diện vẫn cảnh báo giá không phải dữ liệu thời gian thực.
- `Galaxy Tab S10` được chuẩn hóa thành `Galaxy Tab S10+ 12GB/256GB`; tên cũ không chỉ rõ model thực tế.
- MSI PRO MP2412 được sửa từ tấm nền IPS sang VA theo trang thông số của MSI.
- Các trường RAM iPhone không có trong thông số chính thức của Apple đã bị loại bỏ, tránh biến dữ liệu bên thứ ba thành khẳng định của hãng.
- Nguồn hãng được trả về qua metadata và hiển thị thành liên kết bấm được trong chatbox.

## Nguyên tắc vận hành

1. Giá và trạng thái `active` thuộc database cửa hàng; không được diễn giải thành tồn kho thời gian thực.
2. Thông số hãng thuộc file xác minh và phải có URL nguồn.
3. Không tự động lấy nội dung ngẫu nhiên từ Google đưa thẳng vào database. Kết quả tìm kiếm chỉ dùng để tìm trang chính thức, sau đó con người duyệt bản ghi.
4. Khi nhập sản phẩm mới, bắt buộc lưu SKU/part number; nếu thiếu thì gắn trạng thái `store_catalog_only`.
5. Chạy lại `python sync_verified_products.py`, `python export_rag.py`, `python rebuild_rag.py` và bộ kiểm thử sau mỗi lần đổi catalog.
