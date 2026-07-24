"""Import all region scrapers so they register themselves."""

from scrapers.regions.br import BRScraper
from scrapers.regions.id import IDScraper
from scrapers.regions.my import MYScraper
from scrapers.regions.ph import PHScraper
from scrapers.regions.sg import SGScraper
from scrapers.regions.th import THScraper
from scrapers.regions.tw import TWScraper
from scrapers.regions.vn import VNScraper

__all__ = [
    "SGScraper",
    "MYScraper",
    "IDScraper",
    "THScraper",
    "VNScraper",
    "PHScraper",
    "TWScraper",
    "BRScraper",
]
