"""Run the locked study serially; retain every attempt and keep warmups separate."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

from controlled_study.prepare import BACKEND, REPO, sha, code_sha, load, write_new
from controlled_study.server import MODEL


def http(url, value=None, timeout=5):
    request = urllib.request.Request(url, data=json.dumps(value).encode() if value is not None else None,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def verify_lock(root):
    lock = load(root / "lock.json")
    for name, digest in lock["input_sha256"].items():
        if sha(root / name) != digest:
            raise RuntimeError("Locked input changed: " + name)
    for name, digest in lock["source_sha256"].items():
        if code_sha(REPO / name) != digest:
            raise RuntimeError("Locked source changed: " + name)
    return lock


def gpu_state():
    try:
        return subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total,memory.free,utilization.gpu,temperature.gpu",
                                        "--format=csv,noheader"], text=True, timeout=8).strip()
    except (OSError, subprocess.SubprocessError) as error:
        return "unavailable: " + str(error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--gpu-python", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8013)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    lock = verify_lock(root)
    protocol = load(root / "protocol.json")
    cases = {c["id"]: c for c in load(root / "cases.json")["cases"]}
    out = root / "runs"
    if out.exists() and not args.resume:
        raise RuntimeError("Results already exist; explicit --resume continues without rerunning recorded attempts")
    out.mkdir(exist_ok=True)
    manifest_path = out / "manifest.json"
    if not manifest_path.exists():
        git = ["git", "-c", "safe.directory=" + REPO.as_posix(), "-C", str(REPO)]
        write_new(manifest_path, {"status": "running", "started_utc": datetime.now(timezone.utc).isoformat(),
                                 "preregistration_commit": subprocess.check_output(git + ["rev-parse", "HEAD"], text=True).strip(),
                                 "lock_sha256": sha(root / "lock.json"), "protocol_sha256": sha(root / "protocol.json"),
                                 "worker_python": sys.executable, "gpu_python": str(args.gpu_python),
                                 "model_profile_sha256": sha(args.profile), "gpu_at_start": gpu_state(),
                                 "expected_fixed_input_attempts": 60 * 3 * 6,
                                 "expected_rollout_attempts": 4 * 3 * 4,
                                 "quality_scores": "pending two independent humans; no automatic grades"})
    else:
        if load(manifest_path)["lock_sha256"] != sha(root / "lock.json"):
            raise RuntimeError("Resume lock mismatch")
    url = f"http://127.0.0.1:{args.port}"
    try:
        http(url + "/health")
    except Exception:
        pass
    else:
        raise RuntimeError("Experimental port already occupied; do not terminate an unowned server")
    server = None
    server_log = None
    condition = None
    records_path = out / "results.jsonl"
    known = []
    if records_path.exists():
        known = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    completed = {(r["repeat"], r["configuration"], r["phase"], r["case_id"]) for r in known}
    collected = len(completed)

    def stop_server():
        nonlocal server, server_log, condition
        if server is not None:
            try:
                http(url + "/shutdown", {}, timeout=5)
                server.wait(timeout=30)
            except Exception:
                if server.poll() is None:
                    # Only this Popen tree is owned by the study.
                    subprocess.run(["taskkill", "/PID", str(server.pid), "/T", "/F"], capture_output=True)
                    server.wait(timeout=15)
            server = None
            server_log.close()
            server_log = None
            condition = None

    def start_server(desired, block):
        nonlocal server, server_log, condition
        if condition == desired and server is not None and server.poll() is None:
            return
        stop_server()
        log_path = block / "server.log"
        server_log = log_path.open("ab")
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8",
               "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
        command = [str(args.gpu_python), "-X", "utf8", "-B", "-u", "-m", "controlled_study.server",
                   "--profile", str(args.profile), "--condition", desired, "--port", str(args.port)]
        server = subprocess.Popen(command, cwd=BACKEND, env=env, stdout=server_log, stderr=subprocess.STDOUT,
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        write_new(block / ("server_launch_" + str(server.pid) + ".json"),
                  {"pid": server.pid, "command": command, "gpu_before": gpu_state()})
        deadline = time.monotonic() + 360
        last = None
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise RuntimeError("Owned GPU server exited; inspect " + str(log_path))
            try:
                state = http(url + "/health", timeout=3)
                last = state
                if state.get("status") == "not_ready":
                    raise RuntimeError("GPU runtime not_ready: " + str(state.get("error")))
                if state.get("status") == "ready":
                    if state.get("condition") != desired or state.get("adapter_loaded") != (desired == "ft"):
                        raise RuntimeError("GPU condition mismatch")
                    condition = desired
                    return
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
            time.sleep(1)
        raise RuntimeError("GPU readiness deadline; last state=" + str(last))

    def collect(repeat, label, case, phase, block):
        nonlocal collected
        key = (repeat, label, phase, case["id"])
        if key in completed:
            return
        verify_lock(root)
        spec = protocol["conditions"][label]
        folder = block / phase / case["id"]
        folder.mkdir(parents=True, exist_ok=False)
        input_case = {key: case[key] for key in ("id", "category", "question", "history", "history_questions")}
        if phase == "rollout":
            input_case.update(history=[], history_questions=case["rollout_questions"])
        request = {"method": spec["method"], "condition": spec["adapter"], "case": input_case,
                   "database": str(root / "frozen_products.db"), "corpus": str(root / "corpus"),
                   "snapshot_timestamp": "2026-10-28T09:13:35.517911+00:00", "timeout": 120,
                   "ollama_url": "http://127.0.0.1:11434", "hf_url": url,
                   "plain_prompt": (root / "plain_prompt.txt").read_text(encoding="utf-8"),
                   "journal_dir": str(folder)}
        write_new(folder / "request.json", request)
        before = gpu_state()
        started = time.perf_counter()
        deadline = 600 if phase == "rollout" else 180
        try:
            process = subprocess.run([sys.executable, "-X", "utf8", "-B", "-m", "controlled_study.worker",
                                      str(folder / "request.json"), str(folder / "response.json")], cwd=BACKEND,
                                     capture_output=True, timeout=deadline,
                                     env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"})
            (folder / "worker.log").write_bytes(process.stdout + b"\n" + process.stderr)
            if process.returncode or not (folder / "response.json").exists():
                raise RuntimeError("Worker failed; inspect worker.log")
            result = load(folder / "response.json")
        except subprocess.TimeoutExpired as error:
            (folder / "worker.log").write_bytes((error.stdout or b"") + b"\n" + (error.stderr or b""))
            calls = []
            for start in sorted(folder.glob("call-*-started.json")):
                end = start.with_name(start.name.replace("-started", "-completed"))
                calls.append(load(end) if end.exists() else {**load(start), "error": "Parent deadline; completion unknown"})
            result = {"status": "timeout", "answer": "", "error": "Whole-case deadline exceeded", "calls": calls,
                      "llm_called": any(c["phase"] == "final" for c in calls),
                      "setup_llm_called": any(c["phase"] == "setup" for c in calls)}
        except Exception as error:
            result = {"status": "error", "answer": "", "error": str(error), "calls": []}
        record = {"repeat": repeat, "configuration": label, "phase": phase, "case_id": case["id"],
                  "family": case["family"], "category": case["category"], "question": case["question"],
                  "input_history": input_case["history"], "history_questions": input_case["history_questions"],
                  "result": result, "wall_ms": (time.perf_counter() - started) * 1000,
                  "deadline_seconds": deadline, "gpu_before": before,
                  "finished_utc": datetime.now(timezone.utc).isoformat()}
        write_new(folder / "record.json", record)
        with records_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            stream.flush()
        completed.add(key)
        collected += 1
        progress = {"collected": collected, "total": 1128, "repeat": repeat,
                    "configuration": label, "phase": phase, "case_id": case["id"],
                    "status": result["status"], "updated_utc": datetime.now(timezone.utc).isoformat()}
        (root / "progress.json").write_text(json.dumps(progress), encoding="utf-8")
        print(json.dumps(progress), flush=True)
        if result["status"] == "not_ready":
            raise RuntimeError("Readiness lost; stop collection, preserve all attempts")

    try:
        for item in protocol["schedule"]:
            repeat, label = item["repeat"], item["condition"]
            block = out / f"r{repeat}" / label
            block.mkdir(parents=True, exist_ok=True)
            start_server(protocol["conditions"][label]["adapter"], block)
            warmup_path = block / "warmup.json"
            if not warmup_path.exists():
                warmups = []
                for _ in range(protocol["warmup"]["per_block_generations"]):
                    warmups.append(http(url + "/generate", {"model": MODEL,
                        "system_prompt": protocol["warmup"]["system"], "user_prompt": protocol["warmup"]["user"],
                        "max_new_tokens": 384, "num_ctx": 4096, "temperature": 0, "repeat_penalty": 1.0,
                        "timeout_seconds": 120}, timeout=125))
                write_new(warmup_path, {"excluded_from_main": True, "responses": warmups})
            write_new(block / "runtime_health.json", http(url + "/health")) if not (block / "runtime_health.json").exists() else None
            for case_id in item["case_ids"]:
                collect(repeat, label, cases[case_id], "fixed", block)
            if label in protocol["rollout_conditions"]:
                for case_id in protocol["rollout_case_ids"]:
                    collect(repeat, label, cases[case_id], "rollout", block)
        manifest = load(manifest_path)
        manifest.update(status="completed", attempts=collected, finished_utc=datetime.now(timezone.utc).isoformat())
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as error:
        manifest = load(manifest_path)
        manifest.update(status="interrupted", attempts=collected, error=str(error),
                        interrupted_utc=datetime.now(timezone.utc).isoformat())
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        raise
    finally:
        stop_server()


if __name__ == "__main__":
    main()
