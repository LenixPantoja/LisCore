from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    _get_cached_permission,
    _set_cached_permission,
    get_current_user,
    require_permission,
)
from app.domains.alarms.api.schemas import (
    AcknowledgeRequest,
    CloseRequest,
    NoteRequest,
    NotifyRequest,
    RuleCreate,
    RuleUpdate,
)
from app.domains.alarms.application.use_cases import alarm_use_cases as uc
from app.domains.users.infrastructure.models import AppUser
from app.domains.users.infrastructure.repository import PermissionRepository

router = APIRouter(redirect_slashes=False)

StateFilter = Literal["ACTIVAS", "NUEVA", "NOTIFICADA", "ACUSADA", "ESCALADA", "CERRADA", "TODAS"]
LevelFilter = Literal["PANICO", "CRITICO", "DELTA"]


@router.get("/summary")
async def alarms_summary(
    after_id: Optional[int] = Query(None, ge=0, description="Devuelve las alarmas pendientes nuevas con id mayor a este"),
    user: AppUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Contador del menú e indicadores. Solo requiere sesión: si el usuario no
    tiene 'Alarms:List' responde {allowed: false} (sin 403, para que el menú
    no muestre errores a quien no usa el módulo).
    """
    allowed = _get_cached_permission(user.usr_rol_id, "Alarms:List")
    if allowed is None:
        allowed = await PermissionRepository.role_has_permission(db, user.usr_rol_id, "Alarms:List")
        _set_cached_permission(user.usr_rol_id, "Alarms:List", allowed)
    if not allowed:
        return {"allowed": False}
    return await uc.summary(db, after_id)


@router.get("", dependencies=[Depends(require_permission("Alarms:List"))])
async def list_alarms(
    state: StateFilter = Query("ACTIVAS"),
    level: Optional[LevelFilter] = Query(None),
    area_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None, max_length=100),
    date_from: Optional[date] = Query(None, description="Las cerradas se filtran por fecha de detección; las abiertas siempre aparecen"),
    date_to: Optional[date] = Query(None),
    limit: int = Query(300, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    return await uc.list_alarms(db, date_from=date_from, date_to=date_to, state=state, level=level,
                                area_id=area_id, search=search, limit=limit)


@router.get("/by-order/{order_number}", dependencies=[Depends(require_permission("Alarms:List"))])
async def alarms_by_order(order_number: str, db: AsyncSession = Depends(get_db)):
    return await uc.alarms_for_order(db, order_number)


# ── Reglas (antes de /{alarm_id} para que no choquen las rutas) ───────────────
@router.get("/rules", dependencies=[Depends(require_permission("Alarms:List"))])
async def list_rules(
    search: Optional[str] = Query(None, max_length=100),
    active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await uc.list_rules(db, search, active)


async def _has(db: AsyncSession, user: AppUser, permission: str) -> bool:
    cached = _get_cached_permission(user.usr_rol_id, permission)
    if cached is None:
        cached = await PermissionRepository.role_has_permission(db, user.usr_rol_id, permission)
        _set_cached_permission(user.usr_rol_id, permission, cached)
    return cached


@router.get("/rules/by-test/{test_id}")
async def rules_by_test(test_id: int, user: AppUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Valores críticos de una prueba (sección de la gestión de Pruebas). Solo
    requiere sesión: responde allowed/can_edit en vez de 403 para que la
    pantalla de pruebas no muestre errores a quien no maneja el módulo.
    """
    can_edit = await _has(db, user, "Alarms:Rules")
    allowed = can_edit or await _has(db, user, "Alarms:List")
    if not allowed:
        return {"allowed": False, "can_edit": False, "installed": True, "rules": []}
    from app.domains.alarms.infrastructure.detector import alarms_ready
    installed = await alarms_ready(db)
    return {"allowed": True, "can_edit": can_edit, "installed": installed,
            "rules": await uc.rules_for_test(db, test_id) if installed else []}


@router.get("/rules/enterprises", dependencies=[Depends(require_permission("Alarms:Rules"))])
async def search_enterprises(search: Optional[str] = Query(None, max_length=100), db: AsyncSession = Depends(get_db)):
    """Empresas para las reglas exclusivas por cliente."""
    return await uc.search_enterprises(db, search)


@router.get("/rules/tests", dependencies=[Depends(require_permission("Alarms:Rules"))])
async def search_tests(search: Optional[str] = Query(None, max_length=100), db: AsyncSession = Depends(get_db)):
    return await uc.search_tests(db, search)


@router.post("/rules", status_code=status.HTTP_201_CREATED)
async def create_rule(body: RuleCreate, user: AppUser = Depends(require_permission("Alarms:Rules")),
                      db: AsyncSession = Depends(get_db)):
    return await uc.create_rule(db, body.model_dump(), user)


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: int, body: RuleUpdate, user: AppUser = Depends(require_permission("Alarms:Rules")),
                      db: AsyncSession = Depends(get_db)):
    return await uc.update_rule(db, rule_id, body.model_dump(exclude_unset=True), user)


@router.delete("/rules/{rule_id}", dependencies=[Depends(require_permission("Alarms:Rules"))])
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    """Elimina la regla si nunca generó alarmas (si ya generó, hay que desactivarla)."""
    return await uc.delete_rule(db, rule_id)


@router.post("/scan", dependencies=[Depends(require_permission("Alarms:Rules"))])
async def scan_now(hours: int = Query(24, ge=1, le=72), db: AsyncSession = Depends(get_db)):
    """Revisa ya los resultados de las últimas horas (útil después de activar reglas)."""
    return await uc.scan(db, hours)


# ── Una alarma ────────────────────────────────────────────────────────────────
@router.get("/{alarm_id}", dependencies=[Depends(require_permission("Alarms:List"))])
async def get_alarm(alarm_id: int, db: AsyncSession = Depends(get_db)):
    return await uc.get_alarm(db, alarm_id)


@router.post("/{alarm_id}/notify")
async def notify(alarm_id: int, body: NotifyRequest, user: AppUser = Depends(require_permission("Alarms:Manage")),
                 db: AsyncSession = Depends(get_db)):
    return await uc.notify(db, alarm_id, user, body.channel, body.contact, body.read_back, body.note)


@router.post("/{alarm_id}/acknowledge")
async def acknowledge(alarm_id: int, body: AcknowledgeRequest,
                      user: AppUser = Depends(require_permission("Alarms:Manage")),
                      db: AsyncSession = Depends(get_db)):
    return await uc.acknowledge(db, alarm_id, user, body.note)


@router.post("/{alarm_id}/escalate")
async def escalate(alarm_id: int, body: NoteRequest, user: AppUser = Depends(require_permission("Alarms:Manage")),
                   db: AsyncSession = Depends(get_db)):
    return await uc.escalate(db, alarm_id, user, body.note)


@router.post("/{alarm_id}/note")
async def add_note(alarm_id: int, body: NoteRequest, user: AppUser = Depends(require_permission("Alarms:Manage")),
                   db: AsyncSession = Depends(get_db)):
    return await uc.add_note(db, alarm_id, user, body.note)


@router.post("/{alarm_id}/close")
async def close(alarm_id: int, body: CloseRequest, user: AppUser = Depends(require_permission("Alarms:Manage")),
                db: AsyncSession = Depends(get_db)):
    return await uc.close(db, alarm_id, user, body.reason, body.without_notification)
