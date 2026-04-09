from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.enterprises.api.schemas import EnterpriseCreate, EnterpriseResponse, EnterpriseUpdate, EnterprisePaginatedResponse
from app.domains.enterprises.application.use_cases import create_enterprise, update_enterprise, list_enterprises, get_enterprise

router = APIRouter()

@router.post("/", response_model=EnterpriseResponse, status_code=status.HTTP_201_CREATED)
async def create_new_enterprise(data: EnterpriseCreate, db: AsyncSession = Depends(get_db)):
    """
    Endpoint para crear una nueva empresa.

    - **en_code**: Código único de la empresa (requerido).
    - **en_name**: Nombre de la empresa (requerido).
    - **en_nit**: NIT único de la empresa (requerido).
    - **en_address**: Dirección de la empresa (opcional).
    - **en_phone**: Número de teléfono de la empresa (opcional).
    - **en_Legal_representative**: Representante legal (opcional).
    - **en_mail**: Correo electrónico único de la empresa (opcional).
    - **en_active**: Estado de actividad de la empresa (por defecto True).
    - **en_send_mail**: Indica si se envían correos (por defecto False).
    - **en_send_whatsapp**: Indica si se envían mensajes de WhatsApp (por defecto False).
    - **en_email_electronic_invoice**: Correo electrónico para factura electrónica (opcional).
    - Otros campos como `en_regimen_id`, `en_classification_id`, etc., son opcionales y de tipo entero.
    - **en_password**: Contraseña asociada a la empresa (opcional, incluido según el esquema SQL).
    """
    return await create_enterprise.execute(db, data.model_dump())

@router.patch("/{en_id}", response_model=EnterpriseResponse)
async def update_existing_enterprise(en_id: int, data: EnterpriseUpdate, db: AsyncSession = Depends(get_db)):
    """
    Endpoint para actualizar o inactivar una empresa.
    """
    return await update_enterprise.execute(db, en_id, data.model_dump(exclude_unset=True))

@router.get("/", response_model=EnterprisePaginatedResponse)
async def list_existing_enterprises(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para listar empresas con paginación técnica y búsqueda opcional por nombre, NIT o código.
    """
    return await list_enterprises.execute(db, skip, limit, search)

@router.get("/{en_id}", response_model=EnterpriseResponse)
async def get_enterprise_details(en_id: int, db: AsyncSession = Depends(get_db)):
    """
    Endpoint para obtener el detalle de una empresa específica por su ID.
    """
    return await get_enterprise.execute(db, en_id)