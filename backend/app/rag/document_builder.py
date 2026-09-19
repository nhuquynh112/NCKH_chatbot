from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.rag.product_schema import (
    ProductRecord,
    ProductValidationIssue,
    format_price_vnd,
    load_product_records,
)


def product_to_rag_document(product: ProductRecord) -> dict[str, Any]:
    specs = "\n".join(
        f"- {key}: {value}"
        for key, value in product.specifications.items()
    )
    specs_block = f"\n\nThông số kỹ thuật:\n{specs}" if specs else ""
    content = (
        f"{product.name} mã {product.sku} thuộc nhóm {product.category}. "
        f"Hãng: {product.brand or 'chưa có dữ liệu'}. "
        f"Giá niêm yết: {format_price_vnd(product.price)}. "
        f"Bảo hành: {product.warranty_months} tháng. "
        f"Mô tả: {product.description}."
        f"{specs_block}"
    )
    if product.verification_status == "official_verified":
        content += f"\n\nThông số được đối chiếu nguồn hãng ngày {product.verified_at}."

    return {
        "id": product.sku,
        "type": "product",
        "title": product.name,
        "content": content,
        "metadata": {
            "product_id": product.id,
            "slug": product.slug,
            "sku": product.sku,
            "category": product.category,
            "brand": product.brand,
            "source": "techcare_products.json",
            "verification_status": product.verification_status,
            "verified_at": product.verified_at,
            "source_urls": json.dumps(list(product.source_urls), ensure_ascii=False),
        },
    }


def build_product_rag_documents(
    products_path: Path,
) -> tuple[list[dict[str, Any]], list[ProductValidationIssue]]:
    products, issues = load_product_records(products_path)
    documents = [product_to_rag_document(product) for product in products]
    return documents, issues


def write_product_rag_documents(
    products_path: Path,
    output_path: Path,
) -> tuple[int, list[ProductValidationIssue]]:
    documents, issues = build_product_rag_documents(products_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(documents, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return len(documents), issues
