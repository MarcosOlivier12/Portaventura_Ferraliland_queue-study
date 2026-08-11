import csv
import os
import re
import requests
from datetime import datetime, time
from zoneinfo import ZoneInfo
from statistics import mean, median


# ============================================================
# CONFIGURACIÓN
# ============================================================

MADRID_TZ = ZoneInfo("Europe/Madrid")
UTC_TZ = ZoneInfo("UTC")

CSV_FILE = "data/queue_history.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PortAventura-Queue-Study/1.0)"
}


# ============================================================
# PARQUES
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
# ATRACCIONES QUE QUEREMOS ESTUDIAR
# ============================================================

RIDES = [

    # ---------------- PORTAVENTURA ----------------

    {
        "park": "PortAventura",
        "code": "UNCH",
        "name": "Uncharted",
    },

    {
        "park": "PortAventura",
        "code": "SM",
        "name": "Street Mission",
    },

    {
        "park": "PortAventura",
        "code": "SH",
        "name": "Shambhala",
    },

    {
        "park": "PortAventura",
        "code": "DK",
        "name": "Dragon Khan",
    },

    {
        "park": "PortAventura",
        "code": "FB",
        "name": "Furius Baco",
    },

    {
        "park": "PortAventura",
        "code": "HC",
        "name": "Hurakan Condor",
    },

    {
        "park": "PortAventura",
        "code": "STAM",
        "name": "Stampida",
    },

    {
        "park": "PortAventura",
        "code": "TK",
        "name": "Tutuki Splash",
    },

    {
        "park": "PortAventura",
        "code": "DB",
        "name": "El Diablo - Tren De La Mina",
    },

    {
        "park": "PortAventura",
        "code": "SVR",
        "name": "Silver River Flume",
    },

    {
        "park": "PortAventura",
        "code": "TF",
        "name": "Templo del Fuego",
    },


    # ---------------- FERRARI LAND ----------------

    {
        "park": "Ferrari Land",
        "code": "RF",
        "name": "Red Force",
    },

    {
        "park": "Ferrari Land",
        "code": "TT",
        "name": "Thrill Towers",
    },

    {
        "park": "Ferrari Land",
        "code": "FLY",
        "name": "Flying Dreams",
    },
]


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def normalize_name(name):
    """
    Normaliza nombres para poder comparar los nombres de nuestra
    lista con los nombres devueltos por Queue-Times.
    """

    if not name:
        return ""

    name = name.lower().strip()

    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    name = re.sub(
        r"[^a-z0-9]+",
        " ",
        name
    )

    return " ".join(
        name.split()
    )


def is_open(current_time, opening, closing):
    return (
        opening
        <= current_time
        <= closing
    )


# ============================================================
# QUEUE-TIMES
# ============================================================

def get_queue_times(park_id):

    url = (
        f"https://queue-times.com/parks/"
        f"{park_id}/queue_times.json"
    )

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    rides = []

    rides.extend(
        data.get(
            "rides",
            []
        )
    )

    for land in data.get(
        "lands",
        []
    ):

        rides.extend(
            land.get(
                "rides",
                []
            )
        )

    result = {}

    for ride in rides:

        name = ride.get(
            "name"
        )

        if not name:
            continue

        normalized = normalize_name(
            name
        )

        result[normalized] = {
            "name":
                name,

            "id":
                ride.get("id"),

            "is_open":
                ride.get("is_open"),

            "wait_time":
                ride.get("wait_time"),

            "last_updated":
                ride.get("last_updated"),
        }

    print(
        f"Queue-Times parque {park_id}: "
        f"recibidas {len(result)} atracciones"
    )

    return result


# ============================================================
# PREDICCIÓN / NIVEL DE AFLUENCIA
# ============================================================

def get_crowd_level(park_id, date_madrid):

    """
    Obtiene la predicción de afluencia del día desde
    el calendario mensual de Queue-Times.

    PortAventura = 19
    Ferrari Land = 277
    """

    url = (
        f"https://queue-times.com/parks/"
        f"{park_id}/calendar/"
        f"{date_madrid.year}/"
        f"{date_madrid.month:02d}"
    )

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

        html = response.text

        # ----------------------------------------------------
        # Buscar el día concreto dentro del calendario.
        #
        # Queue-Times muestra las fechas como:
        #
        # 11 Tue 11 45%*
        #
        # o:
        #
        # 11 Tue 11 45%
        #
        # El asterisco significa que es una predicción.
        # ----------------------------------------------------

        day = date_madrid.day

        pattern = (
            rf"\b{day}\s+"
            rf"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)"
            rf"\s+{day}\s+"
            rf"(\d+)%"
        )

        match = re.search(
            pattern,
            html,
            re.IGNORECASE
        )

        if match:

            crowd = int(
                match.group(1)
            )

            return crowd


        # ----------------------------------------------------
        # Segundo intento:
        # buscar el día sin exigir dos veces el número.
        # ----------------------------------------------------

        pattern_fallback = (
            rf"\b{day}\b.*?"
            rf"(\d+)%"
        )

        matches = re.findall(
            pattern_fallback,
            html,
            re.IGNORECASE
        )

        if matches:

            # Tomamos el primer porcentaje encontrado
            # asociado al día.
            return int(
                matches[0]
            )


        print(
            f"No se encontró el día {day} "
            f"en el calendario del parque {park_id}"
        )

    except Exception as error:

        print(
            f"ERROR obteniendo afluencia "
            f"del parque {park_id}: {error}"
        )

    return None


# ============================================================
# ESTADÍSTICAS
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
    # ESTADO DE LOS PARQUES
    # ========================================================

    park_states = {}

    for park_name, park_config in PARKS.items():

        opened = is_open(
            current_time,
            park_config["opening"],
            park_config["closing"]
        )

        park_states[
            park_name
        ] = opened

        print(
            f"{park_name}: "
            f"{'ABIERTO' if opened else 'CERRADO'}"
        )


    print(
        "Horario PortAventura: 10:30 - 23:30"
    )

    print(
        "Horario Ferrari Land: 17:00 - 22:00"
    )


    # ========================================================
    # SI LOS DOS ESTÁN CERRADOS
    # ========================================================

    if not any(
        park_states.values()
    ):

        print(
            "Ambos parques están cerrados."
        )

        print(
            "No se realiza recopilación."
        )

        return []


    # ========================================================
    # CONSULTAR QUEUE-TIMES POR SEPARADO
    # ========================================================

    print(
        "Consultando Queue-Times..."
    )

    queue_data = {}

    for park_name, park_config in PARKS.items():

        # Solo necesitamos consultar el parque si está abierto.
        # Si está cerrado, guardaremos CLOSED_PARK.
        if park_states[park_name]:

            try:

                queue_data[
                    park_name
                ] = get_queue_times(
                    park_config[
                        "queue_times_id"
                    ]
                )

            except Exception as error:

                print(
                    f"ERROR Queue-Times "
                    f"{park_name}: {error}"
                )

                queue_data[
                    park_name
                ] = {}

        else:

            queue_data[
                park_name
            ] = {}


    # ========================================================
    # AFLUENCIA INDEPENDIENTE DE CADA PARQUE
    # ========================================================

    print(
        "Consultando predicción de afluencia..."
    )

    crowd_forecasts = {}

    for park_name, park_config in PARKS.items():

        crowd = get_crowd_level(
            park_config[
                "queue_times_id"
            ],
            date_madrid
        )

        crowd_forecasts[
            park_name
        ] = crowd

        print(
            f"Predicción afluencia "
            f"{park_name}: {crowd}"
        )


    # ========================================================
    # RECOPILAR ATRACCIONES
    # ========================================================

    collected = []

    park_wait_times = {
        "PortAventura": [],
        "Ferrari Land": [],
    }


    for ride_config in RIDES:

        park = ride_config[
            "park"
        ]

        code = ride_config[
            "code"
        ]

        requested_name = ride_config[
            "name"
        ]

        normalized_requested = normalize_name(
            requested_name
        )

        park_is_open = park_states[
            park
        ]

        source = queue_data.get(
            park,
            {}
        )

        ride = source.get(
            normalized_requested
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
        # PARQUE ABIERTO PERO FUENTE NO DISPONIBLE
        # ----------------------------------------------------

        elif not source:

            status = "SOURCE_NOT_AVAILABLE"

            ride_open = False

            wait_minutes = None

            last_updated = None

            api_name = ""


        # ----------------------------------------------------
        # ATRACCIÓN NO ENCONTRADA
        # ----------------------------------------------------

        elif ride is None:

            status = "NOT_FOUND"

            ride_open = False

            wait_minutes = None

            last_updated = None

            api_name = ""


        # ----------------------------------------------------
        # ATRACCIÓN ENCONTRADA
        # ----------------------------------------------------

        else:

            api_name = ride.get(
                "name",
                ""
            )

            wait_minutes = ride.get(
                "wait_time"
            )

            last_updated = ride.get(
                "last_updated"
            )

            ride_is_open = (
                ride.get(
                    "is_open"
                )
                is True
            )


            if ride_is_open:

                status = "OPERATING"

                ride_open = True

            else:

                status = "CLOSED"

                ride_open = False

                wait_minutes = None


            # ------------------------------------------------
            # GUARDAR TIEMPOS VÁLIDOS
            # ------------------------------------------------

            if (
                ride_open
                and isinstance(
                    wait_minutes,
                    (int, float)
                )
            ):

                park_wait_times[
                    park
                ].append(
                    float(
                        wait_minutes
                    )
                )


        print(
            f"{park} | "
            f"{code} | "
            f"{status} | "
            f"{wait_minutes} min"
        )


        collected.append(
            {
                "park":
                    park,

                "code":
                    code,

                "ride":
                    requested_name,

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
            }
        )


    # ========================================================
    # ESTADÍSTICAS POR PARQUE
    # ========================================================

    park_statistics = {}


    for park_name in PARKS:

        waits = park_wait_times[
            park_name
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
                ride["park"]
                == park_name
                and ride["ride_open"]
            )
        )


        rides_with_wait = len(
            waits
        )


        park_statistics[
            park_name
        ] = {

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

            "observed_crowd":
                observed_crowd,
        }


    # ========================================================
    # MOSTRAR ESTADÍSTICAS
    # ========================================================

    for park_name in PARKS:

        stats = park_statistics[
            park_name
        ]

        print(
            "------------------------------------------"
        )

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
            stats["observed_crowd"]
        )


    # ========================================================
    # CREAR FILAS CSV
    # ========================================================

    rows = []


    for ride in collected:

        park = ride[
            "park"
        ]

        stats = park_statistics[
            park
        ]

        row = {

            "timestamp_utc":
                timestamp_utc,

            "timestamp_madrid":
                timestamp_madrid,

            "date_madrid":
                date_madrid.isoformat(),

            "park":
                park,

            "code":
                ride["code"],

            "ride":
                ride["ride"],

            "api_name":
                ride["api_name"],

            "status":
                ride["status"],

            "ride_open":
                ride["ride_open"],

            "wait_minutes":
                ride["wait_minutes"],

            "last_updated":
                ride["last_updated"],

            "crowd_forecast":
                crowd_forecasts[
                    park
                ],

            "observed_crowd_index":
                stats[
                    "observed_crowd"
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

            "park_open":
                park_states[
                    park
                ],

            "park_opening":
                PARKS[
                    park
                ]["opening"].strftime(
                    "%H:%M"
                ),

            "park_closing":
                PARKS[
                    park
                ]["closing"].strftime(
                    "%H:%M"
                ),
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
