"""Attach reviewed product facts and distinguish retailer from official sources."""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Iterable


from app.config import settings

VERIFICATION_PATH = settings.products_path.parent / "product_verified_specs.json"


@lru_cache(maxsize=8)
def _read_verification(path: str, modified_ns: int, size: int) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_verification_data(path: Path = VERIFICATION_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"verified_at": None, "products": {}}
    stat = path.stat()
    return _read_verification(str(path.resolve()), stat.st_mtime_ns, stat.st_size)


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
    preserve_store_fields: bool = False,
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
        if field in record and not (preserve_store_fields and field in product):
            merged[field] = record[field]

    specifications = deepcopy(merged.get("specifications") or {})
    for key in record.get("remove_specifications", []):
        specifications.pop(key, None)
    specifications.update(record.get("specifications") or {})
    merged["specifications"] = specifications
    merged["verification_status"] = record.get("status", "official_verified")
    merged["verified_at"] = record.get("verified_at", data.get("verified_at"))
    merged["source_urls"] = deepcopy(record.get("sources") or [])
    merged["canonical_slug"] = canonical_slug
    for field in ("verification_note", "price_basis", "collected_at", "warranty_source_text",
                  "warranty_policy", "selected_color", "sku"):
        if field in record:
            merged[field] = deepcopy(record[field])
    # Existing normalization already uses the textual warranty when months
    # are unknown. Preserve days, component policies and invoice conditions.
    if merged.get("warranty_months") is None and record.get("warranty_source_text"):
        merged["warranty"] = record["warranty_source_text"]
    return merged


def merge_verified_products(products: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    data = load_verification_data()
    return [merge_verified_product(product, data) for product in products]

