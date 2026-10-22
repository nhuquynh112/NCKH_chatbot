# Demo web B0/B1/B2/P để chụp mục 5.5

Demo chỉ chạy local development. Backend riêng không import `app.main`, không
đăng ký API khách hàng, không seed/rebuild dữ liệu và không dùng PostgreSQL.
Trang demo không gắn `ChatProvider` và dùng khóa localStorage riêng.

**Lưu ý bản demo 20/10:** bản vá website đã đổi source hash toàn bộ app. Study
16/10 không chạy trực tiếp bằng source hiện tại; harness sẽ chặn theo protocol.
Không sửa hash để bỏ qua kiểm tra. Dùng runtime snapshot trước vá đã xác minh trên
máy gốc với source hash trùng protocol, hoặc tạo study
mới theo [hướng dẫn tái lập](REPRODUCING_RESEARCH.md). Kết quả mới cần lưu riêng.

## Khởi chạy

Terminal PowerShell thứ nhất:

```powershell
# Chạy từ gốc bản clone; study phải là bộ snapshot gốc đã có đủ database/run.
$study = Read-Host 'Đường dẫn đầy đủ tới study benchmark gốc'
$demoWork = Join-Path $env:TEMP 'TechCareWebDemo'
Set-Location backend
& .\.venv\Scripts\python.exe -B local_demo.py --study $study --work-dir $demoWork --port 8012 --frontend-port 5174
```

Terminal PowerShell thứ hai:

```powershell
# Terminal mới, bắt đầu tại gốc project:
Set-Location frontend
$env:VITE_BENCHMARK_DEMO='true'
$env:VITE_BENCHMARK_API_URL='http://127.0.0.1:8012'
npm.cmd run dev -- --host 127.0.0.1 --port 5174 --strictPort
```

Mở **http://127.0.0.1:5174/benchmark-demo**. Không cần chạy backend website ở
cổng8000 hoặc dịch vụ7B. Ollama cần có `qwen2.5:3b` và `nomic-embed-text`.

Study cần có `package/test_inputs.jsonl` và snapshot của lượt benchmark gốc.
Harness còn cần `P_results.jsonl` ở thư mục cha và database P/TC01 trong study,
đồng thời source hash phải khớp. GitHub không chứa toàn bộ thư mục này; thiếu
snapshot thì báo lỗi, không tự lấy raw responses để giả lập. Xem
[tái lập nghiên cứu](REPRODUCING_RESEARCH.md) nếu chỉ có bản clone.

## Chụp bốn hình

1. Chọn **Phiên demo mới** để bắt đầu một nhóm lượt thử riêng. Không xóa dữ liệu
   đã lưu. Bản ghi cũ trong cùng phiên vẫn mở lại được khi tải lại trang.
2. Chọn TC01, TC11, TC18 hoặc TC21 trong **Ca kiểm thử**. Câu hỏi được đọc từ
   `study/package/test_inputs.jsonl`, không nhập lại hoặc chỉnh sửa trên web.
3. Chọn B0/B1/B2/P và **Chạy phương pháp**, hoặc dùng **Chạy cả4 phương pháp**.
   Backend thực thi từng lựa chọn; không lấy lại đáp án benchmark để giả lập.
4. Chờ cả bốn khung hoàn tất; chụp các khung A=B0, B=B1, C=B2, D=P, cùng mã TC,
   câu hỏi và phản hồi. Không cắt bỏ phần trả lời sai.
5. Với TC21, hai lượt lịch sử user/assistant tự được nạp từ dữ liệu gốc và hiển
   thị nhãn **lịch sử gốc**. Chỉ câu cuối được đưa qua pipeline. Không có lời gọi
   model để sinh lại lượt assistant trong fixture, không nhập nó như user.

## Pipeline và tính trung thực

Backend tái sử dụng `benchmark.worker.run_case`,
`benchmark.methods.build_method` và `method_settings`. Hai hook riêng của harness
chỉ mở database snapshot có sẵn ở chế độ chỉ đọc và quan sát class/preflight.
Không sửa `RuleMethod`, `PlainLlmMethod`, `BasicRagMethod`, `RagMethod` hoặc luật.

Mô hình gốc, embedding, prompt, tham số sinh, corpus, chỉ mục, lịch sử và mốc
snapshot được đối chiếu với study. Model/embedding khác digest hoặc chỉ mục không
đúng thì báo chưa sẵn sàng, không thay model/nguồn âm thầm. P+FT không được chấp
nhận ở API này. B0 nhận history nhưng luật hiện có không diễn giải nó.

Đây là **lượt chạy web mới**, không phải phản hồi lịch sử của benchmark cũ và
không thay các điểm chất lượng đã báo cáo. Lỗi được hiển thị; câu trả lời giữ
nguyên từ worker, không áp dụng bộ làm sạch câu trả lời của API website.

## Nơi lưu và khôi phục

Mỗi lần khởi động backend tạo thư mục `web-UTC-UUID` mới dưới
thư mục đã truyền bằng `--work-dir` (ví dụ `$demoWork`). Terminal in đường dẫn chính xác. Thư mục chứa
`demo_config.json`, bản sao corpus/database chỉ đọc và
`sessions/<session-id>/<run-id>/{request.json,response.json,worker.log,result.json}`.
Không ghi tệp vào study hoặc lịch sử khách hàng. B1 không mở database.

Trong cùng lần chạy backend, tải lại trang mở phiên demo đã lưu. Backend khởi
động lại tạo instance mới; các tệp instance cũ vẫn được giữ. Lịch sử khách hàng
thông thường không được nhập hoặc xuất vào demo này.

## Tắt và hoàn nguyên

Dừng hai terminal bằng Ctrl+C. Mở frontend bình thường không có
`VITE_BENCHMARK_DEMO=true` thì route demo không được bật; production build luôn
tắt route. Backend website, `.env`, Word và dữ liệu benchmark không đổi.
Chỉ file `frontend/src/App.jsx` nối route development mới; bỏ nhánh demo và
các file demo mới là hoàn nguyên phần tích hợp.

Kiểm thử ranh giới: trong backend chạy
`.\.venv\Scripts\python.exe -B -m unittest tests.test_local_demo -v`.
