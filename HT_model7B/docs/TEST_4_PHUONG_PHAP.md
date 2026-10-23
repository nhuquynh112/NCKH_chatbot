# Test trên web lần lượt B0, B1, B2 và P

Dùng bản `HT_model7B`. B1/B2/P gọi **Qwen2.5-7B-Instruct FP16 gốc**, không fine-tune; B0 không gọi LLM. P+FT không thuộc bốn phương pháp này. Các lượt test mới do nhóm tự chấm, không phải kết quả 24 câu cũ.

Lượt web mới lấy snapshot từ `backend/rag_data_150`: 150 sản phẩm CellphoneS đang sử dụng, từ 151 link nguồn thu thập 23/10/2026; đã loại một mẫu có thông số không nhất quán. B0/B2/P dùng cùng snapshot này; B1 không dùng RAG. Kho `rag_data` và kết quả 24 câu cũ được giữ nguyên. Phải tạo workspace mới khi đổi corpus; không dùng kết quả mới như kết quả của study cũ.

Bộ [80 ca v1.1](evaluation/blind_60_20261023/HUONG_DAN.md) được giữ nguyên từ commit `c621cb8`, sử dụng snapshot **151 sản phẩm** trước khi gỡ Alldocube. Manifest nguồn của bộ đó không khớp catalog 150 hiện tại; riêng S48 và H10 còn tham chiếu Alldocube. Muốn tái lập đúng bộ đề đã có, dùng code/corpus tại commit đó trong checkout riêng. Nếu chấm catalog 150 mới, nhóm cần duyệt lại các ca bị ảnh hưởng và khóa phiên bản đề/đáp án/manifest mới trước khi chạy; không trộn hai phiên bản kết quả. Không đưa câu hỏi hoặc đáp án vào RAG.

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

Mở **http://127.0.0.1:5174/benchmark-demo**. API test: http://127.0.0.1:8012/docs. Không cần backend website cổng 8000 để test bốn phương pháp. Website thường ở 8000/5173 là luồng khác, không dùng thay kết quả B0/B1/B2/P.

## 3. Test 50 câu ở từng phương pháp

1. Chọn **B0**. Nhập câu đầu vào ô “Câu hỏi”, giữ mã `TEST01`, bấm **Chạy phương pháp**. Đợi kết quả rồi bấm **Câu tiếp theo**. Làm đến `TEST50`.
2. Chọn **B1**. Trong **Câu đã lưu**, chọn lại `TEST01` đến `TEST50`, mỗi câu bấm **Chạy phương pháp**. Không cần gõ lại; không bấm “Phiên demo mới” giữa các phương pháp.
3. Lặp lại với **B2**, rồi **P**. Không cần tắt backend khi đổi phương pháp. Kết quả lưu riêng theo mã câu/phương pháp/lượt chạy.
4. Sau mỗi phương pháp có thể tải CSV để sao lưu. Đủ 50 mã câu cho mỗi phương pháp tương ứng ít nhất **200 lượt chạy**; chạy lại tạo thêm lượt, không ghi đè kết quả trước.

Mặc định chỉ hiện khung chat của phương pháp chọn. Bật **Hiện cả 4 khung** để chụp đối chiếu. “Chạy cả 4 phương pháp” chạy tuần tự cùng một đầu vào, là lựa chọn phụ; không chạy song song tranh GPU.

Cùng mã câu phải giữ nguyên câu hỏi và lịch sử cho bốn phương pháp; server từ chối nếu sửa nội dung đã lưu. Muốn sửa bộ test, dùng mã câu mới hoặc phiên mới và ghi rõ phiên bản. Câu độc lập không tự nối lịch sử câu trước. Kết quả hiển thị status, pipeline, model và có thực sự gọi LLM hay không.

### Hai người test trên hai máy

Mỗi người clone/cập nhật cùng commit của nhánh `chatbotv1-demo`, cài cùng model FP16 và embedding rồi chạy hai terminal như trên trên máy của mình. Tạo workspace mới để dùng corpus `rag_data_150`; không mở lại workspace catalog cũ. Chốt trước cùng 50 mã câu, nguyên văn câu hỏi và lịch sử; chia phương pháp để chạy hoặc chạy độc lập rồi đối chiếu. Mỗi máy xuất CSV và giữ raw JSON riêng.

Kiểm tra thông tin cấu hình trên web: dataset `rag_data_150`, 299 tài liệu, model `qwen2.5:7b-instruct-fp16` và precision `F16`. B0 không gọi LLM; B1 không đọc catalog/RAG nên không được bổ sung tài liệu cho riêng B1. Kết quả chất lượng cần chấm theo cùng tiêu chí; thời gian phản hồi giữa hai máy khác phần cứng không phải phép so sánh tốc độ có kiểm soát. Một backend test chỉ nhận một lượt suy luận tại một thời điểm; hai người không chạy đồng thời trên cùng backend.

### Câu nhiều lượt

Mở **Lịch sử đầu vào**, dán lịch sử gốc với đúng vai trò, theo cấu trúc:

```json
[
  {"role": "user", "content": "Nội dung lượt khách hàng đã có"},
  {"role": "assistant", "content": "Nội dung phản hồi thực tế đã có"}
]
```

Đây chỉ là ví dụ schema, không phải hội thoại để chấm. Dùng lịch sử thật trong bộ test; không nhập lời assistant thành user hoặc tạo đáp án thay thế. Lịch sử được lưu cùng mã câu và dùng lại nguyên vẹn cho bốn phương pháp. Câu cuối cần chấm nhập vào ô “Câu hỏi”; câu độc lập để lịch sử `[]`.

## 4. Lưu và chấm điểm

- **Tải CSV chấm điểm**: có câu hỏi, history, answer nguyên bản, status, mode, LLM flag, thời gian, model/digest, nguồn; `score_0_2`, `reviewer`, `notes` để trống cho nhóm.
- **Kết quả JSON**: toàn bộ lượt chạy của phiên. File `request.json`, `response.json`, `result.json`, `worker.log` nằm trong `output\sessions\<session>\<run>`.
- Giữ raw JSON làm bằng chứng; chấm trên bản sao CSV. Nếu chạy lại, ghi rõ lượt được chọn và lý do, tránh chọn riêng phản hồi thuận lợi.
- Đối chiếu đáp án/nguồn nhóm duyệt riêng: 2 = đúng và đủ tiêu chí; 1 = đúng một phần, còn thiếu; 0 = sai trọng tâm/sai dữ kiện/bịa thông tin. Timeout/not_ready/error ghi riêng là lỗi thực thi; không coi là trả lời đúng. B0 `no_rule_match` vẫn cần chấm theo rubric.
- Kiểm tra tự động không phải điểm chất lượng. Giữ cùng 50 câu, corpus, model, history, timeout; công bố phần cứng, trạng thái cold/warm, cách chấm. Nếu cần hai người chấm độc lập, xuất hai bản CSV; không gọi điểm tự chấm là đánh giá độc lập.

## 5. Dừng và mở lại

Ctrl+C để dừng từng terminal. Để tiếp tục đúng thư mục test đã in, tại `backend`:

```powershell
& .\.venv\Scripts\python.exe comparison_demo.py --resume 'C:\duong-dan-thuc-te\web-...'
```

Thay bằng `output` thật; chạy frontend như bước 2, dùng cùng trình duyệt để mở lại phiên. Không xóa localStorage khi test. Không có `--resume` sẽ tạo workspace mới; dữ liệu cũ vẫn trên đĩa. Nếu code/corpus/model đổi, hệ thống có thể từ chối tiếp tục để tránh trộn cấu hình; giữ kết quả cũ và bắt đầu lượt mới.

Nếu lỗi kết nối: kiểm tra Ollama, backend 8012 và frontend 5174. Nếu cổng bận, dừng tiến trình test cũ của mình. Deadline mặc định **120 giây/ca**, áp dụng như nhau cho bốn phương pháp; đây là cấu hình test thủ công mới, không phải benchmark 24 câu cũ. Thiếu RAM/VRAM hoặc quá hạn phải ghi lỗi, không âm thầm chuyển Q4/3B. Không đưa 50 câu/đáp án vào RAG hoặc huấn luyện.
