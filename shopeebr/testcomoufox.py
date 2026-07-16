"""
Playwright -> Camoufox -> Shopee

Opens a Shopee product page in Camoufox and captures internal API JSON
responses instead of copying headers/cookies manually (like test2.py).
"""

import json
import os
import random
import string
from pathlib import Path
from urllib.parse import urlparse

from camoufox.sync_api import Camoufox

# Same product as test2.py / test1.py
SHOP_ID = "421581203"
ITEM_ID = "23598287287"
PRODUCT_URL = f"https://shopee.com.br/product/{SHOP_ID}/{ITEM_ID}"

OUTPUT_DIR = Path(__file__).resolve().parent / "output"

# APIs we care about from test1.py and test2.py
API_HINTS = (
    "bundle_deal/items",
    "hot_sales/get_item_cards",
    "pdp/get_pc",
    "pdp/get",
)


def slug_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/").replace("/", "_")
    return path[:100] or "response"


def get_proxy_by_country(country: str, session_id: str | None = None) -> dict[str, str]:
    if not session_id:
        session_id = "".join(
            random.choice(string.ascii_lowercase + string.digits) for _ in range(5)
        )
    proxy = (
        f"http://lum-customer-hl_1df5a062-zone-static-country-{country}"
        f"-session-{session_id}:5u8xqhj4sa8c@zproxy.lum-superproxy.io:22225"
    )
    return {"http": proxy, "https": proxy}


def build_camoufox_proxy() -> dict | None:
    if os.environ.get("USE_PROXY", "0") != "1":
        return None
    proxies = None
    proxy_url = proxies["http"]
    # http://user:pass@host:port
    creds_host = proxy_url.removeprefix("http://")
    user_pass, host_port = creds_host.rsplit("@", 1)
    username, password = user_pass.split(":", 1)
    return {
        "server": f"http://{host_port}",
        "username": username,
        "password": password,
    }


def dismiss_language_modal(page, language: str = "English") -> bool:
    """Close Shopee BR language picker: 'Selecione seu idioma'."""
    try:
        page.get_by_text("Selecione seu idioma").wait_for(state="visible", timeout=4000)
    except Exception:
        return False

    selectors = [
        page.get_by_role("button", name=language),
        page.get_by_text(language, exact=False),
        page.get_by_text("Português (BR)", exact=False),
    ]
    for locator in selectors:
        try:
            if locator.count() > 0:
                locator.first.click(timeout=5000)
                page.wait_for_timeout(1500)
                print(f"Dismissed language modal -> {language}")
                return True
        except Exception:
            continue

    print("Language modal visible but could not click a button")
    return False


def prepare_shopee_context(browser):
    context = browser.new_context(locale="pt-BR")
    context.add_cookies(
        [
            {
                "name": "language",
                "value": "en",
                "domain": ".shopee.com.br",
                "path": "/",
            }
        ]
    )
    return context


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    captured: list[dict] = []

    print(f"Opening: {PRODUCT_URL}")

    proxy = build_camoufox_proxy()
    if proxy:
        print(f"Using BR proxy: {proxy['server']}")

    with Camoufox(
        headless=os.environ.get("CAMOUFOX_HEADLESS", "false").lower() == "true",
        locale="pt-BR",
        geoip=True,
        proxy=proxy,
    ) as browser:
        context = prepare_shopee_context(browser)
        page = context.new_page()
        language = os.environ.get("SHOPEE_LANGUAGE", "English")

        def on_response(response) -> None:
            url = response.url
            if "shopee.com.br/api/" not in url:
                return
            if response.status != 200:
                return
            if not any(hint in url for hint in API_HINTS):
                return
            try:
                body = response.json()
            except Exception:
                return
            captured.append({"url": url, "data": body})
            if body.get("error") or body.get("data") is None:
                print(f"Captured (check errors): {url}")
            else:
                print(f"Captured: {url}")

        page.on("response", on_response)

        page.goto(PRODUCT_URL, wait_until="domcontentloaded", timeout=90000)
        dismiss_language_modal(page, language=language)
        page.wait_for_timeout(3000)
        dismiss_language_modal(page, language=language)
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(3000)

        title = page.title()
        print(f"Page title: {title!r}")
        print(f"Captured {len(captured)} matching API response(s)")

        summary = {
            "product_url": PRODUCT_URL,
            "page_title": title,
            "captured_count": len(captured),
            "captured_urls": [item["url"] for item in captured],
        }
        summary_path = OUTPUT_DIR / f"{SHOP_ID}_{ITEM_ID}_camoufox_summary.json"
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Saved summary -> {summary_path}")

        for i, item in enumerate(captured):
            out = OUTPUT_DIR / f"{SHOP_ID}_{ITEM_ID}_camoufox_{i}_{slug_from_url(item['url'])}.json"
            out.write_text(
                json.dumps(item["data"], ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"Saved API JSON -> {out}")

        if not captured:
            print(
                "No target APIs captured yet. Shopee may need more load time, "
                "or the page showed a block/captcha. Try headless=False."
            )


if __name__ == "__main__":
    main()
