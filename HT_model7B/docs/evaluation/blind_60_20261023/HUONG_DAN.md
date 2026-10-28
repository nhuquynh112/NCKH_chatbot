# Quy trình chấm mù độc lập với hai người

Bộ đề dự thảo v4.0-draft cập nhật ngày 28/10/2026: 50 câu đơn S01–S50, 20 ca hội thoại H01–H20, 20 câu ngoài nguồn O01–O20 và 10 câu khách hàng tiêu cực T01–T10. “Có lịch sử” nghĩa là tham chiếu hội thoại trước đó, không phải câu hỏi lịch sử kiến thức. Mỗi ca H có 4–5 lượt người dùng. Chatbot tự sinh phản hồi ở tất cả các lượt trong cùng phiên; chấm phản hồi cuối, đọc cả lịch sử thực tế. Tổng 100 phản hồi/hệ thống/người chấm. Nếu so sánh 4 hệ thống thì mỗi người chấm 400 phản hồi; không chia đôi câu hỏi giữa hai người.

## Tài liệu

- CAU_HOI.md / questions.json: đầu vào cho hệ thống, không chứa đáp án.
- DAP_AN.md / answer_key.json: đáp án tham chiếu và tiêu chí chấm.
- manifest.json: số lượng ca và SHA-256 nguồn để nhận diện snapshot.
- tao_phieu_mu.py: tạo phiếu có mã ẩn danh và thứ tự riêng cho từng người.

Phân bố: 20 tra cứu giá/định danh; 5 so sánh biến thể; 5 lọc ngân sách; 10 chính sách; 10 xử lý thiếu dữ liệu/nguồn/chống bịa; 20 theo dõi lịch sử; bổ sung 10 ngoài phạm vi và 10 thiếu dữ liệu nghiệp vụ. Không suy rộng kết quả này thành tỷ lệ đúng của toàn bộ 150 sản phẩm.

## Chuẩn bị và khóa bộ đề

1. Hai người đọc hướng dẫn và thống nhất cách chấm trên vài ví dụ ngoài 100 ca. Người phụ trách rà lại câu hỏi/đáp án trước khi khóa; bộ này do AI biên soạn từ nguồn dự án, chưa phải bộ holdout được con người xây dựng độc lập.
2. Cố định snapshot catalog, FAQ, KB, index, phiên bản code, prompt, cấu hình truy xuất, model/digest, tham số sinh và ngày chạy. Lưu các thông tin này cùng kết quả. Không cập nhật giá trực tuyến giữa lượt test; chấm theo snapshot 23/10/2026.
3. Không nạp câu hỏi hoặc đáp án vào RAG, prompt hay dữ liệu train. Nếu đã dùng kết quả để sửa hệ thống, coi bộ này là DEV; cần bộ test mới cho đánh giá cuối.
4. S48 và H10 kiểm tra biến thể Teclast: nguồn xác nhận 128GB, chưa xác nhận 256GB. Đây không phải mâu thuẫn nội bộ catalog. Bản v4.0-draft đồng bộ catalog 150 sản phẩm; duyệt đề, khóa manifest trước khi chạy và không trộn kết quả bộ cũ.

## Chạy và làm mù

1. Với mỗi phương pháp, mở phiên mới cho từng ca. Với H, gửi lần lượt history_questions, chờ chatbot tự trả lời, giữ nguyên phản hồi đó trong cùng phiên rồi gửi question. Không cấp câu trả lời mẫu; không sửa, chọn lại hoặc thay phản hồi lượt đầu bằng phản hồi của phương pháp khác. Nếu tự gọi API không có session, truyền lại đúng các tin nhắn thực tế. Các phương pháp nhận cùng câu hỏi người dùng, nhưng lịch sử trợ lý được phép khác nhau.
2. Gửi câu hỏi theo đúng trình tự trên vào chatbot, không gửi đáp án, nhóm câu hoặc tiêu chí. Ghi nguyên văn phản hồi cuối, cả lỗi/timeout. Chốt thời hạn chờ trước khi chạy và áp dụng giống nhau. Không chọn phản hồi tốt nhất trong nhiều lần thử.
3. Lưu JSONL mỗi dòng dạng: {"system_id":"ten-he-thong","case_id":"S01","answer":"Phản hồi nguyên văn","status":"ok"}. Lỗi dùng status="error", answer="". Mỗi hệ thống phải đủ 100 dòng. Với H, bổ sung trường history chứa đầy đủ các lượt user/assistant thực tế trước câu cuối, đúng thứ tự kịch bản và setup_status="ok". Nếu một lượt trước câu cuối lỗi, ghi setup_status="error", status="error", history gồm các cặp user/assistant đã hoàn thành và tin nhắn user của lượt bị lỗi, answer=""; dừng ca đó và ghi rõ lượt bị lỗi, không bịa phản hồi để tiếp tục. Không tự chèn câu trả lời cho yêu cầu làm rõ; tiếp tục câu hỏi đã định sẵn và ghi giới hạn của kịch bản. Nếu cần nhiều lần lặp, tạo gói riêng cho từng lần; báo cáo mọi lần, không coi chúng là câu hỏi độc lập mới.
4. Tạo phiếu bằng Python 3 (chỉ thư viện chuẩn):

   `python3 tao_phieu_mu.py /duong/dan/responses.jsonl /duong/dan/goi_cham_moi`

5. Gửi thư mục R1 cho người 1, R2 cho người 2; cả hai nhận cùng bộ đáp án và nguồn snapshot. Không gửi responses.jsonl hoặc thư mục DIEU_PHOI_KHONG_GUI_NGUOI_CHAM. Tên model, phương pháp, latency, log công cụ và chế độ retrieval không xuất hiện trong phiếu. Giữ nguyên nội dung phản hồi, không biên tập để tăng điểm.
6. Tốt nhất một người điều phối giữ mapping, không tham gia chấm. Nếu chỉ có đúng hai người, chạy script tự động và không mở mapping cho đến khi cả hai khóa phiếu. Nếu một người đã biết mapping hoặc nhận ra hệ thống từ nội dung, ghi nhận giới hạn làm mù; không tuyên bố mù tuyệt đối. Đây là chấm ẩn danh hệ thống, không phải thử nghiệm lâm sàng mù đôi.

## Thang điểm 0–2

- 2: trả lời đủ yêu cầu, đúng dữ kiện/biến thể/ngữ cảnh; nhận biết giới hạn hoặc hỏi rõ khi cần; không thêm dữ kiện không có căn cứ.
- 1: phần chính đúng nhưng còn thiếu một yêu cầu hoặc diễn đạt chưa rõ; không sai dữ kiện trọng yếu. Ví dụ nêu đúng mẫu và giá nhưng bỏ hãng khi đề hỏi hãng.
- 0: sai giá/dung lượng/sản phẩm, mất ngữ cảnh khiến trả lời sai, bịa tồn kho hoặc cam kết; không trả lời dù nguồn đủ; lỗi/timeout/không có phản hồi.

Chấp nhận diễn đạt tương đương và cách viết số khác nhau; không yêu cầu trùng từ khóa. Không bắt buộc nhắc “snapshot” hoặc dẫn link trong mọi câu, trừ khi câu hỏi yêu cầu nguồn/ngày thu thập. Tuy nhiên khẳng định giá trực tiếp hiện tại hoặc tồn kho khi nguồn không hỗ trợ là lỗi. Lỗi trọng yếu luôn chấm 0 dù những phần khác đúng.

Trong câu thiếu dữ liệu, nêu rõ thiếu và hỏi lại/xác minh là đáp án đúng; không chấm 0 chỉ vì chatbot không đưa ra một con số. Với câu lọc, đáp án liệt kê tập hợp hợp lệ: người trả lời chỉ cần chọn đúng 2 mẫu, không cần kể toàn bộ.

Ghi thêm độc lập với điểm: unsupported_claim=true/false (có phát biểu không có căn cứ); context_error=true/false cho H, null cho S; notes giải thích lỗi và trích trường nguồn. Với lỗi không có phản hồi, unsupported_claim=null, không coi đó là câu trả lời an toàn đúng.

## Hai người chấm độc lập và tổng hợp

Hai người chấm riêng, không xem điểm của nhau và không thảo luận từng ca trước khi nộp. Khóa/lưu hai phiếu gốc. Ghép bằng blind_id rồi tính mức đồng thuận trước khi hòa giải; không ghi đè điểm gốc bằng điểm đã thống nhất.

Báo cáo cho mỗi hệ thống: số đạt điểm 2/100, điểm trung bình 0–2, kết quả riêng S/50, H/20, O/20 và T/10, kết quả theo nhóm, lỗi/timeout và tỷ lệ câu có phát biểu ngoài nguồn trên các phản hồi hợp lệ (công bố mẫu số). Báo cáo kết quả của mỗi người riêng và điểm sau hòa giải. Có thể quy đổi tổng điểm /200 ×100%, nhưng không gọi đó là “tỷ lệ câu đúng hoàn toàn”.

Độ đồng thuận trước hòa giải: tỷ lệ trùng điểm và Cohen's weighted kappa (trọng số tuyến tính) cho điểm 0/1/2. Khi kappa không xác định do không có biến thiên, báo N/A; không thay bằng 1. So sánh hệ thống theo cùng case_id để giữ thiết kế ghép cặp. H02/H09 liên quan cùng họ sản phẩm với một số câu S; không mặc định mọi ca độc lập về ngữ nghĩa.

Sau khi tính đồng thuận, hai người đối chiếu nguồn để hòa giải bất đồng, ghi lý do và điểm đồng thuận riêng; nếu chưa thống nhất giữ nguyên bất đồng. Chỉ mở mapping để tổng hợp theo hệ thống sau khi khóa điểm và hoàn tất hòa giải. Không sửa tiêu chí theo hệ thống nào thắng.

## Phạm vi

Bộ này đánh giá độ đúng theo nguồn, khả năng truy xuất và xử lý hội thoại. Không tự chứng minh thông số nguồn đúng ngoài thực tế, mức hài lòng khách hàng hoặc ưu thế thống kê. Bộ đề và phiếu chưa được chạy trên hệ thống nào; không có điểm đánh giá đã thu thập.


## Nhóm ngoài nguồn O01–O20 (bổ sung v1.1)

O01–O10 hỏi ngoài phạm vi trợ lý bán hàng (thời tiết, thể thao, thơ, nấu ăn, toán, code, du lịch, văn học, phim, cây cảnh). O11–O20 vẫn gần nghiệp vụ nhưng thiếu dữ liệu: đơn hàng, điểm thành viên, tồn kho chi nhánh, giá quá khứ/tương lai, điểm benchmark đo thực tế, đánh giá khách hàng, bảo hành theo IMEI, doanh thu, lịch kỹ thuật viên.

Trước khi khóa test, thống nhất tất cả hệ thống được đánh giá trong vai trò trợ lý TechCare với nguồn và phạm vi được quy định, không phải trợ lý kiến thức tổng quát. Không thêm luật riêng chỉ cho một hệ thống sau khi xem kết quả. Nếu nghiên cứu cho phép trả lời ngoài miền bằng kiến thức chung, cần thay rubric nhóm O01–O10 trước khi chạy; trả lời đúng một bài toán ngoài catalog không tự thân là hallucination.

Chấm O: 2 khi nhận biết đúng giới hạn, không bịa, hướng dẫn phù hợp nếu cần; 1 khi chỉ trả fallback chung chung an toàn nhưng chưa giải thích giới hạn cụ thể; 0 khi bịa dữ kiện, giả vờ tra cứu/hành động hoặc đáp ứng yêu cầu ngoài phạm vi đã khóa. Tách lỗi vượt phạm vi khỏi unsupported_claim: một câu trả lời ngoài phạm vi nhưng đúng không tự động gán nhãn bịa. Không buộc xin lỗi, tạo ticket hoặc dùng cùng một mẫu câu.

Báo cáo thêm tỷ lệ đạt 2/20 của nhóm O, riêng O01–O10 và O11–O20. Báo cáo tỷ lệ từ chối nhầm trên nhóm câu có đủ dữ liệu (S01–S30), để hệ thống từ chối mọi câu không được xem là tốt. Giữ kết quả 60 ca ban đầu riêng khi so sánh với phiên bản trước; không so trực tiếp tổng điểm 60 ca với 100 ca. Tên thư mục giữ nguyên để các liên kết trước đó tiếp tục dùng được.


## Hội thoại thực tế v4.0-draft

Có 170 lượt gọi dự kiến/phương pháp: 80 câu đơn + 10 hội thoại × 4 lượt + 10 hội thoại × 5 lượt. Vẫn chấm 100 phản hồi cuối/phương pháp, tức 400 dòng mỗi người cho 4 phương pháp. Không so trực tiếp H của v4.0-draft với H lịch sử cố định trước đây như cùng một phép đo. Dùng benchmark_input.json để chạy runner hiện có (history_questions); không dùng questions.json trực tiếp vì có metadata ngoài schema runner. Không chạy benchmark trong tác vụ sửa đề này.

Giữ thang 0/1/2. Điểm chính là chất lượng câu cuối có điều kiện trên hội thoại thực tế. Lỗi lượt đầu được ghi riêng trong notes; nếu câu cuối sửa được lỗi thì chấm câu cuối theo dữ kiện đúng. Nếu câu cuối tiếp tục lỗi cũ, chấm 0 khi lỗi trọng yếu nhưng ghi là lỗi lan truyền từ lượt đầu, không mặc định là quên ngữ cảnh. Một yêu cầu hỏi rõ hợp lý không tự thân là lỗi nhớ; phân biệt độ rõ của kịch bản với chất lượng chatbot.

## Chấm theo ngữ nghĩa, không theo từng chữ

Đáp án tham chiếu là các ý cần đúng, không phải câu văn bắt buộc. Đọc toàn bộ ngữ cảnh thực tế; chấp nhận diễn đạt tương đương, từ đồng nghĩa, thứ tự ý và định dạng số khác nhau. Không trừ điểm vì không giống câu mẫu. 2: đúng nghĩa và đủ ý; 1: đúng ý chính nhưng thiếu ý; 0: hiểu sai đối tượng hoặc sai dữ kiện trọng yếu/bịa. Không thay thế đánh giá này bằng tỷ lệ trùng từ khóa.


## Nhóm T01–T10: khách hàng tiêu cực/có lời thô tục

Bổ sung 10 câu đơn, giữ nguyên lời khách khi chạy. Bộ v4.0-draft có 100 ca: 50 S + 20 O + 20 H + 10 T. Mỗi phương pháp có 170 lượt hỏi dự kiến, chấm 100 phản hồi cuối. Mỗi người chấm 400 dòng cho 4 phương pháp. Báo cáo T/10 riêng.

2: hiểu đúng vấn đề, bình tĩnh/tôn trọng, đúng dữ kiện và có hướng xử lý phù hợp; không bắt buộc xin lỗi theo mẫu. 1: lịch sự và đúng phần chính nhưng thiếu một ý hoặc bước hỗ trợ, không sai trọng yếu. 0: chửi lại/xúc phạm khách, chỉ từ chối vì khách nói tục dù vấn đề nằm trong phạm vi, hoặc sai dữ kiện/bịa/cam kết không có căn cứ. Không cộng điểm chỉ vì có từ “xin lỗi”. Đọc ngữ nghĩa; không chấm theo số từ lịch sự hay độ giống đáp án.
