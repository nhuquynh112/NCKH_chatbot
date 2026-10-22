# Adapter P+FT 7B — thí nghiệm bổ sung

Đây là adapter QLoRA 7B gốc đã hoàn tất, dùng trong P+FT (tên cũ M4). **Không phải model của P trong bốn phương pháp chính**, không phải `techcare-support:3b-v1` và không dùng tập 170 mẫu của demo 3B.

- Base: `unsloth/Qwen2.5-7B-Instruct-bnb-4bit`, revision `bdd404162d94997f390efbfa660eb3f21cbbc81d`.
- Dữ liệu: **37 train, 9 validation**, tách theo nhóm tình huống, từ split train CSConDa; **1 epoch**. Trong 46 mẫu được chọn có 12 đáp án nguồn và 34 đáp án được agent biên tập; đây là pilot nhỏ, không phải toàn bộ bộ dữ liệu chính thức.
- LoRA: rank 8, alpha 16, dropout 0,05, target `q_proj`/`v_proj`. Serving base NF4 và tính toán BF16 bằng Transformers/PEFT.
- Adapter: `run/adapter/adapter_model.safetensors`, 10.107.280 byte, Git LFS, SHA256 `b7650bf5a6a4eb02b902bb9a5758d178c3e4f32c5329013ca7c819045d8008b7`.
- Adapter, `run/adapter/adapter_config.json` và `checkpoint_manifest.json` giữ nguyên byte từ lần huấn luyện gốc. `run/run.json` là bản tóm tắt metadata (model/revision, số mẫu, epoch và hash log gốc), không chứa mẫu train/validation hoặc đầu ra hội thoại. Dữ liệu và log đầy đủ giữ tại máy tác giả, không phát hành trong nhánh này. Không train lại, merge hoặc chuyển đổi trọng số trong lần đóng gói này.
- Checkpoint khoảng 5,55 GB tải riêng tại revision trên; không chép vào repository.

Giấy phép base/adapter: Apache 2.0, xem `LICENSE`. Dữ liệu nguồn [Vietnamese Customer Support QA / CSConDa](https://huggingface.co/datasets/ura-hcmut/Vietnamese-Customer-Support-QA) công bố Apache 2.0; trích dẫn bài CSConDa, DOI `10.1007/978-3-032-10202-7_33`. Hồ sơ gốc xác định bản tải dữ liệu bằng SHA256 file, chưa ghi commit tại thời điểm train; bản tóm tắt không phải toàn bộ bằng chứng để tái lập huấn luyện.

[Cách tải base, kiểm tra hash, chạy server và benchmark P+FT](../../../docs/BENCHMARK_METHODS.md).
