"""Publish measured outputs and a report without inventing human quality outcomes."""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from controlled_study.analyze import analyze
from controlled_study.prepare import ARCHIVE, load, sha, write_new


def number(value):
    return "chưa xác định" if value is None else f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--profile", type=Path, help="Optional local artifact profile, for exporting verified small model metadata only")
    args = parser.parse_args()
    root = args.root.resolve()
    result = analyze(root)
    target = root / "analysis"
    target.mkdir(exist_ok=False)
    write_new(target / "statistics.json", result)
    rows = [json.loads(line) for line in (root / "runs/results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    columns = ["repeat", "configuration", "phase", "case_id", "category", "status", "mode", "llm_called",
               "final_pipeline_ms", "whole_case_wall_ms", "error", "question", "input_history", "answer"]
    with (target / "responses.csv").open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            actual = row["result"]
            writer.writerow({"repeat": row["repeat"], "configuration": row["configuration"], "phase": row["phase"],
                             "case_id": row["case_id"], "category": row["category"], "status": actual["status"],
                             "mode": actual.get("mode"), "llm_called": actual.get("llm_called", False),
                             "final_pipeline_ms": actual.get("latency_ms"), "whole_case_wall_ms": row["wall_ms"],
                             "error": json.dumps(actual.get("error"), ensure_ascii=False) if actual.get("error") else "",
                             "question": row["question"], "input_history": json.dumps(row["input_history"], ensure_ascii=False),
                             "answer": actual.get("answer", "")})
    if args.profile:
        from model_serving.server import verify_artifacts
        profile = load(args.profile)
        identity = verify_artifacts(profile)
        meta = root / "artifact_metadata"
        meta.mkdir(exist_ok=False)
        base, adapter = Path(profile["checkpoint_path"]), Path(profile["adapter_path"])
        for source, name in ((base / "config.json", "base_config.json"),
                             (base / "generation_config.json", "generation_config.json"),
                             (base / "checkpoint_manifest.json", "checkpoint_manifest.json"),
                             (adapter / "adapter_config.json", "adapter_config.json"),
                             (ARCHIVE / "training_run.original.json", "training_run.original.json")):
            shutil.copyfile(source, meta / name)
        write_new(meta / "verification.json", {"verified_utc": datetime.now(timezone.utc).isoformat(),
                                              "identity": identity, "no_weights_copied": True,
                                              "files": {path.name: sha(path) for path in meta.iterdir() if path.is_file()},
                                              "note": "Small metadata copied after collection from artifacts verified by the same loader. Historical profile benchmark_role is not the new study design; see protocol.json."})
    manifest = load(root / "runs/manifest.json")
    protocol = load(root / "protocol.json")
    fixed = {entry["configuration"]: entry for entry in result["by_configuration_phase"] if entry["phase"] == "fixed"}
    report = ["# Thực nghiệm có kiểm soát trên 60 ca mới", "",
              f"Thời gian UTC: {manifest['started_utc']} đến {manifest.get('finished_utc')}. "
              f"Commit đăng ký trước: `{manifest['preregistration_commit']}`. "
              f"SHA-256 lock: `{result['source_lock_sha256']}`.", "",
              "Bộ mới có 24 ca S, 16 H, 12 O và 8 T, do AI hỗ trợ soạn và chưa được người độc lập duyệt. "
              "Đề, snapshot và cấu hình được khóa trước khi model nhận câu mới. Rà trùng từ vựng với đúng dữ liệu train/validation "
              "và 100 kịch bản cũ không phát hiện cặp vượt ngưỡng; điều này không chứng minh độc lập ngữ nghĩa hay đại diện khách hàng thật.", "",
              "Hai điều kiện adapter dùng cùng checkpoint 7B NF4/BF16, Transformers/PEFT, tokenizer, GPU RTX 3060 và tham số sinh. "
              "P_base không nạp adapter; P_ft nạp adapter lịch sử, không huấn luyện thêm. B1/B2 dùng lại thuật toán cũ với transport HF chung; "
              "P_no_memory và P_no_rules chỉ tắt component đã đăng ký. P FP16/Ollama cũ giữ riêng, không trộn vào số đo của bộ mới.", "",
              f"Kiểm tra thực tế: các runtime dùng cùng bộ phiên bản thư viện = {result['same_runtime_packages']}; "
              f"GPU ghi trong các generation thành công: {', '.join(result['generation_gpus'])}. "
              "Hash checkpoint/adapter, condition và NF4/BF16 được đối chiếu cho từng identity và generation đã ghi. "
              "Đối chiếu prompt base/FT được báo riêng phía dưới; nếu có sai khác, không được xem là phép cô lập adapter đạt yêu cầu.", "",
              f"Đã ghi {result['fixed_attempts']} lượt cố định (60 ca × 6 cấu hình × 3 vòng) và {result['rollout_attempts']} lượt rollout bổ sung. "
              "Lịch sử fixture ở lượt cố định giống nhau giữa mọi cấu hình. Rollout dùng bốn kịch bản H đã đăng ký, lịch sử do mỗi cấu hình sinh; "
              "không gộp hai chế độ hoặc coi repeat là câu hỏi độc lập.", "",
              "## Kết quả thực thi trên lượt cố định", "",
              "| Cấu hình | Ca / lượt | Lỗi | Có thử gọi LLM cuối | Trung vị ms | Trung bình ms | P95 ms |", "|---|---:|---:|---:|---:|---:|---:|"]
    for label in protocol["conditions"]:
        item = fixed[label]
        latency = item["final_pipeline_ms_successful"]
        errors = sum(value for key, value in item["statuses"].items() if key not in ("ok", "no_rule_match"))
        report.append(f"| {label} | 60 / {item['attempts']} | {errors} | {item['final_llm_attempted_cases']} | "
                      f"{number(latency['median'])} | {number(latency['mean'])} | {number(latency['p95'])} |")
    report += ["", "Latency chỉ tổng hợp các lượt thành công; tỷ lệ lỗi và số attempt dùng toàn bộ mẫu. "
               "P95 nội suy tuyến tính tại `(n-1)*0,95`, không báo khi ít hơn 20 mẫu. "
               "Đây là pipeline lượt cuối, gồm cả nhánh luật/FAQ, không phải toàn bộ thời gian suy luận thuần của LLM. "
               "Không đo thời gian hiển thị trình duyệt hoặc TTFT; thời gian nạp model và warmup nằm ngoài mẫu độ trễ truy vấn. "
               "Thống kê tách nhánh và từng vòng lặp có trong statistics.json. Không quy ít gọi LLM thành chất lượng tốt hơn.", "",
               "Số generation chạm giới hạn 384 token đầu ra được lưu riêng; chạm giới hạn có thể làm câu trả lời thiếu ý, "
               "nhưng không tự được gán điểm chất lượng hoặc xem là lỗi context. Danh sách ca lỗi và thông báo gốc có trong statistics.json.", "",
               "## Chênh lệch ghép cặp và độ ổn định", "",
               "| Phải trừ trái | Ca đủ 3 lần thành công hai bên | Chênh trung bình ms | CI 95% ms |", "|---|---:|---:|---|"]
    for label, item in result["paired_operational_differences"].items():
        paired = item["final_pipeline_ms"]
        interval = paired["ci95"]
        report.append(f"| {label} | {paired['cases']} | {number(paired['difference_mean'])} | "
                      + (f"[{number(interval[0])}; {number(interval[1])}] |" if interval else "chưa xác định |"))
    report += ["", "Mỗi ca được lấy trung bình trong ba vòng rồi ghép cặp; bootstrap 5.000 lần theo family, seed 20261105. "
               "Giữ các repeat trong cùng đơn vị, không dùng n=180 như 180 câu độc lập. "
               "Mẫu latency ghép cặp loại ca không đủ ba lần thành công và phải đọc cùng tỷ lệ lỗi. "
               "Các khoảng tin cậy mang tính thăm dò, chưa hiệu chỉnh đa kiểm định, không đại diện biến động trên phần cứng khác.", "",
               f"Đối chiếu {len(result['paired_prompt_checks'])} cặp base/FT: {result['adapter_prompt_mismatches']} cặp khác prompt/lời gọi; "
               f"{result['adapter_pairs_with_any_llm_attempt']} cặp có thử gọi LLM, "
               f"{result['adapter_pairs_without_llm_calls']} cặp không gọi LLM. "
               f"Khác phản hồi ở cặp không gọi LLM: {len(result['non_llm_adapter_answer_mismatches'])}. "
               f"Số cặp cấu hình/ca có thay đổi trạng thái hoặc nội dung qua ba vòng: {len(result['repeated_output_variation'])}.", "",
               "Các ca lỗi giữ nguyên request, prompt, response nếu có, record và log. Lỗi context không có phản hồi thay thế; "
               "không diễn giải việc không có phát biểu do lỗi thành 0% phát biểu sai. "
               "Không chọn lại lần chạy thành công hoặc câu trả lời đẹp nhất.", "",
               "## Chất lượng và H1–H3", "",
               "Chưa có điểm/nhãn người chấm cho bộ mới nên chưa kết luận adapter cải thiện chất lượng, "
               "P giảm phát biểu ngoài nguồn, quản lý sản phẩm giảm nhầm, hoặc phân tuyến tiết kiệm chi phí mà giữ nguyên chất lượng. "
               "Hai phiếu mới chứa 360 phản hồi của repetition 1 đã đăng ký trước; hai người chấm độc lập, ẩn tên cấu hình trên phiếu. "
               "H1 cần nhãn phát biểu từ snapshot; H2 cần nhầm sản phẩm/chuyển chủ đề ở nhóm H; H3 cần chất lượng và từ chối nhầm bên cạnh số gọi/thời gian. "
               "Không dùng lại điểm của bộ 400/100 cũ cho phản hồi mới.", "",
               "Chi phí chỉ được đại diện bằng số yêu cầu LLM và số token ghi nhận, không phải tiền hoặc điện năng đã đo. "
               "Tải máy desktop, cache và thời điểm giữa các block còn biến động; hai warmup chat riêng mỗi block và việc đảo thứ tự không loại bỏ mọi yếu tố này. "
               "Lịch sử fixture là dữ liệu tình huống tổng hợp, không đại diện phân bố hội thoại thực địa. "
               "Các số liệu quan sát, kể cả không cải thiện hoặc có lỗi, đều được giữ trong hồ sơ.", "",
               "## Dùng trong báo cáo", "",
               "Có thể bổ sung thiết kế và bảng số liệu thực thi sau mục đánh giá P+FT cũ (một tiểu mục mới), giữ nguyên các bảng/điểm lịch sử. "
               "Phần kiểm định H1–H3 ghi rõ đang chờ hai phiếu và nhãn phát biểu mới; cập nhật chênh lệch chất lượng/CI sau khi chạy score_reviews. "
               "Không chèn kết luận cải thiện chất lượng từ bảng độ trễ. Hướng dẫn lệnh và phạm vi component ở README của controlled_study.", ""]
    with (root / "RESULTS.md").open("x", encoding="utf-8") as stream:
        stream.write("\n".join(report))
    inventory = {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
                 "collection_commit": manifest["preregistration_commit"],
                 "scope": "Exact bytes of public study files after collection/export; inventory excludes itself. Private rater mapping is committed by hash only.",
                 "files": {path.relative_to(root).as_posix(): {"sha256": sha(path), "bytes": path.stat().st_size}
                           for path in sorted(root.rglob("*")) if path.is_file()}}
    write_new(root / "evidence_inventory.json", inventory)
    print(json.dumps({"published": str(target), "observations": len(rows), "human_quality": "pending"}))


if __name__ == "__main__":
    main()
