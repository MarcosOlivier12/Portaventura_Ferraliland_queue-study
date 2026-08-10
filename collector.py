import os
import requests
import json

API_KEY = os.environ["PARK_QUEUE_TIMES_API_KEY"]

url = "https://api.parkqueuetimes.com/v1/parks"

headers = {
    "x-api-key": API_KEY,
    "User-Agent": "PortAventura-Queue-Study/1.0",
}

response = requests.get(url, headers=headers, timeout=30)

print("STATUS:", response.status_code)
print("RESPONSE:")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
