# Bằng chứng so sánh B0/B1/B2/P và P+FT

Đây là bản sao các đầu ra đã tồn tại tại `D:/NCKH/Codex/comparison24_P_20261016T065655Z_e0611f3d`, không phải benchmark chạy trong lần đóng gói release. File nguồn bên ngoài repo không bị ghi đè.

- `main_results_96.jsonl`: 24 ca × B0/B1/B2/P, giữ phản hồi, nguồn và trace thực tế.
- `supplementary_PFT_results_24.jsonl`: 24 phản hồi P+FT 7B, tách khỏi bốn phương pháp chính.
- `summary_main.*`, `summary_supplementary_PFT.*`: bảng tổng hợp đã có.
- `*_scores_ai_preliminary.*`, `AI_SCORING_PROTOCOL.md`, `AI_REVIEW_ADDENDUM.json`: điểm **AI sơ bộ để nhóm duyệt**, không phải hai người chấm độc lập.
- `protocol_P_original.json`, `protocol_validation.json`, các tệp consistency/clarifications/trace: cấu hình và kiểm tra tương ứng lần chạy gốc. Đường dẫn máy gốc được giữ làm provenance.
- `SOURCE_MANIFEST.json`: đường dẫn nguồn, số byte và SHA256 từng bản sao; không ghi đè SHA256SUMS của lần chạy cũ.

Bộ input/answer key riêng ở [backend/benchmark/datasets/chapter5_24](../../../backend/benchmark/datasets/chapter5_24). Không cấp answer key cho model. [Hướng dẫn tái lập](../../REPRODUCING_RESEARCH.md) tạo study mới và không sửa kết quả lịch sử.

Chỉ giữ gói bằng chứng cần đọc/đối chiếu; worker log, SQLite thử, corpus/code snapshot đầy đủ và phiên chụp ảnh vẫn ở máy gốc. Bản sao này chưa đủ để mở lại toàn bộ history hay phục hồi harness bằng cách phát lại raw answer. Các status hoàn tất không phải nhãn chất lượng; điểm AI cần được kiểm tra lại. Không sửa số đo hoặc nội dung mục 5.6 khi đóng gói.
