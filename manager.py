"""
CrawlerManager - Quản lý nhiều crawlers (Facade Pattern)
DataProcessor  - Xử lý & chuẩn hóa dữ liệu
"""

import concurrent.futures
import re
from .base_crawler import BaseCrawler, PhoneProduct
from .crawlers import CellphonesCrawler, FPTShopCrawler, ThegioididongCrawler


class CrawlerManager:
    """
    Quản lý toàn bộ crawlers theo Facade Pattern.
    Client chỉ cần gọi search() mà không cần biết có bao nhiêu crawler.
    """

    def __init__(self):
        self._crawlers: list[BaseCrawler] = [
            CellphonesCrawler(),
            FPTShopCrawler(),
            ThegioididongCrawler(),
        ]

    def register(self, crawler: BaseCrawler):
        """Mở rộng hệ thống: thêm crawler mới (Open/Closed Principle)"""
        self._crawlers.append(crawler)

    def search_all(self, keyword: str, max_workers: int = 3) -> list[PhoneProduct]:
        """
        Tìm kiếm song song trên tất cả websites.
        Dùng ThreadPoolExecutor để tăng tốc độ.
        """
        results: list[PhoneProduct] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(crawler.search, keyword): crawler.source_name
                for crawler in self._crawlers
            }
            for future in concurrent.futures.as_completed(futures):
                source = futures[future]
                try:
                    products = future.result()
                    results.extend(products)
                except Exception as e:
                    print(f"[{source}] Error: {e}")

        return results


class DataProcessor:
    """
    Xử lý và chuẩn hóa dữ liệu crawl được.
    Minh họa: Single Responsibility Principle
    """

    # Mapping tên không chuẩn → tên chuẩn
    BRAND_ALIASES: dict[str, str] = {
        "iphone": "Apple",
        "apple": "Apple",
        "samsung": "Samsung",
        "galaxy": "Samsung",
        "xiaomi": "Xiaomi",
        "redmi": "Xiaomi",
        "poco": "Xiaomi",
        "oppo": "OPPO",
        "reno": "OPPO",
        "find": "OPPO",
        "vivo": "Vivo",
        "realme": "Realme",
        "oneplus": "OnePlus",
        "nokia": "Nokia",
    }

    def normalize(self, products: list[PhoneProduct]) -> list[PhoneProduct]:
        """Pipeline xử lý dữ liệu: normalize → deduplicate → validate"""
        products = [self._normalize_product(p) for p in products]
        products = self._remove_invalid(products)
        return products

    def _normalize_product(self, p: PhoneProduct) -> PhoneProduct:
        """Chuẩn hóa tên, giá, brand"""
        p.name = self._clean_name(p.name)
        p.brand = self._resolve_brand(p.name, p.brand)
        if p.price and p.price < 1000:
            # Giá có thể đang ở đơn vị nghìn đồng
            p.price *= 1000
        p.rating = round(min(max(p.rating, 0), 5), 1)  # Clamp 0-5
        return p

    @staticmethod
    def _clean_name(name: str) -> str:
        """Xóa ký tự thừa, normalize whitespace"""
        name = re.sub(r"\s+", " ", name).strip()
        # Xóa những phần quảng cáo thường gặp
        for noise in ["[Trả góp 0%]", "[Mới]", "- Chính hãng", "(Chính hãng)"]:
            name = name.replace(noise, "").strip()
        return name

    def _resolve_brand(self, name: str, current_brand: str) -> str:
        """Xác định brand chính xác từ tên sản phẩm"""
        name_lower = name.lower()
        for keyword, brand in self.BRAND_ALIASES.items():
            if keyword in name_lower:
                return brand
        return current_brand or "Unknown"

    @staticmethod
    def _remove_invalid(products: list[PhoneProduct]) -> list[PhoneProduct]:
        """Loại bỏ sản phẩm không hợp lệ (giá = 0, tên rỗng)"""
        return [p for p in products if p.name and p.price > 0]

    @staticmethod
    def group_by_brand(products: list[PhoneProduct]) -> dict[str, list[PhoneProduct]]:
        """Nhóm sản phẩm theo thương hiệu"""
        groups: dict[str, list[PhoneProduct]] = {}
        for p in products:
            groups.setdefault(p.brand, []).append(p)
        return groups

    @staticmethod
    def sort_by_price(products: list[PhoneProduct], asc: bool = True) -> list[PhoneProduct]:
        return sorted(products, key=lambda p: p.price, reverse=not asc)

    @staticmethod
    def sort_by_rating(products: list[PhoneProduct]) -> list[PhoneProduct]:
        return sorted(products, key=lambda p: (p.rating, p.review_count), reverse=True)
