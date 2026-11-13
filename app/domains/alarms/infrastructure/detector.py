"""
Detección de valores críticos.

Revisa los resultados numéricos de las pruebas que tienen una regla activa en
"CriticalRules" y crea/actualiza la alarma de ese resultado en "Alarms":

  - Resultado < pánico bajo  o > pánico alto  → PANICO
  - Resultado < crítico bajo o > crítico alto → CRITICO
  - Cambio frente al resultado anterior del paciente ≥ delta % → DELTA

Se ejecuta:
  - al instante cuando llega un resultado (notificación de Postgres, ver
    laboratories/infrastructure/formula_listener.py);
  - en el barrido periódico (cada minuto), que además escala las alarmas que
    superaron su tiempo meta sin notificarse y cierra las que quedaron sin
    resultado (resultado borrado / prueba descartada / orden anulada);
  - antes de validar, para que el bloqueo de validación no dependa del barrido.

Si las tablas del módulo aún no existen (SQL 062 sin correr), no hace nada.
"""
import json
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Iterable, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.alarms.domain import constants as C
from app.shared.utils.range_evaluator import SEX_TYPE_IDS_FEMALE, SEX_TYPE_IDS_MALE
from utils.timezone import get_bogota_now

logger = logging.getLogger(__name__)

# Solo se revisan órdenes creadas en este periodo (evita alarmas de historia vieja)
LOOKBACK_DAYS = 3
# Al arrancar el backend se revisan los resultados de las últimas horas
CATCH_UP_HOURS = 12

# ── ¿Existen las tablas del módulo? (cacheado) ─────────────────────────────────
_ready_cache: tuple[bool, float] = (False, 0.0)


_msgs_cache: tuple[bool, float] = (False, 0.0)


async def messages_ready(db: AsyncSession) -> bool:
    """¿Existen las columnas de mensaje clínico (SQL 063)?"""
    global _msgs_cache
    ok, checked = _msgs_cache
    if ok or time.monotonic() - checked < 300:
        return ok
    try:
        exists = (await db.execute(text("""
            SELECT count(*) = 2 FROM information_schema.columns
            WHERE (table_name = 'Alarms' AND column_name = 'al_message')
               OR (table_name = 'CriticalRules' AND column_name = 'cr_msg_panic_high')
        """))).scalar()
    except Exception:
        exists = False
    _msgs_cache = (bool(exists), time.monotonic())
    return bool(exists)


_preg_cache: tuple[bool, float] = (False, 0.0)


async def pregnancy_ready(db: AsyncSession) -> bool:
    """¿Existen las columnas de embarazo en las reglas (SQL 064)?"""
    global _preg_cache
    ok, checked = _preg_cache
    if ok or time.monotonic() - checked < 300:
        return ok
    try:
        exists = (await db.execute(text("""
            SELECT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name = 'CriticalRules' AND column_name = 'cr_pregnancy')
        """))).scalar()
    except Exception:
        exists = False
    _preg_cache = (bool(exists), time.monotonic())
    return bool(exists)


_ent_cache: tuple[bool, float] = (False, 0.0)


async def enterprise_ready(db: AsyncSession) -> bool:
    """¿Existe la columna de empresa en las reglas (SQL 065)?"""
    global _ent_cache
    ok, checked = _ent_cache
    if ok or time.monotonic() - checked < 300:
        return ok
    try:
        exists = (await db.execute(text("""
            SELECT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name = 'CriticalRules' AND column_name = 'cr_enterprise_id')
        """))).scalar()
    except Exception:
        exists = False
    _ent_cache = (bool(exists), time.monotonic())
    return bool(exists)


def parse_weeks(v) -> Optional[int]:
    """Semanas de gestación desde Orders.o_week_pregnated ('28', '28 semanas', '12.5')."""
    if v is None:
        return None
    digits = ""
    for ch in str(v).strip():
        if ch.isdigit():
            digits += ch
        elif digits:
            break
    return int(digits) if digits and int(digits) <= 45 else None


async def alarms_ready(db: AsyncSession) -> bool:
    global _ready_cache
    ok, checked = _ready_cache
    if ok or time.monotonic() - checked < 300:
        return ok
    try:
        exists = (await db.execute(text(
            "SELECT to_regclass('\"Alarms\"') IS NOT NULL AND to_regclass('\"CriticalRules\"') IS NOT NULL"
        ))).scalar()
    except Exception:
        exists = False
    _ready_cache = (bool(exists), time.monotonic())
    return bool(exists)


# ── Utilidades ─────────────────────────────────────────────────────────────────
def parse_value(result_num, result_text) -> Optional[Decimal]:
    """Valor numérico del resultado (acepta '7,2', '<0.5', '> 1000')."""
    if result_num is not None:
        try:
            return Decimal(str(result_num))
        except InvalidOperation:
            pass
    if not result_text:
        return None
    s = str(result_text).strip().replace(",", ".").lstrip("<>=≤≥ ").strip()
    try:
        v = Decimal(s)
    except InvalidOperation:
        return None
    return v if v.is_finite() else None


def fmt(v) -> str:
    """Número sin ceros sobrantes: 7.20 → 7.2"""
    if v is None:
        return "—"
    d = Decimal(str(v))
    s = format(d.normalize(), "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def _age(dob: date, at: date, age_type: str) -> int:
    if age_type == "DIAS":
        return (at - dob).days
    months = (at.year - dob.year) * 12 + (at.month - dob.month) - (1 if at.day < dob.day else 0)
    if age_type == "MESES":
        return max(months, 0)
    return max(months // 12, 0)


def _num(v) -> Optional[Decimal]:
    return Decimal(str(v)) if v is not None else None


@dataclass
class Rule:
    id: int
    test_id: int
    gender: str
    age_type: str
    min_age: Optional[int]
    max_age: Optional[int]
    panic_low: Optional[Decimal]
    critical_low: Optional[Decimal]
    critical_high: Optional[Decimal]
    panic_high: Optional[Decimal]
    delta_pct: Optional[Decimal]
    delta_days: int
    notify_minutes: int
    block_validation: bool
    msg_panic_low: Optional[str] = None
    msg_critical_low: Optional[str] = None
    msg_critical_high: Optional[str] = None
    msg_panic_high: Optional[str] = None
    msg_delta: Optional[str] = None
    pregnancy: str = "TODAS"
    enterprise_id: Optional[int] = None
    min_week: Optional[int] = None
    max_week: Optional[int] = None

    def message(self, level: str, direction: Optional[str]) -> Optional[str]:
        """Mensaje clínico de la zona (si el de la zona está vacío, usa el del mismo lado)."""
        if level == "DELTA":
            return self.msg_delta
        if direction == "BAJO":
            first, second = ((self.msg_panic_low, self.msg_critical_low) if level == "PANICO"
                             else (self.msg_critical_low, self.msg_panic_low))
        else:
            first, second = ((self.msg_panic_high, self.msg_critical_high) if level == "PANICO"
                             else (self.msg_critical_high, self.msg_panic_high))
        return first or second

    def limits_json(self) -> dict:
        f = lambda v: float(v) if v is not None else None  # noqa: E731
        return {
            "panic_low": f(self.panic_low), "critical_low": f(self.critical_low),
            "critical_high": f(self.critical_high), "panic_high": f(self.panic_high),
            "delta_pct": f(self.delta_pct),
        }


def _rule_applies(r: Rule, sex_type_id: Optional[int], dob: Optional[date], at: date,
                  pregnant: bool = False, weeks: Optional[int] = None,
                  enterprise_id: Optional[int] = None) -> bool:
    if r.enterprise_id is not None and r.enterprise_id != enterprise_id:
        return False
    if r.pregnancy == "EMBARAZADA":
        if not pregnant:
            return False
        if r.min_week is not None or r.max_week is not None:
            if weeks is None:
                return False
            if r.min_week is not None and weeks < r.min_week:
                return False
            if r.max_week is not None and weeks > r.max_week:
                return False
    elif r.pregnancy == "NO_EMBARAZADA" and pregnant:
        return False
    if r.gender == "MASCULINO" and sex_type_id not in SEX_TYPE_IDS_MALE:
        return False
    if r.gender == "FEMENINO" and sex_type_id not in SEX_TYPE_IDS_FEMALE:
        return False
    if r.min_age is None and r.max_age is None:
        return True
    if dob is None:
        return False
    age = _age(dob, at, r.age_type or "AÑOS")
    if r.min_age is not None and age < r.min_age:
        return False
    if r.max_age is not None and age > r.max_age:
        return False
    return True


def pick_rule(rules: list[Rule], sex_type_id, dob, at: date,
              pregnant: bool = False, weeks: Optional[int] = None,
              enterprise_id: Optional[int] = None) -> Optional[Rule]:
    """La regla más específica que aplica: empresa > embarazo (con semanas) > sexo > edad."""
    ok = [r for r in rules if _rule_applies(r, sex_type_id, dob, at, pregnant, weeks, enterprise_id)]
    if not ok:
        return None
    ok.sort(key=lambda r: (
        r.enterprise_id is not None,
        r.pregnancy == "EMBARAZADA" and (r.min_week is not None or r.max_week is not None),
        r.pregnancy != "TODAS",
        r.gender != "AMBOS",
        r.min_age is not None or r.max_age is not None,
        -r.id,
    ), reverse=True)
    return ok[0]


def classify(v: Decimal, r: Rule) -> Optional[tuple[str, str, Decimal]]:
    """(nivel, dirección, límite cruzado) o None si el valor no es crítico."""
    if r.panic_low is not None and v < r.panic_low:
        return C.LEVEL_PANICO, "BAJO", r.panic_low
    if r.panic_high is not None and v > r.panic_high:
        return C.LEVEL_PANICO, "ALTO", r.panic_high
    if r.critical_low is not None and v < r.critical_low:
        return C.LEVEL_CRITICO, "BAJO", r.critical_low
    if r.critical_high is not None and v > r.critical_high:
        return C.LEVEL_CRITICO, "ALTO", r.critical_high
    return None


def describe(level: str, direction: Optional[str], limit, value, unit: Optional[str],
             prev_value=None, delta_pct=None) -> str:
    u = f" {unit.strip()}" if unit and unit.strip() else ""
    if level == C.LEVEL_DELTA:
        return (f"Cambio brusco: {fmt(value)}{u} frente a {fmt(prev_value)}{u} del resultado anterior "
                f"(variación ≥ {fmt(delta_pct)} %).")
    cmp_ = "menor que" if direction == "BAJO" else "mayor que"
    return f"{C.LEVEL_LABEL[level]}: {fmt(value)}{u}, {cmp_} {fmt(limit)}{u}."


# ── SQL ────────────────────────────────────────────────────────────────────────
_CANDIDATES = """
    SELECT l.l_id, l.l_test_id, l.l_result, l.l_result_num, l.l_date_transmited,
           od.od_order_id AS order_id, o.o_his_id AS patient_id, o.o_created_at,
           o.o_pregnated, o.o_week_pregnated, o.o_enterprise_id,
           p.pt_date_of_birth AS dob, p.pt_sex_type AS sex_type,
           t.units, t.name AS test_name, t.is_formula, an.a_name AS analyzer_name
    FROM "Laboratories" l
    LEFT JOIN "Analyzers" an ON an.a_id = l.a_analyzer_result_id
    JOIN "OrdersDetails" od ON od.od_id = l.l_order_detail_id
    JOIN "Orders" o ON o.o_id = od.od_order_id
    JOIN "TestsLab" t ON t.id = l.l_test_id
    LEFT JOIN "Patients" p ON p.pt_id = o.o_his_id
    WHERE l.l_test_id IN (SELECT cr_test_id FROM "CriticalRules" WHERE cr_active)
      AND l.l_result IS NOT NULL AND btrim(l.l_result) <> ''
      AND COALESCE(l.l_state, 0) <> 5
      AND COALESCE(od.od_cancelled, 0) = 0
      AND COALESCE(o.o_cancelled, 0) = 0
      AND COALESCE(o.o_order_state, 0) <> 7
      AND o.o_created_at >= :lookback
"""

_PREVIOUS = text("""
    SELECT l.l_result_num, l.l_result, o.o_created_at, o.o_number
    FROM "Laboratories" l
    JOIN "OrdersDetails" od ON od.od_id = l.l_order_detail_id
    JOIN "Orders" o ON o.o_id = od.od_order_id
    WHERE o.o_his_id = :pid AND l.l_test_id = :tid AND o.o_id <> :oid
      AND o.o_created_at < :created AND o.o_created_at >= :since
      AND l.l_result IS NOT NULL AND btrim(l.l_result) <> ''
      AND COALESCE(l.l_state, 0) <> 5
      AND COALESCE(od.od_cancelled, 0) = 0 AND COALESCE(o.o_cancelled, 0) = 0
    ORDER BY o.o_created_at DESC
    LIMIT 3
""")

_INSERT_ALARM = text("""
    INSERT INTO "Alarms" (al_laboratory_id, al_order_id, al_test_id, al_patient_id, al_rule_id,
        al_level, al_direction, al_value, al_last_value, al_limit, al_limits,
        al_previous_value, al_previous_date, al_previous_order,
        al_state, al_notify_minutes, al_block_validation, al_detected_at, al_updated_at)
    VALUES (:lab, :order_id, :test_id, :patient_id, :rule_id,
        :level, :direction, :value, :value, :limit, CAST(:limits AS JSONB),
        :prev_value, :prev_date, :prev_order,
        'NUEVA', :minutes, :block, :now, :now)
    ON CONFLICT (al_laboratory_id) WHERE al_state <> 'CERRADA' DO NOTHING
    RETURNING al_id
""")

_INSERT_EVENT = text("""
    INSERT INTO "AlarmEvents" (ae_alarm_id, ae_type, ae_user_id, ae_user_name, ae_channel,
        ae_contact, ae_read_back, ae_detail, ae_created_at)
    VALUES (:alarm_id, :type, :user_id, :user_name, :channel, :contact, :read_back, :detail, :now)
""")


async def add_event(db: AsyncSession, alarm_id: int, type_: str, detail: str,
                    user_id: Optional[int] = None, user_name: str = C.SYSTEM_USER,
                    channel: Optional[str] = None, contact: Optional[str] = None,
                    read_back: Optional[bool] = None, now: Optional[datetime] = None) -> None:
    await db.execute(_INSERT_EVENT, {
        "alarm_id": alarm_id, "type": type_, "user_id": user_id, "user_name": user_name,
        "channel": channel, "contact": contact, "read_back": read_back, "detail": detail,
        "now": now or get_bogota_now(),
    })


async def _load_rules(db: AsyncSession, test_ids: Iterable[int]) -> dict[int, list[Rule]]:
    ids = list(set(test_ids))
    if not ids:
        return {}
    msgs = ("cr_msg_panic_low, cr_msg_critical_low, cr_msg_critical_high, cr_msg_panic_high, cr_msg_delta"
            if await messages_ready(db) else
            "NULL AS cr_msg_panic_low, NULL AS cr_msg_critical_low, NULL AS cr_msg_critical_high, "
            "NULL AS cr_msg_panic_high, NULL AS cr_msg_delta")
    ent = "cr_enterprise_id" if await enterprise_ready(db) else "NULL::int AS cr_enterprise_id"
    preg = ("cr_pregnancy, cr_min_week, cr_max_week" if await pregnancy_ready(db) else
            "'TODAS' AS cr_pregnancy, NULL::int AS cr_min_week, NULL::int AS cr_max_week")
    rows = (await db.execute(text(f"""
        SELECT cr_id, cr_test_id, cr_gender, cr_age_type, cr_min_age, cr_max_age,
               cr_panic_low, cr_critical_low, cr_critical_high, cr_panic_high,
               cr_delta_pct, cr_delta_days, cr_notify_minutes, cr_block_validation, {msgs}, {preg}, {ent}
        FROM "CriticalRules" WHERE cr_active AND cr_test_id = ANY(:ids)
    """), {"ids": ids})).all()
    out: dict[int, list[Rule]] = {}
    for r in rows:
        out.setdefault(r.cr_test_id, []).append(Rule(
            id=r.cr_id, test_id=r.cr_test_id, gender=(r.cr_gender or "AMBOS").upper(),
            age_type=r.cr_age_type or "AÑOS", min_age=r.cr_min_age, max_age=r.cr_max_age,
            panic_low=_num(r.cr_panic_low), critical_low=_num(r.cr_critical_low),
            critical_high=_num(r.cr_critical_high), panic_high=_num(r.cr_panic_high),
            delta_pct=_num(r.cr_delta_pct), delta_days=r.cr_delta_days or 30,
            notify_minutes=r.cr_notify_minutes or 30, block_validation=bool(r.cr_block_validation),
            msg_panic_low=r.cr_msg_panic_low, msg_critical_low=r.cr_msg_critical_low,
            msg_critical_high=r.cr_msg_critical_high, msg_panic_high=r.cr_msg_panic_high,
            msg_delta=r.cr_msg_delta,
            pregnancy=(r.cr_pregnancy or "TODAS").upper(), min_week=r.cr_min_week, max_week=r.cr_max_week,
            enterprise_id=r.cr_enterprise_id,
        ))
    return out


async def _previous(db: AsyncSession, row, rule: Rule):
    if row.patient_id is None:
        return None
    created = row.o_created_at
    rows = (await db.execute(_PREVIOUS, {
        "pid": row.patient_id, "tid": row.l_test_id, "oid": row.order_id,
        "created": created, "since": created - timedelta(days=max(rule.delta_days, 1)),
    })).all()
    for p in rows:
        v = parse_value(p.l_result_num, p.l_result)
        if v is not None:
            return v, p.o_created_at, p.o_number
    return None


async def evaluate(db: AsyncSession, *, order_ids: Optional[list[int]] = None,
                   since: Optional[datetime] = None, lookback_days: int = LOOKBACK_DAYS) -> int:
    """
    Revisa los resultados (de las órdenes indicadas, o los que cambiaron desde
    `since`) y crea/actualiza sus alarmas. No hace commit. Retorna cuántas
    alarmas nuevas creó.
    """
    if not await alarms_ready(db):
        return 0
    now = get_bogota_now()
    params: dict = {"lookback": now - timedelta(days=lookback_days)}
    sql = _CANDIDATES
    if order_ids is not None:
        if not order_ids:
            return 0
        sql += " AND od.od_order_id = ANY(:order_ids)"
        params["order_ids"] = list(order_ids)
    elif since is not None:
        sql += " AND GREATEST(l.l_date_transmited, l.l_updated_at, l.l_created_at) >= :since"
        params["since"] = since
    else:
        return 0

    # Un solo proceso evalúa a la vez (varios workers de uvicorn)
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext('alarm_eval'))"))

    rows = (await db.execute(text(sql), params)).all()
    if not rows:
        return 0
    rules = await _load_rules(db, (r.l_test_id for r in rows))
    lab_ids = [r.l_id for r in rows]

    open_alarms = {a.al_laboratory_id: a for a in (await db.execute(text("""
        SELECT al_id, al_laboratory_id, al_level, al_state, al_last_value
        FROM "Alarms" WHERE al_laboratory_id = ANY(:ids) AND al_state <> 'CERRADA'
    """), {"ids": lab_ids})).all()}
    closed_values: set[tuple[int, Decimal]] = {
        (c.al_laboratory_id, Decimal(str(c.al_last_value)))
        for c in (await db.execute(text("""
            SELECT al_laboratory_id, al_last_value FROM "Alarms"
            WHERE al_laboratory_id = ANY(:ids) AND al_state = 'CERRADA' AND al_last_value IS NOT NULL
        """), {"ids": lab_ids})).all()
    }

    msgs_ok = await messages_ready(db)
    created = 0
    for row in rows:
        value = parse_value(row.l_result_num, row.l_result)
        if value is None:
            continue
        at = row.o_created_at.date() if row.o_created_at else now.date()
        rule = pick_rule(rules.get(row.l_test_id, []), row.sex_type, row.dob, at,
                         bool(row.o_pregnated), parse_weeks(row.o_week_pregnated), row.o_enterprise_id)
        if rule is None:
            continue
        open_a = open_alarms.get(row.l_id)
        if open_a is not None and open_a.al_last_value is not None and Decimal(str(open_a.al_last_value)) == value:
            continue  # sin cambios
        if open_a is None and (row.l_id, value) in closed_values:
            continue  # ya se gestionó y se cerró con este mismo valor

        cls = classify(value, rule)
        prev = None
        if cls is not None or rule.delta_pct is not None:
            prev = await _previous(db, row, rule)
        if cls is None and rule.delta_pct is not None and prev is not None and prev[0] != 0:
            pct = abs(value - prev[0]) / abs(prev[0]) * 100
            if pct >= rule.delta_pct:
                cls = (C.LEVEL_DELTA, "ALTO" if value > prev[0] else "BAJO", None)

        if open_a is None:
            if cls is None:
                continue
            level, direction, limit = cls
            message = rule.message(level, direction)
            new_id = (await db.execute(_INSERT_ALARM, {
                "lab": row.l_id, "order_id": row.order_id, "test_id": row.l_test_id,
                "patient_id": row.patient_id, "rule_id": rule.id, "level": level,
                "direction": direction, "value": value, "limit": limit,
                "limits": json.dumps(rule.limits_json()),
                "prev_value": prev[0] if prev else None, "prev_date": prev[1] if prev else None,
                "prev_order": prev[2] if prev else None, "minutes": rule.notify_minutes,
                "block": rule.block_validation, "now": now,
            })).scalar()
            if new_id:
                if message and msgs_ok:
                    await db.execute(text('UPDATE "Alarms" SET al_message = :m WHERE al_id = :id'),
                                     {"m": message[:255], "id": new_id})
                origin = ("calculado por fórmula" if row.is_formula
                          else f"analizador {row.analyzer_name}" if row.l_date_transmited and row.analyzer_name
                          else "analizador" if row.l_date_transmited else "digitado en el LIS")
                await add_event(db, new_id, C.EV_DETECTADA,
                                describe(level, direction, limit, value, row.units,
                                         prev[0] if prev else None, rule.delta_pct)
                                + (f" Posible: {message}." if message else "") + f" Origen: {origin}.",
                                now=now)
                created += 1
            continue

        # Alarma abierta y el resultado cambió
        u = f" {row.units.strip()}" if row.units and row.units.strip() else ""
        if cls is None:
            if open_a.al_state in C.PENDING_STATES:
                await db.execute(text("""
                    UPDATE "Alarms" SET al_state = 'CERRADA', al_closed_at = :now, al_last_value = :v, al_updated_at = :now
                    WHERE al_id = :id
                """), {"id": open_a.al_id, "v": value, "now": now})
                await add_event(db, open_a.al_id, C.EV_CERRADA,
                                f"Cierre automático: el resultado se corrigió a {fmt(value)}{u} y ya no es crítico.", now=now)
            else:
                await db.execute(text('UPDATE "Alarms" SET al_last_value = :v, al_updated_at = :now WHERE al_id = :id'),
                                 {"id": open_a.al_id, "v": value, "now": now})
                await add_event(db, open_a.al_id, C.EV_CAMBIO,
                                f"El resultado cambió a {fmt(value)}{u} y ya no es crítico. Cierre la alarma cuando corresponda.", now=now)
            continue

        level, direction, limit = cls
        worse = C.LEVEL_RANK[level] > C.LEVEL_RANK.get(open_a.al_level, 0)
        reopen = worse and open_a.al_state in (C.STATE_NOTIFICADA, C.STATE_ACUSADA)
        await db.execute(text(f"""
            UPDATE "Alarms" SET al_level = :level, al_direction = :direction, al_value = :v, al_last_value = :v,
                   al_limit = :limit, al_limits = CAST(:limits AS JSONB), al_rule_id = :rule_id,
                   al_notify_minutes = :minutes, al_block_validation = :block, al_updated_at = :now
                   {", al_state = 'NUEVA', al_detected_at = :now" if reopen else ""}
            WHERE al_id = :id
        """), {"id": open_a.al_id, "level": level, "direction": direction, "v": value, "limit": limit,
               "limits": json.dumps(rule.limits_json()), "rule_id": rule.id, "minutes": rule.notify_minutes,
               "block": rule.block_validation, "now": now})
        msg = f"El resultado cambió a {fmt(value)}{u}. " + describe(level, direction, limit, value, row.units,
                                                                   prev[0] if prev else None, rule.delta_pct)
        if msgs_ok:
            await db.execute(text('UPDATE "Alarms" SET al_message = :m WHERE al_id = :id'),
                             {"m": (rule.message(level, direction) or None), "id": open_a.al_id})
        if reopen:
            await add_event(db, open_a.al_id, C.EV_REABIERTA, msg + " Empeoró: debe notificarse de nuevo al médico.", now=now)
        elif worse:
            await add_event(db, open_a.al_id, C.EV_EMPEORO,
                            msg + f" Empeoró de {C.LEVEL_LABEL.get(open_a.al_level, open_a.al_level)} a {C.LEVEL_LABEL[level]}.", now=now)
        else:
            await add_event(db, open_a.al_id, C.EV_CAMBIO, msg, now=now)
    return created


async def escalate_overdue(db: AsyncSession) -> int:
    """Pasa a ESCALADA las alarmas NUEVAS que superaron su tiempo meta. No hace commit."""
    if not await alarms_ready(db):
        return 0
    now = get_bogota_now()
    rows = (await db.execute(text("""
        UPDATE "Alarms" SET al_state = 'ESCALADA', al_updated_at = :now
        WHERE al_state = 'NUEVA' AND al_detected_at + make_interval(mins => al_notify_minutes) < :now
        RETURNING al_id, al_notify_minutes
    """), {"now": now})).all()
    for r in rows:
        await add_event(db, r.al_id, C.EV_ESCALADA,
                        f"Escalada automáticamente: pasaron más de {r.al_notify_minutes} min sin registrar la notificación al médico. "
                        "Avise al coordinador del laboratorio.", now=now)
    return len(rows)


async def close_orphans(db: AsyncSession) -> int:
    """Cierra las alarmas pendientes cuyo resultado se borró, se descartó o la orden se anuló."""
    if not await alarms_ready(db):
        return 0
    now = get_bogota_now()
    rows = (await db.execute(text("""
        SELECT a.al_id,
               CASE WHEN COALESCE(o.o_cancelled, 0) <> 0 OR COALESCE(o.o_order_state, 0) = 7 THEN 'la orden fue anulada'
                    WHEN COALESCE(od.od_cancelled, 0) <> 0 THEN 'el estudio fue anulado'
                    WHEN COALESCE(l.l_state, 0) = 5 THEN 'la prueba fue descartada'
                    ELSE 'el resultado fue borrado' END AS reason
        FROM "Alarms" a
        JOIN "Laboratories" l ON l.l_id = a.al_laboratory_id
        JOIN "OrdersDetails" od ON od.od_id = l.l_order_detail_id
        JOIN "Orders" o ON o.o_id = od.od_order_id
        WHERE a.al_state IN ('NUEVA', 'ESCALADA')
          AND (l.l_result IS NULL OR btrim(l.l_result) = '' OR COALESCE(l.l_state, 0) = 5
               OR COALESCE(od.od_cancelled, 0) <> 0 OR COALESCE(o.o_cancelled, 0) <> 0
               OR COALESCE(o.o_order_state, 0) = 7)
    """))).all()
    for r in rows:
        await db.execute(text("""
            UPDATE "Alarms" SET al_state = 'CERRADA', al_closed_at = :now, al_last_value = NULL, al_updated_at = :now
            WHERE al_id = :id
        """), {"id": r.al_id, "now": now})
        await add_event(db, r.al_id, C.EV_CERRADA, f"Cierre automático: {r.reason}.", now=now)
    return len(rows)
