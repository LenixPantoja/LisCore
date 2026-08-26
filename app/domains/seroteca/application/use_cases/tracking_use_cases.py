from typing import Optional
import logging
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.domains.seroteca.infrastructure.repository import (
    SampleLogRepository,
    GradillaPosicionRepository,
    GradillaRepository,
)
from app.domains.samples.domain.models import SamplesOrder
from app.domains.samples.domain.constants import (
    SAMPLE_ORDER_STATE_CON_MUESTRA,
    SAMPLE_ORDER_STATE_ALMACENADA,
    SAMPLE_ORDER_STATE_DESCARTADA,
)
from app.domains.seroteca.domain.constants import SAMPLE_LOG_STATE_RETIRADA


def _format_position_label(row: int, col: int) -> str:
    """Etiqueta estilo hoja de cálculo: letra de columna (0=A, 1=B, ...) + fila 1-indexada. Ej: row=0, col=2 -> 'C1'."""
    n = col
    letters = ""
    while True:
        n, rem = divmod(n, 26)
        letters = chr(ord("A") + rem) + letters
        if n == 0:
            break
        n -= 1
    return f"{letters}{row + 1}"


async def _build_storage_observation(db: AsyncSession, g_id: int, row: int, col: int) -> tuple[str, Optional[int]]:
    """Construye el texto de observación y el log_location_id para un evento de almacenamiento."""
    rack = await GradillaRepository.get_by_id_with_location(db, g_id)
    g_number = rack.g_number if rack and rack.g_number else str(g_id)
    location = rack.seroteca.location if rack and rack.seroteca else None
    loc_name = location.loc_name if location else "Sin ubicación"
    loc_id = location.loc_id if location else None

    position_label = _format_position_label(row, col)
    observation = f"Muestra almacenada en gradilla [ {g_number} ] posicion [ {position_label} ] Localidad [ {loc_name} ]"
    return observation, loc_id


async def _describe_existing_storage(db: AsyncSession, existing, sample: SamplesOrder, barcode: str) -> str:
    """Mensaje para cuando un barcode ya está ocupando una posición: indica gradilla + posición
    con el formato de etiqueta (ej. 'gradilla 200826-5 posición C1'), y aclara si la muestra
    en esa posición ya fue descartada (para no confundirlo con un almacenamiento activo)."""
    rack = await GradillaRepository.get_by_id_with_location(db, existing.gp_gradilla_id)
    g_number = rack.g_number if rack and rack.g_number else str(existing.gp_gradilla_id)
    position_label = _format_position_label(existing.gp_row, existing.gp_col)

    if sample.so_state == SAMPLE_ORDER_STATE_DESCARTADA:
        return (
            f"La muestra con código de barras '{barcode}' fue descartada. "
            f"Se encontraba almacenada en gradilla {g_number} posición {position_label}."
        )
    return f"La muestra con código de barras '{barcode}' ya está almacenada en gradilla {g_number} posición {position_label}."


async def _sample_work_group_ids(db: AsyncSession, sample: SamplesOrder) -> set[int]:
    """
    Retorna el conjunto de work_group_id de los estudios de la orden de la
    muestra cuyas pruebas se extraen de ESTE tubo (mismo grupo de sufijo de
    tipo de muestra que su sample_type), para validar contra los grupos de
    trabajo asignados a una gradilla.
    """
    from app.domains.samples.domain.models import SampleType
    from app.domains.testslabs.domain.models import TestsLab
    from app.domains.studieslab.domain.models import StudiesTestDetail, StudiesLab
    from app.domains.orders.domain.models import OrdersDetail

    if not sample.so_sample_type_id or not sample.so_order_id:
        return set()

    all_st_rows = (await db.execute(select(SampleType))).scalars().all()
    st_by_id = {st.st_id: st for st in all_st_rows}
    st = st_by_id.get(sample.so_sample_type_id)
    sfx = st.st_sufix if st and st.st_sufix is not None else sample.so_sample_type_id
    related_st_ids = {
        s.st_id for s in all_st_rows
        if (s.st_sufix if s.st_sufix is not None else s.st_id) == sfx
    } or {sample.so_sample_type_id}

    tube_test_ids = set(
        (await db.execute(
            select(TestsLab.id).where(TestsLab.samples_type_id.in_(related_st_ids))
        )).scalars().all()
    )
    if not tube_test_ids:
        return set()

    wg_rows = (
        await db.execute(
            select(StudiesLab.work_groups_id)
            .select_from(OrdersDetail)
            .join(StudiesLab, StudiesLab.id == OrdersDetail.od_study_id)
            .join(StudiesTestDetail, StudiesTestDetail.studies_id == OrdersDetail.od_study_id)
            .where(
                OrdersDetail.od_order_id == sample.so_order_id,
                StudiesTestDetail.tests_id.in_(tube_test_ids),
            )
            .distinct()
        )
    ).scalars().all()
    return {wg for wg in wg_rows if wg is not None}


async def _validate_sample_work_group(db: AsyncSession, sample: SamplesOrder, g_id: int) -> None:
    """Exige que la muestra tenga al menos un estudio de alguno de los grupos de trabajo asignados a la gradilla."""
    from app.domains.seroteca.domain.models import GradillaWorkGroup

    rack_wg_ids = set(
        (await db.execute(
            select(GradillaWorkGroup.gwg_work_group_id).where(GradillaWorkGroup.gwg_gradilla_id == g_id)
        )).scalars().all()
    )
    if not rack_wg_ids:
        return  # gradilla sin restricción de grupo de trabajo

    sample_wgs = await _sample_work_group_ids(db, sample)
    if not (rack_wg_ids & sample_wgs):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La muestra '{sample.so_barcode}' no tiene estudios para esa gradilla.",
        )


async def _get_sample_by_barcode(db: AsyncSession, barcode: str) -> SamplesOrder:
    """Search by barcode. Tries exact match, then reconstructed legacy format {10digits}-{rest}."""
    from sqlalchemy.orm import selectinload

    candidates = [barcode]

    # If input is all digits and longer than 10, try legacy format: first 10 + "-" + rest
    clean = barcode.replace("-", "")
    if clean.isdigit() and len(clean) > 10:
        candidates.append(f"{clean[:10]}-{clean[10:]}")

    for candidate in candidates:
        result = await db.execute(
            select(SamplesOrder)
            .where(SamplesOrder.so_barcode == candidate)
            .options(selectinload(SamplesOrder.order))
        )
        sample = result.scalars().first()
        if sample:
            logger.debug(f"[barcode_search] Found sample {sample.so_id} for candidate='{candidate}'")
            return sample

    logger.warning(f"[barcode_search] Not found for barcode='{barcode}', candidates={candidates}")
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Sample with barcode '{barcode}' not found",
    )


async def log_sample_event(
    db: AsyncSession,
    barcode: str,
    state: int,
    user_id: Optional[int],
    location_id: Optional[int],
    notes: Optional[str],
) -> dict:
    sample = await _get_sample_by_barcode(db, barcode)

    if sample.so_state == SAMPLE_ORDER_STATE_DESCARTADA:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La muestra con código de barras '{barcode}' fue descartada y ya no admite trazabilidad.",
        )

    # When a sample is found and tracked, mark it as "Con Muestra" at the order level
    sample.so_state = SAMPLE_ORDER_STATE_CON_MUESTRA
    if location_id is not None:
        sample.so_current_location_id = location_id
    await db.flush()

    log = await SampleLogRepository.create(db, {
        "log_sample_order_id": sample.so_id,
        "log_state": state,
        "log_location_id": location_id,
        "log_observation": notes,
        "log_user_id": user_id,
    })

    # Obtener los estudios asociados a la orden de la muestra
    from app.domains.orders.domain.models import OrdersDetail
    from app.domains.studieslab.domain.models import StudiesLab
    from sqlalchemy.orm import selectinload

    studies = []
    if sample.order:
        stmt = (
            select(OrdersDetail)
            .where(OrdersDetail.od_order_id == sample.order.o_id)
            .options(selectinload(OrdersDetail.study))
        )
        result = await db.execute(stmt)
        order_details = result.scalars().all()
        seen_study_ids = set()
        for od in order_details:
            if od.study and od.study.id not in seen_study_ids:
                seen_study_ids.add(od.study.id)
                studies.append({
                    "study_id": od.study.id,
                    "study_name": od.study.name,
                    "study_code": od.study.code,
                })

    await db.commit()

    return {
        "sl_id": log.sl_id,
        "log_state": log.log_state,
        "log_observation": log.log_observation,
        "log_create_at": log.log_create_at,
        "so_barcode": sample.so_barcode,
        "so_id": sample.so_id,
        "studies": studies,
    }


async def get_sample_history(
    db: AsyncSession, barcode: str, skip: int, limit: int
) -> dict:
    sample = await _get_sample_by_barcode(db, barcode)
    logs, total = await SampleLogRepository.get_by_sample(db, sample.so_id, skip, limit)

    # Enriquecer cada log con location_name y headquarter_name
    enriched = []
    for log in logs:
        log_dict = {
            "sl_id": log.sl_id,
            "log_sample_order_id": log.log_sample_order_id,
            "log_state": log.log_state,
            "log_location_id": log.log_location_id,
            "location": log.location,
            "log_observation": log.log_observation,
            "log_user_id": log.log_user_id,
            "user": log.user,
            "log_create_at": log.log_create_at,
            "location_name": log.location.loc_name if log.location else None,
            "headquarter_name": None,
        }
        # Obtener el nombre de la sede desde sample → order
        if log.sample and log.sample.order:
            from app.domains.Headquarters.domain.models import Headquarter
            hq = await db.get(Headquarter, log.sample.order.o_headquarter_id)
            log_dict["headquarter_name"] = hq.name if hq else None

        enriched.append(log_dict)

    return {"items": enriched, "total": total, "skip": skip, "limit": limit}


async def auto_store_in_rack(
    db: AsyncSession,
    barcode: str,
    g_id: int,
    user_id: Optional[int],
) -> dict:
    """Auto-assign the sample to the next free position in the rack."""
    sample = await _get_sample_by_barcode(db, barcode)

    # Verificar que el tubo no esté ya almacenado en alguna posición
    existing = await GradillaPosicionRepository.is_sample_stored(db, sample.so_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=await _describe_existing_storage(db, existing, sample, barcode),
        )

    await _validate_sample_work_group(db, sample, g_id)

    pos = await GradillaPosicionRepository.get_next_free(db, g_id)
    if not pos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No free positions available in this rack",
        )

    pos = await GradillaPosicionRepository.store_sample(db, pos.gp_id, sample.so_id, user_id)

    observation, loc_id = await _build_storage_observation(db, g_id, pos.gp_row, pos.gp_col)
    await SampleLogRepository.create(db, {
        "log_sample_order_id": sample.so_id,
        "log_state": 2,  # Almacenada
        "log_location_id": loc_id,
        "log_observation": observation,
        "log_user_id": user_id,
    })

    sample.so_state = SAMPLE_ORDER_STATE_ALMACENADA
    await db.commit()
    return pos


async def manual_store_in_position(
    db: AsyncSession,
    barcode: str,
    gp_id: int,
    user_id: Optional[int],
) -> dict:
    """Place a sample in a specific rack position."""
    sample = await _get_sample_by_barcode(db, barcode)

    # Verificar que el tubo no esté ya almacenado en alguna posición
    existing = await GradillaPosicionRepository.is_sample_stored(db, sample.so_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=await _describe_existing_storage(db, existing, sample, barcode),
        )

    target_pos = await GradillaPosicionRepository.get_by_id(db, gp_id)
    if not target_pos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    await _validate_sample_work_group(db, sample, target_pos.gp_gradilla_id)

    pos = await GradillaPosicionRepository.store_sample(db, gp_id, sample.so_id, user_id)
    if not pos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Position is already occupied or does not exist",
        )

    observation, loc_id = await _build_storage_observation(db, pos.gp_gradilla_id, pos.gp_row, pos.gp_col)
    await SampleLogRepository.create(db, {
        "log_sample_order_id": sample.so_id,
        "log_state": 2,
        "log_location_id": loc_id,
        "log_observation": observation,
        "log_user_id": user_id,
    })

    sample.so_state = SAMPLE_ORDER_STATE_ALMACENADA
    await db.commit()
    return pos


async def release_position(
    db: AsyncSession,
    gp_id: int,
    user_id: Optional[int],
    justification: str,
) -> dict:
    # Capturar el so_id/posición ANTES de liberar: GradillaPosicionRepository.release_position
    # limpia gp_sample_id, así que después de liberarla ya no hay forma de saber qué muestra era.
    target = await GradillaPosicionRepository.get_by_id(db, gp_id)
    if not target or not target.gp_occupied:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Position is already free or does not exist",
        )
    so_id = target.gp_sample_id
    g_id = target.gp_gradilla_id
    row, col = target.gp_row, target.gp_col

    pos = await GradillaPosicionRepository.release_position(db, gp_id)
    if not pos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Position is already free or does not exist",
        )

    if so_id is not None:
        rack = await GradillaRepository.get_by_id_with_location(db, g_id)
        g_number = rack.g_number if rack and rack.g_number else str(g_id)
        location = rack.seroteca.location if rack and rack.seroteca else None
        loc_name = location.loc_name if location else "Sin ubicación"
        loc_id = location.loc_id if location else None
        position_label = _format_position_label(row, col)

        await SampleLogRepository.create(db, {
            "log_sample_order_id": so_id,
            "log_state": SAMPLE_LOG_STATE_RETIRADA,
            "log_location_id": loc_id,
            "log_observation": (
                f"Muestra retirada de gradilla [ {g_number} ] posicion [ {position_label} ] "
                f"Localidad [ {loc_name} ]. Motivo: {justification}"
            ),
            "log_user_id": user_id,
        })
        await db.commit()

    return pos
