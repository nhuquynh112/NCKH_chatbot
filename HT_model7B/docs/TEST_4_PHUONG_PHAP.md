# Test trên web và chấm ẩn danh

Dùng bản `HT_model7B`. B1/B2/P gọi **Qwen2.5-7B-Instruct FP16 gốc**, không fine-tune; B0 không gọi LLM. P+FT không thuộc bốn phương pháp này. Các lượt test mới do nhóm tự chấm, không phải kết quả 24 câu cũ.

Lượt web mới lấy snapshot từ `backend/rag_data_150`: 150 sản phẩm CellphoneS đang sử dụng, từ 151 link nguồn thu thập 23/10/2026; đã loại một mẫu có thông số không nhất quán. B0/B2/P dùng cùng snapshot này; B1 không dùng RAG. Kho `rag_data` và kết quả 24 câu cũ được giữ nguyên. Phải tạo workspace mới khi đổi corpus; không dùng kết quả mới như kết quả của study cũ.

Bộ [100 ca v4.0-draft](evaluation/blind_60_20261023/HUONG_DAN.md) đã đồng bộ catalog **150 sản phẩm**, gồm đề, đáp án, manifest và hai phiếu Excel. S48/H10 dùng Teclast 128GB và biến thể 256GB chưa được xác nhận. Nhóm cần duyệt và khóa bản dự thảo trước khi chạy; tạo lượt mới, không trộn kết quả phiên bản cũ. Không đưa câu hỏi hoặc đáp án vào RAG.

`comparison_demo.py` mặc định mở **chế độ chấm mù**: một khung chat, chọn Trợ lý A/B/C/D. Ánh xạ được xáo trộn riêng cho mỗi phiên và lưu ở backend; không suy ra phương pháp từ chữ A/B/C/D. Trang, API trả kết quả và CSV cho người chấm không có tên phương pháp, model, pipeline, nhánh luật, cờ gọi LLM hoặc thời gian xử lý. Phản hồi được giữ nguyên. Trạng thái hoàn tất `no_rule_match` được hiển thị chung là `ok`; trạng thái gốc vẫn có trong file điều phối, điểm chất lượng luôn để người chấm nhập.

Người điều phối giữ terminal và thư mục output; người chấm chỉ dùng giao diện/CSV ẩn danh. Đây không phải cơ chế chống người có quyền đọc source/file trên máy. Văn phong, nội dung và thời gian chờ thực tế vẫn có thể giúp nhận ra hệ thống; không tuyên bố mù tuyệt đối. Những phản hồi đã xem kèm nhãn trước đây cần ghi nhận giới hạn này.

## 1. Chuẩn bị một lần

Cần Git/Git LFS, Python, Node.js và Ollama. Môi trường đã dùng kiểm tra: Python 3.14.3, Node.js 24.14.0. Vite yêu cầu Node `^20.19.0 || >=22.12.0`. FP16 khoảng 15,24 GB; máy ít VRAM cần chia tải CPU/GPU và có thể chậm. Chưa kiểm thử laptop RTX 3050.

PowerShell, tại nơi muốn lưu source:

```powershell
git lfs install
git clone --branch chatbotv1-demo https://github.com/nhuquynh112/NCKH_chatbot.git
Set-Location NCKH_chatbot\HT_model7B
python -m venv backend\.venv
& .\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
Set-Location frontend
npm.cmd ci
Set-Location ..
ollama pull qwen2.5:7b-instruct-fp16
ollama pull nomic-embed-text
ollama show qwen2.5:7b-instruct-fp16
```

`ollama show` phải ghi quantization `F16`. Giữ Ollama hoạt động. Trọng số 7B do Ollama tải riêng; Git chứa code, corpus, manifest và hướng dẫn. Clone thông thường còn lấy weight 3B qua LFS để bảo toàn bản cũ; nếu chỉ cần 7B, đặt `$env:GIT_LFS_SKIP_SMUDGE='1'` trước clone và `Remove-Item Env:GIT_LFS_SKIP_SMUDGE` sau clone.

Không cần PostgreSQL, `.env`, seed website, rebuild RAG hoặc dữ liệu trên máy tác giả. Chế độ test tự sao chép corpus đi kèm và tạo **database snapshot mới trong thư mục test ngoài repository**. Worker chỉ mở snapshot đó ở chế độ đọc; không sử dụng database/lịch sử khách hàng.

## 2. Mở hai terminal

Terminal 1, tại `NCKH_chatbot\HT_model7B\backend`:

```powershell
& .\.venv\Scripts\python.exe comparison_demo.py
```

Terminal in đường dẫn `output` dạng `...\TechCare\comparison_test\web-...`. Giữ đường dẫn này để mở lại kết quả. Muốn tự chọn nơi lưu ngoài repository:

```powershell
& .\.venv\Scripts\python.exe comparison_demo.py --work-dir D:\TechCareTest
```

Terminal 2, tại `NCKH_chatbot\HT_model7B\frontend`:

```powershell
npm.cmd run test:methods
```

Mở **http://127.0.0.1:5174/benchmark-demo**. Chế độ ẩn danh không mở `/docs`, JSON cấu hình model hoặc kết quả đầy đủ cho người chấm. Không cần backend website cổng 8000. Website thường ở 8000/5173 là luồng khác, không dùng thay kết quả các phương pháp benchmark.

## 3. Test trên giao diện ẩn danh

1. Chọn một mã **Trợ lý**. Nhập đúng mã ca và câu hỏi từ bộ đề, bấm **Gửi câu hỏi**. Trang không tự nạp hay chạy bộ 100 ca.
2. Chọn **Câu tiếp theo** để nhập ca tiếp theo, hoặc sửa mã thành mã ca thật của bộ đề. Câu độc lập dùng lịch sử `[]`.
3. Đổi trợ lý và chọn các câu đã lưu để chạy cùng câu hỏi. Không bấm **Phiên đánh giá mới** giữa các trợ lý vì phiên mới có bảng quy đổi khác. Cùng một mã phải giữ nguyên câu hỏi; lịch sử thực tế được khóa riêng cho từng trợ lý.
4. Bấm **Tải phiếu CSV ẩn danh** để lưu phản hồi và chấm; giữ `system_id`, `run_id` và file gốc để điều phối ghép đúng phương pháp sau khi khóa điểm. Không tự gán A=B0 hoặc nhập điểm vào dòng Excel ngẫu nhiên.

Người chấm chỉ thấy một khung, không có nút hiện cả bốn phương pháp hoặc liên kết raw JSON. Giao diện đối chiếu cũ vẫn dành riêng cho người điều phối: thêm `--coordinator` khi khởi động backend trong workspace mới. Chế độ đó hiện tên phương pháp/model và mở API docs, không dùng để chấm mù.

Câu độc lập không tự nối lịch sử câu trước. Với ca H của bộ v4.0-draft, nhập từng câu theo kịch bản; dùng mã riêng cho mỗi lượt, rồi truyền đúng các cặp user/assistant thực tế của chính trợ lý đó trong **Lịch sử đầu vào** khi hỏi tiếp. Không chèn đáp án mẫu. Trang không tự sinh hay nối hội thoại H; người điều phối cần giữ log và xác định phản hồi cuối để chấm.

### Hai người test trên hai máy

Mỗi người clone/cập nhật cùng commit của nhánh `chatbotv1-demo`, cài cùng model FP16 và embedding rồi chạy hai terminal như trên trên máy của mình. Tạo workspace mới để dùng corpus `rag_data_150`; không mở lại workspace catalog cũ. Chốt cùng mã ca và kịch bản người dùng; các ca H dùng lịch sử thật riêng của từng trợ lý theo giao thức đã khóa. Nếu hai người cùng chấm độ đồng thuận thì cả hai phải nhận cùng phản hồi thực tế; hai máy tự sinh hai bộ phản hồi khác nhau không tạo thành cặp điểm cho cùng phản hồi. Mỗi máy xuất CSV và giữ raw JSON riêng.

Người điều phối kiểm tra `demo_config.json`: dataset `rag_data_150`, 299 tài liệu, model `qwen2.5:7b-instruct-fp16`, precision `F16`. Không gửi file này cho người chấm. Mã trợ lý của hai phiên/máy không mặc định cùng phương pháp; ghép bằng bảng quy đổi riêng sau khi khóa điểm. Kết quả chất lượng cần chấm theo cùng tiêu chí; thời gian phản hồi giữa hai máy khác phần cứng không phải phép so sánh tốc độ có kiểm soát. Một backend test chỉ nhận một lượt suy luận tại một thời điểm.

### Câu nhiều lượt

Mở **Lịch sử đầu vào**, dán lịch sử gốc với đúng vai trò, theo cấu trúc:

```json
[
  {"role": "user", "content": "Nội dung lượt khách hàng đã có"},
  {"role": "assistant", "content": "Nội dung phản hồi thực tế đã có"}
]
```

Đây chỉ là ví dụ schema, không phải hội thoại để chấm. Với bộ v4.0-draft dùng lịch sử do chính trợ lý đang chọn đã trả lời, giữ đúng vai trò; không nhập lời assistant thành user hoặc tạo đáp án thay thế. Đổi trợ lý không tự mang lịch sử trợ lý trước sang. Câu cuối cần chấm nhập vào ô “Câu hỏi”; câu độc lập để lịch sử `[]`.

## 4. Lưu và chấm điểm

- **CSV ẩn danh**: mã trợ lý và `system_id`, mã câu, `run_id`, câu hỏi, history, answer nguyên bản, status; `score_0_2`, `reviewer`, `notes` để trống cho nhóm. Không có metadata nhận diện pipeline.
- **Chỉ người điều phối giữ**: bảng `output\sessions\<session>\mapping_RIENG.json` quy đổi `system_id`/nhãn sang phương pháp. File `request.json`, `response.json`, `result.json`, `worker.log` trong `output\sessions\<session>\<run>` vẫn giữ nguyên phương pháp/pipeline/model để kiểm chứng, không phục vụ qua API người chấm.
- **Excel có sẵn** không tự nhận kết quả từ web. Mã ẩn danh của CSV mới không phải mã ẩn danh đã tạo trong Excel. Người điều phối dùng bảng quy đổi/file raw để điền đúng phản hồi theo phương pháp và mã ca vào file điều phối Excel, rồi chuyển sang R1/R2 theo hướng dẫn Excel; không đoán hoặc đổi ngẫu nhiên mapping cũ.
- Giữ raw JSON làm bằng chứng; chấm trên bản sao CSV. Nếu chạy lại, ghi rõ lượt được chọn và lý do, tránh chọn riêng phản hồi thuận lợi.
- Đối chiếu đáp án/nguồn nhóm duyệt riêng: 2 = đúng và đủ tiêu chí; 1 = đúng một phần, còn thiếu; 0 = sai trọng tâm/sai dữ kiện/bịa thông tin. Timeout/not_ready/error ghi riêng là lỗi thực thi; không coi là trả lời đúng. B0 `no_rule_match` vẫn cần chấm theo rubric.
- Kiểm tra tự động không phải điểm chất lượng. Giữ cùng bộ đề, corpus, model, giao thức hội thoại, timeout; công bố phần cứng, trạng thái cold/warm, cách chấm. Nếu cần hai người chấm độc lập, xuất hai bản CSV của cùng bộ phản hồi; không gọi điểm tự chấm là đánh giá độc lập.

## 5. Dừng và mở lại

Ctrl+C để dừng từng terminal. Để tiếp tục đúng thư mục test đã in, tại `backend`:

```powershell
& .\.venv\Scripts\python.exe comparison_demo.py --resume 'C:\duong-dan-thuc-te\web-...'
```

Thay bằng `output` thật; chạy frontend như bước 2, dùng cùng trình duyệt để mở lại phiên. Không xóa localStorage khi test. Không có `--resume` sẽ tạo workspace mới; dữ liệu cũ vẫn trên đĩa. Workspace cũ trước bản chấm mù cần được giữ riêng và tạo lượt mới; không chuyển qua lại chế độ trong workspace đã lưu. Nếu code/corpus/model đổi, hệ thống có thể từ chối tiếp tục để tránh trộn cấu hình.

Nếu lỗi kết nối: kiểm tra Ollama, backend 8012 và frontend 5174. Nếu cổng bận, dừng tiến trình test cũ của mình. Deadline mặc định **120 giây/ca**, áp dụng như nhau cho bốn phương pháp; đây là cấu hình test thủ công mới, không phải benchmark 24 câu cũ. Thiếu RAM/VRAM hoặc quá hạn phải ghi lỗi, không âm thầm chuyển Q4/3B. Không đưa câu hỏi/đáp án đánh giá vào RAG hoặc huấn luyện.
