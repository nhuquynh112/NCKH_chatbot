"""Anonymous transport views; never change a benchmark answer or its pipeline."""
import secrets
from uuid import uuid4


def create_systems(methods):
    order = list(methods)
    secrets.SystemRandom().shuffle(order)
    return [{"system_id": str(uuid4()), "label": f"Trợ lý {chr(65 + index)}", "method": method}
            for index, method in enumerate(order)]


def public_systems(systems):
    return [{"system_id": row["system_id"], "label": row["label"]} for row in systems]


def public_record(record, systems):
    system = next(row for row in systems if row["method"] == record["method"])
    result = record["result"]
    # Use an allowlist: model, pipeline, mode, tool flags, timing and raw errors
    # stay in the coordinator's files. The answer/history are copied verbatim.
    return {**{key: record[key] for key in ("run_id", "session_id", "case_id", "question", "fixed_history", "created_at")},
            "system_id": system["system_id"], "system_label": system["label"],
            # no_rule_match is a completed baseline fallback, not a transport
            # failure. Keep that routing detail only in the original result.
            "result": {"status": "ok" if result["status"] == "no_rule_match" else result["status"],
                       "answer": result.get("answer", "")}}
