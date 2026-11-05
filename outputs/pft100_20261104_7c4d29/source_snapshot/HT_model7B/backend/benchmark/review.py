"""Validate a completed human review and create a new summary without replacing raw results."""
import argparse
import json
from pathlib import Path
from uuid import uuid4

from benchmark.run import export_tables
from benchmark.schema import HumanReview


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in (args.run / "results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    reviews = [HumanReview.model_validate_json(line).model_dump() for line in args.reviews.read_text(encoding="utf-8").splitlines() if line.strip()]
    key = lambda row:(row["run_id"],row["method"],row.get("case_id"),row.get("repeat",1))
    allowed, seen = {key(r) for r in rows}, set()
    for review in reviews:
        if key(review) not in allowed or key(review) in seen:
            parser.error("Review has an unknown/duplicate result key")
        seen.add(key(review))
        if any(review.get(k) is not None for k in ("correctness","grounded","hallucination","policy_compliant","appropriate_abstention","correct_sources","relevant")) and not review.get("reviewer"):
            parser.error("Scored reviews require a reviewer name")
    directory = args.run / ("reviewed-" + uuid4().hex[:8])
    directory.mkdir(exist_ok=False)
    (directory / "reviews.jsonl").write_text("\n".join(json.dumps(r,ensure_ascii=False) for r in reviews)+"\n",encoding="utf-8")
    export_tables(directory,rows,reviews)
    print(directory)


if __name__ == "__main__":
    main()
