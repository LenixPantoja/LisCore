"""
Use case: generate barcode stickers for tubes in an order.

Logic:
  - Load order → patient, enterprise
  - Load SamplesOrder (tubes) for the order
  - Load StudiesLab ordered in the order (via OrdersDetail)
      Each study has: code, work_groups_id
      Each study's test_details → TestsLab.samples_type_id (which tube type)
  - For each tube (SamplesOrder):
      Find studies whose tests cover the tube's sample type.
      Group studies by StudiesLab.work_groups_id → one sticker per group.
      tests_line shows study codes (-BHC-QS - SUERO).
"""
from collections import defaultdict
from datetime import date
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.samples.domain.models import SamplesOrder, SampleType
from app.domains.studieslab.domain.models import StudiesLab, StudiesTestDetail
from app.domains.masters.domain.models import WorkGroup
from app.domains.reports.infrastructure.printer_barcodes.barcode_generator import (
    build_stickers_pdf,
    pdf_to_base64,
)


async def generate_barcode_stickers(db: AsyncSession, order_id: int) -> dict:
    # 1. Load order with patient and enterprise
    order_result = await db.execute(
        select(Order)
        .filter(Order.o_id == order_id)
        .options(
            selectinload(Order.patient),
            selectinload(Order.enterprise),
        )
    )
    order = order_result.scalars().first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden con ID {order_id} no encontrada.",
        )

    # 2. Load tubes (SamplesOrder) with their sample type
    tubes_result = await db.execute(
        select(SamplesOrder)
        .filter(SamplesOrder.so_order_id == order_id)
        .options(selectinload(SamplesOrder.sample_type))
    )
    tubes: List[SamplesOrder] = tubes_result.scalars().all()

    if not tubes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La orden {order_id} no tiene tubos/muestras registradas.",
        )

    # 3. Load distinct study IDs in the order
    od_result = await db.execute(
        select(OrdersDetail.od_study_id)
        .filter(OrdersDetail.od_order_id == order_id)
        .distinct()
    )
    study_ids: List[int] = od_result.scalars().all()

    if not study_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La orden {order_id} no tiene estudios registrados.",
        )

    # 4. Load StudiesLab with test_details → TestsLab (for sample type lookup)
    studies_result = await db.execute(
        select(StudiesLab)
        .filter(StudiesLab.id.in_(study_ids))
        .options(
            selectinload(StudiesLab.test_details).selectinload(StudiesTestDetail.test),
            selectinload(StudiesLab.work_group),
        )
    )
    studies: List[StudiesLab] = studies_result.scalars().all()

    # 5. Collect work group IDs and build wg_map
    wg_ids = {s.work_groups_id for s in studies if s.work_groups_id}
    wg_map: dict[int, WorkGroup] = {}
    if wg_ids:
        wg_result = await db.execute(
            select(WorkGroup).filter(WorkGroup.wg_id.in_(wg_ids))
        )
        for wg in wg_result.scalars().all():
            wg_map[wg.wg_id] = wg

    # 6. For each study, compute which sample type IDs it covers (from its tests)
    #    study_id → set of sample_type_ids (empty = all tube types)
    tube_sample_type_ids = {t.so_sample_type_id for t in tubes if t.so_sample_type_id}

    # sample_wg_studies[sample_type_id][wg_id] = [study_code, ...]
    sample_wg_studies: dict[int, dict[int, list[str]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for study in studies:
        wg_id = study.work_groups_id
        if not wg_id:
            continue
        code = (study.code or study.name or "").strip()
        if not code:
            continue

        # Determine which sample types this study covers
        covered_st_ids: set[int] = set()
        for std in study.test_details:
            if std.test and std.test.samples_type_id is not None:
                covered_st_ids.add(std.test.samples_type_id)

        target_st_ids = covered_st_ids if covered_st_ids else tube_sample_type_ids

        for st_id in target_st_ids:
            if code not in sample_wg_studies[st_id][wg_id]:
                sample_wg_studies[st_id][wg_id].append(code)

    # 7. Build patient header data
    patient = order.patient
    enterprise = order.enterprise

    patient_full_name = " ".join(filter(None, [
        getattr(patient, "pt_firts_name", None),
        getattr(patient, "pt_middle_name", None),
        getattr(patient, "pt_last_name", None),
        getattr(patient, "pt_second_last_name", None),
    ])).upper() if patient else "PACIENTE"

    identification = (
        getattr(patient, "pt_Number_document", "-") if patient else "-"
    )
    enterprise_name = (
        (getattr(enterprise, "en_description", None) or "").upper()
        if enterprise else "-"
    )

    age_str = "-"
    if patient and getattr(patient, "pt_date_of_birth", None):
        dob = patient.pt_date_of_birth
        today = date.today()
        years = (
            today.year - dob.year
            - ((today.month, today.day) < (dob.month, dob.day))
        )
        age_str = f"{years} A"

    # 8. Build sticker data list: one sticker per (tube × work_group)
    stickers = []

    for tube in tubes:
        st: SampleType | None = tube.sample_type
        if not st:
            continue
        st_id = st.st_id
        sample_type_name = (st.st_name or "").upper()
        sufix = st.st_sufix if st.st_sufix is not None else ""
        barcode_value = f"{order.o_number}{sufix}"
        label_number = f"{order.o_number}-{sufix}"

        wg_studies_for_tube: dict[int, list[str]] = sample_wg_studies.get(st_id, {})

        if not wg_studies_for_tube:
            # No studies configured for this tube → generic sticker
            stickers.append({
                "patient_full_name": patient_full_name,
                "identification": identification,
                "enterprise_name": enterprise_name,
                "age_str": age_str,
                "work_group_name": sample_type_name,
                "barcode_value": barcode_value,
                "label_number": label_number,
                "tests_line": f"- {sample_type_name}",
            })
            continue

        # Sort work groups by wg_order_of_print
        sorted_wg_ids = sorted(
            wg_studies_for_tube.keys(),
            key=lambda wid: (
                (wg_map[wid].wg_order_of_print or 999)
                if wid in wg_map else 999
            ),
        )

        for wg_id in sorted_wg_ids:
            wg: WorkGroup | None = wg_map.get(wg_id)
            wg_name = (wg.wg_name or "").upper() if wg else f"GRUPO {wg_id}"
            codes = wg_studies_for_tube[wg_id]
            tests_line = f"-{'-'.join(codes)} - {sample_type_name}"

            stickers.append({
                "patient_full_name": patient_full_name,
                "identification": identification,
                "enterprise_name": enterprise_name,
                "age_str": age_str,
                "work_group_name": wg_name,
                "barcode_value": barcode_value,
                "label_number": label_number,
                "tests_line": tests_line,
            })

    if not stickers:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se pudieron generar stickers. Verifique que los estudios "
                   "tengan pruebas y tipos de muestra configurados.",
        )

    # 9. Build PDF and return
    pdf_bytes = build_stickers_pdf(stickers)
    b64 = pdf_to_base64(pdf_bytes)

    filename = f"stickers_{order.o_number}_{identification.replace(' ', '_')}.pdf"

    return {
        "filename": filename,
        "base64_pdf": b64,
        "order_number": order.o_number,
        "order_id": order_id,
        "total_stickers": len(stickers),
    }
