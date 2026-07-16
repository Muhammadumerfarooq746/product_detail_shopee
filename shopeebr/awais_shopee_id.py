"""
Open a Shopee product page with Botasaurus and capture /api/v4/pdp/get_pc response.

Valid response must have data.item.item_id. Retries with a fresh stealth profile.

  python test_s.py
  python test_s.py "https://shopee.co.id/product/451021432/23285088262"
"""

import json
import re
import sys
import time
import uuid
from urllib.parse import parse_qs, urlparse

from botasaurus.browser import browser, Driver

# ============ EDIT THESE ============
PRODUCT_URL = "https://shopee.co.id/product/451021432/23285088262"
# "ip" = host:port:user:pass   |  "luminati" = Bright Data sticky session
PROXY_MODE = "luminati"
PROXY_COUNTRY = "id"  # only used for luminati mode
HEADLESS = False
TIMEOUT_SEC = 60
MAX_RETRIES = 5  # new browser profile (+ new luminati session) each attempt
# ====================================

# IP proxy: host:port:user:pass
IP_PROXY_HOST = ""
IP_PROXY_PORT = ""
IP_PROXY_USER = ""
IP_PROXY_PASS = ""

# Luminati / Bright Data
LUM_USER = "lum-customer-hl_1df5a062-zone-static"
LUM_PASS = "5u8xqhj4sa8c"
LUM_HOST = "zproxy.lum-superproxy.io:22225"


def make_proxy(country: str, session_id: str) -> str:
    if PROXY_MODE == "luminati":
        user = f"{LUM_USER}-country-{country}-session-{session_id}"
        return f"http://{user}:{LUM_PASS}@{LUM_HOST}"
    # plain IP auth — do NOT append -country/-session (causes 407 / ERR_TUNNEL)
    return f"http://{IP_PROXY_USER}:{IP_PROXY_PASS}@{IP_PROXY_HOST}:{IP_PROXY_PORT}"


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


def is_valid_pdp_body(content) -> bool:
    """Good response = data.item.item_id present."""
    try:
        if isinstance(content, (bytes, bytearray)):
            content = content.decode("utf-8", errors="replace")
        data = json.loads(content) if isinstance(content, str) else content
        item_id = data.get("data", {}).get("item", {}).get("item_id")
        return item_id is not None
    except Exception:
        return False


def parse_json_body(content):
    if isinstance(content, (bytes, bytearray)):
        content = content.decode("utf-8", errors="replace")
    if isinstance(content, str):
        return json.loads(content)
    return content


def click_english_dialog(driver: Driver, timeout: int = 20) -> bool:
    print("Looking for English language dialog button...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            el = driver.select("button.shopee-button-outline.vsIIDR", wait=1)
            if el:
                print("Clicking: button.shopee-button-outline.vsIIDR")
                el.click()
                driver.sleep(1)
                return True
        except Exception:
            pass

        try:
            el = driver.get_element_with_exact_text("English", wait=1)
            if el:
                print("Clicking English button (text match)")
                el.click()
                driver.sleep(1)
                return True
        except Exception:
            pass

        driver.sleep(0.5)

    print("English button not found (maybe already dismissed)")
    return False


def get_profile(data):
    return data.get("profile") or f"shopee-{uuid.uuid4().hex[:12]}"


def get_proxy(data):
    return data.get("proxy") or None


@browser(
    headless=HEADLESS,
    proxy=get_proxy,
    profile=get_profile,
    tiny_profile=True,  # fresh lightweight profile each attempt
    remove_default_browser_check_argument=True,  # harder for bot detection
    wait_for_complete_page_load=False,
    close_on_crash=True,
    raise_exception=False,
    create_error_logs=False,
    output=None,
    reuse_driver=False,
)
def scrape_shopee_pdp(driver: Driver, data):
    product_url = data["product_url"]
    shop_id, item_id = parse_product_ids(product_url)
    attempt = data.get("attempt", 1)
    profile = driver.config.profile
    session_id = data.get("session_id", "?")

    print(f"\n>>> ATTEMPT {attempt}/{MAX_RETRIES}  profile={profile}")
    print(f"Proxy mode={PROXY_MODE}  session={session_id}")
    print(f"Product URL: {product_url}")
    print(f"shop_id={shop_id}  item_id={item_id}")

    print("Opening product page...")
    driver.get(product_url)
    driver.sleep(2)

    # Fail fast on proxy tunnel / chrome net errors
    try:
        page_url = driver.current_url or ""
        title = (driver.title or "").lower()
        html = (driver.page_html or "")[:2000].lower()
    except Exception:
        page_url, title, html = "", "", ""

    if (
        "ERR_TUNNEL" in html
        or "err_tunnel_connection_failed" in html
        or "err_proxy" in html
        or "this site can’t be reached" in html
        or "this site can't be reached" in html
        or "chrome-error://" in page_url
    ):
        print(f"PROXY/TUNNEL FAILED  url={page_url!r} title={title!r}")
        return {
            "ok": False,
            "valid": False,
            "shop_id": shop_id,
            "item_id": item_id,
            "error": "proxy_tunnel_failed",
        }

    click_english_dialog(driver)
    driver.sleep(1)

    print("Now watching for: /api/v4/pdp/get_pc?item_id=...&shop_id=...")
    matched = {"request_id": None, "url": None, "status": None}

    def after_response_handler(request_id, response, event):
        url = response.url
        if is_target_get_pc(url, shop_id, item_id):
            print(f"\nMatched get_pc: status={response.status}")
            print(f"URL: {url}")
            matched["request_id"] = request_id
            matched["url"] = url
            matched["status"] = response.status
            driver.responses.append(request_id)

    driver.after_response_received(after_response_handler)

    print("Reloading product page after language select...")
    driver.get(product_url)

    start = time.time()
    while time.time() - start < TIMEOUT_SEC:
        if matched["request_id"]:
            driver.sleep(0.5)
            bodies = driver.responses.collect()
            if not bodies:
                print("Matched request but no body yet, waiting...")
                driver.sleep(1)
                matched["request_id"] = None  # wait for next if body missing
                driver.responses.clear()
                continue

            body = bodies[0]
            content = body.get_decoded_content()

            if not is_valid_pdp_body(content):
                print("INVALID get_pc body (missing data.item.item_id) — will retry with new profile")
                try:
                    preview = content if isinstance(content, str) else str(content)
                    print(f"Body preview: {preview[:500]}")
                except Exception:
                    pass
                return {
                    "ok": False,
                    "valid": False,
                    "shop_id": shop_id,
                    "item_id": item_id,
                    "error": "missing data.item.item_id",
                    "status": matched["status"],
                    "url": matched["url"],
                }

            parsed = parse_json_body(content)
            print("\n" + "=" * 60)
            print("VALID GET_PC RESPONSE (data.item.item_id present)")
            print("=" * 60)
            print(f"STATUS: {matched['status']}")
            print(f"URL: {matched['url']}")
            print(f"item_id: {parsed['data']['item']['item_id']}")
            print(f"title: {parsed['data']['item'].get('title', '')[:80]}")
            print(json.dumps(parsed, indent=2, ensure_ascii=False)[:8000])
            print("=" * 60)
            return {
                "ok": True,
                "valid": True,
                "shop_id": shop_id,
                "item_id": item_id,
                "status": matched["status"],
                "url": matched["url"],
                "item": parsed["data"]["item"],
                "data": parsed,
            }

        print(f"  waiting for get_pc... {int(time.time() - start)}s")
        driver.sleep(1)

    print("FAILED: get_pc not seen within timeout")
    return {
        "ok": False,
        "valid": False,
        "shop_id": shop_id,
        "item_id": item_id,
        "error": "timeout",
    }


if __name__ == "__main__":
    product_url = sys.argv[1] if len(sys.argv) > 1 else PRODUCT_URL
    final = None

    for attempt in range(1, MAX_RETRIES + 1):
        profile = f"shopee-{uuid.uuid4().hex[:12]}"
        session_id = uuid.uuid4().hex[:16]
        proxy = make_proxy(PROXY_COUNTRY, session_id)

        print(
            f"\n{'=' * 60}\n"
            f"Starting attempt {attempt}/{MAX_RETRIES}\n"
            f"  profile={profile}\n"
            f"  proxy_mode={PROXY_MODE} session={session_id}\n"
            f"  proxy={proxy.split('@')[-1]}\n"
            f"{'=' * 60}"
        )

        result = scrape_shopee_pdp(
            {
                "product_url": product_url,
                "proxy": proxy,
                "profile": profile,
                "session_id": session_id,
                "attempt": attempt,
            }
        )

        if isinstance(result, dict) and result.get("ok") and result.get("valid"):
            final = result
            print(f"\nSUCCESS on attempt {attempt}")
            break

        print(f"\nAttempt {attempt} failed: {result}")
        if attempt < MAX_RETRIES:
            print("Retrying with new browser profile + new proxy session...")
            time.sleep(2)

    if not final:
        print(f"\nGAVE UP after {MAX_RETRIES} attempts")
        sys.exit(1)

    print("\nDone.")