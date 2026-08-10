import os
import requests
import json

API_KEY = os.environ["PARK_QUEUE_TIMES_API_KEY"]

PARK_ID = 87

url = f"https://api.parkqueuetimes.com/v1/parks/{PARK_ID}/live"

headers = {
    "x-api-key": API_KEY,
    "User-Agent": "PortAventura-Queue-Study/1.0",
}

response = requests.get(url, headers=headers, timeout=30)

print("STATUS:", response.status_code)
print("ATRACCIONES DE PORT AVENTURA WORLD:")
print("===================================")

data = response.json()

print(json.dumps(data, indent=2, ensure_ascii=False))
