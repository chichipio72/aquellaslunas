from fastapi import FastAPI
from skyfield.api import load

app = FastAPI()

@app.get("/")
def root():
    return {"mensaje": "API de Aquellas Lunas funcionando!"}

@app.get("/ahora")
def ahora():
    ts = load.timescale()
    t = ts.now()
    return {"fecha_juliana_tt": t.tt}
