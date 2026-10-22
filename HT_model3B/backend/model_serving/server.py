"""Serve the original verified 7B adapter on its NF4 checkpoint, entirely offline."""
import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import threading
import time

PROFILE = Path(__file__).parent / "profiles/qwen25_7b.json"
LOG = logging.getLogger(__name__)


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_artifacts(profile):
    checkpoint, adapter = Path(profile["checkpoint_path"]), Path(profile["adapter_path"])
    run = json.loads((adapter.parent / "run.json").read_text(encoding="utf-8"))
    config = json.loads((adapter / "adapter_config.json").read_text(encoding="utf-8"))
    manifest = json.loads((checkpoint / "checkpoint_manifest.json").read_text(encoding="utf-8"))
    if (run["status"] != "completed" or run["checkpoint"]["repo"] != profile["base_repo"]
            or run["checkpoint"]["revision"] != profile["base_revision"]):
        raise ValueError("Training provenance does not match the selected 7B profile")
    if manifest["revision"] != profile["base_revision"] or manifest["repo"] != profile["base_repo"]:
        raise ValueError("Checkpoint revision mismatch")
    if config["r"] != 8 or set(config["target_modules"]) != {"q_proj", "v_proj"}:
        raise ValueError("Unexpected adapter architecture")
    if sum(item["name"] == "model.safetensors" for item in manifest["files"]) != 1:
        raise ValueError("Checkpoint manifest must identify the pinned weights exactly once")
    for item in manifest["files"]:
        path = checkpoint / item["name"]
        if path.parent.resolve() != checkpoint.resolve():
            raise ValueError("Invalid checkpoint manifest path")
        if path.stat().st_size != item["bytes"] or sha256(path) != item["local_sha256"]:
            raise ValueError(f"Checkpoint integrity mismatch: {item['name']}")
        if item["name"] == "model.safetensors" and item["local_sha256"] != profile["checkpoint_sha256"]:
            raise ValueError("Checkpoint weights differ from the pinned profile")
    adapter_hash = sha256(adapter / "adapter_model.safetensors")
    if adapter_hash != profile["adapter_sha256"]:
        raise ValueError("Adapter weights differ from the pinned profile")
    return {"model": profile["model"], "base_repo": profile["base_repo"],
            "base_revision": profile["base_revision"], "adapter_sha256": adapter_hash,
            "checkpoint_sha256": profile["checkpoint_sha256"],
            "run_sha256": sha256(adapter.parent / "run.json")}


class AdapterRuntime:
    def __init__(self, profile):
        self.profile = profile
        self.state = {"status": "loading", "model": profile["model"], "adapter_loaded": False}
        self.slot = threading.BoundedSemaphore(1)

    def load(self):
        try:
            os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                              HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false")
            identity = verify_artifacts(self.profile)
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM
            from peft import PeftModel, prepare_model_for_kbit_training
            if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
                raise RuntimeError("CUDA with BF16 support is required for this verified runtime")
            if torch.cuda.mem_get_info()[0] < 9 * 1024**3:
                raise RuntimeError("Need at least 9 GiB free VRAM; unload other chat models first")
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
                raise RuntimeError("Expected the original NF4 checkpoint")
            model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=False)
            self.model = PeftModel.from_pretrained(model, self.profile["adapter_path"],
                                                 is_trainable=False, local_files_only=True)
            self.model.eval()
            self.model.config.use_cache = True
            if not self.model.active_adapters or any(p.device.type != "cuda" for p in self.model.parameters()):
                raise RuntimeError("Adapter inactive or unexpected CPU offload")
            self.state = {**identity, "status": "ready", "adapter_loaded": True,
                          "active_adapters": self.model.active_adapters,
                          "gpu": torch.cuda.get_device_name(0), "quantization": "NF4/BF16",
                          "packages": {n: importlib.metadata.version(n) for n in
                                       ("torch", "transformers", "peft", "bitsandbytes")},
                          "loaded_at": datetime.now(timezone.utc).isoformat()}
            LOG.info("MODEL_READY %s", json.dumps(self.state))
        except Exception as exc:
            self.state = {**self.state, "status": "not_ready", "adapter_loaded": False,
                          "error": f"{type(exc).__name__}: {exc}"}
            LOG.exception("MODEL_NOT_READY")

    def generate(self, request):
        if self.state["status"] != "ready":
            raise RuntimeError(self.state.get("error", "Model is still loading"))
        if request.get("model") != self.profile["model"]:
            raise ValueError("Requested model does not match this server")
        if request.get("temperature", 0) != 0 or request.get("repeat_penalty", 1.0) != 1.0:
            raise ValueError("This experiment requires greedy decoding and repetition penalty 1.0")
        tokens = int(request.get("max_new_tokens", 384))
        context = int(request.get("num_ctx", 4096))
        timeout = float(request.get("timeout_seconds", 20))
        if not 1 <= tokens <= 384 or not 512 <= context <= 4096 or not 1 <= timeout <= 120:
            raise ValueError("Generation limits outside supported bounds")
        for key in ("system_prompt", "user_prompt"):
            if not isinstance(request.get(key), str) or len(request[key]) > 60000:
                raise ValueError(f"Invalid {key}")
        if not self.slot.acquire(blocking=False):
            raise RuntimeError("7B busy; only one generation is allowed at a time")
        try:
            torch = self.torch
            from transformers import StoppingCriteria, StoppingCriteriaList
            started = time.perf_counter()

            class Deadline(StoppingCriteria):
                expired = False

                def __call__(self, input_ids, scores, **kwargs):
                    self.expired = time.perf_counter() - started >= timeout
                    return self.expired

            deadline = Deadline()
            messages = [{"role": "system", "content": request["system_prompt"]},
                        {"role": "user", "content": request["user_prompt"]}]
            inputs = self.tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                                       return_dict=True, return_tensors="pt").to("cuda")
            length = inputs["input_ids"].shape[-1]
            if length + tokens > context:
                raise ValueError("Context exceeds limit; no silent prompt truncation")
            torch.cuda.reset_peak_memory_stats()
            with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
                output = self.model.generate(**inputs, do_sample=False, max_new_tokens=tokens,
                                             repetition_penalty=1.0, use_cache=True,
                                             pad_token_id=self.tokenizer.pad_token_id,
                                             stopping_criteria=StoppingCriteriaList([deadline]))
            torch.cuda.synchronize()
            if deadline.expired or time.perf_counter() - started >= timeout:
                raise TimeoutError("7B generation exceeded the requested deadline")
            answer = self.tokenizer.decode(output[0, length:], skip_special_tokens=True)
            return {**self.state, "answer": answer, "generation_ms": (time.perf_counter()-started)*1000,
                    "input_tokens": length, "output_tokens": output.shape[-1]-length,
                    "peak_allocated_bytes": torch.cuda.max_memory_allocated()}
        finally:
            self.slot.release()


def handler_for(runtime):
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, status, body):
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            self.send_json(200, runtime.state) if self.path == "/health" else self.send_json(404, {"error":"Not found"})

        def do_POST(self):
            if self.path != "/generate":
                return self.send_json(404, {"error": "Not found"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 131072:
                    raise ValueError("Invalid request size")
                self.connection.settimeout(10)
                request = json.loads(self.rfile.read(size))
                if not isinstance(request, dict):
                    raise ValueError("JSON object required")
                self.send_json(200, runtime.generate(request))
            except (ValueError, TypeError) as exc:
                self.send_json(400, {"error": str(exc)})
            except TimeoutError as exc:
                self.send_json(504, {"error": str(exc)})
            except Exception as exc:
                LOG.exception("Generation failed")
                self.send_json(503, {"error": str(exc), "model": runtime.profile["model"]})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=PROFILE)
    parser.add_argument("--port", type=int, default=8011)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    if args.check_only:
        print(json.dumps(verify_artifacts(profile), indent=2))
        return
    runtime = AdapterRuntime(profile)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(runtime))
    threading.Thread(target=runtime.load, daemon=True).start()
    LOG.info("Serving 7B at http://127.0.0.1:%s; inspect /health before use", args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
