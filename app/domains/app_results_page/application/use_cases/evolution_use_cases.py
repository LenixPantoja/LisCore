"""
Gráfico evolutivo para el portal de resultados (pacientes y empresas).

Equivalente portal de `orders.get_grafico_evolutivo` (que exige permisos RBAC del
personal del laboratorio): devuelve el histórico de un examen para un paciente,
evaluando cada resultado contra sus rangos de referencia (NORMAL / ACEPTABLE /
CRITICO) según el género y la edad del paciente.

Reglas del portal:
- Sólo resultados validados (Validada / Laboratorio Impreso), igual que el listado.
- Se excluyen las órdenes anuladas.
- Una empresa sólo ve resultados de órdenes asociadas a ella.
"""

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.app_results_page.domain.helpers import full_name
from app.domains.enterprises.domain.models import Enterprise
from app.domains.laboratories.domain.constants import LABORATORY_STATE_IMPRESO, LABORATORY_STATE_VALIDADA
from app.domains.laboratories.domain.models import Laboratory
from app.domains.orders.domain.constants import ORDER_STATE_ANULADA
from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.patients.domain.models import Patient
from app.domains.testslabs.domain.models import TestsLab
from app.shared.utils.range_evaluator import bulk_fetch_ranges, evaluate_reference_range_sync

_VALIDATED_LAB_STATES = (LABORATORY_STATE_VALIDADA, LABORATORY_STATE_IMPRESO)


def lab_numeric_value(lab: Laboratory, decimals: Optional[int] = None) -> tuple[Optional[float], Optional[str]]:
    """Devuelve (valor_numérico, valor_texto) de un laboratorio. Sólo uno de los dos viene informado."""
    value: Optional[float] = None
    if lab.l_result_num is not None:
        value = float(lab.l_result_num)
    elif lab.l_result:
        try:
            value = float(str(lab.l_result).strip().replace(",", "."))
        except ValueError:
            return None, str(lab.l_result)
    else:
        return None, None
    if decimals is not None:
        value = round(value, decimals)
    return value, None


async def _build_evolution(
    db: AsyncSession,
    patient: Patient,
    test_id: int,
    enterprise_id: Optional[int] = None,
) -> dict:
    test = await db.get(TestsLab, test_id)
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prueba de laboratorio no encontrada.")

    stmt = (
        select(Laboratory, Order)
        .join(OrdersDetail, Laboratory.l_order_detail_id == OrdersDetail.od_id)
        .join(Order, OrdersDetail.od_order_id == Order.o_id)
        .where(
            Order.o_his_id == patient.pt_id,
            Order.o_order_state != ORDER_STATE_ANULADA,
            Laboratory.l_test_id == test_id,
            Laboratory.l_state.in_(_VALIDATED_LAB_STATES),
        )
        .order_by(Order.o_date.asc(), Order.o_id.asc(), Laboratory.l_id.asc())
    )
    if enterprise_id is not None:
        stmt = stmt.where(Order.o_enterprise_id == enterprise_id)

    rows = (await db.execute(stmt)).all()

    ranges = (await bulk_fetch_ranges(db, [test_id])).get(test_id, [])
    patient_dob = patient.pt_date_of_birth
    patient_sex = patient.pt_sex_type

    historico = []
    for lab, order in rows:
        value, text = lab_numeric_value(lab, test.num_decimal_result)
        if value is None and not text:
            continue

        range_type, ref_min, ref_max = evaluate_reference_range_sync(
            ranges, value, patient_dob, patient_sex, result_text=text
        )

        fecha = lab.l_date_transmited or lab.l_created_at
        if fecha is None and order.o_date:
            fecha = datetime.combine(order.o_date, datetime.min.time())

        historico.append({
            "fecha": fecha,
            "valor": value,
            "valor_texto": text,
            "referencia_min": float(ref_min) if ref_min is not None else None,
            "referencia_max": float(ref_max) if ref_max is not None else None,
            "estado": range_type,
            "orden_numero": order.o_number,
        })

    return {
        "test_id": test.id,
        "prueba": test.name,
        "codigo": test.code,
        "unidad": test.units,
        "paciente": full_name(patient),
        "historico": historico,
    }


async def get_patient_evolution(db: AsyncSession, patient: Patient, test_id: int) -> dict:
    """Histórico evolutivo de un examen para el paciente autenticado."""
    return await _build_evolution(db, patient, test_id)


async def get_enterprise_patient_evolution(
    db: AsyncSession,
    enterprise: Enterprise,
    document_number: str,
    test_id: int,
) -> dict:
    """Histórico evolutivo de un examen para un paciente de la empresa autenticada."""
    patient = (
        await db.execute(select(Patient).where(Patient.pt_Number_document == document_number.strip()))
    ).scalar_one_or_none()

    # Sin órdenes con esta empresa: se responde igual que si no existiera (no revelar pacientes ajenos).
    linked = 0
    if patient is not None:
        linked = (
            await db.execute(
                select(func.count())
                .select_from(Order)
                .where(Order.o_his_id == patient.pt_id, Order.o_enterprise_id == enterprise.en_id)
            )
        ).scalar() or 0
    if patient is None or linked == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado.")

    return await _build_evolution(db, patient, test_id, enterprise_id=enterprise.en_id)
