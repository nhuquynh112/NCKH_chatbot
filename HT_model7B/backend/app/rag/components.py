"""Architecture switches for controlled experiments; application defaults stay fully enabled."""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class RagComponents:
    query_normalization: bool = True
    bm25: bool = True
    domain_ranking: bool = True
    product_context: bool = True
    postcheck: bool = True
    rule_routing: bool = True

    def without(self, name):
        if name not in self.__dataclass_fields__:
            raise ValueError(f"Unknown RAG component: {name}")
        return replace(self, **{name: False})
