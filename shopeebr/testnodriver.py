"""
nodriver + Chrome -> Shopee

Reads country,shop_id,item_id from url_shopee.txt.
Saves one JSON per product: output/{REGION}/{item_id}.json
with pdp get_pc + hot_sales only (no cookies/summary).
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import string
from pathlib import Path

import nodriver as uc
from nodriver import cdp


def get_proxy_by_country(country: str, session_id: str | None = None) -> dict[str, str]:
    if not session_id:
        session_id = "".join(
            random.choice(string.ascii_lowercase + string.digits) for _ in range(5)
        )
    country = country.lower()
    proxy = (
        f"http://lum-customer-hl_1df5a062-zone-static-country-{country}"
        f"-session-{session_id}:5u8xqhj4sa8c@zproxy.lum-superproxy.io:22225"
    )
    return {"http": proxy, "https": proxy}


ROOT = Path(__file__).resolve().parent
URL_FILE = ROOT / "url_shopee.txt"
OUTPUT_DIR = ROOT / "output"
SUCCESS_FILE = ROOT / "downloaded_ids.txt"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Only PDP detail + hot sales
API_HINTS = (
    "hot_sales/get_item_cards",
    "pdp/get_pc",
)

REGION_DOMAINS = {
    "sg": "shopee.sg",
    "my": "shopee.com.my",
    "id": "shopee.co.id",
    "th": "shopee.co.th",
    "vn": "shopee.vn",
    "ph": "shopee.ph",
    "tw": "shopee.tw",
    "br": "shopee.com.br",
}


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


def load_downloaded_ids(path: Path) -> set[str]:
    """Return set of 'country,shop_id,item_id' already downloaded."""
    if not path.is_file():
        return set()
    done: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.lower().startswith("country,"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 3:
            done.add(f"{parts[0].lower()},{parts[1]},{parts[2]}")
    return done


def mark_downloaded(path: Path, region: str, shop_id: str, item_id: str) -> None:
    """Append successful id to downloaded_ids.txt (same format as url_shopee.txt)."""
    key = f"{region.lower()},{shop_id},{item_id}"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        path.write_text("country,shop_id,item_id\n", encoding="utf-8")
    # avoid duplicates if file already has it
    existing = load_downloaded_ids(path)
    if key in existing:
        return
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{key}\n")
    print(f"Tracked success -> {key}")


def load_entries(path: Path) -> list[tuple[str, str, str, str]]:
    """
    Load url_shopee.txt rows as (region, shop_id, item_id, product_url).
    Format: country,shop_id,item_id
    """
    if not path.is_file():
        raise SystemExit(f"Missing URL file: {path}")

    entries: list[tuple[str, str, str, str]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 3:
            raise SystemExit(f"{path}:{line_no}: expected country,shop_id,item_id -> {line!r}")

        country, shop_id, item_id = parts
        # skip header
        if line_no == 1 and country.lower() == "country":
            continue

        country = country.lower()
        domain = REGION_DOMAINS.get(country)
        if not domain:
            raise SystemExit(f"{path}:{line_no}: unknown country {country!r}")
        if not shop_id.isdigit() or not item_id.isdigit():
            raise SystemExit(f"{path}:{line_no}: shop_id/item_id must be numeric -> {line!r}")

        region = country.upper()
        product_url = f"https://{domain}/product/{shop_id}/{item_id}"
        entries.append((region, shop_id, item_id, product_url))

    if not entries:
        raise SystemExit(f"No product rows found in {path}")
    return entries


def output_path_for(region: str, item_id: str) -> Path:
    """output/{REGION}/{item_id}.json"""
    folder = OUTPUT_DIR / region.upper()
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{item_id}.json"


def pick_api_payload(captured: list[dict], hint: str) -> dict | None:
    """Return latest matching API body for a URL hint."""
    chosen = None
    for item in captured:
        url = item.get("url") or ""
        data = item.get("data")
        if hint in url and isinstance(data, dict):
            chosen = data
    return chosen


def build_combined_payload(captured: list[dict]) -> dict:
    return {
        "pdp_get_pc": pick_api_payload(captured, "pdp/get_pc"),
        "pdp_hot_sales": pick_api_payload(captured, "hot_sales/get_item_cards"),
    }


def has_usable_data(captured: list[dict]) -> bool:
    """Need a real get_pc payload (not anti-bot error)."""
    pdp = pick_api_payload(captured, "pdp/get_pc")
    if not isinstance(pdp, dict) or not pdp:
        return False
    if pdp.get("error") and pdp.get("data") is None:
        return False
    keys = set(str(k) for k in pdp.keys())
    if keys <= {"0", "1", "2", "3", "5", "9", "error"}:
        return False
    return True


def summarize_capture(captured: list[dict]) -> str:
    """Short debug line for failed captures."""
    parts: list[str] = []
    for item in captured:
        url = str(item.get("url") or "")
        data = item.get("data")
        hint = next((h for h in API_HINTS if h in url), "other")
        err = None
        if isinstance(data, dict):
            err = data.get("error") or data.get("error_msg") or data.get("error_code")
        parts.append(f"{hint}:error={err!r}")
    return "; ".join(parts) if parts else "(empty)"


HOMEPAGE_TITLES = (
    "cheaper, faster on shopee",
    "shopee singapore",
    "shopee malaysia",
    "shopee indonesia",
    "shopee thailand",
    "shopee việt nam",
    "shopee philippines",
    "shopee 蝦皮購物",
    "shopee brasil",
)


def looks_like_homepage(title: str, href: str, item_id: str) -> bool:
    t = (title or "").lower()
    h = (href or "").lower()
    if "/verify/traffic" in h or "/verify/" in h:
        return True
    # Only treat as PDP if item_id is in the path (not only in ?next= query)
    path = h.split("?", 1)[0]
    if item_id and item_id in path:
        return False
    if "/product/" in path:
        return False
    if any(x in t for x in HOMEPAGE_TITLES) and "product" not in t:
        return True
    if path.rstrip("/").endswith((".sg", ".com.my", ".co.id", ".co.th", ".vn", ".ph", ".tw", ".com.br")):
        return True
    return False


def is_traffic_verify(href: str) -> bool:
    return "/verify/traffic" in (href or "").lower()


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


async def page_location(tab) -> tuple[str, str]:
    title = await tab.evaluate("document.title") or ""
    href = await tab.evaluate("location.href") or ""
    return str(title), str(href)


async def wait_for_pdp(tab, item_id: str, seconds: float = 12.0) -> bool:
    """Poll until URL/title look like a product page (not homepage/verify bounce)."""
    steps = max(1, int(seconds / 0.5))
    for _ in range(steps):
        title, href = await page_location(tab)
        if is_traffic_verify(href):
            await tab.sleep(0.5)
            continue
        if not looks_like_homepage(title, href, item_id):
            return True
        await tab.sleep(0.5)
    return False


async def wait_out_traffic_verify(tab, item_id: str, seconds: float = 20.0) -> bool:
    """Some Shopee traffic checks auto-redirect after a few seconds."""
    title, href = await page_location(tab)
    if not is_traffic_verify(href):
        return True
    print(f"Traffic verify page detected — waiting up to {seconds:.0f}s for redirect...")
    print(f"  {href}")
    steps = max(1, int(seconds / 1.0))
    for i in range(steps):
        await tab.sleep(1.0)
        title, href = await page_location(tab)
        if not is_traffic_verify(href):
            print(f"Left verify page after {i + 1}s -> {href}")
            return not looks_like_homepage(title, href, item_id)
    print("Still stuck on traffic verify (anti-bot).")
    return False


async def gentle_scroll(tab) -> None:
    await tab.evaluate(
        """
        (() => {
          window.scrollTo(0, 400);
          setTimeout(() => window.scrollTo(0, 900), 400);
          setTimeout(() => window.scrollTo(0, 0), 900);
        })()
        """
    )
    await tab.sleep(1.5)


async def scrape_one(
    browser,
    region: str,
    shop_id: str,
    item_id: str,
    product_url: str,
    language: str,
    max_attempts: int = 3,
) -> bool:
    domain = REGION_DOMAINS[region.lower()]
    home_url = f"https://{domain}/"
    # SEO-style fallback Shopee also accepts
    alt_url = f"https://{domain}/-i.{shop_id}.{item_id}"
    interceptor_js = build_interceptor_js(domain)
    out_path = output_path_for(region, item_id)

    print(f"Opening: {product_url}")
    print(f"region={region} shop_id={shop_id} item_id={item_id}")
    print(f"output -> {out_path}")

    tab = await browser.get("about:blank")
    await tab.send(cdp.page.enable())
    await tab.send(cdp.network.enable())
    await tab.send(
        cdp.network.set_cookie(
            name="language",
            value="en",
            url=home_url,
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

    # Warm up on homepage so the first product hit isn't a cold bot check
    print(f"Warm-up: {home_url}")
    await tab.get(home_url)
    await tab.sleep(3)
    await install_interceptor(tab, interceptor_js)
    await dismiss_language_modal(tab, language=language)
    await tab.sleep(2)

    captured: list[dict] = []
    urls_to_try = [product_url, alt_url]

    for attempt in range(1, max_attempts + 1):
        target = urls_to_try[(attempt - 1) % len(urls_to_try)]
        print(f"Attempt {attempt}/{max_attempts} -> {target}")
        await tab.evaluate("window.__SHOPEE_API_CAPTURE__ = []")

        print("Navigating to product...")
        await tab.get(target)
        await tab.sleep(4)
        await install_interceptor(tab, interceptor_js)
        await dismiss_language_modal(tab, language=language)
        await tab.sleep(2)
        await dismiss_language_modal(tab, language=language)

        title, href = await page_location(tab)
        if is_traffic_verify(href):
            await wait_out_traffic_verify(tab, item_id, seconds=25)

        ok_pdp = await wait_for_pdp(tab, item_id, seconds=10)
        title, href = await page_location(tab)
        print(f"Page title: {title!r}")
        print(f"Location: {href!r}")
        if is_traffic_verify(href):
            print("Blocked by Shopee /verify/traffic (anti-bot). Proxy or real Chrome profile needed.")
        elif not ok_pdp or looks_like_homepage(title, href, item_id):
            print("Still on homepage / bounced — retrying navigation once...")
            await tab.get(target)
            await tab.sleep(5)
            await install_interceptor(tab, interceptor_js)
            await dismiss_language_modal(tab, language=language)
            title, href = await page_location(tab)
            if is_traffic_verify(href):
                await wait_out_traffic_verify(tab, item_id, seconds=25)
            await wait_for_pdp(tab, item_id, seconds=10)
            title, href = await page_location(tab)
            print(f"Page title (retry): {title!r}")
            print(f"Location (retry): {href!r}")

        await gentle_scroll(tab)
        await tab.sleep(6)

        raw = await tab.evaluate("JSON.stringify(window.__SHOPEE_API_CAPTURE__ || [])")
        captured = json.loads(raw) if raw else []
        print(f"Captured {len(captured)} matching API response(s)")
        print(f"Capture summary: {summarize_capture(captured)}")

        if has_usable_data(captured):
            print(f"Got usable data on attempt {attempt}")
            break

        print(f"No usable data on attempt {attempt}/{max_attempts}")
        if attempt < max_attempts:
            await tab.sleep(3)
    else:
        print(f"Failed after {max_attempts} attempts for {product_url}")

    if not has_usable_data(captured):
        print(
            "No usable product data after retries — keeping any existing output file. "
            "Manual Chrome works because it has cookies/fingerprint; automated Chrome "
            "is often bounced to homepage or gets anti-bot get_pc. Try USE_PROXY=1."
        )
        return False

    payload = {
        "region": region.upper(),
        "shop_id": shop_id,
        "item_id": item_id,
        "product_url": product_url,
        **build_combined_payload(captured),
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved -> {out_path}")
    mark_downloaded(SUCCESS_FILE, region, shop_id, item_id)
    return True


async def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    language = os.environ.get("SHOPEE_LANGUAGE", "English*")
    headless = os.environ.get("HEADLESS", "false").lower() == "true"
    max_attempts = int(os.environ.get("MAX_ATTEMPTS", "3"))
    use_proxy = os.environ.get("USE_PROXY", "0") == "1"
    entries = load_entries(URL_FILE)
    already_done = load_downloaded_ids(SUCCESS_FILE)

    pending = []
    for e in entries:
        region, shop_id, item_id, product_url = e
        key = f"{region.lower()},{shop_id},{item_id}"
        out_path = output_path_for(region, item_id)
        if key in already_done or out_path.is_file():
            if key not in already_done and out_path.is_file():
                mark_downloaded(SUCCESS_FILE, region, shop_id, item_id)
                already_done.add(key)
            continue
        pending.append(e)

    limit = int(os.environ.get("LIMIT", "0") or "0")
    if limit > 0:
        pending = pending[:limit]

    print(f"Loaded {len(entries)} product(s) from {URL_FILE}")
    print(f"Already downloaded: {len(already_done)}")
    print(f"Remaining: {len(pending)}" + (f" (LIMIT={limit})" if limit else ""))
    print(f"Success log: {SUCCESS_FILE}")
    print(f"Chrome: {CHROME_PATH}")
    print(f"headless={headless} max_attempts={max_attempts} use_proxy={use_proxy}")

    if not pending:
        print("Nothing left to download.")
        return

    for idx, (region, shop_id, item_id, product_url) in enumerate(pending, start=1):
        print(f"\n=== [{idx}/{len(pending)}] {region} {shop_id}/{item_id} ===")
        browser_args = [
            "--window-size=1400,900",
            "--lang=en-US",
            "--disable-dev-shm-usage",
        ]
        if use_proxy:
            proxy_url = get_proxy_by_country(region.lower())["http"]
            browser_args.append(f"--proxy-server={proxy_url}")
            print(f"Using proxy country={region.lower()}")

        user_data_dir = os.environ.get("CHROME_USER_DATA_DIR", "").strip() or None
        start_kwargs: dict = {
            "headless": headless,
            "browser_executable_path": CHROME_PATH,
            "browser_args": browser_args,
        }
        if user_data_dir:
            start_kwargs["user_data_dir"] = user_data_dir
            print(f"Using Chrome profile: {user_data_dir}")

        browser = await uc.start(**start_kwargs)
        print("Chrome started")
        try:
            ok = await scrape_one(
                browser,
                region=region,
                shop_id=shop_id,
                item_id=item_id,
                product_url=product_url,
                language=language,
                max_attempts=max_attempts,
            )
            print(f"Result for [{region}] {item_id}: {'OK' if ok else 'FAILED'}")
        finally:
            browser.stop()
            print(
                "Browser closed — moving to next URL"
                if idx < len(pending)
                else "Browser closed"
            )
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
