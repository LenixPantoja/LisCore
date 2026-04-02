from fastapi import APIRouter
from app.domains.patients.api.router import router as patients_router
from app.domains.users.api.router import router as users_router

api_router = APIRouter()

api_router.include_router(patients_router, prefix="/patients", tags=["Patients"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])