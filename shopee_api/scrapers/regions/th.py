from scrapers.base import BaseShopeeScraper
from scrapers.registry import register


@register
class THScraper(BaseShopeeScraper):
    region = "TH"
    domain = "shopee.co.th"
