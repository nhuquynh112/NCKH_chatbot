# Chấm mù từng bước — bản cập nhật 28/10/2026

Đối chiếu với code commit `6415b22`, nhánh `chatbotv1-demo`. Đây là hướng dẫn thao tác, không phải kết quả đã chạy hoặc điểm đã chấm.

## 1. Hiểu đúng việc cần làm

Một người điều phối chạy 4 phương pháp, lưu câu trả lời, tạo hai phiếu. Hai người chấm đọc **cùng các câu trả lời thực tế**, nhưng không biết câu nào thuộc phương pháp nào. Mỗi người chấm riêng rồi gửi lại file. Người điều phối tính kappa trên hai bộ điểm ban đầu, sau đó mới hòa giải bất đồng.

Với 100 ca × 4 phương pháp: mỗi người chấm 400 dòng, không chia 200 dòng/người. Không để mỗi người tự chạy lại chatbot rồi ghép hai bộ điểm: câu trả lời khác nhau không phải một đối tượng để đo đồng thuận.

Nên có người điều phối không tham gia chấm. Nếu nhóm chỉ có hai người và một người đã xem phương pháp hoặc mapping, cần ghi rõ giới hạn làm mù trong báo cáo; không gọi đó là mù hoàn toàn.

## 2. Kiểm tra bộ đề trước khi chạy chính thức

Catalog hiện tại có **150 sản phẩm**. Bộ **v4.0-draft** đã cập nhật đề, đáp án và hai phiếu Excel tương ứng. S48/H10 đã chuyển sang Teclast: nguồn xác nhận 128GB, chưa xác nhận biến thể 256GB. Vẫn có 100 ca và 400 dòng chấm/người.

Nhóm đọc duyệt bản dự thảo, khóa manifest và tạo lượt chạy mới trên corpus 150 sản phẩm. Không ghép câu trả lời hay điểm của bộ cũ vào bản mới. Có thể thử thao tác ở phiên riêng; không tính điểm thử vào kết quả chính thức. Đáp án chỉ gửi người chấm, không nhập vào chatbot/RAG.

## 3. Mở web ẩn danh

Nếu máy đã cài môi trường, mở hai terminal trên Linux.

Terminal 1:

```bash
cd /home/ad/Desktop/NCKH_chatbot/HT_model7B/backend
.venv/bin/python comparison_demo.py
```

Terminal 2:

```bash
cd /home/ad/Desktop/NCKH_chatbot/HT_model7B/frontend
npm run test:methods
```

Mở `http://127.0.0.1:5174/benchmark-demo`. Nếu chưa có môi trường Python/Node/model, làm phần cài đặt trong `TEST_4_PHUONG_PHAP.md` trước; các lệnh trên không tự cài chúng. Windows dùng lệnh PowerShell trong tài liệu đó.

Web hiện Trợ lý A/B/C/D. Không coi A=B0, B=B1: ánh xạ được xáo trộn theo phiên. Không bấm **Phiên đánh giá mới** giữa bốn trợ lý. Ghi lại đường dẫn `output` in ở terminal, giữ nguyên thư mục và log để tiếp tục/đối chiếu. Không dùng `--coordinator` cho giao diện người chấm.

## 4. Chạy câu đơn

Ví dụ với S01:

1. Chọn Trợ lý A.
2. Điền mã `S01` và nguyên câu S01 trong bộ đề đã khóa.
3. Lịch sử đầu vào để `[]`.
4. Bấm **Gửi câu hỏi**, chờ và giữ câu trả lời thực tế.
5. Chọn B, C, D và chạy cùng câu S01. Giữ câu hỏi đúng nguyên bản.
6. Chuyển mã S02, tiếp tục như vậy. Nút **Câu tiếp theo** sinh mã TEST..., vì vậy cần sửa thành đúng mã bộ đề.

Không chọn lại câu trả lời hay nhất khi chạy nhiều lần. Nếu phải chạy lại vì lỗi, ghi lượt được sử dụng và lý do; giữ mọi log gốc.

## 5. Chạy hội thoại 4–5 lượt

**Web mới chưa tự nối lịch sử.** Vẫn phải đưa toàn bộ lịch sử thật vào ô **Lịch sử đầu vào (JSON)** khi hỏi lượt tiếp theo.

Ví dụ H01 có 4 lượt, chạy riêng với Trợ lý A:

| Lượt | Mã nhập trên web | Lịch sử đầu vào |
|---|---|---|
| 1 | H01_L1 | [] |
| 2 | H01_L2 | Câu hỏi 1 + phản hồi thật 1 |
| 3 | H01_L3 | Cả cặp 1 và cặp 2 |
| 4, câu cuối | H01 | Cả cặp 1, 2 và 3 |

Các câu hỏi lấy đúng từ kịch bản H01. Với ca 5 lượt, dùng Hxx_L1 đến Hxx_L4 rồi mã Hxx cho câu cuối. Cách đặt mã này giúp phản hồi cuối khớp mã ca trong Excel, và không vi phạm yêu cầu cùng mã phải cùng câu hỏi trên web.

Schema lịch sử minh họa (thay nội dung bằng log thật):

```json
[
  {"role":"user","content":"Câu hỏi lượt 1 đã gửi"},
  {"role":"assistant","content":"Phản hồi lượt 1 thực tế của trợ lý đang chọn"}
]
```

Ở lượt sau, nối thêm các cặp đã hoàn thành, không bỏ lịch sử cũ. Không chép đáp án tham chiếu vào lịch sử. Khi chuyển sang Trợ lý B, bắt đầu H01_L1 với `[]`, để B tự trả lời mọi lượt; không lấy lịch sử của A cho B. Giữ mọi câu trả lời nguyên văn, kể cả câu sai. Nếu một lượt thiết lập bị lỗi, giữ log các lượt đã có, ghi lỗi và dừng ca; không chế câu trả lời để tiếp tục.

Mỗi hội thoại chỉ có **một điểm cho phản hồi cuối**. Lịch sử trước đó giúp hiểu ngữ cảnh và xác định nguồn gốc lỗi. Có 170 lượt hỏi dự kiến/phương pháp khi không lỗi, nhưng chỉ 100 phản hồi cuối được chấm/phương pháp.

## 6. Xuất dữ liệu và đưa vào Excel

Bấm **Tải phiếu CSV ẩn danh** trên web. CSV là tệp tải về, không phải thao tác gửi điểm. Giữ file gốc chưa chấm và toàn bộ thư mục output.

CSV có run_id, case_id, system_id, system_label, question, history, answer, status và các ô điểm trống. Với lượt hội thoại, giữ các dòng trung gian để kiểm chứng nhưng chỉ đưa phản hồi cuối H01–H20 vào 400 dòng chấm.

Các mã A/B/C/D và system_id của web **không trùng** mã K... trong Excel có sẵn. Người điều phối xem `output/sessions/<session>/mapping_RIENG.json` để quy đổi đúng system_id → phương pháp, rồi điền theo **phương pháp + mã ca** trong file điều phối Excel. Không đoán theo chữ A/B/C/D hoặc thứ tự dòng CSV. Giữ thêm bảng ghi run_id nào được chọn cho từng phương pháp/mã ca, đặc biệt khi có chạy lại.

Mở `outputs/kappa_4_methods_20261023/Dieu_phoi_RIENG.xlsx`, tab `Nhap_phan_hoi`:

| Cột | Cách dùng |
|---|---|
| B/C | Phương pháp và mã ca có sẵn, dùng để tìm đúng dòng |
| D | Dán nguyên văn câu trả lời cuối |
| E | Trạng thái thực tế; dùng raw log khi cần phân biệt no_rule_match |
| F | Ghi run_id, session và lý do chạy lại nếu có |
| G | Với H: toàn bộ lịch sử thật trước câu cuối; câu đơn để trống |

Sau đó chuyển sang phiếu người chấm bằng **Dán chỉ giá trị**:

| Nguồn trong file điều phối | Đích |
|---|---|
| Xuat_R1!C9:D408 | Phieu_R1.xlsx → E9:F408 |
| Xuat_R1!E9:E408 | Phieu_R1.xlsx → C9:C408 |
| Xuat_R2!C9:D408 | Phieu_R2.xlsx → E9:F408 |
| Xuat_R2!E9:E408 | Phieu_R2.xlsx → C9:C408 |

Không sắp xếp lại hàng trước bước chuyển. Kiểm tra mã ở cột A hai bên để bảo đảm dán đúng. Không dán công thức/liên kết từ file điều phối sang phiếu người chấm. Ô H4 báo số dòng thiếu trạng thái; cần hết thiếu trước khi phát phiếu. Phản hồi dài thì dùng AutoFit Row Height để đọc hết.

CSV cũng có thể dùng để chấm, nhưng script kappa hiện tại nhận **hai file Excel**, không tự nhận CSV web. Để tránh phải đổi định dạng về sau, nên dùng luồng Excel ở trên.

## 7. Gửi phiếu cho hai người

- Người 1 nhận riêng Phieu_R1.xlsx.
- Người 2 nhận riêng Phieu_R2.xlsx.
- Cả hai nhận cùng bộ tiêu chí, đáp án tham chiếu và snapshot nguồn đã khóa.
- Không gửi file điều phối, mapping, raw log hoặc thông tin tên phương pháp/model.

Có thể gửi file qua kênh nhóm đang dùng. Không gửi cả thư mục dự án/output cho người chấm vì bên trong có bảng giải mã. Hai người không xem phiếu của nhau trong lúc chấm.

## 8. Người chấm điền gì?

Ghi tên ở B3, ngày ở E3. Với mỗi dòng, đọc lịch sử C (nếu có), câu hỏi D, phản hồi E, đáp án/tiêu chí G. Điền **điểm tại H**, lý do tại **I**.

- **2:** đúng nghĩa, đúng ngữ cảnh, đủ ý, không bịa.
- **1:** đúng phần chính nhưng thiếu ý, không sai dữ kiện trọng yếu.
- **0:** sai trọng yếu, nhầm sản phẩm/ngữ cảnh, bịa hoặc không trả lời khi nguồn đủ; lỗi thực thi không có phản hồi cũng 0 và ghi rõ lỗi.

Không cần giống từng chữ đáp án. Câu ngoài nguồn mà nhận biết đúng giới hạn vẫn có thể 2. Với khách chửi tục, đánh giá thái độ bình tĩnh và cách hỗ trợ đúng; không cộng điểm chỉ vì có chữ “xin lỗi”. Không đổi giá đúng theo snapshot bằng giá thị trường hôm chấm.

Chưa chấm để trống, không nhập 0 thay. Giữ nguyên mã, câu hỏi, phản hồi, lịch sử và thứ tự. H3 đếm số điểm đã nhập; khi hoàn tất phải đủ 400. Nếu ca có lỗi từ lượt trước, ghi rõ, không mặc định mọi câu sai đều là lỗi memory.

## 9. Gửi điểm lại như thế nào?

Người chấm bấm **Lưu** và gửi lại chính file `.xlsx` đã điền qua kênh trao đổi hoặc đính kèm vào chat này. Không gửi ảnh chụp màn hình hay chỉ tổng điểm: cần từng dòng để ghép cặp và tính kappa.

Tin nhắn mẫu:

> Em gửi Phieu_R1.xlsx đã chấm đủ 400 dòng, giữ nguyên mã và phản hồi. Đây là điểm chấm độc lập, chưa trao đổi/hòa giải với người còn lại.

Người 2 gửi tương tự. Giao diện web hiện tại không có nút gửi/đồng bộ điểm; điểm không tự được nộp khi tải CSV hay sửa Excel.

Giữ bản gốc hai người nộp, sao chép để phân tích. Không sửa điểm cho khớp nhau trước khi tính kappa.

## 10. Tính kappa và khoảng tin cậy

Đặt hai file đã chấm cạnh tinh_kappa.py, mapping_RIENG.json, families.json. Tại thư mục đó chạy:

```bash
python3 tinh_kappa.py Phieu_R1.xlsx Phieu_R2.xlsx --out ket_qua_kappa_lan1
```

Windows có thể dùng `python`. Không cần cài thư viện thêm. Công cụ yêu cầu đủ 400 dòng và cặp phản hồi/lịch sử trùng nhau; ô thiếu hoặc mã sai sẽ bị báo lỗi. Không coi ô trống là 0. Tên thư mục kết quả phải mới.

Đọc BAO_CAO.md để xem đồng thuận, kappa tuyến tính và CI 95%; statistics.json có chi tiết; bat_dong.json liệt kê ca chấm khác. Kappa đo sự đồng thuận giữa hai người, không phải độ chính xác của chatbot. CI dùng bootstrap theo family, không coi 400 phản hồi là 400 câu hỏi độc lập.

Sau khi lưu kết quả độc lập, hai người mới xem lại các ca bất đồng và ghi điểm thống nhất trong file riêng. Nếu vẫn hòa giải mù, người điều phối chỉ đưa mã/câu trả lời/điểm, không gửi trường tên phương pháp trong bat_dong.json. Chỉ giải mã phương pháp sau khi khóa điểm. Không thay điểm gốc bằng điểm hòa giải rồi báo kappa đó là độ đồng thuận ban đầu.
