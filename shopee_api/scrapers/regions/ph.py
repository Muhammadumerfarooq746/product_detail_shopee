from scrapers.base import BaseShopeeScraper
from scrapers.registry import register


@register
class PHScraper(BaseShopeeScraper):
    region = "PH"
    domain = "shopee.ph"
