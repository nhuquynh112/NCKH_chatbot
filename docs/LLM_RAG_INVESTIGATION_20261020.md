# Điều tra và sửa đường LLM/RAG website – 20/10/2026

## Kết luận và phạm vi

Đã sửa đường website trên nhánh `chatbot-v1`, HEAD vẫn là `1cef995f95b3b315037e2102fd82488e621e0370`. Chưa commit, tag hoặc push. Các ca nghiệm thu mới đạt **15/15**, trong đó có **4 completion LLM thật**. Không cộng các kết quả này vào benchmark nghiên cứu.

Lỗi RAM được xử lý bằng kiểm tra bằng chứng: corpus hiện tại **không có định nghĩa dual-channel** nên trả thiếu dữ liệu và tạo ticket, không lấy catalog Pixel để giải thích. Chưa bổ sung kiến thức để chatbot tự giải thích khái niệm đó. Câu hỏi kỹ thuật có nguồn phù hợp vẫn gọi model thật và trả lời đúng nội dung nguồn.

Đề xuất: sử dụng bản sửa cho demo local có giám sát trên máy đã kiểm thử; **tiếp tục chặn phát hành chính thức** cho tới khi xác nhận trên máy demo đích và xử lý các mục đóng gói còn mở trong báo cáo release trước. Chưa có số đo cold-start đầy đủ hoặc kết quả trên laptop RTX 3050. Không tuyên bố độ chính xác tổng quát từ 15 ca chẩn đoán.

Thư mục bằng chứng mới, hoàn toàn ngoài repo:

`D:\NCKH\Codex\rag_investigation_20261020_c872e4`

Các file trọng yếu:

- `acceptance_criteria.json`: tiêu chí đã lưu trước khi triển khai.
- `retrieval_before.json`, `api_before.json`: truy xuất và API trước sửa; đủ query, điểm thành phần, metadata, nội dung, context, prompt và output thô.
- `corpus_and_identity_before.json`, `index_validation.json`: corpus, identity và kiểm tra index.
- `api_after_verified.json`: 15 lượt API cuối, input/history, context thực tế, prompt, options, raw Ollama, mode, ticket và timing.
- `assessment_verified.json`: kiểm tra theo tiêu chí định trước; không sửa raw output hoặc metric nghiên cứu.
- [API_RAW_OUTPUTS.md](D:/NCKH/Codex/rag_investigation_20261020_c872e4/API_RAW_OUTPUTS.md): toàn bộ câu hỏi/phản hồi API và completion Ollama nguyên văn.
- `transport_timing_before.json`, `transport_timing_after.json`: đối chứng transport.
- `tests-20261020T130953Z-a56cde72/`: sáu nhóm regression cuối.
- `preservation_check.json`, `gguf_integrity.json`, `benchmark_code_preservation.json`: kiểm tra bảo toàn.

Các lần dò trung gian cũng được giữ riêng (`api_after.json`, `api_after_final.json`); bảng dưới dùng **`api_after_verified.json` của code cuối**.

## 1. Trạng thái và kiến trúc đã xác minh

Luồng website: frontend gửi `POST /api/chat/messages` → router kiểm tra chủ phiên → `services.chat_service` đọc lịch sử, bảo vệ thông tin nhạy cảm, xử lý ticket/FAQ → `AIService.query` → service AI → rule/catalog hoặc retrieval/context/LLM → postcheck → lưu assistant message và tạo ticket khi cần. Lượt điều tra dùng đúng endpoint FastAPI bằng TestClient với SQLite riêng; không kết nối PostgreSQL của người dùng.

Sau sửa, `AIService` tạo `WebsiteChatService`. Các câu hỏi nghiệp vụ, sản phẩm được nêu rõ, bảo mật và hỗ trợ tiếp tục đi qua `_ask` hiện có. Nhánh giải thích kỹ thuật chung có bước xét bằng chứng trước khi dựng context. Request Ollama của website nằm trong scope có deadline và I/O có thể hủy.

Các pipeline nghiên cứu vẫn tạo service gốc trong `app.rag.chat_service`; B0/B1/B2/P/P+FT và metric không sửa. **Website sau vá không được gọi là kết quả P lịch sử.**

| Thành phần | Giá trị kiểm chứng |
|---|---|
| Model được gọi | `techcare-support:3b-v1` |
| Digest Ollama | `35ce2ecac067a190a224a8ddb75af219bb158b344fca0b5a0214d1b24000207c` |
| Embedding | `nomic-embed-text`, 768 chiều; digest `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f` |
| Prefix | `search_query:` cho query; chữ ký index `nomic-embed-text\|nomic-task-prefix-v1` |
| Nguồn RAG | `knowledge_base.md`, `product_catalog_extended.md`, `faq_curated.json` trong `backend/rag_data`; rule/catalog còn đọc dữ liệu nghiệp vụ hiện có |
| Index | JSON, **195 đoạn**, `is_current=True`; không rebuild |
| Options sinh | `temperature=0`, `num_predict=384`, `num_ctx=4096`, `repeat_penalty=1.0`, `keep_alive=30m` |
| Máy đo | RTX 3060 12 GB, driver 617.14; Ollama 0.40.6; Python 3.14.3 |

Không train lại hoặc thay model. GGUF vẫn có 1.929.902.496 byte; SHA-256 `87710c00e7b1da9c873d2ba0ddc89e89eb24075f81ebfba55ed527832ecc3b18`, khớp profile.

## 2. Nguyên nhân RAG và bằng chứng trước sửa

### Query, index và ranking

Query thực sự gửi embedding:

```text
search_query: RAM dual-channel nghĩa là gì?
ram dual-channel nghia la gi
```

Chuẩn hóa giữ nguyên ý nghĩa, không thêm tên Pixel. Embedding trả đúng kiểu/768 chiều. Đối chiếu embedding tài liệu với vector đã lưu cho các đoạn Laptop đồ họa, Pixel và Laptop lập trình có cosine gần 1 (khoảng 0,999999), index khớp corpus. Không có bằng chứng stale index hoặc gán nhầm vector. Kiểm tra này không chứng minh chất lượng ngữ nghĩa của embedding với mọi câu hỏi.

BM25 đầu bảng là `COD nghĩa là sao?` (7,3382), sau đó Pixel 9 Pro XL (4,7267). Semantic đầu bảng là MSI Immerse GH30 V2 (0,6522), Gigabyte G5 (0,6452), MSI Raider GE68 HX (0,6355). Hai bộ xếp hạng không trùng nhau và đều chưa có bằng chứng dual-channel.

Sau trộn và điều chỉnh domain, API chọn:

| Hạng | ID / tài liệu | Cosine | BM25 thô | Hybrid | Điều chỉnh | Điểm cuối |
|---|---|---:|---:|---:|---:|---:|
| 1 | doc_165 – Pixel 9 Pro XL 16GB/512GB | 0,6293 | 4,7267 | 0,6223 | +0,04 | 0,6623 |
| 2 | doc_164 – Pixel 9 12GB/256GB | 0,6304 | 1,8428 | 0,5304 | +0,04 | 0,5704 |
| 3 | doc_117 – Gigabyte G5 | 0,6452 | 1,6106 | 0,5269 | +0,04 | 0,5669 |
| 4 | doc_026 – Điện thoại chơi game | 0,6242 | 1,7600 | 0,5224 | +0,04 | 0,5624 |
| 5 | doc_023 – Laptop đồ họa | 0,6163 | 1,7737 | 0,5184 | +0,04 | 0,5584 |

Retriever chuẩn hóa BM25 bằng `s/(s+3)`, trộn `0,60*vector + 0,40*lexical` rồi cộng domain adjustment. Các token phổ biến/khớp chuỗi con có thể tăng hạng; điểm vượt ngưỡng 0,38 chỉ biểu thị độ gần, chưa xác nhận tài liệu giải thích đúng khái niệm. Cả năm đoạn trên được đưa vào context.

Corpus không có chuỗi `dual-channel`/`dual channel`. NVMe xuất hiện trong 19 đoạn và OLED trong 16 đoạn, nhưng đó không phải các định nghĩa được hỗ trợ. Sáu câu chẩn đoán trước sửa còn cho thấy OLED truy xuất cả chính sách/giờ mở cửa; câu hỏi kiến thức lạ truy xuất bảo hành/ticket. Lỗi không chỉ xuất hiện ở một câu RAM.

### Context, prompt và đầu ra

System prompt yêu cầu chỉ dùng context, nhưng luôn nối thêm quy tắc `ACTIVE PRODUCT` ngay cả khi không có sản phẩm đang hỏi. Đây là yếu tố có thể làm câu hỏi khái niệm bị gán cho SKU; chưa thực hiện ablation để quy riêng tác động của quy tắc này.

Bằng chứng trực tiếp là context chứa catalog không giải thích dual-channel, sau đó model trả nguyên văn:

```text
RAM dual-channel ở đây chỉ đề cập đến cấu hình của sản phẩm Google Pixel 9 Pro XL 16GB/512GB. Mình chưa có thông tin cụ thể về bảo hành hoặc lỗi sản phẩm liên quan đến cấu hình này. Mình có thể chỉ ra thông số RAM 16GB của mẫu này. Nếu cần thông số khác, mình cần mẫu sản phẩm cụ thể để kiểm tra.
```

API trước sửa hoàn tất sau **5.672,84 ms**, mode `llm+rag`. Postcheck số liệu/URL/thao tác không phát hiện diễn giải sai chủ đề này vì số RAM có trong context. Do đó, chỉ nhắc model bám nguồn hoặc chỉ kiểm tra số liệu chưa đủ.

## 3. Bản sửa website

1. Nhận diện có giới hạn các câu giải thích/đặc điểm kỹ thuật và các chủ đề/thuật ngữ được hỏi; giữ các cụm định danh như dual-channel, không rút còn mỗi RAM.
2. Giữ ranking hybrid hiện có làm tập ứng viên; xét thêm ứng viên BM25 để không mất nguồn khớp chính xác ngoài top semantic. Không xóa Pixel hoặc đổi dữ liệu/index.
3. Chỉ nhận bằng chứng kỹ thuật có chủ đề yêu cầu; loại catalog SKU cho câu khái niệm chung. Với định nghĩa, yêu cầu câu giải thích về chính thuật ngữ đó. Với nhiều chủ đề, nhận nhiều nguồn để phủ đủ từng chủ đề; thiếu một chủ đề thì trả thiếu bằng chứng.
4. Giữ bộ lọc dòng prompt injection, ngưỡng 0,38 và giới hạn 3.000 ký tự/đoạn, 10.000 ký tự/context của retriever hiện có. Kiểm tra lại độ phủ sau cắt context. Không chèn đoạn không liên quan để đủ top-k.
5. Nếu không có bằng chứng, không gọi model để đoán; context rỗng, fallback và ticket. Nếu có nguồn, dùng system prompt nền hiện có với context kỹ thuật, không nối quy tắc active SKU không phù hợp. Giữ postcheck và luật chuyển nhân viên.
6. Lỗi transport truyền lên `AIService` để trả `ai_unavailable`; không thông báo nhầm rằng corpus thiếu kiến thức khi nguồn thực ra có nhưng dịch vụ hỏng.

Đây là cơ chế xét bằng chứng bằng heuristic, không phải bộ phân loại ngữ nghĩa tổng quát. Từ ngữ/kiểu hỏi chưa nhận diện được vẫn có thể đi qua đường cũ; cần mở rộng đánh giá trước phát hành rộng. Không hardcode định nghĩa hoặc câu trả lời riêng cho RAM.

## 4. Timeout và transport

Giữ nguyên timeout: frontend Axios **30 giây**, deadline AI backend **25 giây**, chat HTTP **16 giây**, embedding **8 giây**. Context/output budget không thay đổi. Không đặt production thành 90 giây.

Đối chứng cùng `GET /api/tags`, không sinh token:

| Transport | Ba lượt, ms |
|---|---|
| urllib, kết nối mới tới localhost | 2.118,64 / 2.075,91 / 2.063,48 |
| urllib, kết nối mới tới 127.0.0.1 | 42,08 / 31,01 / 29,54 |
| httpx async, client mới tới localhost | 289,05 / 279,75 / 278,66 |

Tra cứu địa chỉ trả IPv6 trước IPv4; chi phí phụ thuộc địa chỉ/transport tái hiện ổn định, phù hợp với chờ kết nối fallback trên Windows. Không quy toàn bộ lỗi lịch sử cho GPU hoặc khẳng định đã chứng minh chính xác mọi bước TCP.

API RAM trước sửa: embedding HTTP 2.121,75 ms; retrieval tổng 2.155,26 ms (đã gồm embedding); dựng context 13,93 ms; chat HTTP 3.147,17 ms. Riêng Ollama báo generation tổng 1.089,70 ms, load 11,12 ms, prompt 1.142 token/323,50 ms, sinh 88 token/747,67 ms. Phần chờ HTTP lớn hơn rõ rệt thời gian suy luận của model.

Transport mới dùng async HTTP, xử lý IPv6/IPv4 và tái sử dụng kết nối trong một request. Chat đọc stream để đo first-token và đóng kết nối khi hủy; nội dung các chunk được ghép nguyên văn, không sửa câu trả lời. HTTPS vẫn xác minh chứng chỉ. Không thêm retry.

Mỗi request có deadline chung. Budget I/O không vượt timeout riêng hoặc thời gian còn lại. Khi outer timeout/caller cancellation xảy ra, scope hủy future và coroutine I/O, chờ đóng response/client, chặn dispatch mới của worker cũ. Test loopback xác nhận socket đóng và chỉ có một POST, kể cả chờ thêm sau hủy. `to_thread` không thể cưỡng bức dừng mọi lệnh Python trong worker; worker có thể hoàn tất phần CPU ngắn nhưng không được gửi thêm I/O trong scope đã hủy.

`/ready` chỉ kiểm tra DB/tên model; không chứng minh model đã warm hoặc có thể sinh token. Không thêm lời gọi sinh câu trả lời vào readiness. Không phát hiện lời gọi model lặp từ tạo tiêu đề; tiêu đề vẫn được xử lý cục bộ.

Timeout 16 giây trong báo cáo release cũ **không tái hiện ở baseline mới**: cùng câu RAM hoàn tất 5,67 giây nhưng sai. Bằng chứng transport giải thích một phần latency, không đủ để quy toàn bộ timeout cũ cho một nguyên nhân. Không dừng/unload Ollama dùng chung để ép cold-start; cũng chưa xác minh việc GPU dừng sinh trên server sau mọi lần disconnect. Bằng chứng hủy phía ứng dụng và đóng socket có trong test mới.

## 5. Nghiệm thu với model/API thật

Đã warm cả chat lẫn embedding trước ba lượt cuối, `/api/ps` ghi nhận cả hai model nạp. RAM-W1 là lượt API đầu sau warm-up nên vẫn có chi phí khởi tạo đường API; không phải full cold-start. Không chạy benchmark song song khi đo lượt cuối.

| Ca | Context được nhận | Completion LLM thật | Mode | Ticket mới | API, ms |
|---|---|---:|---|---|---:|
| RAM-W1 | Rỗng | 0 | fallback | Có | 1.033,43 |
| RAM-W2 | Rỗng | 0 | fallback | Có | 695,19 |
| RAM-W3 | Rỗng | 0 | fallback | Có | 710,01 |
| TECH-W1 | doc_023 – Laptop đồ họa | 1 | llm+rag | Không | 1.254,45 |
| TECH-W2 | doc_023 | 1 | llm+rag | Không | 914,67 |
| TECH-W3 | doc_023 | 1 | llm+rag | Không | 941,29 |
| NVME | Rỗng | 0 | fallback | Có | 660,95 |
| OLED | Rỗng | 0 | fallback | Có | 719,61 |
| MULTI | doc_023 + doc_022 – Laptop lập trình | 1 | llm+rag | Không | 1.432,85 |
| PRICE | Catalog nghiệp vụ | 0 | rule+rag | Không | 269,22 |
| UNKNOWN | Rỗng | 0 | fallback | Có | 721,04 |
| HISTORY-1 | AirPods Pro 2 USB-C | 0 | rule+rag | Không | 271,96 |
| HISTORY-2 | Cùng sản phẩm từ lịch sử | 0 | rule+rag | Không | 285,96 |
| OFFLINE | doc_023 qua BM25, không sinh được | 0 | ai_unavailable | Có | 4.460,92 |
| TIMEOUT-REAL | doc_023 qua BM25, không sinh được | 0 | ai_unavailable | Có | 481,13 |

OFFLINE dùng URL cổng không có dịch vụ trong harness riêng. TIMEOUT-REAL vẫn gửi tới Ollama thật nhưng cố ý giảm timeout client của riêng phép thử xuống **50 ms**, phục hồi sau lượt thử; embedding và một chat request đều hết hạn, không có completion. Đây là kiểm tra nhánh lỗi, không phải tái hiện model mất 16 giây ở cấu hình mặc định. Mỗi ca âm có một lần thử embedding rồi một lần thử chat; không phải retry cùng yêu cầu và không có dispatch sau đóng scope.

### Timing từng giai đoạn

Đơn vị ms. Retrieval khác = retrieval/admission tổng trừ embedding HTTP để không cộng trùng. `Khác/API` là phần còn lại gồm DB/FAQ/ticket/serialization/khởi tạo; chưa phân rã tiếp. Với rule, không có context gửi LLM hoặc chat request.

| Ca | Tiền xử lý AI | Embedding HTTP | Retrieval khác | Context | Chat HTTP | Khác/API |
|---|---:|---:|---:|---:|---:|---:|
| RAM-W1 | 48,89 | 318,55 | 131,98 | 0 | 0 | 534,01 |
| RAM-W2 | 50,18 | 323,65 | 49,62 | 0 | 0 | 271,74 |
| RAM-W3 | 42,38 | 331,49 | 48,86 | 0 | 0 | 287,28 |
| TECH-W1 | 48,08 | 342,58 | 71,00 | 16,89 | 598,22 | 177,68 |
| TECH-W2 | 42,34 | 278,21 | 56,63 | 0,86 | 343,46 | 193,17 |
| TECH-W3 | 53,76 | 267,92 | 61,31 | 1,04 | 353,80 | 203,46 |
| MULTI | 42,52 | 281,69 | 61,28 | 1,50 | 817,39 | 228,47 |
| OFFLINE | 40,61 | 2.050,99 | 30,58 | 0,92 | 2.051,49 | 286,33 |
| TIMEOUT-REAL | 77,19 | 63,23 | 30,55 | 0,88 | 54,82 | 254,46 |

Timing của cả 15 ca, first-token và metadata Ollama nằm trong JSON gốc. Median RAM warm 710,01 ms là **thời gian fallback**, không phải tốc độ sinh định nghĩa. Median TECH warm 941,29 ms có completion thật. Không dùng hai nhóm này để tuyên bố tốc độ model tăng theo tỷ lệ; câu hỏi/context/output và cache khác nhau.

### Output nguyên văn

Ba TECH-W1/W2/W3 hỏi `Trong tài liệu, laptop đồ họa có những đặc điểm kỹ thuật nào?`, cả ba completion Ollama giống nhau:

```text
Laptop đồ họa có những đặc điểm kỹ thuật sau:

- GPU rời.
- RAM lớn.
- Màn hình màu sắc chính xác.
- SSD dung lượng cao.
```

MULTI hỏi `So sánh đặc điểm laptop đồ họa và laptop lập trình trong tài liệu.`, completion Ollama:

```text
Laptop đồ họa:

- GPU rời.
- RAM lớn.
- Màn hình màu sắc chính xác.
- SSD dung lượng cao.

Laptop lập trình:

- RAM tối thiểu 16GB.
- SSD tốc độ cao.
- CPU nhiều nhân.
- Màn hình Full HD trở lên.
```

RAM-W1/W2/W3 là fallback của hệ thống, **không phải lời LLM sinh**:

```text
Mình chưa có tài liệu kỹ thuật đủ liên quan để giải thích nội dung này trong dữ liệu hiện tại. Mình có thể tạo ticket để nhân viên TechCare kiểm tra và tư vấn chính xác hơn cho bạn.
```

PRICE trả `Sạc Anker Nano 65W: giá 990.000 VND; bảo hành 18 tháng.` HISTORY-1 hỏi giá AirPods Pro 2 USB-C, sau đó HISTORY-2 hỏi `Mẫu đó bảo hành bao lâu?`; service nhận đúng lịch sử `user → assistant thật → user`, trả bảo hành **12 tháng của AirPods Pro 2 USB-C**. Không nhập lời assistant thành user. Toàn bộ output nguyên văn của 15 lượt và lịch sử DB được giữ trong các file bằng chứng dẫn ở đầu báo cáo.

## 6. Regression và bảo toàn

| Kiểm tra | Kết quả cuối |
|---|---|
| Unit/integration | **163/163**, gồm 21 test mới; có fixture/mock, không phải 163 completion thật |
| Hội thoại/canonical catalog | **225/225** |
| API / concurrent | **5/5 / 16/16** |
| FAQ online / offline | **32/32 / 32/32**, cả hai `generative_cases=0` |
| Frontend lint/build | Đạt; API contract không đổi |
| API thật mới | **15/15** theo tiêu chí đã khóa; 4 completion thật, các ca khác là rule/fallback/lỗi dịch vụ |
| Model/index | GGUF khớp SHA/kích thước; 195 đoạn còn current; không rebuild |
| Bảo toàn | 234 file baseline được đối chiếu; chỉ `backend/app/services/ai_service.py` thay đổi trong số đó; không file baseline nào mất |

Các test mới bao gồm: listing RAM không đủ để giải thích dual-channel; NVMe/OLED thiếu định nghĩa; định nghĩa đúng chủ đề; hai chủ đề dùng hai nguồn; thiếu một chủ đề phải abstain; không lấy định nghĩa từ đoạn injection hoặc phần bị cắt; không vượt ngưỡng context; giữ route bảo mật/nghiệp vụ/lịch sử; P dùng factory gốc; giữ options và nội dung stream; timeout/caller cancel/outer deadline đóng I/O, không retry hoặc dispatch muộn.

Có các lượt test ban đầu thất bại, log vẫn được giữ. Một fixture deadline 150 ms kết thúc trước khi HTTP khởi tạo xong nên assertion đợi socket đã mở không hợp lệ; fixture cuối dùng 1 giây để kiểm tra hủy **kết nối đang mở**. Không tăng timeout production. Bộ cuối đã chạy đủ sáu nhóm và đạt. Cảnh báo Starlette TestClient/SQLite ResourceWarning vẫn còn trong test, không che log.

Lượt unit đầu thiếu override DB đã tạo mới `backend/techcare.db` lúc chạy test; tệp này được xác minh thời điểm tạo và chuyển nguyên vẹn ra `initial-unit-only.db` trong thư mục điều tra. PostgreSQL của người dùng không bị truy cập. Các lượt còn lại đặt DB/temp/log ngoài repo bằng runner hiện có.

### Các file thay đổi riêng trong tác vụ này

- `backend/app/services/ai_service.py`: nối factory website và scope request; giữ các sửa có trước.
- `backend/app/rag/website_service.py` (mới): xét bằng chứng/context kỹ thuật riêng cho website.
- `backend/app/website_transport.py` (mới): transport async có deadline, hủy I/O và observer tùy chọn.
- `backend/tests/test_website_rag.py` (mới): 21 regression mới.
- `docs/LLM_RAG_INVESTIGATION_20261020.md` (mới): báo cáo này.

Giữ nguyên Word, `.env`, model profile, trọng số, dữ liệu/index, code RAG gốc, benchmark/model_serving/training và các báo cáo cũ so với trạng thái đầu điều tra. Git index vẫn rỗng; không commit/tag/push. Observer mặc định tắt, không tự ghi prompt/lịch sử khách hàng ra log; phép đo chỉ ghi dữ liệu tổng hợp giả lập để thử API.

## 7. Demo benchmark cũ và giới hạn còn lại

Protocol benchmark băm toàn bộ `app/`, `benchmark/`, `model_serving/`. Code trước vá khớp study, code hiện tại khác đúng ba file đường website nên `verify_study` **chặn chạy study cũ từ repo hiện tại**. Đây không phải thay thuật toán P; không sửa hash/protocol để bỏ qua rào chắn.

Đã tạo runtime tách riêng từ backup trước vá, kiểm tra nguyên byte với protocol gốc và chuẩn bị thành công snapshot demo đọc-only cho TC01/TC11/TC18/TC21:

`D:\NCKH\Codex\rag_investigation_20261020_c872e4\frozen_benchmark_runtime\backend`

Kết quả xác minh nằm trong `frozen_demo_verification.json`. Chưa chạy lại 16 lượt model B0/B1/B2/P hoặc chụp giao diện ở lượt điều tra này. Nếu cần khởi động lại demo gốc, dùng terminal PowerShell riêng:

```powershell
Set-Location 'D:\NCKH\Codex\rag_investigation_20261020_c872e4\frozen_benchmark_runtime\backend'
& 'C:\Python314\python.exe' -B local_demo.py --study 'D:\NCKH\Codex\comparison24_P_20261016T065655Z_e0611f3d\study' --work-dir 'D:\NCKH\Codex\rag_investigation_20261020_c872e4\frozen_demo_work' --port 8012 --frontend-port 5174
```

Frontend demo và bốn phương pháp dùng hướng dẫn hiện có trong `LOCAL_BENCHMARK_DEMO.md`; P của demo gốc vẫn là P nghiên cứu, dùng base `qwen2.5:3b`. Không dùng nó để minh họa bản vá website với `techcare-support:3b-v1`.

Các giới hạn phải giữ khi trình bày kết quả:

- Chưa đo full cold-start và chưa thử laptop RTX 3050; số đo thuộc máy RTX 3060 hiện tại.
- Chưa có định nghĩa dual-channel/NVMe/OLED được duyệt trong corpus; trả thiếu dữ liệu là hành vi nghiệm thu, không phải bổ sung tri thức thành công.
- Bộ xét bằng chứng là heuristic và các câu kiểu mới có thể không đi vào nhánh kỹ thuật; bốn completion đúng không chứng minh hết hallucination.
- TestClient gọi đúng endpoint/service/DB và Ollama thật, nhưng chưa kiểm tra lại bằng trình duyệt/uvicorn qua TCP hoặc nhiều khách sinh token đồng thời trong lượt này.
- Chưa tái hiện được đầy đủ nguyên nhân timeout lịch sử hoặc chứng minh GPU hủy mọi generation sau disconnect.
- Những mục đóng gói còn mở ở báo cáo release trước, gồm cài model sạch và cảnh báo dependency build, không được coi là đã xử lý bởi bản vá RAG.
