"""Dispatch scrape jobs via Celery, background thread, or inline."""

from __future__ import annotations

import logging
import threading

from django.conf import settings

from products.models import JobStatus, ScrapeJob

logger = logging.getLogger(__name__)


def dispatch_scrape_job(job: ScrapeJob) -> None:
    """Queue a pending job according to SHOPEE_DISPATCH_MODE."""
    if job.status != JobStatus.PENDING:
        return

    mode = getattr(settings, "SHOPEE_DISPATCH_MODE", "thread").lower()

    if mode == "celery":
        from products.tasks import run_scrape_job

        run_scrape_job.delay(job.id)
        logger.info("Dispatched job %s via celery", job.id)
        return

    if mode == "eager":
        from products.services import execute_scrape_job

        execute_scrape_job(job.id)
        logger.info("Ran job %s eagerly", job.id)
        return

    # Default: background thread (no Redis required for local dev)
    from django.db import close_old_connections

    from products.services import execute_scrape_job

    def _run(job_id: int) -> None:
        close_old_connections()
        try:
            execute_scrape_job(job_id)
        finally:
            close_old_connections()

    t = threading.Thread(
        target=_run,
        args=(job.id,),
        name=f"scrape-job-{job.id}",
        daemon=True,
    )
    t.start()
    logger.info("Dispatched job %s via thread", job.id)
