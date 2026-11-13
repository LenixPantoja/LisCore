"""Consultas del módulo de Alarmas y Críticos (SQL directo)."""
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_ALARM_SELECT = """
    SELECT a.al_id, a.al_laboratory_id, a.al_order_id, a.al_test_id, a.al_patient_id, a.al_rule_id,
           a.al_level, a.al_direction, a.al_value, a.al_last_value, a.al_limit, a.al_limits,
           a.al_previous_value, a.al_previous_date, a.al_previous_order,
           a.al_state, a.al_notify_minutes, a.al_block_validation,
           a.al_detected_at, a.al_notified_at, a.al_closed_at,
           l.l_state, l.l_result, l.l_date_transmited,
           o.o_number, o.o_priority, o.o_hq_consecutive, o.o_age, o.o_created_at,
           o.o_pregnated, o.o_week_pregnated, ent.en_name AS enterprise_name,
           hq.prefix AS hq_prefix, hq.name AS hq_name,
           s.name AS service_name,
           wg.wg_id, wg.wg_name,
           t.code AS test_code, t.name AS test_name, t.units AS test_units,
           p."pt_Number_document" AS pt_document, p.pt_firts_name, p.pt_middle_name, p.pt_last_name,
           p.pt_second_last_name, p.pt_sex_type, p.pt_date_of_birth, p.pt_phone_number,
           m.med_id, m.med_codigo, m.med_name, m.med_specialty, m.med_phone, m.med_mail,
           trim(concat_ws(' ', un.usr_first_name, un.usr_last_name)) AS notified_by_name,
           {MSG} AS al_message,
           l.a_analyzer_result_id, an.a_name AS analyzer_name, t.is_formula AS test_is_formula,
           me.created_at AS manual_at, me.user_name AS manual_user
    FROM "Alarms" a
    JOIN "Laboratories" l ON l.l_id = a.al_laboratory_id
    LEFT JOIN "Analyzers" an ON an.a_id = l.a_analyzer_result_id
    LEFT JOIN LATERAL (
        -- Última edición manual del resultado (traza "Edición de Resultado") hasta la detección
        SELECT tr.created_at, trim(concat_ws(' ', tu.usr_first_name, tu.usr_last_name)) AS user_name
        FROM "AppTrace" tr
        LEFT JOIN "AppUsers" tu ON tu.usr_id = tr.usr_id
        WHERE tr.order_id = a.al_order_id AND tr.test_id = a.al_test_id AND tr.operation_type = 3
          AND upper(COALESCE(tu.usr_login, '')) <> 'ANALIZADOR'   -- usuario técnico de la interfaz
          AND tr.created_at <= a.al_detected_at + interval '2 minutes'
        ORDER BY tr.created_at DESC LIMIT 1
    ) me ON TRUE
    JOIN "Orders" o ON o.o_id = a.al_order_id
    JOIN "TestsLab" t ON t.id = a.al_test_id
    LEFT JOIN "Work_groups" wg ON wg.wg_id = t.work_group_id
    LEFT JOIN "Patients" p ON p.pt_id = a.al_patient_id
    LEFT JOIN "Services" s ON s.id = o.o_service_id
    LEFT JOIN "Enterprises" ent ON ent.en_id = o.o_enterprise_id
    LEFT JOIN "Headquarters" hq ON hq.id = o.o_headquarter_id
    LEFT JOIN "Medics" m ON m.med_id = o.o_medic_id
    LEFT JOIN "AppUsers" un ON un.usr_id = a.al_notified_by
"""


def _sel(msgs_ok: bool) -> str:
    return _ALARM_SELECT.replace("{MSG}", "a.al_message" if msgs_ok else "NULL::varchar")


class AlarmRepository:
    # ── Bandeja ────────────────────────────────────────────────────────────────
    @staticmethod
    def _where(date_from: datetime, date_to: datetime, level: Optional[str], area_id: Optional[int],
               search: Optional[str]) -> tuple[str, dict]:
        # Las alarmas abiertas siempre se muestran; las cerradas, solo las del periodo.
        conds = ["(a.al_state <> 'CERRADA' OR a.al_detected_at BETWEEN :date_from AND :date_to)"]
        params: dict = {"date_from": date_from, "date_to": date_to}
        if level:
            conds.append("a.al_level = :level")
            params["level"] = level
        if area_id:
            conds.append("wg.wg_id = :area_id")
            params["area_id"] = area_id
        if search and search.strip():
            q = search.strip()
            conds.append("""(o.o_number = :q_exact OR p."pt_Number_document" = :q_exact
                OR lower(t.code) = lower(:q_exact) OR t.name ILIKE :q_like
                OR concat_ws(' ', p.pt_firts_name, p.pt_middle_name, p.pt_last_name, p.pt_second_last_name) ILIKE :q_like)""")
            params["q_exact"] = q
            params["q_like"] = f"%{q}%"
        return " WHERE " + " AND ".join(conds), params

    @staticmethod
    async def list_alarms(db: AsyncSession, *, date_from: datetime, date_to: datetime, state: Optional[str],
                          level: Optional[str], area_id: Optional[int], search: Optional[str], limit: int,
                          msgs_ok: bool = False):
        where, params = AlarmRepository._where(date_from, date_to, level, area_id, search)
        counts_rows = (await db.execute(text(f"""
            SELECT a.al_state, count(*) FROM "Alarms" a
            JOIN "Orders" o ON o.o_id = a.al_order_id
            JOIN "TestsLab" t ON t.id = a.al_test_id
            LEFT JOIN "Work_groups" wg ON wg.wg_id = t.work_group_id
            LEFT JOIN "Patients" p ON p.pt_id = a.al_patient_id
            {where} GROUP BY a.al_state
        """), params)).all()

        state_sql = ""
        if state == "ACTIVAS":
            state_sql = " AND a.al_state <> 'CERRADA'"
        elif state and state != "TODAS":
            state_sql = " AND a.al_state = :state"
            params["state"] = state
        params["limit"] = limit
        rows = (await db.execute(text(f"""
            {_sel(msgs_ok)} {where} {state_sql}
            ORDER BY (a.al_state = 'CERRADA'),
                     CASE a.al_level WHEN 'PANICO' THEN 0 WHEN 'CRITICO' THEN 1 ELSE 2 END,
                     a.al_detected_at
            LIMIT :limit
        """), params)).all()
        return rows, {r[0]: r[1] for r in counts_rows}

    @staticmethod
    async def get_alarm(db: AsyncSession, alarm_id: int, msgs_ok: bool = False):
        return (await db.execute(text(f"{_sel(msgs_ok)} WHERE a.al_id = :id"), {"id": alarm_id})).first()

    @staticmethod
    async def get_events(db: AsyncSession, alarm_id: int):
        return (await db.execute(text("""
            SELECT ae_id, ae_type, ae_user_name, ae_channel, ae_contact, ae_read_back, ae_detail, ae_created_at
            FROM "AlarmEvents" WHERE ae_alarm_id = :id ORDER BY ae_created_at, ae_id
        """), {"id": alarm_id})).all()

    @staticmethod
    async def lock_alarm(db: AsyncSession, alarm_id: int):
        return (await db.execute(text("""
            SELECT al_id, al_state, al_level, al_value, al_order_id, al_notified_at
            FROM "Alarms" WHERE al_id = :id FOR UPDATE
        """), {"id": alarm_id})).first()

    @staticmethod
    async def alarms_for_order(db: AsyncSession, order_number: str, msgs_ok: bool = False):
        return (await db.execute(text(f"""
            {_sel(msgs_ok)} WHERE o.o_number = :n ORDER BY a.al_detected_at DESC
        """), {"n": order_number})).all()

    # ── Resumen (contador del menú e indicadores) ─────────────────────────────
    @staticmethod
    async def summary(db: AsyncSession, now: datetime, kpi_since: datetime):
        counts = (await db.execute(text("""
            SELECT count(*) FILTER (WHERE al_state <> 'CERRADA') AS active,
                   count(*) FILTER (WHERE al_state <> 'CERRADA' AND al_level = 'PANICO') AS active_panic,
                   count(*) FILTER (WHERE al_state IN ('NUEVA', 'ESCALADA')) AS pending,
                   count(*) FILTER (WHERE al_state IN ('NUEVA', 'ESCALADA') AND al_level = 'PANICO') AS pending_panic,
                   count(*) FILTER (WHERE al_state IN ('NUEVA', 'ESCALADA')
                                    AND al_detected_at + make_interval(mins => al_notify_minutes) < :now) AS overdue
            FROM "Alarms" WHERE al_state <> 'CERRADA'
        """), {"now": now})).first()
        kpi = (await db.execute(text("""
            SELECT count(*) AS notified,
                   avg(EXTRACT(EPOCH FROM (al_notified_at - al_detected_at)) / 60) AS avg_minutes,
                   count(*) FILTER (WHERE al_notified_at <= al_detected_at + make_interval(mins => al_notify_minutes)) AS on_time
            FROM "Alarms" WHERE al_notified_at IS NOT NULL AND al_detected_at >= :since
        """), {"since": kpi_since})).first()
        # Marca de avisos: último evento que debe avisar (alarma nueva, reabierta o que empeoró)
        latest_id = (await db.execute(text("""
            SELECT COALESCE(max(ae_id), 0) FROM "AlarmEvents"
            WHERE ae_type IN ('DETECTADA', 'REABIERTA', 'EMPEORO')
        """))).scalar()
        return counts, kpi, latest_id

    @staticmethod
    async def new_pending(db: AsyncSession, after_id: int, msgs_ok: bool = False):
        return (await db.execute(text(f"""
            SELECT DISTINCT ON (a.al_id) a.al_id, a.al_level, a.al_value, a.al_direction, t.name AS test_name, t.units,
                   {"a.al_message" if msgs_ok else "NULL::varchar AS al_message"},
                   o.o_number, concat_ws(' ', p.pt_firts_name, p.pt_last_name) AS patient_name,
                   (e.ae_type <> 'DETECTADA') AS worsened
            FROM "AlarmEvents" e
            JOIN "Alarms" a ON a.al_id = e.ae_alarm_id
            JOIN "TestsLab" t ON t.id = a.al_test_id
            JOIN "Orders" o ON o.o_id = a.al_order_id
            LEFT JOIN "Patients" p ON p.pt_id = a.al_patient_id
            WHERE e.ae_id > :after AND e.ae_type IN ('DETECTADA', 'REABIERTA', 'EMPEORO')
              AND a.al_state IN ('NUEVA', 'ESCALADA')
            ORDER BY a.al_id DESC, e.ae_id DESC LIMIT 5
        """), {"after": after_id})).all()

    # ── Reglas ────────────────────────────────────────────────────────────────
    _RULE_SELECT = """
        SELECT r.*, t.code AS test_code, t.name AS test_name, t.units AS test_units,
               wg.wg_name AS area_name,
               (to_jsonb(r) ->> 'cr_enterprise_id')::int AS enterprise_id,
               (SELECT e.en_name FROM "Enterprises" e WHERE e.en_id = (to_jsonb(r) ->> 'cr_enterprise_id')::int) AS enterprise_name,
               trim(concat_ws(' ', u.usr_first_name, u.usr_last_name)) AS updated_by_name,
               (SELECT count(*) FROM "Alarms" a WHERE a.al_rule_id = r.cr_id) AS alarms_count
        FROM "CriticalRules" r
        JOIN "TestsLab" t ON t.id = r.cr_test_id
        LEFT JOIN "Work_groups" wg ON wg.wg_id = t.work_group_id
        LEFT JOIN "AppUsers" u ON u.usr_id = COALESCE(r.cr_updated_by, r.cr_created_by)
    """

    @staticmethod
    async def list_rules(db: AsyncSession, search: Optional[str], active: Optional[bool]):
        conds, params = [], {}
        if search and search.strip():
            conds.append("(lower(t.code) = lower(:q) OR t.name ILIKE :ql OR wg.wg_name ILIKE :ql)")
            params.update(q=search.strip(), ql=f"%{search.strip()}%")
        if active is not None:
            conds.append("r.cr_active = :active")
            params["active"] = active
        where = (" WHERE " + " AND ".join(conds)) if conds else ""
        return (await db.execute(text(f"""
            {AlarmRepository._RULE_SELECT} {where}
            ORDER BY r.cr_active DESC, wg.wg_name NULLS LAST, t.name, r.cr_gender, r.cr_min_age NULLS FIRST
        """), params)).all()

    @staticmethod
    async def rules_for_test(db: AsyncSession, test_id: int):
        return (await db.execute(text(f"""
            {AlarmRepository._RULE_SELECT} WHERE r.cr_test_id = :tid
            ORDER BY r.cr_active DESC, r.cr_gender, r.cr_min_age NULLS FIRST, r.cr_id
        """), {"tid": test_id})).all()

    @staticmethod
    async def get_rule(db: AsyncSession, rule_id: int):
        return (await db.execute(text(f"{AlarmRepository._RULE_SELECT} WHERE r.cr_id = :id"), {"id": rule_id})).first()

    @staticmethod
    async def search_enterprises(db: AsyncSession, search: Optional[str]):
        params: dict = {}
        cond = ""
        if search and search.strip():
            cond = "AND (e.en_name ILIKE :q OR e.en_code ILIKE :q OR e.en_nit ILIKE :q)"
            params["q"] = f"%{search.strip()}%"
        return (await db.execute(text(f"""
            SELECT e.en_id, e.en_code, e.en_name, e.en_nit FROM "Enterprises" e
            WHERE e.en_active IS NOT FALSE {cond}
            ORDER BY e.en_name LIMIT 30
        """), params)).all()

    @staticmethod
    async def search_tests(db: AsyncSession, search: Optional[str]):
        params: dict = {}
        cond = ""
        if search and search.strip():
            cond = "AND (lower(t.code) = lower(:q) OR t.code ILIKE :ql OR t.name ILIKE :ql)"
            params.update(q=search.strip(), ql=f"%{search.strip()}%")
        return (await db.execute(text(f"""
            SELECT t.id, t.code, t.name, t.units, t.test_type, wg.wg_name AS area_name,
                   (SELECT count(*) FROM "CriticalRules" r WHERE r.cr_test_id = t.id) AS rules_count
            FROM "TestsLab" t
            LEFT JOIN "Work_groups" wg ON wg.wg_id = t.work_group_id
            WHERE t.active IS NOT FALSE {cond}
            ORDER BY (lower(t.code) = lower(:q)) DESC NULLS LAST, t.name
            LIMIT 30
        """ if cond else """
            SELECT t.id, t.code, t.name, t.units, t.test_type, wg.wg_name AS area_name,
                   (SELECT count(*) FROM "CriticalRules" r WHERE r.cr_test_id = t.id) AS rules_count
            FROM "TestsLab" t
            LEFT JOIN "Work_groups" wg ON wg.wg_id = t.work_group_id
            WHERE t.active IS NOT FALSE
            ORDER BY t.name LIMIT 30
        """), params)).all()
