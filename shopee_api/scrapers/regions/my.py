from scrapers.base import BaseShopeeScraper
from scrapers.registry import register


@register
class MYScraper(BaseShopeeScraper):
    region = "MY"
    domain = "shopee.com.my"
