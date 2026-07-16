import json

import requests

API_TOKEN = ""

url = "https://api.scrapeless.com/api/v1/scraper/request"

headers = {
    "x-api-token": API_TOKEN,
    "Content-Type": "application/json",
}

payload = {
    "actor": "scraper.shopee.search",
    "input": {
        # "url": "https://shopee.com.my/api/v4/search/search_items?by=relevancy&keyword=computer&limit=30&order=desc&page=1&page_type=search",
        "url": "https://shopee.co.th/api/v4/search/search_items?by=sales&keyword=baby%20pants&limit=30&newest=0&order=desc&page_type=search"

    },
}

response = requests.post(url, headers=headers, json=payload)
data = response.json()

with open("results_scrapeless.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Saved response to results_scrapeless.json")
