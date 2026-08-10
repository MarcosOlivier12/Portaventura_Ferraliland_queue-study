import os
import requests

API_KEY = os.environ["PARK_QUEUE_TIMES_API_KEY"]

PARK_ID = 87

URL = f"https://api.parkqueuetimes.com/v1/parks/{PARK_ID}/live"

HEADERS = {
    "x-api-key": API_KEY,
    "User-Agent": "PortAventura-Queue-Study/1.0",
}

TARGETS = [
    "Uncharted",
    "Street Mission",
    "Shambhala",
    "Dragon Khan",
    "Furius Baco",
    "Hurakan Condor",
    "Stampida",
    "Tutuki Splash",
    "El Diablo",
    "Silver River Flume",
    "Templo del Fuego",
    "Red Force",
    "Thrill Towers",
    "Flying Dreams",
]

response = requests.get(URL, headers=HEADERS, timeout=30)
response.raise_for_status()

rides = response.json()["data"]["rides"]

print("RESULTADO DE LAS 14 ATRACCIONES")
print("================================")

for target in TARGETS:

    matches = [
        ride for ride in rides
        if target.lower() in ride["name"].lower()
        or ride["name"].lower() in target.lower()
    ]

    if matches:
        for ride in matches:
            print(
                f"{target} -> "
                f"NOMBRE API: {ride['name']} | "
                f"ID: {ride['id']} | "
                f"ESTADO: {ride['status']} | "
                f"COLA: {ride['waitMinutes']}"
            )
    else:
        print(f"{target} -> NO ENCONTRADA")
