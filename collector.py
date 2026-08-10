import csv
import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from statistics import mean, median

# ============================================================
# CONFIGURACIÓN
# ============================================================

API_KEY = os.environ["PARK_QUEUE_TIMES_API_KEY"]

PARK_ID = 87
BASE_URL = f"https://api.parkqueuetimes.com/v1/parks/{PARK_ID}"

MADRID_TZ = ZoneInfo("Europe/Madrid")
UTC_TZ = ZoneInfo("UTC")

CSV_FILE = "data/queue_history.csv"

HEADERS = {
    "x-api-key": API_KEY,
    "User-Agent": "PortAventura-Queue-Study/1.0",
}


# ============================================================
# ATRACCIONES DEFINITIVAS
# ============================================================

RIDES = [
    # PORTAVENTURA

    {"park": "PortAventura", "code": "UNCH", "name": "Uncharted", "id": 5614},
    {"park": "PortAventura", "code": "SM", "name": "Street Mission", "id": 5652},
    {"park": "PortAventura", "code": "SH", "name": "Shambhala", "id": 5603},
    {"park": "PortAventura", "code": "DK", "name": "Dragon Khan", "id": 5630},
    {"park": "PortAventura", "code": "FB", "name": "Furius Baco", "id": 5596},
    {"park": "PortAventura", "code": "HC", "name": "Hurakan Condor", "id": 5644},
    {"park": "PortAventura", "code": "STAM", "name": "Stampida", "id": 5608},
    {"park": "PortAventura", "code": "TK", "name": "Tutuki Splash", "id": 5649},
    {"park": "PortAventura", "code": "DB", "name": "El Diablo - Tren De La Mina", "id": 5645},
    {"park": "PortAventura", "code": "SVR", "name": "Silver River Flume", "id": 5646},
    {"park": "PortAventura", "code": "TF", "name": "Templo del Fuego", "id": 5591},

    # FERRARI LAND

    {"park": "Ferrari Land", "code": "RF", "name": "Red Force", "id": 5612},
    {"park": "Ferrari Land", "code": "TT", "name": "Thrill Towers", "id": 5590},
    {"park": "Ferrari Land", "code": "FLY", "name": "Flying Dreams", "id": 5611},
]


# ============================================================
# API
# ============================================================

def api_get(endpoint):

    url = f"{BASE_URL}{endpoint}"

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("success"):
        raise RuntimeError(
            result.get("error", "Error desconocido de la API")
        )

    return result["data"]


# ============================================================
# LIVE
# ============================================================

def get_live_data():

    data = api_get("/live")

    rides = data.get("rides", [])

    return {
        int(ride["id"]): ride
        for ride in rides
    }


# ============================================================
# CALENDARIO / PREDICCIÓN
# ============================================================

def get_calendar_day(today):

    try:

        data = api_get("/calendar")

        for day in data.get("days", []):

            if day.get("date") == today:
                return day

    except Exception as e:

        print(f"Advertencia calendario: {e}")

    return {}


# ============================================================
# HORARIO
# ============================================================

def get_schedule_day(today):

    try:

        data = api_get("/schedule")

        for day in data.get("schedule", []):

            if day.get("date") == today:
                return day

    except Exception as e:

        print(f"Advertencia horario: {e}")

    return {}


# ============================================================
# CONVERTIR HORA
# ============================================================

def parse_time(value):

    if not value:
        return None

    try:

        # Ejemplo:
        # 2026-08-11T11:00:00+02:00

        return datetime.fromisoformat(value)

    except Exception:

        return None


# ============================================================
# DETERMINAR SI EL PARQUE ESTÁ ABIERTO
# ============================================================

def is_park_open(now_madrid, opening, closing):

    opening_dt = parse_time(opening)
    closing_dt = parse_time(closing)

    if not opening_dt or not closing_dt:
        return None

    return (
        opening_dt <= now_madrid <= closing_dt
    )


# ============================================================
# ÍNDICE DE AFLUENCIA OBSERVADA
# ============================================================

def calculate_observed_crowd(wait_times):

    if not wait_times:
        return None

    average_wait = mean(wait_times)
    median_wait = median(wait_times)
    maximum_wait = max(wait_times)

    average_score = min(
        average_wait / 120 * 100,
        100
    )

    median_score = min(
        median_wait / 120 * 100,
        100
    )

    maximum_score = min(
        maximum_wait / 180 * 100,
        100
    )

    observed_index = (
        average_score * 0.45
        + median_score * 0.35
        + maximum_score * 0.20
    )

    return round(observed_index, 1)


# ============================================================
# RECOPILACIÓN
# ============================================================

def collect():

    now_utc = datetime.now(UTC_TZ)
    now_madrid = now_utc.astimezone(MADRID_TZ)

    timestamp_utc = now_utc.isoformat()
    timestamp_madrid = now_madrid.isoformat()

    date_madrid = now_madrid.date().isoformat()

    print("==========================================")
    print("PORTAVENTURA QUEUE STUDY")
    print(
        "Hora Madrid:",
        now_madrid.strftime("%Y-%m-%d %H:%M:%S")
    )
    print("==========================================")

    # --------------------------------------------------------
    # CONSULTAS
    # --------------------------------------------------------

    print("Consultando tiempos de cola...")
    live_rides = get_live_data()

    print("Consultando predicción de afluencia...")
    calendar_day = get_calendar_day(date_madrid)

    print("Consultando horario...")
    schedule_day = get_schedule_day(date_madrid)

    crowd_forecast = (
        calendar_day.get("crowdPercent")
    )

    # --------------------------------------------------------
    # HORARIO
    # --------------------------------------------------------

    opening_time = schedule_day.get(
        "openingTime"
    )

    closing_time = schedule_day.get(
        "closingTime"
    )

    print(
        f"Horario: {opening_time} -> {closing_time}"
    )

    # --------------------------------------------------------
    # PORTAVENTURA Y FERRARI LAND
    #
    # De momento la API devuelve el horario del complejo.
    # Lo guardamos como referencia.
    # --------------------------------------------------------

    park_open = is_park_open(
        now_madrid,
        opening_time,
        closing_time
    )

    print(
        f"Parque abierto: {park_open}"
    )

    # --------------------------------------------------------
    # ATRACCIONES
    # --------------------------------------------------------

    collected = []
    wait_times_all = []

    for ride_config in RIDES:

        ride = live_rides.get(
            ride_config["id"]
        )

        if ride is None:

            print(
                f"{ride_config['code']} -> NOT_FOUND"
            )

            status = "NOT_FOUND"
            wait_minutes = None
            last_updated = None
            api_name = ""

        else:

            api_name = ride.get(
                "name",
                ""
            )

            status = ride.get(
                "status",
                "UNKNOWN"
            )

            wait_minutes = ride.get(
                "waitMinutes"
            )

            last_updated = ride.get(
                "lastUpdated"
            )

            if isinstance(
                wait_minutes,
                (int, float)
            ):

                wait_times_all.append(
                    float(wait_minutes)
                )

        collected.append(
            {
                "park": ride_config["park"],
                "code": ride_config["code"],
                "ride": ride_config["name"],
                "api_name": api_name,
                "ride_id": ride_config["id"],
                "status": status,
                "wait_minutes": wait_minutes,
                "last_updated": last_updated,
            }
        )

        print(
            f"{ride_config['park']} | "
            f"{ride_config['code']} | "
            f"{status} | "
            f"{wait_minutes} min"
        )

    # --------------------------------------------------------
    # ESTADÍSTICAS
    # --------------------------------------------------------

    rides_with_wait = len(
        wait_times_all
    )

    rides_operating = sum(
        1
        for item in collected
        if item["status"] == "OPERATING"
    )

    if wait_times_all:

        queue_mean = round(
            mean(wait_times_all),
            1
        )

        queue_median = round(
            median(wait_times_all),
            1
        )

        queue_max = max(
            wait_times_all
        )

        observed_crowd_index = (
            calculate_observed_crowd(
                wait_times_all
            )
        )

    else:

        queue_mean = None
        queue_median = None
        queue_max = None
        observed_crowd_index = None

    print("------------------------------------------")
    print(f"Predicción de afluencia: {crowd_forecast}")
    print(f"Cola media: {queue_mean}")
    print(f"Mediana: {queue_median}")
    print(f"Máxima: {queue_max}")
    print(f"Atracciones operativas: {rides_operating}")
    print(f"Atracciones con cola: {rides_with_wait}")
    print(
        f"Índice de afluencia observado: "
        f"{observed_crowd_index}"
    )
    print("------------------------------------------")

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    rows = []

    for item in collected:

        rows.append(
            {
                "timestamp_utc": timestamp_utc,
                "timestamp_madrid": timestamp_madrid,
                "date_madrid": date_madrid,

                "park": item["park"],
                "code": item["code"],
                "ride": item["ride"],
                "api_name": item["api_name"],
                "ride_id": item["ride_id"],

                "status": item["status"],
                "wait_minutes": item["wait_minutes"],
                "last_updated": item["last_updated"],

                "crowd_forecast": crowd_forecast,
                "observed_crowd_index":
                    observed_crowd_index,

                "queue_mean": queue_mean,
                "queue_median": queue_median,
                "queue_max": queue_max,

                "rides_operating":
                    rides_operating,

                "rides_with_wait":
                    rides_with_wait,

                "park_open":
                    park_open,

                "park_opening":
                    opening_time,

                "park_closing":
                    closing_time,
            }
        )

    return rows


# ============================================================
# GUARDAR CSV
# ============================================================

def save_rows(rows):

    os.makedirs(
        "data",
        exist_ok=True
    )

    fieldnames = [
        "timestamp_utc",
        "timestamp_madrid",
        "date_madrid",

        "park",
        "code",
        "ride",
        "api_name",
        "ride_id",

        "status",
        "wait_minutes",
        "last_updated",

        "crowd_forecast",
        "observed_crowd_index",

        "queue_mean",
        "queue_median",
        "queue_max",

       
