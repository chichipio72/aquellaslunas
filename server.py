from fastapi import FastAPI, Query
from skyfield.api import load
from datetime import datetime
import pytz

app = FastAPI()

@app.get("/")
def root():
    return {"mensaje": "API de Aquellas Lunas funcionando!"}

@app.get("/ahora")
def ahora(tz: float = Query(0, description="Huso horario en horas. Ej: -3 para Argentina")):
    """
    Devuelve:
    - fecha juliana (TT)
    - hora UTC
    - hora local según tz elegido
    """

    # Skyfield: tiempo actual
    ts = load.timescale()
    t = ts.now()

    # Tiempo UTC como datetime
    utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)

    # Convertimos a zona horaria del usuario
    try:
        # tz puede ser decimal (ej: 5.5 para India)
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
