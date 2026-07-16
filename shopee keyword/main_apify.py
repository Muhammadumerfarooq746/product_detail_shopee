import json

from apify_client import ApifyClient

# Initialize the ApifyClient with your API token
client = ApifyClient("")

# Prepare the Actor input
run_input = {
    "location": "tênis",
    "keywords": ["iphone"],
    "shopUrls": [],
    "categoryUrls": [],
    "priceSlicing": False,
    "country": "ID",
    "maxItems": 40,
    "debug": False,
}

# Run the Actor and wait for it to finish
run = client.actor("fmKWN5uByUCIy2Sam").call(run_input=run_input)

# Fetch Actor results and save to JSON
items = list(client.dataset(run.default_dataset_id).iterate_items())

with open("results_apify.json", "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

print(f"Saved {len(items)} items to results_apify.json")