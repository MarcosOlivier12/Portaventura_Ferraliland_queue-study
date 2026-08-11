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

MADRID_TZ = ZoneInfo("Europe/Madrid")
UTC_TZ = ZoneInfo("UTC")

CSV_FILE = "data/queue_history.csv"

QUEUE_TIMES_BASE = "https://queue-times.com/parks"

PORTAVENTURA_QUEUE_ID = 19
FERRARI_LAND_QUEUE_ID = 277

HEADERS = {
    "User-Agent": "PortAventura-Queue-Study/1.0"
}

if API_KEY:
    HEADERS["x-api-key"] = API_KEY


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
# CAMPOS CSV
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
# HORARIOS
# ============================================================

def is_open(current_time, opening, closing):
    return opening <= current_time <= closing


# ============================================================
# QUEUE-TIMES
# ============================================================

def get_queue_times(park_id):

    url = (
        f"{QUEUE_TIMES_BASE}/"
        f"{park_id}/queue_times.json"
    )

    print(
        f"Consultando Queue-Times parque {park_id}..."
    )

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        rides = {}

        # Queue-Times puede devolver atracciones
        # directamente o dentro de lands.

        all_rides = []

        all_rides.extend(
            data.get("rides", [])
        )

        for land in data.get("lands", []):

            all_rides.extend(
                land.get("rides", [])
            )

        for ride in all_rides:

            ride_id = ride.get("id")

            ride_name = ride.get("name")

            if ride_id is None:
                continue

            if not ride_name:
                ride_name = ""

            is_operating = (
                ride.get("is_open") is True
            )

            rides[int(ride_id)] = {
                "id": ride_id,
                "name": ride_name,
                "status": (
                    "OPERATING"
                    if is_operating
                    else "CLOSED"
                ),
                "waitMinutes": ride.get(
                    "wait_time"
                ),
                "lastUpdated": ride.get(
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
# AFLUENCIA / CALENDARIO
# ============================================================

def get_crowd_forecast(park_id, date_madrid):

    url = (
        f"{QUEUE_TIMES_BASE}/"
        f"{park_id}/calendar/"
        f"{date_madrid.year}/"
        f"{date_madrid.month:02d}/"
        f"{date_madrid.day:02d}"
    )

    print(
        f"Consultando calendario Queue-Times "
        f"parque {park_id}..."
    )

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        # ----------------------------------------------------
        # Intentar localizar el porcentaje de afluencia.
        # Queue-Times puede devolver diferentes estructuras.
        # ----------------------------------------------------

        def find_crowd(obj):

            if isinstance(obj, dict):

                possible_keys = [
                    "crowd_percent",
                    "crowdPercent",
                    "crowd",
                    "percentage",
                    "percent",
                    "crowd_percentage",
                ]

                for key in possible_keys:

                    value = obj.get(key)

                    if isinstance(
                        value,
                        (int, float)
                    ):

                        if 0 <= value <= 100:
                            return value

                for value in obj.values():

                    result = find_crowd(value)

                    if result is not None:
                        return result

            elif isinstance(obj, list):

                for item in obj:

                    result = find_crowd(item)

                    if result is not None:
                        return result

            return None

        crowd = find_crowd(data)

        if crowd is not None:

            crowd = round(
                float(crowd),
                1
            )

            print(
                f"Afluencia encontrada parque "
                f"{park_id}: {crowd}%"
            )

            return crowd

        print(
            f"No se encontró porcentaje de "
            f"afluencia para parque {park_id}"
        )

    except Exception as error:

        print(
            f"ERROR obteniendo afluencia "
            f"del parque {park_id}: {error}"
        )

    return None


# ============================================================
# AFLUENCIA OBSERVADA
# ============================================================

def calculate_observed_crowd(wait_times):

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
# ESTADÍSTICAS POR PARQUE
# ============================================================

def calculate_park_stats(collected):

    wait_times = []

    for ride in collected:

        if (
            ride["ride_open"]
            and isinstance(
                ride["wait_minutes"],
                (int, float)
            )
        ):

            wait_times.append(
                float(
                    ride["wait_minutes"]
                )
            )

    rides_operating = sum(
        1
        for ride in collected
        if ride["ride_open"]
    )

    rides_with_wait = len(
        wait_times
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

    return {
        "queue_mean": queue_mean,
        "queue_median": queue_median,
        "queue_max": queue_max,
        "rides_operating": rides_operating,
        "rides_with_wait": rides_with_wait,
        "observed_crowd_index": observed_index,
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
        now_madrid.date()
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

    # --------------------------------------------------------
    # ESTADO DE PARQUES
    # --------------------------------------------------------

    portaventura_open = is_open(
        current_time,
        PORTAVENTURA_OPENING,
        PORTAVENTURA_CLOSING,
    )

    ferrari_land_open = is_open(
        current_time,
        FERRARI_OPENING,
        FERRARI_CLOSING,
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
    # SI NO HAY NINGÚN PARQUE ABIERTO
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
    # DATOS QUEUE-TIMES
    # --------------------------------------------------------

    portaventura_data = {}

    ferrari_data = {}

    if portaventura_open:

        portaventura_data = (
            get_queue_times(
                PORTAVENTURA_QUEUE_ID
            )
        )

    if ferrari_land_open:

        ferrari_data = (
            get_queue_times(
                FERRARI_LAND_QUEUE_ID
            )
        )

    # --------------------------------------------------------
    # AFLUENCIA
    # --------------------------------------------------------

    portaventura_forecast = None
    ferrari_forecast = None

    if portaventura_open:

        portaventura_forecast = (
            get_crowd_forecast(
                PORTAVENTURA_QUEUE_ID,
                date_madrid,
            )
        )

    if ferrari_land_open:

        ferrari_forecast = (
            get_crowd_forecast(
                FERRARI_LAND_QUEUE_ID,
                date_madrid,
            )
        )

    print(
        "Predicción afluencia PortAventura:",
        portaventura_forecast
    )

    print(
        "Predicción afluencia Ferrari Land:",
        ferrari_forecast
    )

    # --------------------------------------------------------
    # CONSTRUIR RESULTADOS
    # --------------------------------------------------------

    collected = []

    for config in RIDES:

        park = config["park"]

        ride_id = int(
            config["id"]
        )

        # Seleccionar la fuente correcta.
        if park == "PortAventura":

            park_is_open = (
                portaventura_open
            )

            live_data = (
                portaventura_data
            )

            crowd_forecast = (
                portaventura_forecast
            )

        else:

            park_is_open = (
                ferrari_land_open
            )

            live_data = (
                ferrari_data
            )

            crowd_forecast = (
                ferrari_forecast
            )

        ride = live_data.get(
            ride_id
        )

        # ----------------------------------------------------
        # PARQUE CERRADO
        # ----------------------------------------------------

        if not park_is_open:

            status = "CLOSED_PARK"

            ride_open = False

            wait_minutes = None

            last_updated = None

            api_name = ""

        # ----------------------------------------------------
        # FUENTE NO DISPONIBLE
        # ----------------------------------------------------

        elif ride is None:

            status = (
                "SOURCE_NOT_AVAILABLE"
            )

            ride_open = False

            wait_minutes = None

            last_updated = None

            api_name = ""

        # ----------------------------------------------------
        # DATOS DISPONIBLES
        # ----------------------------------------------------

        else:

            api_name = ride.get(
                "name",
                ""
            )

            status = ride.get(
                "status",
                "UNKNOWN"
            )

            last_updated = ride.get(
                "lastUpdated"
            )

            if status == "OPERATING":

                ride_open = True

                wait_minutes = ride.get(
                    "waitMinutes"
                )

            else:

                ride_open = False

                wait_minutes = None

        collected.append(
            {
                "park": park,
                "code": config["code"],
                "ride": config["name"],
                "api_name": api_name,
                "ride_id": ride_id,
                "status": status,
                "ride_open": ride_open,
                "wait_minutes": wait_minutes,
                "last_updated": last_updated,
                "crowd_forecast": crowd_forecast,
            }
        )

    # --------------------------------------------------------
    # ESTADÍSTICAS SEPARADAS
    # --------------------------------------------------------

    portaventura_collected = [
        ride
        for ride in collected
        if ride["park"] == "PortAventura"
    ]

    ferrari_collected = [
        ride
        for ride in collected
        if ride["park"] == "Ferrari Land"
    ]

    portaventura_stats = (
        calculate_park_stats(
            portaventura_collected
        )
    )

    ferrari_stats = (
        calculate_park_stats(
            ferrari_collected
        )
    )

    # --------------------------------------------------------
    # MOSTRAR ESTADÍSTICAS
    # --------------------------------------------------------

    print(
        "------------------------------------------"
    )

    for ride in collected:

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
        "PortAventura"
    )

    print(
        "Cola media:",
        portaventura_stats[
            "queue_mean"
        ]
    )

    print(
        "Mediana:",
        portaventura_stats[
            "queue_median"
        ]
    )

    print(
        "Máxima:",
        portaventura_stats[
            "queue_max"
        ]
    )

    print(
        "Atracciones operativas:",
        portaventura_stats[
            "rides_operating"
        ]
    )

    print(
        "Atracciones con cola:",
        portaventura_stats[
            "rides_with_wait"
        ]
    )

    print(
        "Índice de afluencia observado:",
        portaventura_stats[
            "observed_crowd_index"
        ]
    )

    print(
        "------------------------------------------"
    )

    print(
        "Ferrari Land"
    )

    print(
        "Cola media:",
        ferrari_stats[
            "queue_mean"
        ]
    )

    print(
        "Mediana:",
        ferrari_stats[
            "queue_median"
        ]
    )

    print(
        "Máxima:",
        ferrari_stats[
            "queue_max"
        ]
    )

    print(
        "Atracciones operativas:",
        ferrari_stats[
            "rides_operating"
        ]
    )

    print(
        "Atracciones con cola:",
        ferrari_stats[
            "rides_with_wait"
        ]
    )

    print(
        "Índice de afluencia observado:",
        ferrari_stats[
            "observed_crowd_index"
        ]
    )

    # --------------------------------------------------------
    # PREPARAR FILAS CSV
    # --------------------------------------------------------

    rows = []

    for ride in collected:

        if ride["park"] == "PortAventura":

            stats = portaventura_stats

        else:

            stats = ferrari_stats

        row = {

            "timestamp_utc":
                timestamp_utc,

            "timestamp_madrid":
                timestamp_madrid,

            "date_madrid":
                date_madrid.isoformat(),

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
                ride["crowd_forecast"],

            "observed_crowd_index":
                stats[
                    "observed_crowd_index"
                ],

            "queue_mean":
                stats[
                    "queue_mean"
                ],

            "queue_median":
                stats[
                    "queue_median"
                ],

            "queue_max":
                stats[
                    "queue_max"
                ],

            "rides_operating":
                stats[
                    "rides_operating"
                ],

            "rides_with_wait":
                stats[
                    "rides_with_wait"
                ],

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

        # ----------------------------------------------------
        # VALIDACIÓN DE COLUMNAS
        # ----------------------------------------------------

        if set(row.keys()) != set(
            FIELDNAMES
        ):

            missing = (
                set(FIELDNAMES)
                - set(row.keys())
            )

            extra = (
                set(row.keys())
                - set(FIELDNAMES)
            )

            raise RuntimeError(
                "Columnas incorrectas. "
                f"Faltan: {missing}. "
                f"Sobran: {extra}."
            )

        rows.append(row)

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
    # Comprobar que todas las filas tienen exactamente
    # las mismas columnas que FIELDNAMES.
    # --------------------------------------------------------

    for index, row in enumerate(rows, start=1):

        if len(row) != len(
            FIELDNAMES
        ):

            raise RuntimeError(
                f"La fila {index} tiene "
                f"{len(row)} columnas; "
                f"se esperaban "
                f"{len(FIELDNAMES)}."
            )

    file_exists = os.path.exists(
        CSV_FILE
    )

    # --------------------------------------------------------
    # Si el CSV existente tiene una estructura antigua,
    # no añadir datos incompatibles.
    # --------------------------------------------------------

    if file_exists:

        with open(
            CSV_FILE,
            "r",
            newline="",
            encoding="utf-8"
        ) as file:

            reader = csv.reader(
                file
            )

            existing_header = next(
                reader,
                None
            )

        if existing_header != FIELDNAMES:

            backup_file = (
                CSV_FILE
                + ".old"
            )

            print(
                "El CSV existente tiene "
                "una cabecera antigua."
            )

            print(
                f"Se crea copia en {backup_file}"
            )

            os.replace(
                CSV_FILE,
                backup_file
            )

            file_exists = False

    # --------------------------------------------------------
    # ESCRITURA
    # --------------------------------------------------------

    with open(
        CSV_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=FIELDNAMES,
            extrasaction="raise",
        )

        if not file_exists:

            writer.writeheader()

        writer.writerows(
            rows
        )

    # --------------------------------------------------------
    # VALIDACIÓN FINAL DEL CSV
    # --------------------------------------------------------

    with open(
        CSV_FILE,
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.reader(
            file
        )

        header = next(
            reader,
            None
        )

        if header != FIELDNAMES:

            raise RuntimeError(
                "La cabecera del CSV "
                "no coincide con FIELDNAMES."
            )

        for line_number, row in enumerate(
            reader,
            start=2
        ):

            if len(row) != len(
                FIELDNAMES
            ):

                raise RuntimeError(
                    f"CSV corrupto: "
                    f"línea {line_number} "
                    f"tiene {len(row)} "
                    f"columnas en vez de "
                    f"{len(FIELDNAMES)}."
                )

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
