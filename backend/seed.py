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
        products_data = [

# =========================
# APPLE
# =========================

{
    "name":"iPhone 17 128GB",
    "slug":"iphone-17-128gb",
    "category":"Điện thoại",
    "brand":"Apple",
    "description":"iPhone 17 màn hình OLED 6.3 inch, chip Apple A19, camera AI thế hệ mới.",
    "price":25990000,
    "warranty_months":12,
    "specifications":{
        "Màn hình":"6.3 inch OLED",
        "Chip":"Apple A19",
        "RAM":"8GB",
        "Bộ nhớ":"128GB"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"iPhone 17 Pro 256GB",
    "slug":"iphone-17-pro-256gb",
    "category":"Điện thoại",
    "brand":"Apple",
    "description":"iPhone 17 Pro khung Titan, camera AI Pro, chip Apple A19 Pro.",
    "price":33990000,
    "warranty_months":12,
    "specifications":{
        "Màn hình":"6.3 inch OLED",
        "Chip":"Apple A19 Pro",
        "RAM":"12GB",
        "Bộ nhớ":"256GB"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"MacBook Air M4 13 inch",
    "slug":"macbook-air-m4",
    "category":"Laptop",
    "brand":"Apple",
    "description":"MacBook Air M4 siêu mỏng nhẹ, pin lên tới 18 giờ.",
    "price":27990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Apple M4",
        "RAM":"16GB",
        "SSD":"512GB",
        "GPU":"Apple GPU"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"iPad Air M3 WiFi",
    "slug":"ipad-air-m3",
    "category":"Máy tính bảng",
    "brand":"Apple",
    "description":"iPad Air M3 mạnh mẽ dành cho học tập và sáng tạo.",
    "price":17990000,
    "warranty_months":12,
    "specifications":{
        "Chip":"Apple M3",
        "RAM":"8GB",
        "Storage":"128GB"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"AirPods Pro 2 USB-C",
    "slug":"airpods-pro-2",
    "category":"Tai nghe",
    "brand":"Apple",
    "description":"Tai nghe chống ồn chủ động ANC thế hệ mới.",
    "price":5990000,
    "warranty_months":12,
    "specifications":{
        "Pin":"6 giờ",
        "Bluetooth":"5.3",
        "Chống nước":"IP54"
    },
    "image_url":None,
    "is_active":True
},

# =========================
# SAMSUNG
# =========================

{
    "name":"Samsung Galaxy S25 Ultra",
    "slug":"galaxy-s25-ultra",
    "category":"Điện thoại",
    "brand":"Samsung",
    "description":"Galaxy AI mạnh mẽ, camera 200MP.",
    "price":32990000,
    "warranty_months":12,
    "specifications":{
        "Chip":"Snapdragon 8 Elite",
        "RAM":"12GB",
        "Storage":"256GB"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"Samsung Galaxy S25",
    "slug":"galaxy-s25",
    "category":"Điện thoại",
    "brand":"Samsung",
    "description":"Điện thoại AI cao cấp cho công việc và giải trí.",
    "price":22990000,
    "warranty_months":12,
    "specifications":{
        "Chip":"Snapdragon 8 Elite",
        "RAM":"12GB",
        "Storage":"256GB"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"Galaxy Tab S10",
    "slug":"galaxy-tab-s10",
    "category":"Máy tính bảng",
    "brand":"Samsung",
    "description":"Tablet Android cao cấp hỗ trợ bút S-Pen.",
    "price":18990000,
    "warranty_months":12,
    "specifications":{
        "RAM":"12GB",
        "Storage":"256GB"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"Galaxy Buds3 Pro",
    "slug":"galaxy-buds3-pro",
    "category":"Tai nghe",
    "brand":"Samsung",
    "description":"Tai nghe chống ồn AI.",
    "price":4990000,
    "warranty_months":12,
    "specifications":{
        "Bluetooth":"5.4",
        "ANC":"Có"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"Galaxy Watch Ultra",
    "slug":"galaxy-watch-ultra",
    "category":"Đồng hồ",
    "brand":"Samsung",
    "description":"Đồng hồ thông minh Galaxy Watch Ultra.",
    "price":14990000,
    "warranty_months":12,
    "specifications":{
        "GPS":"Dual GPS",
        "Pin":"100 giờ"
    },
    "image_url":None,
    "is_active":True
},

# =========================
# DELL
# =========================

{
    "name":"Dell Inspiron 15 3530",
    "slug":"dell-inspiron-3530",
    "category":"Laptop",
    "brand":"Dell",
    "description":"Laptop văn phòng bán chạy.",
    "price":15990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Intel Core i5-1334U",
        "RAM":"16GB",
        "SSD":"512GB"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"Dell Vostro 3530",
    "slug":"dell-vostro-3530",
    "category":"Laptop",
    "brand":"Dell",
    "description":"Laptop doanh nghiệp ổn định.",
    "price":17990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Intel Core i5-1335U",
        "RAM":"16GB",
        "SSD":"512GB"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"Dell XPS 14",
    "slug":"dell-xps-14",
    "category":"Laptop",
    "brand":"Dell",
    "description":"Laptop cao cấp cho lập trình và thiết kế.",
    "price":45990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Core Ultra 7",
        "RAM":"32GB",
        "SSD":"1TB"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"Dell Alienware m16",
    "slug":"alienware-m16",
    "category":"Laptop",
    "brand":"Dell",
    "description":"Gaming laptop RTX 4070.",
    "price":69990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Core i9",
        "RAM":"32GB",
        "SSD":"1TB",
        "GPU":"RTX 4070"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"Dell P2425H",
    "slug":"dell-p2425h",
    "category":"Màn hình",
    "brand":"Dell",
    "description":"Màn hình văn phòng 24 inch IPS.",
    "price":4890000,
    "warranty_months":36,
    "specifications":{
        "Kích thước":"24 inch",
        "Tấm nền":"IPS",
        "Refresh":"100Hz"
    },
    "image_url":None,
    "is_active":True
},

# =========================
# PHỤ KIỆN
# =========================

{
    "name":"Chuột Logitech M650",
    "slug":"logitech-m650",
    "category":"Phụ kiện",
    "brand":"Logitech",
    "description":"Chuột không dây văn phòng.",
    "price":790000,
    "warranty_months":24,
    "specifications":{
        "Kết nối":"Bluetooth",
        "Pin":"24 tháng"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"Bàn phím Logitech K380",
    "slug":"logitech-k380",
    "category":"Phụ kiện",
    "brand":"Logitech",
    "description":"Bàn phím Bluetooth đa thiết bị.",
    "price":890000,
    "warranty_months":24,
    "specifications":{
        "Bluetooth":"Có",
        "Pin":"24 tháng"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"SSD Kingston NV3 1TB",
    "slug":"kingston-nv3-1tb",
    "category":"Phụ kiện",
    "brand":"Kingston",
    "description":"SSD NVMe PCIe Gen4 tốc độ cao.",
    "price":1890000,
    "warranty_months":60,
    "specifications":{
        "Dung lượng":"1TB",
        "Chuẩn":"PCIe Gen4"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"Sạc Anker Nano 65W",
    "slug":"anker-nano-65w",
    "category":"Phụ kiện",
    "brand":"Anker",
    "description":"Sạc nhanh GaN 65W.",
    "price":990000,
    "warranty_months":18,
    "specifications":{
        "Công suất":"65W",
        "Cổng":"USB-C"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"WD My Passport 2TB",
    "slug":"wd-my-passport-2tb",
    "category":"Phụ kiện",
    "brand":"Western Digital",
    "description":"Ổ cứng di động 2TB.",
    "price":2290000,
    "warranty_months":36,
    "specifications":{
        "Dung lượng":"2TB",
        "USB":"3.2"
    },
    "image_url":None,
    "is_active":True
},

# =========================
# ASUS
# =========================

{
    "name":"ASUS Vivobook 15 OLED",
    "slug":"asus-vivobook-15-oled",
    "category":"Laptop",
    "brand":"ASUS",
    "description":"Laptop học tập và văn phòng với màn hình OLED sắc nét.",
    "price":16990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Intel Core i5-13500H",
        "RAM":"16GB",
        "SSD":"512GB"
    },
    "image_url":"/images/products/asus-vivobook-15-oled.jpg",
    "is_active":True
},

{
    "name":"ASUS Zenbook 14 OLED",
    "slug":"asus-zenbook-14",
    "category":"Laptop",
    "brand":"ASUS",
    "description":"Laptop mỏng nhẹ cao cấp cho doanh nhân.",
    "price":27990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Intel Core Ultra 7",
        "RAM":"16GB",
        "SSD":"1TB"
    },
    "image_url":"/images/products/asus-zenbook-14.png",
    "is_active":True
},

{
    "name":"ASUS ROG Strix G16",
    "slug":"rog-strix-g16",
    "category":"Laptop",
    "brand":"ASUS",
    "description":"Laptop gaming RTX4060.",
    "price":36990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Core i7-14650HX",
        "RAM":"16GB",
        "SSD":"1TB",
        "GPU":"RTX4060"
    },
    "image_url":"/images/products/rog-strix-g16.png",
    "is_active":True
},

{
    "name":"ASUS TUF Gaming A15",
    "slug":"asus-tuf-a15",
    "category":"Laptop",
    "brand":"ASUS",
    "description":"Gaming laptop AMD Ryzen.",
    "price":24990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Ryzen 7 8845HS",
        "RAM":"16GB",
        "SSD":"512GB",
        "GPU":"RTX4050"
    },
    "image_url":"/images/products/asus-tuf-a15.png",
    "is_active":True
},

{
    "name":"ASUS ProArt P16",
    "slug":"asus-proart-p16",
    "category":"Laptop",
    "brand":"ASUS",
    "description":"Laptop dành cho designer và editor.",
    "price":52990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Ryzen AI 9",
        "RAM":"32GB",
        "SSD":"1TB"
    },
    "image_url":"/images/products/asus-proart-p16.avif",
    "is_active":True
},

# =========================
# LENOVO
# =========================

{
    "name":"Lenovo ThinkPad E14 Gen 6",
    "slug":"thinkpad-e14-gen6",
    "category":"Laptop",
    "brand":"Lenovo",
    "description":"Laptop doanh nghiệp nổi tiếng về độ bền.",
    "price":21990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Intel Core Ultra 5",
        "RAM":"16GB",
        "SSD":"512GB"
    },
    "image_url":"/images/products/thinkpad-e14-gen6.avif",
    "is_active":True
},

{
    "name":"Lenovo LOQ 15",
    "slug":"lenovo-loq-15",
    "category":"Laptop",
    "brand":"Lenovo",
    "description":"Laptop gaming tầm trung.",
    "price":24990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Core i7",
        "RAM":"16GB",
        "SSD":"512GB",
        "GPU":"RTX4050"
    },
    "image_url":"/images/products/lenovo-loq-15.webp",
    "is_active":True
},

{
    "name":"Lenovo Yoga Slim 7",
    "slug":"yoga-slim-7",
    "category":"Laptop",
    "brand":"Lenovo",
    "description":"Laptop mỏng nhẹ cao cấp.",
    "price":28990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Core Ultra 7",
        "RAM":"16GB",
        "SSD":"1TB"
    },
    "image_url":"/images/products/yoga-slim-7.png",
    "is_active":True
},

{
    "name":"Lenovo Legion 5",
    "slug":"legion-5",
    "category":"Laptop",
    "brand":"Lenovo",
    "description":"Gaming laptop hiệu năng cao.",
    "price":32990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Ryzen 9",
        "RAM":"32GB",
        "SSD":"1TB",
        "GPU":"RTX4070"
    },
    "image_url":"/images/products/legion-5.avif",
    "is_active":True
},

{
    "name":"Lenovo Tab P12",
    "slug":"lenovo-tab-p12",
    "category":"Máy tính bảng",
    "brand":"Lenovo",
    "description":"Tablet Android màn hình lớn.",
    "price":11990000,
    "warranty_months":12,
    "specifications":{
        "RAM":"8GB",
        "Storage":"256GB"
    },
    "image_url":"/images/products/lenovo-tab-p12.png",
    "is_active":True
},

# =========================
# HP
# =========================

{
    "name":"HP Pavilion 15",
    "slug":"hp-pavilion-15",
    "category":"Laptop",
    "brand":"HP",
    "description":"Laptop học tập và văn phòng.",
    "price":17990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Core i5",
        "RAM":"16GB",
        "SSD":"512GB"
    },
    "image_url":"/images/products/hp-pavilion-15.png",
    "is_active":True
},

{
    "name":"HP Victus 15",
    "slug":"hp-victus-15",
    "category":"Laptop",
    "brand":"HP",
    "description":"Gaming laptop RTX4050.",
    "price":23990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Ryzen 7",
        "RAM":"16GB",
        "SSD":"512GB",
        "GPU":"RTX4050"
    },
    "image_url":"/images/products/hp-victus-15.png",
    "is_active":True
},

{
    "name":"HP Omen 16",
    "slug":"hp-omen-16",
    "category":"Laptop",
    "brand":"HP",
    "description":"Gaming laptop cao cấp.",
    "price":38990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Core i9",
        "RAM":"32GB",
        "SSD":"1TB",
        "GPU":"RTX4070"
    },
    "image_url":"/images/products/hp-omen-16.webp",
    "is_active":True
},

{
    "name":"HP Envy x360",
    "slug":"hp-envy-x360",
    "category":"Laptop",
    "brand":"HP",
    "description":"Laptop xoay gập cảm ứng.",
    "price":26990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Ryzen 7",
        "RAM":"16GB",
        "SSD":"1TB"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"HP EliteBook 840 G11",
    "slug":"elitebook-840-g11",
    "category":"Laptop",
    "brand":"HP",
    "description":"Laptop doanh nghiệp bảo mật cao.",
    "price":29990000,
    "warranty_months":36,
    "specifications":{
        "CPU":"Core Ultra 7",
        "RAM":"16GB",
        "SSD":"512GB"
    },
    "image_url":None,
    "is_active":True
},

# =========================
# ACER
# =========================

{
    "name":"Acer Aspire 5",
    "slug":"acer-aspire-5",
    "category":"Laptop",
    "brand":"Acer",
    "description":"Laptop văn phòng phổ thông.",
    "price":15990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Intel Core i5-13420H",
        "RAM":"16GB",
        "SSD":"512GB"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"Acer Swift Go 14",
    "slug":"acer-swift-go-14",
    "category":"Laptop",
    "brand":"Acer",
    "description":"Laptop mỏng nhẹ OLED.",
    "price":23990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Intel Core Ultra 7",
        "RAM":"16GB",
        "SSD":"1TB"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"Acer Nitro V 15",
    "slug":"acer-nitro-v15",
    "category":"Laptop",
    "brand":"Acer",
    "description":"Gaming laptop RTX4050.",
    "price":22990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Core i7",
        "RAM":"16GB",
        "SSD":"512GB",
        "GPU":"RTX4050"
    },
    "image_url":"/images/products/acer-nitro-v15.avif",
    "is_active":True
},

{
    "name":"Acer Predator Helios Neo 16",
    "slug":"predator-helios-neo16",
    "category":"Laptop",
    "brand":"Acer",
    "description":"Gaming laptop hiệu năng cao.",
    "price":38990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Core i9",
        "RAM":"32GB",
        "SSD":"1TB",
        "GPU":"RTX4070"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"Acer KA242Y",
    "slug":"acer-ka242y",
    "category":"Màn hình",
    "brand":"Acer",
    "description":"Màn hình IPS 24 inch 100Hz.",
    "price":2990000,
    "warranty_months":36,
    "specifications":{
        "Kích thước":"24 inch",
        "Refresh":"100Hz"
    },
    "image_url":None,
    "is_active":True
},

# =========================
# MSI
# =========================

{
    "name":"MSI Modern 15",
    "slug":"msi-modern-15",
    "category":"Laptop",
    "brand":"MSI",
    "description":"Laptop văn phòng thiết kế đẹp.",
    "price":17990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Core i5",
        "RAM":"16GB",
        "SSD":"512GB"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"MSI Katana 15",
    "slug":"msi-katana15",
    "category":"Laptop",
    "brand":"MSI",
    "description":"Gaming laptop RTX4060.",
    "price":28990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Core i7",
        "RAM":"16GB",
        "SSD":"1TB",
        "GPU":"RTX4060"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"MSI Raider GE68",
    "slug":"msi-raider-ge68",
    "category":"Laptop",
    "brand":"MSI",
    "description":"Gaming flagship.",
    "price":52990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Core i9",
        "RAM":"32GB",
        "SSD":"2TB",
        "GPU":"RTX4080"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"MSI PRO MP2412",
    "slug":"msi-pro-mp2412",
    "category":"Màn hình",
    "brand":"MSI",
    "description":"Màn hình IPS văn phòng.",
    "price":2790000,
    "warranty_months":36,
    "specifications":{
        "24 inch":"IPS",
        "Refresh":"100Hz"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"MSI Immerse GH30",
    "slug":"msi-gh30",
    "category":"Tai nghe",
    "brand":"MSI",
    "description":"Tai nghe gaming.",
    "price":1290000,
    "warranty_months":12,
    "specifications":{
        "Jack":"3.5mm"
    },
    "image_url":None,
    "is_active":True
},

# =========================
# GIGABYTE
# =========================

{
    "name":"Gigabyte G5",
    "slug":"gigabyte-g5",
    "category":"Laptop",
    "brand":"Gigabyte",
    "description":"Gaming laptop RTX4060.",
    "price":26990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Core i7",
        "RAM":"16GB",
        "SSD":"512GB"
    },
    "image_url":"/images/products/gigabyte-g5.png",
    "is_active":True
},

{
    "name":"Gigabyte Aorus 15",
    "slug":"gigabyte-aorus15",
    "category":"Laptop",
    "brand":"Gigabyte",
    "description":"Gaming laptop cao cấp.",
    "price":39990000,
    "warranty_months":24,
    "specifications":{
        "CPU":"Core Ultra 9",
        "RAM":"32GB",
        "SSD":"1TB"
    },
    "image_url":"/images/products/gigabyte-aorus15.png",
    "is_active":True
},

{
    "name":"Gigabyte GS27Q",
    "slug":"gigabyte-gs27q",
    "category":"Màn hình",
    "brand":"Gigabyte",
    "description":"Màn hình Gaming QHD 170Hz.",
    "price":6990000,
    "warranty_months":36,
    "specifications":{
        "27 inch":"QHD",
        "Refresh":"170Hz"
    },
    "image_url":"/images/products/gigabyte-gs27q.png",
    "is_active":True
},

# =========================
# XIAOMI
# =========================

{
    "name":"Xiaomi 15",
    "slug":"xiaomi-15",
    "category":"Điện thoại",
    "brand":"Xiaomi",
    "description":"Flagship Snapdragon 8 Elite.",
    "price":21990000,
    "warranty_months":12,
    "specifications":{
        "RAM":"12GB",
        "Storage":"256GB"
    },
    "image_url":"/images/products/xiaomi-15.webp",
    "is_active":True
},

{
    "name":"Redmi Note 14 Pro+",
    "slug":"redmi-note14-pro-plus",
    "category":"Điện thoại",
    "brand":"Xiaomi",
    "description":"Điện thoại tầm trung camera 200MP.",
    "price":10990000,
    "warranty_months":12,
    "specifications":{
        "RAM":"12GB",
        "Storage":"256GB"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"Xiaomi Pad 7 Pro",
    "slug":"xiaomi-pad7-pro",
    "category":"Máy tính bảng",
    "brand":"Xiaomi",
    "description":"Tablet Snapdragon mạnh mẽ.",
    "price":14990000,
    "warranty_months":12,
    "specifications":{
        "RAM":"8GB",
        "Storage":"256GB"
    },
    "image_url":None,
    "is_active":True
},

# =========================
# GOOGLE
# =========================

{
    "name":"Google Pixel 9",
    "slug":"pixel9",
    "category":"Điện thoại",
    "brand":"Google",
    "description":"Camera AI nổi tiếng của Google.",
    "price":20990000,
    "warranty_months":12,
    "specifications":{
        "Chip":"Tensor G4",
        "RAM":"12GB",
        "Storage":"256GB"
    },
    "image_url":None,
    "is_active":True
},

{
    "name":"Google Pixel 9 Pro XL",
    "slug":"pixel9-pro-xl",
    "category":"Điện thoại",
    "brand":"Google",
    "description":"Flagship AI của Google.",
    "price":30990000,
    "warranty_months":12,
    "specifications":{
        "Chip":"Tensor G4",
        "RAM":"16GB",
        "Storage":"512GB"
    },
    "image_url":None,
    "is_active":True
}

]
        products = [Product(**item) for item in products_data]
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
