"""Merge the finished local QLoRA run into portable dense weights, offline."""
import argparse
import gc
import json
import os
from pathlib import Path
import time
os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run = json.loads((args.run_dir / "run.json").read_text(encoding="utf-8"))
    if run["status"] != "completed":
        parser.error("Training must finish successfully before export")
    target = args.run_dir / "merged_dense"
    if target.exists():
        parser.error("Export exists; preserve it")
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    started = time.perf_counter()
    checkpoint = Path(run["checkpoint_dir"])
    model = AutoModelForCausalLM.from_pretrained(checkpoint, device_map={"":0}, dtype=torch.bfloat16,
                attn_implementation="sdpa", local_files_only=True, trust_remote_code=False)
    model = model.dequantize(dtype=torch.bfloat16)
    # Transformers 5.19 retains the NF4 deserialization conversion after
    # dequantization. Dense Qwen2 weights must not be serialized back to NF4.
    if model.config.model_type != "qwen2":
        raise RuntimeError("This export workaround is limited to the checked Qwen2 architecture")
    model._weight_conversions = [entry for entry in getattr(model,"_weight_conversions",[])
        if not any(type(op).__name__.startswith("Bnb4bit") for op in getattr(entry,"operations",[]))]
    if getattr(model, "is_quantized", False):
        raise RuntimeError("Dequantization did not finish")
    model = PeftModel.from_pretrained(model, args.run_dir / "adapter", is_trainable=False, local_files_only=True)
    model = model.merge_and_unload(safe_merge=True).to(dtype=torch.bfloat16)
    if any("lora_" in name for name,_ in model.named_parameters()):
        raise RuntimeError("Unmerged adapter parameters")
    if any(not torch.isfinite(parameter).all().item() for parameter in model.parameters()):
        raise RuntimeError("Nonfinite merged weights")
    model.config.use_cache = True
    model.save_pretrained(target, safe_serialization=True, max_shard_size="1GB")
    AutoTokenizer.from_pretrained(checkpoint, local_files_only=True).save_pretrained(target)
    result = {"source":"NF4 checkpoint dequantized to BF16, adapter merged; final GGUF must be evaluated independently",
              "adapter":str((args.run_dir / "adapter").resolve()), "checkpoint":run["checkpoint"],
              "seconds":round(time.perf_counter()-started,3), "merged_bytes":sum(p.stat().st_size for p in target.glob("*.safetensors")),
              "cuda_peak_bytes":torch.cuda.max_memory_allocated(), "dtype":"bfloat16"}
    (args.run_dir / "merge.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="checkpoint"},indent=2),flush=True)
    del model
    gc.collect()
    torch.cuda.empty_cache()
if __name__ == "__main__":
    main()

