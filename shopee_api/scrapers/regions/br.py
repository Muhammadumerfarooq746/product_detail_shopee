from scrapers.base import BaseShopeeScraper
from scrapers.registry import register


@register
class BRScraper(BaseShopeeScraper):
    region = "BR"
    domain = "shopee.com.br"
    preferred_language = "English*"
