from scrapers.base import BaseShopeeScraper
from scrapers.registry import register


@register
class SGScraper(BaseShopeeScraper):
    region = "SG"
    domain = "shopee.sg"
