from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.lifespan import lifespan

app = FastAPI(lifespan=lifespan)

# Configuración CORS
origins = [
    "http://localhost",
    "http://localhost:4200",  # React/Vue/Angular típico
    "http://localhost:8080",  # Desarrollo
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    # Agrega aquí tus dominios de producción
    "https://tudominio.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Para desarrollo, puedes usar ["*"] pero no recomendado en producción
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos HTTP (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Permite todos los headers
)


app.include_router(api_router, prefix="/api")