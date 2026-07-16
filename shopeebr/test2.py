import random
import requests
import string
def get_proxy_by_country(country: str, session_id: str = None):
    if not session_id:
        session_id = ''.join(random.choice(
            string.ascii_lowercase + string.digits) for _ in range(5))
    return {
        'http': f"http://lum-customer-hl_1df5a062-zone-static-country-{country}-session-{session_id}:5u8xqhj4sa8c@zproxy.lum-superproxy.io:22225",
        'https': f"http://lum-customer-hl_1df5a062-zone-static-country-{country}-session-{session_id}:5u8xqhj4sa8c@zproxy.lum-superproxy.io:22225"
    }
url = "https://shopee.com.br/api/v2/bundle_deal/items/"

querystring = {
    "anchor_item": "23598287287",
    "bundle_deal_id": "449638301905123",
    "from_item": "23598287287",
    "item_card_sdk_version": "3",
    "limit": "7",
    "need_recommended_items": "true",
    "offset": "0",
    "page_scenario": "3",
    "page_source": "1"
}

headers = {
    "Host": "shopee.com.br",
    "Connection": "keep-alive",
    "sec-ch-ua-platform": "\"macOS\"",
    "af-ac-enc-dat": "a63d27bbf0166ec5",
    "x-sap-ri": "359d586a1ac1861cd565b13a0b0140e200840fcd0289e099083d",
    "af-ac-enc-sz-token": "nwj3ekY4QH9G4tAAEyaH6g==|eA0pPmCPCHf0Yaeig0+SmqoQJ/buJs+gLJC602gvLSuHr+HcYqKHbXN4ELTQiZz2rwfwIQua7cTrLco=|0OCGptrZ4U810M9R|08|3",
    "If-None-Match-": "55b03-0e1cb02c5a8c04f8595915a9fbc26300",
    "sec-ch-ua": "\"Not;A=Brand\";v=\"8\", \"Chromium\";v=\"150\", \"Google Chrome\";v=\"150\"",
    "sec-ch-ua-mobile": "?0",
    "X-API-SOURCE": "pc",
    "x-sz-sdk-version": "1.12.40",
    "X-Requested-With": "XMLHttpRequest",
    "X-Shopee-Language": "en",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "x-sap-sec": "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",
    "Accept": "*/*",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://shopee.com.br/product/421581203/23598287287",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "_sapid=a8cd907b8150c811ad905c79f851a7d76a8fd1ed01dd45c0770e4657; csrftoken=lCSGXCnWgu2eSytcCCpRWsJqnqO9QTwL; ssr-tz=Asia/Karachi; _QPWSDCXHZQA=f7f29546-69a4-45bf-857e-3ed8734504ff; REC7iLP4Q=10b15584-21ab-42aa-b289-729d0a05c05c; REC_T_ID=7cf21298-80f4-11f1-a2b9-4a1fd0149e81; SPC_R_T_ID=kOXmjn2TjT07GkNzkBvV8tgepsVnSgxutvxlQ7NAwFzScRGjwI6vMBxUNUMyd5l+qvSoGfbXolaeZQAHNiZBHv3V4tmVXlyOklkLhY+k9lbuZq/fnv2xbv4LlqMcSPQkM1XnIpLwzeOSn2ePFtiN8j6E5TxCh+SqbBSsStL4s3A=; SPC_R_T_IV=RW9COGdkcnExalBGdkVoYw==; SPC_T_ID=kOXmjn2TjT07GkNzkBvV8tgepsVnSgxutvxlQ7NAwFzScRGjwI6vMBxUNUMyd5l+qvSoGfbXolaeZQAHNiZBHv3V4tmVXlyOklkLhY+k9lbuZq/fnv2xbv4LlqMcSPQkM1XnIpLwzeOSn2ePFtiN8j6E5TxCh+SqbBSsStL4s3A=; SPC_T_IV=RW9COGdkcnExalBGdkVoYw==; SPC_SI=cXYnagAAAABhUkQyYndhSyriXwUAAAAAcktYQjd5RVE=; SPC_SEC_SI=v1-bXZxZjUyYUIwYk9DZWhkUp0GHA1GQtPsLwRcqS2o606EaRI6rfPRbFHRwWqWWh46Ys3b4I5N7PouidcAzQ4WlH8hQRZ72vVEvl9zv3jJzGg=; SPC_F=zEU640291fQGmH1sTJqiGzN0IpcSn40O; language=en; sense_sa_r=s; shopee_webUnique_ccd=nwj3ekY4QH9G4tAAEyaH6g%3D%3D%7CeA0pPmCPCHf0Yaeig0%2BSmqoQJ%2FbuJs%2BgLJC602gvLSuHr%2BHcYqKHbXN4ELTQiZz2rwfwIQua7cTrLco%3D%7C0OCGptrZ4U810M9R%7C08%7C3; ds=0e8066192f12c5b9424acaf34c03a613"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())