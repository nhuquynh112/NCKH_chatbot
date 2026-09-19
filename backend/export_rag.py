import json
import sys
from pathlib import Path

from app.database import SessionLocal
from app.models import Product, FAQ
from app.product_enrichment import merge_verified_product
from app.rag.document_builder import write_product_rag_documents

# ==========================================================
# Output Paths
# ==========================================================

OUTPUT_DIR = Path("rag_data")
OUTPUT_DIR.mkdir(exist_ok=True)

PRODUCT_JSON = OUTPUT_DIR / "techcare_products.json"
PRODUCT_MD = OUTPUT_DIR / "product_catalog_extended.md"
FAQ_MD = OUTPUT_DIR / "faq_generated.md"

# ==========================================================
# Export Product JSON
# ==========================================================


def export_products_json(db):

    products = (
        db.query(Product)
        .filter(Product.is_active == True)
        .all()
    )

    data = []

    for p in products:

        item = merge_verified_product(
            {
                "id": p.id,
                "slug": p.slug,
                "sku": p.slug,
                "name": p.name,
                "brand": p.brand,
                "category": p.category,
                "price": float(p.price),
                "description": p.description,
                "warranty_months": p.warranty_months,
                "specifications": p.specifications,
                "image_url": p.image_url,
            }
        )
        data.append(item)

    PRODUCT_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )

    print(f"✓ Exported {len(data)} products -> {PRODUCT_JSON}")


# ==========================================================
# Export Product Markdown
# ==========================================================


def export_products_markdown(db):

    products = (
        db.query(Product)
        .filter(Product.is_active == True)
        .all()
    )

    with open(PRODUCT_MD, "w", encoding="utf-8") as f:

        f.write("# DANH MỤC SẢN PHẨM TECHCARE\n\n")

        for p in products:

            f.write(f"# {p.name}\n\n")

            f.write("## Thông tin chung\n\n")

            f.write(f"Hãng: {p.brand}\n\n")

            f.write(f"Danh mục: {p.category}\n\n")

            f.write(f"Giá: {int(p.price):,} VNĐ\n\n")

            f.write(f"Bảo hành: {p.warranty_months} tháng\n\n")

            f.write("## Mô tả\n\n")

            f.write(f"{p.description}\n\n")

            if p.specifications:

                f.write("## Thông số kỹ thuật\n\n")

                for key, value in p.specifications.items():

                    f.write(f"- {key}: {value}\n")

                f.write("\n")

            f.write("---\n\n")

    print(f"✓ Exported Product Catalog -> {PRODUCT_MD}")


# ==========================================================
# Export FAQ
# ==========================================================


def export_faq_markdown(db):

    faqs = db.query(FAQ).all()

    with open(FAQ_MD, "w", encoding="utf-8") as f:

        f.write("# FAQ TECHCARE\n\n")

        for faq in faqs:

            f.write(f"## {faq.question}\n\n")

            f.write(f"{faq.answer}\n\n")

            f.write("---\n\n")

    print(f"✓ Exported {len(faqs)} FAQs -> {FAQ_MD}")


# ==========================================================
# Main
# ==========================================================


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    db = SessionLocal()

    try:

        export_products_json(db)

        export_products_markdown(db)

        export_faq_markdown(db)

        count, issues = write_product_rag_documents(
            PRODUCT_JSON, OUTPUT_DIR / "techcare_rag_documents.json"
        )
        for issue in issues:
            print(issue.format())
        print(f"✓ Generated {count} product RAG documents")

    finally:

        db.close()

    print("\n===================================")
    print(" RAG Export Completed Successfully ")
    print("===================================")
    print(f"Product JSON : {PRODUCT_JSON}")
    print(f"Product MD   : {PRODUCT_MD}")
    print(f"FAQ MD       : {FAQ_MD}")
    print("Knowledge MD : (Không ghi đè)")
    print("===================================")


if __name__ == "__main__":
    main()
