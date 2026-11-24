import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from benchmark.protocol import MethodName


class HistoryTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_-]+$")
    category: str = Field(min_length=1)
    question: str = Field(min_length=1)
    expected_answer: str | None = None
    required_facts: list[str] | None = None
    forbidden_claims: list[str] | None = None
    expected_source: str | None = None
    expected_source_ids: list[str] | None = None
    risk_level: Literal["low", "medium", "high"] = "medium"
    notes: str | None = None
    evidence: list[str] = Field(default_factory=list)
    # Only user turns: every method must generate its own setup answers.
    history_questions: list[str] = Field(default_factory=list)
    history: list[HistoryTurn] = Field(default_factory=list)
    family_id: str | None = None

    @model_validator(mode="after")
    def require_evidence_for_gold(self):
        if (self.expected_answer or self.required_facts) and not self.evidence:
            raise ValueError("Gold answers/facts require documented source evidence")
        if self.history and self.history_questions:
            raise ValueError("Use fixed history OR generated setup questions, not both")
        return self


class HumanReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    method: MethodName
    case_id: str
    repeat: int = 1
    reviewer: str | None = None
    correctness: Literal["correct", "incorrect", "insufficient_information", "no_evidence", "not_applicable"] | None = None
    grounded: bool | None = None
    hallucination: bool | None = None
    policy_compliant: bool | None = None
    appropriate_abstention: bool | None = None
    correct_sources: bool | None = None
    relevant: bool | None = None
    notes: str | None = None


def load_cases(path: Path):
    text = path.read_text(encoding="utf-8")
    records = [json.loads(line) for line in text.splitlines() if line.strip()] if path.suffix == ".jsonl" else json.loads(text)["cases"]
    cases = [Case.model_validate(row) for row in records]
    ids = [case.id for case in cases]
    if not cases or len(set(ids)) != len(ids):
        raise ValueError("Dataset must contain unique case IDs and at least one case")
    return cases
