import json
import requests

url = "http://api.tmapi.top/shopee/item_detail"

querystring = {"apiToken":"",
"site":"sg",
"item_id":448475661,
"shop_id":29969299771,
}

response = requests.request("get", url, params=querystring)
data = response.json()
print(data)
with open("results.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Saved {len(data.get('data', {}).get('items', []))} items to results.json")