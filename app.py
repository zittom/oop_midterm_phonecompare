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
@app.route("/")
def serve_frontend():
    return send_file("index.html")
CORS(app)  # Cho phép frontend gọi API

repo = ProductRepository()
manager = CrawlerManager()
processor = DataProcessor()


# ─── API Endpoints ────────────────────────────────────────────────────────────

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
        PhoneProduct("iPhone 15 Pro 256GB", 28990000, "Cellphones",
                     "https://cellphones.com.vn/iphone-15-pro.html",
                     "Apple", 4.8, 1240,
                     "https://cdn.cellphones.com.vn/media/catalog/product/i/p/ip15pro.jpg"),
        PhoneProduct("iPhone 15 Pro 256GB", 29200000, "FPTShop",
                     "https://fptshop.com.vn/dien-thoai/iphone-15-pro",
                     "Apple", 4.7, 980),
        PhoneProduct("iPhone 15 Pro 256GB", 28750000, "Thegioididong",
                     "https://thegioididong.com/tin-tuc/iphone-15-pro",
                     "Apple", 4.9, 2100),
        PhoneProduct("Samsung Galaxy S24 Ultra 256GB", 26990000, "Cellphones",
                     "https://cellphones.com.vn/samsung-s24-ultra.html",
                     "Samsung", 4.7, 850),
        PhoneProduct("Samsung Galaxy S24 Ultra 256GB", 27500000, "FPTShop",
                     "https://fptshop.com.vn/dien-thoai/samsung-s24-ultra",
                     "Samsung", 4.6, 620),
        PhoneProduct("Samsung Galaxy S24 Ultra 256GB", 26500000, "Thegioididong",
                     "https://thegioididong.com/dien-thoai/samsung-galaxy-s24-ultra",
                     "Samsung", 4.8, 1500),
        PhoneProduct("Xiaomi 14 Ultra 512GB", 20990000, "Cellphones",
                     "https://cellphones.com.vn/xiaomi-14-ultra.html",
                     "Xiaomi", 4.6, 340),
        PhoneProduct("Xiaomi 14 Ultra 512GB", 21500000, "FPTShop",
                     "https://fptshop.com.vn/dien-thoai/xiaomi-14-ultra",
                     "Xiaomi", 4.5, 280),
        PhoneProduct("OPPO Find X7 Ultra 512GB", 23990000, "Cellphones",
                     "https://cellphones.com.vn/oppo-find-x7-ultra.html",
                     "OPPO", 4.5, 210),
        PhoneProduct("OPPO Find X7 Ultra 512GB", 23500000, "Thegioididong",
                     "https://thegioididong.com/dien-thoai/oppo-find-x7-ultra",
                     "OPPO", 4.4, 180),
        PhoneProduct("Samsung Galaxy A55 128GB", 9990000, "Cellphones",
                     "https://cellphones.com.vn/samsung-a55.html",
                     "Samsung", 4.4, 560),
        PhoneProduct("Samsung Galaxy A55 128GB", 9500000, "FPTShop",
                     "https://fptshop.com.vn/dien-thoai/samsung-a55",
                     "Samsung", 4.3, 420),
        PhoneProduct("Xiaomi Redmi Note 13 Pro 256GB", 6990000, "FPTShop",
                     "https://fptshop.com.vn/dien-thoai/redmi-note-13-pro",
                     "Xiaomi", 4.5, 780),
        PhoneProduct("Xiaomi Redmi Note 13 Pro 256GB", 6500000, "Thegioididong",
                     "https://thegioididong.com/dien-thoai/redmi-note-13-pro",
                     "Xiaomi", 4.6, 920),
        PhoneProduct("iPhone 15 128GB", 20990000, "Cellphones",
                     "https://cellphones.com.vn/iphone-15.html",
                     "Apple", 4.7, 1680),
        PhoneProduct("iPhone 15 128GB", 21200000, "FPTShop",
                     "https://fptshop.com.vn/dien-thoai/iphone-15",
                     "Apple", 4.6, 1200),
        PhoneProduct("iPhone 15 128GB", 20750000, "Thegioididong",
                     "https://thegioididong.com/dien-thoai/iphone-15",
                     "Apple", 4.8, 2400),
        PhoneProduct("Vivo X100 Pro 512GB", 19990000, "Cellphones",
                     "https://cellphones.com.vn/vivo-x100-pro.html",
                     "Vivo", 4.4, 150),
        PhoneProduct("Realme GT5 Pro 512GB", 15990000, "FPTShop",
                     "https://fptshop.com.vn/dien-thoai/realme-gt5-pro",
                     "Realme", 4.3, 95),
        PhoneProduct("OnePlus 12 512GB", 18990000, "Cellphones",
                     "https://cellphones.com.vn/oneplus-12.html",
                     "OnePlus", 4.5, 130),
    ]

    saved = repo.bulk_upsert(demo_products)
    return jsonify({"message": f"Seeded {saved} demo products ✓"})


if __name__ == "__main__":
    print("🚀 Phone Compare API → http://localhost:5000")
    print("📡 Seed demo data:   http://localhost:5000/api/seed")
    app.run(debug=True, port=5000)
