"""Reproduce the validated 3B QLoRA setup on reviewed, local training data."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import math
import os
from pathlib import Path
import statistics
import time
import tempfile

from training.data import AssistantCollator, encode_example, normalized, read_jsonl, sha256_file

PROJECT = Path(os.environ.get("CHATBOT_PROJECT_DIR", str(Path(__file__).resolve().parents[2])))
ROOT = Path(os.environ.get("CHATBOT_WORK_DIR", "D:/NCKH/Codex" if os.name == "nt" else str(Path(tempfile.gettempdir()) / "nckh-chatbot")))
MODEL_DIRECTORY = PROJECT / "backend/models/techcare-support-3b-v1"


def load_frozen_cases():
    # The original eight development cases are bundled as data, without
    # importing a benchmark application or using either held-out test file.
    path = Path(__file__).with_name("development_cases.json")
    return json.loads(path.read_text(encoding="utf-8")), sha256_file(path)


def benchmark(model, tokenizer, cases, system, torch):
    model.eval()
    rows = []
    for case in cases:
        messages = [{"role": "system", "content": system}, {"role": "user", "content":
                    f"NGỮ CẢNH:\n{case['context']}\nCÂU HỎI:\n{case['question']}"}]
        inputs = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                                return_dict=True, return_tensors="pt").to("cuda")
        torch.cuda.synchronize()
        start = time.perf_counter()
        with torch.inference_mode():
            output = model.generate(**inputs, do_sample=False, max_new_tokens=384,
                                    pad_token_id=tokenizer.pad_token_id, use_cache=True)
        torch.cuda.synchronize()
        answer = tokenizer.decode(output[0, inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
        folded = normalized(answer)
        missing = [s for s in case["required"] if normalized(s) not in folded]
        forbidden = [s for s in case["forbidden"] if normalized(s) in folded]
        rows.append({"case": case["id"], "answer": answer, "missing": missing, "forbidden": forbidden,
                     "passed": not missing and not forbidden,
                     "ms": round((time.perf_counter() - start) * 1000, 2)})
    return {"cases": len(rows), "passed": sum(row["passed"] for row in rows),
            "median_ms": statistics.median(row["ms"] for row in rows), "results": rows,
            "interpretation": "Keyword checks require human review; HF latency is not directly comparable to Ollama."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=MODEL_DIRECTORY / "data")
    parser.add_argument("--checkpoint", type=Path, default=ROOT / "training_cache/qwen25_3b_nf4")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=-1, help="-1: requested epoch count; 2: compatibility trial")
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--epochs", type=int, choices=[1,2], default=2)
    parser.add_argument("--rank", type=int, choices=[8,16], default=16)
    parser.add_argument("--all-linear", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--learning-rate", type=float, choices=[5e-5,1e-4], default=1e-4)
    args = parser.parse_args()
    if args.run_dir.exists():
        parser.error("Run directory exists; preserve every experiment rather than overwrite")
    if args.steps not in {-1, 2} or args.max_length != 512:
        parser.error("Supported reproduction: two-step trial or 1–2 epochs, 512 tokens")
    os.environ.update(HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
                      TRANSFORMERS_OFFLINE="1", WANDB_DISABLED="true")
    manifest = json.loads((args.data / "manifest.json").read_text(encoding="utf-8"))
    if manifest["source_split"] != "train" or manifest.get("official_test_used_for_training") is not False:
        parser.error("Prepared source split is not safe for training")
    for split in ("train", "validation"):
        if sha256_file(args.data / f"{split}.jsonl") != manifest[f"{split}_sha256"]:
            parser.error(f"{split} changed since review/export")
    if not 20 <= manifest["accepted"] <= 200:
        parser.error("Reviewed sample count outside the bounded pilot")
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainerCallback, TrainingArguments, set_seed
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        parser.error("Verified CUDA/bfloat16 required; no CPU fallback")
    checkpoint_manifest = json.loads((args.checkpoint / "checkpoint_manifest.json").read_text(encoding="utf-8"))
    for item in checkpoint_manifest["files"]:
        local = args.checkpoint / item["name"]
        if local.stat().st_size != item["bytes"] or sha256_file(local) != item["local_sha256"]:
            parser.error("Checkpoint integrity check failed")
    set_seed(20261014)
    tokenizer = AutoTokenizer.from_pretrained(args.checkpoint, local_files_only=True, trust_remote_code=False)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    train_source = read_jsonl(args.data / "train.jsonl")
    validation_source = read_jsonl(args.data / "validation.jsonl")
    train_keys = {row["question_sha256"] for row in train_source}
    if {row["scenario_group"] for row in train_source} & {row["scenario_group"] for row in validation_source}:
        parser.error("Train/validation scenario family overlap")
    if train_keys & {row["question_sha256"] for row in validation_source}:
        parser.error("Train/validation question overlap")
    train = [encode_example(row, tokenizer, args.max_length) for row in train_source]
    validation = [encode_example(row, tokenizer, args.max_length) for row in validation_source]
    if len(train) != manifest["train_rows"] or len(validation) != manifest["validation_rows"]:
        parser.error("Prepared row counts changed")
    args.run_dir.mkdir(parents=True)
    run = {"status": "started", "started_utc": datetime.now(timezone.utc).isoformat(),
           "source": manifest, "checkpoint": checkpoint_manifest, "steps_requested": args.steps, "epochs_requested": args.epochs, "checkpoint_dir":str(args.checkpoint.resolve()),
           "max_length": args.max_length, "gpu": torch.cuda.get_device_name(0),
           "packages": {name: importlib.metadata.version(name) for name in
                        ("torch", "transformers", "peft", "bitsandbytes", "accelerate", "datasets")}}
    run_path = args.run_dir / "run.json"

    def save():
        run_path.write_text(json.dumps(run, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    class FiniteLoss(TrainerCallback):
        def on_log(self, args, state, control, logs=None, **kwargs):
            if any(isinstance(value, float) and not math.isfinite(value) for value in (logs or {}).values()):
                raise RuntimeError("Non-finite training metric; stop and preserve failure")

    save()
    try:
        torch.cuda.reset_peak_memory_stats()
        model = AutoModelForCausalLM.from_pretrained(args.checkpoint, device_map={"": 0},
                                                    dtype=torch.bfloat16, attn_implementation="sdpa",
                                                    local_files_only=True, trust_remote_code=False)
        if not getattr(model, "is_loaded_in_4bit", False):
            raise RuntimeError("Checkpoint did not load as 4-bit; refusing full-weight training")
        if any(parameter.device.type != "cuda" for parameter in model.parameters()):
            raise RuntimeError("Unexpected CPU/disk offload; the requested experiment must run on GPU")
        cases, fixture_hash = load_frozen_cases()
        run["benchmark_fixture_sha256"] = fixture_hash
        system = (PROJECT / "backend/rag_data/system_prompt.txt").read_text(encoding="utf-8")
        run["benchmark_prompt_sha256"] = sha256_file(PROJECT / "backend/rag_data/system_prompt.txt")
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True,
                                                gradient_checkpointing_kwargs={"use_reentrant": False})
        model = get_peft_model(model, LoraConfig(r=args.rank, lora_alpha=args.rank*2, lora_dropout=0.05, bias="none",
                                                task_type="CAUSAL_LM", target_modules="all-linear" if args.all_linear else ["q_proj", "v_proj"]))
        run["trainable_parameters"] = sum(p.numel() for p in model.parameters() if p.requires_grad)
        run["lora"] = {"rank": args.rank, "alpha": args.rank*2, "targets": "all-linear" if args.all_linear else ["q_proj", "v_proj"], "learning_rate": args.learning_rate}
        with model.disable_adapter(), torch.autocast("cuda",dtype=torch.bfloat16):
            run["base_behavior"] = benchmark(model, tokenizer, cases if args.steps == -1 else cases[:1], system, torch)
        save()
        model.config.use_cache = False
        config = TrainingArguments(output_dir=str(args.run_dir / "checkpoints"),
                                   per_device_train_batch_size=1, per_device_eval_batch_size=1,
                                   gradient_accumulation_steps=1 if args.steps == 2 else 4,
                                   num_train_epochs=args.epochs, max_steps=args.steps, learning_rate=args.learning_rate,
                                   bf16=True, fp16=False, gradient_checkpointing=True,
                                   gradient_checkpointing_kwargs={"use_reentrant": False},
                                   optim="adamw_torch", weight_decay=0.01, max_grad_norm=1.0,
                                   warmup_steps=0.1, logging_steps=1, logging_nan_inf_filter=False,
                                   save_strategy="no", report_to="none", dataloader_num_workers=0,
                                   remove_unused_columns=False, seed=20261014, data_seed=20261014)
        trainer = Trainer(model=model, args=config, train_dataset=train, eval_dataset=validation,
                          data_collator=AssistantCollator(tokenizer.pad_token_id), callbacks=[FiniteLoss()])
        run["validation_before"] = trainer.evaluate()
        save()
        started = time.perf_counter()
        outcome = trainer.train()
        run["training_seconds"] = round(time.perf_counter() - started, 3)
        run["training_metrics"] = outcome.metrics
        run["log_history"] = trainer.state.log_history
        run["validation_after"] = trainer.evaluate()
        model.save_pretrained(args.run_dir / "adapter", safe_serialization=True)
        tokenizer.save_pretrained(args.run_dir / "adapter")
        model.gradient_checkpointing_disable()
        model.config.use_cache = True
        with torch.autocast("cuda",dtype=torch.bfloat16):
            run["candidate_behavior"] = benchmark(model, tokenizer, cases if args.steps == -1 else cases[:1], system, torch)
        run["peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
        run["peak_reserved_bytes"] = torch.cuda.max_memory_reserved()
        run["status"] = "completed"
        run["deployment"] = "Candidate adapter only; main Ollama model unchanged"
        save()
        print(json.dumps({key: run[key] for key in ("status", "training_seconds", "trainable_parameters",
                                                   "peak_allocated_bytes", "validation_before", "validation_after")}, indent=2))
    except Exception as error:
        run["status"] = "failed"
        run["failure_type"] = type(error).__name__
        run["failure"] = str(error)[:1000]
        save()
        raise


if __name__ == "__main__":
    main()
