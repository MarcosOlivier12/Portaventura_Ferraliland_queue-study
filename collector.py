import csv
import os
import requests
from datetime import datetime, time
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
# HORARIOS FIJOS - HORA MADRID
# ============================================================

PORTAVENTURA_OPENING = time(10, 30)
PORTAVENTURA_CLOSING = time(23, 30)

FERRARI_OPENING = time(17, 0)
FERRARI_CLOSING = time(22, 0)


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
# API
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


def get_queue_times():
    """
    Obtiene los tiempos de cola de PortAventura directamente
    desde Queue-Times.

    PortAventura Park = ID 19
    """

    url = "https://queue-times.com/parks/19/queue_times.json"

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()

        data = response.json()

        rides = {}

        # Queue-Times puede devolver atracciones directamente
        # o dentro de lands.
        all_rides = []

        all_rides.extend(data.get("rides", []))

        for land in data.get("lands", []):
            all_rides.extend(land.get("rides", []))

        for ride in all_rides:
            ride_name = ride.get("name")

            if not ride_name:
                continue

            rides[ride_name] = {
                "id": ride.get("id"),
                "status": (
                    "OPERATING"
                    if ride.get("is_open") is True
                    else "CLOSED"
                ),
                "waitMinutes": ride.get("wait_time"),
                "lastUpdated": ride.get("last_updated")
            }

        print(f"Queue-Times: recibidas {len(rides)} atracciones")

        return rides

    except Exception as e:
        print(f"ERROR consultando Queue-Times: {e}")
        return {}

# ============================================================
# PREDICCIÓN DE AFLUENCIA
# ============================================================

def get_calendar_day(today):

    print(
        "Consultando predicción de afluencia..."
    )

    try:

        data = api_get(
            "/calendar"
        )

        days = data.get(
            "days",
            []
        )

        for day in days:

            if day.get(
                "date"
            ) == today:

                return day

    except Exception as error:

        print(
            "ERROR calendario:",
            error
        )

    return {}


# ============================================================
# HORARIO DE PARQUES
# ============================================================

def is_open(
    current_time,
    opening,
    closing
):

    return (
        opening
        <= current_time
        <= closing
    )


# ============================================================
# AFLUENCIA OBSERVADA
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
# RECOPILACIÓN
# ============================================================

def collect():

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

    current_time = now_madrid.time()

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

    # --------------------------------------------------------
    # ESTADO DE LOS PARQUES
    # --------------------------------------------------------

    portaventura_open = is_open(
        current_time,
        PORTAVENTURA_OPENING,
        PORTAVENTURA_CLOSING
    )

    ferrari_land_open = is_open(
        current_time,
        FERRARI_OPENING,
        FERRARI_CLOSING
    )

    print(
        "PortAventura:",
        "ABIERTO"
        if portaventura_open
        else "CERRADO"
    )

    print(
        "Ferrari Land:",
        "ABIERTO"
        if ferrari_land_open
        else "CERRADO"
    )

    print(
        "Horario PortAventura: 10:30 - 23:30"
    )

    print(
        "Horario Ferrari Land: 17:00 - 22:00"
    )

    # --------------------------------------------------------
    # SI AMBOS PARQUES ESTÁN CERRADOS
    # --------------------------------------------------------

    if (
        not portaventura_open
        and not ferrari_land_open
    ):

        print(
            "Ambos parques están cerrados."
        )

        print(
            "No se realiza recopilación."
        )

        return []

    # --------------------------------------------------------
    # API
    # --------------------------------------------------------

    live_data = get_live_data()

    calendar_day = get_calendar_day(
        date_madrid
    )

    crowd_forecast = (
        calendar_day.get(
            "crowdPercent"
        )
    )

    print(
        "Predicción de afluencia:",
        crowd_forecast
    )

    # --------------------------------------------------------
    # ATRACCIONES
    # --------------------------------------------------------

    collected = []

    wait_times = []

    for ride_config in RIDES:

        park = ride_config["park"]

        ride_id = ride_config["id"]

        ride = live_data.get(
            ride_id
        )

        # ------------------------------------
        # ¿EL PARQUE DE ESTA ATRACCIÓN ESTÁ ABIERTO?
        # ------------------------------------

        if park == "PortAventura":

            park_is_open = (
                portaventura_open
            )

        else:

            park_is_open = (
                ferrari_land_open
            )

        # ------------------------------------
        # ATRACCIÓN NO ENCONTRADA
        # ------------------------------------

        if ride is None:

            status = "NOT_FOUND"

            wait_minutes = None

            last_updated = None

            api_name = ""

            ride_open = False

        else:

            api_name = ride.get(
                "name",
                ""
            )

            api_status = ride.get(
                "status",
                "UNKNOWN"
            )

            wait_minutes = ride.get(
                "waitMinutes"
            )

            last_updated = ride.get(
                "lastUpdated"
            )

            # --------------------------------
            # ESTADO INDIVIDUAL
            # --------------------------------

            if not park_is_open:

                status = "CLOSED_PARK"

                ride_open = False

                wait_minutes = None

            elif api_status == "OPERATING":

                status = "OPERATING"

                ride_open = True

            else:

                status = api_status

                ride_open = False

                wait_minutes = None

            # --------------------------------
            # SOLO CONTAR COLAS VÁLIDAS
            # --------------------------------

            if (
                ride_open
                and isinstance(
                    wait_minutes,
                    (int, float)
                )
            ):

                wait_times.append(
                    float(
                        wait_minutes
                    )
                )

        # ------------------------------------
        # GUARDAR RESULTADO
        # ------------------------------------

        collected.append(
            {
                "park":
                    park,

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

                "ride_open":
                    ride_open,

                "wait_minutes":
                    wait_minutes,

                "last_updated":
                    last_updated,
            }
        )

        print(
            f"{park} | "
            f"{ride_config['code']} | "
            f"{status} | "
            f"{wait_minutes} min"
        )

    # --------------------------------------------------------
    # ESTADÍSTICAS
    # --------------------------------------------------------

    rides_with_wait = len(
        wait_times
    )

    rides_operating = sum(
        1
        for ride in collected
        if ride["ride_open"]
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

    # --------------------------------------------------------
    # CREAR FILAS CSV
    # --------------------------------------------------------

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

            "ride_open":
                ride["ride_open"],

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

            "portaventura_open":
                portaventura_open,

            "ferrari_land_open":
                ferrari_land_open,

            "portaventura_opening":
                "10:30",

            "portaventura_closing":
                "23:30",

            "ferrari_land_opening":
                "17:00",

            "ferrari_land_closing":
                "22:00",
        }

        rows.append(
            row
        )

    return rows


# ============================================================
# GUARDAR CSV
# ============================================================

def save_rows(rows):

    if not rows:

        print(
            "No hay registros que guardar."
        )

        return

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
        "ride_open",
        "wait_minutes",
        "last_updated",

        "crowd_forecast",
        "observed_crowd_index",

        "queue_mean",
        "queue_median",
        "queue_max",

        "rides_operating",
        "rides_with_wait",

        "portaventura_open",
        "ferrari_land_open",

        "portaventura_opening",
        "portaventura_closing",

        "ferrari_land_opening",
        "ferrari_land_closing",
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
