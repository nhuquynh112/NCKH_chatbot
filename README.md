# Demo AI/RAG cho đề tài chatbot CSKH

Chủ đề demo: **TechCare Electronics - website bán thiết bị điện tử**.

Nên chọn một chủ đề cụ thể thay vì làm "chatbot chung chung", vì RAG cần dữ liệu rõ ràng để truy xuất. Chủ đề thiết bị điện tử rất hợp với chăm sóc khách hàng: tư vấn sản phẩm, hỏi bảo hành, đổi trả, lỗi kỹ thuật, giao hàng, thanh toán, kiểm tra đơn và tạo ticket.

## Việc của thành viên AI/RAG

1. Chạy LLM local bằng Ollama.
2. Tạo bộ dữ liệu mẫu cho doanh nghiệp.
3. Xây RAG: câu hỏi -> embedding -> tìm context -> đưa context cho LLM -> trả lời.
4. Viết system prompt chống bịa thông tin.
5. Kiểm thử bằng bộ câu hỏi mẫu.
6. Viết báo cáo phần lý thuyết: LLM, embedding, vector database, RAG, evaluation.

## Cài model Ollama

Chạy trong PowerShell hoặc terminal VS Code:

```powershell
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

Nếu máy yếu, dùng model nhỏ hơn:

```powershell
ollama pull qwen2.5:1.5b
```

Nếu dùng model nhỏ hơn, sửa biến `CHAT_MODEL` trong `rag_chat_ollama.py`.

## Chạy demo RAG đơn giản

Script `rag_chat_ollama.py` dùng Ollama embedding và lưu vector index bằng JSON, chưa cần cài ChromaDB. Cách này dễ demo nhanh; trong báo cáo có thể nói vector database có thể thay bằng ChromaDB khi triển khai hoàn chỉnh.

```powershell
cd "D:\OneDrive\Documents\New project 2\ai_rag_demo"
python rag_chat_ollama.py --build
python rag_chat_ollama.py
```

Sau đó thử hỏi:

```text
Laptop NovaBook Air 14 giá bao nhiêu?
Máy nào phù hợp sinh viên học online và làm Word Excel?
Tai nghe SonicBuds Pro có chống ồn không?
Bảo hành điện thoại bao lâu?
Đơn TCDH1007 đang ở đâu?
Tôi mua laptop bị lỗi màn hình xanh thì làm sao?
Shop có bán máy giặt không?
```

## File trong thư mục này

- `knowledge_base.md`: dữ liệu đưa vào RAG.
- `eval_questions.json`: câu hỏi kiểm thử và đáp án kỳ vọng.
- `system_prompt.txt`: prompt dùng cho chatbot.
- `rag_chat_ollama.py`: demo RAG local với Ollama.
- `generate_techcare_dataset.py`: script tạo dataset lớn cho đề tài.
- `techcare_chatbot_dataset.json`: dataset đầy đủ gồm metadata, tài liệu RAG và Q/A pairs.
- `techcare_train_pairs.jsonl`: dữ liệu dạng messages, dùng để thử nghiệm fine-tuning/instruction tuning.
- `techcare_qa_pairs.csv`: 620 cặp hỏi đáp, mở được bằng Excel.
- `techcare_eval_120.json`: 120 mẫu dùng để đánh giá chatbot.
- `techcare_rag_documents.json`: tài liệu RAG dạng JSON, có thể đưa vào ChromaDB/FAISS.
- `DATASET_TECHCARE.md`: mô tả dataset để đưa vào báo cáo.
- `run_eval_ollama.py`: chạy đánh giá tự động một số câu bằng Ollama.
- `GHI_CHU_FINE_TUNING.md`: giải thích phần fine-tuning để trình bày với thầy.
- `product_catalog_extended.md`: catalog mở rộng 100 sản phẩm để RAG truy xuất.
- `techcare_products_100.json`: dữ liệu 100 sản phẩm dạng JSON.
- `techcare_product_qa_500.csv`: 500 cặp hỏi đáp sinh từ catalog 100 sản phẩm.
- `generate_extended_catalog.py`: script tạo lại catalog 100 sản phẩm.

## Dataset lớn cho yêu cầu 200-1000 mẫu

Đề tài có yêu cầu tự tạo dataset Q/A chatbot chăm sóc khách hàng khoảng 200-1000 mẫu. Bộ demo này đã tạo sẵn **620 cặp hỏi đáp** cho TechCare Electronics.

Nếu muốn tạo lại dataset:

```powershell
cd "D:\OneDrive\Documents\New project 2\ai_rag_demo"
python generate_techcare_dataset.py
```

Ý nghĩa từng file:

```text
techcare_qa_pairs.csv          -> bảng Q/A để xem, thống kê, đưa vào phụ lục
techcare_train_pairs.jsonl     -> dữ liệu dùng cho fine-tuning thử nghiệm
techcare_eval_120.json         -> bộ câu hỏi đánh giá
techcare_rag_documents.json    -> tài liệu dùng cho vector database
```

Lưu ý: hiện demo đang chạy theo hướng **RAG trước**, vì đây là hướng dễ demo, dễ giải thích và đúng thực tế hơn. Fine-tuning có thể trình bày là phần thử nghiệm mở rộng bằng dataset `techcare_train_pairs.jsonl`.

Ngoài dataset Q/A chính, demo còn có catalog mở rộng **100 mặt hàng** và **500 Q/A sản phẩm** để hệ thống nhìn giống một shop điện tử thật hơn. Khi chạy `python rag_chat_ollama.py --build`, RAG sẽ đọc cả `knowledge_base.md` và `product_catalog_extended.md`.

## Phần nào đã xong?

- Phần 3 RAG system: đã có demo hỏi -> tìm ngữ cảnh -> trả lời.
- Phần 4 Fine-tuning: đã có dataset 620 mẫu để phục vụ fine-tuning, nhưng chưa fine-tune model thật.
- Phần 5 Prompt Engineering: đã có `system_prompt.txt`.
- Phần 6 Evaluation AI: đã có `eval_questions.json` và `techcare_eval_120.json`, cần chạy test rồi điền kết quả.

## Chạy evaluation tự động

Chạy thử 10 câu trước:

```powershell
cd "D:\OneDrive\Documents\New project 2\ai_rag_demo"
python run_eval_ollama.py --limit 10
```

Nếu máy chạy ổn, tăng lên 30 hoặc 120:

```powershell
python run_eval_ollama.py --limit 30
python run_eval_ollama.py --limit 120
```

Kết quả sẽ lưu vào `evaluation_results.json`. Điểm `rough_accuracy` chỉ là chấm tương đối bằng script; khi viết báo cáo nên kiểm tra thủ công vài câu quan trọng.

## Nên viết vào báo cáo như thế nào

Tên hệ thống:

> Xây dựng chatbox hỗ trợ chăm sóc khách hàng cho website bán thiết bị điện tử TechCare Electronics ứng dụng mô hình ngôn ngữ lớn local và RAG.

Kiến trúc:

```text
User
-> Website chatbox
-> Backend API
-> RAG engine
-> Vector index
-> Ollama LLM local
-> Câu trả lời / tạo ticket nếu không chắc
```

Kết quả cần chứng minh:

- Chatbot trả lời đúng chính sách dựa trên dữ liệu.
- Chatbot tư vấn sản phẩm điện tử dựa trên nhu cầu khách hàng.
- Khi không có đủ dữ liệu, chatbot không bịa mà đề nghị tạo ticket.
- Có bảng so sánh câu trả lời khi có RAG và không có RAG.
