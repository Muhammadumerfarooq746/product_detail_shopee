"""Import already-downloaded JSON into ProductRecord tracking rows."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from products.models import ProductRecord


class Command(BaseCommand):
    help = (
        "Scan SHOPEE_OUTPUT_DIR/{REGION}/*.json and upsert ProductRecord rows "
        "(IDs only; payload stays on disk)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be imported without writing DB",
        )

    def handle(self, *args, **options):
        root = Path(settings.SHOPEE_OUTPUT_DIR)
        if not root.is_dir():
            self.stdout.write(f"No output dir: {root}")
            return

        dry = options["dry_run"]
        created = updated = skipped = 0

        for region_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            region = region_dir.name.upper()
            for path in sorted(region_dir.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    self.stderr.write(f"Skip {path}: {exc}")
                    skipped += 1
                    continue

                item_id = str(data.get("item_id") or path.stem)
                shop_id = str(data.get("shop_id") or "")
                if not shop_id or not item_id:
                    skipped += 1
                    continue

                relpath = f"{region}/{path.name}"
                if dry:
                    self.stdout.write(f"would upsert {region} {shop_id}/{item_id}")
                    created += 1
                    continue

                _, was_created = ProductRecord.objects.update_or_create(
                    region=region,
                    item_id=item_id,
                    defaults={"shop_id": shop_id, "json_path": relpath},
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"done created={created} updated={updated} skipped={skipped} dry_run={dry}"
            )
        )
