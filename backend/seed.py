from app.database import engine, Base, SessionLocal
from app.models import Product, FAQ
import datetime

def seed():
    # Tạo các bảng
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Kiểm tra xem có sản phẩm chưa
    if db.query(Product).count() == 0:
        print("Seeding products...")
        products = [
            Product(
                name="iPhone 15 Pro Max 256GB",
                slug="iphone-15-pro-max-256gb",
                category="Điện thoại",
                brand="Apple",
                description="Thiết kế titan bền bỉ, chip A17 Pro mạnh mẽ, camera 48MP zoom quang 5x ấn tượng.",
                price=34990000,
                warranty_months=12,
                specifications={"Màn hình": "6.7 inch", "Chip": "Apple A17 Pro", "RAM": "8GB"},
                image_url="https://cdn.tgdd.vn/Products/Images/42/305658/iphone-15-pro-max-blue-thumbnew-600x600.jpg",
                is_active=True
            ),
            Product(
                name="MacBook Air M2 2022 8GB/256GB",
                slug="macbook-air-m2-2022-8gb-256gb",
                category="Laptop",
                brand="Apple",
                description="Thiết kế siêu mỏng nhẹ, chip M2 cho hiệu suất vượt trội, thời lượng pin 18 giờ.",
                price=24990000,
                warranty_months=12,
                specifications={"Màn hình": "13.6 inch", "Chip": "Apple M2", "RAM": "8GB", "Ổ cứng": "256GB SSD"},
                image_url="https://cdn.tgdd.vn/Products/Images/44/282827/apple-macbook-air-m2-2022-xam-600x600.jpg",
                is_active=True
            ),
            Product(
                name="Tai nghe Bluetooth AirPods Pro 2",
                slug="airpods-pro-2",
                category="Phụ kiện",
                brand="Apple",
                description="Chống ồn chủ động xuất sắc, âm thanh không gian cá nhân hóa, hộp sạc MagSafe có loa.",
                price=5990000,
                warranty_months=12,
                specifications={"Thời lượng pin": "6 giờ", "Chống nước": "IP54", "Cổng sạc": "Type-C"},
                image_url="https://cdn.tgdd.vn/Products/Images/54/315750/airpods-pro-2-type-c-thumb-600x600.jpg",
                is_active=True
            ),
            Product(
                name="Samsung Galaxy S24 Ultra 5G 256GB",
                slug="samsung-galaxy-s24-ultra-5g-256gb",
                category="Điện thoại",
                brand="Samsung",
                description="Tích hợp Galaxy AI thông minh, khung viền Titan, camera 200MP cực nét.",
                price=33990000,
                warranty_months=12,
                specifications={"Màn hình": "6.8 inch", "Chip": "Snapdragon 8 Gen 3 for Galaxy", "RAM": "12GB"},
                image_url="https://cdn.tgdd.vn/Products/Images/42/307174/samsung-galaxy-s24-ultra-grey-thumb-600x600.jpg",
                is_active=True
            )
        ]
        db.add_all(products)
    
    if db.query(FAQ).count() == 0:
        print("Seeding FAQs...")
        faqs = [
            FAQ(
                question="Cửa hàng có hỗ trợ trả góp không?",
                answer="Chào bạn, TechCare hỗ trợ trả góp 0% qua thẻ tín dụng và qua các công ty tài chính như Home Credit, HD Saison. Thủ tục rất đơn giản và duyệt nhanh trong 15 phút.",
                category="Thanh toán"
            ),
            FAQ(
                question="Chính sách đổi trả của TechCare như thế nào?",
                answer="Tất cả sản phẩm lỗi do nhà sản xuất sẽ được 1 ĐỔI 1 miễn phí trong 30 ngày đầu tiên. Các tháng tiếp theo áp dụng chính sách bảo hành của hãng.",
                category="Bảo hành"
            )
        ]
        db.add_all(faqs)

    db.commit()
    db.close()
    print("Seeding completed!")

if __name__ == "__main__":
    seed()
