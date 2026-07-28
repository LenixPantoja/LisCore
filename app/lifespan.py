import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from datetime import datetime
import pytz

from app.domains.laboratories.infrastructure.formula_listener import start_listener, stop_listener

# Set timezone for the application
BOGOTA_TZ = pytz.timezone("America/Bogota")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    os.environ["TZ"] = "America/Bogota"

    # Log startup with Bogota time
    bogota_time = datetime.now(BOGOTA_TZ)
    print(f"Starting up LIS Backend... (Timezone: America/Bogota, Current time: {bogota_time.strftime('%Y-%m-%d %H:%M:%S')})")

    # Escucha resultados de laboratorio escritos directamente en la BD (fuera de la API)
    # para recalcular pruebas de fórmula dependientes.
    await start_listener()

    yield

    # Shutdown actions
    await stop_listener()
    print("Shutting down LIS Backend...")
