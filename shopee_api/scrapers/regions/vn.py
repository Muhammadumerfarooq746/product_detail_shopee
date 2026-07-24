from scrapers.base import BaseShopeeScraper
from scrapers.registry import register


@register
class VNScraper(BaseShopeeScraper):
    region = "VN"
    domain = "shopee.vn"
