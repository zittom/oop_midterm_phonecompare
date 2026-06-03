"""
Database Layer - SQLite + Repository Pattern
Minh họa: Encapsulation, Separation of Concerns
Mô hình lưu trữ tối ưu cho hiệu suất truy vấn (indexes, FTS)
"""

import sqlite3
import json
from contextlib import contextmanager
from typing import Optional
from crawler.base_crawler import PhoneProduct


DB_PATH = "phone_compare.db"

# ─── Schema ──────────────────────────────────────────────────────────────────
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    price       REAL    NOT NULL,
    source      TEXT    NOT NULL,
    url         TEXT,
    brand       TEXT,
    rating      REAL    DEFAULT 0,
    review_count INTEGER DEFAULT 0,
    image_url   TEXT,
    specs       TEXT,          -- JSON
    scraped_at  TEXT,
    UNIQUE(name, source)       -- Tránh duplicate
);

-- Full-Text Search index (tìm kiếm nhanh theo tên)
CREATE VIRTUAL TABLE IF NOT EXISTS products_fts USING fts5(
    name,
    brand,
    content='products',
    content_rowid='id'
);

-- Trigger đồng bộ FTS khi INSERT
CREATE TRIGGER IF NOT EXISTS products_ai AFTER INSERT ON products BEGIN
    INSERT INTO products_fts(rowid, name, brand)
    VALUES (new.id, new.name, new.brand);
END;

-- Trigger đồng bộ FTS khi DELETE
CREATE TRIGGER IF NOT EXISTS products_ad AFTER DELETE ON products BEGIN
    INSERT INTO products_fts(products_fts, rowid, name, brand)
    VALUES ('delete', old.id, old.name, old.brand);
END;

-- Index tối ưu truy vấn theo giá và brand
CREATE INDEX IF NOT EXISTS idx_price  ON products(price);
CREATE INDEX IF NOT EXISTS idx_brand  ON products(brand);
CREATE INDEX IF NOT EXISTS idx_source ON products(source);
"""


class DatabaseManager:
    """Quản lý kết nối SQLite (Singleton Pattern)"""

    _instance: Optional["DatabaseManager"] = None

    def __new__(cls, db_path: str = DB_PATH):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.db_path = db_path
            cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)
        print(f"[DB] Initialized → {self.db_path}")

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")   # Tăng hiệu suất ghi
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


class ProductRepository:
    """
    Repository Pattern: tách biệt logic truy vấn khỏi business logic.
    Mọi thao tác với DB đều đi qua đây.
    """

    def __init__(self):
        self.db = DatabaseManager()

    # ── Write ─────────────────────────────────────────────────────────────────
    def upsert(self, product: PhoneProduct) -> int:
        """Insert hoặc update nếu (name, source) đã tồn tại"""
        sql = """
            INSERT INTO products
                (name, price, source, url, brand, rating, review_count, image_url, specs, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name, source) DO UPDATE SET
                price        = excluded.price,
                rating       = excluded.rating,
                review_count = excluded.review_count,
                scraped_at   = excluded.scraped_at
        """
        with self.db._connect() as conn:
            cur = conn.execute(sql, (
                product.name, product.price, product.source,
                product.url, product.brand, product.rating,
                product.review_count, product.image_url,
                json.dumps(product.specs, ensure_ascii=False),
                product.scraped_at,
            ))
            return cur.lastrowid

    def bulk_upsert(self, products: list[PhoneProduct]) -> int:
        """Lưu nhiều sản phẩm cùng lúc (hiệu quả hơn loop)"""
        count = 0
        for p in products:
            self.upsert(p)
            count += 1
        print(f"[DB] Saved {count} products")
        return count

    # ── Read ──────────────────────────────────────────────────────────────────
    def search(self, keyword: str, limit: int = 50) -> list[dict]:
        """Tìm kiếm Full-Text Search (nhanh hơn LIKE)"""
        sql = """
            SELECT p.*
            FROM   products p
            JOIN   products_fts f ON f.rowid = p.id
            WHERE  products_fts MATCH ?
            ORDER  BY p.price ASC
            LIMIT  ?
        """
        # Escape ký tự đặc biệt của FTS5
        safe_kw = keyword.replace('"', '""')
        try:
            with self.db._connect() as conn:
                rows = conn.execute(sql, (f'"{safe_kw}"', limit)).fetchall()
                return [dict(r) for r in rows]
        except sqlite3.OperationalError:
            # Fallback: dùng LIKE nếu FTS lỗi
            return self.search_like(keyword, limit)

    def search_like(self, keyword: str, limit: int = 50) -> list[dict]:
        """Fallback search bằng LIKE"""
        sql = """
            SELECT * FROM products
            WHERE  name  LIKE ? OR brand LIKE ?
            ORDER  BY price ASC
            LIMIT  ?
        """
        pattern = f"%{keyword}%"
        with self.db._connect() as conn:
            rows = conn.execute(sql, (pattern, pattern, limit)).fetchall()
            return [dict(r) for r in rows]

    def get_cheapest_by_model(self, model_name: str) -> list[dict]:
        """So sánh giá cùng model từ các nguồn khác nhau"""
        sql = """
            SELECT source, MIN(price) as price, url, rating, review_count, image_url
            FROM   products
            WHERE  name LIKE ?
            GROUP  BY source
            ORDER  BY price ASC
        """
        with self.db._connect() as conn:
            rows = conn.execute(sql, (f"%{model_name}%",)).fetchall()
            return [dict(r) for r in rows]

    def get_all(self, brand: str = None, max_price: float = None,
                min_rating: float = None, limit: int = 100) -> list[dict]:
        """Lấy sản phẩm với bộ lọc"""
        conditions = []
        params = []
        if brand:
            conditions.append("brand = ?")
            params.append(brand)
        if max_price:
            conditions.append("price <= ?")
            params.append(max_price)
        if min_rating:
            conditions.append("rating >= ?")
            params.append(min_rating)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"SELECT * FROM products {where} ORDER BY price ASC LIMIT ?"
        params.append(limit)

        with self.db._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def get_brands(self) -> list[str]:
        """Lấy danh sách thương hiệu có trong DB"""
        with self.db._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT brand FROM products WHERE brand != 'Unknown' ORDER BY brand"
            ).fetchall()
            return [r["brand"] for r in rows]

    def get_stats(self) -> dict:
        """Thống kê tổng quan"""
        with self.db._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            sources = conn.execute(
                "SELECT source, COUNT(*) as cnt FROM products GROUP BY source"
            ).fetchall()
            cheapest = conn.execute(
                "SELECT name, price, source FROM products ORDER BY price ASC LIMIT 1"
            ).fetchone()
            return {
                "total_products": total,
                "by_source": {r["source"]: r["cnt"] for r in sources},
                "cheapest": dict(cheapest) if cheapest else None,
            }
