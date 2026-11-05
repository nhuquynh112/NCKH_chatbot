# Thực nghiệm có kiểm soát trên 60 ca mới

Thời gian UTC: 2026-11-05T14:24:27.546142+00:00 đến 2026-11-05T16:53:03.605849+00:00. Commit đăng ký trước: `d26700766c95efef2c805b933ed99c88b21f7b72`. SHA-256 lock: `e7e5f108cc540fa20ecfd22b817adbe4b1f8b40ccd76f9663fa1cb84ecc5f9d6`.

Bộ mới có 24 ca S, 16 H, 12 O và 8 T, do AI hỗ trợ soạn và chưa được người độc lập duyệt. Đề, snapshot và cấu hình được khóa trước khi model nhận câu mới. Rà trùng từ vựng với đúng dữ liệu train/validation và 100 kịch bản cũ không phát hiện cặp vượt ngưỡng; điều này không chứng minh độc lập ngữ nghĩa hay đại diện khách hàng thật.

Hai điều kiện adapter dùng cùng checkpoint 7B NF4/BF16, Transformers/PEFT, tokenizer, GPU RTX 3060 và tham số sinh. P_base không nạp adapter; P_ft nạp adapter lịch sử, không huấn luyện thêm. B1/B2 dùng lại thuật toán cũ với transport HF chung; P_no_memory và P_no_rules chỉ tắt component đã đăng ký. P FP16/Ollama cũ giữ riêng, không trộn vào số đo của bộ mới.

Kiểm tra thực tế: các runtime dùng cùng bộ phiên bản thư viện = True; GPU ghi trong các generation thành công: NVIDIA GeForce RTX 3060. Hash checkpoint/adapter, condition và NF4/BF16 được đối chiếu cho từng identity và generation đã ghi. Đối chiếu prompt base/FT được báo riêng phía dưới; nếu có sai khác, không được xem là phép cô lập adapter đạt yêu cầu.

Đã ghi 1080 lượt cố định (60 ca × 6 cấu hình × 3 vòng) và 48 lượt rollout bổ sung. Lịch sử fixture ở lượt cố định giống nhau giữa mọi cấu hình. Rollout dùng bốn kịch bản H đã đăng ký, lịch sử do mỗi cấu hình sinh; không gộp hai chế độ hoặc coi repeat là câu hỏi độc lập.

## Kết quả thực thi trên lượt cố định

| Cấu hình | Ca / lượt | Lỗi | Có thử gọi LLM cuối | Trung vị ms | Trung bình ms | P95 ms |
|---|---:|---:|---:|---:|---:|---:|
| P_base | 60 / 180 | 0 | 39 | 265,23 | 1.925,21 | 9.844,25 |
| P_ft | 60 / 180 | 0 | 39 | 260,00 | 1.834,87 | 8.711,23 |
| B1_base | 60 / 180 | 0 | 180 | 11.178,05 | 11.388,38 | 23.219,45 |
| B2_base | 60 / 180 | 24 | 180 | 6.961,26 | 7.562,11 | 12.247,19 |
| P_no_memory | 60 / 180 | 0 | 63 | 294,12 | 2.799,07 | 9.703,52 |
| P_no_rules | 60 / 180 | 0 | 177 | 6.680,37 | 6.995,39 | 10.396,57 |

Latency chỉ tổng hợp các lượt thành công; tỷ lệ lỗi và số attempt dùng toàn bộ mẫu. P95 nội suy tuyến tính tại `(n-1)*0,95`, không báo khi ít hơn 20 mẫu. Đây là pipeline lượt cuối, gồm cả nhánh luật/FAQ, không phải toàn bộ thời gian suy luận thuần của LLM. Không đo thời gian hiển thị trình duyệt hoặc TTFT; thời gian nạp model và warmup nằm ngoài mẫu độ trễ truy vấn. Thống kê tách nhánh và từng vòng lặp có trong statistics.json. Không quy ít gọi LLM thành chất lượng tốt hơn.

Số generation chạm giới hạn 384 token đầu ra được lưu riêng; chạm giới hạn có thể làm câu trả lời thiếu ý, nhưng không tự được gán điểm chất lượng hoặc xem là lỗi context. Danh sách ca lỗi và thông báo gốc có trong statistics.json.

## Chênh lệch ghép cặp và độ ổn định

| Phải trừ trái | Ca đủ 3 lần thành công hai bên | Chênh trung bình ms | CI 95% ms |
|---|---:|---:|---|
| P_ft minus P_base | 60 | -90,35 | [-171,09; -21,68] |
| B1_base minus P_base | 60 | 9.463,17 | [7.860,40; 11.103,46] |
| B2_base minus P_base | 52 | 5.379,52 | [4.006,96; 6.684,34] |
| P_no_memory minus P_base | 60 | 873,86 | [272,21; 1.536,53] |
| P_no_rules minus P_base | 60 | 5.070,18 | [4.088,44; 6.072,61] |

Mỗi ca được lấy trung bình trong ba vòng rồi ghép cặp; bootstrap 5.000 lần theo family, seed 20261105. Giữ các repeat trong cùng đơn vị, không dùng n=180 như 180 câu độc lập. Mẫu latency ghép cặp loại ca không đủ ba lần thành công và phải đọc cùng tỷ lệ lỗi. Các khoảng tin cậy mang tính thăm dò, chưa hiệu chỉnh đa kiểm định, không đại diện biến động trên phần cứng khác.

Đối chiếu 180 cặp base/FT: 0 cặp khác prompt/lời gọi; 39 cặp có thử gọi LLM, 141 cặp không gọi LLM. Khác phản hồi ở cặp không gọi LLM: 0. Số cặp cấu hình/ca có thay đổi trạng thái hoặc nội dung qua ba vòng: 0.

Các ca lỗi giữ nguyên request, prompt, response nếu có, record và log. Lỗi context không có phản hồi thay thế; không diễn giải việc không có phát biểu do lỗi thành 0% phát biểu sai. Không chọn lại lần chạy thành công hoặc câu trả lời đẹp nhất.

## Chất lượng và H1–H3

Chưa có điểm/nhãn người chấm cho bộ mới nên chưa kết luận adapter cải thiện chất lượng, P giảm phát biểu ngoài nguồn, quản lý sản phẩm giảm nhầm, hoặc phân tuyến tiết kiệm chi phí mà giữ nguyên chất lượng. Hai phiếu mới chứa 360 phản hồi của repetition 1 đã đăng ký trước; hai người chấm độc lập, ẩn tên cấu hình trên phiếu. H1 cần nhãn phát biểu từ snapshot; H2 cần nhầm sản phẩm/chuyển chủ đề ở nhóm H; H3 cần chất lượng và từ chối nhầm bên cạnh số gọi/thời gian. Không dùng lại điểm của bộ 400/100 cũ cho phản hồi mới.

Chi phí chỉ được đại diện bằng số yêu cầu LLM và số token ghi nhận, không phải tiền hoặc điện năng đã đo. Tải máy desktop, cache và thời điểm giữa các block còn biến động; hai warmup chat riêng mỗi block và việc đảo thứ tự không loại bỏ mọi yếu tố này. Lịch sử fixture là dữ liệu tình huống tổng hợp, không đại diện phân bố hội thoại thực địa. Các số liệu quan sát, kể cả không cải thiện hoặc có lỗi, đều được giữ trong hồ sơ.

## Dùng trong báo cáo

Có thể bổ sung thiết kế và bảng số liệu thực thi sau mục đánh giá P+FT cũ (một tiểu mục mới), giữ nguyên các bảng/điểm lịch sử. Phần kiểm định H1–H3 ghi rõ đang chờ hai phiếu và nhãn phát biểu mới; cập nhật chênh lệch chất lượng/CI sau khi chạy score_reviews. Không chèn kết luận cải thiện chất lượng từ bảng độ trễ. Hướng dẫn lệnh và phạm vi component ở README của controlled_study.
