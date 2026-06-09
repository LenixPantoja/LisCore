from typing import Optional
import logging
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.domains.seroteca.infrastructure.repository import (
    SampleLogRepository,
    GradillaPosicionRepository,
)
from app.domains.samples.domain.models import SamplesOrder
from app.domains.samples.domain.constants import (
    SAMPLE_ORDER_STATE_CON_MUESTRA,
    SAMPLE_ORDER_STATE_ALMACENADA,
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
        for od in order_details:
            if od.study:
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
            detail=f"La muestra con código de barras '{barcode}' ya está almacenada en la posición {existing.gp_id} (rack {existing.gp_gradilla_id}, fila {existing.gp_row}, col {existing.gp_col}).",
        )

    pos = await GradillaPosicionRepository.get_next_free(db, g_id)
    if not pos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No free positions available in this rack",
        )

    pos = await GradillaPosicionRepository.store_sample(db, pos.gp_id, sample.so_id, user_id)

    await SampleLogRepository.create(db, {
        "log_sample_order_id": sample.so_id,
        "log_state": 2,  # Almacenada
        "log_location_id": None,
        "log_observation": f"Stored in rack {g_id}, row {pos.gp_row}, col {pos.gp_col}",
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
            detail=f"La muestra con código de barras '{barcode}' ya está almacenada en la posición {existing.gp_id} (rack {existing.gp_gradilla_id}, fila {existing.gp_row}, col {existing.gp_col}).",
        )

    pos = await GradillaPosicionRepository.store_sample(db, gp_id, sample.so_id, user_id)
    if not pos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Position is already occupied or does not exist",
        )

    await SampleLogRepository.create(db, {
        "log_sample_order_id": sample.so_id,
        "log_state": 2,
        "log_location_id": None,
        "log_observation": f"Manually stored in position {gp_id} (row {pos.gp_row}, col {pos.gp_col})",
        "log_user_id": user_id,
    })

    sample.so_state = SAMPLE_ORDER_STATE_ALMACENADA
    await db.commit()
    return pos


async def release_position(
    db: AsyncSession,
    gp_id: int,
    user_id: Optional[int],
) -> dict:
    pos = await GradillaPosicionRepository.release_position(db, gp_id)
    if not pos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Position is already free or does not exist",
        )

    # Log the retrieval
    if pos.gp_sample_id is not None:
        await SampleLogRepository.create(db, {
            "log_sample_order_id": pos.gp_sample_id,
            "log_state": 3,  # Retirada
            "log_location_id": None,
            "log_observation": f"Retrieved from position {gp_id}",
            "log_user_id": user_id,
        })
        await db.commit()

    return pos
