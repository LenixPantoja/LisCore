from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    print("Starting up LIS Backend...")
    yield
    # Shutdown actions
    print("Shutting down LIS Backend...")
