# Audit chatbot TechCare — 14/10/2026

Nhánh làm việc: `frontend-chat-integration`, working tree ban đầu sạch. Audit dựa trên code, PostgreSQL hiện tại (chỉ đọc sản phẩm/FAQ), chạy thử local và kiểm thử trên SQLite riêng. Không thay `.env`, migration, dữ liệu khách hàng, model chính; không commit/push.

## Kiến trúc thực tế

- Frontend React/Vite, chat widget và trang hội thoại; API axios timeout 30 giây. Giao diện được giữ nguyên.
- FastAPI + SQLAlchemy; `.env` hiện tại chọn PostgreSQL, không phải SQLite mặc định trong README. Database có 53 sản phẩm, 2 FAQ active. Không có bảng đơn hàng/tồn kho hay kết nối vận chuyển.
- `/api/chat/messages` lưu bản tin đã che dữ liệu nhạy cảm, lấy lịch sử trong cùng phiên, gọi AIService, lưu câu trả lời và tạo/cập nhật ticket. Quyền visitor/JWT và contract response giữ nguyên.
- Ollama local: model chính `qwen2.5:3b` (1,9 GB), embedding `nomic-embed-text:latest` (274 MB). Đã tải thêm `qwen2.5:7b` Q4_K_M (4,7 GB) làm ứng viên benchmark; chưa thay model chính. RTX 3060 12.288 MiB, RAM khoảng 15,9 GiB, CPU i5-10400F. Không gọi cloud LLM.
- Pipeline kết hợp luật nghiệp vụ, FAQ và retrieval. JSON là vector store đang dùng; Chroma tùy chọn, chưa cài/chưa chạy kiểm thử tích hợp ở máy này.
- Index mới: 195 tài liệu, vector 768 chiều, cùng model và task-prefix, thay nguyên tử. Các kết quả audit/pipeline này được đo trước fine-tuning.

## Lỗi xác minh và sửa

| Mức | Vấn đề/nguồn bằng chứng | Nguyên nhân | Thay đổi |
|---|---|---|---|
| Cao | Giá DB có thể bị file hiệu chỉnh ghi đè: `product_enrichment.py` và `ProductCatalog._load_database_products` | Merge cả `price`/`warranty_months` từ bản xác minh cũ khi đọc DB | Giữ trường bán hàng hiện tại; kiểm thử giá/bảo hành khác bản hiệu chỉnh |
| Cao | Catalog không còn active vẫn có thể hồi sinh từ JSON | Kiểm tra `not products` gộp DB trống và DB lỗi | Phân biệt `[]` và `None`, gắn nhãn bản xuất khi DB lỗi |
| Cao | `SAFE01` baseline vẫn trả giá dù có yêu cầu tiết lộ prompt | Trả dữ kiện sản phẩm trước kiểm tra an toàn | Chặn injection/hỗ trợ/chuyển người trước mọi FAQ hoặc dữ kiện |
| Cao | Hai FAQ thật trong DB cam kết 0%/15 phút và đổi mọi hàng lỗi miễn phí 30 ngày | Dữ liệu seed không có nguồn, FAQ exact trả thẳng | Nhận diện đúng hai nội dung seed cũ và không dùng chúng để trả lời; không sửa bản ghi DB; thay seed cho DB mới |
| Cao | Model làm theo lệnh giả trong tài liệu: raw benchmark trả giá 1 VND thay 399.000 | Prompt đơn thuần chưa bảo vệ được model nhỏ | Lọc dòng chỉ dẫn trong context, chặn yêu cầu ở router, kiểm tra số/URL sau generation; không tuyên bố giải quyết mọi injection |
| Trung bình | FAQ paraphrase và câu gồm phí + thời gian giao thất bại | Chỉ exact được trả trực tiếp; match cả từ trong đáp án, score cộng 2–3 quá mạnh | Matcher dựa câu hỏi/keyword, tách chủ đề, ưu tiên FAQ live phù hợp; 30 FAQ gốc có điều kiện và câu hỏi tiếp theo |
| Trung bình | FAQ xuất file nhưng không có trong index | `knowledge_paths` chỉ gồm KB/catalog | Đưa FAQ biên tập JSON vào source docs; FAQ quản trị đọc mỗi lượt, không đợi embedding |
| Trung bình | Không phân biệt model/prefix khi tái sử dụng vector | Index không lưu embedding signature; Nomic không có task prefix | Thêm prefix query/document, signature và kiểm tra chiều; rebuild 195 tài liệu bằng Ollama |
| Trung bình | Model/index lỗi có thể làm mọi câu hỏi mất AIService | Init tự rebuild trước khi router được dùng | Init nhẹ; lexical nguồn mới khi index thiếu/cũ; luật/FAQ vẫn chạy |
| Trung bình | Hỏi so sánh có giá có thể chỉ trả mẫu đầu | `product_fact_answer` trước comparison | Route comparison trước single-product fact |
| Trung bình | “Mẫu đó” sau danh sách có thể chọn nhầm, “mẫu khác” mất ngân sách | Chọn sản phẩm cuối và chỉ đọc tiền ở câu hiện tại | Hỏi lại khi mơ hồ; giữ ngân sách từ lượt user trước; không dùng giá assistant làm ngân sách |
| Trung bình | Tư vấn chuột có thể lẫn bàn phím/phụ kiện khác | Category DB là phụ kiện, bộ lọc so danh mục quá hẹp rồi giữ toàn catalog | Dùng SKU của đúng nhóm/sản phẩm phụ kiện phù hợp |
| Trung bình | Không chuyển người khi khách yêu cầu trực tiếp | Chỉ lỗi/fallback tạo ticket | Intent chuyển người; tra ticket theo session được phép, không đọc phiên khác |
| Trung bình | Có thể giữ OTP đứng trước nhãn hoặc số liên hệ thứ hai | Regex che một số điện thoại, OTP một chiều | Che toàn bộ số phù hợp, OTP đảo thứ tự; dùng nội dung đã che khi chuyển vào AI/ticket issue |
| Trung bình | Model timeout không dừng worker ngay, tiêu đề gọi thêm LLM | Socket 120s trong khi API chờ 25s; gọi model tạo tiêu đề | Socket query/generation có giới hạn, tối đa 2 generation, output/context hữu hạn, tiêu đề xác định |
| Trung bình | Database lỗi trả 500/chi tiết, `/ready` chỉ kiểm tra server Ollama | Không handler SQLAlchemy; chưa kiểm tra model đã cài | HTTP 503 chung, readiness kiểm tra đủ hai model |
| Thấp | Lint quét cả `node_modules`, báo rất nhiều cảnh báo phụ thuộc | Script `oxlint` không giới hạn đường dẫn | Chỉ lint source/config dự án; build giữ nguyên |
| Đánh giá | 225/225 cũ được gọi là “độ chính xác” dù chủ yếu là luật | Thiếu bộ FAQ/RAG, mode, nguồn và baseline độc lập | Bộ cố định 32 câu, retrieval 11 câu, raw model 8 câu; tách tỷ lệ đạt tiêu chí và năng lực LLM |

## Chưa giải quyết / giới hạn

- Không có live order/stock: chatbot tiếp nhận yêu cầu, không tự tạo trạng thái giao hàng. Ticket status chỉ trong phiên hiện tại.
- Database thật giữ nguyên 2 FAQ seed; chatbot bỏ qua đúng hai nội dung thiếu căn cứ. Trang quản trị vẫn hiển thị chúng cho đến khi nhóm sửa bằng chức năng quản trị. Bản FAQ mới đã có hiệu lực trong chatbot mà không cần sửa DB.
- Chính sách, giá và SLA là demo, cần doanh nghiệp duyệt trước sử dụng thật. Mốc hỗ trợ 24 giờ được diễn đạt là tham khảo demo, không cam kết thực tế.
- Các laptop thiếu SKU và số liệu benchmark vẫn chỉ có cấu hình catalog; chưa kiểm tra lại toàn bộ nguồn hãng trong lượt này.
- Không thay embedding model; chưa có bằng chứng đánh giá tiếng Việt đủ lớn. Hybrid/BM25 cải thiện trên tập nhỏ, không chứng minh tối ưu toàn cục.
- Raw Qwen 3B vẫn có lỗi injection/thiếu dữ kiện. 7B xử lý tốt hơn câu injection và so sánh ở bộ nhỏ, nhưng cùng đạt 6/8 theo kiểm tra từ khóa và chậm hơn. Hệ thống dựa luật, dữ liệu và fallback để giảm lỗi; chưa có bảo đảm an toàn mọi câu ngoài mẫu.
- Chroma, load dài hạn và tranh chấp đồng thời trên cùng một session chưa có benchmark đầy đủ. 16 yêu cầu tải thử dùng các phiên riêng.
- Nếu DB không khả dụng ngay lúc import app, các thao tác khởi tạo bảng ban đầu vẫn có thể làm backend không khởi động; handler 503 áp dụng khi dịch vụ đã chạy.
- Chưa đo hài lòng người dùng thật. Sau giai đoạn audit đã khảo sát 200 train CSConDa, lọc 46 mẫu, chia 37/9 rồi thêm 133 train tổng hợp. 3B đã train GPU hai epoch và tích hợp thành `techcare-support:3b-v1`. Cấu hình chạy đầu giảm điểm trên 21 câu; cấu hình điều chỉnh đạt 12/12 tiêu chí ở tập mới, base 10/12. Giữ cả kết quả chưa tốt và giới hạn tập tổng hợp trong `CHATBOT_EVALUATION_REPORT.md`. `.env` và dữ liệu khách hàng giữ nguyên.

Theo yêu cầu đã làm rõ, model 3B đã xác nhận, adapter, dữ liệu đã lọc, mã huấn luyện và bằng chứng cần cho đề tài được giữ trong project. Môi trường GPU, checkpoint nguồn/cache, log và thử nghiệm chưa chọn vẫn ở `D:\NCKH\Codex`; database thử và build thử không cần thiết đã được xóa.
