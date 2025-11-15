from fastapi import FastAPI, Query
from skyfield.api import load, Topos
from skyfield import almanac
from datetime import datetime, timedelta
import pytz

# Crear una sola aplicación FastAPI
app = FastAPI()


# ======================
# ENDPOINT PRINCIPAL "/"
# ======================
@app.get("/")
def root():
    return {"mensaje": "API de Aquellas Lunas funcionando!"}


# ======================
# ENDPOINT /ahora
# ======================
@app.get("/ahora")
def ahora(tz: float = Query(0, description="Huso horario en horas. Ej: -3 para Argentina")):

    ts = load.timescale()
    t = ts.now()

    utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)

    try:
        user_tz = pytz.FixedOffset(int(tz * 60))
        local_time = utc_now.astimezone(user_tz)
    except Exception as e:
        return {"error": f"Huso horario inválido: {tz}", "detalle": str(e)}

    return {
        "fecha_juliana_TT": t.tt,
        "utc": utc_now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "local_time": local_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "tz": tz
    }


# ======================
# FUNCIÓN BASE DE CÁLCULO
# ======================
def calcular_datos(fecha: datetime, lat: float, lon: float, tz: float):

    ts = load.timescale()
    planets = load('de421.bsp')

    observador = planets['earth'] + Topos(latitude_degrees=lat, longitude_degrees=lon)

    tz_fixed = pytz.FixedOffset(int(tz * 60))
    dia_local = fecha.replace(tzinfo=tz_fixed)
    dia_utc = dia_local.astimezone(pytz.utc)

    t0 = ts.from_datetime(dia_utc)
    t1 = ts.from_datetime(dia_utc + timedelta(days=1))

    # Sol — salida/puesta
    f_sol = almanac.sunrise_sunset(planets, observador)
    tiempos_sol, eventos_sol = almanac.find_discrete(t0, t1, f_sol)

    salida_sol = None
    puesta_sol = None
    for t, evento in zip(tiempos_sol, eventos_sol):
        dt_local = t.utc_datetime().replace(tzinfo=pytz.utc).astimezone(tz_fixed)
        if evento == 1:
            salida_sol = dt_local.strftime("%Y-%m-%d %H:%M")
        else:
            puesta_sol = dt_local.strftime("%Y-%m-%d %H:%M")

    # Luna — salida/puesta
    f_luna = almanac.risings_and_settings(planets, planets['moon'], observador)
    tiempos_luna, eventos_luna = almanac.find_discrete(t0, t1, f_luna)

    salida_luna = None
    puesta_luna = None
    for t, evento in zip(tiempos_luna, eventos_luna):
        dt_local = t.utc_datetime().replace(tzinfo=pytz.utc).astimezone(tz_fixed)
        if evento == 1:
            salida_luna = dt_local.strftime("%Y-%m-%d %H:%M")
        else:
            puesta_luna = dt_local.strftime("%Y-%m-%d %H:%M")

    # Fase lunar, iluminación, distancias
    t = ts.from_datetime(dia_utc)
    e = planets
    sol, luna = e['sun'], e['moon']

    dist_luna = observador.at(t).observe(luna).distance().km
    dist_sol  = observador.at(t).observe(sol).distance().km

    fase_func = almanac.moon_phase(e)
    fase_rad = fase_func(t)
    iluminacion = almanac.fraction_illuminated(e, 'moon', t)

    # Edad lunar
    f_moonphases = almanac.moon_phases(e)
    t_prev, _ = almanac.find_discrete(t0 - timedelta(days=30), t0, f_moonphases)
    if len(t_prev) > 0:
        ultima_nueva = t_prev[-1].utc_datetime().replace(tzinfo=pytz.utc).astimezone(tz_fixed)
        edad = (dia_local - ultima_nueva).total_seconds() / 86400
    else:
        edad = None

    # Traducir fase
    fase_deg = fase_rad.degrees
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
        "fecha": dia_local.strftime("%Y-%m-%d"),
        "sol": {"salida": salida_sol, "puesta": puesta_sol},
        "luna": {
            "salida": salida_luna,
            "puesta": puesta_luna,
            "fase": fase_nombre,
            "edad_dias": round(edad, 2) if edad else None,
            "iluminacion": round(float(iluminacion), 4),
            "distancia_km": round(dist_luna, 2),
        },
        "sol_distancia_km": round(dist_sol, 2)
    }


# ======================
# ENDPOINT /datos
# ======================
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
