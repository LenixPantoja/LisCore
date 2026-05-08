"""
Utilidad para registrar trazas de operaciones en la tabla AppTrace.

Uso ejemplo:
    from utils.trace import register_trace
    from app.domains.traces.constants import OPERATION_CREATE_ORDER

    await register_trace(
        db=db,
        operation_type=OPERATION_CREATE_ORDER,
        operation_description="Orden 2025001 creada con estudios: BHC, QS",
        usr_id=current_user.u_id,
        order_id=order.o_id,
        notes="Creada desde la sede Bogotá",
    )
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.traces.models import AppTrace


async def register_trace(
    db: AsyncSession,
    operation_type: int,
    operation_description: str,
    usr_id: Optional[int] = None,
    order_id: Optional[int] = None,
    test_id: Optional[int] = None,
    notes: Optional[str] = None,
) -> AppTrace:
    """
    Registra una traza de operación en la base de datos.

    Args:
        db: Sesión de base de datos activa.
        operation_type: Tipo de operación (usar constantes de traces.constants).
        operation_description: Descripción detallada de la operación.
        usr_id: ID del usuario que ejecuta la operación.
        order_id: ID de la orden relacionada (opcional).
        test_id: ID de la prueba relacionada (opcional).
        notes: Notas adicionales, ej. resultado anterior antes de edición.

    Returns:
        Instancia de AppTrace persistida.
    """
    trace = AppTrace(
        usr_id=usr_id,
        order_id=order_id,
        operation_type=operation_type,
        operation_description=operation_description,
        notes=notes,
        test_id=test_id,
    )
    db.add(trace)
    await db.flush()
    return trace
