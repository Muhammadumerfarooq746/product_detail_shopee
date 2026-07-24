from django.core.management.base import BaseCommand

from products.models import JobStatus, ScrapeJob
from products.services import execute_scrape_job


class Command(BaseCommand):
    help = "Run pending (or a specific) scrape job(s) synchronously."

    def add_arguments(self, parser):
        parser.add_argument(
            "--job-id",
            type=int,
            help="Run a single job by id",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Max pending jobs to run when --job-id is omitted",
        )
        parser.add_argument(
            "--all-pending",
            action="store_true",
            help="Run all pending jobs (respects --limit unless set high)",
        )

    def handle(self, *args, **options):
        job_id = options.get("job_id")
        if job_id:
            result = execute_scrape_job(job_id)
            self.stdout.write(self.style.SUCCESS(str(result)))
            return

        qs = ScrapeJob.objects.filter(status=JobStatus.PENDING).order_by("id")
        limit = options["limit"]
        jobs = list(qs[:limit])
        if not jobs:
            self.stdout.write("No pending jobs.")
            return

        self.stdout.write(f"Running {len(jobs)} pending job(s)...")
        for job in jobs:
            self.stdout.write(f"--- job {job.id} {job.region} {job.item_id} ---")
            result = execute_scrape_job(job.id)
            style = self.style.SUCCESS if result.get("ok") else self.style.ERROR
            self.stdout.write(style(str(result)))
