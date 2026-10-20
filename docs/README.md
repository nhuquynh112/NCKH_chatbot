# Tài liệu TechCare

- [Cài đặt và chạy website](../README.md): hướng dẫn chính cho máy Windows mới.
- [Bản demo ngày 20/10/2026](DEMO_RELEASE.md): phạm vi, kết quả kiểm tra cuối, giới hạn và lệnh quay video trên máy hiện tại.
- [Điều tra LLM/RAG](LLM_RAG_INVESTIGATION_20261020.md): bằng chứng trước/sau bản vá riêng cho website; giữ nguyên số liệu benchmark.
- [Tái lập nghiên cứu trên máy khác](REPRODUCING_RESEARCH.md): bộ 24 câu, B0/B1/B2/P, P+FT và vị trí bằng chứng đã đóng gói.
- [Demo web bốn phương pháp](LOCAL_BENCHMARK_DEMO.md): ảnh giao diện thực tế, lịch sử TC21 và giới hạn của harness.
- [Giao thức Chương 5](CHAPTER5_RUNBOOK.md), [hồ sơ thực nghiệm](CHAPTER5_EXPERIMENTS_24.md): giữ nguyên các mô tả thí nghiệm và mục 5.6; đường dẫn `.local` là đường dẫn của lần chạy gốc, không phải file được tải từ GitHub.
- [Model serving và benchmark M1–M4](MODELS_AND_BENCHMARK.md), [kết quả tích hợp](INTEGRATION_RESULTS.md), [audit tích hợp](INTEGRATION_PLAN.md).
- [Bằng chứng so sánh 24 câu đã đóng gói](research/chapter5-24/README.md): raw outputs, điểm AI sơ bộ và SHA256; không phải kết quả đo mới.
- [Model demo 3B](../backend/models/techcare-support-3b-v1/README.md): trọng số, dữ liệu, provenance và tái tạo huấn luyện.
- [Giấy phép và nguồn](THIRD_PARTY_NOTICES.md).

## Hồ sơ lịch sử được giữ nguyên nội dung

Các file sau đã chuyển vào `history/`; tên nhánh, đường dẫn và số đo bên trong mô tả thời điểm thí nghiệm cũ. Không dùng chúng thay cho hướng dẫn cài đặt hiện hành.

- [Audit 14/10](history/CHATBOT_AUDIT.md).
- [Kết quả đánh giá 14/10](history/CHATBOT_EVALUATION_REPORT.md).
- [Các cải tiến](history/CHATBOT_IMPROVEMENTS.md).
- [Nguồn dataset và quyết định sử dụng](history/DATASET_CANDIDATES.md).
- [Hồi quy catalog/API đã lưu](history/EVALUATION_REPORT.md).
- [Kiểm toán thông số sản phẩm](history/PRODUCT_DATA_AUDIT.md).

Các log/cache/database thử đầy đủ vẫn giữ trên máy gốc và bị Git bỏ qua. Kết quả kiểm thử release mới dùng thư mục riêng ngoài repository; không ghi đè các hồ sơ trên.
