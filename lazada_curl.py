"""
Python equivalent of the Lazada mtop getDetailInfo curl.
`t`, `sign`, and cookies must match a live browser session or the API may reject the request.
"""

import json
from pathlib import Path

import requests

BASE = "https://acs-m.lazada.com.ph/h5/mtop.global.detail.web.getdetailinfo/1.0/"

# Query string (must stay in sync with the signed request in the browser).
PARAMS = {
    "jsv": "2.6.1",
    "appKey": "24677475",
    "t": "1776416108257",
    "sign": "cd71ccc19ee758a0ddaa354742cee53f",
    "api": "mtop.global.detail.web.getDetailInfo",
    "v": "1.0",
    "type": "originaljson",
    "isSec": "1",
    "AntiCreep": "true",
    "timeout": "20000",
    "dataType": "json",
    "sessionOption": "AutoLoginOnly",
    "x-i18n-language": "en",
    "x-i18n-regionID": "PH",
    "appkey": "24677475",
}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)

PRODUCT_PATH = "https://www.lazada.com.ph/products/i272991001.html"
PRODUCT_URI = "i272991001"
PAGE_TS = "1776416104984"

# Same subset as in the curl’s cookieParams JSON (not necessarily full Cookie header).
COOKIE_PARAMS_INNER = {
    "hng": "PH|en-PH|PHP|608",
    "hng.sig": "4-ZnIK6EHRJcGqAJZ0_efm4MfSWbEqUs8J0oqlH1VNw",
    "t_fv": "1776416104422",
    "t_uid": "lZsKJE8uWafEQiozsUXECRWJ91pTyhgS",
    "t_sid": "vJQaMuCBpGOYuv4mg0UQx6vYWgzT8S6v",
    "utm_channel": "NA",
    "lwrid": "AgGdmqaf%2FZUyQ952kjUQxe5uI4RM",
    "lzd_cid": "eec6f18d-4f32-485a-9afc-b824026c0697",
}

COOKIES = {
    "hng": "PH|en-PH|PHP|608",
    "hng.sig": "4-ZnIK6EHRJcGqAJZ0_efm4MfSWbEqUs8J0oqlH1VNw",
    "t_fv": "1776416104422",
    "t_uid": "lZsKJE8uWafEQiozsUXECRWJ91pTyhgS",
    "t_sid": "vJQaMuCBpGOYuv4mg0UQx6vYWgzT8S6v",
    "utm_channel": "NA",
    "lwrid": "AgGdmqaf%2FZUyQ952kjUQxe5uI4RM",
    "lzd_cid": "eec6f18d-4f32-485a-9afc-b824026c0697",
    "lzd_sid": "1cdefa99ecd2de7e30a2224c5af45ce4",
    "_tb_token_": "71667b3e3ee97",
    "_m_h5_tk": "2ae4096fd233bc70a44ddb890f7d52da_1776426188238",
    "_m_h5_tk_enc": "122c2be171ed54c22cdb3f42a76c8939",
}

HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://www.lazada.com.ph",
    "Referer": "https://www.lazada.com.ph/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": USER_AGENT,
    "entrance": "",
    "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    "sec-ch-ua-mobile": "?0",
    'sec-ch-ua-platform': '"macOS"',
    "traffic": "",
    "x-i18n-language": "en",
    "x-i18n-regionID": "PH",
    "x-ua": f"defaultUAFromHeader with @@{PRODUCT_PATH}@@{PAGE_TS}",
    "x-umidtoken": f"defaultToken1_um_not_loaded@@{PRODUCT_PATH}@@{PAGE_TS}",
}


def build_data_field() -> str:
    inner = {
        "deviceType": "pc",
        "path": PRODUCT_PATH,
        "uri": PRODUCT_URI,
        "headerParams": json.dumps({"user-agent": USER_AGENT}, separators=(",", ":")),
        "cookieParams": json.dumps(COOKIE_PARAMS_INNER, separators=(",", ":")),
        "requestParams": "{}",
    }
    return json.dumps(inner, separators=(",", ":"))


def main() -> None:
    form = {"data": build_data_field()}
    r = requests.post(
        BASE,
        params=PARAMS,
        data=form,
        headers=HEADERS,
        cookies=COOKIES,
        timeout=30,
    )
    r.raise_for_status()
    body = r.json()

    out = Path("output") / "lazada_curl_mtop_response.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"HTTP {r.status_code}, wrote {out}")


if __name__ == "__main__":
    main()
