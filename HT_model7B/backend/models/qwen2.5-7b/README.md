# Qwen2.5-7B gốc dùng cho hệ thống 7B

Model Ollama `qwen2.5:7b-instruct-fp16`, trọng số FP16 (`F16`), khoảng 15 GB, không gắn adapter và không fine-tune thêm bởi nhóm. Dùng artifact FP16 được phát hành, không upcast từ Q4_K_M. [Nguồn chính thức](https://ollama.com/library/qwen2.5:7b-instruct-fp16), [manifest](model_manifest.json), [Apache 2.0](LICENSE).

```powershell
ollama pull qwen2.5:7b-instruct-fp16
ollama pull nomic-embed-text
```

Trọng số nằm trong kho model do Ollama quản lý trên từng máy, không nằm trong repository. Manifest giữ digest của bản đã xác minh; `ollama list`/API `/api/tags` cho biết digest trên máy khác. Không coi hai lượt đo khác digest là cùng bản trọng số.

Kiểm tra `ollama show qwen2.5:7b-instruct-fp16`: trường quantization phải là `F16`. FP16 vượt VRAM 12 GB khi nạp toàn bộ; Ollama có thể chia tải CPU/GPU nếu đủ RAM, với độ trễ phụ thuộc máy. Không tự đổi sang Q4 khi thiếu bộ nhớ. Bản Q4 đã có và các kết quả cũ được giữ riêng.

Benchmark giữ context 4096, output tối đa 384, temperature 0 và repeat_penalty 1. B1/B2/P dùng cùng tag; B0 không gọi model. Model 3B cũ và giấy phép của nó được giữ ở thư mục hệ thống `HT_model3B`, độc lập với bản 7B này.
