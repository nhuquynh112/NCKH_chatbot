# Thực nghiệm có kiểm soát trên 60 ca mới

Module này chỉ dùng cho nghiên cứu, không được website import. Không thay đổi B0/B1/B2/P/P+FT, model mặc định, database khách hàng, điểm hoặc kết quả cũ.

## Cấu hình và đơn vị so sánh

Sáu cấu hình, mỗi cấu hình chạy 60 ca cố định × 3 lần:

| Mã | Mô hình | Pipeline |
|---|---|---|
| P_base | Cùng checkpoint 7B NF4, không nạp adapter | P đầy đủ |
| P_ft | Cùng checkpoint, nạp adapter lịch sử | P đầy đủ |
| B1_base | 7B NF4 không adapter | PlainLlmMethod gốc, đổi transport sang runtime chung |
| B2_base | 7B NF4 không adapter | BasicRagMethod gốc, đổi transport sang runtime chung |
| P_no_memory | 7B NF4 không adapter | P, chỉ product_context=False |
| P_no_rules | 7B NF4 không adapter | P, chỉ rule_routing=False |

Hai trạng thái model dùng cùng Transformers/PEFT, NF4/BF16, GPU, checkpoint, tokenizer, SDPA, prepare_model_for_kbit_training và tham số sinh. Nhánh base không chứa PeftModel hoặc tham số lora; không giả lập base bằng adapter đang nạp nhưng đổi nhãn. Cả hai sử dụng lại nguyên hàm generate của server gốc. Transport thực nghiệm kiểm tra chặt condition, adapter_loaded, hash checkpoint/adapter; không thay model âm thầm.

P_base/P_ft dùng cùng câu hỏi, lịch sử cố định, corpus, prompt template và generation. Đối chiếu prompt thực tế ở nhóm có gọi LLM phải được báo riêng. Bộ sinh có thể được bỏ qua ở các nhánh luật/FAQ; không gán mọi khác biệt pipeline cho năng lực LLM.

P_no_memory/P_no_rules sử dụng đúng các công tắc RagComponents đã có. Tắt quản lý sản phẩm không đồng nghĩa xóa toàn bộ lịch sử khỏi prompt. Tắt rule_routing không tắt retriever threshold hoặc postcheck. Phạm vi loại bỏ được ghi đúng tên component, không thay nhiều thành phần cùng lúc. P FP16/Ollama cũ được giữ làm đối chứng hệ thống lịch sử, không nhập vào phép cô lập adapter mới.

## Đề mới và khóa trước khi chạy

`dataset.py` soạn 60 ca: 24 S, 16 H, 12 O, 8 T. Đây là đề mới do AI hỗ trợ soạn, chưa được người độc lập duyệt; không gọi là tập kiểm tra ngoại bộ độc lập. Các lịch sử cố định là fixture có vai trò user/assistant, được viết từ dữ kiện catalog, không phải phản hồi đã đo của chatbot. Mọi cấu hình nhận cùng fixture.

`prepare.py` kiểm tra hash đúng 37 mẫu train và 9 validation của adapter, đối chiếu với 100 kịch bản cũ và kiểm tra trùng trong đề mới. Kiểm tra chính xác và gần trùng dùng accent folding, SequenceMatcher >= 0,88 hoặc token Jaccard >= 0,80. Không đưa câu trả lời fixture hay đáp án vào so sánh train; không đưa rubric/đáp án vào request gửi model. Kiểm tra từ vựng không chứng minh độc lập ngữ nghĩa.

Từ `HT_model7B/backend`, dùng Python ứng dụng đã cài requirements:

```powershell
python -B -m controlled_study.prepare --root ../../outputs/controlled_60_20261105
# Sau khi kiểm tra draft/audit và hoàn tất code, khóa trước lần chạy đề mới đầu tiên:
python -B -m controlled_study.prepare --root ../../outputs/controlled_60_20261105 --freeze
```

Nếu có cặp gần trùng, bước chuẩn bị báo và không khóa. `lock.json` lưu hash đầu vào, snapshot, code và thời điểm khóa. Runner dừng nếu hash thay đổi. Không điều chỉnh prompt, luật, nguồn hoặc đề dựa trên kết quả của bộ đã khóa. Rubric và reference_products chỉ phục vụ người chấm, không đi vào context của LLM.

## Chạy

Cần NVIDIA hỗ trợ CUDA/BF16, ít nhất 9 GiB VRAM trống trước khi nạp model; Ollama phục vụ đúng nomic-embed-text của snapshot. Chuẩn bị checkpoint/adapter khớp profile như hồ sơ P+FT đã công bố. Không tải hoặc train mới tự động. Tạo một profile cục bộ chứa đường dẫn artifact phù hợp máy; không commit profile chứa cấu hình cá nhân.

```powershell
python -B -m controlled_study.run --root ../../outputs/controlled_60_20261105 --profile <profile-local.json> --gpu-python <python-GPU.exe>
```

Runner tự quản lý server loopback tại 8013, ghi lệnh/PID server do nó mở, khởi động lại khi đổi base/ft và giải phóng khi xong. Không dừng dịch vụ/ứng dụng khác. Model cần được nạp ngoài môi trường sandbox chặn localhost. Thứ tự block được khóa, P_base/P_ft đảo chiều qua các vòng; thứ tự ca được xáo trộn cố định và dùng chung trong từng vòng. Hai lượt warmup giống nhau trước mỗi block được lưu riêng, loại khỏi mẫu chính.

Có 1.080 lượt cố định. Ngoài ra bốn kịch bản H đã đăng ký N25/N29/N33/N37 được chạy rollout (lịch sử thực do từng cấu hình sinh) ở P_base/P_ft/P_no_memory/P_no_rules, mỗi cấu hình 3 lần: thêm 48 lượt. Thời gian toàn hội thoại chỉ mô tả bốn kịch bản này, không suy rộng thành cả nhóm H. Không gộp rollout với lượt cố định khi tính latency hoặc chấm chất lượng chính.

Giới hạn chung: mỗi lời gọi model 120 giây, ca cố định 180 giây (gồm khởi động worker), toàn rollout 600 giây. Giữ lỗi/timeout/context overflow, không thay phản hồi lỗi bằng phản hồi chạy lại. `--resume` chỉ tiếp tục các ca chưa ghi nhận, giữ nguyên cả ca đã lỗi; không dùng để chọn lần thành công. Mỗi attempt có request, response nếu có, record và log. Prompt được journal trước lời gọi và sau khi hoàn tất để vẫn giữ bằng chứng khi worker timeout.

## Đo lường và chấm

- Báo tỷ lệ lỗi trên tất cả attempt; số lời gọi LLM là attempt, số generation thành công lấy từ metadata. Tách nhánh rule/FAQ, LLM và non-LLM khác; không xem mọi fallback là tối ưu thành công.
- Độ trễ pipeline lượt cuối không bao gồm setup; wall time toàn rollout bao gồm setup/worker overhead. Báo từng vòng lặp, không coi ba lần của một ca là ba câu hỏi độc lập. Trung vị/trung bình/p95 giữ định nghĩa và mẫu số; p95 nội suy `(n-1)*0,95`, không báo khi dưới 20 mẫu thành công.
- Chất lượng chính: chỉ chấm repetition 1 đã đăng ký trước; giữ và báo mức thay đổi nội dung ở repetition 2/3, không chọn câu trả lời đẹp nhất. Hai người chấm nhận phiếu ẩn tên phương pháp, không xem raw outputs/ánh xạ trước khi hoàn tất. Hồ sơ raw có tên cấu hình nên ẩn nhãn trên phiếu không bảo đảm mù nếu người chấm mở hồ sơ này.
- H1: người chấm xác định từng phát biểu nghiệp vụ và gán supported/contradicted/insufficient_evidence từ snapshot; tách phát biểu không kiểm chứng được. Không tự gán nhãn bằng AI. Báo cả số phát biểu và số ca có nhãn; không đổi trường hợp không có phát biểu thành 0% sai.
- H2: chấm nhầm sản phẩm và chuyển chủ đề trên 16 ca H cố định, so P_base/P_no_memory; giữ nguyên lịch sử và chỉ đổi component đã nêu.
- H3: so P_base/P_no_rules về số gọi LLM, latency, chất lượng và từ chối nhầm; điểm/nhãn cần con người. Báo cả lỗi và câu không đủ dữ kiện, không suy chất lượng từ mode hoặc thời gian.
- Sau khi có nhãn: phân tích riêng từng người chấm, ghép theo mã ca/cấu hình; CI 95% bằng bootstrap 5.000 lần theo family, seed 20261105. Giữ các vòng lặp trong cùng đơn vị, không tăng cỡ mẫu bằng repeat. Latency ghép cặp chỉ dùng ca có đủ ba lần thành công ở cả hai bên và báo số ca loại; tỷ lệ lỗi/số attempt vẫn dùng toàn bộ. Chất lượng 0–2, nhầm sản phẩm và từ chối nhầm không được tự điền khi thiếu phiếu.

Chưa có điểm mới thì kết quả H1–H3 và lợi ích chất lượng của adapter là chưa xác định. Không sửa điểm R1/R2 cũ hoặc báo cáo kết luận cải thiện khi chỉ có số liệu thực thi.
