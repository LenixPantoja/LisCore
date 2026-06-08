from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.remissions.infrastructure.repository import (
    ExternalLabRepository,
    RemissionRepository,
)
from app.domains.remissions.domain.constants import (
    DETAIL_ITEM_STATE_RECEIVED_OK,
    DETAIL_ITEM_STATE_REJECTED,
)


# ═══════════════════════════════════════════════════════════════════════
#  External Reference Laboratories Use Cases
# ═══════════════════════════════════════════════════════════════════════

async def create_external_lab(db: AsyncSession, data: dict) -> dict:
    lab = await ExternalLabRepository.create(db, data)
    return lab


async def list_external_labs(db: AsyncSession, active_only: bool = True) -> dict:
    items = await ExternalLabRepository.list_all(db, active_only=active_only)
    return {"items": items, "total": len(items)}


async def get_external_lab(db: AsyncSession, erl_id: int) -> dict:
    lab = await ExternalLabRepository.get_by_id(db, erl_id)
    if not lab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratorio externo con ID {erl_id} no encontrado.",
        )
    return lab


async def update_external_lab(db: AsyncSession, erl_id: int, data: dict) -> dict:
    lab = await ExternalLabRepository.update(db, erl_id, data)
    if not lab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratorio externo con ID {erl_id} no encontrado.",
        )
    return lab


async def delete_external_lab(db: AsyncSession, erl_id: int) -> dict:
    lab = await ExternalLabRepository.delete(db, erl_id)
    if not lab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratorio externo con ID {erl_id} no encontrado.",
        )
    return {"success": True, "message": "Laboratorio externo eliminado correctamente."}


# ═══════════════════════════════════════════════════════════════════════
#  Remissions Use Cases
# ═══════════════════════════════════════════════════════════════════════

async def create_remission(
    db: AsyncSession,
    rem_type: str,
    origin_headquarter_id: int,
    user_id: int,
    dest_headquarter_id: Optional[int] = None,
    dest_external_lab_id: Optional[int] = None,
    observations: Optional[str] = None,
) -> dict:
    remission, error = await RemissionRepository.create_remission(
        db,
        rem_type=rem_type,
        origin_headquarter_id=origin_headquarter_id,
        user_id=user_id,
        dest_headquarter_id=dest_headquarter_id,
        dest_external_lab_id=dest_external_lab_id,
        observations=observations,
    )
    if error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

    return {
        "success": True,
        "rem_id": remission.rem_id,
        "rem_consecutive": remission.rem_consecutive,
        "message": "Remisión creada correctamente.",
    }


def _enrich_remission(remission, include_details: bool = False) -> dict:
    """
    Toma un objeto Remission SQLAlchemy (con relaciones eager-loaded)
    y lo convierte a dict agregando los campos enriquecidos:
    - origin_headquarter: { name }
    - dest_headquarter: { name } o None
    - dest_external_lab: response completo o None
    - created_by_user: { usr_login, full_name }
    
    Args:
        remission: Objeto Remission de SQLAlchemy.
        include_details: Si True, serializa la relación 'details'.
                         Solo debe ser True cuando la relación fue eager-loaded.
    """
    base = {
        "rem_id": remission.rem_id,
        "rem_consecutive": remission.rem_consecutive,
        "rem_type": remission.rem_type,
        "rem_origin_headquarter_id": remission.rem_origin_headquarter_id,
        "rem_dest_headquarter_id": remission.rem_dest_headquarter_id,
        "rem_dest_external_lab_id": remission.rem_dest_external_lab_id,
        "rem_state": remission.rem_state,
        "rem_courier_name": remission.rem_courier_name,
        "rem_temperature_courier": remission.rem_temperature_courier,
        "rem_observations": remission.rem_observations,
        "rem_created_by_user_id": remission.rem_created_by_user_id,
        "rem_created_at": remission.rem_created_at,
        "rem_sent_at": remission.rem_sent_at,
        "rem_received_at": remission.rem_received_at,
    }

    # Sede origen
    if remission.origin_headquarter:
        base["origin_headquarter"] = {"name": remission.origin_headquarter.name}
    else:
        base["origin_headquarter"] = None

    # Sede destino (solo para LOCAL)
    if remission.dest_headquarter:
        base["dest_headquarter"] = {"name": remission.dest_headquarter.name}
    else:
        base["dest_headquarter"] = None

    # Laboratorio externo destino (solo para EXTERNAL)
    if remission.dest_external_lab:
        base["dest_external_lab"] = {
            "erl_id": remission.dest_external_lab.erl_id,
            "erl_nit": remission.dest_external_lab.erl_nit,
            "erl_name": remission.dest_external_lab.erl_name,
            "erl_address": remission.dest_external_lab.erl_address,
            "erl_phone": remission.dest_external_lab.erl_phone,
            "erl_mail": remission.dest_external_lab.erl_mail,
            "erl_active": remission.dest_external_lab.erl_active,
            "erl_created_at": remission.dest_external_lab.erl_created_at,
            "erl_updated_at": remission.dest_external_lab.erl_updated_at,
        }
    else:
        base["dest_external_lab"] = None

    # Usuario creador
    if remission.created_by_user:
        parts = [
            remission.created_by_user.usr_first_name or "",
            remission.created_by_user.usr_middle_name or "",
            remission.created_by_user.usr_last_name or "",
            remission.created_by_user.usr_second_last_name or "",
        ]
        full_name = " ".join(p for p in parts if p).strip()
        base["created_by_user"] = {
            "usr_login": remission.created_by_user.usr_login,
            "full_name": full_name or None,
        }
    else:
        base["created_by_user"] = None

    # Detalles agrupados por tubo (SamplesOrder)
    # cada grupo contiene: número de orden, tipo de muestra, color y sub-detalle de estudios
    if include_details and remission.details:
        from collections import OrderedDict
        tube_groups = OrderedDict()
        for d in remission.details:
            so = d.sample_order
            so_id = so.so_id if so else d.remd_sample_order_id
            if so_id not in tube_groups:
                order_number = so.order.o_number if so and so.order else None
                sample_type_name = so.sample_type.st_name if so and so.sample_type else None
                sample_type_color = so.sample_type.st_color if so and so.sample_type else None
                tube_groups[so_id] = {
                    "remd_sample_order_id": so_id,
                    "so_barcode": so.so_barcode if so else None,
                    "order_number": order_number,
                    "sample_type_name": sample_type_name,
                    "sample_type_color": sample_type_color,
                    "remd_item_state": d.remd_item_state,
                    "remd_rejection_reason": d.remd_rejection_reason,
                    "studies": [],
                }
            # Agregar estudio al sub-detalle (solo estudios, desduplicados)
            od = d.order_detail
            if od and od.study:
                study_key = od.study.id
                existing_studies = {s["study_id"] for s in tube_groups[so_id]["studies"]}
                if study_key not in existing_studies:
                    tube_groups[so_id]["studies"].append({
                        "study_id": od.study.id,
                        "study_name": od.study.name,
                        "study_code": od.study.code,
                    })
        base["details"] = list(tube_groups.values())

    return base


async def get_remission(db: AsyncSession, rem_id: int) -> dict:
    remission = await RemissionRepository.get_remission_by_id(db, rem_id, load_details=True)
    if not remission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Remisión con ID {rem_id} no encontrada.",
        )
    return _enrich_remission(remission, include_details=True)


async def list_remissions(
    db: AsyncSession,
    state: Optional[int] = None,
    type_: Optional[str] = None,
    origin_hq_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> dict:
    items = await RemissionRepository.list_remissions(
        db, state=state, type_=type_, origin_hq_id=origin_hq_id, skip=skip, limit=limit
    )
    enriched = [_enrich_remission(r) for r in items]
    return {"items": enriched, "total": len(enriched)}


async def add_items_by_barcode(
    db: AsyncSession,
    remission_id: int,
    sample_barcode: str,
    user_id: int,
) -> dict:
    """
    Recibe un código de barras de muestra (ej: 060600022613).
    Los primeros 10 dígitos son el número de orden, los siguientes el sufijo.
    Resuelve el SamplesOrder y los OrdersDetails asociados y los agrega a la remisión.
    """
    # 1. Parsear barcode
    if len(sample_barcode) < 11:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Código de barras inválido: '{sample_barcode}'. Debe tener al menos 11 caracteres (10 del número de orden + sufijo).",
        )

    order_number = sample_barcode[:10]

    # 2. Buscar orden por número
    from app.domains.orders.domain.models import Order as OrderModel
    result = await db.execute(
        select(OrderModel).where(OrderModel.o_number == order_number)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden con número '{order_number}' no encontrada.",
        )

    # 3. Buscar SamplesOrder por código de barras completo
    from app.domains.samples.domain.models import SamplesOrder, SampleType
    from sqlalchemy.orm import selectinload

    so_result = await db.execute(
        select(SamplesOrder)
        .where(SamplesOrder.so_barcode == sample_barcode)
        .options(selectinload(SamplesOrder.sample_type))
    )
    sample_order = so_result.scalar_one_or_none()
    if not sample_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Muestra con código de barras '{sample_barcode}' no encontrada.",
        )

    # 4. Determinar el sufijo y todos los SampleType que lo comparten
    sample_type = sample_order.sample_type
    if not sample_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La muestra con barcode '{sample_barcode}' no tiene un tipo de muestra asociado.",
        )

    target_sufix = sample_type.st_sufix if sample_type.st_sufix is not None else sample_type.st_id

    # 5. Obtener todos los SampleType IDs que comparten el mismo sufijo
    where_conditions = [SampleType.st_sufix == target_sufix]
    # Fallback: si el tipo de muestra no tiene sufijo, también considerar su propio st_id
    if sample_type.st_sufix is None:
        where_conditions.append(SampleType.st_id == target_sufix)

    st_result = await db.execute(
        select(SampleType.st_id).where(or_(*where_conditions))
    )
    sample_type_ids = set(st_result.scalars().all())
    # Asegurar que incluimos el tipo de muestra actual
    sample_type_ids.add(sample_type.st_id)

    # 6. Buscar TestsLab que tengan estos tipos de muestra
    from app.domains.testslabs.domain.models import TestsLab
    test_result = await db.execute(
        select(TestsLab.id).where(TestsLab.samples_type_id.in_(sample_type_ids))
    )
    test_ids = set(test_result.scalars().all())
    if not test_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No se encontraron exámenes asociados al tipo de muestra de la muestra '{sample_barcode}'.",
        )

    # 7. Buscar los StudiesTestDetail que vinculan estudios con tests
    from app.domains.studieslab.domain.models import StudiesTestDetail
    std_result = await db.execute(
        select(StudiesTestDetail.studies_id).where(StudiesTestDetail.tests_id.in_(test_ids))
    )
    study_ids = set(std_result.scalars().all())

    if not study_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No se encontraron estudios vinculados a los exámenes de esta muestra.",
        )

    # 8. Buscar OrdersDetails de la orden que correspondan a esos estudios
    from app.domains.orders.domain.models import OrdersDetail
    od_result = await db.execute(
        select(OrdersDetail).where(
            OrdersDetail.od_order_id == order.o_id,
            OrdersDetail.od_study_id.in_(study_ids),
        )
    )
    order_details = od_result.scalars().all()

    if not order_details:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No se encontraron detalles de orden para los estudios asociados a la muestra '{sample_barcode}'.",
        )

    # 9. Construir los pares (so_id, od_id) y agregarlos
    pairs = [
        {"remd_sample_order_id": sample_order.so_id, "remd_order_detail_id": od.od_id}
        for od in order_details
    ]

    details, error = await RemissionRepository.add_items(db, remission_id, pairs, user_id)
    if error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

    return {
        "success": True,
        "items_count": len(details),
        "message": f"{len(details)} ítems agregados correctamente.",
    }


async def add_items(
    db: AsyncSession,
    remission_id: int,
    items: list,
    user_id: int,
) -> dict:
    """
    Agrega un array de ítems directamente a la remisión.
    Cada ítem debe tener remd_sample_order_id y remd_order_detail_id.
    """
    details, error = await RemissionRepository.add_items(db, remission_id, items, user_id)
    if error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

    return {
        "success": True,
        "items_count": len(details),
        "message": f"{len(details)} ítems agregados correctamente.",
    }


async def remove_item(
    db: AsyncSession,
    remission_id: int,
    detail_id: int,
    user_id: int,
) -> dict:
    detail, error = await RemissionRepository.remove_item(db, remission_id, detail_id, user_id)
    if error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

    return {"success": True, "message": f"Ítem con ID {detail_id} eliminado correctamente."}


async def ship_remission(
    db: AsyncSession,
    remission_id: int,
    user_id: int,
    courier_name: Optional[str] = None,
    temperature_courier: Optional[str] = None,
) -> dict:
    remission, error = await RemissionRepository.ship_remission(
        db, remission_id, user_id, courier_name, temperature_courier
    )
    if error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

    return {
        "success": True,
        "message": "Remisión enviada correctamente.",
        "rem_id": remission.rem_id,
        "rem_state": remission.rem_state,
        "rem_sent_at": remission.rem_sent_at.isoformat() if remission.rem_sent_at else None,
    }


async def receive_item(
    db: AsyncSession,
    remission_id: int,
    detail_id: int,
    user_id: int,
    item_state: int,
    rejection_reason: Optional[str] = None,
) -> dict:
    detail, error = await RemissionRepository.receive_item(
        db, remission_id, detail_id, user_id, item_state, rejection_reason
    )
    if error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

    state_label = "Recibido Conforme" if item_state == DETAIL_ITEM_STATE_RECEIVED_OK else "Rechazado"
    return {
        "success": True,
        "message": f"Ítem {detail_id} procesado: {state_label}.",
        "remd_id": detail.remd_id,
        "remd_item_state": detail.remd_item_state,
    }


async def cancel_remission(
    db: AsyncSession,
    remission_id: int,
    user_id: int,
    notes: Optional[str] = None,
) -> dict:
    remission, error = await RemissionRepository.cancel_remission(db, remission_id, user_id, notes)
    if error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

    return {
        "success": True,
        "message": "Remisión cancelada correctamente.",
        "rem_id": remission.rem_id,
        "rem_state": remission.rem_state,
    }