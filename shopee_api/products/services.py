"""Execute a ScrapeJob: run region scraper, write JSON, update DB tracking."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from products.models import JobStatus, ProductRecord, ScrapeJob
from scrapers.registry import get_scraper_class

logger = logging.getLogger(__name__)


def _scraper_kwargs() -> dict:
    return {
        "output_dir": Path(settings.SHOPEE_OUTPUT_DIR),
        "chrome_path": settings.SHOPEE_CHROME_PATH,
        "headless": bool(getattr(settings, "SHOPEE_HEADLESS", False)),
        "max_attempts": int(getattr(settings, "SHOPEE_MAX_ATTEMPTS", 3)),
        "use_proxy": bool(getattr(settings, "SHOPEE_USE_PROXY", False)),
        "language": getattr(settings, "SHOPEE_LANGUAGE", "English*"),
    }


def execute_scrape_job(job_id: int) -> dict:
    """
    Run scrape for job_id. Safe to call from Celery, thread, or management command.
    Returns a small status dict.
    """
    try:
        job = ScrapeJob.objects.get(pk=job_id)
    except ScrapeJob.DoesNotExist:
        logger.error("ScrapeJob %s not found", job_id)
        return {"ok": False, "error": "job_not_found", "job_id": job_id}

    if job.status == JobStatus.SKIPPED:
        return {"ok": True, "status": JobStatus.SKIPPED, "job_id": job_id}

    if job.status == JobStatus.SUCCESS and not job.force:
        return {"ok": True, "status": JobStatus.SUCCESS, "job_id": job_id}

    job.status = JobStatus.RUNNING
    job.error_message = ""
    job.save(update_fields=["status", "error_message", "updated_at"])

    try:
        scraper_cls = get_scraper_class(job.region)
        scraper = scraper_cls(**_scraper_kwargs())
        result = asyncio.run(scraper.run(job.shop_id, job.item_id))
    except Exception as exc:  # noqa: BLE001 — surface any scraper/browser failure
        logger.exception("Scrape job %s failed", job_id)
        job.status = JobStatus.FAILED
        job.error_message = str(exc)[:2000]
        job.finished_at = timezone.now()
        job.save(
            update_fields=["status", "error_message", "finished_at", "updated_at"]
        )
        return {"ok": False, "status": JobStatus.FAILED, "job_id": job_id, "error": str(exc)}

    if not result.ok:
        job.status = JobStatus.FAILED
        job.error_message = (result.error or "scrape_failed")[:2000]
        job.finished_at = timezone.now()
        job.save(
            update_fields=["status", "error_message", "finished_at", "updated_at"]
        )
        return {
            "ok": False,
            "status": JobStatus.FAILED,
            "job_id": job_id,
            "error": job.error_message,
        }

    relpath = job.default_json_relpath()
    if result.json_path:
        try:
            relpath = str(
                Path(result.json_path).resolve().relative_to(
                    Path(settings.SHOPEE_OUTPUT_DIR).resolve()
                )
            )
        except ValueError:
            relpath = f"{job.region}/{job.item_id}.json"

    with transaction.atomic():
        job.status = JobStatus.SUCCESS
        job.json_path = relpath
        job.error_message = ""
        job.finished_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "json_path",
                "error_message",
                "finished_at",
                "updated_at",
            ]
        )
        record, _ = ProductRecord.objects.update_or_create(
            region=job.region,
            item_id=job.item_id,
            defaults={
                "shop_id": job.shop_id,
                "json_path": relpath,
                "last_job": job,
            },
        )

    logger.info(
        "Scrape job %s success -> %s (record=%s)",
        job_id,
        relpath,
        record.pk,
    )
    return {
        "ok": True,
        "status": JobStatus.SUCCESS,
        "job_id": job_id,
        "json_path": relpath,
    }
