"""Apply auditable, official-source product corrections to catalog records."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Iterable


VERIFICATION_PATH = (
    Path(__file__).resolve().parents[1] / "rag_data" / "product_verified_specs.json"
)


def load_verification_data(path: Path = VERIFICATION_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"verified_at": None, "products": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def verification_record_for_slug(
    slug: str | None,
    data: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]] | tuple[None, None]:
    if not slug:
        return None, None
    data = data or load_verification_data()
    for canonical_slug, record in data.get("products", {}).items():
        aliases = {canonical_slug, *(record.get("catalog_slugs") or [])}
        if slug in aliases:
            return canonical_slug, record
    return None, None


def merge_verified_product(
    product: dict[str, Any],
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a copy with reviewed corrections and provenance attached."""
    data = data or load_verification_data()
    merged = deepcopy(product)
    canonical_slug, record = verification_record_for_slug(merged.get("slug"), data)
    if not record:
        merged["verification_status"] = "store_catalog_only"
        merged["verification_note"] = (
            "Cấu hình cửa hàng chưa được đối chiếu vì tên sản phẩm thiếu mã SKU/part number."
        )
        return merged

    for field in ("name", "slug", "description", "price", "warranty_months"):
        if field in record:
            merged[field] = record[field]

    specifications = deepcopy(merged.get("specifications") or {})
    for key in record.get("remove_specifications", []):
        specifications.pop(key, None)
    specifications.update(record.get("specifications") or {})
    merged["specifications"] = specifications
    merged["verification_status"] = record.get("status", "official_verified")
    merged["verified_at"] = data.get("verified_at")
    merged["source_urls"] = deepcopy(record.get("sources") or [])
    merged["canonical_slug"] = canonical_slug
    return merged


def merge_verified_products(products: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    data = load_verification_data()
    return [merge_verified_product(product, data) for product in products]

