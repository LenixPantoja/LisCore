import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from datetime import datetime
import pytz

# Set timezone for the application
BOGOTA_TZ = pytz.timezone("America/Bogota")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    os.environ["TZ"] = "America/Bogota"
    
    # Log startup with Bogota time
    bogota_time = datetime.now(BOGOTA_TZ)
    print(f"Starting up LIS Backend... (Timezone: America/Bogota, Current time: {bogota_time.strftime('%Y-%m-%d %H:%M:%S')})")
    yield
    # Shutdown actions
    print("Shutting down LIS Backend...")
