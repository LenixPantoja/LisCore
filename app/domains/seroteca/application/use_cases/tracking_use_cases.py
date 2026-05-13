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


async def _get_sample_by_barcode(db: AsyncSession, barcode: str) -> SamplesOrder:
    """Search by barcode. Tries exact match, then reconstructed legacy format {10digits}-{rest}."""
    candidates = [barcode]

    # If input is all digits and longer than 10, try legacy format: first 10 + "-" + rest
    clean = barcode.replace("-", "")
    if clean.isdigit() and len(clean) > 10:
        candidates.append(f"{clean[:10]}-{clean[10:]}")

    for candidate in candidates:
        result = await db.execute(
            select(SamplesOrder).where(SamplesOrder.so_barcode == candidate)
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

    sample.so_state = state
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
    await db.commit()
    return log


async def get_sample_history(
    db: AsyncSession, barcode: str, skip: int, limit: int
) -> dict:
    sample = await _get_sample_by_barcode(db, barcode)
    logs, total = await SampleLogRepository.get_by_sample(db, sample.so_id, skip, limit)
    return {"items": logs, "total": total, "skip": skip, "limit": limit}


async def auto_store_in_rack(
    db: AsyncSession,
    barcode: str,
    g_id: int,
    user_id: Optional[int],
) -> dict:
    """Auto-assign the sample to the next free position in the rack."""
    sample = await _get_sample_by_barcode(db, barcode)

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

    sample.so_state = 2
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

    sample.so_state = 2
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
