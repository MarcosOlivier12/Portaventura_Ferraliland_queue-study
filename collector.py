import csv
import os
import requests

from datetime import datetime, time
from zoneinfo import ZoneInfo
from statistics import mean, median


# ============================================================
# CONFIGURACIÓN
# ============================================================

QUEUE_TIMES_PORTAVENTURA_ID = 19
QUEUE_TIMES_FERRARI_ID = 277

PARKQUEUETIMES_API_KEY = os.environ.get(
    "PARK_QUEUE_TIMES_API_KEY"
)

PARKQUEUETIMES_BASE_URL = (
    "https://api.parkqueuetimes.com/v1"
)

PARKQUEUETIMES_PORTAVENTURA_ID = 87
PARKQUEUETIMES_FERRARI_ID = 88

CSV_FILE = "data/queue_history.csv"

MADRID_TZ = ZoneInfo("Europe/Madrid")
UTC_TZ = ZoneInfo("UTC")

QUEUE_TIMES_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(compatible; PortAventura-Queue-Study/1.0)"
    )
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

    # --------------------------------------------------------
    # PORTAVENTURA
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # FERRARI LAND
    # --------------------------------------------------------

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
# FUNCIONES AUXILIARES
# ============================================================

def is_open(current_time, opening, closing):
    return opening <= current_time <= closing


def normalize_name(name):
    if not name:
        return ""

    text = str(name).lower().strip()

    replacements = {
        "-": " ",
        "_": " ",
        "–": " ",
        "—": " ",
        "'": "",
        ".": "",
        ",": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


# ============================================================
# QUEUE-TIMES
# ============================================================

def get_queue_times_for_park(park_id, park_name):

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
            headers=QUEUE_TIMES_HEADERS
        )

        response.raise_for_status()

        data = response.json()

        all_rides = []

        # Algunas respuestas tienen las atracciones
        # directamente en "rides".
        rides_direct = data.get("rides", [])

        if isinstance(rides_direct, list):
            all_rides.extend(rides_direct)

        # Y otras las contienen dentro de "lands".
        lands = data.get("lands", [])

        if isinstance(lands, list):

            for land in lands:

                if not isinstance(land, dict):
                    continue

                land_rides = land.get(
                    "rides",
                    []
                )

                if isinstance(land_rides, list):
                    all_rides.extend(
                        land_rides
                    )

        rides_by_id = {}
        rides_by_name = {}

        for ride in all_rides:

            if not isinstance(ride, dict):
                continue

            ride_id = ride.get("id")
            ride_name = ride.get("name")

            if ride_id is not None:

                rides_by_id[
                    str(ride_id)
                ] = ride

            normalized = normalize_name(
                ride_name
            )

            if normalized:

                rides_by_name[
                    normalized
                ] = ride

        print(
            f"Queue-Times {park_name}: "
            f"recibidas {len(rides_by_id)} atracciones"
        )

        return {
            "by_id": rides_by_id,
            "by_name": rides_by_name,
        }

    except Exception as error:

        print(
            f"ERROR Queue-Times {park_name}:",
            error
        )

        return {
            "by_id": {},
            "by_name": {},
        }


def find_ride(source, config):

    if not source:
        return None

    # --------------------------------------------------------
    # 1. BUSCAR POR ID
    # --------------------------------------------------------

    ride_id = str(
        config["id"]
    )

    ride = source.get(
        "by_id",
        {}
    ).get(
        ride_id
    )

    if ride is not None:
        return ride

    # --------------------------------------------------------
    # 2. BUSCAR POR NOMBRE
    # --------------------------------------------------------

    config_name = normalize_name(
        config["name"]
    )

    ride = source.get(
        "by_name",
        {}
    ).get(
        config_name
    )

    if ride is not None:
        return ride

    # --------------------------------------------------------
    # 3. BÚSQUEDA FLEXIBLE
    # --------------------------------------------------------

    for api_name, candidate in source.get(
        "by_name",
        {}
    ).items():

        if (
            config_name in api_name
            or api_name in config_name
        ):

            return candidate

    return None


# ============================================================
# PREDICCIÓN DE AFLUENCIA
# ============================================================

def get_crowd_forecast(
    park_id,
    park_name,
    date_madrid
):

    print(
        f"Consultando predicción de afluencia "
        f"{park_name}..."
    )

    url = (
        f"https://queue-times.com/parks/"
        f"{park_id}/calendar/"
        f"{date_madrid[:4]}/"
        f"{date_madrid[5:7]}/"
        f"{date_madrid[8:10]}"
    )

    try:

        response = requests.get(
            url,
            headers=QUEUE_TIMES_HEADERS,
            timeout=30
        )

        response.raise_for_status()

        html = response.text

        # ----------------------------------------------------
        # BUSCAR "Nivel de multitud"
        # ----------------------------------------------------

        import re

        patterns = [
            r"Nivel de multitud[^0-9]{0,100}(\d{1,3})\s*%",
            r"crowd[^0-9]{0,100}(\d{1,3})\s*%",
            r"crowd[^:]*:\s*(\d{1,3})",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                html,
                re.IGNORECASE
            )

            if match:

                crowd = float(
                    match.group(1)
                )

                print(
                    f"Afluencia encontrada "
                    f"{park_name}: "
                    f"{crowd:.0f}%"
                )

                return crowd

        print(
            f"No se encontró el nivel de multitud "
            f"en Queue-Times para {park_name}"
        )

        return None

    except requests.HTTPError as error:

        print(
            f"ERROR HTTP obteniendo "
            f"afluencia {park_name}:",
            error
        )

        return None

    except Exception as error:

        print(
            f"ERROR obteniendo "
            f"afluencia {park_name}:",
            error
        )

        return None


# ============================================================
# ESTADÍSTICAS
# ============================================================

def get_observed_crowd(wait_times):

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


def calculate_statistics(rows):

    wait_times = []

    for row in rows:

        if not row["ride_open"]:
            continue

        value = row["wait_minutes"]

        if value is None:
            continue

        try:

            value = float(value)

            wait_times.append(
                value
            )

        except (
            TypeError,
            ValueError
        ):

            continue

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
            "operating": rides_operating,
            "with_wait": rides_with_wait,
            "observed": None,
        }

    return {
        "mean": round(
            mean(wait_times),
            1
        ),

        "median": round(
            median(wait_times),
            1
        ),

        "max": max(
            wait_times
        ),

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
    # FUERA DEL HORARIO DE PORTAVENTURA
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
    # QUEUE-TIMES
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
# AFLUENCIA POR PARQUE
# --------------------------------------------------------

    port_forecast = get_crowd_forecast(
        QUEUE_TIMES_PORTAVENTURA_ID,
        "PortAventura",
        date_madrid
    )

    ferrari_forecast = get_crowd_forecast(
        QUEUE_TIMES_FERRARI_ID,
        "Ferrari Land",
        date_madrid
    )

    print(
        "Predicción afluencia PortAventura:",
        port_forecast
    )

    print(
        "Predicción afluencia Ferrari Land:",
        ferrari_forecast
    )
    # --------------------------------------------------------
    # CONSTRUIR DATOS
    # --------------------------------------------------------

    collected = []

    for config in RIDES:

        park = config["park"]

        if park == "PortAventura":

            source = portaventura_data
            park_open = portaventura_open

        else:

            source = ferrari_data
            park_open = ferrari_land_open

        ride = find_ride(
            source,
            config
        )

        status = "SOURCE_NOT_AVAILABLE"
        ride_open = False
        wait_minutes = None
        last_updated = None
        api_name = ""

        if ride is not None:

            api_name = ride.get(
                "name",
                ""
            )

            last_updated = ride.get(
                "last_updated"
            )

            if not park_open:

                status = "CLOSED_PARK"

            else:

                is_operating = (
                    ride.get("is_open") is True
                )

                if is_operating:

                    status = "OPERATING"
                    ride_open = True

                    wait_minutes = ride.get(
                        "wait_time"
                    )

                else:

                    status = "CLOSED"

        collected.append(
            {
                "park": park,
                "code": config["code"],
                "ride": config["name"],
                "api_name": api_name,
                "ride_id": config["id"],
                "status": status,
                "ride_open": ride_open,
                "wait_minutes": wait_minutes,
                "last_updated": last_updated,
            }
        )
    # --------------------------------------------------------
    # ESTADÍSTICAS
    # --------------------------------------------------------

    port_rows = [
        row
        for row in collected
        if row["park"] == "PortAventura"
    ]

    ferrari_rows = [
        row
        for row in collected
        if row["park"] == "Ferrari Land"
    ]

    port_stats = calculate_statistics(
        port_rows
    )

    ferrari_stats = calculate_statistics(
        ferrari_rows
    )

    # --------------------------------------------------------
    # MOSTRAR ESTADÍSTICAS
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
    # EXACTAMENTE 25 CAMPOS
    # --------------------------------------------------------

    rows = []

    for ride in collected:

        if ride["park"] == "PortAventura":

            stats = port_stats
            forecast = port_forecast

        else:

            stats = ferrari_stats
            forecast = ferrari_forecast

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
                forecast,

            "observed_crowd_index":
                stats["observed"],

            "queue_mean":
                stats["mean"],

            "queue_median":
                stats["median"],

            "queue_max":
                stats["max"],

            "rides_operating":
                stats["operating"],

            "rides_with_wait":
                stats["with_wait"],

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

        # Comprobación interna antes de guardar.
        if len(row) != len(FIELDNAMES):

            raise RuntimeError(
                "ERROR INTERNO: la fila de "
                f"{ride['park']} {ride['code']} "
                f"tiene {len(row)} campos "
                f"en vez de {len(FIELDNAMES)}."
            )

        rows.append(row)

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

    print(
        f"Columnas por fila: {len(FIELDNAMES)}"
    )

    return rows


# ============================================================
# VALIDACIÓN CSV
# ============================================================

def validate_existing_csv():

    if not os.path.exists(
        CSV_FILE
    ):

        return

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
    # VALIDAR CSV ANTES DE MODIFICARLO
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
            extrasaction="raise"
        )

        if not file_exists:

            writer.writeheader()

        for row in rows:

            writer.writerow(
                row
            )

    # --------------------------------------------------------
    # VALIDAR CSV COMPLETO DESPUÉS
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
