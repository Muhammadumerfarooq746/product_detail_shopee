import base64
import json
import os
import time
from pathlib import Path

import requests

API_KEY = os.environ.get(
    "SCRAPELESS_API_TOKEN",
    "",
)
HOST = "api.scrapeless.com"
REQUEST_URL = f"https://{HOST}/api/v1/scraper/request"

ROOT = Path(__file__).resolve().parent
IDS_FILE = ROOT / "shopee_id.txt"
OUTPUT_DIR = ROOT / "shopee"

REGION_DOMAINS = {
    "sg": "shopee.sg",
    "id": "shopee.co.id",
    "vn": "shopee.vn",
    "th": "shopee.co.th",
    "ph": "shopee.ph",
    "my": "shopee.com.my",
    "tw": "shopee.tw",
    "co": "shopee.com.co",
    "cl": "shopee.cl",
    "mx": "shopee.com.mx",
    "br": "shopee.com.br",
}


def resolve_region(region: str) -> str:
    key = region.strip().lower()
    if key in REGION_DOMAINS:
        return REGION_DOMAINS[key]
    if key.startswith("shopee."):
        return key
    raise ValueError(f"Unknown region: {region!r}")


def build_pdp_url(region: str, shop_id: str, item_id: str) -> str:
    return f"https://{region}/api/v4/pdp/get_pc?item_id={item_id}&shop_id={shop_id}"


def parse_ids_file(path: Path) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 3:
            raise ValueError(
                f"{path}:{line_no}: expected region,shop_id,item_id — got {line!r}"
            )
        region_key, shop_id, item_id = parts
        entries.append((resolve_region(region_key), shop_id, item_id))
    if not entries:
        raise ValueError(f"No product IDs found in {path}")
    return entries


def create_task(product_url: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "x-api-token": API_KEY,
    }
    payload = {
        "actor": "scraper.shopeev3",
        "input": {
            "action": "shopee.product",
            "url": product_url,
        },
    }
    response = requests.post(REQUEST_URL, headers=headers, json=payload, timeout=60)
    task_id = response.headers.get("x-task-id")
    if not task_id:
        try:
            body = response.json()
            task_id = body.get("taskId") or body.get("task_id")
        except json.JSONDecodeError:
            pass
    if not task_id:
        raise RuntimeError(
            f"Scrapeless did not return a task id (HTTP {response.status_code}): {response.text}"
        )
    return task_id


def decode_task_payload(payload: dict) -> dict:
    response = payload.get("response", {})
    if response.get("encoding") == "base64" and response.get("data"):
        decoded = base64.b64decode(response["data"]).decode("utf-8")
        try:
            return json.loads(decoded)
        except json.JSONDecodeError:
            return {"raw": decoded}
    if isinstance(payload.get("data"), (dict, list)):
        return payload["data"]
    return payload


def poll_result(task_id: str, max_attempts: int = 60, interval: float = 2.0) -> dict:
    headers = {"x-api-token": API_KEY}
    result_url = f"https://{HOST}/api/v1/scraper/result/{task_id}"

    for attempt in range(max_attempts):
        response = requests.get(result_url, headers=headers, timeout=60)

        try:
            body = response.json()
        except json.JSONDecodeError:
            body = None

        if response.status_code == 400 and isinstance(body, dict) and body.get("code") == 20500:
            if attempt >= 2:
                raise RuntimeError(
                    f"Scrapeless error 20500 for task {task_id}. "
                    "Check API quota or actor access in your Scrapeless dashboard."
                )
            time.sleep(interval)
            continue

        if response.status_code not in (200, 201):
            if attempt + 1 < max_attempts:
                time.sleep(interval)
                continue
            raise RuntimeError(
                f"Task {task_id} failed (HTTP {response.status_code}): {response.text}"
            )

        if body is None:
            return {"raw": response.text}

        state = body.get("state")
        if state == "completed":
            if body.get("success") is False:
                raise RuntimeError(f"Task {task_id} failed: {json.dumps(body)}")
            return decode_task_payload(body)

        if response.status_code == 200 and "data" in body and state is None:
            return decode_task_payload(body)

        if attempt + 1 < max_attempts:
            time.sleep(interval)
            continue

        raise TimeoutError(
            f"Task {task_id} did not complete after {max_attempts} attempts: {json.dumps(body)}"
        )

    raise TimeoutError(f"Task {task_id} timed out")


def save_product(region: str, shop_id: str, item_id: str) -> Path:
    product_url = build_pdp_url(region, shop_id, item_id)
    task_id = create_task(product_url)
    print(f"shop_id={shop_id} item_id={item_id} task_id={task_id}")

    data = poll_result(task_id)
    out_path = OUTPUT_DIR / f"{shop_id}_{item_id}.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    products = parse_ids_file(IDS_FILE)

    for region, shop_id, item_id in products:
        try:
            out_path = save_product(region, shop_id, item_id)
            print(f"Saved -> {out_path}")
        except Exception as exc:
            print(f"Failed shop_id={shop_id} item_id={item_id}: {exc}")


if __name__ == "__main__":
    main()
