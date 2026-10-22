# Triển khai P đã xác minh

- benchmark/protocol.py:21 method_spec(P) => proposed, ollama, đủ sáu thành phần true.
- benchmark/methods.py:16 method_settings => CHAT_MODEL=qwen2.5:3b, USE_PROJECT_CHAT_MODEL=False, top5/ngưỡng0.38, corpus copy, JSON/nomic.
- benchmark/methods.py:122 RagMethod => create_default_chat_service(config), gắn switches cho cả ChatService/ retriever, bọc client để ghi mọi lời gọi.
- benchmark/methods.py:198 build_method => RagMethod cho proposed; không đổi nhãn PlainLlmMethod/B2.
- app/model_client.py:100 create_model_client => OllamaClient khi provider=ollama, không nhánh HF/LoRA.
- Runtime preflight24/24: qwen2.5:3b digest357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b, embedding nomic digest0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f, semantic195documents. Ollama show không có dòng ADAPTER.
- QueryRewriter, vector/BM25 và xếp hạng heuristic theo miền có thật; không có bằng chứng learned cross-encoder reranker. Fallback và hậu kiểm thật, không đảm bảo đúng ngữ nghĩa mọi câu.
- P so P+FT: same flags,24/24 nguồn ID giống,7/7 prompt/generationsettings giống,17/17 non-LLManswer giống. Khácmodel3B/7B, weights, Q4_K_MvsNF4/BF16, OllamavsHF/PEFT. Không kết luận tác dụng riêng FT.
- Repo chatbot-v1, HEAD1cef995f95b3b315037e2102fd82488e621e0370; tên branch đổi so với trước, source98filehash không đổi. Không checkout/commit/push.
