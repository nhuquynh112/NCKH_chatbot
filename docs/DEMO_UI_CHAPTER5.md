# Tự chạy UI và chụp minh chứng Chương 5

Demo này chọn **P với base `qwen2.5:3b`**, dùng cùng snapshot đã khóa của bộ 24 câu. Không lấy ảnh của profile 3B đã fine-tune rồi ghi là P. Các câu dưới đây có căn cứ đã kiểm tra trong package; câu trả lời của chatbot vẫn cần kiểm tra thực tế, không được bảo đảm trước.

## Mở hai terminal

Ollama phải đang hoạt động và có `qwen2.5:3b`, `nomic-embed-text`. Không cần khởi động 7B cho ảnh của P. Nếu vừa chạy 7B, dừng đúng server của mình trước để giải phóng VRAM.

Terminal backend:

```powershell
cd D:\NCKH\2026_Chatbot\Code\NCKH_chatbot\backend
python -B -m benchmark.demo --study '..\.local\chapter5-24-20261015T145015Z\study-v2' --port 8012 --frontend-port 5174
```

Lệnh tạo database demo **mới** trong `.local/ui-demo-.../demo.db`, nạp snapshot sản phẩm/FAQ và giữ riêng lịch sử/ticket thử. Không ghi vào database ứng dụng thật. Mỗi lần chạy lệnh tạo demo mới; giữ terminal này trong suốt lúc chụp. Dừng bằng Ctrl+C, không xóa database cũ.

Terminal frontend:

```powershell
cd D:\NCKH\2026_Chatbot\Code\NCKH_chatbot\frontend
$env:VITE_API_BASE_URL='http://127.0.0.1:8012/api'
npm run dev -- --host 127.0.0.1 --port 5174 --strictPort
```

Mở `http://127.0.0.1:5174/faqs`. Có nút **Đoạn chat mới**, cột **Lịch sử trò chuyện** và phần **Nguồn tham khảo** trên phản hồi có nguồn. Nếu port bận, không tắt tiến trình lạ; đổi hai port tương ứng ở cả hai terminal. API `/ready` tại `http://127.0.0.1:8012/ready` cần có `chat_model=qwen2.5:3b`, `ai=ok`. API liveness hoặc trang web mở được chưa chứng minh chatbot đã trả lời đúng.

## Checklist chụp ảnh

Mỗi tình huống độc lập nên bắt đầu **Đoạn chat mới**; riêng mục hội thoại nối tiếp dùng cùng phiên. Chờ hết trạng thái đang trả lời. Chụp đủ câu hỏi, phản hồi và nguồn cần minh chứng; không cắt phần trả lời sai để làm ảnh trông đúng.

| Ảnh gợi ý | Thao tác/câu hỏi | Điểm đối chiếu trong nguồn, không phải kết quả đã được hứa |
|---|---|---|
| 5-UI-01 mở chatbot | Mở `/faqs`, bấm Đoạn chat mới | Hiện khung nhập, phiên mới và không lộ dữ liệu khách khác |
| 5-UI-02 dữ kiện catalog | “Mình cần tổng hợp giá niêm yết và số tháng bảo hành của Sạc Anker Nano 65W trong catalog.” | TC01: 990.000 đồng, 18 tháng; `sources/techcare_products.json#slug=anker-nano-65w` |
| 5-UI-03 so sánh | “So Galaxy S25 với S25 Ultra trong catalog: pin mỗi chiếc bao nhiêu mAh?” | TC04: S25 4000mAh, Ultra 5000mAh; không đảo hai mẫu |
| 5-UI-04 thiếu dữ liệu | “iPad Air M3 Wi-Fi 128GB của shop là bản 11 inch hay 13 inch?” | TC12: chưa đủ thông tin, cần xác nhận biến thể; source có ghi cần xác nhận 11/13 inch |
| 5-UI-05 FAQ | “Nhân viên và chatbot có cùng hỗ trợ 24 giờ mỗi ngày không?” | TC10/FAQ hours: chatbot tiếp nhận 24/7, nhân viên 08:00–21:30 theo chính sách demo, ngày lễ có thể đổi |
| 5-UI-06 theo ngữ cảnh | Gửi “Tôi đang xem AirPods Pro 2 USB-C.”; chờ trả lời, rồi hỏi “Còn bảo hành bao lâu?” | TC21: đúng AirPods, 12 tháng. UI tự sinh lượt trước nên đây là hội thoại demo tự do, không hoàn toàn giống lịch sử cố định trong benchmark |
| 5-UI-07 nguồn | Dùng câu sản phẩm hoặc FAQ ở trên, xem toàn phần Nguồn tham khảo | Đọc tên/URL; kiểm tra nguồn có thật sự hỗ trợ phát biểu. Nếu có nguồn thừa hoặc sai, ghi nhận thay vì coi có nguồn là đúng |
| 5-UI-08 lịch sử | Đổi sang Đoạn chat mới rồi chọn lại phiên cũ; có thể tải lại trang | Câu hỏi/phản hồi còn đúng phiên và đúng thứ tự; sidebar title có thể đổi theo câu đầu |
| 5-UI-09 ticket | Phiên thử riêng: “Cho mình gặp nhân viên hỗ trợ về việc kiểm tra lỗi thiết bị.” | Kiểm tra dòng thông báo đã tạo ticket. Nếu cần xem chi tiết, dùng trang quản trị ticket của database demo, không đưa thông tin đăng nhập vào ảnh |

Các source paths trong bảng thuộc package đã sao chép vào `study-v2/package/`; corpus runtime ở `study-v2/corpus/`. Giá và chính sách là mô phỏng nghiên cứu, không phải cam kết bán hàng hiện thời.

## Khi có lỗi

Ghi thời gian, câu hỏi nguyên văn, phiên đang dùng, phản hồi/HTTP status và ảnh lỗi. Giữ `demo.db`, `demo_config.json` cùng log terminal. Nếu câu trả lời sai, nguồn không liên quan, lịch sử nhầm hoặc không tạo ticket, ảnh đó là bằng chứng lỗi cần xử lý; không mô tả là PASS. Khi sửa prompt/luật dựa trên bộ 24 câu, đánh dấu bộ này là DEV và tạo version/test khóa mới trước khi kết luận chất lượng.

Không nhập tên thật, số điện thoại/email, mật khẩu, OTP, số thẻ hoặc thông tin đơn hàng thật. Không chụp trang đăng nhập, DevTools có token, localStorage, `.env` hay màn hình chứa thông tin khách hàng. Dùng nội dung tình huống chung trong bảng. Chưa có kiểm tra trình duyệt ở checklist này: các ô chỉ được đánh dấu sau khi bạn thao tác và quan sát thực tế.
