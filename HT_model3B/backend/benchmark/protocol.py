"""Method registry shared by the runner, worker and review schema."""
from dataclasses import asdict
from typing import Literal, get_args

from app.rag.components import RagComponents

MethodName = Literal["M1", "M2", "M3", "M4", "B0", "B1", "B2", "P", "P+FT",
    "P-no-query-normalization", "P-no-bm25", "P-no-domain-ranking",
    "P-no-product-context", "P-no-postcheck", "P-no-rule-routing"]
METHOD_NAMES = get_args(MethodName)
ABLATIONS = {
    "P-no-query-normalization": "query_normalization",
    "P-no-bm25": "bm25",
    "P-no-domain-ranking": "domain_ranking",
    "P-no-product-context": "product_context",
    "P-no-postcheck": "postcheck",
    "P-no-rule-routing": "rule_routing",
}


def method_spec(method):
    if method not in METHOD_NAMES:
        raise ValueError(f"Unknown method: {method}")
    kind = ("plain" if method in {"M2", "B1"} else "basic_rag" if method == "B2"
            else "rules" if method in {"M1", "B0"} else "proposed")
    components = RagComponents()
    if method in ABLATIONS:
        components = components.without(ABLATIONS[method])
    return {"method": method, "kind": kind,
            "provider": "hf_lora" if method in {"M4", "P+FT"} else "ollama",
            "components": asdict(components) if kind == "proposed" else None,
            "removed_component": ABLATIONS.get(method),
            "curated_faq_rules": method == "B0",
            "history_policy": "stateless_rules_receiving_fixed_history" if kind == "rules" else "fixed_input_history",
            "bm25_ablation_policy": "Remove lexical candidates/contribution; retain vector coefficient 0.60, ranking and threshold unchanged."}
