"""Shared nodriver scraper for Shopee PDP APIs."""

from __future__ import annotations

import json
import os
import random
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import nodriver as uc
from nodriver import cdp

API_HINTS = (
    "hot_sales/get_item_cards",
    "pdp/get_pc",
)

REGION_DOMAINS: dict[str, str] = {
    "sg": "shopee.sg",
    "my": "shopee.com.my",
    "id": "shopee.co.id",
    "th": "shopee.co.th",
    "vn": "shopee.vn",
    "ph": "shopee.ph",
    "tw": "shopee.tw",
    "br": "shopee.com.br",
}


def get_proxy_by_country(country: str, session_id: str | None = None) -> dict[str, str]:
    """Build Luminati proxy URL from env credentials."""
    if not session_id:
        session_id = "".join(
            random.choice(string.ascii_lowercase + string.digits) for _ in range(5)
        )
    country = country.lower()
    user = os.environ.get("LUMINATI_USER", "")
    password = os.environ.get("LUMINATI_PASSWORD", "")
    host = os.environ.get("LUMINATI_HOST", "zproxy.lum-superproxy.io")
    port = os.environ.get("LUMINATI_PORT", "22225")
    if not user or not password:
        raise RuntimeError(
            "USE_PROXY requires LUMINATI_USER and LUMINATI_PASSWORD env vars"
        )
    # user may already include zone/country template; if plain, append country-session
    if "country-" not in user:
        user = f"{user}-country-{country}-session-{session_id}"
    else:
        user = user.replace("{country}", country).replace("{session}", session_id)
    proxy = f"http://{user}:{password}@{host}:{port}"
    return {"http": proxy, "https": proxy}


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


def pick_api_payload(captured: list[dict], hint: str) -> dict | None:
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
    pdp = pick_api_payload(captured, "pdp/get_pc")
    if not isinstance(pdp, dict) or not pdp:
        return False
    if pdp.get("error") and pdp.get("data") is None:
        return False
    keys = set(str(k) for k in pdp.keys())
    if keys <= {"0", "1", "2", "3", "5", "9", "error"}:
        return False
    return True


@dataclass
class ScrapeResult:
    ok: bool
    payload: dict[str, Any] | None = None
    error: str = ""
    json_path: Path | None = None


class BaseShopeeScraper:
    """Region scrapers subclass this and set `region` / optional overrides."""

    region: str = ""
    domain: str = ""
    preferred_language: str = "English*"

    def __init__(
        self,
        *,
        output_dir: Path,
        chrome_path: str,
        headless: bool = False,
        max_attempts: int = 3,
        use_proxy: bool = False,
        language: str | None = None,
    ) -> None:
        if not self.region:
            raise ValueError("region must be set on scraper subclass")
        self.region = self.region.upper()
        self.domain = self.domain or REGION_DOMAINS[self.region.lower()]
        self.output_dir = Path(output_dir)
        self.chrome_path = chrome_path
        self.headless = headless
        self.max_attempts = max_attempts
        self.use_proxy = use_proxy
        self.language = language or self.preferred_language

    def product_url(self, shop_id: str, item_id: str) -> str:
        return f"https://{self.domain}/product/{shop_id}/{item_id}"

    def output_path(self, item_id: str) -> Path:
        folder = self.output_dir / self.region
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{item_id}.json"

    async def dismiss_language_modal(self, tab, language: str | None = None) -> bool:
        language = language or self.language
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
                return True
            if clicked is None:
                return False
            await tab.sleep(1)
        return False

    async def install_interceptor(self, tab, interceptor_js: str) -> None:
        await tab.evaluate(interceptor_js)

    async def scrape_one(
        self,
        browser,
        shop_id: str,
        item_id: str,
        *,
        max_attempts: int | None = None,
    ) -> ScrapeResult:
        max_attempts = max_attempts or self.max_attempts
        interceptor_js = build_interceptor_js(self.domain)
        out_path = self.output_path(item_id)
        product_url = self.product_url(shop_id, item_id)

        tab = await browser.get("about:blank")
        await tab.send(cdp.page.enable())
        await tab.send(cdp.network.enable())
        await tab.send(
            cdp.network.set_cookie(
                name="language",
                value="en",
                url=f"https://{self.domain}/",
                domain=f".{self.domain}",
                path="/",
            )
        )
        await tab.send(
            cdp.page.add_script_to_evaluate_on_new_document(
                source=interceptor_js + "\n" + AUTO_LANGUAGE_JS,
                run_immediately=True,
            )
        )

        captured: list[dict] = []
        for attempt in range(1, max_attempts + 1):
            await tab.evaluate("window.__SHOPEE_API_CAPTURE__ = []")
            await tab.get(product_url)
            await tab.sleep(3)
            await self.install_interceptor(tab, interceptor_js)
            await self.dismiss_language_modal(tab)
            await tab.sleep(2)
            await self.dismiss_language_modal(tab)
            await tab.sleep(1)
            await self.dismiss_language_modal(tab)
            await tab.sleep(5)

            raw = await tab.evaluate("JSON.stringify(window.__SHOPEE_API_CAPTURE__ || [])")
            captured = json.loads(raw) if raw else []
            if has_usable_data(captured):
                break
            if attempt < max_attempts:
                await tab.sleep(2)

        if not has_usable_data(captured):
            return ScrapeResult(
                ok=False,
                error=f"No usable pdp/get_pc after {max_attempts} attempts",
            )

        payload = {
            "region": self.region,
            "shop_id": shop_id,
            "item_id": item_id,
            "product_url": product_url,
            **build_combined_payload(captured),
        }
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return ScrapeResult(ok=True, payload=payload, json_path=out_path)

    async def run(self, shop_id: str, item_id: str) -> ScrapeResult:
        browser_args = ["--window-size=1400,900"]
        if self.use_proxy:
            proxy_url = get_proxy_by_country(self.region.lower())["http"]
            browser_args.append(f"--proxy-server={proxy_url}")

        browser = await uc.start(
            headless=self.headless,
            browser_executable_path=self.chrome_path,
            browser_args=browser_args,
        )
        try:
            return await self.scrape_one(browser, shop_id, item_id)
        finally:
            browser.stop()
