"""Region scraper registry."""

from __future__ import annotations

from typing import TYPE_CHECKING, Type

from scrapers.base import REGION_DOMAINS, BaseShopeeScraper

if TYPE_CHECKING:
    pass

_REGISTRY: dict[str, Type[BaseShopeeScraper]] = {}


def register(cls: Type[BaseShopeeScraper]) -> Type[BaseShopeeScraper]:
    key = cls.region.upper()
    _REGISTRY[key] = cls
    return cls


def domain_for(region: str) -> str:
    return REGION_DOMAINS[region.lower()]


def get_scraper_class(region: str) -> Type[BaseShopeeScraper]:
    key = region.upper()
    if key not in _REGISTRY:
        # Import regions lazily so registry is populated
        import scrapers.regions  # noqa: F401

    if key not in _REGISTRY:
        raise KeyError(f"Unknown region: {region!r}. Known: {sorted(_REGISTRY)}")
    return _REGISTRY[key]


def available_regions() -> list[str]:
    import scrapers.regions  # noqa: F401

    return sorted(_REGISTRY.keys())
