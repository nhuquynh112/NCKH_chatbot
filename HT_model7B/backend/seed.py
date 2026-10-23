from app.database import engine, Base, SessionLocal
from app.models import Product, FAQ
from app.product_enrichment import merge_verified_product
import datetime

def seed():
    # Tạo các bảng
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Kiểm tra xem có sản phẩm chưa
    if db.query(Product).count() == 0:
        print("Seeding products...")
        from app.catalog_data import read_catalog
        from app.config import settings
        products_data = read_catalog(settings.products_path)
        # Apply the same reviewed corrections used by the live chatbot so a
        # fresh database cannot re-introduce known catalog mistakes.
        products_data = [merge_verified_product(item, preserve_store_fields=True) for item in products_data]
        product_fields = {
            "id", "name", "slug", "category", "brand", "description", "price",
            "warranty_months", "specifications", "image_url", "is_active",
        }
        products = [
            Product(**{key: value for key, value in item.items() if key in product_fields})
            for item in products_data
        ]
        db.add_all(products)
    
    if db.query(FAQ).count() == 0:
        print("Seeding FAQs...")
        from app.rag.faq_matcher import load_curated_faqs
        faqs = [FAQ(question=item["question"], answer=item["answer"], category=item["category"],
                    keywords=item.get("triggers", [])) for item in load_curated_faqs()]
        db.add_all(faqs)

    db.commit()
    db.close()
    print("Seeding completed!")

if __name__ == "__main__":
    seed()
