# Nguồn dataset và quyết định sử dụng — 14/10/2026

Người dùng đã duyệt CSConDa theo phương án khảo sát 200 mẫu train và đã tải train/test/README. Dữ liệu nằm tại `D:\NCKH\Codex\training_cache\csconda\raw`. Các bộ khác dưới đây mới được đọc card/giấy phép, chưa tải. Dữ liệu hội thoại dùng học hành vi; chính sách TechCare dùng FAQ/RAG; giá và cấu hình bán hàng dùng catalog/database. Không lấy giá, tồn kho hoặc chính sách doanh nghiệp khác làm sự thật của TechCare.

## 1. CSConDa — ưu tiên tiếng Việt

[Nguồn gốc](https://huggingface.co/datasets/ura-hcmut/Vietnamese-Customer-Support-QA), [bài nghiên cứu](https://arxiv.org/abs/2507.22542).

| Thuộc tính | Thông tin đã đối chiếu |
|---|---|
| Ngôn ngữ, số mẫu | Việt; 9.849 cặp; train 8.349, test 1.500 |
| Nội dung | Hội thoại hỗ trợ doanh nghiệp phần mềm, có viết tắt/không dấu |
| Định dạng, dung lượng | Parquet; card ghi 1,47 MB |
| Giấy phép | Apache-2.0; cần đăng nhập, chấp nhận điều kiện truy cập, trích dẫn, không tái nhận dạng |
| Cách tải sau duyệt | Xin quyền trên trang gốc, tải train/test riêng; giữ test nguyên vẹn |

Ví dụ preview rút gọn: khách hỏi không thấy đơn từ Shopee; nhân viên giải thích dữ liệu chưa được truyền. Phù hợp benchmark ngôn ngữ CSKH và SFT/LoRA hành vi hỏi lại, nêu giới hạn. Không phải catalog điện tử hay kiến thức TechCare. Dữ liệu đã che thông tin cá nhân nhưng cần rà soát lại. Tiền xử lý trung bình: loại hướng dẫn chức năng doanh nghiệp khác, kiểm tra trùng mẫu và tách holdout. Không đưa test vào huấn luyện/RAG.

## 2. Bitext Customer Support — tham khảo luồng bán hàng

[Nguồn gốc](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset).

| Thuộc tính | Thông tin đã đối chiếu |
|---|---|
| Ngôn ngữ, số mẫu | Anh; 26.872 cặp, 27 intent, 11 nhóm |
| Nội dung | Hủy/đổi đơn, giao hàng, thanh toán, hoàn tiền, chuyển nhân viên |
| Định dạng, dung lượng | CSV; card ghi 19,2 MB |
| Giấy phép | CDLA-Sharing-1.0; phải đối chiếu điều khoản nguồn khi phân phối dữ liệu dẫn xuất |
| Cách tải sau duyệt | Tải CSV tại Files của nguồn gốc, cố định revision |

Ví dụ ngắn: “cancel order {{Order Number}}”. Dữ liệu kết hợp tổng hợp và giám sát ngôn ngữ, có lỗi gõ và văn phong khác nhau. Hữu ích chọn tình huống và học intent; SFT/LoRA cần biên tập lại câu trả lời theo chức năng TechCare. Nhiều câu trả lời dài và giả định có portal/tài khoản/thao tác đơn hàng. Không dùng làm RAG chính sách. Công sức trung bình–cao nếu chuyển sang tiếng Việt: dịch local hoặc biên tập thủ công, bỏ placeholder, loại cam kết thao tác chưa triển khai. Đề xuất chỉ chọn 200–500 tình huống sau duyệt.

## 3. Bactrian-X — lựa chọn nghiên cứu phụ

[Nguồn gốc](https://huggingface.co/datasets/MBZUAI/Bactrian-X), [tác giả và giới hạn](https://github.com/mbzuai-nlp/bactrian-x), [file tiếng Việt](https://huggingface.co/datasets/MBZUAI/Bactrian-X/blob/main/data/vi.json.gz).

| Thuộc tính | Thông tin đã đối chiếu |
|---|---|
| Ngôn ngữ, số mẫu | 52 ngôn ngữ; tổng 3.484.884; khoảng 67.000/ngôn ngữ, chưa đếm file Việt |
| Nội dung | Instruction/input/output tổng quát, câu trả lời tổng hợp |
| Định dạng, dung lượng | JSON.gz; file Việt 20,9 MB, cả bộ 1,2 GB |
| Giấy phép | CC BY-NC 4.0; tác giả giới hạn dùng nghiên cứu |
| Cách tải sau duyệt | Chỉ tải `data/vi.json.gz`, không tải cả bộ |

Ví dụ cấu trúc: instruction yêu cầu giải thích, input tùy chọn, output tiếng Việt. Có thể bổ sung SFT/LoRA tiếng Việt; không phù hợp RAG cửa hàng hoặc thông số/giá hiện tại. Tác giả công bố nguồn phản hồi GPT-3.5 và dịch máy năm 2023: cần lọc lỗi, thiên lệch, dữ kiện cũ. Việc dùng dataset công khai này không yêu cầu gọi API cloud, nhưng nguồn gốc cần ghi trong báo cáo. Tiền xử lý cao, ưu tiên thấp trước buổi demo; tránh cho sản phẩm thương mại khi chưa giải quyết giới hạn nguồn.

## 4. dataset-vi-chatbot-ai — chưa khuyến nghị

[Nguồn gốc](https://huggingface.co/datasets/huutho13254/dataset-vi-chatbot-ai).

| Thuộc tính | Thông tin đã đối chiếu |
|---|---|
| Ngôn ngữ, số mẫu | Card ghi Việt/Anh; 8.700 hội thoại |
| Nội dung | `messages`, `source`; preview nhiều mẫu tiếng Anh từ Bitext |
| Định dạng, dung lượng | Parquet; card ghi 2,2 MB |
| Giấy phép | Không có giấy phép thống nhất rõ; card yêu cầu tuân thủ từng nguồn |
| Cách tải sau duyệt | Files/Parquet; chỉ cân nhắc khi xác minh được provenance và quyền sử dụng |

Ví dụ preview rút gọn: khách muốn cập nhật địa chỉ, assistant xin thông tin. Card quảng bá function calling nhưng bảng thành phần ghi 0 mẫu ở nhóm này; nhóm tiếng Việt tự nhiên cũng ghi 0. Có thể xem cấu trúc SFT/LoRA, không dùng làm RAG/catalog. Rủi ro thông tin quảng bá chưa khớp dữ liệu, câu trả lời tự nhận làm được thao tác không có trong TechCare, giấy phép nguồn trộn. Tiền xử lý/rà soát cao. Chưa đề xuất tải.

## Quyết định đã duyệt và kết quả khảo sát

Ưu tiên bộ nội bộ: 30 FAQ biên tập và catalog 53 sản phẩm đã có, mở rộng 150–300 hội thoại tình huống có người nhóm duyệt, gắn nguồn và trường `needs_human`. Chia train/validation/test theo **tình huống và sản phẩm**, tránh biến thể cùng câu rơi cả train lẫn test. Không dùng `evaluation_cases.json` làm train.

CSConDa đã được chọn. Đã xác minh file train 8.349 dòng, giữ file test 1.500 dòng riêng. Khảo sát 200 câu với seed 20261014, đóng băng file gốc bằng SHA256. Giữ 46 tình huống: **12 đáp án người hỗ trợ viết nguyên bản, 34 đáp án do agent biên tập từ câu hỏi gốc**, loại 154 mẫu. Bản biên tập không được gọi là hội thoại thật nguyên bản. Nhiều nhãn General vẫn chứa hướng dẫn giao diện hoặc chính sách doanh nghiệp nguồn, nên không thể dùng nhãn đó như bộ lọc chất lượng.

Tách **37 train / 9 validation theo nhóm tình huống**, không để cùng nhóm vào cả hai tập. Các câu hỏi đánh giá pipeline và raw-LLM không được đưa vào train. Test chính thức không dùng cho train, lựa chọn hyperparameter hoặc RAG. Do pilot nhỏ và phần lớn mục tiêu là câu đã biên tập, không suy rộng kết quả thành hiệu quả trên toàn bộ CSConDa hay CSKH bán lẻ thật.

Nguồn khảo sát và quyết định từng dòng: `D:\NCKH\Codex\training_cache\csconda_survey`; dữ liệu đã chuẩn bị và manifest: `D:\NCKH\Codex\training_cache\csconda_prepared_grouped`. Đã đối chiếu SHA256 hai file với metadata nguồn tại revision `ae8232e93a2ce4edb15560f6ef8e52f38ce1733d`. SHA256 train: `03a6b01c16fba952852a38ee84247942a9436a4822f3aa8acffdd32d1f3cc954`; test: `b3070c1d1a3a3d53aace601df40dc7665b0c5b0ef529e7d588e1ccf1d0ac25b2`. Tác giả yêu cầu trích dẫn bài CSConDa, DOI `10.1007/978-3-032-10202-7_33`.

Đã cài môi trường CUDA riêng ngoài repo, kiểm tra GPU rồi chạy pilot 7B một epoch trên 37/9 mẫu. Kết quả raw 8 câu không tăng, nên không nâng model chính. Tiếp theo đã train 3B: **170 train = 37 CSConDa đã lọc + 133 ví dụ tổng hợp có ngữ cảnh**, giữ 9 validation CSConDa. Các giá mô phỏng thay đổi theo ngữ cảnh để dạy đọc dữ kiện, không nhập lại vào catalog. Nguồn 12 đáp án người hỗ trợ nguyên bản và 34 đáp án biên tập vẫn được ghi rõ trong provenance.

Tập tổng hợp 21 câu được đóng băng trước train, giữ sản phẩm và cách hỏi riêng: cấu hình chạy đầu đạt 12/21 so với base 18/21, được giữ làm kết quả không tốt. Sau khi đã xem tập đó, không gọi việc thử lại là holdout độc lập. Chọn lại cấu hình prompt/repetition trên 8 câu phát triển; đánh giá tiếp bằng **12 câu tổng hợp mới đóng băng trước khi chọn cấu hình**, base 10/12, trained 12/12 theo tiêu chí tự động. Các tập này do agent tạo, không thay cho thử nghiệm khách hàng thật hoặc test chính thức CSConDa.

3B dùng checkpoint NF4 `unsloth/Qwen2.5-3B-Instruct-bnb-4bit` revision `2672b588848527e456d320c11926c794539f47d5`, LoRA rank 16 trên all-linear, 2 epoch, LR 1e-4, sequence 512. Adapter được gộp, chuyển GGUF Q4_K_M và cài local thành `techcare-support:3b-v1`. Model, adapter, dữ liệu đã chọn và bằng chứng chính được đóng gói trong `backend/models/techcare-support-3b-v1`, theo yêu cầu giữ các phần đã xác nhận cùng project. Tuân theo giấy phép upstream [Qwen2.5-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct), **Qwen Research License**, dù card của bản đóng gói NF4 ghi Apache. Giữ nguyên license trong Modelfile và thư mục model.

## Tham khảo cách viết FAQ bán lẻ

Đã xem [FPT Shop](https://fptshop.com.vn/ho-tro/chinh-sach-doi-san-pham) và [Best Buy](https://www.bestbuy.com/site/help-topics/return-exchange-policy/pcmcat260800050014.c?id=pcmcat260800050014). Áp dụng cách trình bày điều kiện, giấy tờ và bước tiếp theo; không sao chép thời hạn hay cam kết của họ thành chính sách TechCare. Các câu FAQ mới là nội dung gốc cho môi trường nghiên cứu.
