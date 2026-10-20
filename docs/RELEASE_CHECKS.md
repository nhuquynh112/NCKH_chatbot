# Kiểm tra đóng gói release — 20/10/2026

**Trạng thái: chưa đủ điều kiện phát hành; chưa commit/push.** Nhánh `chatbot-v1`, HEAD vẫn là `1cef995f95b3b315037e2102fd82488e621e0370`. Remote đã truy cập được và đang cùng HEAD tại lần kiểm tra; không force push, không sửa lịch sử.

## Những thay đổi đã thực hiện

- Viết lại README tiếng Việt, hướng dẫn cài từ đầu, model/embedding, SQLite/PostgreSQL, URL đã đối chiếu và giới hạn của readiness.
- Gom sáu tài liệu audit/evaluation/dataset vào `docs/history/`, giữ nguyên byte. Không sửa nội dung các bảng nghiên cứu hoặc mục 5.6. Không sửa Word.
- Chuyển bộ dựng báo cáo tạm khoảng 54,7 MB ra ngoài repo; giữ bản sao của bốn file mẫu/rỗng không được sử dụng trước khi bỏ khỏi project. Không xóa database, `.env`, Chroma runtime hoặc `.local` chứa study đầy đủ.
- Đóng gói bộ 24 câu gốc, answer key tách riêng và nguồn; sao chép nguyên byte 96 raw responses chính, 24 phản hồi P+FT, điểm AI sơ bộ và các kiểm tra liên quan. SHA256 từng file nguồn nằm trong `research/chapter5-24/SOURCE_MANIFEST.json`.
- Giữ nguyên trọng số, profile và cơ chế chọn `techcare-support:3b-v1`; giữ embedding `nomic-embed-text` và khả năng chuyển về base 3B. Giữ code B0/B1/B2/P/P+FT, ablation, training và serving 7B.
- Script dùng work directory portable; mỗi lượt test có thư mục riêng, không ghi đè báo cáo cũ. Thêm chẩn đoán tải đồng thời; không nới tiêu chí đạt.
- Sửa `frontend/.env.example` từ biến không được code đọc sang `VITE_API_BASE_URL`, có `/api`. Không sửa `.env` đang dùng.
- Vá lockfile trong dải phiên bản khai báo: Axios 1.20.0, source-map-js 1.2.2 và các dependency có thể cập nhật an toàn. Không chạy `npm audit fix --force` hoặc chuyển Tailwind lên major mới.
- Compose không chứa mật khẩu PostgreSQL cố định và chỉ bind loopback; không chạy Docker hay thay database thật.

## Kiểm thử đã chạy

Môi trường: Windows, Python 3.14.3, Node 24.14.0, npm 11.9.0, PowerShell 7.6.5 và Windows PowerShell 5.1, Git LFS 3.6.1, Ollama 0.40.6.

| Nhóm | Kết quả và giới hạn |
|---|---|
| Backend unit/integration | **142/142 đạt**; gồm API, bảo mật, catalog/RAG, serving, benchmark, ablation và ranh giới demo. Một phần có mock; không phải 142 lượt LLM thật. |
| Hồi quy hội thoại | **225/225 đạt** trên database thử. |
| API và tải | Lượt đầu **4/5 API, 15/16 tải**, có OperationalError; chưa đủ log để quy chính xác nguyên nhân. Hai workflow tiếp theo **5/5 API, 16/16 tải**. Giữ nguyên lần lỗi, không tuyên bố đã sửa lỗi đồng thời. |
| FAQ/RAG cố định | **32/32 đạt**, `generative_cases=0`; không chứng minh chất lượng LLM. Một số query embedding ở lượt online có fallback lexical. |
| Ollama offline | **32/32 đạt**, dùng cổng không sẵn sàng theo test; không phải LLM vẫn hoạt động khi offline. |
| Frontend | Lint và production build đạt, gồm lượt chạy Windows PowerShell 5.1 sau cập nhật lockfile. |
| Cài mới backend | Tạo venv mới ngoài repo, cài requirements thành công; `pip check` không báo xung đột. |
| Cài mới frontend | `npm ci` đạt với lockfile đã vá trong bản sao sạch. |
| Seed và rebuild | Bản sao sạch có **53 sản phẩm, 30 FAQ, 195 đoạn index**, semantic enabled; không rebuild dữ liệu repo thật. |
| Khởi chạy HTTP | FastAPI `/docs`, `/health`, `/ready` và Vite `/products`, `/faqs` đều 200 trên cổng thử 8020/5175; đã dừng riêng hai tiến trình thử. Không coi HTTP 200 là kiểm tra chất lượng sinh. |
| Model 3B | Kích thước/SHA256 khớp profile; `-VerifyOnly` đạt cả PowerShell 7 và 5.1; LFS pointer bị từ chối đúng. Không thực hiện lại import ghi vào tag Ollama đang dùng, nên chưa xác nhận toàn bộ nhánh import của installer mới bằng một lần cài model sạch. |
| Git LFS | `fsck --objects --pointers` đạt; GGUF và adapter là trọng số thật, vẫn được LFS quản lý. Chưa tải lại 2 GB qua một máy khác nên không cam kết quota/băng thông LFS từ đó. |
| Nghiên cứu | Tạo study mới từ package đã đóng gói thành công; validate bộ M1–M4 20 câu đạt. Không chạy lại benchmark/đổi số liệu lịch sử. |
| Artifact 7B | `model_serving.server --check-only` đạt hash và provenance của checkpoint/adapter gốc ngoài repo; không nạp GPU hoặc đo lại P+FT. |
| Git/file | `git diff --check` đạt tại lần rà soát; Word, `.env`, profile và code thuật toán benchmark được đối chiếu với bản trước khi dọn. |

Các cảnh báo thư viện test về Starlette/httpx và kết nối SQLite chưa đóng hết vẫn được lưu; không sửa test để ẩn cảnh báo. Workflow 5.1 xử lý stderr theo exit code nên warning không bị tính nhầm thành test failure.

## Lỗi chặn phát hành đã xác minh

Trên **bản cài sạch**, gửi API câu `RAM dual-channel nghĩa là gì?`:

1. `/ready` báo `ready`, đúng model `techcare-support:3b-v1`; embedding thật có phản hồi và retriever có 195 đoạn.
2. Lời gọi Ollama `/api/chat` chạm deadline **16 giây**, kể cả sau warm-up. API trả fallback và tạo ticket; đây không phải câu trả lời LLM thành công. Log runtime xác nhận request bị hủy; model vẫn nạp trên GPU. Không đủ bằng chứng để quy nguyên nhân cho riêng model, driver hoặc bản Ollama.
3. Chẩn đoán tách riêng, chỉ trong bản sao với `AI_RESPONSE_TIMEOUT_SECONDS=90`, thực sự gọi đúng model và nhận phản hồi sau khoảng **14,74 giây**, mode `llm+rag`. Đây không phải kiểm thử cấu hình mặc định; trạng thái cache/warm-up khác nên không chứng minh tăng timeout là lời giải.
4. Phản hồi chẩn đoán lại nói về Google Pixel 9 Pro XL thay vì giải thích đúng trọng tâm RAM dual-channel. Retrieval đã lấy các đoạn Pixel trong context. Giữ nguyên output; không chấm thành đạt hoặc chỉnh câu trả lời để chụp ảnh.

Vì vậy, model không bị mất/corrupt, nhưng **chưa xác nhận được một bản demo RAG/LLM đáng tin cậy với cấu hình mặc định trên môi trường hiện tại**. Đóng gói không tự sửa routing, prompt, timeout production, model hoặc thuật toán P để vượt bài thử. Cần xử lý nguyên nhân latency và chọn context, rồi chạy lại smoke API/LLM thật trước khi quyết định commit/push.

## Bảo mật và dependency

- Quét 254 object văn bản trong lịch sử Git: không thấy token HF/GitHub/AWS hoặc private key theo các pattern đã dùng; không thấy `.env` thật trong lịch sử. Đây là kiểm tra có phạm vi, không phải chứng nhận tuyệt đối không còn secret.
- File dự kiến phát hành không chứa database, log khách hàng, venv/node_modules hoặc `.env` thật. Giá trị demo admin/JWT/PostgreSQL có trong lịch sử cũ được xác định là giá trị mẫu; không rewrite lịch sử.
- Npm audit tổng sau vá vẫn **7 cảnh báo: 5 high, 2 moderate**, thuộc nhóm Tailwind/build dependencies. Audit `--omit=dev` báo **0**. Không gọi toàn bộ repository là sạch lỗ hổng; hướng nâng Tailwind major cần kiểm thử giao diện riêng.
- Giữ giấy phép model/data; không tự gán giấy phép mới cho mã nguồn. Docker chưa có trên máy nên Compose chưa được kiểm thử runtime. RTX 3050 laptop và clone tải LFS trên máy khác chưa được thử.

## Bằng chứng và bước tiếp theo

Toàn bộ log, bản trước khi sửa, file đã chuyển và bản demo sạch nằm ở:

```text
D:\NCKH\Codex\release_20261020_9f04b2
  preexisting_manifest.json, preexisting.patch, before/
  file_moves.json, removed_templates/, archived_report_tools/
  tests-20261020T120627Z-b891f866/   # lượt tải chưa đạt
  tests-20261020T121607Z-445a3734/   # workflow PowerShell 7 đạt
  tests-20261020T122713Z-63ac8ddd/   # workflow Windows PowerShell 5.1 đạt
  clean_demo/, clean_install.log, clean_rebuild.log, clean_http_checks.json
  clean_demo_smoke.json, clean_demo_smoke_warm.json
  llm_long_timeout_diagnostic.json, model_warmup.json
  npm_audit.json, npm_audit_after.json, npm_runtime_audit.json
  git_history_security.json, lfs_fsck.log, 7b_artifact_check.json
```

Trước phát hành: sửa và kiểm tra lỗi timeout/ngữ cảnh trong phạm vi được duyệt; đánh giá các cảnh báo build; kiểm tra nhánh remote lại. Sau đó rà diff và stage riêng phần release, **loại file Word đã có sửa trước tác vụ**; chỉ commit/push khi các kiểm tra bắt buộc đạt. Hiện chưa tạo commit, tag hoặc push nên chưa có commit hash release để clone.
