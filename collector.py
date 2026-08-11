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

MADRID_TZ = ZoneInfo("Europe/Madrid")
UTC_TZ = ZoneInfo("UTC")

CSV_FILE = "data/queue_history.csv"

HEADERS = {
    "User-Agent": "PortAventura-Queue-Study/1.0",
}


# ============================================================
# PARQUES QUEUE-TIMES
# ============================================================

PARKS = {
    "PortAventura": {
        "queue_times_id": 19,
        "opening": time(10, 30),
        "closing": time(23, 30),
    },

    "Ferrari Land": {
        "queue_times_id": 277,
        "opening": time(17, 0),
        "closing": time(22, 0),
    },
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
# VALIDACIÓN DE COLUMNAS
# ============================================================

EXPECTED_COLUMNS = len(FIELDNAMES)


def validate_row(row):

    missing = [
        field
        for field in FIELDNAMES
        if field not in row
    ]

    extra = [
        field
        for field in row
        if field not in FIELDNAMES
    ]

    if missing:
        raise ValueError(
            "Faltan columnas: "
            + ", ".join(missing)
        )

    if extra:
        raise ValueError(
            "Columnas desconocidas: "
            + ", ".join(extra)
        )

    if len(row) != EXPECTED_COLUMNS:
        raise ValueError(
            f"La fila tiene {len(row)} columnas. "
            f"Se esperaban {EXPECTED_COLUMNS}."
        )


# ============================================================
# QUEUE-TIMES
# ============================================================

def get_queue_times(park_id):

    url = (
        f"https://queue-times.com/"
        f"parks/{park_id}/queue_times.json"
    )

    try:

        print(
            f"Consultando Queue-Times parque {park_id}..."
        )

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        rides = {}

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

        for ride in all_rides:

            ride_name = ride.get(
                "name"
            )

            if not ride_name:
                continue

            rides[
                ride_name
            ] = {
                "id":
                    ride.get("id"),

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
            f"Queue-Times parque {park_id}: "
            f"recibidas {len(rides)} atracciones"
        )

        return rides

    except Exception as error:

        print(
            f"ERROR Queue-Times parque {park_id}:",
            error
        )

        return {}


# ============================================================
# BUSCAR ATRACCIÓN POR ID
# ============================================================

def find_ride(live_data, ride_id):

    for ride in live_data.values():

        if ride.get("id") == ride_id:
            return ride

    return None


# ============================================================
# AFLUENCIA
# ============================================================

def get_crowd_forecast(park_id, date_string):

    print(
        f"Consultando calendario Queue-Times "
        f"parque {park_id}..."
    )

    url = (
        f"https://queue-times.com/"
        f"parks/{park_id}/calendar/"
        f"{date_string[:4]}/"
        f"{date_string[5:7]}/"
        f"{date_string[8:10]}"
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
        # FORMATO DIRECTO
        # ----------------------------------------------------

        if isinstance(
            data,
            dict
        ):

            for key in (
                "crowd",
                "crowd_percent",
                "crowdPercent",
                "percentage",
                "percent",
            ):

                value = data.get(key)

                if value is not None:

                    print(
                        f"Afluencia encontrada parque "
                        f"{park_id}: {value}%"
                    )

                    return value

        # ----------------------------------------------------
        # LISTA DE DÍAS
        # ----------------------------------------------------

        if isinstance(
            data,
            list
        ):

            for day in data:

                if not isinstance(
                    day,
                    dict
                ):
                    continue

                day_date = (
                    day.get("date")
                    or day.get("day")
                )

                if day_date == date_string:

                    value = (
                        day.get("crowd")
                        or day.get("crowd_percent")
                        or day.get("crowdPercent")
                        or day.get("percentage")
                        or day.get("percent")
                    )

                    if value is not None:

                        print(
                            f"Afluencia encontrada parque "
                            f"{park_id}: {value}%"
                        )

                        return value

        print(
            f"No se encontró afluencia "
            f"para parque {park_id}"
        )

    except Exception as error:

        print(
            f"ERROR obteniendo afluencia "
            f"del parque {park_id}:",
            error
        )

    return None


# ============================================================
# HORARIO
# ============================================================

def is_open(
    current_time,
    opening,
    closing
):

    return (
        opening
        <= current_time
        < closing
    )


# ============================================================
# ÍNDICE DE AFLUENCIA OBSERVADO
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
        (
            average_wait
            / 120
        ) * 100,
        100
    )

    median_score = min(
        (
            median_wait
            / 120
        ) * 100,
        100
    )

    maximum_score = min(
        (
            maximum_wait
            / 180
        ) * 100,
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
    # HORARIOS
    # --------------------------------------------------------

    portaventura_open = is_open(
        current_time,
        PARKS[
            "PortAventura"
        ]["opening"],
        PARKS[
            "PortAventura"
        ]["closing"]
    )

    ferrari_land_open = is_open(
        current_time,
        PARKS[
            "Ferrari Land"
        ]["opening"],
        PARKS[
            "Ferrari Land"
        ]["closing"]
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
    # QUEUE-TIMES
    # --------------------------------------------------------

    portaventura_data = get_queue_times(
        PARKS[
            "PortAventura"
        ]["queue_times_id"]
    )

    ferrari_data = get_queue_times(
        PARKS[
            "Ferrari Land"
        ]["queue_times_id"]
    )

    # --------------------------------------------------------
    # AFLUENCIA
    # --------------------------------------------------------

    portaventura_forecast = None
    ferrari_forecast = None

    if portaventura_open:

        portaventura_forecast = (
            get_crowd_forecast(
                19,
                date_madrid
            )
        )

    if ferrari_land_open:

        ferrari_forecast = (
            get_crowd_forecast(
                277,
                date_madrid
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
    # DATOS POR PARQUE
    # --------------------------------------------------------

    park_data = {
        "PortAventura":
            portaventura_data,

        "Ferrari Land":
            ferrari_data,
    }

    park_open = {
        "PortAventura":
            portaventura_open,

        "Ferrari Land":
            ferrari_land_open,
    }

    park_forecast = {
        "PortAventura":
            portaventura_forecast,

        "Ferrari Land":
            ferrari_forecast,
    }

    # --------------------------------------------------------
    # PRIMERA PASADA:
    # RECOPILAR ATRACCIONES
    # --------------------------------------------------------

    collected = []

    wait_times_by_park = {
        "PortAventura": [],
        "Ferrari Land": [],
    }

    for ride_config in RIDES:

        park = ride_config[
            "park"
        ]

        ride_id = ride_config[
            "id"
        ]

        live_data = park_data[
            park
        ]

        ride = find_ride(
            live_data,
            ride_id
        )

        park_is_open = park_open[
            park
        ]

        # ----------------------------------------------------
        # NO ENCONTRADA
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
            # ATRACCIÓN OPERATIVA
            # ------------------------------------------------

            elif api_status == "OPERATING":

                status = "OPERATING"

                ride_open = True

            # ------------------------------------------------
            # OTROS ESTADOS
            # ------------------------------------------------

            else:

                status = api_status

                ride_open = False

                wait_minutes = None

        # ----------------------------------------------------
        # GUARDAR COLA VÁLIDA
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
                "park": park,
                "code": ride_config["code"],
                "ride": ride_config["name"],
                "api_name": api_name,
                "ride_id": ride_id,
                "status": status,
                "ride_open": ride_open,
                "wait_minutes": wait_minutes,
                "last_updated": last_updated,
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

            observed = (
                calculate_observed_crowd(
                    waits
                )
            )

        else:

            queue_mean = None
            queue_median = None
            queue_max = None
            observed = None

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

            "observed":
                observed,

            "rides_operating":
                rides_operating,

            "rides_with_wait":
                rides_with_wait,
        }

    # --------------------------------------------------------
    # MOSTRAR RESULTADOS
    # --------------------------------------------------------

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

    for park in (
        "PortAventura",
        "Ferrari Land"
    ):

        stats = statistics[
            park
        ]

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
            stats["observed"]
        )

        print(
            "------------------------------------------"
        )

    # --------------------------------------------------------
    # CREAR FILAS CSV
    # --------------------------------------------------------

    rows = []

    for ride in collected:

        park = ride[
            "park"
        ]

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
                park_forecast[
                    park
                ],

            "observed_crowd_index":
                stats["observed"],

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

        # ----------------------------------------------------
        # VALIDACIÓN
        # ----------------------------------------------------

        validate_row(
            row
        )

        rows.append(
            row
        )

    print(
        f"Filas preparadas: {len(rows)}"
    )

    print(
        f"Columnas por fila: {EXPECTED_COLUMNS}"
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

    # --------------------------------------------------------
    # VALIDAR TODAS LAS FILAS ANTES DE TOCAR EL CSV
    # --------------------------------------------------------

    for index, row in enumerate(
        rows,
        start=1
    ):

        validate_row(
            row
        )

        if len(row) != EXPECTED_COLUMNS:

            raise ValueError(
                f"Fila {index}: "
                f"{len(row)} columnas "
                f"en lugar de "
                f"{EXPECTED_COLUMNS}."
            )

    os.makedirs(
        "data",
        exist_ok=True
    )

    file_exists = os.path.exists(
        CSV_FILE
    )

    # --------------------------------------------------------
    # SI EXISTE, COMPROBAR CABECERA
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

            header = next(
                reader,
                None
            )

            if header != FIELDNAMES:

                raise ValueError(
                    "La cabecera del CSV "
                    "no coincide con la estructura "
                    "actual de 25 columnas."
                )

    # --------------------------------------------------------
    # ESCRIBIR
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
            extrasaction="raise"
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
        f"{EXPECTED_COLUMNS} columnas."
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
