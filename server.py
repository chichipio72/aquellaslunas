from fastapi import FastAPI, Query
from skyfield.api import load, wgs84
from skyfield import almanac
from datetime import datetime, timedelta
import pytz

# ============================================================
# INICIALIZACIÓN
# ============================================================

app = FastAPI()
ts = load.timescale()


# ============================================================
# ENDPOINT PRINCIPAL "/"
# ============================================================
@app.get("/")
def root():
    return {"mensaje": "API de Aquellas Lunas funcionando!"}


# ============================================================
# ENDPOINT /ahora
# ============================================================
@app.get("/ahora")
def ahora(tz: float = Query(0, description="Huso horario en horas. Ej: -3 para Argentina")):
    t = ts.now()
    utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)

    try:
        user_tz = pytz.FixedOffset(int(tz * 60))
        local_time = utc_now.astimezone(user_tz)
    except:
        return {"error": "Huso horario inválido"}

    return {
        "fecha_juliana_TT": t.tt,
        "utc": utc_now.strftime("%Y-%m-%d %H:%M:%S"),
        "local_time": local_time.strftime("%Y-%m-%d %H:%M:%S"),
        "tz": tz
    }


# ============================================================
# FUNCIÓN BASE — CALCULAR DATOS ASTRONÓMICOS
# ============================================================

def calcular_datos(fecha: datetime, lat: float, lon: float, tz: float):

    # EPHEMERIDES (igual que tu script viejo)
    eph = load('de421.bsp')

    # TZ local del usuario
    user_tz = pytz.FixedOffset(int(tz * 60))

    # Fechas local y UTC
    fecha_local = fecha.replace(tzinfo=user_tz)
    fecha_utc = fecha_local.astimezone(pytz.utc)

    # Observador (forma compatible Skyfield 1.45)
    observador = wgs84.latlon(lat, lon)

    # Rango de un día
    t0 = ts.utc(fecha_utc)
    t1 = ts.utc((fecha_local + timedelta(days=1)).astimezone(pytz.utc))

    # ------------------------------------------------------------
    # SALIDA Y PUESTA DEL SOL
    # ------------------------------------------------------------
    sol_func = almanac.risings_and_settings(eph, eph['Sun'], observador)
    t_sol, e_sol = almanac.find_discrete(t0, t1, sol_func)

    salida_sol = None
    puesta_sol = None

    for t, event in zip(t_sol, e_sol):
        dt = t.utc_datetime().replace(tzinfo=pytz.utc).astimezone(user_tz)
        if event == 1 and salida_sol is None:
            salida_sol = dt.strftime("%Y-%m-%d %H:%M")
        elif event == 0 and puesta_sol is None:
            puesta_sol = dt.strftime("%Y-%m-%d %H:%M")

    # ------------------------------------------------------------
    # SALIDA Y PUESTA DE LA LUNA
    # ------------------------------------------------------------
    luna_func = almanac.risings_and_settings(eph, eph['Moon'], observador)
    t_luna, e_luna = almanac.find_discrete(t0, t1, luna_func)

    salida_luna = None
    puesta_luna = None

    for t, event in zip(t_luna, e_luna):
        dt = t.utc_datetime().replace(tzinfo=pytz.utc).astimezone(user_tz)
        if event == 1 and salida_luna is None:
            salida_luna = dt.strftime("%Y-%m-%d %H:%M")
        elif event == 0 and puesta_luna is None:
            puesta_luna = dt.strftime("%Y-%m-%d %H:%M")

    # ------------------------------------------------------------
    # FASE LUNAR (ángulo)
    # ------------------------------------------------------------
    fase_deg = almanac.moon_phase(eph, ts.utc(fecha_utc)).degrees

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

    # ------------------------------------------------------------
    # ILUMINACIÓN
    # ------------------------------------------------------------
    iluminacion = almanac.fraction_illuminated(eph, 'moon', ts.utc(fecha_utc))

    # ------------------------------------------------------------
    # DISTANCIAS (forma totalmente compatible)
    # ------------------------------------------------------------
    t = ts.utc(fecha_utc)

    # Esto siempre funciona, en cualquier Skyfield
    dist_luna = (eph['Moon'] - observador).at(t).distance().km
    dist_sol =  (eph['Sun']  - observador).at(t).distance().km

    # ------------------------------------------------------------
    # RESPUESTA
    # ------------------------------------------------------------
    return {
        "fecha": fecha_local.strftime("%Y-%m-%d"),
        "sol": {
            "salida": salida_sol,
            "puesta": puesta_sol,
        },
        "luna": {
            "salida": salida_luna,
            "puesta": puesta_luna,
            "fase": fase_nombre,
            "iluminacion": round(float(iluminacion), 4),
            "distancia_km": round(dist_luna, 2)
        },
        "sol_distancia_km": round(dist_sol, 2)
    }


# ============================================================
# ENDPOINT /datos
# ============================================================

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
