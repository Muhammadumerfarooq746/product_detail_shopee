# Shopee scrape API

Django + DRF under `shopee_api/`.

## Storage

- **DB:** `region`, `shop_id`, `item_id` + job status
- **Payload:** `output/{REGION}/{item_id}.json` (returned by product API)

## Quick start

```bash
cd shopee_api
source ../.venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Default dispatch mode is `thread` (no Redis). For Celery:

```bash
# terminal 1 — Redis must be running
export SHOPEE_DISPATCH_MODE=celery
celery -A config worker -l info

# terminal 2
export SHOPEE_DISPATCH_MODE=celery
python manage.py runserver
```

## API (v1)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/regions/` | list regions |
| POST | `/api/v1/scrape/` | create scrape job (dispatches worker) |
| POST | `/api/v1/scrape/bulk/` | bulk create jobs |
| GET | `/api/v1/jobs/{id}/` | job status |
| GET | `/api/v1/products/{region}/` | list tracked IDs |
| GET | `/api/v1/products/{region}/{item_id}/` | return JSON payload |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/scrape/ \
  -H 'Content-Type: application/json' \
  -d '{"region":"SG","shop_id":"268706552","item_id":"28457123615"}'

curl http://127.0.0.1:8000/api/v1/jobs/1/
```

## Management commands

```bash
# Run pending jobs sync (useful if dispatch failed)
python manage.py run_scrape_jobs --limit 5
python manage.py run_scrape_jobs --job-id 1

# Register existing JSON files into ProductRecord
python manage.py import_json_records
# Or point at shopeebr output:
# SHOPEE_OUTPUT_DIR=../shopeebr/output python manage.py import_json_records
```

## Env

| Variable | Default | Notes |
|----------|---------|-------|
| `SHOPEE_DISPATCH_MODE` | `thread` | `thread` / `celery` / `eager` |
| `SHOPEE_HEADLESS` | `false` | Chrome headless |
| `SHOPEE_USE_PROXY` | `0` | needs `LUMINATI_*` env |
| `SHOPEE_MAX_ATTEMPTS` | `3` | retries per product |
| `CELERY_BROKER_URL` | `redis://127.0.0.1:6379/0` | when mode=celery |
