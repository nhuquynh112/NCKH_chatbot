import json
import sys
from pathlib import Path

from app.database import SessionLocal
from app.models import Product, FAQ
from app.product_enrichment import merge_verified_product
from app.rag.document_builder import write_product_rag_documents
from app.config import settings
from app.rag.faq_matcher import load_curated_faqs, LEGACY_UNVERIFIED_ANSWERS

# ==========================================================
# Output Paths
# ==========================================================

OUTPUT_DIR = settings.products_path.parent
OUTPUT_DIR.mkdir(exist_ok=True)

PRODUCT_JSON = settings.products_path
PRODUCT_MD = settings.product_catalog_path
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
            }, preserve_store_fields=True
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

            item = merge_verified_product({
                "slug": p.slug, "name": p.name, "warranty_months": p.warranty_months,
                "specifications": p.specifications,
            }, preserve_store_fields=True)

            f.write(f"# {p.name}\n\n")

            f.write("## Thông tin chung\n\n")

            f.write(f"Hãng: {p.brand}\n\n")

            f.write(f"Danh mục: {p.category}\n\n")

            f.write(f"Giá: {int(p.price):,} VNĐ\n\n")

            warranty = item.get("warranty_source_text") or (
                f"{p.warranty_months} tháng" if p.warranty_months is not None else "Chưa xác nhận"
            )
            f.write(f"Bảo hành tham khảo: {warranty}\n\n")
            if item.get("price_basis") == "retailer_reference_snapshot_for_research":
                f.write(f"Dữ liệu tham khảo CellphoneS ngày {item.get('collected_at')}; giá dùng cho demo, không xác nhận tồn kho/giá thực tế hoặc chính sách TechCare.\n\n")

            f.write("## Mô tả\n\n")

            f.write(f"{p.description}\n\n")

            if p.specifications:

                f.write("## Thông số kỹ thuật\n\n")

                for key, value in p.specifications.items():

                    f.write(f"- {key}: {value}\n")

                f.write("\n")

            for source in item.get("source_urls", []):
                f.write(f"Nguồn tham khảo: {source['title']} — {source['url']}\n\n")

            f.write("---\n" if p is products[-1] else "---\n\n")

    print(f"✓ Exported Product Catalog -> {PRODUCT_MD}")


# ==========================================================
# Export FAQ
# ==========================================================


def export_faq_markdown(db):

    faqs = [faq for faq in db.query(FAQ).filter(FAQ.is_active.is_(True)).order_by(FAQ.id).all()
            if faq.answer not in LEGACY_UNVERIFIED_ANSWERS]
    curated_count = 0

    with open(FAQ_MD, "w", encoding="utf-8") as f:

        f.write("# FAQ TECHCARE\n\n")
        f.write("FAQ trong môi trường nghiên cứu; chính sách demo cần xác nhận trước khi dùng cho doanh nghiệp thật.\n\n")

        for faq in faqs:

            f.write(f"## {faq.question}\n\n")

            f.write(f"{faq.answer}\n\n")

            f.write("---\n\n")

        existing_questions = {faq.question for faq in faqs}
        for faq in load_curated_faqs():
            if faq["question"] not in existing_questions:
                f.write(f"## {faq['question']}\n\n{faq['answer']}\n\n---\n\n")
                curated_count += 1

    print(f"✓ Exported {len(faqs)} active admin FAQs + {curated_count} curated demo FAQs -> {FAQ_MD}")


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
