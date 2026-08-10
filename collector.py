import csv
import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

API_KEY = os.environ["PARK_QUEUE_TIMES_API_KEY"]
BASE_URL = "https://api.parkqueuetimes.com/v1"

TIMEZONE = ZoneInfo("Europe/Madrid")

PARKS = {
    "PortAventura": "PortAventura Park",
    "FerrariLand": "Ferrari Land",
}

TARGET_RIDES = {
    "PortAventura": {
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
    },
    "FerrariLand": {
        "Red Force",
        "Thrill Towers",
        "Flying Dreams",
    },
}

HEADERS = {
    "x-api-key": API_KEY,
    "User-Agent": "PortAventura-Queue-Study/1.0",
}

DATA_DIR = "data"
CSV_FILE = os.path.join(DATA_DIR, "queue_history.csv")

os.makedirs(DATA_DIR, exist_ok=True)


def api_get(endpoint):
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    result = response.json()

    if not result.get("success"):
        raise RuntimeError(result.get("error", "API error"))

    return result["data"]


def get_parks():
    return api_get("/parks")


def find_park_id(parks, wanted_name):
    wanted = wanted_name.lower()

    for park in parks:
        name = park["name"].lower()
        slug = park["slug"].lower()

        if wanted in name or wanted in slug:
            return park["id"]

    raise RuntimeError(f"No se encontró el parque: {wanted_name}")


def collect_park(park_name, park_id):
    now = datetime.now(TIMEZONE)

    live = api_get(f"/parks/{park_id}/live")
    park_info = api_get(f"/parks/{park_id}")
    calendar = api_get(f"/parks/{park_id}/calendar")

    hours = park_info.get("hours") or {}

    today = now.date().isoformat()

    crowd_percent = None

    for day in calendar.get("days", []):
        if day.get("date") == today:
            crowd_percent = day.get("crowdPercent")
            break

    target_names = TARGET_RIDES[park_name]

    rides_by_normalized_name = {
        ride["name"].strip().lower(): ride
        for ride in live.get("rides", [])
    }

    rows = []

    for target_name in target_names:
        ride = rides_by_normalized_name.get(target_name.lower())

        # Si el nombre de la API cambia ligeramente,
        # buscamos coincidencia parcial.
        if ride is None:
            for api_name, candidate in rides_by_normalized_name.items():
                if target_name.lower() in api_name or api_name in target_name.lower():
                    ride = candidate
                    break

        if ride is None:
            rows.append({
                "timestamp": now.isoformat(),
                "park": park_name,
                "ride_requested": target_name,
                "ride_api_name": "",
                "ride_id": "",
                "status": "NOT_FOUND",
                "wait_minutes": "",
                "ride_last_updated": "",
                "park_opening": hours.get("openingTime", ""),
                "park_closing": hours.get("closingTime", ""),
                "crowd_percent": crowd_percent,
            })
            continue

        rows.append({
            "timestamp": now.isoformat(),
            "park": park_name,
            "ride_requested": target_name,
            "ride_api_name": ride.get("name", ""),
            "ride_id": ride.get("id", ""),
            "status": ride.get("status", ""),
            "wait_minutes": ride.get("waitMinutes"),
            "ride_last_updated": ride.get("lastUpdated", ""),
            "park_opening": hours.get("openingTime", ""),
            "park_closing": hours.get("closingTime", ""),
            "crowd_percent": crowd_percent,
        })

    return rows


def append_rows(rows):
    fieldnames = [
        "timestamp",
        "park",
        "ride_requested",
        "ride_api_name",
        "ride_id",
        "status",
        "wait_minutes",
        "ride_last_updated",
        "park_opening",
        "park_closing",
        "crowd_percent",
    ]

    file_exists = os.path.exists(CSV_FILE)

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerows(rows)


def main():
    print("Iniciando recopilación...")

    parks = get_parks()

    all_rows = []

    for park_name, search_name in PARKS.items():
        try:
            park_id = find_park_id(parks, search_name)

            print(
                f"{park_name}: encontrado con ID {park_id}"
            )

            rows = collect_park(park_name, park_id)

            all_rows.extend(rows)

            for row in rows:
                print(
                    park_name,
                    "|",
                    row["ride_requested"],
                    "|",
                    row["status"],
                    "|",
                    row["wait_minutes"],
                    "min"
                )

        except Exception as e:
            print(f"ERROR en {park_name}: {e}")

    append_rows(all_rows)

    print(
        f"Recopilación terminada. "
        f"{len(all_rows)} registros guardados."
    )


if __name__ == "__main__":
    main()
