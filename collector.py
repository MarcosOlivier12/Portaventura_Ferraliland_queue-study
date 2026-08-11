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

PARK_IDS = {
    "PortAventura": 19,
    "Ferrari Land": 277,
}

QUEUE_TIMES_URL = "https://queue-times.com/parks"

MADRID_TZ = ZoneInfo("Europe/Madrid")
UTC_TZ = ZoneInfo("UTC")

CSV_FILE = "data/queue_history.csv"

HEADERS = {
    "x-api-key": API_KEY,
    "User-Agent": "PortAventura-Queue-Study/2.0",
}


# ============================================================
# HORARIOS - HORA MADRID
# ============================================================

PORTAVENTURA_OPENING = time(10, 30)
PORTAVENTURA_CLOSING = time(23, 30)

FERRARI_OPENING = time(17, 0)
FERRARI_CLOSING = time(22, 0)


# ============================================================
# ATRACCIONES
# ============================================================

RIDES = [

    # ========================================================
    # PORTAVENTURA
    # ========================================================

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


    # ========================================================
    # FERRARI LAND
    # ========================================================

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
# NORMALIZACIÓN DE NOMBRES
# ============================================================

def normalize_name(name):

    if not name:
        return ""

    name = str(name).lower().strip()

    replacements = {
        "-": " ",
        "_": " ",
        "–": " ",
        "—": " ",
        "'": "",
        ".": "",
        ",": "",
        "(": "",
        ")": "",
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    # Eliminar dobles espacios
    name = " ".join(name.split())

    return name


# ============================================================
# ALIAS DE ATRACCIONES
# ============================================================

RIDE_ALIASES = {

    "Uncharted": [
        "uncharted",
    ],

    "Street Mission": [
        "street mission",
        "sesame street mission",
    ],

    "Shambhala": [
        "shambhala",
    ],

    "Dragon Khan": [
        "dragon khan",
    ],

    "Furius Baco": [
        "furius baco",
    ],

    "Hurakan Condor": [
        "hurakan condor",
    ],

    "Stampida": [
        "stampida",
    ],
    "Tutuki Splash": [
        "tutuki splash",
    ],

    "El Diablo - Tren De La Mina": [
        "el diablo tren de la mina",
        "el diablo",
        "tren de la mina",
    ],

    "Silver River Flume": [
        "silver river flume",
    ],

    "Templo del Fuego": [
        "templo del fuego",
    ],

    "Red Force": [
        "red force",
    ],

    "Thrill Towers": [
        "thrill towers",
    ],

    "Flying Dreams": [
        "flying dreams",
    ],
}


# ============================================================
# API QUEUE-TIMES
# ============================================================

def get_queue_times(park_id):

    url = (
        f"{QUEUE_TIMES_URL}/"
        f"{park_id}/queue_times.json"
    )

    try:

        response = requests.get(
            url,
            headers={
                "User-Agent":
                    "Mozilla/5.0 "
                    "(compatible; "
                    "PortAventuraQueueStudy/2.0)"
            },
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        all_rides = []

        # Algunas respuestas contienen rides directamente
        all_rides.extend(
            data.get("rides", [])
        )

        # Otras contienen lands
        for land in data.get("lands", []):

            all_rides.extend(
                land.get("rides", [])
            )

        rides = {}

        for ride in all_rides:

            name = ride.get("name")

            if not name:
                continue

            normalized = normalize_name(name)

            rides[normalized] = {
                "id": ride.get("id"),
                "name": name,
                "is_open": ride.get("is_open"),
                "wait_time": ride.get("wait_time"),
                "last_updated": ride.get(
                    "last_updated"
                ),
            }

        print(
            f"Queue-Times parque {park_id}: "
            f"recibidas {len(rides)} atracciones"
        )

        return rides

    except Exception as error:

        print(
            f"ERROR Queue-Times parque "
            f"{park_id}: {error}"
        )

        return {}


# ============================================================
# BUSCAR ATRACCIÓN
# ============================================================

def find_ride(
    ride_config,
    queue_data
):

    configured_name = ride_config["name"]

    # --------------------------------------------------------
    # 1. Buscar por ID
    # --------------------------------------------------------

    configured_id = ride_config.get("id")

    if configured_id is not None:

        for ride in queue_data.values():

            if ride.get("id") == configured_id:

                return ride


    # --------------------------------------------------------
    # 2. Buscar por nombre exacto
    # --------------------------------------------------------

    normalized_config =
        normalize_name(
            configured_name
        )

    if normalized_config in queue_data:

        return queue_data[
            normalized_config
        ]


    # --------------------------------------------------------
    # 3. Buscar mediante alias
    # --------------------------------------------------------

    aliases = RIDE_ALIASES.get(
        configured_name,
        []
    )

    for alias in aliases:

        normalized_alias = normalize_name(
            alias
        )

        if normalized_alias in queue_data:

            return queue_data[
                normalized_alias
            ]


    # --------------------------------------------------------
    # 4. Comparación parcial
    # --------------------------------------------------------

    for queue_name, ride in queue_data.items():

        if (
            normalized_config in queue_name
            or queue_name in normalized_config
        ):

            return ride


    return None


# ============================================================
# CALENDARIO / AFLUENCIA
# ============================================================

def get_crowd_forecast(
    park_id,
    date_madrid
):

    print(
        f"Consultando calendario Queue-Times "
        f"parque {park_id}..."
    )

    url = (
        f"{QUEUE_TIMES_URL}/"
        f"{park_id}/calendar/"
        f"{date_madrid}"
    )

    try:

        response = requests.get(
            url,
            headers={
                "User-Agent":
                    "Mozilla/5.0 "
                    "(compatible; "
                    "PortAventuraQueueStudy/2.0)"
            },
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        # ----------------------------------------------------
        # Intentar diferentes formatos
        # ----------------------------------------------------

        candidates = []

        if isinstance(data, list):

            candidates = data

        elif isinstance(data, dict):

            for key in [
                "data",
                "days",
                "calendar",
            ]:

                value = data.get(key)

                if isinstance(value, list):

                    candidates.extend(
                        value
                    )

        # ----------------------------------------------------
        # Buscar fecha
        # ----------------------------------------------------

        for item in candidates:

            if not isinstance(item, dict):
                continue

            item_date = (
                item.get("date")
                or item.get("day")
                or item.get("datetime")
            )

            if item_date:

                item_date = str(
                    item_date
                )[:10]

            if item_date == date_madrid:

                value = (
                    item.get("crowd")
                    or item.get("crowdPercent")
                    or item.get("crowd_percent")
                    or item.get("percentage")
                )

                if value is not None:

                    try:

                        value = float(value)

                        print(
                            f"Afluencia encontrada "
                            f"parque {park_id}: "
                            f"{value}%"
                        )

                        return value

                    except ValueError:
                        pass


        # ----------------------------------------------------
        # Si la respuesta es directamente un objeto del día
        # ----------------------------------------------------

        if isinstance(data, dict):

            for key in [
                "crowd",
                "crowdPercent",
                "crowd_percent",
                "percentage",
            ]:

                value = data.get(key)

                if value is not None:

                    try:

                        value = float(value)

                        print(
                            f"Afluencia encontrada "
                            f"parque {park_id}: "
                            f"{value}%"
                        )

                        return value

                    except ValueError:
                        pass


        print(
            f"No se encontró afluencia para "
            f"{date_madrid} en parque {park_id}"
        )

    except Exception as error:

        print(
            f"ERROR obteniendo afluencia "
            f"del parque {park_id}: "
            f"{error}"
        )

    return None


# ============================================================
# HORARIOS
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


    # ========================================================
    # ESTADO DE PARQUES
    # ========================================================

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


    # ========================================================
    # SI AMBOS CERRADOS
    # ========================================================

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


    # ========================================================
    # QUEUE-TIMES
    # ========================================================

    queue_portaventura = {}

    queue_ferrari = {}

    if portaventura_open:

        print(
            "Consultando Queue-Times "
            "parque 19..."
        )

        queue_portaventura = get_queue_times(
            PARK_IDS["PortAventura"]
        )

    if ferrari_land_open:

        print(
            "Consultando Queue-Times "
            "parque 277..."
        )

        queue_ferrari = get_queue_times(
            PARK_IDS["Ferrari Land"]
        )


    # ========================================================
    # AFLUENCIA
    # ========================================================

    print(
        "Consultando calendario Queue-Times..."
    )

    crowd_portaventura = None

    crowd_ferrari = None

    if portaventura_open:

        crowd_portaventura = (
            get_crowd_forecast(
                PARK_IDS["PortAventura"],
                date_madrid
            )
        )

    if ferrari_land_open:

        crowd_ferrari = (
            get_crowd_forecast(
                PARK_IDS["Ferrari Land"],
                date_madrid
            )
        )

    print(
        "Predicción afluencia PortAventura:",
        crowd_portaventura
    )

    print(
        "Predicción afluencia Ferrari Land:",
        crowd_ferrari
    )


    # ========================================================
    # DATOS POR PARQUE
    # ========================================================

    park_wait_times = {
        "PortAventura": [],
        "Ferrari Land": [],
    }

    collected = []


    # ========================================================
    # ATRACCIONES
    # ========================================================

    for ride_config in RIDES:

        park = ride_config["park"]

        code = ride_config["code"]

        configured_name = ride_config["name"]

        ride_id = ride_config["id"]


        # ----------------------------------------------------
        # Seleccionar fuente correcta
        # ----------------------------------------------------

        if park == "PortAventura":

            park_is_open = (
                portaventura_open
            )

            queue_data = (
                queue_portaventura
            )

        else:

            park_is_open = (
                ferrari_land_open
            )

            queue_data = (
                queue_ferrari
            )


        # ----------------------------------------------------
        # Parque cerrado
        # ----------------------------------------------------

        if not park_is_open:

            collected.append(
                {
                    "park": park,
                    "code": code,
                    "ride": configured_name,
                    "api_name": "",
                    "ride_id": ride_id,
                    "status": "CLOSED_PARK",
                    "ride_open": False,
                    "wait_minutes": None,
                    "last_updated": None,
                }
            )

            print(
                f"{park} | {code} | "
                f"CLOSED_PARK | None min"
            )

            continue


        # ----------------------------------------------------
        # Buscar atracción
        # ----------------------------------------------------

        ride = find_ride(
            ride_config,
            queue_data
        )


        if ride is None:

            status = (
                "SOURCE_NOT_AVAILABLE"
            )

            ride_open = False

            wait_minutes = None

            last_updated = None

            api_name = ""

        else:

            api_name = ride.get(
                "name",
                ""
            )

            is_ride_open = (
                ride.get("is_open")
                is True
            )

            wait_minutes = ride.get(
                "wait_time"
            )

            last_updated = ride.get(
                "last_updated"
            )


            # ------------------------------------------------
            # ATRACCIÓN ABIERTA
            # ------------------------------------------------

            if is_ride_open:

                status = "OPERATING"

                ride_open = True

                if isinstance(
                    wait_minutes,
                    (int, float)
                ):

                    park_wait_times[
                        park
                    ].append(
                        float(
                            wait_minutes
                        )
                    )

            else:

                status = "CLOSED"

                ride_open = False

                wait_minutes = None


        collected.append(
            {
                "park": park,
                "code": code,
                "ride": configured_name,
                "api_name": api_name,
                "ride_id": ride_id,
                "status": status,
                "ride_open": ride_open,
                "wait_minutes": wait_minutes,
                "last_updated": last_updated,
            }
        )

        print(
            f"{park} | {code} | "
            f"{status} | "
            f"{wait_minutes} min"
        )


    # ========================================================
    # ESTADÍSTICAS POR PARQUE
    # ========================================================

    statistics = {}


    for park in [
        "PortAventura",
        "Ferrari Land",
    ]:

        wait_times = (
            park_wait_times[park]
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

            observed_index = (
                calculate_observed_crowd(
                    wait_times
                )
            )

        else:

            queue_mean = None
            queue_median = None
            queue_max = None
            observed_index = None


        rides_operating = sum(
            1
            for ride in collected
            if (
                ride["park"] == park
                and ride["ride_open"]
            )
        )

        rides_with_wait = len(
            wait_times
        )


        statistics[park] = {
            "queue_mean": queue_mean,
            "queue_median": queue_median,
            "queue_max": queue_max,
            "observed_index":
                observed_index,
            "rides_operating":
                rides_operating,
            "rides_with_wait":
                rides_with_wait,
        }


        print(
            "------------------------------------------"
        )

        print(
            park
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
            observed_index
        )


    print(
        "------------------------------------------"
    )


    # ========================================================
    # CREAR FILAS CSV
    # ========================================================

    rows = []

    for ride in collected:

        park = ride["park"]

        stats = statistics[park]


        if park == "PortAventura":

            crowd_forecast = (
                crowd_portaventura
            )

        else:

            crowd_forecast = (
                crowd_ferrari
            )


        row = {

            "timestamp_utc":
                timestamp_utc,

            "timestamp_madrid":
                timestamp_madrid,

            "date_madrid":
                date_madrid,

            "park":
                park,

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
                stats["observed_index"],

            "queue_mean":
                stats["queue_mean"],

            "queue_median":
                stats["queue_median"],

            "queue_max":
                stats["queue_max"],

            "rides_operating":
                stats["rides_operating"],

            "rides_with_wait":
                stats["rides_with_wait"],

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

        rows.append(row)


    print(
        f"Filas preparadas: {len(rows)}"
    )

    print(
        "Columnas por fila:",
        len(rows[0]) if rows else 0
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


    # ========================================================
    # VALIDACIÓN
    # ========================================================

    expected_columns = len(
        fieldnames
    )

    for index, row in enumerate(rows):

        row_columns = len(row)

        if row_columns != expected_columns:

            raise ValueError(
                f"Fila {index + 1} tiene "
                f"{row_columns} columnas; "
                f"se esperaban "
                f"{expected_columns}."
            )


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
            fieldnames=fieldnames,
            extrasaction="ignore"
        )


        if not file_exists:

            writer.writeheader()


        writer.writerows(
            rows
        )


    print(
        f"Guardados {len(rows)} registros."
    )

    print(
        f"Estructura validada: "
        f"{expected_columns} columnas."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    try:

        rows = collect()

        save_rows(rows)

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
