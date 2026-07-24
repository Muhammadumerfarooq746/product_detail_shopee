"""Celery tasks for Shopee scrape jobs."""

from __future__ import annotations

from celery import shared_task

from products.services import execute_scrape_job


@shared_task(bind=True, name="products.run_scrape_job", max_retries=0)
def run_scrape_job(self, job_id: int) -> dict:
    """Async scrape worker entrypoint."""
    return execute_scrape_job(job_id)
