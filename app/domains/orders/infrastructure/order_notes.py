"""
Notas de la orden por usuario (tabla "OrderNotes", script 067).

La nota de ingreso (Orders.o_note) se devuelve como primera nota, a nombre de
quien creó la orden. Si el script 067 aún no se ha corrido, solo se devuelve
esa nota y agregar notas responde 503 con un mensaje claro.
"""
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.user_errors import user_error, not_available
from app.domains.traces.constants import OPERATION_ADD_ORDER_NOTE, OPERATION_DELETE_ORDER_NOTE, OPERATION_EDIT_ORDER_NOTE
from utils.trace import register_trace

MAX_LEN = 2000
_ready: Optional[bool] = None


async def notes_ready(db: AsyncSession) -> bool:
    global _ready
    if _ready:
        return True
    _ready = bool((await db.execute(text("SELECT to_regclass('public.\"OrderNotes\"') IS NOT NULL"))).scalar())
    return _ready


_edit_ready: Optional[bool] = None


async def edit_ready(db: AsyncSession) -> bool:
    """Columna on_updated_at (script 068) para marcar notas editadas."""
    global _edit_ready
    if _edit_ready:
        return True
    _edit_ready = bool((await db.execute(text("""
        SELECT EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_name = 'OrderNotes' AND column_name = 'on_updated_at')
    """))).scalar())
    return _edit_ready


_USER_NAME = "NULLIF(trim(concat_ws(' ', {u}.usr_first_name, {u}.usr_last_name)), '')"


async def list_notes(db: AsyncSession, order_id: int, current_user_id: int) -> dict:
    order = (await db.execute(text(f"""
        SELECT o.o_id, o.o_note, o.o_created_at, o."o_AppUser_id" AS user_id,
               {_USER_NAME.format(u='u')} AS user_name, u.usr_login
        FROM "Orders" o LEFT JOIN "AppUsers" u ON u.usr_id = o."o_AppUser_id"
        WHERE o.o_id = :o
    """), {"o": order_id})).mappings().first()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La orden no existe.")

    notes = []
    if (order["o_note"] or "").strip():
        notes.append({
            "id": None,
            "kind": "INGRESO",
            "text": order["o_note"].strip(),
            "author": order["user_name"] or order["usr_login"] or "Ingreso de la orden",
            "author_id": order["user_id"],
            "created_at": order["o_created_at"],
            "updated_at": None,
            "can_delete": False,
            "can_edit": False,
        })

    installed = await notes_ready(db)
    if installed:
        upd = "n.on_updated_at" if await edit_ready(db) else "NULL::timestamp"
        rows = (await db.execute(text(f"""
            SELECT n.on_id, n.on_text, n.on_created_at, n.on_user_id, {upd} AS on_updated_at,
                   {_USER_NAME.format(u='u')} AS user_name, u.usr_login
            FROM "OrderNotes" n LEFT JOIN "AppUsers" u ON u.usr_id = n.on_user_id
            WHERE n.on_order_id = :o
            ORDER BY n.on_created_at, n.on_id
        """), {"o": order_id})).mappings().all()
        for r in rows:
            notes.append({
                "id": r["on_id"],
                "kind": "LABORATORIO",
                "text": r["on_text"],
                "author": r["user_name"] or r["usr_login"] or "Usuario desconocido",
                "author_id": r["on_user_id"],
                "created_at": r["on_created_at"],
                "updated_at": r["on_updated_at"],
                # Solo el autor puede modificar o eliminar su nota
                "can_delete": r["on_user_id"] == current_user_id,
                "can_edit": r["on_user_id"] == current_user_id,
            })
    return {"installed": installed, "notes": notes}


async def _trace(db: AsyncSession, op: int, order_id: int, user_id: Optional[int], action: str, body: str) -> None:
    """Traza en AppTrace con el texto de la nota (queda aunque la nota se elimine)."""
    number = (await db.execute(text('SELECT o_number FROM "Orders" WHERE o_id = :o'), {"o": order_id})).scalar()
    await register_trace(
        db=db, operation_type=op, usr_id=user_id, order_id=order_id,
        operation_description=f"{action} {number or order_id}",
        notes=body[:1000],
    )


def clean_notes(texts) -> list[str]:
    """Quita vacías y recorta; cada nota máximo MAX_LEN caracteres."""
    out = []
    for t in texts or []:
        t = (t or "").strip()
        if t:
            out.append(t[:MAX_LEN])
    return out


async def insert_notes(db: AsyncSession, order_id: int, user_id: Optional[int], texts: list[str]) -> bool:
    """
    Registra notas sin hacer commit (las confirma quien llama, p. ej. al crear
    la orden). Devuelve False si la tabla aún no existe.
    """
    texts = clean_notes(texts)
    if not texts:
        return True
    if not await notes_ready(db):
        return False
    for t in texts:
        await db.execute(text("""
            INSERT INTO "OrderNotes" (on_order_id, on_text, on_user_id) VALUES (:o, :t, :u)
        """), {"o": order_id, "t": t, "u": user_id})
        await _trace(db, OPERATION_ADD_ORDER_NOTE, order_id, user_id, "Nota agregada en admisión a la orden", t)
    return True


async def notes_text(db: AsyncSession, order_id: int, o_note: Optional[str]) -> Optional[str]:
    """Todas las notas en un solo texto (para planes de trabajo e impresos)."""
    parts = [o_note.strip()] if (o_note or "").strip() else []
    if await notes_ready(db):
        rows = (await db.execute(text(f"""
            SELECT n.on_text, {_USER_NAME.format(u='u')} AS user_name, u.usr_login
            FROM "OrderNotes" n LEFT JOIN "AppUsers" u ON u.usr_id = n.on_user_id
            WHERE n.on_order_id = :o ORDER BY n.on_created_at, n.on_id
        """), {"o": order_id})).all()
        for body, name, login in rows:
            parts.append(f"{name or login or 'Usuario'}: {body}")
    return " | ".join(parts) or None


async def add_note(db: AsyncSession, order_id: int, user_id: int, body: str) -> dict:
    body = (body or "").strip()
    if not body:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Escriba el texto de la nota.")
    if len(body) > MAX_LEN:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"La nota no puede superar {MAX_LEN} caracteres.")
    if not await notes_ready(db):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            not_available("Agregar notas a la orden", "falta correr el script 067_notas_orden.sql"))
    exists = (await db.execute(text('SELECT 1 FROM "Orders" WHERE o_id = :o'), {"o": order_id})).scalar()
    if not exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La orden no existe.")
    await db.execute(text("""
        INSERT INTO "OrderNotes" (on_order_id, on_text, on_user_id) VALUES (:o, :t, :u)
    """), {"o": order_id, "t": body, "u": user_id})
    await _trace(db, OPERATION_ADD_ORDER_NOTE, order_id, user_id, "Nota agregada a la orden", body)
    await db.commit()
    return await list_notes(db, order_id, user_id)


async def update_note(db: AsyncSession, order_id: int, note_id: int, user_id: int, body: str) -> dict:
    body = (body or "").strip()
    if not body:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Escriba el texto de la nota.")
    if len(body) > MAX_LEN:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"La nota no puede superar {MAX_LEN} caracteres.")
    if not await notes_ready(db):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La nota no existe.")
    row = (await db.execute(text("""
        SELECT on_user_id, on_text FROM "OrderNotes" WHERE on_id = :n AND on_order_id = :o FOR UPDATE
    """), {"n": note_id, "o": order_id})).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La nota no existe.")
    if row[0] != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo quien escribió la nota puede modificarla.")
    if row[1] == body:
        return await list_notes(db, order_id, user_id)
    if await edit_ready(db):
        await db.execute(text("""
            UPDATE "OrderNotes" SET on_text = :t, on_updated_at = (now() AT TIME ZONE 'America/Bogota') WHERE on_id = :n
        """), {"t": body, "n": note_id})
    else:
        await db.execute(text('UPDATE "OrderNotes" SET on_text = :t WHERE on_id = :n'), {"t": body, "n": note_id})
    await _trace(db, OPERATION_EDIT_ORDER_NOTE, order_id, user_id, "Nota modificada en la orden",
                 f"Antes: {row[1]}\nAhora: {body}")
    await db.commit()
    return await list_notes(db, order_id, user_id)


async def delete_note(db: AsyncSession, order_id: int, note_id: int, user_id: int) -> dict:
    if not await notes_ready(db):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La nota no existe.")
    row = (await db.execute(text("""
        SELECT on_user_id, on_text FROM "OrderNotes" WHERE on_id = :n AND on_order_id = :o
    """), {"n": note_id, "o": order_id})).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La nota no existe.")
    if row[0] != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo quien escribió la nota puede eliminarla.")
    await db.execute(text('DELETE FROM "OrderNotes" WHERE on_id = :n'), {"n": note_id})
    await _trace(db, OPERATION_DELETE_ORDER_NOTE, order_id, user_id, "Nota eliminada de la orden", row[1])
    await db.commit()
    return await list_notes(db, order_id, user_id)
