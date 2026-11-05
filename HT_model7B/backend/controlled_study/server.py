"""Same NF4 runtime for base/adapter; base does not load any adapter weights."""
import argparse
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import threading

from model_serving.server import AdapterRuntime, handler_for, verify_artifacts

MODEL = "qwen2.5-7b-controlled"


class ControlledRuntime(AdapterRuntime):
    def __init__(self, profile, condition):
        super().__init__({**profile, "model": MODEL})
        self.condition = condition

    def load(self):
        try:
            os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                              HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false")
            identity = verify_artifacts(self.profile)
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM
            from peft import PeftModel, prepare_model_for_kbit_training
            if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
                raise RuntimeError("CUDA/BF16 required; no CPU or precision substitution")
            if torch.cuda.mem_get_info()[0] < 9 * 1024 ** 3:
                raise RuntimeError("Need at least 9 GiB free VRAM before loading")
            self.torch = torch
            torch.manual_seed(20261014)
            base = self.profile["checkpoint_path"]
            self.tokenizer = AutoTokenizer.from_pretrained(base, local_files_only=True, trust_remote_code=False)
            if self.tokenizer.pad_token_id is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            model = AutoModelForCausalLM.from_pretrained(
                base, device_map={"": 0}, dtype=torch.bfloat16,
                attn_implementation="sdpa", local_files_only=True, trust_remote_code=False)
            if not getattr(model, "is_loaded_in_4bit", False):
                raise RuntimeError("Expected pinned NF4 checkpoint")
            model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=False)
            if self.condition == "ft":
                model = PeftModel.from_pretrained(model, self.profile["adapter_path"],
                                                 is_trainable=False, local_files_only=True)
                if not model.active_adapters:
                    raise RuntimeError("Adapter did not activate")
            elif isinstance(model, PeftModel) or any("lora_" in name for name, _ in model.named_parameters()):
                raise RuntimeError("Base condition unexpectedly contains an adapter")
            self.model = model
            self.model.eval()
            self.model.config.use_cache = True
            if any(parameter.device.type != "cuda" for parameter in model.parameters()):
                raise RuntimeError("CPU offload is not permitted")
            active = list(model.active_adapters) if self.condition == "ft" else []
            self.state = {**identity, "model": MODEL, "status": "ready", "condition": self.condition,
                          "adapter_loaded": self.condition == "ft", "active_adapters": active,
                          "adapter_sha256": identity["adapter_sha256"] if self.condition == "ft" else None,
                          "candidate_adapter_sha256": identity["adapter_sha256"],
                          "gpu": torch.cuda.get_device_name(0), "quantization": "NF4/BF16",
                          "seed": 20261014, "attention": "sdpa", "cpu_offload": False,
                          "packages": {name: importlib.metadata.version(name) for name in
                                       ("torch", "transformers", "peft", "bitsandbytes")},
                          "loaded_at": datetime.now(timezone.utc).isoformat()}
            logging.info("MODEL_READY %s", json.dumps(self.state))
        except Exception as error:
            self.state = {**self.state, "status": "not_ready", "condition": self.condition,
                          "error": f"{type(error).__name__}: {error}"}
            logging.exception("MODEL_NOT_READY")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--condition", choices=("base", "ft"), required=True)
    parser.add_argument("--port", type=int, default=8013)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    runtime = ControlledRuntime(json.loads(args.profile.read_text(encoding="utf-8-sig")), args.condition)
    original_handler = handler_for(runtime)

    class StudyHandler(original_handler):
        def do_POST(self):
            if self.path == "/shutdown":
                self.send_json(200, {"stopping": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                super().do_POST()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), StudyHandler)
    threading.Thread(target=runtime.load, daemon=True).start()
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
