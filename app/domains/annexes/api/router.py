from fastapi import APIRouter, Depends, status, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.domains.annexes.api.schemas import (
    AnnexedResultUploadResponse,
    AnnexedResultListResponse,
)
from app.domains.annexes.application.use_cases import annexed_use_cases

router = APIRouter(prefix="/annexes", tags=["Annexed Results"])


@router.post(
    "/upload",
    response_model=AnnexedResultUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir PDF anexo a resultados de una orden",
    description="Recibe un PDF y lo sube a MinIO, registrando el anexo en la orden correspondiente.",
    dependencies=[Depends(require_permission("AnnexedResults:Upload"))],
)
async def upload_annexed_result(
    order_id: int = Form(...),
    user_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    return await annexed_use_cases.upload_annexed_result(db, order_id, file, user_id)


@router.get(
    "/order/{order_id}",
    response_model=AnnexedResultListResponse,
    summary="Listar PDFs anexos de una orden",
    description="Retorna la lista de archivos PDF anexos a los resultados de una orden.",
    dependencies=[Depends(require_permission("AnnexedResults:List"))],
)
async def list_annexed_results(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await annexed_use_cases.list_annexed_results(db, order_id)


@router.delete(
    "/{ar_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar un PDF anexo",
    description="Elimina el registro y el archivo de MinIO.",
    dependencies=[Depends(require_permission("AnnexedResults:Delete"))],
)
async def delete_annexed_result(
    ar_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await annexed_use_cases.delete_annexed_result(db, ar_id)
