"""
Bloqueo para generar consecutivos sin duplicados.

Los consecutivos "leer el último y sumar 1" fallan si dos usuarios crean al
mismo tiempo: ambos leen el mismo último número antes de que el otro guarde.
pg_advisory_xact_lock hace que el segundo espere hasta que el primero confirme
(o revierta) su transacción; al continuar, ya ve el número guardado.
El bloqueo se libera solo al terminar la transacción.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def lock_consecutive(db: AsyncSession, key: str) -> None:
    """Bloquea `key` (p. ej. "order_number:031126") hasta el fin de la transacción."""
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": key})
