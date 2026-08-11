import csv
import os
import shutil
import requests

from datetime import datetime, time
from zoneinfo import ZoneInfo
from statistics import mean, median


# ============================================================
# CONFIGURACIÓN
# ============================================================

API_KEY = os.environ["PARK_QUEUE_TIMES_API_KEY"]

MADRID_TZ = ZoneInfo("Europe/Madrid")
UTC_TZ = ZoneInfo("UTC")

CSV_FILE = "data/queue_history.csv"

HEADERS = {
    "x-api-key": API_KEY,
    "User-Agent": "PortAventura-Queue-Study/2.0",
}

QUEUE_TIMES_HEADERS = {
    "User-Agent": "PortAventura-Queue-Study/2.0",
    "Accept": "application/json",
}


# ============================================================
# ID DE LOS PARQUES EN QUEUE-TIMES
# ============================================================

QUEUE_TIMES_PARKS = {
    "PortAventura": 19,
    "Ferrari Land": 277,
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

    "park_open",

    "park_opening",
    "park_closing",
]


# ============================================================
# NORMALIZACIÓN DE NOMBRES
# ============================================================

def normalize_name(name):

    if not name:
        return ""

    value = str(name).lower().strip()

    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
        "-": " ",
        "_": " ",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = " ".join(value.split())

    return value


# ============================================================
# HORARIOS
# ============================================================

def is_open(current_time, opening, closing):

    return opening <= current_time <= closing


def get_park_hours(park):

    if park == "PortAventura":

        return (
            PORTAVENTURA_OPENING,
            PORTAVENTURA_CLOSING,
        )

    return (
        FERRARI_OPENING,
        FERRARI_CLOSING,
    )


# ============================================================
# PARK QUEUE TIMES API
# ============================================================

def park_api_get(endpoint):

    url = (
        "https://api.parkqueuetimes.com/v1"
        + endpoint
    )

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
# BUSCAR ID DE CADA PARQUE EN PARKQUEUETIMES
# ============================================================

def get_parkqueuetimes_ids():

    print(
        "Consultando lista de parques de ParkQueueTimes..."
    )

    try:

        data = park_api_get("/parks")

        result = {}

        for park in data:

            park_name = park.get(
                "name",
                ""
            )

            normalized = normalize_name(
                park_name
            )

            if normalized == normalize_name(
                "PortAventura"
            ):

                result["PortAventura"] = park.get(
                    "id"
                )

            elif normalized == normalize_name(
                "Ferrari Land"
            ):

                result["Ferrari Land"] = park.get(
                    "id"
                )

        print(
            "ID ParkQueueTimes PortAventura:",
            result.get("PortAventura")
        )

        print(
            "ID ParkQueueTimes Ferrari Land:",
            result.get("Ferrari Land")
        )

        return result

    except Exception as error:

        print(
            "ERROR buscando parques ParkQueueTimes:",
            error
        )

        return {}


# ============================================================
# PREDICCIÓN DE AFLUENCIA
# ============================================================

def get_crowd_forecast(
    park_id,
    park_name,
    date_madrid
):

    if not park_id:

        print(
            f"No existe ID de ParkQueueTimes para {park_name}"
        )

        return None

    print(
        f"Consultando calendario "
        f"ParkQueueTimes {park_name}..."
    )

    try:

        data = park_api_get(
            f"/parks/{park_id}/calendar"
        )

        days = data.get(
            "days",
            []
        )

        for day in days:

            if day.get("date") == date_madrid:

                crowd = day.get(
                    "crowdPercent"
                )

                print(
                    f"Afluencia {park_name}:",
                    crowd
                )

                return crowd

        print(
            f"No se encontró {date_madrid} "
            f"en el calendario de {park_name}"
        )

    except Exception as error:

        print(
            f"ERROR obteniendo afluencia "
            f"{park_name}:",
            error
        )

    return None


# ============================================================
# QUEUE-TIMES
# ============================================================

def get_queue_times(park_name):

    park_id = QUEUE_TIMES_PARKS[
        park_name
    ]

    print(
        f"Consultando Queue-Times "
        f"parque {park_id}..."
    )

    url = (
        f"https://queue-times.com/parks/"
        f"{park_id}/queue_times.json"
    )

    try:

        response = requests.get(
            url,
            headers=QUEUE_TIMES_HEADERS,
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

            rides[
                normalize_name(
                    ride_name
                )
            ] = {
                "name":
                    ride_name,

                "id":
                    ride.get(
                        "id"
                    ),

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
            f"Queue-Times parque {park_id}: "
            f"recibidas {len(rides)} atracciones"
        )

        return rides

    except Exception as error:

        print(
            f"ERROR Queue-Times "
            f"{park_name}:",
            error
        )

        return {}


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
# MAPEAR ATRACCIONES
# ============================================================

def find_ride(
    ride_config,
    queue_data
):

    wanted = normalize_name(
        ride_config["name"]
    )

    # Coincidencia exacta
    if wanted in queue_data:

        return queue_data[
            wanted
        ]

    # Coincidencia por nombre parcial
    for name, ride in queue_data.items():

        if (
            wanted in name
            or name in wanted
        ):

            return ride

    return None


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

    # --------------------------------------------------------
    # PARQUES ABIERTOS
    # --------------------------------------------------------

    portaventura_open = is_open(
        current_time,
        PORTAVENTURA_OPENING,
        PORTAVENTURA_CLOSING
    )

    ferrari_open = is_open(
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
        if ferrari_open
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
    # OBTENER COLAS
    # --------------------------------------------------------

    portaventura_queue = get_queue_times(
        "PortAventura"
    )

    ferrari_queue = {}

    if ferrari_open:

        ferrari_queue = get_queue_times(
            "Ferrari Land"
        )

    # --------------------------------------------------------
    # IDS PARA AFLUENCIA
    # --------------------------------------------------------

    park_ids = get_parkqueuetimes_ids()

    portaventura_crowd = get_crowd_forecast(
        park_ids.get(
            "PortAventura"
        ),
        "PortAventura",
        date_madrid
    )

    ferrari_crowd = None

    if ferrari_open:

        ferrari_crowd = get_crowd_forecast(
            park_ids.get(
                "Ferrari Land"
            ),
            "Ferrari Land",
            date_madrid
        )

    print(
        "Predicción afluencia PortAventura:",
        portaventura_crowd
    )

    print(
        "Predicción afluencia Ferrari Land:",
        ferrari_crowd
    )

    # --------------------------------------------------------
    # PROCESAR POR PARQUE
    # --------------------------------------------------------

    collected = []

    statistics = {}

    for park_name in [
        "PortAventura",
        "Ferrari Land",
    ]:

        if park_name == "PortAventura":

            park_open = portaventura_open
            queue_data = portaventura_queue
            crowd_forecast = portaventura_crowd

        else:

            park_open = ferrari_open
            queue_data = ferrari_queue
            crowd_forecast = ferrari_crowd

        park_rides = []

        wait_times = []

        # ----------------------------------------------------
        # ATRACCIONES
        # ----------------------------------------------------

        for ride_config in RIDES:

            if ride_config["park"] != park_name:

                continue

            ride = find_ride(
                ride_config,
                queue_data
            )

            # -----------------------------------------------
            # NO HAY DATOS
            # -----------------------------------------------

            if ride is None:

                if not park_open:

                    status = "CLOSED_PARK"

                else:

                    status = "SOURCE_NOT_AVAILABLE"

                ride_open = False

                wait_minutes = None

                api_name = ""

                last_updated = None

            else:

                api_name = ride.get(
                    "name",
                    ""
                )

                last_updated = ride.get(
                    "lastUpdated"
                )

                api_status = ride.get(
                    "status",
                    "UNKNOWN"
                )

                wait_minutes = ride.get(
                    "waitMinutes"
                )

                # -------------------------------------------
                # PARQUE CERRADO
                # -------------------------------------------

                if not park_open:

                    status = "CLOSED_PARK"

                    ride_open = False

                    wait_minutes = None

                # -------------------------------------------
                # ATRACCIÓN OPERATIVA
                # -------------------------------------------

                elif api_status == "OPERATING":

                    status = "OPERATING"

                    ride_open = True

                # -------------------------------------------
                # ATRACCIÓN CERRADA / DOWN
                # -------------------------------------------

                else:

                    status = api_status

                    ride_open = False

                    wait_minutes = None

                # -------------------------------------------
                # COLA VÁLIDA
                # -------------------------------------------

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

            park_rides.append(
                {
                    "config":
                        ride_config,

                    "park":
                        park_name,

                    "api_name":
                        api_name,

                    "status":
                        status,

                    "ride_open":
                        ride_open,

                    "wait_minutes":
                        wait_minutes,

                    "last_updated":
                        last_updated,

                    "crowd_forecast":
                        crowd_forecast,
                }
            )

        # ----------------------------------------------------
        # ESTADÍSTICAS
        # ----------------------------------------------------

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
            for ride in park_rides
            if ride["ride_open"]
        )

        rides_with_wait = len(
            wait_times
        )

        statistics[
            park_name
        ] = {
            "queue_mean":
                queue_mean,

            "queue_median":
                queue_median,

            "queue_max":
                queue_max,

            "observed_index":
                observed_index,

            "rides_operating":
                rides_operating,

            "rides_with_wait":
                rides_with_wait,
        }

        # ----------------------------------------------------
        # MOSTRAR RESULTADOS
        # ----------------------------------------------------

        for ride in park_rides:

            config = ride["config"]

            print(
                f"{park_name} | "
                f"{config['code']} | "
                f"{ride['status']} | "
                f"{ride['wait_minutes']} min"
            )

            collected.append(
                ride
            )

    # --------------------------------------------------------
    # ESTADÍSTICAS EN CONSOLA
    # --------------------------------------------------------

    print(
        "------------------------------------------"
    )

    for park_name in [
        "PortAventura",
        "Ferrari Land",
    ]:

        stats = statistics[
            park_name
        ]

        print(
            park_name
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
            stats["observed_index"]
        )

        print(
            "------------------------------------------"
        )

    # --------------------------------------------------------
    # CREAR FILAS CSV
    # --------------------------------------------------------

    rows = []

    for ride in collected:

        config = ride["config"]

        park_name = ride["park"]

        if park_name == "PortAventura":

            park_open = portaventura_open

            opening = "10:30"
            closing = "23:30"

        else:

            park_open = ferrari_open

            opening = "17:00"
            closing = "22:00"

        stats = statistics[
            park_name
        ]

        row = {

            "timestamp_utc":
                timestamp_utc,

            "timestamp_madrid":
                timestamp_madrid,

            "date_madrid":
                date_madrid,

            "park":
                park_name,

            "code":
                config["code"],

            "ride":
                config["name"],

            "api_name":
                ride["api_name"],

            "ride_id":
                config["id"],

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

            "park_open":
                park_open,

            "park_opening":
                opening,

            "park_closing":
                closing,
        }

        # ----------------------------------------------------
        # VALIDACIÓN DE FILA
        # ----------------------------------------------------

        if len(row) != len(FIELDNAMES):

            raise RuntimeError(
                "Fila incorrecta: "
                f"{len(row)} columnas. "
                f"Esperadas: {len(FIELDNAMES)}"
            )

        rows.append(
            row
        )

    print(
        f"Filas preparadas: {len(rows)}"
    )

    print(
        f"Columnas por fila: {len(FIELDNAMES)}"
    )

    return rows


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

            rows = list(
                reader
            )

        if not rows:

            return True

        header = rows[0]

        # ----------------------------------------------------
        # HEADER INCORRECTO
        # ----------------------------------------------------

        if header != FIELDNAMES:

            print(
                "El CSV existente utiliza "
                "una estructura antigua."
            )

            return False

        # ----------------------------------------------------
        # VALIDAR TODAS LAS FILAS
        # ----------------------------------------------------

        for line_number, row in enumerate(
            rows[1:],
            start=2
        ):

            if len(row) != len(
                FIELDNAMES
            ):

                print(
                    f"CSV corrupto: línea "
                    f"{line_number} tiene "
                    f"{len(row)} columnas "
                    f"en vez de "
                    f"{len(FIELDNAMES)}."
                )

                return False

        return True

    except Exception as error:

        print(
            "ERROR validando CSV:",
            error
        )

        return False


# ============================================================
# REPARAR / AISLAR CSV ANTIGUO
# ============================================================

def reset_corrupt_csv():

    if not os.path.exists(
        CSV_FILE
    ):

        return

    backup_file = (
        CSV_FILE
        + ".corrupt-"
        + datetime.now(
            UTC_TZ
        ).strftime(
            "%Y%m%d-%H%M%S"
        )
        + ".bak"
    )

    print(
        "El CSV existente no es compatible."
    )

    print(
        "Guardando copia en:",
        backup_file
    )

    shutil.copy2(
        CSV_FILE,
        backup_file
    )

    os.remove(
        CSV_FILE
    )

    print(
        "CSV antiguo aislado."
    )

    print(
        "Se creará un CSV nuevo y limpio."
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
    # VALIDAR CSV ANTES DE ESCRIBIR
    # --------------------------------------------------------

    if not validate_existing_csv():

        reset_corrupt_csv()

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
    # VALIDACIÓN FINAL
    # --------------------------------------------------------

    if not validate_existing_csv():

        raise RuntimeError(
            "El CSV sigue siendo inválido "
            "después de guardar."
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
