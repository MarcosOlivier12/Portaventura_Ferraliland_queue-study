import csv
import os
import requests

from datetime import datetime, time
from zoneinfo import ZoneInfo
from statistics import mean, median


# ============================================================
# CONFIGURACIÓN
# ============================================================

API_KEY = os.environ.get("PARK_QUEUE_TIMES_API_KEY")

PARKQUEUETIMES_PARK_ID = 87

QUEUE_TIMES_PORTAVENTURA_ID = 19
QUEUE_TIMES_FERRARI_ID = 277

CSV_FILE = "data/queue_history.csv"

MADRID_TZ = ZoneInfo("Europe/Madrid")
UTC_TZ = ZoneInfo("UTC")

PARK_QUEUE_BASE_URL = (
    f"https://api.parkqueuetimes.com/v1/parks/"
    f"{PARKQUEUETIMES_PARK_ID}"
)

HEADERS = {
    "x-api-key": API_KEY or "",
    "User-Agent": "PortAventura-Queue-Study/1.0",
}


# ============================================================
# HORARIOS
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
# FUNCIONES AUXILIARES
# ============================================================

def is_open(current_time, opening, closing):

    return opening <= current_time <= closing


def normalize_name(name):

    if not name:
        return ""

    return (
        str(name)
        .lower()
        .strip()
        .replace("-", " ")
        .replace("_", " ")
    )


# ============================================================
# PARKQUEUETIMES
# ============================================================

def park_queue_api_get(endpoint):

    if not API_KEY:
        print(
            "AVISO: PARK_QUEUE_TIMES_API_KEY no está configurada."
        )
        return None

    url = f"{PARK_QUEUE_BASE_URL}{endpoint}"

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
        )

        response.raise_for_status()

        result = response.json()

        if not result.get("success"):

            print(
                "ParkQueueTimes devolvió error:",
                result.get(
                    "error",
                    "Error desconocido"
                )
            )

            return None

        return result.get("data")

    except Exception as error:

        print(
            f"ERROR ParkQueueTimes {endpoint}:",
            error
        )

        return None


def get_calendar_day(today):

    print(
        "Consultando predicción de afluencia..."
    )

    try:

        data = park_queue_api_get(
            "/calendar"
        )

        if not data:
            return {}

        days = data.get(
            "days",
            []
        )

        for day in days:

            if day.get("date") == today:

                return day

    except Exception as error:

        print(
            "ERROR calendario:",
            error
        )

    return {}


# ============================================================
# QUEUE-TIMES
# ============================================================

def get_queue_times_for_park(
    park_id,
    park_name
):

    print(
        f"Consultando Queue-Times {park_name}..."
    )

    url = (
        f"https://queue-times.com/parks/"
        f"{park_id}/queue_times.json"
    )

    try:

        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent":
                    "Mozilla/5.0 "
                    "(compatible; "
                    "PortAventura-Queue-Study/1.0)"
            }
        )

        response.raise_for_status()

        data = response.json()

        all_rides = []

        all_rides.extend(
            data.get("rides", [])
        )

        for land in data.get(
            "lands",
            []
        ):

            all_rides.extend(
                land.get(
                    "rides",
                    []
                )
            )

        rides = {}

        for ride in all_rides:

            ride_id = ride.get("id")
            ride_name = ride.get("name")

            if ride_id is None:
                continue

            rides[str(ride_id)] = {
                "id":
                    ride_id,

                "name":
                    ride_name or "",

                "status":
                    (
                        "OPERATING"
                        if ride.get("is_open") is True
                        else "CLOSED"
                    ),

                "waitMinutes":
                    ride.get("wait_time"),

                "lastUpdated":
                    ride.get("last_updated"),
            }

        print(
            f"Queue-Times {park_name}: "
            f"recibidas {len(rides)} atracciones"
        )

        return rides

    except Exception as error:

        print(
            f"ERROR Queue-Times {park_name}:",
            error
        )

        return {}


# ============================================================
# AFLUENCIA
# ============================================================

def get_crowd_forecast():

    calendar_day = get_calendar_day(
        datetime.now(
            MADRID_TZ
        ).date().isoformat()
    )

    return calendar_day.get(
        "crowdPercent"
    )


def get_observed_crowd(
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

    index = (
        average_score * 0.45
        + median_score * 0.35
        + maximum_score * 0.20
    )

    return round(
        index,
        1
    )


# ============================================================
# ESTADÍSTICAS POR PARQUE
# ============================================================

def calculate_statistics(
    rows
):

    wait_times = [
        float(row["wait_minutes"])
        for row in rows
        if row["ride_open"]
        and isinstance(
            row["wait_minutes"],
            (int, float)
        )
    ]

    rides_operating = sum(
        1
        for row in rows
        if row["ride_open"]
    )

    rides_with_wait = len(
        wait_times
    )

    if not wait_times:

        return {
            "mean": None,
            "median": None,
            "max": None,
            "operating":
                rides_operating,
            "with_wait":
                rides_with_wait,
            "observed":
                None,
        }

    return {
        "mean":
            round(
                mean(wait_times),
                1
            ),

        "median":
            round(
                median(wait_times),
                1
            ),

        "max":
            max(wait_times),

        "operating":
            rides_operating,

        "with_wait":
            rides_with_wait,

        "observed":
            get_observed_crowd(
                wait_times
            ),
    }


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

    current_time = (
        now_madrid.time()
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
    # SI PORTAVENTURA ESTÁ CERRADO
    # --------------------------------------------------------

    if not portaventura_open:

        print(
            "PortAventura está cerrado."
        )

        print(
            "No se realiza recopilación."
        )

        return []

    # --------------------------------------------------------
    # OBTENER QUEUES
    # --------------------------------------------------------

    portaventura_data = (
        get_queue_times_for_park(
            QUEUE_TIMES_PORTAVENTURA_ID,
            "PortAventura"
        )
    )

    ferrari_data = (
        get_queue_times_for_park(
            QUEUE_TIMES_FERRARI_ID,
            "Ferrari Land"
        )
    )

    # --------------------------------------------------------
    # AFLUENCIA
    # --------------------------------------------------------

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
    # PRIMERA PASADA
    # --------------------------------------------------------

    collected = []

    for config in RIDES:

        park = config["park"]

        ride_id = str(
            config["id"]
        )

        if park == "PortAventura":

            source = portaventura_data
            park_open = (
                portaventura_open
            )

        else:

            source = ferrari_data
            park_open = (
                ferrari_land_open
            )

        ride = source.get(
            ride_id
        )

        api_name = ""
        status = "SOURCE_NOT_AVAILABLE"
        ride_open = False
        wait_minutes = None
        last_updated = None

        if ride is not None:

            api_name = ride.get(
                "name",
                ""
            )

            last_updated = ride.get(
                "lastUpdated"
            )

            if not park_open:

                status = "CLOSED_PARK"

            elif ride.get(
                "status"
            ) == "OPERATING":

                status = "OPERATING"
                ride_open = True

                wait_minutes = ride.get(
                    "waitMinutes"
                )

            else:

                status = "CLOSED"

        collected.append(
            {
                "park":
                    park,

                "code":
                    config["code"],

                "ride":
                    config["name"],

                "api_name":
                    api_name,

                "ride_id":
                    config["id"],

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

    # --------------------------------------------------------
    # ESTADÍSTICAS SEPARADAS
    # --------------------------------------------------------

    port_rows = [
        row
        for row in collected
        if row["park"]
        == "PortAventura"
    ]

    ferrari_rows = [
        row
        for row in collected
        if row["park"]
        == "Ferrari Land"
    ]

    port_stats = calculate_statistics(
        port_rows
    )

    ferrari_stats = calculate_statistics(
        ferrari_rows
    )

    # --------------------------------------------------------
    # MOSTRAR RESULTADOS
    # --------------------------------------------------------

    print(
        "------------------------------------------"
    )

    print(
        "PortAventura"
    )

    print(
        "Cola media:",
        port_stats["mean"]
    )

    print(
        "Mediana:",
        port_stats["median"]
    )

    print(
        "Máxima:",
        port_stats["max"]
    )

    print(
        "Atracciones operativas:",
        port_stats["operating"]
    )

    print(
        "Atracciones con cola:",
        port_stats["with_wait"]
    )

    print(
        "Índice de afluencia observado:",
        port_stats["observed"]
    )

    print(
        "------------------------------------------"
    )

    print(
        "Ferrari Land"
    )

    print(
        "Cola media:",
        ferrari_stats["mean"]
    )

    print(
        "Mediana:",
        ferrari_stats["median"]
    )

    print(
        "Máxima:",
        ferrari_stats["max"]
    )

    print(
        "Atracciones operativas:",
        ferrari_stats["operating"]
    )

    print(
        "Atracciones con cola:",
        ferrari_stats["with_wait"]
    )

    print(
        "Índice de afluencia observado:",
        ferrari_stats["observed"]
    )

    print(
        "------------------------------------------"
    )

    # --------------------------------------------------------
    # CREAR FILAS CSV
    # SIEMPRE EXACTAMENTE 25 COLUMNAS
    # --------------------------------------------------------

    rows = []

    for ride in collected:

        if ride["park"] == "PortAventura":

            observed = (
                port_stats["observed"]
            )

            queue_mean = (
                port_stats["mean"]
            )

            queue_median = (
                port_stats["median"]
            )

            queue_max = (
                port_stats["max"]
            )

            rides_operating = (
                port_stats["operating"]
            )

            rides_with_wait = (
                port_stats["with_wait"]
            )

        else:

            observed = (
                ferrari_stats["observed"]
            )

            queue_mean = (
                ferrari_stats["mean"]
            )

            queue_median = (
                ferrari_stats["median"]
            )

            queue_max = (
                ferrari_stats["max"]
            )

            rides_operating = (
                ferrari_stats["operating"]
            )

            rides_with_wait = (
                ferrari_stats["with_wait"]
            )

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
                observed,

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

        print(
            f"{ride['park']} | "
            f"{ride['code']} | "
            f"{ride['status']} | "
            f"{ride['wait_minutes']} min"
        )

    print(
        "------------------------------------------"
    )

    print(
        f"Filas preparadas: {len(rows)}"
    )

    return rows


# ============================================================
# COLUMNAS CSV
# ============================================================

FIELDNAMES = [

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


# ============================================================
# VALIDAR CSV EXISTENTE
# ============================================================

def validate_existing_csv():

    if not os.path.exists(
        CSV_FILE
    ):

        return True

    try:

        with open(
            CSV_FILE,
            "r",
            newline="",
            encoding="utf-8"
        ) as file:

            reader = csv.reader(
                file
            )

            for line_number, row in enumerate(
                reader,
                start=1
            ):

                if len(row) != len(
                    FIELDNAMES
                ):

                    raise RuntimeError(
                        f"CSV corrupto: línea "
                        f"{line_number} tiene "
                        f"{len(row)} columnas "
                        f"en vez de "
                        f"{len(FIELDNAMES)}."
                    )

        return True

    except UnicodeDecodeError:

        raise RuntimeError(
            "El CSV no está codificado "
            "correctamente en UTF-8."
        )


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

    # --------------------------------------------------------
    # VALIDAR CSV ANTES DE AÑADIR
    # --------------------------------------------------------

    validate_existing_csv()

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
            fieldnames=FIELDNAMES,
            extrasaction="ignore"
        )

        if not file_exists:

            writer.writeheader()

        for row in rows:

            writer.writerow(
                row
            )

    # --------------------------------------------------------
    # VALIDACIÓN FINAL
    # --------------------------------------------------------

    validate_existing_csv()

    print(
        f"Guardados {len(rows)} registros."
    )

    print(
        f"Estructura validada: "
        f"{len(FIELDNAMES)} columnas."
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
