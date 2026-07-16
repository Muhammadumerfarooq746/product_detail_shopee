import json
import os
from pathlib import Path

import requests

API_TOKEN = os.environ.get(
    "NOXAPI_TOKEN",
    "",
)

URL = "http://api.noxapi.com/v1/shopee/item_detail_by_url"

payload = {
    "url": "https://shopee.vn/product/550942423/24322062261",
}

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

response = requests.post(URL, json=payload, headers=headers, timeout=60)
if not response.ok:
    raise SystemExit(f"HTTP {response.status_code}: {response.text}")

data = response.json()
out = Path("shopee") / "550942423_24322062261_noxapi.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved -> {out}")
