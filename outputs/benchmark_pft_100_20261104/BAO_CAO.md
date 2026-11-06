# Benchmark bổ sung P+FT — 100 ca, ngày 04/11/2026

P+FT dùng adapter 7B lịch sử đã hoàn tất ngày 14/10/2026. Không huấn luyện lại trong lượt này. Catalog mới được đưa qua RAG: 150 sản phẩm, 299 tài liệu; bộ đề v4.0-draft gồm 100 ca, trong đó 20 ca hội thoại tự sinh lịch sử.

Giữ nguyên pipeline P, generation temperature=0, context=4096, max output=384, repeat penalty=1. Câu đơn/mỗi lần gọi model tối đa 120 giây; toàn bộ ca H tối đa 600 giây. Câu hỏi, corpus và database đóng băng trùng lượt P đã thu ngày 28/10/2026.

## Kết quả thực thi

| Chỉ tiêu | P — 7B FP16 gốc | P+FT — 7B NF4/BF16 |
|---|---:|---:|
| Số ca | 100 | 100 |
| Ca có thử gọi LLM ở lượt cuối | 35 | 35 |
| Ca có gọi LLM ở lượt thiết lập | 19 | 19 |
| Ca có lỗi embedding/truy xuất | 0 | 0 |
| Trung vị pipeline lượt cuối (ms) | 242.23 | 274.62 |
| P95 pipeline lượt cuối (ms) | 16173.88 | 16216.17 |
| Trung bình pipeline lượt cuối (ms) | 5504.74 | 4934.59 |

Trạng thái P: {"ok": 100}. Trạng thái P+FT: {"ok": 99, "error": 1}.
Phản hồi cuối trùng nguyên văn với P: 70/100. Đây là mức trùng văn bản, không phải độ chính xác.
Thời gian pipeline trên chỉ dùng các ca hoàn tất; số mẫu, wall time toàn ca và tỷ lệ lỗi có trong statistics.json. Lượt cuối có thể đi qua luật/FAQ mà không gọi LLM; việc chọn P+FT không có nghĩa cả 100 câu đều sinh bằng model.

## Đối chiếu trên cùng tập ca hoàn tất

Bảng tổng thể ở trên có 100 ca thành công của P và 99 của P+FT. Để tránh so thời gian trên hai mẫu khác nhau, dưới đây tính lại trên các mã ca cùng hoàn tất. Các chênh lệch vẫn chỉ mang tính mô tả do khác runtime/precision và thời điểm thu thập.

| Tập ca và chỉ tiêu | P | P+FT |
|---|---:|---:|
| Cùng hoàn tất: số ca | 99 | 99 |
| Cùng hoàn tất: Trung vị pipeline cuối (ms) | 239.68 | 274.62 |
| Cùng hoàn tất: Trung bình pipeline cuối (ms) | 5397.91 | 4934.59 |
| Cùng hoàn tất: P95 pipeline cuối (ms) | 15793.71 | 16216.17 |
| Cùng hoàn tất và có gọi LLM cuối: số ca | 34 | 34 |
| Cùng hoàn tất và có gọi LLM cuối: Trung vị pipeline cuối (ms) | 12683.19 | 11978.54 |
| Cùng hoàn tất và có gọi LLM cuối: Trung bình pipeline cuối (ms) | 15290.59 | 13886.20 |
| Cùng hoàn tất và có gọi LLM cuối: P95 pipeline cuối (ms) | 34014.44 | 26223.20 |

## Ca lỗi S47

S47 bị server từ chối trước generation: input có 3758 token, cần dự phòng 384 token đầu ra, tổng 4142 vượt context 4096. Lỗi gốc: Context exceeds limit; no silent prompt truncation.
Đây là lỗi kiểm tra giới hạn prompt của runtime HF, không phải lỗi embedding hoặc timeout. Server không tự cắt prompt; không suy đoán việc Ollama đã xử lý/cắt ngữ cảnh ở lượt P vì log cũ không có đủ bằng chứng tokenization đó.
Giữ ca lỗi trong mẫu 100 ca, tỷ lệ lỗi 1%. Không tăng riêng context hoặc chọn lượt chạy lại thành công để thay mẫu. P+FT có 35 ca thử gọi LLM cuối, 34 ca gọi cuối hoàn tất; CSV có cột error và S47 không có câu trả lời thay thế.

## Model và dữ liệu fine-tune lịch sử

Adapter LoRA rank 8, alpha 16, target q_proj/v_proj, learning rate 5e-05; 37 mẫu train, 9 mẫu validation từ ura-hcmut/Vietnamese-Customer-Support-QA; 1.0 epoch, max length 512.
Checkpoint: unsloth/Qwen2.5-7B-Instruct-bnb-4bit, revision bdd404162d94997f390efbfa660eb3f21cbbc81d.
Adapter SHA256: `b7650bf5a6a4eb02b902bb9a5758d178c3e4f32c5329013ca7c819045d8008b7`.
Checkpoint SHA256: `99b85155b7bb40344d8c3938c8ec1147b27028804bca5d2e5559cb8e6533747d`.
Loss validation lịch sử trên 9 mẫu: 3.723275 trước và 3.675476 sau fine-tune; không phải kết quả chất lượng của bộ 100 ca mới.

## Dữ liệu để chấm và giới hạn diễn giải

- PFT_100.csv: câu trả lời thật, lịch sử user/assistant, trạng thái và latency; score_0_2/reviewer/notes để trống.
- comparison_P_PFT.csv: 100 cặp phản hồi P và P+FT, mỗi phương pháp có lịch sử thực tế riêng.
- statistics.json: chỉ số thực thi, model identity, package versions, hash dữ liệu/code và provenance.
- Chưa có điểm chất lượng 0–2 hoặc accuracy P+FT. Cần chấm thêm các phản hồi mới; không dùng lại điểm hoặc kappa của bộ bốn phương pháp để gán cho P+FT.
- P+FT là thử nghiệm bổ sung. NF4/BF16 và Transformers/PEFT khác FP16/Ollama của P; không quy toàn bộ khác biệt cho fine-tuning. Thời điểm thu thập, warm-up và tải GPU cũng khác nên latency chỉ mang tính mô tả.
- Corpus/case đóng băng và dữ liệu train được giữ riêng. Không đưa câu hỏi, đáp án hoặc điểm người chấm vào train/RAG.
- Model server đã xác minh adapter active, identity đúng hash; ba ca smoke S01/S31/H01 có trước lượt chính, lưu riêng và không trộn vào 100 phản hồi.

Lượt này chỉ xuất số liệu và phản hồi để đánh giá bổ sung; kết quả chính B0/B1/B2/P và hai phiếu đã chấm được giữ nguyên.