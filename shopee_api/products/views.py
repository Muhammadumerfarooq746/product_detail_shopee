"""API views — scrape endpoints with async job dispatch."""

from __future__ import annotations

import json

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from products.dispatch import dispatch_scrape_job
from products.models import JobStatus, ProductRecord, ScrapeJob
from products.serializers import (
    BulkScrapeSerializer,
    ProductRecordSerializer,
    ScrapeCreateSerializer,
    ScrapeJobSerializer,
)


def _enqueue_job(region: str, shop_id: str, item_id: str, force: bool) -> ScrapeJob:
    """Create a job row and dispatch if pending."""
    if not force:
        existing = ProductRecord.objects.filter(
            region=region.upper(), item_id=item_id
        ).first()
        if existing:
            return ScrapeJob.objects.create(
                region=region.upper(),
                shop_id=shop_id,
                item_id=item_id,
                status=JobStatus.SKIPPED,
                force=force,
                json_path=existing.json_path,
                error_message="Already scraped; pass force=true to re-scrape",
                finished_at=timezone.now(),
            )

    job = ScrapeJob.objects.create(
        region=region.upper(),
        shop_id=shop_id,
        item_id=item_id,
        status=JobStatus.PENDING,
        force=force,
        json_path=f"{region.upper()}/{item_id}.json",
    )
    dispatch_scrape_job(job)
    return job


class ScrapeCreateView(APIView):
    """POST /api/v1/scrape/ — create one scrape job."""

    def post(self, request):
        ser = ScrapeCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        job = _enqueue_job(
            data["region"], data["shop_id"], data["item_id"], data.get("force", False)
        )
        return Response(ScrapeJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class BulkScrapeView(APIView):
    """POST /api/v1/scrape/bulk/ — create many scrape jobs."""

    def post(self, request):
        ser = BulkScrapeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        force_default = ser.validated_data.get("force", False)
        jobs = []
        for item in ser.validated_data["items"]:
            jobs.append(
                _enqueue_job(
                    item["region"],
                    item["shop_id"],
                    item["item_id"],
                    item.get("force", force_default),
                )
            )
        return Response(
            {"count": len(jobs), "jobs": ScrapeJobSerializer(jobs, many=True).data},
            status=status.HTTP_202_ACCEPTED,
        )


class JobStatusView(APIView):
    """GET /api/v1/jobs/{id}/"""

    def get(self, request, job_id: int):
        try:
            job = ScrapeJob.objects.get(pk=job_id)
        except ScrapeJob.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(ScrapeJobSerializer(job).data)


class ProductDetailView(APIView):
    """GET /api/v1/products/{region}/{item_id}/ — return JSON payload from disk."""

    def get(self, request, region: str, item_id: str):
        region = region.upper()
        try:
            record = ProductRecord.objects.get(region=region, item_id=item_id)
        except ProductRecord.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        path = record.absolute_json_path()
        if not path.is_file():
            return Response(
                {
                    "detail": "JSON file missing",
                    "region": region,
                    "item_id": item_id,
                    "json_path": record.json_path,
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        return Response(
            {
                "meta": ProductRecordSerializer(record).data,
                "data": payload,
            }
        )


class ProductListByRegionView(APIView):
    """GET /api/v1/products/{region}/ — list tracked product IDs for a region."""

    def get(self, request, region: str):
        region = region.upper()
        qs = ProductRecord.objects.filter(region=region)
        return Response(
            {
                "region": region,
                "count": qs.count(),
                "products": ProductRecordSerializer(qs[:500], many=True).data,
            }
        )


class RegionsView(APIView):
    """GET /api/v1/regions/"""

    def get(self, request):
        from scrapers.registry import available_regions

        return Response({"regions": available_regions()})
