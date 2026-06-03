"""
Concrete Crawlers - Kế thừa từ BaseCrawler
Minh họa: Inheritance + Polymorphism trong OOP
"""

from urllib.parse import quote_plus
from .base_crawler import BaseCrawler, PhoneProduct


class CellphonesCrawler(BaseCrawler):
    """Crawler cho cellphones.vn"""

    def __init__(self):
        super().__init__(
            source_name="Cellphones",
            base_url="https://cellphones.com.vn",
        )

    def _build_search_url(self, keyword: str) -> str:
        return f"{self.base_url}/catalogsearch/result/?q={quote_plus(keyword)}"

    def _parse_products(self, html: str) -> list[PhoneProduct]:
        soup = self.get_soup(html)
        products = []

        # Selector cập nhật cho cellphones.com.vn
        items = soup.select("div.product-info-container, .cps-product-item")
        if not items:
            # Fallback selectors
            items = soup.select("[class*='product'][class*='item']")

        for item in items[:20]:  # Lấy tối đa 20 sản phẩm
            try:
                name_el = item.select_one("h3, .product-name, [class*='name']")
                price_el = item.select_one(".product__price--show, [class*='price']")
                img_el = item.select_one("img")
                link_el = item.select_one("a[href]")

                if not name_el:
                    continue

                name = name_el.get_text(strip=True)
                price_str = price_el.get_text(strip=True) if price_el else "0"
                price = self._parse_price(price_str)
                image_url = img_el.get("src", "") if img_el else ""
                url = self.base_url + link_el["href"] if link_el else self.base_url

                # Lấy rating nếu có
                rating_el = item.select_one("[class*='star'], [class*='rating']")
                rating = 0.0
                if rating_el:
                    try:
                        style = rating_el.get("style", "")
                        if "width:" in style:
                            pct = float(style.split("width:")[1].replace("%", "").strip())
                            rating = round(pct / 20, 1)  # 100% → 5 sao
                    except Exception:
                        pass

                product = PhoneProduct(
                    name=name,
                    price=price,
                    source=self.source_name,
                    url=url,
                    brand=self._extract_brand(name),
                    rating=rating,
                    image_url=image_url,
                )
                products.append(product)

            except Exception as e:
                self.logger.debug(f"Parse error on item: {e}")

        return products


class FPTShopCrawler(BaseCrawler):
    """Crawler cho fptshop.com.vn"""

    def __init__(self):
        super().__init__(
            source_name="FPTShop",
            base_url="https://fptshop.com.vn",
        )

    def _build_search_url(self, keyword: str) -> str:
        return f"{self.base_url}/tim-kiem?q={quote_plus(keyword)}&category=dien-thoai"

    def _parse_products(self, html: str) -> list[PhoneProduct]:
        soup = self.get_soup(html)
        products = []

        items = soup.select(".cdt-product, [class*='product-item']")

        for item in items[:20]:
            try:
                name_el = item.select_one("h3, .product-name, [class*='name']")
                price_el = item.select_one(".price, [class*='price']")
                img_el = item.select_one("img")
                link_el = item.select_one("a[href]")

                if not name_el:
                    continue

                name = name_el.get_text(strip=True)
                price_str = price_el.get_text(strip=True) if price_el else "0"
                price = self._parse_price(price_str)
                image_url = img_el.get("src", img_el.get("data-src", "")) if img_el else ""
                href = link_el["href"] if link_el else ""
                url = href if href.startswith("http") else self.base_url + href

                # Review count
                review_el = item.select_one("[class*='review'], [class*='comment']")
                review_count = 0
                if review_el:
                    text = review_el.get_text(strip=True)
                    digits = "".join(c for c in text if c.isdigit())
                    review_count = int(digits) if digits else 0

                product = PhoneProduct(
                    name=name,
                    price=price,
                    source=self.source_name,
                    url=url,
                    brand=self._extract_brand(name),
                    review_count=review_count,
                    image_url=image_url,
                )
                products.append(product)

            except Exception as e:
                self.logger.debug(f"Parse error: {e}")

        return products


class ThegioididongCrawler(BaseCrawler):
    """Crawler cho thegioididong.com"""

    def __init__(self):
        super().__init__(
            source_name="ThegioididongCrawler",
            base_url="https://www.thegioididong.com",
        )

    def _build_search_url(self, keyword: str) -> str:
        return f"{self.base_url}/tim-kiem?key={quote_plus(keyword)}"

    def _parse_products(self, html: str) -> list[PhoneProduct]:
        soup = self.get_soup(html)
        products = []

        items = soup.select("li.item, .product-item, [class*='product']")

        for item in items[:20]:
            try:
                name_el = item.select_one("h3, .product-name, [class*='name']")
                price_el = item.select_one("strong.price, [class*='price']")
                img_el = item.select_one("img")
                link_el = item.select_one("a[href]")

                if not name_el:
                    continue

                name = name_el.get_text(strip=True)
                price = self._parse_price(price_el.get_text() if price_el else "0")
                image_url = img_el.get("src", img_el.get("data-src", "")) if img_el else ""
                href = link_el["href"] if link_el else ""
                url = href if href.startswith("http") else self.base_url + href

                # Rating từ data attribute
                rating_el = item.select_one("[data-score], [class*='star']")
                rating = 0.0
                if rating_el and rating_el.get("data-score"):
                    try:
                        rating = float(rating_el["data-score"])
                    except Exception:
                        pass

                review_el = item.select_one("[class*='review-count'], [class*='rate-count']")
                review_count = 0
                if review_el:
                    digits = "".join(c for c in review_el.get_text() if c.isdigit())
                    review_count = int(digits) if digits else 0

                product = PhoneProduct(
                    name=name,
                    price=price,
                    source=self.source_name,
                    url=url,
                    brand=self._extract_brand(name),
                    rating=rating,
                    review_count=review_count,
                    image_url=image_url,
                )
                products.append(product)

            except Exception as e:
                self.logger.debug(f"Parse error: {e}")

        return products
