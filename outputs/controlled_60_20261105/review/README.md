# Hướng dẫn hai người chấm độc lập

Mỗi phiếu có 360 phản hồi: 60 ca mới, mỗi ca sáu cấu hình ẩn tên. Chỉ chấm phản hồi ở lần lặp 1 đã đăng ký trước; không cần hỏi chatbot trên web hoặc chấm lại ba lần. Hai phiếu chứa cùng nội dung nhưng khác thứ tự, ghép bằng Mã chấm chứ không theo số dòng.

Mỗi người chỉ nhận một phiếu và nguồn `Nguon_cham.zip`. Chấm độc lập, không xem phiếu người kia, raw outputs, mã nguồn định tuyến hoặc ánh xạ trước khi hoàn tất. Nguồn tham chiếu không cho biết cấu hình nào đã tạo phản hồi. Có thể đoán hệ thống từ cách trả lời; nghiên cứu chỉ bảo đảm ẩn tên trên phiếu, không khẳng định mù hoàn toàn.

## Sheet Phieu_cham

Không sửa A–G, mã chấm hoặc nội dung model. Điền tên/ngày ở B3/F3. Các ô vàng cần người chấm nhập; ô trống là chưa chấm, không phải 0. NA chỉ là không áp dụng.

- H, chất lượng 0–2: 2 đáp ứng đủ tiêu chí và đúng dữ kiện/phạm vi; 1 đúng một phần hoặc thiếu ý; 0 sai/không đáp ứng hoặc lỗi thực thi không có phản hồi. Đọc G và nguồn đầy đủ. Lỗi thực thi vẫn thuộc mẫu số, người chấm tự nhập điểm 0.
- I, nhầm sản phẩm trên nhóm H: 1 có nhầm, 0 không nhầm, NA nếu không thể đánh giá như không có phản hồi.
- J, chuyển chủ đề trên nhóm H: 1 chuyển đúng, 0 chuyển sai, NA nếu ca không có yêu cầu chuyển hoặc không có phản hồi để đánh giá.
- K, từ chối nhầm: 1 từ chối yêu cầu có thể hỗ trợ từ dữ liệu/phạm vi, 0 không từ chối nhầm; NA nếu không áp dụng, gồm nhóm T hoặc lỗi thực thi. Yêu cầu thiếu dữ kiện cần hỏi lại/từ chối xác nhận phù hợp không tự động là từ chối nhầm.
- L ghi lý do và nguồn/cụm dữ kiện liên quan. Nếu thấy tiêu chí không khớp snapshot, ghi vấn đề ở đây và báo người điều phối; không tự đổi G.

Sheet `Lich_su` chứa fixture đầu vào đã khóa, đúng vai trò user/assistant, giống nhau cho mọi cấu hình. Đây không phải các lượt assistant được đo trong nghiên cứu. Chỉ đánh giá phản hồi cuối của dòng tương ứng; không tự cộng điểm cho fixture.

## Sheet Phat_bieu và H1

C chỉ gợi ý đoạn đọc bằng cách tách câu/dòng, chưa phải phân đoạn phát biểu đơn chính thức. Người chấm đọc phản hồi nguyên văn ở Phieu_cham, tách/gộp thành các phát biểu đơn tại D; có thể thêm dòng với cùng Mã chấm/Mã ca. Không tạo phát biểu cho phản hồi trống.

E chọn `business_fact` cho dữ kiện nghiệp vụ có thể kiểm chứng, hoặc `non_factual` cho lời chào/lời hỏi, lời khuyên không chứa dữ kiện cần kiểm chứng hoặc không có phát biểu. Với `business_fact`, F chọn:

- `supported`: snapshot hỗ trợ phát biểu đúng sản phẩm, biến thể, thời điểm, phạm vi và mức chắc chắn.
- `contradicted`: snapshot có dữ kiện trái với phát biểu.
- `insufficient_evidence`: không có đủ căn cứ để xác nhận; không tự dùng kiến thức cá nhân hoặc nguồn live thay snapshot.

G ghi ID/tệp, trích dữ kiện và lý do; H ghi chú thêm. Với `non_factual`, để F trống. Không có phát biểu nghiệp vụ thì tỷ lệ phát biểu sai là chưa xác định, không được gán 0%.

Đối chiếu snapshot nghiệp vụ đầy đủ, không chỉ vài hit đã truy xuất. Vì vậy chỉ số này đo sự phù hợp với kho nguồn đã khóa, không tự chứng minh mọi trích dẫn của model đúng hoặc mọi phát biểu nằm trong đúng top-K mà model đã nhận. Giữ đúng phân biệt nguồn nhà bán lẻ và chính sách demo TechCare: không chuyển cam kết của nhà bán lẻ khác thành cam kết của TechCare; không biến khoảng dự kiến thành đảm bảo. Khẳng định đã thực hiện giao dịch/giữ hàng cần bằng chứng, không chỉ lời yêu cầu của user.

`Nguon_tham_chieu` giúp đọc tiêu chí và một số dữ kiện theo mã ca. Giải nén `Nguon_cham.zip` để tra toàn bộ sáu tệp nghiệp vụ, gồm knowledge base, catalog, FAQ, sản phẩm, tài liệu sản phẩm và thông số xác minh. Dùng giá/thông số trong snapshot, không lấy dữ liệu mới trên URL. URL chỉ ghi nhận xuất xứ; nguồn là dữ liệu nghiên cứu, không xác nhận tồn kho hoặc giao dịch thực tế.

## Hoàn tất

Lưu bản sao đã chấm thành `Phieu_R1_da_cham.xlsx` hoặc `Phieu_R2_da_cham.xlsx` rồi gửi người điều phối; giữ nguyên hai phiếu trắng trong hồ sơ gốc. Người điều phối giữ ánh xạ riêng để tự ghép về đúng cấu hình; người chấm không cần biết B1/B2/P hoặc tên model của mỗi dòng. Không chuyển điểm từ các phiếu 400/100 cũ sang phiếu mới. Phần tổng hợp chỉ được chạy trên điểm/nhãn thật, không tự điền ô trống hoặc sửa điểm để tăng đồng thuận.

`mapping_commitment.json` chỉ công bố hash của ánh xạ đã tạo, không công bố tên phương pháp theo mã chấm. Người điều phối cần giữ bản sao riêng của ánh xạ; script tổng hợp kiểm tra đúng hash này trước khi ghép. Tỷ lệ phát biểu ngoài nguồn theo tổng số phát biểu và chênh lệch ghép cặp theo từng phản hồi là hai đại lượng khác nhau, được ghi riêng khi có nhãn thật.
