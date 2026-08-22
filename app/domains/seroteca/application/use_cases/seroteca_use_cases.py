from typing import Optional
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.seroteca.infrastructure.repository import (
    SerotecaRepository, GradillaRepository, TipoGradillaRepository, SampleLogRepository,
)
from app.domains.traces.constants import OPERATION_MANAGE_SEROTECA, OPERATION_MANAGE_GRADILLA
from app.domains.traces.models import AppTrace
from app.domains.seroteca.domain.models import Seroteca, Gradilla
from app.domains.seroteca.domain.constants import SAMPLE_LOG_STATE_DESCARTADA
from app.domains.samples.domain.constants import SAMPLE_ORDER_STATE_DESCARTADA
from utils.timezone import get_bogota_now


def _add_trace(db: AsyncSession, user_id: int | None, op_type: int, description: str, notes: str | None = None):
    if user_id:
        db.add(AppTrace(
            usr_id=user_id,
            operation_type=op_type,
            operation_description=description,
            notes=notes,
        ))


# ── Serotecas ────────────────────────────────────────────────────────────────

async def create_seroteca(db: AsyncSession, data: dict, user_id: int | None = None) -> dict:
    result = await SerotecaRepository.create(db, data)
    _add_trace(
        db, user_id, OPERATION_MANAGE_SEROTECA,
        f"Creación de seroteca {result.s_name}",
        f"ID: {result.s_id} | Nombre: {result.s_name} | Sede: {result.s_headquarter_id}",
    )
    await db.commit()
    return result


async def get_seroteca(db: AsyncSession, s_id: int) -> dict:
    item = await SerotecaRepository.get_by_id(db, s_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seroteca not found")
    return item


async def list_serotecas(
    db: AsyncSession,
    skip: int,
    limit: int,
    search: Optional[str],
    active_only: bool,
    headquarter_id: Optional[int] = None,
) -> dict:
    items, total = await SerotecaRepository.list_paginated(
        db, skip, limit, search, active_only, headquarter_id
    )
    return {"items": items, "total": total, "skip": skip, "limit": limit}


async def update_seroteca(db: AsyncSession, s_id: int, data: dict, user_id: int | None = None) -> dict:
    # Snapshot before
    before = await SerotecaRepository.get_by_id(db, s_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seroteca not found")

    editable_fields = ["s_name", "s_description", "s_location_id", "s_headquarter_id", "s_active"]
    field_labels = {
        "s_name": "Nombre", "s_description": "Descripción",
        "s_location_id": "Ubicación", "s_headquarter_id": "Sede", "s_active": "Activo",
    }

    before_snap = {f: getattr(before, f, None) for f in editable_fields}

    item = await SerotecaRepository.update(db, s_id, data)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seroteca not found")

    diff = []
    for f in editable_fields:
        if f in data and data[f] is not None:
            old = before_snap.get(f)
            new = data[f]
            if old != new:
                diff.append(f"{field_labels.get(f, f)}: {old} → {new}")

    if diff:
        _add_trace(
            db, user_id, OPERATION_MANAGE_SEROTECA,
            f"Edición de seroteca {item.s_name}",
            " | ".join(diff),
        )
        await db.commit()

    return item


async def delete_seroteca(db: AsyncSession, s_id: int, user_id: int | None = None) -> dict:
    before = await SerotecaRepository.get_by_id(db, s_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seroteca not found")
    name = before.s_name
    deleted = await SerotecaRepository.delete(db, s_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seroteca not found")
    _add_trace(
        db, user_id, OPERATION_MANAGE_SEROTECA,
        f"Eliminación de seroteca {name}",
        f"ID: {s_id} | Nombre: {name}",
    )
    await db.commit()
    return {"detail": "Seroteca deleted"}


# ── Gradillas ────────────────────────────────────────────────────────────────

async def create_rack(db: AsyncSession, data: dict, user_id: int | None = None) -> dict:
    from app.domains.masters.domain.models import WorkGroup

    work_group_ids = data.get("work_group_ids") or []
    found_ids = set((
        await db.execute(select(WorkGroup.wg_id).where(WorkGroup.wg_id.in_(work_group_ids)))
    ).scalars().all())
    missing = set(work_group_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grupo(s) de trabajo no encontrado(s): {', '.join(str(i) for i in sorted(missing))}.",
        )

    # If g_tipo_gradilla_id is provided, auto-fill rows + cols from the template
    tipo = None
    if data.get("g_tipo_gradilla_id"):
        tipo = await TipoGradillaRepository.get_by_id(db, data["g_tipo_gradilla_id"])
        if not tipo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de gradilla not found")
        if not data.get("g_rows"):
            data["g_rows"] = tipo.tg_rows
        if not data.get("g_cols"):
            data["g_cols"] = tipo.tg_cols
        if tipo.tg_storage_days and not data.get("g_discard_date"):
            data["g_discard_date"] = get_bogota_now() + timedelta(days=tipo.tg_storage_days)

    from utils.Consecutives.consecutive_gradillas import generate_gradilla_number
    data["g_number"] = await generate_gradilla_number(db)

    result = await GradillaRepository.create(db, data)
    _add_trace(
        db, user_id, OPERATION_MANAGE_GRADILLA,
        f"Creación de gradilla {result.g_name}",
        (
            f"ID: {result.g_id} | Número: {result.g_number} | Seroteca: {result.g_seroteca_id} "
            f"| {result.g_rows}x{result.g_cols} | Grupos de trabajo: {sorted(work_group_ids)}"
        ),
    )
    await db.commit()
    return result


async def _attach_sample_work_groups(db: AsyncSession, rack: Gradilla) -> None:
    """
    Adjunta a cada muestra almacenada en la gradilla el/los grupo(s) de trabajo
    a los que corresponden sus estudios (mismo criterio que la validación de
    almacenamiento), para que el front pueda mostrar a qué grupo pertenece
    cada muestra.
    """
    from app.domains.masters.domain.models import WorkGroup
    from app.domains.seroteca.application.use_cases.tracking_use_cases import _sample_work_group_ids

    samples = [pos.sample for pos in rack.positions if pos.sample is not None]
    if not samples:
        return

    wg_ids_by_sample: dict[int, set[int]] = {}
    all_wg_ids: set[int] = set()
    for sample in samples:
        wg_ids = await _sample_work_group_ids(db, sample)
        wg_ids_by_sample[sample.so_id] = wg_ids
        all_wg_ids |= wg_ids

    wg_by_id: dict[int, WorkGroup] = {}
    if all_wg_ids:
        wg_rows = (await db.execute(select(WorkGroup).where(WorkGroup.wg_id.in_(all_wg_ids)))).scalars().all()
        wg_by_id = {wg.wg_id: wg for wg in wg_rows}

    for sample in samples:
        sample.work_groups = [
            wg_by_id[wg_id] for wg_id in sorted(wg_ids_by_sample.get(sample.so_id, set())) if wg_id in wg_by_id
        ]


async def get_rack(db: AsyncSession, g_id: int) -> dict:
    rack = await GradillaRepository.get_by_id(db, g_id)
    if not rack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rack not found")
    await _attach_sample_work_groups(db, rack)
    return rack


async def list_racks(
    db: AsyncSession,
    s_id: int,
    skip: int,
    limit: int,
    search: Optional[str] = None,
    discarted: Optional[bool] = None,
) -> dict:
    items, total = await GradillaRepository.list_by_seroteca(db, s_id, skip, limit, search, discarted)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


async def update_rack(db: AsyncSession, g_id: int, data: dict, user_id: int | None = None) -> dict:
    before = await GradillaRepository.get_by_id(db, g_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rack not found")

    work_group_ids = data.get("work_group_ids")
    if work_group_ids is not None:
        from app.domains.masters.domain.models import WorkGroup
        found_ids = set((
            await db.execute(select(WorkGroup.wg_id).where(WorkGroup.wg_id.in_(work_group_ids)))
        ).scalars().all())
        missing = set(work_group_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo(s) de trabajo no encontrado(s): {', '.join(str(i) for i in sorted(missing))}.",
            )

        # No permitir desvincular un grupo de trabajo si la gradilla ya tiene
        # muestras almacenadas que corresponden a ese grupo.
        current_wg_ids = {link.gwg_work_group_id for link in before.work_group_links}
        removed_wg_ids = current_wg_ids - set(work_group_ids)
        if removed_wg_ids:
            from app.domains.seroteca.application.use_cases.tracking_use_cases import _sample_work_group_ids

            occupied_samples = [pos.sample for pos in before.positions if pos.gp_occupied and pos.sample is not None]
            barcodes_by_blocked_wg: dict[int, list[str]] = {}
            for sample in occupied_samples:
                sample_wgs = await _sample_work_group_ids(db, sample)
                for wg_id in sample_wgs & removed_wg_ids:
                    barcodes_by_blocked_wg.setdefault(wg_id, []).append(sample.so_barcode)

            if barcodes_by_blocked_wg:
                wg_rows = (
                    await db.execute(select(WorkGroup).where(WorkGroup.wg_id.in_(barcodes_by_blocked_wg.keys())))
                ).scalars().all()
                wg_name_by_id = {wg.wg_id: wg.wg_name for wg in wg_rows}
                details = "; ".join(
                    f"{wg_name_by_id.get(wg_id, wg_id)} (muestras: {', '.join(barcodes)})"
                    for wg_id, barcodes in barcodes_by_blocked_wg.items()
                )
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"No se puede desvincular el/los grupo(s) de trabajo con muestras ya "
                        f"almacenadas en la gradilla: {details}."
                    ),
                )

    editable_fields = ["g_name", "g_rows", "g_cols", "g_discard_date", "g_active"]
    field_labels = {
        "g_name": "Nombre", "g_rows": "Filas", "g_cols": "Columnas",
        "g_discard_date": "Fecha descarte", "g_active": "Activo",
    }
    before_snap = {f: getattr(before, f, None) for f in editable_fields}
    before_wg_ids = sorted(link.gwg_work_group_id for link in before.work_group_links)

    rack = await GradillaRepository.update(db, g_id, data)
    if not rack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rack not found")

    diff = []
    for f in editable_fields:
        if f in data and data[f] is not None:
            old = before_snap.get(f)
            new = data[f]
            if old != new:
                diff.append(f"{field_labels.get(f, f)}: {old} → {new}")

    if work_group_ids is not None and sorted(work_group_ids) != before_wg_ids:
        diff.append(f"Grupos de trabajo: {before_wg_ids} → {sorted(work_group_ids)}")

    if diff:
        _add_trace(
            db, user_id, OPERATION_MANAGE_GRADILLA,
            f"Edición de gradilla {rack.g_name}",
            " | ".join(diff),
        )
        await db.commit()

    return rack


async def delete_rack(db: AsyncSession, g_id: int, user_id: int | None = None) -> dict:
    before = await GradillaRepository.get_by_id(db, g_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rack not found")

    occupied = [pos for pos in before.positions if pos.gp_occupied and pos.sample is not None]
    if occupied:
        barcodes = ", ".join(pos.sample.so_barcode for pos in occupied)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"No se puede eliminar la gradilla '{before.g_name}': todavía tiene "
                f"{len(occupied)} muestra(s) almacenada(s) ({barcodes}). Retire o descarte "
                f"las muestras antes de eliminarla."
            ),
        )

    name = before.g_name
    number = before.g_number
    deleted = await GradillaRepository.delete(db, g_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rack not found")
    _add_trace(
        db, user_id, OPERATION_MANAGE_GRADILLA,
        f"Eliminación de gradilla {name}",
        f"ID: {g_id} | Número: {number} | Nombre: {name}",
    )
    await db.commit()
    return {"detail": "Rack and all its positions deleted"}


async def _get_pending_tests_by_sample(db: AsyncSession, samples: list) -> dict[int, list[str]]:
    """
    Para cada muestra (tubo), determina qué pruebas siguen pendientes de
    procesar (l_state en Sin Resultados=0, Pendiente=1 o Con Resultados=2),
    considerando SOLO las pruebas que se extraen de ESE tubo (mismo sufijo de
    tipo de muestra que el tubo, dentro de la misma orden) y aplicando la
    regla de is_required por estudio: si el estudio tiene pruebas requeridas,
    solo esas determinan si está pendiente; si no tiene ninguna requerida,
    deben estar procesadas todas sus pruebas.

    Retorna {so_id: [codigo_prueba, ...]} — solo para las muestras que
    todavía tienen algo pendiente.
    """
    from app.domains.samples.domain.models import SampleType
    from app.domains.testslabs.domain.models import TestsLab
    from app.domains.studieslab.domain.models import StudiesTestDetail
    from app.domains.laboratories.domain.models import Laboratory
    from app.domains.orders.domain.models import OrdersDetail

    PENDING_LAB_STATES = (0, 1, 2)  # Sin Resultados, Pendiente, Con Resultados

    # Agrupar todos los SampleTypes por sufijo (un tubo puede alimentar
    # varios SampleTypes que comparten el mismo sufijo físico)
    all_st_rows = (await db.execute(select(SampleType))).scalars().all()
    st_by_id = {st.st_id: st for st in all_st_rows}
    suffix_groups: dict[int, set[int]] = {}
    for st in all_st_rows:
        sfx = st.st_sufix if st.st_sufix is not None else st.st_id
        suffix_groups.setdefault(sfx, set()).add(st.st_id)

    pending_by_sample: dict[int, list[str]] = {}

    for sample in samples:
        if not sample.so_sample_type_id or not sample.so_order_id:
            continue

        st = st_by_id.get(sample.so_sample_type_id)
        sfx = st.st_sufix if st and st.st_sufix is not None else sample.so_sample_type_id
        related_st_ids = suffix_groups.get(sfx, {sample.so_sample_type_id})

        tube_tests = (
            await db.execute(
                select(TestsLab.id, TestsLab.code).where(TestsLab.samples_type_id.in_(related_st_ids))
            )
        ).all()
        tube_test_ids = {r.id for r in tube_tests}
        test_code_by_id = {r.id: (r.code or str(r.id)) for r in tube_tests}
        if not tube_test_ids:
            continue

        lab_rows = (
            await db.execute(
                select(Laboratory.l_test_id, Laboratory.l_state, OrdersDetail.od_study_id)
                .join(OrdersDetail, OrdersDetail.od_id == Laboratory.l_order_detail_id)
                .where(
                    OrdersDetail.od_order_id == sample.so_order_id,
                    Laboratory.l_test_id.in_(tube_test_ids),
                )
            )
        ).all()
        if not lab_rows:
            continue

        study_ids = {r.od_study_id for r in lab_rows}
        required_rows = (
            await db.execute(
                select(StudiesTestDetail.studies_id, StudiesTestDetail.tests_id).where(
                    StudiesTestDetail.studies_id.in_(study_ids),
                    StudiesTestDetail.is_required == True,
                )
            )
        ).all()
        required_by_study: dict[int, set[int]] = {}
        for r in required_rows:
            required_by_study.setdefault(r.studies_id, set()).add(r.tests_id)

        labs_by_study: dict[int, list] = {}
        for r in lab_rows:
            labs_by_study.setdefault(r.od_study_id, []).append(r)

        pending_codes: list[str] = []
        for study_id, study_labs in labs_by_study.items():
            required_ids = required_by_study.get(study_id, set())
            # Solo las pruebas requeridas determinan si el estudio está pendiente;
            # si no hay ninguna requerida definida, deben estar procesadas todas.
            relevant = [l for l in study_labs if l.l_test_id in required_ids] if required_ids else study_labs
            for lab in relevant:
                if lab.l_state in PENDING_LAB_STATES:
                    code = test_code_by_id.get(lab.l_test_id, str(lab.l_test_id))
                    if code not in pending_codes:
                        pending_codes.append(code)

        if pending_codes:
            pending_by_sample[sample.so_id] = pending_codes

    return pending_by_sample


async def _get_user_display_name(db: AsyncSession, user_id: int | None) -> str:
    from app.domains.users.infrastructure.models import AppUser

    user = await db.get(AppUser, user_id) if user_id else None
    parts = [
        user.usr_first_name if user else None,
        user.usr_middle_name if user else None,
        user.usr_last_name if user else None,
        user.usr_second_last_name if user else None,
    ]
    return " ".join(p for p in parts if p).strip() or "Usuario desconocido"


def _pending_sample_info(pos, pending_by_sample: dict[int, list[str]]) -> dict:
    pending = pending_by_sample[pos.sample.so_id]
    return {
        "so_id": pos.sample.so_id,
        "so_barcode": pos.sample.so_barcode,
        "pending_tests": pending,
        "message": f"Muestra {pos.sample.so_barcode} tiene pendiente {', '.join(pending)}",
    }


async def _discard_samples(
    db: AsyncSession,
    samples: list,
    user_id: int,
    user_name: str,
    loc_id: Optional[int],
    loc_name: str,
    time_str: str,
) -> list[int]:
    discarded_ids: list[int] = []
    for sample in samples:
        sample.so_state = SAMPLE_ORDER_STATE_DESCARTADA
        await SampleLogRepository.create(db, {
            "log_sample_order_id": sample.so_id,
            "log_state": SAMPLE_LOG_STATE_DESCARTADA,
            "log_location_id": loc_id,
            "log_observation": f"Muestra Descartada por [ {user_name} ] [ {time_str} ] [ {loc_name} ]",
            "log_user_id": user_id,
        })
        discarded_ids.append(sample.so_id)
    return discarded_ids


async def discard_rack(db: AsyncSession, g_id: int, user_id: int) -> dict:
    """
    Descarta las muestras de una gradilla que ya tienen todos sus estudios
    procesados (poniendo so_state=4 y registrando un SamplesLog por cada
    una). Las muestras con estudios pendientes se OMITEN (no se tocan) y se
    reportan en la respuesta para que el usuario sepa qué falta.

    La gradilla solo queda marcada como completamente descartada
    (g_discarted=1) cuando, al final de la operación, no le queda ninguna
    muestra pendiente. Si aún quedan muestras pendientes, la gradilla sigue
    con g_discarted=0 y puede volver a intentarse más adelante.
    """
    rack = await GradillaRepository.get_by_id_for_discard(db, g_id)
    if not rack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rack not found")
    if rack.g_discarted:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La gradilla '{rack.g_name}' ya fue descartada.",
        )

    occupied_positions = [pos for pos in rack.positions if pos.gp_occupied and pos.sample is not None]
    # Muestras que ya estaban descartadas de un intento parcial anterior: no se tocan ni se reportan
    active_positions = [pos for pos in occupied_positions if pos.sample.so_state != SAMPLE_ORDER_STATE_DESCARTADA]

    pending_by_sample = await _get_pending_tests_by_sample(db, [pos.sample for pos in active_positions])

    ready_positions = [pos for pos in active_positions if pos.sample.so_id not in pending_by_sample]
    pending_samples = [
        _pending_sample_info(pos, pending_by_sample)
        for pos in active_positions
        if pos.sample.so_id in pending_by_sample
    ]

    user_name = await _get_user_display_name(db, user_id)
    location = rack.seroteca.location if rack.seroteca else None
    loc_name = location.loc_name if location else "Sin ubicación"
    loc_id = location.loc_id if location else None

    now = get_bogota_now()
    time_str = now.strftime("%I:%M:%S %p").lower()

    discarded_sample_ids = await _discard_samples(
        db, [pos.sample for pos in ready_positions], user_id, user_name, loc_id, loc_name, time_str
    )

    fully_discarded = len(pending_samples) == 0
    if fully_discarded:
        rack.g_discarted = 1
        rack.g_updated_at = get_bogota_now()

    _add_trace(
        db, user_id, OPERATION_MANAGE_GRADILLA,
        f"Descarte de gradilla {rack.g_name}",
        (
            f"ID: {rack.g_id} | Número: {rack.g_number} | Muestras descartadas: {len(discarded_sample_ids)} "
            f"| Muestras pendientes (omitidas): {len(pending_samples)} | Gradilla completamente descartada: {fully_discarded}"
        ),
    )

    await db.commit()
    await db.refresh(rack)

    if fully_discarded:
        message = f"Gradilla '{rack.g_name}' descartada completamente. {len(discarded_sample_ids)} muestra(s) marcada(s) como Descartada."
    elif discarded_sample_ids:
        message = (
            f"{len(discarded_sample_ids)} muestra(s) marcada(s) como Descartada. "
            f"{len(pending_samples)} muestra(s) quedaron pendientes por tener estudios sin procesar "
            f"— la gradilla NO quedó completamente descartada."
        )
    else:
        message = (
            f"No se descartó ninguna muestra: las {len(pending_samples)} muestra(s) de la gradilla "
            f"todavía tienen estudios pendientes por procesar."
        )

    return {
        "g_id": rack.g_id,
        "g_name": rack.g_name,
        "g_discarted": rack.g_discarted,
        "fully_discarded": fully_discarded,
        "samples_discarded": len(discarded_sample_ids),
        "discarded_sample_ids": discarded_sample_ids,
        "samples_pending": len(pending_samples),
        "pending_samples": pending_samples,
        "message": message,
    }


async def discard_rack_by_work_group(db: AsyncSession, g_id: int, work_group_id: int, user_id: int) -> dict:
    """
    Descarta, dentro de una gradilla, solo las muestras cuyos estudios
    correspondan al grupo de trabajo indicado y que ya tengan todo procesado.
    Las muestras de ese grupo que sigan pendientes se reportan pero no se
    tocan (igual que en discard_rack). La gradilla completa solo queda
    marcada como g_discarted=1 si, al terminar, no queda ninguna muestra
    activa pendiente en TODA la gradilla (no solo en el grupo indicado).
    """
    from app.domains.masters.domain.models import WorkGroup
    from app.domains.seroteca.application.use_cases.tracking_use_cases import _sample_work_group_ids

    work_group = await db.get(WorkGroup, work_group_id)
    if not work_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grupo de trabajo con ID {work_group_id} no encontrado.",
        )

    rack = await GradillaRepository.get_by_id_for_discard(db, g_id)
    if not rack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rack not found")
    if rack.g_discarted:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La gradilla '{rack.g_name}' ya fue descartada.",
        )

    occupied_positions = [pos for pos in rack.positions if pos.gp_occupied and pos.sample is not None]
    active_positions = [pos for pos in occupied_positions if pos.sample.so_state != SAMPLE_ORDER_STATE_DESCARTADA]

    pending_by_sample = await _get_pending_tests_by_sample(db, [pos.sample for pos in active_positions])

    group_positions = []
    for pos in active_positions:
        wgs = await _sample_work_group_ids(db, pos.sample)
        if work_group_id in wgs:
            group_positions.append(pos)

    if not group_positions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La gradilla '{rack.g_name}' no tiene muestras activas del grupo de trabajo '{work_group.wg_name}'.",
        )

    ready_positions = [pos for pos in group_positions if pos.sample.so_id not in pending_by_sample]
    pending_samples = [
        _pending_sample_info(pos, pending_by_sample)
        for pos in group_positions
        if pos.sample.so_id in pending_by_sample
    ]

    user_name = await _get_user_display_name(db, user_id)
    location = rack.seroteca.location if rack.seroteca else None
    loc_name = location.loc_name if location else "Sin ubicación"
    loc_id = location.loc_id if location else None

    now = get_bogota_now()
    time_str = now.strftime("%I:%M:%S %p").lower()

    discarded_sample_ids = await _discard_samples(
        db, [pos.sample for pos in ready_positions], user_id, user_name, loc_id, loc_name, time_str
    )

    # ¿Queda algo activo en TODA la gradilla (no solo en el grupo) tras este descarte?
    remaining_active = len(active_positions) - len(discarded_sample_ids)
    fully_discarded = remaining_active == 0
    if fully_discarded:
        rack.g_discarted = 1
        rack.g_updated_at = get_bogota_now()

    _add_trace(
        db, user_id, OPERATION_MANAGE_GRADILLA,
        f"Descarte de gradilla {rack.g_name} - grupo {work_group.wg_name}",
        (
            f"ID: {rack.g_id} | Número: {rack.g_number} | Grupo de trabajo: {work_group.wg_name} "
            f"| Muestras descartadas: {len(discarded_sample_ids)} | Muestras pendientes (omitidas): {len(pending_samples)} "
            f"| Gradilla completamente descartada: {fully_discarded}"
        ),
    )

    await db.commit()
    await db.refresh(rack)

    if discarded_sample_ids and not pending_samples:
        message = f"{len(discarded_sample_ids)} muestra(s) del grupo '{work_group.wg_name}' descartada(s) correctamente."
    elif discarded_sample_ids:
        message = (
            f"{len(discarded_sample_ids)} muestra(s) del grupo '{work_group.wg_name}' descartada(s). "
            f"{len(pending_samples)} muestra(s) de ese grupo quedaron pendientes por tener estudios sin procesar."
        )
    else:
        message = (
            f"No se descartó ninguna muestra del grupo '{work_group.wg_name}': "
            f"las {len(pending_samples)} muestra(s) todavía tienen estudios pendientes por procesar."
        )

    return {
        "g_id": rack.g_id,
        "g_name": rack.g_name,
        "g_discarted": rack.g_discarted,
        "fully_discarded": fully_discarded,
        "samples_discarded": len(discarded_sample_ids),
        "discarded_sample_ids": discarded_sample_ids,
        "samples_pending": len(pending_samples),
        "pending_samples": pending_samples,
        "message": message,
    }


async def discard_sample(db: AsyncSession, g_id: int, so_id: int, user_id: int) -> dict:
    """
    Descarta una única muestra (por so_id) dentro de una gradilla, siempre
    que ya tenga todos sus estudios procesados. Si tiene estudios
    pendientes, no se descarta y se informa cuáles faltan.
    """
    rack = await GradillaRepository.get_by_id_for_discard(db, g_id)
    if not rack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rack not found")

    pos = next(
        (p for p in rack.positions if p.gp_occupied and p.sample is not None and p.sample.so_id == so_id),
        None,
    )
    if not pos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La muestra con ID {so_id} no está almacenada en la gradilla '{rack.g_name}'.",
        )

    sample = pos.sample
    if sample.so_state == SAMPLE_ORDER_STATE_DESCARTADA:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La muestra '{sample.so_barcode}' ya fue descartada.",
        )

    pending_by_sample = await _get_pending_tests_by_sample(db, [sample])
    if sample.so_id in pending_by_sample:
        pending = pending_by_sample[sample.so_id]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Muestra {sample.so_barcode} tiene pendiente {', '.join(pending)}",
        )

    user_name = await _get_user_display_name(db, user_id)
    location = rack.seroteca.location if rack.seroteca else None
    loc_name = location.loc_name if location else "Sin ubicación"
    loc_id = location.loc_id if location else None

    now = get_bogota_now()
    time_str = now.strftime("%I:%M:%S %p").lower()

    await _discard_samples(db, [sample], user_id, user_name, loc_id, loc_name, time_str)

    occupied_positions = [p for p in rack.positions if p.gp_occupied and p.sample is not None]
    remaining_active = [
        p for p in occupied_positions
        if p.sample.so_id != sample.so_id and p.sample.so_state != SAMPLE_ORDER_STATE_DESCARTADA
    ]
    fully_discarded = len(remaining_active) == 0
    if fully_discarded and not rack.g_discarted:
        rack.g_discarted = 1
        rack.g_updated_at = get_bogota_now()

    _add_trace(
        db, user_id, OPERATION_MANAGE_GRADILLA,
        f"Descarte individual de muestra {sample.so_barcode} - gradilla {rack.g_name}",
        (
            f"ID gradilla: {rack.g_id} | Número: {rack.g_number} | Muestra: {sample.so_barcode} (so_id {sample.so_id}) "
            f"| Gradilla completamente descartada: {fully_discarded}"
        ),
    )

    await db.commit()
    await db.refresh(rack)
    await db.refresh(sample)

    return {
        "so_id": sample.so_id,
        "so_barcode": sample.so_barcode,
        "so_state": sample.so_state,
        "g_id": rack.g_id,
        "g_name": rack.g_name,
        "g_discarted": rack.g_discarted,
        "fully_discarded": fully_discarded,
        "message": f"Muestra '{sample.so_barcode}' descartada correctamente.",
    }


# ── Tipos de Gradilla ─────────────────────────────────────────────────────────

async def create_tipo_gradilla(db: AsyncSession, data: dict) -> dict:
    return await TipoGradillaRepository.create(db, data)


async def get_tipo_gradilla(db: AsyncSession, tg_id: int) -> dict:
    item = await TipoGradillaRepository.get_by_id(db, tg_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de gradilla not found")
    return item


async def list_tipos_gradilla(
    db: AsyncSession,
    skip: int,
    limit: int,
    search: Optional[str] = None,
    active_only: bool = False,
) -> dict:
    items, total = await TipoGradillaRepository.list_paginated(db, skip, limit, search, active_only)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


async def update_tipo_gradilla(db: AsyncSession, tg_id: int, data: dict) -> dict:
    item = await TipoGradillaRepository.update(db, tg_id, data)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de gradilla not found")
    return item


async def delete_tipo_gradilla(db: AsyncSession, tg_id: int) -> dict:
    deleted = await TipoGradillaRepository.delete(db, tg_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de gradilla not found")
    return {"detail": "Tipo de gradilla deleted"}


# ── Gradilla Sticker Generation ──────────────────────────────────────────────

async def generate_gradilla_sticker(db: AsyncSession, g_id: int) -> dict:
    from app.domains.seroteca.infrastructure.gradilla_sticker import generate_sticker

    rack = await GradillaRepository.get_by_id(db, g_id)
    if not rack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gradilla not found")

    return generate_sticker(rack)