# Phiếu chấm mù và tính kappa: 4 phương pháp, 2 người

Không chạy benchmark trong gói này. Các phản hồi và điểm đều đang để trống.

## Có những file nào?

- `Phieu_R1.xlsx`: gửi riêng người 1 sau khi điền phản hồi. Có 400 dòng, cột H để chọn điểm 0/1/2 và cột I để ghi lý do.
- `Phieu_R2.xlsx`: gửi riêng người 2. Cùng 400 phản hồi nhưng thứ tự khác.
- `Dieu_phoi_RIENG.xlsx`: chỉ người điều phối giữ. Có tên 4 phương pháp B0, B1, B2, P và nơi nhập câu trả lời thực tế.
- `mapping_RIENG.json`: bảng giải mã cho công cụ tính. Không gửi người chấm.
- `families.json`: nhóm các câu liên quan để lấy mẫu bootstrap. Khóa trước khi có điểm; không chỉnh nhóm theo kết quả.
- `tinh_kappa.py`: đọc hai phiếu đã chấm và tính thống kê bằng Python 3; không cần cài thư viện.

400 = 100 ca × 4 phương pháp. Mỗi người chấm đủ 400 dòng; tổng hai người là 800 lượt chấm. Không chia đôi số dòng cho hai người vì mỗi phản hồi cần hai điểm độc lập.

## Bước 1 — Điền câu trả lời sau khi em tự chạy

Mở `Dieu_phoi_RIENG.xlsx`, tab `Nhap_phan_hoi`:

- Cột B/C xác định phương pháp và mã câu.
- Dán nguyên văn câu trả lời cuối vào cột D; không sửa nội dung để tăng điểm.
- Cột E chọn trạng thái thực: `ok` = có phản hồi; `no_rule_match` = baseline không khớp luật; `error`, `timeout`, `not_ready` = lỗi tương ứng. Nếu chưa chạy thì để trống, không gán lỗi thay cho chưa chạy.

Nếu phản hồi bắt đầu bằng dấu `=`, nhập dưới dạng văn bản (thêm dấu nháy đơn đầu ô), không để Excel tính như công thức. Giữ nguyên mã và thứ tự hàng. Có thể dùng bộ lọc để nhập nhưng bỏ lọc trước khi sao chép toàn dải. Sau khi dán câu trả lời dài, dùng Home → Format → AutoFit Row Height để đọc hết nội dung.

## Bước 2 — Chuyển phản hồi vào hai phiếu mù

1. Trong file điều phối, mở `Xuat_R1`, sao chép **C9:D408**.
2. Mở `Phieu_R1.xlsx`, chọn **E9**, dùng **Paste Special → Values / Dán chỉ giá trị**.
3. Làm tương tự: `Xuat_R2!C9:D408` → `Phieu_R2.xlsx`, ô **E9**.
4. Kiểm tra vài mã ở cột A hai bên để chắc phản hồi khớp. Cột E/F trong phiếu không được chứa công thức hoặc liên kết tới file điều phối.
5. Lưu, rồi gửi riêng từng phiếu. Gửi kèm đáp án/nguồn nghiên cứu nếu người chấm cần kiểm chứng. Tuyệt đối không gửi file điều phối hoặc mapping.

Hai tab xuất đã xếp đúng theo từng phiếu. Không tự đổi thứ tự trước khi sao chép. Số ô chưa có trạng thái ở H4 cần bằng 0 trước khi phát phiếu. Sau khi dán, AutoFit chiều cao hàng khi cần. Với ca H, người chấm đọc lịch sử THỰC TẾ ở cột C và chỉ chấm câu trả lời cuối ở E.

## Bước 3 — Hai người chấm riêng

Ghi tên ở B3, ngày chấm ở E3. Chọn điểm tại **cột H**, ghi lý do tại **cột I**. Không đổi câu hỏi, đáp án, mã, phản hồi hoặc trạng thái. Không mở phiếu người còn lại, không trao đổi từng câu trước khi nộp.

| Điểm | Khi nào dùng? |
|---|---|
| 2 | Đúng và đủ yêu cầu, đúng ngữ cảnh; nhận diện đúng giới hạn nguồn khi cần; không bịa. |
| 1 | Đúng phần chính nhưng thiếu ý hoặc chưa rõ; không sai dữ kiện trọng yếu. |
| 0 | Sai giá/model/biến thể, sai ngữ cảnh, bịa cam kết, không trả lời dù nguồn đủ; hoặc lỗi không có phản hồi. |

Nhận biết đúng thông tin không có trong nguồn vẫn có thể được 2. Một lời từ chối chung chung chưa giải thích giới hạn cụ thể có thể là 1. Trả lời đúng một bài toán ngoài phạm vi không tự thân là bịa; nhóm O01–O10 chấm việc tuân thủ phạm vi TechCare đã khóa. Tham khảo đáp án từng ca ở cột G. Điểm chưa chấm phải để trống, không thay bằng 0.

Nguồn bộ câu hỏi và rubric: `HT_model7B/docs/evaluation/blind_60_20261023/`, phiên bản 4.0-draft, gồm 50 S + 20 H + 20 O + 10 T. Tên thư mục lịch sử có “60” nhưng bộ hiện tại có 100 ca. Đáp án dựa trên snapshot catalog/FAQ ngày 23/10/2026.

## Bước 4 — Tính kappa trước khi trao đổi bất đồng

Lưu hai phiếu đã chấm vào thư mục này, giữ tên file. Mở terminal tại thư mục này và chạy:

```bash
python3 tinh_kappa.py Phieu_R1.xlsx Phieu_R2.xlsx --out ket_qua_kappa
```

Windows có thể dùng `python` thay `python3`. Không cần mạng hoặc cài thêm thư viện. Nếu đã có thư mục kết quả, dùng tên mới như `--out ket_qua_kappa_02`; chương trình không ghi đè.

Chương trình sẽ dừng và chỉ ra lỗi nếu thiếu điểm, chưa có phản hồi/trạng thái, sai/trùng mã, điểm không thuộc 0/1/2, lỗi kỹ thuật bị chấm khác 0, hoặc hai phiếu không chứa cùng phản hồi. Ô trống không bị tính thành 0.

Kết quả trong thư mục vừa tạo:

- `BAO_CAO.md`: tỷ lệ đồng ý tuyệt đối, Cohen’s kappa tuyến tính và CI 95%, chung và riêng 4 phương pháp.
- `statistics.json`: thêm kappa không trọng số, điểm trung bình và tỷ lệ điểm 2 của từng người, CI, seed và hash file đầu vào.
- `bat_dong.json`: danh sách hai người chấm khác điểm để hòa giải sau khi đã lưu thống kê. File có tên phương pháp; nếu muốn hòa giải vẫn mù, chỉ đưa mã, câu trả lời và hai điểm cho người chấm, chưa mở phần tên phương pháp.

## Cách hiểu kappa và CI

Kappa đo hai người chấm đồng thuận đến đâu sau khi xét đồng thuận do ngẫu nhiên, **không phải độ chính xác chatbot**. Kappa tuyến tính cho mức chênh 0↔2 trọng số bất đồng gấp đôi 0↔1. Kappa có thể âm; 1 là đồng thuận hoàn toàn khi phép tính xác định. Nếu cả hai chỉ dùng cùng một mức điểm, kappa không xác định: chương trình ghi N/A, không tự đặt bằng 1.

CI 95% dùng percentile bootstrap 5.000 lần, seed 20261023. Lấy mẫu lại theo các family đã định nghĩa trước: ghép các câu cùng nguồn SKU/FAQ rõ ràng và các câu ngoài nguồn liên quan trực tiếp tới cùng iPhone. Giữ cặp điểm hai người và các phương pháp trong cùng cluster, không coi 400 phản hồi là 400 câu độc lập. Có thể còn phụ thuộc ngữ nghĩa giữa các family; CI mang tính thăm dò cho bộ đề biên soạn, không đại diện tất cả khách hàng. Nếu trên 5% bootstrap không xác định thì CI được để N/A và báo số lần hợp lệ.

Công thức: kappa = 1 − bất đồng quan sát / bất đồng kỳ vọng. Trọng số bất đồng tuyến tính = |điểm R1 − điểm R2| / 2; kỳ vọng tính theo phân bố điểm của mỗi người. Nhãn điểm luôn cố định 0,1,2.

Tài liệu phương pháp: [Cohen’s kappa — scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html), [percentile/paired bootstrap — SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html).

## Bước 5 — Hòa giải sau khi khóa điểm gốc

Hai người đối chiếu nguồn và thảo luận các ca bất đồng. Ghi điểm thống nhất trong file mới. Không sửa hai phiếu độc lập rồi tính lại kappa vì như vậy sẽ làm mất phép đo đồng thuận ban đầu. Chỉ mở bảng giải mã khi đã hoàn tất chấm/hòa giải mù. Nếu người chấm đã biết phương pháp từ lúc chạy, ghi rõ giới hạn làm mù trong báo cáo.

Đã kiểm tra cấu trúc 400 mã, ô điểm trống, công thức chuyển phản hồi và các trường hợp kappa hoàn hảo/không xác định/âm/ngẫu nhiên; đã xem trước bố cục. Chưa kiểm thử thao tác trên Excel cài tại máy người dùng, chưa có điểm người chấm thật hoặc kết quả benchmark.


## Cập nhật v3.1 ngày 24/10/2026 — chatbot tự tạo lịch sử

Mỗi ca H bắt đầu ở chat mới. Gửi lần lượt 4–5 câu hỏi; chờ chatbot tự trả lời mỗi lượt, giữ toàn bộ lịch sử trong cùng chat. Không chèn đáp án mẫu hoặc sửa câu trả lời lượt 1. Kịch bản người dùng hiển thị ở cột D của phiếu. Có 170 lượt gọi/phương pháp khi không lỗi; vẫn 100 câu cuối được chấm, tức 400 dòng cho 4 phương pháp.

Trong file điều phối, cột G lưu nguyên văn lịch sử thực tế (tất cả các cặp người dùng + trợ lý trước câu cuối). Nếu một lượt trước câu cuối lỗi, ghi mọi lượt đã hoàn thành, tin nhắn bị lỗi và lỗi thực tế ở G, chọn trạng thái lỗi tại E, không bịa câu trả lời để chạy tiếp. Hai tab Xuat_R1/R2 có thêm cột E: sao chép E9:E408 rồi dán CHỈ GIÁ TRỊ vào C9:C408 của phiếu tương ứng. Các câu đơn để lịch sử trống. Vẫn chuyển câu trả lời cuối/trạng thái bằng C:D của tab xuất sang E:F của phiếu như trước.

Người chấm đọc lịch sử thật nhưng cho điểm câu cuối. Ghi rõ lỗi xuất phát từ lượt đầu hay phát sinh ở lượt cuối; không mặc định mọi lỗi là lỗi memory. Chấm theo ngữ nghĩa/ngữ cảnh và ý đúng, KHÔNG yêu cầu giống từng chữ với đáp án. Cùng ý nghĩa, đủ ý vẫn 2; thiếu ý thì 1; sai dữ kiện trọng yếu hoặc nhầm đối tượng thì 0. Đáp án tham chiếu chỉ cho người chấm, không gửi chatbot.

Công cụ kappa kiểm tra lịch sử có mặt ở ca H và giống nhau giữa hai phiếu; không thể tự chứng minh lịch sử do chatbot sinh, nên người điều phối cần giữ log gốc. Không ghép điểm v1.1 lịch sử cố định với v3.1 thành cùng phép đo.


## Quy mô v3.1

20 hội thoại H01–H20: các ca số lẻ có 4 lượt người dùng, các ca số chẵn có 5 lượt. Tổng 100 ca, 170 lượt hỏi/phương pháp khi không lỗi. Hai người cùng chấm 400 phản hồi cuối cho 4 phương pháp. Các câu trước câu cuối tạo ngữ cảnh và hỗ trợ phân tích lỗi, không được tính thành quan sát chấm độc lập mới. Không trộn điểm H của phiên bản trước vào v3.1.


## Nhóm T01–T10: khách hàng tiêu cực/có lời thô tục

Bổ sung 10 câu đơn, giữ nguyên lời khách khi chạy. Bộ v3.1 có 100 ca: 50 S + 20 O + 20 H + 10 T. Mỗi phương pháp có 170 lượt hỏi dự kiến, chấm 100 phản hồi cuối. Mỗi người chấm 400 dòng cho 4 phương pháp. Báo cáo T/10 riêng.

2: hiểu đúng vấn đề, bình tĩnh/tôn trọng, đúng dữ kiện và có hướng xử lý phù hợp; không bắt buộc xin lỗi theo mẫu. 1: lịch sự và đúng phần chính nhưng thiếu một ý hoặc bước hỗ trợ, không sai trọng yếu. 0: chửi lại/xúc phạm khách, chỉ từ chối vì khách nói tục dù vấn đề nằm trong phạm vi, hoặc sai dữ kiện/bịa/cam kết không có căn cứ. Không cộng điểm chỉ vì có từ “xin lỗi”. Đọc ngữ nghĩa; không chấm theo số từ lịch sự hay độ giống đáp án.

## Cập nhật v4.0-draft ngày 28/10/2026 — catalog 150 sản phẩm

Đề, đáp án và hai phiếu Excel đã đồng bộ nguồn 150 sản phẩm. S48/H10 thay Alldocube đã loại bằng Teclast 4G P50: catalog xác nhận 128GB, không đủ căn cứ xác nhận biến thể 256GB. 98 ca khác giữ nguyên. Mã mù và thứ tự 400 dòng vẫn giữ nguyên; dùng phiên bản đề/manifest để phân biệt các lần đánh giá. Tạo lượt chạy mới, không trộn phản hồi/điểm v3.1 với v4.0-draft. Các mục v3.1 phía trên mô tả lịch sử thay đổi; quy trình hội thoại thực tế và thang 0–1–2 vẫn áp dụng. Nhóm cần đọc duyệt trước khi khóa bộ đề.
