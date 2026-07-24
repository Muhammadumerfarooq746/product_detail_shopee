from scrapers.base import BaseShopeeScraper
from scrapers.registry import register


@register
class TWScraper(BaseShopeeScraper):
    region = "TW"
    domain = "shopee.tw"
