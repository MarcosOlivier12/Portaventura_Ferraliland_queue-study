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
# ATRACCIONES
# ============================================================

RIDES = [

    # ---------------- PORTAVENTURA ----------------

    {
        "park": "PortAventura",
        "code": "UNCH",
        "name": "Uncharted",
        "id": 5614,
    },
    {
        "park": "PortAventura",
        "code": "SM",
        "name": "Street Mission",
        "id": 5652,
    },
    {
        "park": "PortAventura",
        "code": "SH",
        "name": "Shambhala",
        "id": 5603,
    },
    {
        "park": "PortAventura",
        "code": "DK",
        "name": "Dragon Khan",
        "id": 5630,
    },
    {
        "park": "PortAventura",
        "code": "FB",
        "name": "Furius Baco",
        "id": 5596,
    },
    {
        "park": "PortAventura",
        "code": "HC",
        "name": "Hurakan Condor",
        "id": 5644,
    },
    {
        "park": "PortAventura",
        "code": "STAM",
        "name": "Stampida",
        "id": 5608,
    },
    {
        "park": "PortAventura",
        "code": "TK",
        "name": "Tutuki Splash",
        "id": 5649,
    },
    {
        "park": "PortAventura",
        "code": "DB",
        "name": "El Diablo - Tren De La Mina",
        "id": 5645,
    },
    {
        "park": "PortAventura",
        "code": "SVR",
        "name": "Silver River Flume",
        "id": 5646,
    },
    {
        "park": "PortAventura",
        "code": "TF",
        "name": "Templo del Fuego",
        "id": 5591,
    },

    # ---------------- FERRARI LAND ----------------

    {
        "park": "Ferrari Land",
        "code": "RF",
        "name": "Red Force",
        "id": 5612,
    },
    {
        "park": "Ferrari Land",
        "code": "TT",
        "name": "Thrill Towers",
        "id": 5590,
    },
    {
        "park": "Ferrari Land",
        "code": "FLY",
        "name": "Flying Dreams",
        "id": 5611,
    },
]


# ============================================================
# FUNCIÓN GENERAL PARA LA API
# ============================================================

def api_get(endpoint):

    url = f"{BASE_URL}{endpoint}"

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("success"):
        raise RuntimeError(
            result.get(
                "error",
                "Error desconocido de la API"
            )
        )

    return result["data"]


# ============================================================
# TIEMPOS DE COLA
# ============================================================

def get_live_data():

    print("Consultando tiempos de cola...")

    data = api_get("/live")

    rides = data.get("rides", [])

    return {
        int(ride["id"]): ride
        for ride in rides
    }


# ============================================================
# PREDICCIÓN DE AFLUENCIA
# ============================================================

def get_calendar_day(today):

    print("Consultando predicción de afluencia...")

    try:

        data = api_get("/calendar")

        days = data.get("days", [])

        for day in days:

            if day.get("date") == today:
                return day

    except Exception as e:

        print(
            "ERROR calendario:",
            e
        )

    return {}


# ============================================================
# HORARIO DEL PARQUE
# ============================================================

def get_schedule_day(today):

    print("Consultando horario...")

    try:

        data = api_get("/schedule")

        schedule = data.get(
            "schedule",
            []
        )

        for day in schedule:

            if day.get("date") == today:
                return day

    except Exception as e:

        print(
            "ERROR horario:",
            e
        )

    return {}


# ============================================================
# CONVERTIR FECHA/HORA
# ============================================================

def parse_datetime(value):

    if not value:
        return None

    try:

        return datetime.fromisoformat(
            value
        )

    except Exception:

        return None


# ============================================================
# SABER SI EL PARQUE ESTÁ ABIERTO
# ============================================================

def calculate_park_open(
    now_madrid,
    opening,
    closing
):

    opening_dt = parse_datetime(
        opening
    )

    closing_dt = parse_datetime(
        closing
    )

    if (
        opening_dt is None
        or closing_dt is None
    ):
        return None

    return (
        opening_dt
        <= now_madrid
        <= closing_dt
    )


# ============================================================
# ÍNDICE DE AFLUENCIA OBSERVADA
# ============================================================

def calculate_observed_crowd(
    wait_times
):

    if not wait_times:
        return None

    average_wait = mean(
        wait_times
    )

    median_wait = median(
        wait_times
    )

    maximum_wait = max(
        wait_times
    )

    # -----------------------------------------
    # NORMALIZACIÓN
    # -----------------------------------------

    average_score = min(
        (average_wait / 120) * 100,
        100
    )

    median_score = min(
        (median_wait / 120) * 100,
        100
    )

    maximum_score = min(
        (maximum_wait / 180) * 100,
        100
    )

    # -----------------------------------------
    # ÍNDICE FINAL
    # -----------------------------------------

    observed_index = (
        average_score * 0.45
        + median_score * 0.35
        + maximum_score * 0.20
    )

    return round(
        observed_index,
        1
    )


# ============================================================
# RECOPILACIÓN PRINCIPAL
# ============================================================

def collect():

    # -----------------------------------------
    # HORA
    # -----------------------------------------

    now_utc = datetime.now(
        UTC_TZ
    )

    now_madrid = now_utc.astimezone(
        MADRID_TZ
    )

    timestamp_utc = (
        now_utc.isoformat()
    )

    timestamp_madrid = (
        now_madrid.isoformat()
    )

    date_madrid = (
        now_madrid.date().isoformat()
    )

    print(
        "=========================================="
    )

    print(
        "PORTAVENTURA QUEUE STUDY"
    )

    print(
        "Hora Madrid:",
        now_madrid.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print(
        "=========================================="
    )

    # -----------------------------------------
    # API
    # -----------------------------------------

    live_data = get_live_data()

    calendar_day = get_calendar_day(
        date_madrid
    )

    schedule_day = get_schedule_day(
        date_madrid
    )

    # -----------------------------------------
    # AFLUENCIA PREVISTA
    # -----------------------------------------

    crowd_forecast = (
        calendar_day.get(
            "crowdPercent"
        )
    )

    print(
        "Predicción de afluencia:",
        crowd_forecast
    )

    # -----------------------------------------
    # HORARIO
    # -----------------------------------------

    opening_time = (
        schedule_day.get(
            "openingTime"
        )
    )

    closing_time = (
        schedule_day.get(
            "closingTime"
        )
    )

    print(
        "Apertura:",
        opening_time
    )

    print(
        "Cierre:",
        closing_time
    )

    park_open = calculate_park_open(
        now_madrid,
        opening_time,
        closing_time
    )

    print(
        "Parque abierto:",
        park_open
    )

    # -----------------------------------------
    # ATRACCIONES
    # -----------------------------------------

    collected = []

    wait_times = []

    for ride_config in RIDES:

        ride_id = ride_config["id"]

        ride = live_data.get(
            ride_id
        )

        if ride is None:

            print(
                ride_config["code"],
                "-> NOT_FOUND"
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

                wait_times.append(
                    float(
                        wait_minutes
                    )
                )

        collected.append(
            {
                "park":
                    ride_config["park"],

                "code":
                    ride_config["code"],

                "ride":
                    ride_config["name"],

                "api_name":
                    api_name,

                "ride_id":
                    ride_id,

                "status":
                    status,

                "wait_minutes":
                    wait_minutes,

                "last_updated":
                    last_updated,
            }
        )

        print(
            f"{ride_config['park']} | "
            f"{ride_config['code']} | "
            f"{status} | "
            f"{wait_minutes} min"
        )

    # -----------------------------------------
    # ESTADÍSTICAS
    # -----------------------------------------

    rides_with_wait = len(
        wait_times
    )

    rides_operating = sum(
        1
        for ride in collected
        if ride["status"] == "OPERATING"
    )

    if wait_times:

        queue_mean = round(
            mean(wait_times),
            1
        )

        queue_median = round(
            median(wait_times),
            1
        )

        queue_max = max(
            wait_times
        )

        observed_crowd_index = (
            calculate_observed_crowd(
                wait_times
            )
        )

    else:

        queue_mean = None

        queue_median = None

        queue_max = None

        observed_crowd_index = None

    print(
        "------------------------------------------"
    )

    print(
        "Cola media:",
        queue_mean
    )

    print(
        "Mediana:",
        queue_median
    )

    print(
        "Máxima:",
        queue_max
    )

    print(
        "Atracciones operativas:",
        rides_operating
    )

    print(
        "Atracciones con cola:",
        rides_with_wait
    )

    print(
        "Índice de afluencia observado:",
        observed_crowd_index
    )

    print(
        "------------------------------------------"
    )

    # -----------------------------------------
    # CREAR FILAS CSV
    # -----------------------------------------

    rows = []

    for ride in collected:

        row = {

            "timestamp_utc":
                timestamp_utc,

            "timestamp_madrid":
                timestamp_madrid,

            "date_madrid":
                date_madrid,

            "park":
                ride["park"],

            "code":
                ride["code"],

            "ride":
                ride["ride"],

            "api_name":
                ride["api_name"],

            "ride_id":
                ride["ride_id"],

            "status":
                ride["status"],

            "wait_minutes":
                ride["wait_minutes"],

            "last_updated":
                ride["last_updated"],

            "crowd_forecast":
                crowd_forecast,

            "observed_crowd_index":
                observed_crowd_index,

            "queue_mean":
                queue_mean,

            "queue_median":
                queue_median,

            "queue_max":
                queue_max,

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

        rows.append(
            row
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
        "rides_operating",
        "rides_with_wait",
        "park_open",
        "park_opening",
        "park_closing",
    ]

    file_exists = os.path.exists(
        CSV_FILE
    )

    with open(
        CSV_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        if not file_exists:

            writer.writeheader()

        writer.writerows(
            rows
        )

    print(
        f"Guardados {len(rows)} registros."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    try:

        rows = collect()

        save_rows(
            rows
        )

        print(
            "=========================================="
        )

        print(
            "RECOPILACIÓN COMPLETADA CORRECTAMENTE"
        )

        print(
            "=========================================="
        )

    except Exception as error:

        print(
            "=========================================="
        )

        print(
            "ERROR:",
            error
        )

        print(
            "=========================================="
        )

        raise


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":

    main()
