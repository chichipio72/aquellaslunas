from fastapi import FastAPI, Query
from skyfield.api import load, wgs84
from skyfield import almanac
from datetime import datetime, timedelta
import pytz

app = FastAPI()

# Cargar efemérides una sola vez (rápido y estable en Render)
ts = load.timescale()
eph = load('de421.bsp')


@app.get("/")
def root():
    return {"mensaje": "API de Aquellas Lunas funcionando!"}


@app.get("/ahora")
def ahora(tz: float = Query(0, description="Huso horario. Ej: -3 para Argentina")):

    t = ts.now()
    utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)

    try:
        user_tz = pytz.FixedOffset(int(tz * 60))
        local_time = utc_now.astimezone(user_tz)
    except:
        return {"error": "TZ inválido"}

    return {
        "fecha_juliana_TT": t.tt,
        "utc": utc_now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "local_time": local_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "tz": tz
    }


def calcular_datos(fecha: datetime, lat: float, lon: float, tz: float):

    # Zona horaria local
    tz_fixed = pytz.FixedOffset(int(tz * 60))
    fecha_local = fecha.replace(tzinfo=tz_fixed)
    fecha_utc = fecha_local.astimezone(pytz.utc)

    # Observador - versión Skyfield 1.53 correcta
    observador = wgs84.latlon(lat, lon)

    # Intervalo del día
    t0 = ts.from_datetime(fecha_utc)
    t1 = ts.from_datetime(fecha_utc + timedelta(days=1))

    # Sunrise/Sunset
    sol_func = almanac.risings_and_settings(eph, eph["Sun"], observador)
    t_sol, e_sol = almanac.find_discrete(t0, t1, sol_func)

    salida_sol = puesta_sol = None
    for t, e in zip(t_sol, e_sol):
        dt = t.utc_datetime().astimezone(tz_fixed)
        if e == 1 and salida_sol is None:
            salida_sol = dt.strftime("%Y-%m-%d %H:%M")
        if e == 0 and puesta_sol is None:
            puesta_sol = dt.strftime("%Y-%m-%d %H:%M")

    # Moonrise/Moonset
    luna_func = almanac.risings_and_settings(eph, eph["Moon"], observador)
    t_luna, e_luna = almanac.find_discrete(t0, t1, luna_func)

    salida_luna = puesta_luna = None
    for t, e in zip(t_luna, e_luna):
        dt = t.utc_datetime().astimezone(tz_fixed)
        if e == 1 and salida_luna is None:
            salida_luna = dt.strftime("%Y-%m-%d %H:%M")
        if e == 0 and puesta_luna is None:
            puesta_luna = dt.strftime("%Y-%m-%d %H:%M")

    # Momento actual del día (para fase e iluminación)
    t_actual = ts.from_datetime(fecha_utc)

    # Fase lunar
    fase_rad = almanac.moon_phase(eph, t_actual)
    fase_deg = fase_rad.degrees

    # Iluminación
    iluminacion = almanac.fraction_illuminated(eph, "Moon", t_actual)

    # Distancias: método correcto en Skyfield 1.53
    topo = eph["earth"] + observador
    ast = topo.at(t_actual)

    dist_luna = ast.observe(eph["Moon"]).distance().km
    dist_sol = ast.observe(eph["Sun"]).distance().km

    # Clasificación de fase
    if fase_deg < 45:
        fase_nombre = "Luna nueva"
    elif fase_deg < 90:
        fase_nombre = "Creciente"
    elif fase_deg < 135:
        fase_nombre = "Cuarto creciente"
    elif fase_deg < 180:
        fase_nombre = "Gibosa creciente"
    elif fase_deg < 225:
        fase_nombre = "Luna llena"
    elif fase_deg < 270:
        fase_nombre = "Gibosa menguante"
    elif fase_deg < 315:
        fase_nombre = "Cuarto menguante"
    else:
        fase_nombre = "Menguante"

    return {
        "fecha": fecha_local.strftime("%Y-%m-%d"),
        "sol": {
            "salida": salida_sol,
            "puesta": puesta_sol
        },
        "luna": {
            "salida": salida_luna,
            "puesta": puesta_luna,
            "fase": fase_nombre,
            "iluminacion": round(float(iluminacion), 4),
            "distancia_km": round(dist_luna, 2)
        },
        "distancia_sol_km": round(dist_sol, 2)
    }


@app.get("/datos")
def datos(lat: float, lon: float, tz: float, fecha: str = None):
    if fecha:
        try:
            fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
        except:
            return {"error": "Formato de fecha inválido. Use YYYY-MM-DD"}
    else:
        fecha_dt = datetime.utcnow()

    return calcular_datos(fecha_dt, lat, lon, tz)
