import io
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.domains.annexes.infrastructure.repository import AnnexedResultRepository
from app.domains.orders.domain.models import Order
from utils.minio_client import (
    upload_annexed_pdf,
    build_annexed_object_name,
    download_annexed_pdf,
)
from app.domains.annexes.domain.models import AnnexedResult


async def upload_annexed_result(
    db: AsyncSession,
    order_id: int,
    file: UploadFile,
    user_id: int | None = None,
) -> dict:
    # 1. Validate order exists
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden con ID {order_id} no encontrada.",
        )

    # 2. Read file content
    file_data = await file.read()
    if not file_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío.",
        )

    # 3. Validate it's a PDF
    content_type = file.content_type or "application/pdf"
    if content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten archivos PDF.",
        )

    # 4. Create DB record first to get ar_id
    ann = await AnnexedResultRepository.create(db, {
        "ar_order_id": order_id,
        "ar_file": "",  # temporary, will update
        "ar_user_record_file": user_id,
    })

    # 5. Build object name and upload to MinIO
    object_name = build_annexed_object_name(order.o_number, ann.ar_id, file.filename or "documento.pdf")
    upload_annexed_pdf(file_data, object_name, content_type="application/pdf")

    # 6. Update record with the object name
    ann.ar_file = object_name
    await db.flush()
    await db.refresh(ann)
    await db.commit()

    return {
        "success": True,
        "ar_id": ann.ar_id,
        "ar_file": object_name,
        "order_id": order_id,
        "message": "PDF anexo subido correctamente.",
    }


async def list_annexed_results(db: AsyncSession, order_id: int) -> dict:
    items = await AnnexedResultRepository.get_by_order_id(db, order_id)
    return {
        "items": items,
        "total": len(items),
    }


async def delete_annexed_result(db: AsyncSession, ar_id: int) -> dict:
    ann = await AnnexedResultRepository.get_by_id(db, ar_id)
    if not ann:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resultado anexo con ID {ar_id} no encontrado.",
        )

    # Delete from MinIO (best-effort)
    try:
        from utils.minio_client import get_minio_client
        from app.core.config import settings
        client = get_minio_client()
        client.remove_object(settings.MINIO_ANNEXE_RESULT_BUCKET, ann.ar_file)
    except Exception:
        pass  # Ignore errors, the DB record is the source of truth

    await AnnexedResultRepository.delete(db, ar_id)
    await db.commit()

    return {
        "success": True,
        "message": "Resultado anexo eliminado correctamente.",
    }


async def get_annexed_pdf_bytes(db: AsyncSession, ar_id: int) -> bytes:
    ann = await AnnexedResultRepository.get_by_id(db, ar_id)
    if not ann:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resultado anexo con ID {ar_id} no encontrado.",
        )

    pdf_bytes = download_annexed_pdf(ann.ar_file)
    if pdf_bytes is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El archivo PDF no se encuentra en el almacenamiento.",
        )

    return pdf_bytes