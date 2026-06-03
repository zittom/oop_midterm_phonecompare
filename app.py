"""
Flask API Server - REST endpoints cho Frontend
Chạy: python app.py
"""

import json
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

from crawler.manager import CrawlerManager, DataProcessor
from database import ProductRepository

app = Flask(__name__)
CORS(app)  # Cho phép frontend gọi API

repo = ProductRepository()
manager = CrawlerManager()
processor = DataProcessor()

# --- THÊM ĐOẠN CODE NÀY VÀO ĐÂY ---
# Kiểm tra nếu DB đang trống thì tự động nạp dữ liệu mẫu
if repo.get_stats()["total_products"] == 0:
    from crawler.base_crawler import PhoneProduct
    demo_products = [
        PhoneProduct("iPhone 15 Pro Max 256GB", 29990000, "Cellphones", "https://cellphones.com.vn/iphone-15-pro-max.html", "Apple", 4.9, 1520, "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/i/p/iphone-15-pro-max_3.png"),
        PhoneProduct("iPhone 15 128GB", 19990000, "Cellphones", "https://cellphones.com.vn/iphone-15.html", "Apple", 4.7, 1280, "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/i/p/iphone-15-hong-1.png"),
        PhoneProduct("iPhone 13 128GB", 13990000, "Cellphones", "https://cellphones.com.vn/iphone-13.html", "Apple", 4.8, 3420, "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/i/p/iphone-13_2_.png"),
        PhoneProduct("Samsung Galaxy S24 Ultra 256GB", 26990000, "Cellphones", "https://cellphones.com.vn/samsung-galaxy-s24-ultra.html", "Samsung", 4.8, 950, "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/s/s/ss-s24-ultra-xam-222.png"),
        PhoneProduct("Samsung Galaxy Z Fold5 256GB", 29990000, "Cellphones", "https://cellphones.com.vn/samsung-galaxy-z-fold-5.html", "Samsung", 4.6, 420, "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/s/a/samsung-galaxy-z-fold-5-256gb_1.png"),
        PhoneProduct("Samsung Galaxy A55 5G 128GB", 9490000, "Cellphones", "https://cellphones.com.vn/samsung-galaxy-a55.html", "Samsung", 4.5, 630, "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/s/a/samsung-galaxy-a55-5g_1_.png"),
        PhoneProduct("Xiaomi 14 5G", 19990000, "Cellphones", "https://cellphones.com.vn/xiaomi-14.html", "Xiaomi", 4.7, 310, "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/d/i/dien-thoai-xiaomi-14_1__1.png"),
        PhoneProduct("Xiaomi Redmi Note 13 Pro 4G", 6490000, "Cellphones", "https://cellphones.com.vn/xiaomi-redmi-note-13-pro-4g.html", "Xiaomi", 4.5, 890, "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/d/i/dien-thoai-xiaomi-redmi-note-13-pro-4g-xanh-1.png"),
        PhoneProduct("OPPO Reno11 5G", 10490000, "Cellphones", "https://cellphones.com.vn/oppo-reno-11.html", "OPPO", 4.4, 210, "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/d/i/dien-thoai-oppo-reno11-xanh-1_1.png"),
        PhoneProduct("OPPO Find N3 5G", 41990000, "Cellphones", "https://cellphones.com.vn/oppo-find-n3.html", "OPPO", 4.6, 120, "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/o/p/oppo-find-n3-5g-vang_2__1.jpg"),
        PhoneProduct("vivo V30 5G", 13490000, "Cellphones", "https://cellphones.com.vn/vivo-v30.html", "Vivo", 4.5, 180, "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/d/i/dien-thoai-vivo-v30_1_.png"),
        PhoneProduct("ASUS ROG Phone 8", 21990000, "Cellphones", "https://cellphones.com.vn/asus-rog-phone-8.html", "ASUS", 4.8, 95, "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/a/s/asus-rog-phone-8_1__1.png"),
    ]
    repo.bulk_upsert(demo_products)
    print("Đã tự động nạp dữ liệu mẫu!")
# ----------------------------------------


# ─── API Endpoints ────────────────────────────────────────────────────────────

@app.route("/")
def serve_frontend():
    return send_file("index.html")

@app.get("/api/search")
def search():
    """
    Tìm kiếm + crawl realtime
    GET /api/search?q=iphone+15&source=db
    source=db    → chỉ tìm trong DB
    source=live  → crawl mới từ websites
    """
    keyword = request.args.get("q", "").strip()
    source = request.args.get("source", "db")

    if not keyword:
        return jsonify({"error": "Thiếu từ khóa tìm kiếm"}), 400

    if source == "live":
        # Crawl trực tiếp từ web
        raw = manager.search_all(keyword)
        products = processor.normalize(raw)
        repo.bulk_upsert(products)
        data = [p.to_dict() for p in products]
    else:
        # Tìm trong database
        data = repo.search(keyword)
        # Parse specs JSON nếu có
        for item in data:
            if isinstance(item.get("specs"), str):
                try:
                    item["specs"] = json.loads(item["specs"])
                except Exception:
                    item["specs"] = {}

    return jsonify({
        "keyword": keyword,
        "count": len(data),
        "products": data,
    })


@app.get("/api/compare")
def compare():
    """
    So sánh giá cùng model từ nhiều nguồn
    GET /api/compare?model=iPhone+15+Pro
    """
    model = request.args.get("model", "").strip()
    if not model:
        return jsonify({"error": "Thiếu tên model"}), 400

    results = repo.get_cheapest_by_model(model)
    return jsonify({
        "model": model,
        "count": len(results),
        "sources": results,
    })


@app.get("/api/products")
def get_products():
    """
    Lấy danh sách với bộ lọc
    GET /api/products?brand=Samsung&max_price=10000000&min_rating=4
    """
    brand = request.args.get("brand")
    max_price = request.args.get("max_price", type=float)
    min_rating = request.args.get("min_rating", type=float)
    limit = request.args.get("limit", 50, type=int)

    products = repo.get_all(brand=brand, max_price=max_price,
                            min_rating=min_rating, limit=limit)
    return jsonify({"count": len(products), "products": products})


@app.get("/api/brands")
def get_brands():
    return jsonify(repo.get_brands())


@app.get("/api/stats")
def get_stats():
    return jsonify(repo.get_stats())


@app.get("/api/seed")
def seed_demo():
    """Tạo dữ liệu demo để test frontend (không cần crawl thật)"""
    from datetime import datetime
    from crawler.base_crawler import PhoneProduct

demo_products = [
        PhoneProduct("iPhone 15 Pro Max 256GB", 29990000, "Cellphones",
                     "https://cellphones.com.vn/iphone-15-pro-max.html",
                     "Apple", 4.9, 1520,
                     "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/i/p/iphone-15-pro-max_3.png"),
        
        PhoneProduct("iPhone 15 128GB", 19990000, "Cellphones",
                     "https://cellphones.com.vn/iphone-15.html",
                     "Apple", 4.7, 1280,
                     "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/i/p/iphone-15-hong-1.png"),

        PhoneProduct("iPhone 13 128GB", 13990000, "Cellphones",
                     "https://cellphones.com.vn/iphone-13.html",
                     "Apple", 4.8, 3420,
                     "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/i/p/iphone-13_2_.png"),

        PhoneProduct("Samsung Galaxy S24 Ultra 256GB", 26990000, "Cellphones",
                     "https://cellphones.com.vn/samsung-galaxy-s24-ultra.html",
                     "Samsung", 4.8, 950,
                     "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/s/s/ss-s24-ultra-xam-222.png"),

        PhoneProduct("Samsung Galaxy Z Fold5 256GB", 29990000, "Cellphones",
                     "https://cellphones.com.vn/samsung-galaxy-z-fold-5.html",
                     "Samsung", 4.6, 420,
                     "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/s/a/samsung-galaxy-z-fold-5-256gb_1.png"),

        PhoneProduct("Samsung Galaxy A55 5G 128GB", 9490000, "Cellphones",
                     "https://cellphones.com.vn/samsung-galaxy-a55.html",
                     "Samsung", 4.5, 630,
                     "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/s/a/samsung-galaxy-a55-5g_1_.png"),

        PhoneProduct("Xiaomi 14 5G", 19990000, "Cellphones",
                     "https://cellphones.com.vn/xiaomi-14.html",
                     "Xiaomi", 4.7, 310,
                     "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/d/i/dien-thoai-xiaomi-14_1__1.png"),

        PhoneProduct("Xiaomi Redmi Note 13 Pro 4G", 6490000, "Cellphones",
                     "https://cellphones.com.vn/xiaomi-redmi-note-13-pro-4g.html",
                     "Xiaomi", 4.5, 890,
                     "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/d/i/dien-thoai-xiaomi-redmi-note-13-pro-4g-xanh-1.png"),

        PhoneProduct("OPPO Reno11 5G", 10490000, "Cellphones",
                     "https://cellphones.com.vn/oppo-reno-11.html",
                     "OPPO", 4.4, 210,
                     "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/d/i/dien-thoai-oppo-reno11-xanh-1_1.png"),

        PhoneProduct("OPPO Find N3 5G", 41990000, "Cellphones",
                     "https://cellphones.com.vn/oppo-find-n3.html",
                     "OPPO", 4.6, 120,
                     "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/o/p/oppo-find-n3-5g-vang_2__1.jpg"),

        PhoneProduct("vivo V30 5G", 13490000, "Cellphones",
                     "https://cellphones.com.vn/vivo-v30.html",
                     "Vivo", 4.5, 180,
                     "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/d/i/dien-thoai-vivo-v30_1_.png"),

        PhoneProduct("ASUS ROG Phone 8", 21990000, "Cellphones",
                     "https://cellphones.com.vn/asus-rog-phone-8.html",
                     "ASUS", 4.8, 95,
                     "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/a/s/asus-rog-phone-8_1__1.png"),
    ]

    saved = repo.bulk_upsert(demo_products)
    return jsonify({"message": f"Seeded {saved} demo products ✓"})


if __name__ == "__main__":
    print("🚀 Phone Compare API → http://localhost:5000")
    print("📡 Seed demo data:   http://localhost:5000/api/seed")
    app.run(debug=True, port=5000)
