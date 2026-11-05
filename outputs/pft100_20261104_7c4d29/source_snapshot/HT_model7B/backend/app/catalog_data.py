"""Validate and synchronize catalog data without deleting customer records."""
import json
from pathlib import Path

from app.models import Product
from app.schemas.product import ProductCreate


def read_catalog(path: Path) -> list[dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("Catalog must be a nonempty JSON array")
    seen = set()
    for row in rows:
        ProductCreate.model_validate(row)
        if row["slug"] in seen:
            raise ValueError("Duplicate product slug: " + row["slug"])
        seen.add(row["slug"])
        if row.get("price", 0) <= 0:
            raise ValueError("Catalog price must be positive: " + row["slug"])
    return rows


def synchronize_catalog(db, rows: list[dict], replace_active: bool = False) -> dict:
    """Caller owns commit/rollback. Preserve IDs on updates and all other tables."""
    existing = {p.slug: p for p in db.query(Product).all()}
    empty = not existing
    added = updated = retired = 0
    fields = set(ProductCreate.model_fields)
    for row in rows:
        values = {key: value for key, value in row.items() if key in fields}
        values["is_active"] = True
        product = existing.get(row["slug"])
        if product is None:
            # A fresh clone uses the same IDs as the exported RAG catalog.
            if empty and row.get("id") is not None:
                values["id"] = int(row["id"])
            db.add(Product(**values))
            added += 1
        elif any(getattr(product, key) != value for key, value in values.items()):
            for key, value in values.items():
                setattr(product, key, value)
            updated += 1
    if replace_active:
        active_slugs = {row["slug"] for row in rows}
        for slug, product in existing.items():
            if slug not in active_slugs and product.is_active:
                product.is_active = False
                retired += 1
    db.flush()
    return {"added": added, "updated": updated, "retired": retired,
            "active": db.query(Product).filter(Product.is_active.is_(True)).count()}
