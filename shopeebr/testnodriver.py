"""
nodriver + Chrome -> Shopee

Reads product URL(s) from url_shopee.txt, opens each in Chrome,
dismisses language modal, captures API JSON + cookies.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
from pathlib import Path
import string
from urllib.parse import urlparse

import nodriver as uc
from nodriver import cdp

def get_proxy_by_country(country: str, session_id: str = None):
    if not session_id:
        session_id = ''.join(random.choice(
            string.ascii_lowercase + string.digits) for _ in range(5))
    return {
        'http': f"http://lum-customer-hl_1df5a062-zone-static-country-{country}-session-{session_id}:5u8xqhj4sa8c@zproxy.lum-superproxy.io:22225",
        'https': f"http://lum-customer-hl_1df5a062-zone-static-country-{country}-session-{session_id}:5u8xqhj4sa8c@zproxy.lum-superproxy.io:22225"
    }
ROOT = Path(__file__).resolve().parent
URL_FILE = ROOT / "url_shopee.txt"
OUTPUT_DIR = ROOT / "output"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

API_HINTS = (
    "bundle_deal/items",
    "hot_sales/get_item_cards",
    "pdp/get_pc",
    "pdp/get",
)


def build_interceptor_js(domain: str) -> str:
    return r"""
(() => {
  if (window.__SHOPEE_API_CAPTURE__) return "already";
  window.__SHOPEE_API_CAPTURE__ = [];
  const hints = %HINTS%;
  const domain = %DOMAIN%;

  const interesting = (url) =>
    typeof url === "string" &&
    url.includes(domain + "/api/") &&
    hints.some((h) => url.includes(h));

  const push = async (url, response) => {
    try {
      const clone = response.clone();
      const text = await clone.text();
      let data;
      try { data = JSON.parse(text); } catch { data = { raw: text }; }
      window.__SHOPEE_API_CAPTURE__.push({ url, data, status: response.status });
    } catch (e) {}
  };

  const origFetch = window.fetch;
  window.fetch = async function(...args) {
    const response = await origFetch.apply(this, args);
    try {
      const url = typeof args[0] === "string" ? args[0] : (args[0] && args[0].url);
      if (interesting(url) && response.status === 200) push(url, response);
    } catch (e) {}
    return response;
  };

  const OrigXHR = window.XMLHttpRequest;
  function WrappedXHR() {
    const xhr = new OrigXHR();
    let reqUrl = "";
    const open = xhr.open;
    xhr.open = function(method, url, ...rest) {
      reqUrl = String(url || "");
      return open.call(this, method, url, ...rest);
    };
    xhr.addEventListener("load", function() {
      try {
        if (!interesting(reqUrl) || xhr.status !== 200) return;
        let data;
        try { data = JSON.parse(xhr.responseText); } catch { data = { raw: xhr.responseText }; }
        window.__SHOPEE_API_CAPTURE__.push({ url: reqUrl, data, status: xhr.status });
      } catch (e) {}
    });
    return xhr;
  }
  WrappedXHR.prototype = OrigXHR.prototype;
  window.XMLHttpRequest = WrappedXHR;
  return "installed";
})()
""".replace("%HINTS%", json.dumps(list(API_HINTS))).replace(
        "%DOMAIN%", json.dumps(domain)
    )


def slug_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/").replace("/", "_")
    return path[:100] or "response"


DOMAIN_TO_REGION = {
    "shopee.sg": "SG",
    "shopee.com.my": "MY",
    "shopee.co.id": "ID",
    "shopee.co.th": "TH",
    "shopee.vn": "VN",
    "shopee.ph": "PH",
    "shopee.tw": "TW",
    "shopee.com.br": "BR",
}


def region_from_domain(domain: str) -> str:
    return DOMAIN_TO_REGION.get(domain, domain.split(".")[-1].upper())


def load_entries(path: Path) -> list[tuple[str, str]]:
    """
    Load lines from url_shopee.txt.
    Supported:
      REGION,https://shopee.../product/shop/item
      https://shopee.../product/shop/item   (region inferred from domain)
    """
    if not path.is_file():
        raise SystemExit(f"Missing URL file: {path}")
    entries: list[tuple[str, str]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "," in line:
            region, product_url = line.split(",", 1)
            region = region.strip().upper()
            product_url = product_url.strip()
        else:
            product_url = line
            domain = urlparse(product_url).netloc.replace("www.", "")
            region = region_from_domain(domain)
        if not product_url.startswith("http"):
            raise SystemExit(f"{path}:{line_no}: invalid URL -> {line!r}")
        entries.append((region, product_url))
    if not entries:
        raise SystemExit(f"No URLs found in {path}")
    return entries


def parse_product_url(product_url: str) -> tuple[str, str, str]:
    """Return (domain, shop_id, item_id) from a Shopee product URL."""
    parsed = urlparse(product_url)
    domain = parsed.netloc.replace("www.", "")
    match = re.search(r"/product/(\d+)/(\d+)", parsed.path)
    if not match:
        match = re.search(r"\.(\d+)\.(\d+)/?$", parsed.path)
    if not match:
        raise ValueError(f"Could not parse shop_id/item_id from URL: {product_url}")
    shop_id, item_id = match.group(1), match.group(2)
    return domain, shop_id, item_id


def output_dir_for(region: str, shop_id: str) -> Path:
    """output/{REGION}/{shop_id}/"""
    path = OUTPUT_DIR / region.upper() / shop_id
    path.mkdir(parents=True, exist_ok=True)
    return path


AUTO_LANGUAGE_JS = r"""
(() => {
  const pick = () => {
    const titleHit = [...document.querySelectorAll("h1,h2,div,span,p")]
      .some(n => (n.textContent || "").includes("Selecione seu idioma"));
    if (!titleHit) return false;
    const preferred = ["English*", "English", "Português (BR)", "Portugues (BR)"];
    const nodes = [...document.querySelectorAll("button, a, [role='button'], div, span")];
    for (const label of preferred) {
      const el = nodes.find(n => {
        const t = (n.textContent || "").replace(/\s+/g, " ").trim();
        return t === label || t === label.replace("*", "") || t.startsWith(label.replace("*", ""));
      });
      if (!el) continue;
      const clickable = el.closest("button, a, [role='button']") || el;
      clickable.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
      clickable.click();
      return true;
    }
    return false;
  };
  pick();
  const obs = new MutationObserver(() => pick());
  obs.observe(document.documentElement, { childList: true, subtree: true });
  setTimeout(() => obs.disconnect(), 15000);
})();
"""


async def dismiss_language_modal(tab, language: str = "English") -> bool:
    """Close Shopee language picker if present."""
    for attempt in range(5):
        clicked = await tab.evaluate(
            f"""
            (() => {{
              const hasTitle = [...document.querySelectorAll("*")]
                .some(n => ((n.childElementCount === 0 ? n.textContent : "") || "")
                  .includes("Selecione seu idioma")
                  || ((n.textContent || "").includes("Selecione seu idioma")
                      && (n.textContent || "").length < 80));
              const bodyHas = (document.body && document.body.innerText || "")
                .includes("Selecione seu idioma");
              if (!hasTitle && !bodyHas) return null;

              const texts = {json.dumps([
                  language,
                  language + "*",
                  "English*",
                  "English",
                  "Português (BR)",
                  "Portugues (BR)",
              ])};
              const nodes = [...document.querySelectorAll("button, a, [role='button'], div, span")];
              for (const text of texts) {{
                const el = nodes.find(n => {{
                  const t = (n.textContent || "").replace(/\\s+/g, " ").trim();
                  const want = text.replace("*", "");
                  return t === text || t === want || t.startsWith(want);
                }});
                if (!el) continue;
                const clickable = el.closest("button, a, [role='button']") || el;
                clickable.dispatchEvent(new MouseEvent("click", {{
                  bubbles: true, cancelable: true, view: window
                }}));
                clickable.click();
                return (clickable.textContent || text).replace(/\\s+/g, " ").trim();
              }}
              return "modal-found-no-button";
            }})()
            """
        )
        if clicked and clicked != "modal-found-no-button":
            await tab.sleep(1.5)
            print(f"Dismissed language modal -> {clicked}")
            return True
        if clicked is None:
            return False
        await tab.sleep(1)
        print(f"Language modal still open (attempt {attempt + 1}/5)")

    print("Language modal visible but could not click a button")
    return False


async def install_interceptor(tab, interceptor_js: str) -> None:
    result = await tab.evaluate(interceptor_js)
    print(f"Interceptor: {result}")


def has_usable_data(captured: list[dict]) -> bool:
    """True if we got at least one API payload with real data (not anti-bot error)."""
    for item in captured:
        data = item.get("data")
        if not isinstance(data, dict) or not data:
            continue
        if data.get("error") and data.get("data") is None:
            continue
        # Reject pure anti-bot error blobs
        keys = set(str(k) for k in data.keys())
        if keys <= {"0", "1", "2", "3", "5", "9", "error"}:
            continue
        return True
    return False


async def scrape_one(
    browser,
    product_url: str,
    language: str,
    region: str,
    max_attempts: int = 3,
) -> bool:
    domain, shop_id, item_id = parse_product_url(product_url)
    region = (region or region_from_domain(domain)).upper()
    interceptor_js = build_interceptor_js(domain)
    out_dir = output_dir_for(region, shop_id)

    print(f"Opening: {product_url}")
    print(f"region={region} domain={domain} shop_id={shop_id} item_id={item_id}")
    print(f"output -> {out_dir}")

    tab = await browser.get("about:blank")
    await tab.send(cdp.page.enable())
    await tab.send(cdp.network.enable())
    await tab.send(
        cdp.network.set_cookie(
            name="language",
            value="en",
            url=f"https://{domain}/",
            domain=f".{domain}",
            path="/",
        )
    )
    await tab.send(
        cdp.page.add_script_to_evaluate_on_new_document(
            source=interceptor_js + "\n" + AUTO_LANGUAGE_JS,
            run_immediately=True,
        )
    )
    print("Interceptor + language auto-click registered")

    captured: list[dict] = []
    cookie_list: list[dict] = []
    title = ""
    used_attempts = 0

    for attempt in range(1, max_attempts + 1):
        used_attempts = attempt
        print(f"Attempt {attempt}/{max_attempts}")
        await tab.evaluate("window.__SHOPEE_API_CAPTURE__ = []")

        print("Navigating to product...")
        await tab.get(product_url)
        await tab.sleep(3)
        await install_interceptor(tab, interceptor_js)
        await dismiss_language_modal(tab, language=language)
        await tab.sleep(2)
        await dismiss_language_modal(tab, language=language)
        await tab.sleep(1)
        await dismiss_language_modal(tab, language=language)

        await tab.sleep(5)

        cookies = await browser.cookies.get_all()
        cookie_list = []
        for c in cookies:
            if hasattr(c, "to_json"):
                cookie_list.append(c.to_json())
            else:
                cookie_list.append(
                    {
                        "name": getattr(c, "name", None),
                        "value": getattr(c, "value", None),
                        "domain": getattr(c, "domain", None),
                        "path": getattr(c, "path", None),
                        "expires": getattr(c, "expires", None),
                        "secure": getattr(c, "secure", None),
                        "httpOnly": getattr(c, "http_only", None),
                        "sameSite": str(getattr(c, "same_site", "") or ""),
                    }
                )

        raw = await tab.evaluate("JSON.stringify(window.__SHOPEE_API_CAPTURE__ || [])")
        captured = json.loads(raw) if raw else []
        title = await tab.evaluate("document.title")
        print(f"Page title: {title!r}")
        print(f"Captured {len(captured)} matching API response(s)")

        if has_usable_data(captured):
            print(f"Got usable data on attempt {attempt}")
            break

        print(f"No usable data on attempt {attempt}/{max_attempts}")
        if attempt < max_attempts:
            await tab.sleep(2)
    else:
        print(f"Failed after {max_attempts} attempts for {product_url}")

    success = has_usable_data(captured)

    # Never overwrite good JSON with anti-bot / empty failure payloads.
    if not success:
        print(
            "No usable product data after retries — keeping any existing output files. "
            "Try without HEADLESS (visible Chrome)."
        )
        return False

    cookie_header = "; ".join(
        f"{c.get('name')}={c.get('value')}"
        for c in cookie_list
        if c.get("name") is not None
    )
    cookies_path = out_dir / f"{shop_id}_nodriver_cookies.json"
    cookies_path.write_text(
        json.dumps(
            {
                "region": region,
                "shop_id": shop_id,
                "item_id": item_id,
                "product_url": product_url,
                "cookie_header": cookie_header,
                "cookies": cookie_list,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved cookies ({len(cookie_list)}) -> {cookies_path}")

    summary = {
        "region": region,
        "shop_id": shop_id,
        "item_id": item_id,
        "product_url": product_url,
        "page_title": title,
        "captured_count": len(captured),
        "captured_urls": [item.get("url") for item in captured],
        "cookies_file": str(cookies_path.name),
        "cookie_count": len(cookie_list),
        "success": True,
        "attempts": used_attempts,
    }
    summary_path = out_dir / f"{shop_id}_nodriver_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved summary -> {summary_path}")

    for i, item in enumerate(captured):
        url = item.get("url", "")
        data = item.get("data")
        out = out_dir / f"{shop_id}_nodriver_{i}_{slug_from_url(url)}.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Captured: {url}")
        print(f"Saved API JSON -> {out}")

    return True


async def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    language = os.environ.get("SHOPEE_LANGUAGE", "English*")
    headless = os.environ.get("HEADLESS", "false").lower() == "true"
    max_attempts = int(os.environ.get("MAX_ATTEMPTS", "3"))
    entries = load_entries(URL_FILE)

    print(f"Loaded {len(entries)} URL(s) from {URL_FILE}")
    print(f"Chrome: {CHROME_PATH}")
    print(f"headless={headless} max_attempts={max_attempts}")

    for idx, (region, product_url) in enumerate(entries, start=1):
        print(f"\n=== [{idx}/{len(entries)}] {region} {product_url} ===")
        browser = await uc.start(
            headless=headless,
            browser_executable_path=CHROME_PATH,
            browser_args=[
                "--window-size=1400,900",
                f"--proxy-server={get_proxy_by_country(region)['http']}",
            ],
        )
        print("Chrome started")
        try:
            ok = await scrape_one(
                browser,
                product_url,
                language=language,
                region=region,
                max_attempts=max_attempts,
            )
            print(f"Result for [{region}] {product_url}: {'OK' if ok else 'FAILED'}")
        finally:
            browser.stop()
            print("Browser closed — moving to next URL" if idx < len(entries) else "Browser closed")
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
