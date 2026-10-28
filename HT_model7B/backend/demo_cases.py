"""Load only inference inputs from the existing research test pack."""
from benchmark.schema import load_cases


def load_test_inputs(path):
    return {case.id: {"id": case.id, "category": case.category, "question": case.question,
                     "history": [turn.model_dump() for turn in case.history],
                     "history_questions": list(case.history_questions)} for case in load_cases(path)}
