from scrapers.base import BaseShopeeScraper
from scrapers.registry import register


@register
class IDScraper(BaseShopeeScraper):
    region = "ID"
    domain = "shopee.co.id"
