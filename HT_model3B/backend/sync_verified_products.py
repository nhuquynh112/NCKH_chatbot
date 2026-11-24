"""Synchronize reviewed product facts into the live Product table."""

from __future__ import annotations

import sys

from app.database import SessionLocal
from app.models import Product
from app.product_enrichment import load_verification_data, merge_verified_product


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    verification = load_verification_data()
    changed = 0
    verified = 0
    unresolved: list[str] = []

    with SessionLocal() as db:
        products = db.query(Product).order_by(Product.id.asc()).all()
        for product in products:
            original = {
                "slug": product.slug,
                "name": product.name,
                "description": product.description,
                "price": float(product.price),
                "warranty_months": product.warranty_months,
                "specifications": product.specifications or {},
            }
            merged = merge_verified_product(original, verification)
            if merged.get("verification_status") == "store_catalog_only":
                unresolved.append(f"{product.slug}: {product.name}")
                continue
            verified += 1
            updates = {
                "slug": merged["slug"],
                "name": merged["name"],
                "description": merged["description"],
                "price": merged["price"],
                "warranty_months": merged["warranty_months"],
                "specifications": merged["specifications"],
            }
            if any(original[key] != value for key, value in updates.items()):
                for key, value in updates.items():
                    setattr(product, key, value)
                changed += 1
        db.commit()

    print(f"Verified products: {verified}")
    print(f"Updated database rows: {changed}")
    print(f"Need exact SKU/part number: {len(unresolved)}")
    for item in unresolved:
        print(f"- {item}")


if __name__ == "__main__":
    main()
