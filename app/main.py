from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.api.router import api_router
from app.core.config import settings
from app.core.middleware import add_process_time_header
from app.core.logging_config import setup_sql_logging
from app.lifespan import lifespan

setup_sql_logging()

app = FastAPI(lifespan=lifespan)

app.middleware("http")(add_process_time_header)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")