import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


CATEGORIES = [
    {
        "prefix": "LT",
        "category": "laptop",
        "items": [
            ("NovaBook Air 14 Plus", "Intel Core i5, RAM 16GB, SSD 512GB, màn hình 14 inch, pin 7-9 giờ", "học tập, văn phòng, học online"),
            ("NovaBook Pro 14", "Intel Core i7, RAM 16GB, SSD 1TB, màn hình 14 inch 2.5K", "văn phòng cao cấp, lập trình, thiết kế nhẹ"),
            ("EduBook 13 Lite", "Intel Core i3, RAM 8GB, SSD 256GB, màn hình 13.3 inch", "học sinh, sinh viên, tác vụ cơ bản"),
            ("GamePro 15 Neo", "AMD Ryzen 7, RAM 16GB, SSD 1TB, GPU RTX 4060, màn hình 144Hz", "chơi game, đồ họa, render video"),
            ("GamePro 17", "Intel Core i7, RAM 32GB, SSD 1TB, GPU RTX 4070, màn hình 17 inch 165Hz", "gaming nặng, dựng phim, 3D"),
            ("WorkMate 15", "Intel Core i5, RAM 16GB, SSD 512GB, màn hình 15.6 inch", "kế toán, văn phòng, làm việc nhiều tab"),
            ("CreatorBook 16", "AMD Ryzen 9, RAM 32GB, SSD 1TB, GPU RTX 4060, màn hình 16 inch 2.5K", "thiết kế, edit video, sáng tạo nội dung"),
            ("MiniBook Go 12", "Intel N-series, RAM 8GB, SSD 256GB, màn hình 12 inch", "mang đi học, ghi chú, làm việc nhẹ"),
            ("UltraBook Flex 14", "Intel Core Ultra 5, RAM 16GB, SSD 512GB, màn hình cảm ứng gập 360 độ", "thuyết trình, ghi chú, văn phòng linh hoạt"),
            ("OfficeBook 15 Plus", "Intel Core i5, RAM 16GB, SSD 1TB, màn hình 15.6 inch", "văn phòng, dữ liệu lớn, học tập"),
        ],
        "base_price": 9990000,
        "warranty": "24 tháng",
    },
    {
        "prefix": "PH",
        "category": "điện thoại",
        "items": [
            ("PixelOne A35", "AMOLED 6.4 inch, RAM 6GB, bộ nhớ 128GB, pin 5000mAh", "nghe gọi, mạng xã hội, xem phim"),
            ("PixelOne A56", "AMOLED 6.5 inch 120Hz, RAM 8GB, bộ nhớ 128GB, camera 64MP", "chụp ảnh, dùng hằng ngày, game nhẹ"),
            ("PixelOne Pro X Max", "OLED 6.7 inch 120Hz, RAM 12GB, bộ nhớ 256GB, camera 108MP", "camera tốt, hiệu năng cao"),
            ("NovaPhone Lite", "LCD 6.6 inch, RAM 4GB, bộ nhớ 64GB, pin 5000mAh", "ngân sách tiết kiệm"),
            ("NovaPhone Max", "AMOLED 6.8 inch, RAM 8GB, bộ nhớ 256GB, pin 6000mAh", "pin trâu, xem phim, giải trí"),
            ("Camon V12", "AMOLED 6.7 inch, RAM 8GB, camera selfie 32MP, camera sau 64MP", "chụp ảnh, quay vlog cơ bản"),
            ("RuggedPhone X1", "màn hình 6.5 inch, pin 7000mAh, kháng nước bụi IP68", "đi công trình, đi phượt"),
            ("MiniPhone SE", "màn hình 5.8 inch, RAM 6GB, bộ nhớ 128GB", "máy nhỏ gọn, dùng một tay"),
            ("SpeedPhone G9", "OLED 144Hz, RAM 12GB, chip hiệu năng cao, pin 5000mAh", "chơi game mobile"),
            ("BusinessPhone M2", "AMOLED 6.6 inch, RAM 8GB, bảo mật vân tay, pin 5000mAh", "nhân viên văn phòng, công việc"),
        ],
        "base_price": 3990000,
        "warranty": "12 tháng",
    },
    {
        "prefix": "TB",
        "category": "máy tính bảng",
        "items": [
            ("TabLearn 11 Plus", "màn hình 11 inch 2K, RAM 8GB, bộ nhớ 128GB, hỗ trợ bút", "ghi chú, học online"),
            ("TabLearn Mini 8", "màn hình 8.7 inch, RAM 4GB, bộ nhớ 64GB", "đọc tài liệu, trẻ em học tập"),
            ("TabPro 12", "màn hình 12.4 inch 2.5K, RAM 12GB, bộ nhớ 256GB", "làm việc, vẽ, đa nhiệm"),
            ("TabCinema 13", "màn hình 13 inch, loa kép, pin 10000mAh", "xem phim, giải trí"),
            ("TabNote 10", "màn hình 10.5 inch, hỗ trợ bút, RAM 6GB", "ghi chú, học tập"),
            ("TabKids 9", "màn hình 9 inch, vỏ chống sốc, chế độ trẻ em", "học tập cho trẻ em"),
            ("TabWork 11 LTE", "màn hình 11 inch, RAM 8GB, LTE, pin 8500mAh", "làm việc di động"),
            ("TabSketch 12", "màn hình 12 inch, bút cảm ứng lực nhấn", "vẽ, thiết kế"),
            ("TabLite 10", "màn hình 10 inch, RAM 4GB, bộ nhớ 64GB", "nhu cầu cơ bản"),
            ("TabMax 14", "màn hình 14 inch, RAM 12GB, bộ nhớ 512GB", "đa nhiệm, thay laptop nhẹ"),
        ],
        "base_price": 4990000,
        "warranty": "12 tháng",
    },
    {
        "prefix": "HP",
        "category": "tai nghe",
        "items": [
            ("SonicBuds Pro 2", "true wireless, ANC, xuyên âm, IPX4, pin 28 giờ với hộp sạc", "học online, làm việc, di chuyển"),
            ("SonicBuds Lite 2", "true wireless, mic đàm thoại, IPX4, pin 20 giờ", "nghe gọi cơ bản"),
            ("SonicBuds Sport", "true wireless, móc tai thể thao, IPX5, pin 24 giờ", "chạy bộ, tập gym"),
            ("SoundMax ANC", "tai nghe chụp tai, ANC, pin 40 giờ", "làm việc văn phòng, chống ồn"),
            ("SoundMax Studio", "tai nghe chụp tai, âm thanh cân bằng, đệm tai êm", "nghe nhạc, học online"),
            ("CallMate 300", "tai nghe bluetooth một bên, mic lọc ồn", "tài xế, telesales"),
            ("GameHead X7", "tai nghe gaming, mic rời, âm thanh vòm giả lập", "chơi game"),
            ("TypeC Ear Pro", "tai nghe có dây USB-C, mic đàm thoại", "điện thoại không cổng 3.5mm"),
            ("Classic Ear 3.5", "tai nghe có dây 3.5mm, mic cơ bản", "nghe gọi tiết kiệm"),
            ("SleepBuds Mini", "tai nghe nhỏ gọn, âm lượng thấp, pin 10 giờ", "nghe podcast, thư giãn"),
        ],
        "base_price": 390000,
        "warranty": "12 tháng",
    },
    {
        "prefix": "WA",
        "category": "đồng hồ thông minh",
        "items": [
            ("FitWatch S3", "đo nhịp tim, SpO2, giấc ngủ, 100 chế độ tập, pin 7 ngày", "theo dõi sức khỏe"),
            ("FitWatch Mini", "màn hình nhỏ gọn, đo nhịp tim, pin 5 ngày", "người thích đồng hồ nhỏ"),
            ("FitWatch Pro", "GPS, SpO2, đo stress, pin 10 ngày", "chạy bộ, luyện tập"),
            ("KidWatch 4G", "định vị GPS, gọi video, nút SOS", "trẻ em"),
            ("BusinessWatch M1", "màn hình AMOLED, nhận thông báo, pin 8 ngày", "nhân viên văn phòng"),
            ("SportWatch X", "chống nước 5ATM, GPS, 120 chế độ tập", "thể thao ngoài trời"),
            ("HealthBand 7", "vòng đeo tay, đo nhịp tim, pin 14 ngày", "theo dõi sức khỏe giá tốt"),
            ("StyleWatch Rose", "thiết kế mỏng, dây kim loại, AMOLED", "thời trang, thông báo"),
            ("OutdoorWatch Trek", "la bàn, cao áp kế, GPS, pin 15 ngày", "leo núi, đi phượt"),
            ("FitWatch Lite", "đo bước chân, nhịp tim, thông báo, pin 7 ngày", "nhu cầu cơ bản"),
        ],
        "base_price": 790000,
        "warranty": "12 tháng",
    },
    {
        "prefix": "PB",
        "category": "sạc dự phòng",
        "items": [
            ("VoltPack 10K", "10.000mAh, sạc nhanh 18W, USB-C", "dùng hằng ngày"),
            ("VoltPack 20K Plus", "20.000mAh, USB-C PD 30W, sạc nhanh", "đi học, đi làm, du lịch"),
            ("VoltPack 30K", "30.000mAh, PD 45W, nhiều cổng sạc", "du lịch dài ngày"),
            ("SlimPack 5K", "5.000mAh, mỏng nhẹ, USB-C", "mang túi nhỏ"),
            ("MagPack 10K", "10.000mAh, sạc không dây nam châm", "điện thoại hỗ trợ sạc nam châm"),
            ("LaptopPack 65W", "20.000mAh, PD 65W", "sạc laptop mỏng nhẹ"),
            ("TravelPack 20K", "20.000mAh, tích hợp cáp USB-C và Lightning", "đi du lịch"),
            ("MiniPack 8K", "8.000mAh, nhỏ gọn, 2 cổng ra", "dùng cơ bản"),
            ("SafePack 15K", "15.000mAh, bảo vệ quá nhiệt, màn hình LED", "an toàn khi sạc"),
            ("SolarPack 20K", "20.000mAh, hỗ trợ sạc năng lượng mặt trời khẩn cấp", "dã ngoại"),
        ],
        "base_price": 390000,
        "warranty": "12 tháng",
    },
    {
        "prefix": "KB",
        "category": "bàn phím",
        "items": [
            ("KeyMate K1", "bàn phím cơ 87 phím, switch red, LED trắng", "gõ văn phòng, lập trình"),
            ("KeyMate K2 RGB", "bàn phím cơ 98 phím, RGB, hot-swap", "gaming, làm việc"),
            ("KeyMate Silent", "bàn phím low-profile, phím êm", "văn phòng yên tĩnh"),
            ("KeyMate Mini 68", "bàn phím cơ 68 phím, bluetooth", "bàn làm việc nhỏ"),
            ("OfficeKey 100", "bàn phím fullsize, phím mềm, chống nước nhẹ", "văn phòng"),
            ("GameKey X5", "bàn phím gaming, RGB, macro", "chơi game"),
            ("TypeMate Fold", "bàn phím gập bluetooth", "máy tính bảng, di chuyển"),
            ("KeyMate Pro Aluminum", "vỏ nhôm, gasket mount, hot-swap", "người thích custom"),
            ("NumPad Pro", "bàn phím số rời, bluetooth", "kế toán"),
            ("ComboKey Lite", "combo bàn phím chuột không dây", "văn phòng tiết kiệm"),
        ],
        "base_price": 290000,
        "warranty": "12 tháng",
    },
    {
        "prefix": "MS",
        "category": "chuột",
        "items": [
            ("MouseMate M1", "chuột không dây, DPI 1600, pin 6 tháng", "văn phòng"),
            ("MouseMate Silent", "chuột không dây, click êm", "thư viện, văn phòng"),
            ("GameMouse X9", "chuột gaming, DPI 12000, RGB", "chơi game"),
            ("GameMouse Ultra", "chuột gaming nhẹ 65g, cảm biến cao cấp", "eSports"),
            ("ErgoMouse Vertical", "chuột công thái học dọc", "giảm mỏi cổ tay"),
            ("TravelMouse Mini", "chuột nhỏ gọn, bluetooth", "di chuyển"),
            ("OfficeMouse Pro", "chuột nhiều nút, cuộn ngang", "Excel, văn phòng"),
            ("CreatorMouse Dial", "chuột có núm xoay phụ", "thiết kế, chỉnh ảnh"),
            ("DualMouse BT", "kết nối 2 thiết bị bluetooth", "laptop và tablet"),
            ("MousePad Charge", "bàn di chuột tích hợp sạc không dây", "bàn làm việc gọn"),
        ],
        "base_price": 190000,
        "warranty": "12 tháng",
    },
    {
        "prefix": "MN",
        "category": "màn hình",
        "items": [
            ("ViewCare 24F", "24 inch Full HD, IPS, 75Hz", "văn phòng, học tập"),
            ("ViewCare 27Q", "27 inch 2K, IPS, 100Hz", "làm việc đa nhiệm"),
            ("GameView 24G", "24 inch Full HD, 165Hz, 1ms", "chơi game FPS"),
            ("GameView 27Q", "27 inch 2K, 165Hz", "gaming và đồ họa"),
            ("CreatorView 27C", "27 inch 4K, độ phủ màu cao", "thiết kế, chỉnh ảnh"),
            ("UltraWide 34", "34 inch ultrawide, 144Hz", "đa nhiệm, dựng timeline"),
            ("OfficeView 22", "22 inch Full HD, tiết kiệm điện", "văn phòng cơ bản"),
            ("PortableView 15", "màn hình di động 15.6 inch USB-C", "làm việc di động"),
            ("EyeCare 27", "27 inch Full HD, lọc ánh sáng xanh", "học tập lâu"),
            ("StudioView 32", "32 inch 4K, IPS", "sáng tạo nội dung"),
        ],
        "base_price": 2490000,
        "warranty": "24 tháng",
    },
    {
        "prefix": "AC",
        "category": "phụ kiện",
        "items": [
            ("HubConnect 6-in-1", "hub USB-C gồm HDMI, USB-A, SD, PD", "laptop mỏng nhẹ"),
            ("HubConnect 9-in-1", "hub USB-C nhiều cổng, LAN, HDMI, PD", "văn phòng"),
            ("Cable USB-C 100W", "cáp USB-C to USB-C, hỗ trợ sạc 100W", "sạc laptop, điện thoại"),
            ("Cable Lightning Fast", "cáp Lightning, sạc nhanh, bọc dù", "thiết bị dùng Lightning"),
            ("Adapter GaN 65W", "củ sạc GaN 65W, 2 USB-C, 1 USB-A", "sạc laptop và điện thoại"),
            ("Adapter GaN 30W", "củ sạc nhỏ gọn 30W USB-C", "điện thoại, máy tính bảng"),
            ("Laptop Stand Air", "giá đỡ laptop nhôm, gấp gọn", "làm việc ergonomic"),
            ("Webcam MeetCam 1080p", "webcam Full HD, mic kép", "họp online, học online"),
            ("MicStream USB", "micro USB thu âm, lọc ồn cơ bản", "livestream, học online"),
            ("CleanKit Pro", "bộ vệ sinh màn hình, bàn phím, tai nghe", "vệ sinh thiết bị"),
        ],
        "base_price": 99000,
        "warranty": "6-12 tháng tùy sản phẩm",
    },
]


def money(value):
    rounded = int(round(value / 10000) * 10000)
    return f"{rounded:,}".replace(",", ".") + " VND"


def build_products():
    products = []
    index = 1
    for category in CATEGORIES:
        for offset, item in enumerate(category["items"], start=1):
            name, specs, use_case = item
            price = category["base_price"] + (offset - 1) * 730000
            sku = f"TCX-{category['prefix']}-{index:03d}"
            products.append(
                {
                    "sku": sku,
                    "name": name,
                    "category": category["category"],
                    "price": money(price),
                    "specs": specs,
                    "use_case": use_case,
                    "warranty": category["warranty"],
                }
            )
            index += 1
    return products


def write_catalog(products):
    lines = [
        "# Catalog mở rộng 100 sản phẩm TechCare",
        "",
        "Catalog này bổ sung thêm sản phẩm để chatbot có dữ liệu giống một website bán thiết bị điện tử thật hơn. Mỗi sản phẩm có mã SKU, nhóm hàng, giá, thông số chính, nhu cầu phù hợp và thời gian bảo hành.",
        "",
    ]

    current_category = None
    for product in products:
        if product["category"] != current_category:
            current_category = product["category"]
            lines.extend(["", f"# Danh mục {current_category}", ""])
        lines.extend(
            [
                f"## {product['name']} - {product['sku']}",
                "",
                f"{product['name']} thuộc nhóm {product['category']}. Giá niêm yết: {product['price']}. Thông số chính: {product['specs']}. Phù hợp với nhu cầu: {product['use_case']}. Bảo hành: {product['warranty']}.",
                "",
            ]
        )

    (ROOT / "product_catalog_extended.md").write_text("\n".join(lines), encoding="utf-8")
    (ROOT / "techcare_products_100.json").write_text(
        json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def write_product_qa(products):
    rows = []
    for product in products:
        rows.extend(
            [
                {
                    "sku": product["sku"],
                    "intent": "product_price",
                    "question": f"{product['name']} giá bao nhiêu?",
                    "answer": f"{product['name']} hiện có giá niêm yết {product['price']}.",
                },
                {
                    "sku": product["sku"],
                    "intent": "product_info",
                    "question": f"{product['name']} có thông số gì nổi bật?",
                    "answer": f"{product['name']} có thông số chính: {product['specs']}.",
                },
                {
                    "sku": product["sku"],
                    "intent": "product_recommendation",
                    "question": f"{product['name']} phù hợp với nhu cầu nào?",
                    "answer": f"{product['name']} phù hợp với nhu cầu: {product['use_case']}.",
                },
                {
                    "sku": product["sku"],
                    "intent": "product_warranty",
                    "question": f"{product['name']} bảo hành bao lâu?",
                    "answer": f"{product['name']} được bảo hành {product['warranty']}.",
                },
                {
                    "sku": product["sku"],
                    "intent": "product_category",
                    "question": f"{product['name']} thuộc nhóm sản phẩm nào?",
                    "answer": f"{product['name']} thuộc nhóm {product['category']}.",
                },
            ]
        )

    with (ROOT / "techcare_product_qa_500.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["sku", "intent", "question", "answer"])
        writer.writeheader()
        writer.writerows(rows)


def main():
    products = build_products()
    write_catalog(products)
    write_product_qa(products)
    print(f"Generated {len(products)} products and {len(products) * 5} product QA rows.")


if __name__ == "__main__":
    main()
