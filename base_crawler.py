"""
Base Crawler - Abstract class cho tất cả website crawlers
Minh họa: Abstraction, Inheritance trong OOP
"""

import abc
import time
import logging
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s')


@dataclass
class PhoneProduct:
    """Data class đại diện cho một sản phẩm điện thoại"""
    name: str
    price: float
    source: str          # Tên website
    url: str
    brand: str = ""
    rating: float = 0.0
    review_count: int = 0
    image_url: str = ""
    specs: dict = field(default_factory=dict)
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "price": self.price,
            "source": self.source,
            "url": self.url,
            "brand": self.brand,
            "rating": self.rating,
            "review_count": self.review_count,
            "image_url": self.image_url,
            "specs": self.specs,
            "scraped_at": self.scraped_at,
        }


class BaseCrawler(abc.ABC):
    """
    Abstract Base Class cho tất cả website crawlers.
    Nguyên tắc OOP: Abstraction + Template Method Pattern
    """

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
    }
    REQUEST_DELAY = 1.5   # giây giữa các request (lịch sự với server)
    MAX_RETRIES = 3

    def __init__(self, source_name: str, base_url: str):
        self.source_name = source_name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.logger = logging.getLogger(source_name)

    # ── Template Method ──────────────────────────────────────────────────────
    def search(self, keyword: str) -> list[PhoneProduct]:
        """
        Template method: định nghĩa skeleton của thuật toán tìm kiếm.
        Các bước cụ thể do subclass implement.
        """
        self.logger.info(f"Searching '{keyword}' on {self.source_name}...")
        url = self._build_search_url(keyword)
        html = self._fetch(url)
        if not html:
            return []
        products = self._parse_products(html)
        self.logger.info(f"Found {len(products)} products")
        return products

    # ── Abstract methods (bắt buộc subclass phải implement) ──────────────────
    @abc.abstractmethod
    def _build_search_url(self, keyword: str) -> str:
        """Tạo URL tìm kiếm theo format của từng website"""
        ...

    @abc.abstractmethod
    def _parse_products(self, html: str) -> list[PhoneProduct]:
        """Parse HTML và trả về danh sách sản phẩm"""
        ...

    # ── Shared utilities ─────────────────────────────────────────────────────
    def _fetch(self, url: str) -> Optional[str]:
        """Fetch HTML với retry logic"""
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                time.sleep(self.REQUEST_DELAY)
                resp = self.session.get(url, timeout=10)
                resp.raise_for_status()
                resp.encoding = "utf-8"
                return resp.text
            except requests.RequestException as e:
                self.logger.warning(f"Attempt {attempt}/{self.MAX_RETRIES} failed: {e}")
                if attempt == self.MAX_RETRIES:
                    self.logger.error(f"Failed to fetch {url}")
        return None

    @staticmethod
    def _parse_price(price_str: str) -> float:
        """Xử lý chuỗi giá tiền → float. VD: '15.990.000₫' → 15990000.0"""
        if not price_str:
            return 0.0
        # Xóa ký tự không phải số
        cleaned = "".join(c for c in price_str if c.isdigit())
        return float(cleaned) if cleaned else 0.0

    @staticmethod
    def _extract_brand(name: str) -> str:
        """Trích xuất brand từ tên sản phẩm"""
        brands = [
            "Samsung", "Apple", "iPhone", "Xiaomi", "OPPO", "Vivo",
            "Realme", "OnePlus", "Huawei", "Nokia", "Sony", "Motorola",
        ]
        name_lower = name.lower()
        for brand in brands:
            if brand.lower() in name_lower:
                return brand if brand != "iPhone" else "Apple"
        return "Unknown"

    def get_soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")
