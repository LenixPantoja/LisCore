"""
utils/minio_client.py

Cliente MinIO singleton y helpers para generar URLs presignadas y subir objetos.
"""
import io
from datetime import datetime, timedelta
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

_client: Optional[Minio] = None


def get_minio_client() -> Minio:
    """Devuelve el cliente MinIO singleton (inicialización perezosa)."""
    global _client
    if _client is None:
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
    return _client


def get_graphic_url(object_name: str | None) -> Optional[str]:
    """
    Dado el nombre de objeto almacenado en l_result_graphic,
    genera y retorna una URL presignada GET desde el bucket 'graphics' de MinIO.

    Retorna None si object_name está vacío o si ocurre cualquier error.
    """
    if not object_name:
        return None
    try:
        client = get_minio_client()
        url = client.presigned_get_object(
            settings.MINIO_GRAPHICS_BUCKET,
            object_name,
            expires=timedelta(hours=settings.MINIO_PRESIGNED_EXPIRES_HOURS),
        )
        return url
    except S3Error:
        return None
    except Exception:
        return None


def upload_graphic(
    file_data: bytes,
    object_name: str,
    content_type: str = "image/jpeg",
) -> str:
    """
    Sube un archivo al bucket 'graphics' de MinIO y retorna el object_name.
    Lanza una excepción si la subida falla.
    """
    client = get_minio_client()
    buf = io.BytesIO(file_data)
    client.put_object(
        settings.MINIO_GRAPHICS_BUCKET,
        object_name,
        buf,
        length=len(file_data),
        content_type=content_type,
    )
    return object_name


def build_graphic_object_name(
    order_number: str,
    test_code: str,
    l_id: int,
    extension: str,
) -> str:
    """
    Genera un nombre de objeto estándar para una imagen de resultado gráfico.
    Formato: IMG_{order_number}_{test_code}_{l_id}_{timestamp}.{ext}
    """
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    ext = extension.lstrip(".").upper()
    return f"IMG_{order_number}_{test_code}_{l_id}_{ts}.{ext}"


def upload_signature(
    file_data: bytes,
    object_name: str,
    content_type: str = "image/png",
) -> str:
    """
    Sube un archivo al bucket de firmas de MinIO y retorna el object_name.
    Lanza una excepción si la subida falla.
    """
    client = get_minio_client()
    buf = io.BytesIO(file_data)
    client.put_object(
        settings.MINIO_SIGNATURES_BUCKET,
        object_name,
        buf,
        length=len(file_data),
        content_type=content_type,
    )
    return object_name


def get_signature_url(object_name: str | None) -> Optional[str]:
    """
    Dado el nombre de objeto, genera una URL presignada GET desde el bucket de firmas.
    Retorna None si object_name está vacío o si ocurre un error.
    """
    if not object_name:
        return None
    try:
        client = get_minio_client()
        url = client.presigned_get_object(
            settings.MINIO_SIGNATURES_BUCKET,
            object_name,
            expires=timedelta(hours=settings.MINIO_PRESIGNED_EXPIRES_HOURS),
        )
        return url
    except S3Error:
        return None
    except Exception:
        return None


def build_signature_object_name(usr_id: int, extension: str = "png") -> str:
    """
    Genera un nombre de objeto estándar para la firma de un usuario.
    Formato: SIGN_{usr_id}_{timestamp}.{ext}
    """
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    ext = extension.lstrip(".").lower()
    return f"SIGN_{usr_id}_{ts}.{ext}"


def upload_annexed_pdf(
    file_data: bytes,
    object_name: str,
    content_type: str = "application/pdf",
) -> str:
    """
    Sube un archivo PDF al bucket de resultados anexos de MinIO y retorna el object_name.
    Lanza una excepción si la subida falla.
    """
    client = get_minio_client()
    # Ensure bucket exists
    if not client.bucket_exists(settings.MINIO_ANNEXE_RESULT_BUCKET):
        client.make_bucket(settings.MINIO_ANNEXE_RESULT_BUCKET)
    buf = io.BytesIO(file_data)
    client.put_object(
        settings.MINIO_ANNEXE_RESULT_BUCKET,
        object_name,
        buf,
        length=len(file_data),
        content_type=content_type,
    )
    return object_name


def download_annexed_pdf(object_name: str) -> Optional[bytes]:
    """
    Descarga un PDF desde el bucket de resultados anexos de MinIO.
    Retorna los bytes del archivo o None si ocurre un error.
    """
    if not object_name:
        return None
    try:
        client = get_minio_client()
        response = client.get_object(
            settings.MINIO_ANNEXE_RESULT_BUCKET,
            object_name,
        )
        data = response.read()
        response.close()
        response.release_conn()
        return data
    except Exception:
        return None


def build_annexed_object_name(order_number: str, ar_id: int, original_filename: str) -> str:
    """
    Genera un nombre de objeto estándar para un PDF anexo.
    Formato: ANNEX_{order_number}_{ar_id}_{timestamp}.pdf
    """
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    # Sanitize filename
    name_part = original_filename.rsplit(".", 1)[0] if "." in original_filename else original_filename
    safe_name = "".join(c for c in name_part if c.isalnum() or c in "._- ")[:30]
    return f"ANNEX_{order_number}_{ar_id}_{ts}_{safe_name}.pdf"
