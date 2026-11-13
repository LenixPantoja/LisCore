"""
Casos de uso del módulo de Alarmas y Críticos.

Flujo de una alarma:
    NUEVA ──(se avisa al médico)──► NOTIFICADA ──(el médico confirma)──► ACUSADA ──► CERRADA
      │                                                                   ▲
      └──(pasa el tiempo meta / escalar)──► ESCALADA ──(se avisa)─────────┘
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.domains.alarms.domain import constants as C
from app.domains.alarms.infrastructure import detector
from app.domains.alarms.infrastructure.detector import (
    add_event, alarms_ready, enterprise_ready, fmt, messages_ready, parse_weeks, pregnancy_ready,
)
from app.domains.alarms.infrastructure.repository import AlarmRepository
from app.shared.utils.range_evaluator import (
    SEX_TYPE_IDS_FEMALE,
    SEX_TYPE_IDS_MALE,
    bulk_fetch_ranges,
    evaluate_reference_range_sync,
)
from utils.timezone import get_bogota_now

logger = logging.getLogger(__name__)


def _require_ready(ready: bool) -> None:
    if not ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El módulo de alarmas no está instalado: falta correr el script SQL 062_alarmas_criticos.sql.",
        )


def _f(v) -> Optional[float]:
    return float(v) if v is not None else None


def _user_name(user) -> str:
    name = " ".join(x for x in [user.usr_first_name, user.usr_last_name] if x).strip()
    return name or user.usr_login or f"Usuario {user.usr_id}"


def _sex(sex_type: Optional[int]) -> Optional[str]:
    if sex_type in SEX_TYPE_IDS_MALE:
        return "H"
    if sex_type in SEX_TYPE_IDS_FEMALE:
        return "M"
    return "I" if sex_type else None


def _age_label(dob: Optional[date], at: Optional[datetime], o_age: Optional[str]) -> str:
    if dob:
        ref = (at or get_bogota_now()).date()
        days = (ref - dob).days
        years = ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))
        if years >= 2:
            return f"{years} años"
        months = (ref.year - dob.year) * 12 + ref.month - dob.month - (1 if ref.day < dob.day else 0)
        return f"{months} meses" if months >= 1 else f"{max(days, 0)} días"
    return o_age or ""


def _origin(r) -> dict:
    """
    De dónde salió el valor:
      - FORMULA: prueba calculada por el sistema.
      - MANUAL: alguien lo digitó/corrigió en el LIS (traza de edición posterior a la transmisión).
      - ANALIZADOR: lo envió el analizador (a_analyzer_result_id).
    """
    if r.test_is_formula:
        return {"type": "FORMULA", "label": "Calculado por fórmula", "analyzer": None, "user": None, "at": None}
    manual_after_tx = r.manual_at is not None and (r.l_date_transmited is None or r.manual_at >= r.l_date_transmited)
    if manual_after_tx or (r.a_analyzer_result_id is None and r.l_date_transmited is None):
        user = r.manual_user or None
        label = f"Digitado por {user}" if user else "Digitado manualmente"
        if r.analyzer_name and manual_after_tx:
            label += f" (corrigió el valor de {r.analyzer_name})"
        return {"type": "MANUAL", "label": label, "analyzer": r.analyzer_name, "user": user, "at": r.manual_at}
    name = r.analyzer_name or "Analizador"
    return {"type": "ANALIZADOR", "label": f"Analizador {name}" if r.analyzer_name else "Analizador",
            "analyzer": r.analyzer_name, "user": None, "at": r.l_date_transmited}


def _alarm_dict(r) -> dict:
    name = " ".join(x for x in [r.pt_firts_name, r.pt_middle_name, r.pt_last_name, r.pt_second_last_name] if x)
    hq = f"{r.hq_prefix}-{r.o_hq_consecutive}" if r.hq_prefix and r.o_hq_consecutive else (
        str(r.o_hq_consecutive) if r.o_hq_consecutive else "")
    limits = r.al_limits or {}
    return {
        "id": r.al_id,
        "level": r.al_level,
        "state": r.al_state,
        "direction": r.al_direction,
        "value": _f(r.al_value),
        "current_value": _f(r.al_last_value),
        "limit": _f(r.al_limit),
        "limits": {
            "panic_low": limits.get("panic_low"), "critical_low": limits.get("critical_low"),
            "critical_high": limits.get("critical_high"), "panic_high": limits.get("panic_high"),
            "delta_pct": limits.get("delta_pct"),
        },
        "previous": ({"value": _f(r.al_previous_value), "date": r.al_previous_date, "order_number": r.al_previous_order}
                     if r.al_previous_value is not None else None),
        "notify_minutes": r.al_notify_minutes,
        "block_validation": bool(r.al_block_validation),
        "detected_at": r.al_detected_at,
        "due_at": r.al_detected_at + timedelta(minutes=r.al_notify_minutes or 30),
        "notified_at": r.al_notified_at,
        "notified_by": r.notified_by_name or None,
        "closed_at": r.al_closed_at,
        "laboratory_id": r.al_laboratory_id,
        "lab_state": r.l_state,
        "origin": _origin(r),
        "source": _origin(r)["label"],
        "message": r.al_message,
        "order": {
            "id": r.al_order_id, "number": r.o_number, "hq_code": hq, "hq_name": r.hq_name,
            "urgent": (r.o_priority or 0) > 0, "service": r.service_name, "created_at": r.o_created_at,
            "enterprise": r.enterprise_name,
        },
        "area": {"id": r.wg_id, "name": r.wg_name or "Sin área"},
        "test": {"id": r.al_test_id, "code": r.test_code, "name": r.test_name, "unit": (r.test_units or "").strip()},
        "patient": {
            "id": r.al_patient_id, "name": name, "document": r.pt_document or "",
            "sex": _sex(r.pt_sex_type), "age": _age_label(r.pt_date_of_birth, r.o_created_at, r.o_age),
            "phone": r.pt_phone_number,
            "pregnant": bool(r.o_pregnated),
            "pregnancy_weeks": parse_weeks(r.o_week_pregnated) if r.o_pregnated else None,
        },
        "medic": ({"id": r.med_id, "codigo": r.med_codigo, "name": r.med_name, "specialty": r.med_specialty,
                   "phone": r.med_phone, "mail": r.med_mail} if r.med_id else None),
    }


def _event_dict(e) -> dict:
    return {
        "id": e.ae_id, "type": e.ae_type, "user": e.ae_user_name or C.SYSTEM_USER, "channel": e.ae_channel,
        "contact": e.ae_contact, "read_back": e.ae_read_back, "detail": e.ae_detail, "at": e.ae_created_at,
    }


# ── Bandeja ────────────────────────────────────────────────────────────────────
async def list_alarms(db: AsyncSession, *, date_from: Optional[date], date_to: Optional[date], state: Optional[str],
                      level: Optional[str], area_id: Optional[int], search: Optional[str], limit: int) -> dict:
    _require_ready(await alarms_ready(db))
    today = get_bogota_now().date()
    d_to = date_to or today
    d_from = date_from or (d_to - timedelta(days=7))
    if d_from > d_to:
        d_from, d_to = d_to, d_from
    rows, counts = await AlarmRepository.list_alarms(
        db, date_from=datetime.combine(d_from, datetime.min.time()),
        date_to=datetime.combine(d_to, datetime.max.time()), state=state, level=level,
        area_id=area_id, search=search, limit=limit, msgs_ok=await messages_ready(db),
    )
    total = sum(counts.values())
    state_counts = {s: counts.get(s, 0) for s in C.STATES}
    state_counts["ACTIVAS"] = total - counts.get(C.STATE_CERRADA, 0)
    state_counts["TODAS"] = total
    return {"items": [_alarm_dict(r) for r in rows], "state_counts": state_counts,
            "date_from": d_from, "date_to": d_to}


async def get_alarm(db: AsyncSession, alarm_id: int) -> dict:
    _require_ready(await alarms_ready(db))
    r = await AlarmRepository.get_alarm(db, alarm_id, await messages_ready(db))
    if r is None:
        raise HTTPException(status_code=404, detail="Alarma no encontrada")
    data = _alarm_dict(r)
    data["events"] = [_event_dict(e) for e in await AlarmRepository.get_events(db, alarm_id)]
    # Rango de referencia (normal) del paciente, para comparar
    try:
        ranges = (await bulk_fetch_ranges(db, [r.al_test_id])).get(r.al_test_id, [])
        _, ref_low, ref_high = evaluate_reference_range_sync(ranges, r.al_value, r.pt_date_of_birth, r.pt_sex_type)
        data["reference"] = {"low": _f(ref_low), "high": _f(ref_high)}
    except Exception:
        data["reference"] = {"low": None, "high": None}
    return data


async def alarms_for_order(db: AsyncSession, order_number: str) -> list[dict]:
    if not await alarms_ready(db):
        return []
    return [_alarm_dict(r) for r in await AlarmRepository.alarms_for_order(db, order_number.strip(), await messages_ready(db))]


async def summary(db: AsyncSession, after_id: Optional[int]) -> dict:
    if not await alarms_ready(db):
        return {"allowed": True, "installed": False, "active": 0, "active_panic": 0, "pending": 0,
                "pending_panic": 0, "overdue": 0, "latest_id": 0, "new_pending": [],
                "kpi": {"notified": 0, "avg_minutes": None, "on_time_pct": None}}
    now = get_bogota_now()
    counts, kpi, latest_id = await AlarmRepository.summary(db, now, now - timedelta(days=30))
    new_pending = []
    if after_id is not None and latest_id > after_id:
        new_pending = [{
            "id": n.al_id, "level": n.al_level, "value": _f(n.al_value), "direction": n.al_direction,
            "test_name": n.test_name, "unit": (n.units or "").strip(), "order_number": n.o_number,
            "patient_name": n.patient_name, "message": n.al_message, "worsened": bool(n.worsened),
        } for n in await AlarmRepository.new_pending(db, after_id, await messages_ready(db))]
    notified = kpi.notified or 0
    return {
        "allowed": True, "installed": True,
        "active": counts.active or 0, "active_panic": counts.active_panic or 0,
        "pending": counts.pending or 0, "pending_panic": counts.pending_panic or 0,
        "overdue": counts.overdue or 0, "latest_id": latest_id or 0, "new_pending": new_pending,
        "kpi": {
            "notified": notified,
            "avg_minutes": round(float(kpi.avg_minutes)) if kpi.avg_minutes is not None else None,
            "on_time_pct": round(100 * (kpi.on_time or 0) / notified) if notified else None,
        },
    }


# ── Acciones sobre una alarma ──────────────────────────────────────────────────
async def _locked(db: AsyncSession, alarm_id: int):
    _require_ready(await alarms_ready(db))
    a = await AlarmRepository.lock_alarm(db, alarm_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Alarma no encontrada")
    if a.al_state == C.STATE_CERRADA:
        raise HTTPException(status_code=409, detail="La alarma ya está cerrada")
    return a


async def notify(db: AsyncSession, alarm_id: int, user, channel: str, contact: str,
                 read_back: bool, note: Optional[str]) -> dict:
    a = await _locked(db, alarm_id)
    if channel in ("LLAMADA", "PRESENCIAL") and not read_back:
        raise HTTPException(
            status_code=400,
            detail="Confirme la verificación de lectura: el médico debe repetir el resultado y el nombre del paciente.",
        )
    now = get_bogota_now()
    first = a.al_state in C.PENDING_STATES
    if first:
        await db.execute(text("""
            UPDATE "Alarms" SET al_state = 'NOTIFICADA', al_notified_at = COALESCE(al_notified_at, :now),
                   al_notified_by = COALESCE(al_notified_by, :uid), al_updated_at = :now
            WHERE al_id = :id
        """), {"id": alarm_id, "now": now, "uid": user.usr_id})
    detail = (f"{C.CHANNEL_LABEL[channel]} a {contact}. Verificación de lectura: {'SÍ' if read_back else 'NO'}."
              + (f" {note.strip()}" if note and note.strip() else ""))
    await add_event(db, alarm_id, C.EV_NOTIFICADA if first else C.EV_NOTA,
                    detail if first else f"Nueva notificación: {detail}",
                    user_id=user.usr_id, user_name=_user_name(user), channel=channel,
                    contact=contact, read_back=read_back, now=now)
    await db.commit()
    return await get_alarm(db, alarm_id)


async def acknowledge(db: AsyncSession, alarm_id: int, user, note: Optional[str]) -> dict:
    a = await _locked(db, alarm_id)
    if a.al_state != C.STATE_NOTIFICADA:
        raise HTTPException(status_code=409, detail="Primero registre la notificación al médico")
    now = get_bogota_now()
    await db.execute(text('UPDATE "Alarms" SET al_state = \'ACUSADA\', al_updated_at = :now WHERE al_id = :id'),
                     {"id": alarm_id, "now": now})
    await add_event(db, alarm_id, C.EV_ACUSADA,
                    "El médico confirmó que recibió el resultado." + (f" {note.strip()}" if note and note.strip() else ""),
                    user_id=user.usr_id, user_name=_user_name(user), now=now)
    await db.commit()
    return await get_alarm(db, alarm_id)


async def escalate(db: AsyncSession, alarm_id: int, user, note: str) -> dict:
    a = await _locked(db, alarm_id)
    if a.al_state != C.STATE_NUEVA:
        raise HTTPException(status_code=409, detail="Solo se pueden escalar alarmas sin notificar")
    now = get_bogota_now()
    await db.execute(text('UPDATE "Alarms" SET al_state = \'ESCALADA\', al_updated_at = :now WHERE al_id = :id'),
                     {"id": alarm_id, "now": now})
    await add_event(db, alarm_id, C.EV_ESCALADA, f"Escalada manualmente: {note.strip()}",
                    user_id=user.usr_id, user_name=_user_name(user), now=now)
    await db.commit()
    return await get_alarm(db, alarm_id)


async def add_note(db: AsyncSession, alarm_id: int, user, note: str) -> dict:
    _require_ready(await alarms_ready(db))
    if await AlarmRepository.lock_alarm(db, alarm_id) is None:
        raise HTTPException(status_code=404, detail="Alarma no encontrada")
    await add_event(db, alarm_id, C.EV_NOTA, note.strip(), user_id=user.usr_id, user_name=_user_name(user))
    await db.commit()
    return await get_alarm(db, alarm_id)


async def close(db: AsyncSession, alarm_id: int, user, reason: str, without_notification: bool) -> dict:
    a = await _locked(db, alarm_id)
    if a.al_state in C.PENDING_STATES and not without_notification:
        raise HTTPException(
            status_code=409,
            detail="Primero registre la notificación al médico. Si el resultado no es válido "
                   "(muestra hemolizada, coagulada, error de digitación…), marque 'Cerrar sin notificar'.",
        )
    now = get_bogota_now()
    await db.execute(text("""
        UPDATE "Alarms" SET al_state = 'CERRADA', al_closed_at = :now, al_closed_by = :uid, al_updated_at = :now
        WHERE al_id = :id
    """), {"id": alarm_id, "now": now, "uid": user.usr_id})
    prefix = "Cerrada SIN notificar al médico (resultado no válido): " if a.al_state in C.PENDING_STATES else "Cerrada: "
    await add_event(db, alarm_id, C.EV_CERRADA, prefix + reason.strip(),
                    user_id=user.usr_id, user_name=_user_name(user), now=now)
    await db.commit()
    return await get_alarm(db, alarm_id)


async def scan(db: AsyncSession, hours: int) -> dict:
    """Revisa ahora los resultados de las últimas `hours` horas (p.ej. tras activar reglas)."""
    _require_ready(await alarms_ready(db))
    now = get_bogota_now()
    created = await detector.evaluate(db, since=now - timedelta(hours=hours),
                                      lookback_days=max(detector.LOOKBACK_DAYS, hours // 24 + 1))
    escalated = await detector.escalate_overdue(db)
    await db.commit()
    return {"created": created, "escalated": escalated, "hours": hours}


# ── Reglas ─────────────────────────────────────────────────────────────────────
def _rule_dict(r) -> dict:
    return {
        "id": r.cr_id, "test_id": r.cr_test_id, "test_code": r.test_code, "test_name": r.test_name,
        "unit": (r.test_units or "").strip(), "area": r.area_name or "Sin área",
        "gender": r.cr_gender, "age_type": r.cr_age_type, "min_age": r.cr_min_age, "max_age": r.cr_max_age,
        "panic_low": _f(r.cr_panic_low), "critical_low": _f(r.cr_critical_low),
        "critical_high": _f(r.cr_critical_high), "panic_high": _f(r.cr_panic_high),
        "delta_pct": _f(r.cr_delta_pct), "delta_days": r.cr_delta_days,
        "notify_minutes": r.cr_notify_minutes, "block_validation": bool(r.cr_block_validation),
        "active": bool(r.cr_active), "note": r.cr_note, "updated_at": r.cr_updated_at,
        "msg_panic_low": getattr(r, "cr_msg_panic_low", None), "msg_critical_low": getattr(r, "cr_msg_critical_low", None),
        "msg_critical_high": getattr(r, "cr_msg_critical_high", None), "msg_panic_high": getattr(r, "cr_msg_panic_high", None),
        "msg_delta": getattr(r, "cr_msg_delta", None),
        "pregnancy": getattr(r, "cr_pregnancy", None) or "TODAS",
        "min_week": getattr(r, "cr_min_week", None), "max_week": getattr(r, "cr_max_week", None),
        "enterprise_id": r.enterprise_id, "enterprise_name": r.enterprise_name,
        "updated_by": r.updated_by_name or None, "alarms_count": r.alarms_count or 0,
    }


async def list_rules(db: AsyncSession, search: Optional[str], active: Optional[bool]) -> list[dict]:
    _require_ready(await alarms_ready(db))
    return [_rule_dict(r) for r in await AlarmRepository.list_rules(db, search, active)]


async def rules_for_test(db: AsyncSession, test_id: int) -> list[dict]:
    if not await alarms_ready(db):
        return []
    return [_rule_dict(r) for r in await AlarmRepository.rules_for_test(db, test_id)]


async def search_tests(db: AsyncSession, search: Optional[str]) -> list[dict]:
    _require_ready(await alarms_ready(db))
    return [{"id": t.id, "code": t.code, "name": t.name, "unit": (t.units or "").strip(),
             "area": t.area_name or "Sin área", "rules_count": t.rules_count or 0}
            for t in await AlarmRepository.search_tests(db, search)]


def _check_rule(d: dict) -> None:
    pl, cl, ch, ph = (d.get(k) for k in ("panic_low", "critical_low", "critical_high", "panic_high"))
    if all(v is None for v in (pl, cl, ch, ph, d.get("delta_pct"))):
        raise HTTPException(400, "Escriba al menos un límite (pánico, crítico o delta)")
    if pl is not None and cl is not None and pl > cl:
        raise HTTPException(400, "El pánico bajo debe ser menor o igual que el crítico bajo")
    if ch is not None and ph is not None and ch > ph:
        raise HTTPException(400, "El crítico alto debe ser menor o igual que el pánico alto")
    lows = [v for v in (pl, cl) if v is not None]
    highs = [v for v in (ch, ph) if v is not None]
    if lows and highs and max(lows) >= min(highs):
        raise HTTPException(400, "Los límites bajos deben ser menores que los límites altos")
    if d.get("min_age") is not None and d.get("max_age") is not None and d["min_age"] > d["max_age"]:
        raise HTTPException(400, "La edad mínima debe ser menor o igual que la máxima")
    if (d.get("pregnancy") or "TODAS") != "EMBARAZADA":
        d["min_week"] = d["max_week"] = None
    elif d.get("min_week") is not None and d.get("max_week") is not None and d["min_week"] > d["max_week"]:
        raise HTTPException(400, "La semana de gestación mínima debe ser menor o igual que la máxima")


_RULE_FIELDS = ("test_id", "gender", "age_type", "min_age", "max_age", "panic_low", "critical_low",
                "critical_high", "panic_high", "delta_pct", "delta_days", "notify_minutes",
                "block_validation", "active", "note")
_MSG_FIELDS = ("msg_panic_low", "msg_critical_low", "msg_critical_high", "msg_panic_high", "msg_delta")
_PREG_FIELDS = ("pregnancy", "min_week", "max_week")


async def _fields(db: AsyncSession) -> tuple:
    return (_RULE_FIELDS + (_MSG_FIELDS if await messages_ready(db) else ())
            + (_PREG_FIELDS if await pregnancy_ready(db) else ())
            + (("enterprise_id",) if await enterprise_ready(db) else ()))


async def search_enterprises(db: AsyncSession, search: Optional[str]) -> list[dict]:
    return [{"id": e.en_id, "code": e.en_code, "name": e.en_name, "nit": e.en_nit}
            for e in await AlarmRepository.search_enterprises(db, search)]


async def _check_enterprise(db: AsyncSession, data: dict) -> None:
    if data.get("enterprise_id") is not None:
        if not (await db.execute(text('SELECT 1 FROM "Enterprises" WHERE en_id = :id'), {"id": data["enterprise_id"]})).first():
            raise HTTPException(404, "La empresa no existe")


async def create_rule(db: AsyncSession, data: dict, user) -> dict:
    _require_ready(await alarms_ready(db))
    data["pregnancy"] = data.get("pregnancy") or "TODAS"
    _check_rule(data)
    await _check_enterprise(db, data)
    if not (await db.execute(text('SELECT 1 FROM "TestsLab" WHERE id = :id'), {"id": data["test_id"]})).first():
        raise HTTPException(404, "La prueba no existe")
    now = get_bogota_now()
    fields = await _fields(db)
    cols = ", ".join(f"cr_{k}" for k in fields)
    vals = ", ".join(f":{k}" for k in fields)
    try:
        new_id = (await db.execute(text(f"""
            INSERT INTO "CriticalRules" ({cols}, cr_created_by, cr_updated_by, cr_created_at, cr_updated_at)
            VALUES ({vals}, :uid, :uid, :now, :now) RETURNING cr_id
        """), {**{k: data.get(k) for k in fields}, "uid": user.usr_id, "now": now})).scalar()
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(400, f"Regla inválida: {e.orig}")
    return _rule_dict(await AlarmRepository.get_rule(db, new_id))


async def update_rule(db: AsyncSession, rule_id: int, data: dict, user) -> dict:
    _require_ready(await alarms_ready(db))
    current = await AlarmRepository.get_rule(db, rule_id)
    if current is None:
        raise HTTPException(404, "Regla no encontrada")
    if "pregnancy" in data and not data["pregnancy"]:
        data["pregnancy"] = "TODAS"
    merged = {k: getattr(current, f"cr_{k}", None) for k in _RULE_FIELDS + _PREG_FIELDS}
    merged.update(data)
    for k in ("panic_low", "critical_low", "critical_high", "panic_high", "delta_pct"):
        if merged[k] is not None:
            merged[k] = Decimal(str(merged[k]))
    _check_rule(merged)
    await _check_enterprise(db, data)
    if "pregnancy" in data:  # al cambiar a TODAS / NO_EMBARAZADA se limpian las semanas
        data["min_week"], data["max_week"] = merged["min_week"], merged["max_week"]
    allowed = await _fields(db)
    data = {k: v for k, v in data.items() if k in allowed}
    if not data:
        return _rule_dict(current)
    sets = ", ".join(f"cr_{k} = :{k}" for k in data)
    try:
        await db.execute(text(f"""
            UPDATE "CriticalRules" SET {sets}, cr_updated_by = :uid, cr_updated_at = :now WHERE cr_id = :id
        """), {**data, "uid": user.usr_id, "now": get_bogota_now(), "id": rule_id})
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(400, f"Regla inválida: {e.orig}")
    return _rule_dict(await AlarmRepository.get_rule(db, rule_id))


async def delete_rule(db: AsyncSession, rule_id: int) -> dict:
    """Elimina una regla solo si nunca generó alarmas; si ya las generó, se debe desactivar."""
    _require_ready(await alarms_ready(db))
    current = await AlarmRepository.get_rule(db, rule_id)
    if current is None:
        raise HTTPException(404, "Regla no encontrada")
    if current.alarms_count:
        raise HTTPException(
            409,
            f"Esta regla ya generó {current.alarms_count} alarma(s) y se conserva para la trazabilidad. "
            "Desactívela en lugar de eliminarla.",
        )
    await db.execute(text('DELETE FROM "CriticalRules" WHERE cr_id = :id'), {"id": rule_id})
    await db.commit()
    return {"deleted": True, "id": rule_id}


# ── Bloqueo de validación ──────────────────────────────────────────────────────
async def check_validation_block(db: AsyncSession, l_ids: list[int]) -> None:
    """
    Impide validar resultados cuya alarma (con 'bloquea validación') aún no se
    ha notificado al médico. Antes revisa esas órdenes para no depender del barrido.
    Si algo falla, no bloquea (la validación es más importante que la alarma).
    """
    if not l_ids:
        return
    try:
        if not await alarms_ready(db):
            return
        order_ids = list((await db.execute(text("""
            SELECT DISTINCT od.od_order_id FROM "Laboratories" l
            JOIN "OrdersDetails" od ON od.od_id = l.l_order_detail_id WHERE l.l_id = ANY(:ids)
        """), {"ids": l_ids})).scalars().all())
        async with async_session() as s:
            await detector.evaluate(s, order_ids=order_ids)
            await s.commit()
        rows = (await db.execute(text("""
            SELECT a.al_level, a.al_value, t.name, t.units
            FROM "Alarms" a JOIN "TestsLab" t ON t.id = a.al_test_id
            WHERE a.al_laboratory_id = ANY(:ids) AND a.al_block_validation
              AND a.al_state IN ('NUEVA', 'ESCALADA')
        """), {"ids": l_ids})).all()
    except Exception:
        logger.exception("No se pudo revisar el bloqueo de validación por alarmas")
        return
    if rows:
        items = "; ".join(
            f"{r.name} = {fmt(r.al_value)}{(' ' + r.units.strip()) if r.units and r.units.strip() else ''} "
            f"({C.LEVEL_LABEL[r.al_level]})" for r in rows)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede validar: {items}. Este valor crítico aún no se ha notificado al médico. "
                   "Registre la notificación en 'Alarmas y Críticos' y vuelva a validar.",
        )
