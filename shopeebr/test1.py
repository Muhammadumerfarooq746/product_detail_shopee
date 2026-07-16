import requests

url = "https://shopee.com.br/api/v4/pdp/hot_sales/get_item_cards"

querystring = {
    "item_id": "23598287287",
    "limit": "8",
    "offset": "0",
    "shop_id": "421581203"
}

headers = {
    "Host": "shopee.com.br",
    "Connection": "keep-alive",
    "sec-ch-ua-platform": "\"macOS\"",
    "sec-ch-ua": "\"Not;A=Brand\";v=\"8\", \"Chromium\";v=\"150\", \"Google Chrome\";v=\"150\"",
    "sec-ch-ua-mobile": "?0",
    "X-API-SOURCE": "pc",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "af-ac-enc-dat": "427f62507a2695c8",
    "X-CSRFToken": "Peu7LMqdO1AIiW0hMszweb9Sxys6nH8I",
    "af-ac-enc-sz-token": "OjP7Vq4L9k65lCPnVhBviQ==|7YxkqM2f0qoLQACBA46UpL/0TCAHMwcagl31cH4k/W4f9tAAdBfDJYC2Ln/YXiwkbDWWW3C56UkMiKY=|0bqam2RAGwAqyuDu|08|3",
    "x-sap-ri": "4d99586a66a1b00aa961583a0b017e45b124776c9bd9ddb6f7fe",
    "sz-token": "OjP7Vq4L9k65lCPnVhBviQ==|7YxkqM2f0qoLQACBA46UpL/0TCAHMwcagl31cH4k/W4f9tAAdBfDJYC2Ln/YXiwkbDWWW3C56UkMiKY=|0bqam2RAGwAqyuDu|08|3",
    "x-sz-sdk-version": "1.12.40",
    "X-Shopee-Language": "en",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "x-sap-sec": "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",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://shopee.com.br/product/421581203/23598287287",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "_sapid=a9e689c5eb7fd1afacbb45c7611e199c58f6c23902a6fc339bca21ff; csrftoken=Peu7LMqdO1AIiW0hMszweb9Sxys6nH8I; ssr-tz=Asia/Karachi; _QPWSDCXHZQA=7236b97b-9846-4873-e93d-323236560715; REC7iLP4Q=a00f268d-84fa-4f58-a465-6d7f736d560e; SPC_T_IV=ajdBdk9aSzJ3YzFTc0lyWg==; SPC_F=c9Twooep3I4cuR82uD40VXFN7QYf395y; REC_T_ID=2a06d47b-80f2-11f1-9ff5-0e629996f788; SPC_R_T_ID=Cp53a5SzUiDJZFsRCcY9DVyKCOOVxYjFtJxeI68QZE/SM/TufbvpYkAFQuWCK7ZKw6Rd9CyDJopNgi2ZRu4csPAXVw1nEbZFMKPVqEFQgl9toCrZLt8NdcuIQTwWZGX0twtXTl5PZQeFzaNTRSCezDvRvE/Tlv0xrD3C5pZbPBo=; SPC_R_T_IV=ajdBdk9aSzJ3YzFTc0lyWg==; SPC_T_ID=Cp53a5SzUiDJZFsRCcY9DVyKCOOVxYjFtJxeI68QZE/SM/TufbvpYkAFQuWCK7ZKw6Rd9CyDJopNgi2ZRu4csPAXVw1nEbZFMKPVqEFQgl9toCrZLt8NdcuIQTwWZGX0twtXTl5PZQeFzaNTRSCezDvRvE/Tlv0xrD3C5pZbPBo=; SPC_SI=V6EragAAAABheVAxcWRSMG0bFQMAAAAAbGNtVkJINHo=; SPC_SEC_SI=v1-QXpiajh0VG83VHBERjBKTh5IRvYQcu7vhjD3v/XLo4wSXMCr0PR/kcZQ/j9esgImj34vAQ2FF75N0Jzu9QOo0REmMHaJCf9cNw4cStwlMqU=; language=en; sense_sa_r=s; shopee_webUnique_ccd=OjP7Vq4L9k65lCPnVhBviQ%3D%3D%7C7YxkqM2f0qoLQACBA46UpL%2F0TCAHMwcagl31cH4k%2FW4f9tAAdBfDJYC2Ln%2FYXiwkbDWWW3C56UkMiKY%3D%7C0bqam2RAGwAqyuDu%7C08%7C3; ds=4b2fdd792b0605bfede8da86ad485583"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.text)