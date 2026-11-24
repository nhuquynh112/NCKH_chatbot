# Giao thức chấm AI sơ bộ đã khóa trước khi đọc toàn bộ 96 đầu ra

Người dùng chọn đánh giá AI sơ bộ để nhóm duyệt trong phiên ngày 16/10/2026. Đây là một lượt chấm của trợ lý AI, không phải hai giám khảo con người độc lập; không tính kappa hoặc ý nghĩa thống kê.

- Dùng nguyên rubric 0–2 và required_criteria/critical_errors trong answer_key.jsonl. Chấm theo ý nghĩa, không theo chuỗi ký tự.
- Điểm 2: đủ các tiêu chí, không sai dữ kiện hoặc bịa thông tin/cam kết. Điểm 1: trả lời đúng một phần, thiếu tiêu chí nhưng không có lỗi nghiêm trọng. Điểm 0: sai dữ kiện cốt lõi/sai đối tượng, phát biểu bịa thuộc critical_errors, từ chối sai câu có đáp án, hoặc không có phản hồi do lỗi.
- Đánh dấu từng tiêu chí là true/false; mô tả lỗi hoặc ý thiếu. Sai đối tượng/sai dữ kiện được hỏi vẫn là 0 dù một số ý đúng.
- Kiểm toàn bộ phát biểu thêm so với snapshot corpus và history; không chỉ kiểm phần trả lời trực tiếp. unsupported_claim=true khi có khẳng định thực tế không được nguồn/hội thoại hỗ trợ; false chỉ sau khi kiểm; null nếu không có câu trả lời hoặc chưa đủ cơ sở chấm. Hướng dẫn/đề nghị hỏi thêm không tự coi là khẳng định đã thực hiện thao tác.
- Phủ định một khẳng định xấu không phải khẳng định xấu. Nhắc lại giá 1 đồng để bác bỏ không phải xác nhận giá 1 đồng. Không coi tên nội bộ/đoạn prompt lặp là dữ kiện thương mại bịa; ghi cờ echo/format riêng và chấm mức đáp ứng yêu cầu theo rubric.
- B1 không được đọc catalog khi sinh; người chấm vẫn đối chiếu cùng nguồn chuẩn. Câu trả lời ngẫu nhiên khớp đúng dữ kiện không bị phạt chỉ vì phương pháp không có retrieval.
- Lỗi vận hành là trạng thái riêng. Nếu timeout vẫn có fallback thực thì giữ nguyên và chấm nội dung đó; timeout không có phản hồi nhận 0. Latency chỉ tổng hợp status ok/no_rule_match có phản hồi và nêu mẫu số.
- Phiếu chấm che nhãn phương pháp; điều này không bảo đảm mù hoàn toàn vì phong cách đầu ra có thể gợi phương pháp. Không dùng model benchmark tự chấm.
- Lưu cả điểm, nhãn unsupported, criteria_met, bằng chứng/giải thích và mức chắc chắn. Các số chất lượng là đánh giá AI sơ bộ, không phải nhãn chuẩn đã được nhóm thông qua.
- Tỷ lệ đủ tiêu chí = số điểm 2 /24; điểm trung bình = tổng điểm /24. Báo riêng 20 đơn lượt và 4 lượt history cố định. Tỷ lệ ngoài nguồn báo true/24 cùng số phản hồi được chấm và số null.
- Không sửa câu hỏi, gold, prompt, trọng số hay retrieval theo các đầu ra này. Giữ nguyên mọi kết quả và lỗi.
