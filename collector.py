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

PQT_BASE_URL = "https://api.parkqueuetimes.com/v1"
QUEUE_TIMES_BASE_URL = "https://queue-times.com/parks"

MADRID_TZ = ZoneInfo("Europe/Madrid")
UTC_TZ = ZoneInfo("UTC")

CSV_FILE = "data/queue_history.csv"

HEADERS = {
    "x-api-key": API_KEY,
    "User-Agent": "PortAventura-Queue-Study/1.0",
}

QUEUE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PortAventura-Queue-Study/1.0)"
}


# ============================================================
# HORARIOS FIJOS - HORA MADRID
# ============================================================

PORTAVENTURA_OPENING = time(10, 30)
PORTAVENTURA_CLOSING = time(23, 30)

FERRARI_OPENING = time(17, 0)
FERRARI_CLOSING = time(22, 0)


# ============================================================
# IDs DE QUEUE-TIMES
# ============================================================

QUEUE_TIMES_PARK_IDS = {
    "PortAventura": 19,
    "Ferrari Land": 277,
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
# PARK QUEUE TIMES API
# ============================================================

def pqt_get(endpoint):

    url = f"{PQT_BASE_URL}{endpoint}"

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
                "Error desconocido de ParkQueueTimes"
            )
        )

    return result["data"]


# ============================================================
# BUSCAR IDs DE PARK QUEUE TIMES
# ============================================================

def get_pqt_park_ids():

    print(
        "Consultando lista de parques de ParkQueueTimes..."
    )

    try:

        data = pqt_get("/parks")

        if not isinstance(data, list):
            raise RuntimeError(
                "Respuesta /parks no es una lista"
            )

        ids = {
            "PortAventura": None,
            "Ferrari Land": None,
        }

        for park in data:

            name = str(
                park.get("name", "")
            ).strip().lower()

            if name in (
                "portaventura",
                "portaventura park",
                "portaventura world",
            ):

                ids["PortAventura"] = park.get(
                    "id"
                )

            elif "ferrari land" in name:

                ids["Ferrari Land"] = park.get(
                    "id"
                )

        print(
            "ID ParkQueueTimes PortAventura:",
            ids["PortAventura"]
        )

        print(
            "ID ParkQueueTimes Ferrari Land:",
            ids["Ferrari Land"]
        )

        return ids

    except Exception as error:

        print(
            "ERROR obteniendo parques ParkQueueTimes:",
            error
        )

        return {
            "PortAventura": None,
            "Ferrari Land": None,
        }


# ============================================================
# PREDICCIÓN DE AFLUENCIA
# ============================================================

def get_crowd_prediction(
    park_name,
    park_id,
    date_madrid
):

    if park_id is None:

        print(
            f"No existe ID ParkQueueTimes para "
            f"{park_name}"
        )

        return None

    print(
        f"Consultando calendario ParkQueueTimes "
        f"{park_name}..."
    )

    try:

        data = pqt_get(
            f"/parks/{park_id}/calendar"
        )

        days = data.get(
            "days",
            []
        )

        for day in days:

            if day.get(
                "date"
            ) == date_madrid:

                crowd = day.get(
                    "crowdPercent"
                )

                print(
                    f"Afluencia encontrada "
                    f"{park_name}: {crowd}%"
                )

                return crowd

        print(
            f"No se encontró {date_madrid} "
            f"en el calendario de {park_name}"
        )

    except Exception as error:

        print(
            f"ERROR obteniendo afluencia "
            f"{park_name}: {error}"
        )

    return None


# ============================================================
# QUEUE-TIMES
# ============================================================

def get_queue_times(
    park_name
):

    park_id = QUEUE_TIMES_PARK_IDS[
        park_name
    ]

    url = (
        f"{QUEUE_TIMES_BASE_URL}/"
        f"{park_id}/queue_times.json"
    )

    print(
        f"Consultando Queue-Times "
        f"{park_name}..."
    )

    try:

        response = requests.get(
            url,
            headers=QUEUE_HEADERS,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        rides = {}

        all_rides = []

        all_rides.extend(
            data.get(
                "rides",
                []
            )
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

        for ride in all_rides:

            ride_name = ride.get(
                "name"
            )

            if not ride_name:
                continue

            ride_id = ride.get(
                "id"
            )

            rides[ride_id] = {

                "id":
                    ride_id,

                "name":
                    ride_name,

                "status":
                    (
                        "OPERATING"
                        if ride.get(
                            "is_open"
                        ) is True
                        else "CLOSED"
                    ),

                "waitMinutes":
                    ride.get(
                        "wait_time"
                    ),

                "lastUpdated":
                    ride.get(
                        "last_updated"
                    ),
            }

        print(
            f"Queue-Times {park_name}: "
            f"recibidas {len(rides)} atracciones"
        )

        return rides

    except Exception as error:

        print(
            f"ERROR consultando Queue-Times "
            f"{park_name}: {error}"
        )

        return {}


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
    # SI AMBOS ESTÁN CERRADOS
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
    # OBTENER COLAS
    # --------------------------------------------------------

    portaventura_live = get_queue_times(
        "PortAventura"
    )

    ferrari_live = get_queue_times(
        "Ferrari Land"
    )

    # --------------------------------------------------------
    # IDs DE PARK QUEUE TIMES
    # --------------------------------------------------------

    pqt_ids = get_pqt_park_ids()

    # --------------------------------------------------------
    # AFLUENCIA PREDICHA
    # --------------------------------------------------------

    crowd_portaventura = get_crowd_prediction(
        "PortAventura",
        pqt_ids["PortAventura"],
        date_madrid
    )

    crowd_ferrari = get_crowd_prediction(
        "Ferrari Land",
        pqt_ids["Ferrari Land"],
        date_madrid
    )

    print(
        "Predicción afluencia PortAventura:",
        crowd_portaventura
    )

    print(
        "Predicción afluencia Ferrari Land:",
        crowd_ferrari
    )

    # --------------------------------------------------------
    # MAPA DE FUENTES
    # --------------------------------------------------------

    live_sources = {
        "PortAventura":
            portaventura_live,

        "Ferrari Land":
            ferrari_live,
    }

    park_open_states = {
        "PortAventura":
            portaventura_open,

        "Ferrari Land":
            ferrari_land_open,
    }

    crowd_forecasts = {
        "PortAventura":
            crowd_portaventura,

        "Ferrari Land":
            crowd_ferrari,
    }

    # --------------------------------------------------------
    # RECOPILACIÓN
    # --------------------------------------------------------

    collected = []

    wait_times_by_park = {
        "PortAventura": [],
        "Ferrari Land": [],
    }

    # --------------------------------------------------------
    # PRIMERO: OBTENER ESTADOS DE TODAS LAS ATRACCIONES
    # --------------------------------------------------------

    for ride_config in RIDES:

        park = ride_config["park"]

        ride_id = ride_config["id"]

        live_data = live_sources[
            park
        ]

        park_is_open = park_open_states[
            park
        ]

        ride = live_data.get(
            ride_id
        )

        # ----------------------------------------------------
        # ATRACCIÓN NO ENCONTRADA
        # ----------------------------------------------------

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

            # ------------------------------------------------
            # PARQUE CERRADO
            # ------------------------------------------------

            if not park_is_open:

                status = "CLOSED_PARK"

                ride_open = False

                wait_minutes = None

            # ------------------------------------------------
            # PARQUE ABIERTO + ATRACCIÓN OPERATIVA
            # ------------------------------------------------

            elif api_status == "OPERATING":

                status = "OPERATING"

                ride_open = True

            # ------------------------------------------------
            # ATRACCIÓN NO OPERATIVA
            # ------------------------------------------------

            else:

                status = api_status

                ride_open = False

                wait_minutes = None

        # ----------------------------------------------------
        # COLA VÁLIDA
        # ----------------------------------------------------

        if (
            ride_open
            and isinstance(
                wait_minutes,
                (int, float)
            )
        ):

            wait_times_by_park[
                park
            ].append(
                float(
                    wait_minutes
                )
            )

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

    # --------------------------------------------------------
    # ESTADÍSTICAS POR PARQUE
    # --------------------------------------------------------

    statistics = {}

    for park in (
        "PortAventura",
        "Ferrari Land"
    ):

        waits = wait_times_by_park[
            park
        ]

        if waits:

            queue_mean = round(
                mean(waits),
                1
            )

            queue_median = round(
                median(waits),
                1
            )

            queue_max = max(
                waits
            )

            observed_crowd = (
                calculate_observed_crowd(
                    waits
                )
            )

        else:

            queue_mean = None

            queue_median = None

            queue_max = None

            observed_crowd = None

        rides_operating = sum(
            1
            for ride in collected
            if (
                ride["park"] == park
                and ride["ride_open"]
            )
        )

        rides_with_wait = len(
            waits
        )

        statistics[
            park
        ] = {

            "queue_mean":
                queue_mean,

            "queue_median":
                queue_median,

            "queue_max":
                queue_max,

            "observed_crowd":
                observed_crowd,

            "rides_operating":
                rides_operating,

            "rides_with_wait":
                rides_with_wait,
        }

    # --------------------------------------------------------
    # MOSTRAR ESTADÍSTICAS
    # --------------------------------------------------------

    for park in (
        "PortAventura",
        "Ferrari Land"
    ):

        stats = statistics[
            park
        ]

        print(
            "------------------------------------------"
        )

        print(
            park
        )

        print(
            "Cola media:",
            stats["queue_mean"]
        )

        print(
            "Mediana:",
            stats["queue_median"]
        )

        print(
            "Máxima:",
            stats["queue_max"]
        )

        print(
            "Atracciones operativas:",
            stats["rides_operating"]
        )

        print(
            "Atracciones con cola:",
            stats["rides_with_wait"]
        )

        print(
            "Índice de afluencia observado:",
            stats["observed_crowd"]
        )

    print(
        "------------------------------------------"
    )

    # --------------------------------------------------------
    # MOSTRAR ATRACCIONES
    # --------------------------------------------------------

    for ride in collected:

        print(
            f"{ride['park']} | "
            f"{ride['code']} | "
            f"{ride['status']} | "
            f"{ride['wait_minutes']} min"
        )

    # --------------------------------------------------------
    # CREAR FILAS CSV
    # --------------------------------------------------------

    rows = []

    for ride in collected:

        park = ride["park"]

        stats = statistics[
            park
        ]

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
                crowd_forecasts[park],

            "observed_crowd_index":
                stats["observed_crowd"],

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

            "park_open":
                park_open_states[park],

            "park_opening":
                (
                    "10:30"
                    if park == "PortAventura"
                    else "17:00"
                ),

            "park_closing":
                (
                    "23:30"
                    if park == "PortAventura"
                    else "22:00"
                ),
        }

        rows.append(
            row
        )

    print(
        "------------------------------------------"
    )

    print(
        f"Filas preparadas: {len(rows)}"
    )

    return rows


# ============================================================
# CSV
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

    "park_open",
    "park_opening",
    "park_closing",
]


# ============================================================
# VALIDAR CSV EXISTENTE
# ============================================================

def validate_existing_csv():

    if not os.path.exists(
        CSV_FILE
    ):

        return True

    with open(
        CSV_FILE,
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.reader(
            file
        )

        rows = list(
            reader
        )

    if not rows:
        return True

    header = rows[0]

    if header != FIELDNAMES:

        raise RuntimeError(
            "La cabecera del CSV no coincide "
            "con la estructura actual de 22 columnas. "
            "Borra data/queue_history.csv y vuelve "
            "a ejecutar el workflow una vez."
        )

    for line_number, row in enumerate(
        rows[1:],
        start=2
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


# ============================================================
# GUARDAR
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
            fieldnames=FIELDNAMES
        )

        if not file_exists:

            writer.writeheader()

        for row in rows:

            if len(row) != len(
                FIELDNAMES
            ):

                raise RuntimeError(
                    "Una fila generada no "
                    "tiene exactamente 22 campos."
                )

            writer.writerow(
                row
            )

    print(
        f"Guardados {len(rows)} registros."
    )

    # --------------------------------------------------------
    # VALIDACIÓN FINAL
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

        all_rows = list(
            reader
        )

    for line_number, row in enumerate(
        all_rows,
        start=1
    ):

        if len(row) != len(
            FIELDNAMES
        ):

            raise RuntimeError(
                f"CSV corrupto después de guardar: "
                f"línea {line_number} tiene "
                f"{len(row)} columnas."
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
