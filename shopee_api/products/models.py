"""
DB stores region + shop_id + item_id and job tracking only.
Scrape payloads live as JSON files under SHOPEE_OUTPUT_DIR/{REGION}/{item_id}.json
and are returned by the API when requested.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from pathlib import Path


class Region(models.TextChoices):
    SG = "SG", "Singapore"
    MY = "MY", "Malaysia"
    ID = "ID", "Indonesia"
    TH = "TH", "Thailand"
    VN = "VN", "Vietnam"
    PH = "PH", "Philippines"
    TW = "TW", "Taiwan"
    BR = "BR", "Brazil"


class JobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"
    SKIPPED = "skipped", "Skipped"


class ScrapeJob(models.Model):
    """One scrape attempt for a (region, shop_id, item_id)."""

    region = models.CharField(max_length=2, choices=Region.choices, db_index=True)
    shop_id = models.CharField(max_length=32, db_index=True)
    item_id = models.CharField(max_length=32, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
        db_index=True,
    )
    force = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, default="")
    # Relative path under SHOPEE_OUTPUT_DIR, e.g. SG/28457123615.json
    json_path = models.CharField(max_length=512, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["region", "shop_id", "item_id"]),
            models.Index(fields=["region", "item_id"]),
            models.Index(fields=["status", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Job#{self.pk} {self.region} {self.shop_id}/{self.item_id} [{self.status}]"

    @property
    def product_url(self) -> str:
        from scrapers.registry import domain_for

        domain = domain_for(self.region)
        return f"https://{domain}/product/{self.shop_id}/{self.item_id}"

    def absolute_json_path(self) -> Path | None:
        if not self.json_path:
            return None
        return Path(settings.SHOPEE_OUTPUT_DIR) / self.json_path

    def default_json_relpath(self) -> str:
        return f"{self.region.upper()}/{self.item_id}.json"


class ProductRecord(models.Model):
    """
    Tracking row for a successfully scraped product.
    Does not store the scrape payload — only IDs + pointer to JSON file.
    """

    region = models.CharField(max_length=2, choices=Region.choices, db_index=True)
    shop_id = models.CharField(max_length=32, db_index=True)
    item_id = models.CharField(max_length=32, db_index=True)
    json_path = models.CharField(max_length=512)
    last_job = models.ForeignKey(
        ScrapeJob,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="product_records",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["region", "item_id"],
                name="uniq_region_item",
            ),
        ]
        indexes = [
            models.Index(fields=["region", "shop_id", "item_id"]),
        ]
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.region} {self.shop_id}/{self.item_id}"

    def absolute_json_path(self) -> Path:
        return Path(settings.SHOPEE_OUTPUT_DIR) / self.json_path
