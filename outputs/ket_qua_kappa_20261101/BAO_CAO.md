# Đồng thuận giữa hai người chấm

Điểm độc lập trước hòa giải. Kappa đo độ đồng thuận, không đo độ đúng của chatbot.

| Nhóm | Số cặp | Đồng ý tuyệt đối | Kappa tuyến tính | CI 95% |
|---|---:|---:|---:|---|
| Tất cả | 400 | 75.0% | 0.6897 | [0.6253; 0.7391] |
| B0 | 100 | 82.0% | 0.7489 | [0.6240; 0.8516] |
| B1 | 100 | 62.0% | 0.4327 | [0.2780; 0.5569] |
| B2 | 100 | 78.0% | 0.6910 | [0.5566; 0.7959] |
| P | 100 | 78.0% | 0.7120 | [0.5665; 0.8021] |

Bootstrap 5000 lần theo family, seed 20261023; không coi 400 phản hồi là 400 câu hỏi độc lập.
CI mô tả độ bất định khi lấy mẫu lại các family của bộ đề đã biên soạn, không chứng minh khả năng khái quát ra toàn bộ khách hàng. Một số quan hệ ngữ nghĩa giữa family vẫn có thể tồn tại.
Kappa N/A khi mẫu không có biến thiên cần thiết. CI N/A nếu trên 5% lần bootstrap không xác định hoặc không đủ cluster. Xem số lần hợp lệ trong statistics.json.
Số phản hồi bất đồng: 100. Giữ nguyên hai phiếu gốc; hòa giải trong tài liệu riêng.

Nguồn phương pháp: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html ; https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html