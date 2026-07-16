"""
Shopee PDP via SeleniumBase UC + CDP Mode (captures /api/v4/pdp/get_pc).

Uses the official CDP network handler pattern — NOT the old
add_cdp_listener + open() + --incognito combo (that closes the window).

  python test_s2.py
"""

import json
import re
import time
from urllib.parse import parse_qs, urlparse

import mycdp
from seleniumbase import SB

# ============ EDIT THESE ============
PRODUCT_URL = "https://shopee.co.id/product/451021432/23285088262"
# SeleniumBase proxy format: user:pass@host:port  (no http://)
# PROXY = "bP5bJCxteU:z2NSRniBeo@170.124.199.150:19685"
PROXY = None
HEADLESS = False
TIMEOUT_SEC = 60
# ====================================

xhr_hits = []  # [url, request_id]


def parse_product_ids(product_url: str):
    path = urlparse(product_url).path
    m = re.search(r"/product/(\d+)/(\d+)", path)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"[.-]i[.-](\d+)[.-](\d+)", path)
    if m:
        return m.group(1), m.group(2)
    raise ValueError(f"Could not parse shop_id/item_id from: {product_url}")


def is_target_get_pc(url: str, shop_id: str, item_id: str) -> bool:
    if "/api/v4/pdp/get_pc" not in url:
        return False
    qs = parse_qs(urlparse(url).query)
    return qs.get("shop_id", [None])[0] == shop_id and qs.get("item_id", [None])[0] == item_id


def is_valid_pdp(data) -> bool:
    try:
        return data.get("data", {}).get("item", {}).get("item_id") is not None
    except Exception:
        return False


def listen_get_pc(page, shop_id: str, item_id: str):
    async def handler(evt):
        url = evt.response.url
        if is_target_get_pc(url, shop_id, item_id):
            print(f"\nMatched get_pc status={evt.response.status}")
            print(f"URL: {url}")
            xhr_hits.append([url, evt.request_id])

    page.add_handler(mycdp.network.ResponseReceived, handler)


async def fetch_bodies(page, hits):
    out = []
    for url, request_id in hits:
        try:
            res = await page.send(mycdp.network.get_response_body(request_id))
            if res is None:
                continue
            out.append({"url": url, "body": res[0], "is_base64": res[1]})
        except Exception as e:
            print(f"Error getting response body: {e}")
    return out


def click_english(sb, timeout=15):
    print("Looking for English dialog...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            sb.cdp.click('button.shopee-button-outline.vsIIDR')
            print("Clicked English button")
            sb.sleep(1)
            return True
        except Exception:
            pass
        try:
            sb.cdp.click('button:contains("English")')
            print("Clicked English (text)")
            sb.sleep(1)
            return True
        except Exception:
            pass
        sb.sleep(0.5)
    print("English button not found")
    return False


def main():
    shop_id, item_id = parse_product_ids(PRODUCT_URL)
    print(f"Product: {PRODUCT_URL}")
    print(f"shop_id={shop_id} item_id={item_id}")
    print(f"proxy={PROXY or 'none'}")

    sb_kwargs = {
        "uc": True,
        "test": True,
        "locale_code": "en",
        "headed": not HEADLESS,
    }
    if PROXY:
        sb_kwargs["proxy"] = PROXY

    with SB(**sb_kwargs) as sb:
        print("Activating CDP mode...")
        sb.activate_cdp_mode("about:blank")
        tab = sb.cdp.page
        listen_get_pc(tab, shop_id, item_id)

        print("Opening product page...")
        sb.cdp.open(PRODUCT_URL)
        sb.sleep(3)

        click_english(sb)

        print("Reloading to capture get_pc...")
        xhr_hits.clear()
        sb.cdp.open(PRODUCT_URL)

        start = time.time()
        while time.time() - start < TIMEOUT_SEC:
            if xhr_hits:
                sb.sleep(1)  # let body settle
                loop = sb.get_event_loop()
                bodies = loop.run_until_complete(fetch_bodies(tab, list(xhr_hits)))
                for item in bodies:
                    raw = item["body"]
                    try:
                        data = json.loads(raw)
                    except Exception:
                        print("Non-JSON body:", str(raw)[:500])
                        continue

                    if is_valid_pdp(data):
                        print("\nVALID get_pc (data.item.item_id present)")
                        print(f"item_id: {data['data']['item']['item_id']}")
                        print(f"title: {data['data']['item'].get('title', '')[:80]}")
                        print(json.dumps(data, indent=2, ensure_ascii=False)[:8000])
                        return

                    print("INVALID get_pc (missing data.item.item_id):")
                    print(json.dumps(data, ensure_ascii=False)[:500])
                    return

            print(f"  waiting for get_pc... {int(time.time() - start)}s")
            sb.sleep(1)

        print("TIMEOUT: get_pc not seen")
        try:
            print(f"URL: {sb.cdp.get_current_url()}")
        except Exception:
            pass


if __name__ == "__main__":
    main()
