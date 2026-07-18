"""
Use case: generate barcode stickers for tubes in an order.

Logic:
  - Load order → patient, enterprise
  - Load SamplesOrder (tubes) for the order
  - Load StudiesLab ordered in the order (via OrdersDetail)
      Each study has: code, work_groups_id
      Each study's test_details → TestsLab.samples_type_id (which tube type)
  - For each tube (SamplesOrder):
      Find studies whose tests cover the tube's sample type (or any sample type
      that shares the same st_sufix, since SamplesOrder may be created with one
      st_id while studies reference another st_id with the same suffix).
      If a single work group → one sticker with full group name.
      If multiple work groups share the same sample type → ONE merged sticker:
        work_group_name = first 5 chars of each group joined with "-" (e.g. QUIMI-ESPEC)
        tests_line      = all study codes from all groups combined.
"""
from collections import defaultdict
from datetime import date
from typing import List
import asyncio

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.samples.domain.models import SamplesOrder, SampleType
from app.domains.studieslab.domain.models import StudiesLab, StudiesTestDetail
from app.domains.masters.domain.models import WorkGroup
from app.domains.reports.infrastructure.printer_barcodes.barcode_generator import (
    build_stickers_result,
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

    # 5b. Build a mapping of st_sufix → all st_ids that share that suffix
    # This is needed because StudiesTestDetail references a specific samples_type_id (st_id),
    # but SamplesOrder may have been created with a different st_id that shares the same suffix.
    st_ids_in_tubes = {t.so_sample_type_id for t in tubes if t.so_sample_type_id}
    all_st_ids_in_db = set()
    for st_id in st_ids_in_tubes:
        all_st_ids_in_db.add(st_id)
    # Also collect any st_id referenced by studies
    for study in studies:
        for std in study.test_details:
            if std.test and std.test.samples_type_id is not None:
                all_st_ids_in_db.add(std.test.samples_type_id)

    # Load all SampleTypes involved to build suffix → [st_id] map
    st_suffix_map: dict[int, list[int]] = defaultdict(list)  # suffix → [st_id, ...]
    if all_st_ids_in_db:
        st_objects = await db.execute(
            select(SampleType).filter(SampleType.st_id.in_(all_st_ids_in_db))
        )
        for st_obj in st_objects.scalars().all():
            sfx = st_obj.st_sufix if st_obj.st_sufix is not None else st_obj.st_id
            st_suffix_map[sfx].append(st_obj.st_id)

    # 6. For each study, compute which sample type IDs it covers (from its tests)
    #    study_id → set of sample_type_ids (empty = all tube types)

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

        # Determine which sample types this study covers (only from tests with print_barcode enabled)
        covered_st_ids: set[int] = set()
        for std in study.test_details:
            if std.test and std.test.print_barcode and std.test.samples_type_id is not None:
                covered_st_ids.add(std.test.samples_type_id)

        # If no test has print_barcode enabled, skip this study entirely
        if not covered_st_ids:
            continue

        for st_id in covered_st_ids:
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
        delta_days = (today - dob).days

        if delta_days >= 365:
            # Adulto: calcular años cumplidos
            years = (
                today.year - dob.year
                - ((today.month, today.day) < (dob.month, dob.day))
            )
            age_str = f"{years} A"
        elif delta_days >= 30:
            # Meses cumplidos
            months = delta_days // 30
            age_str = f"{months} M"
        else:
            # Días de nacido
            age_str = f"{delta_days} D"

    # 8. Build sticker data list: one sticker per tube.
    #    If multiple work groups share the same sample type, they are merged into
    #    a single sticker with abbreviated names (max 5 chars each, joined with "-").
    stickers = []

    for tube in tubes:
        st: SampleType | None = tube.sample_type
        if not st:
            continue
        sample_type_name = (st.st_name or "").upper()
        sufix = st.st_sufix if st.st_sufix is not None else st.st_id
        barcode_value = f"{order.o_number}{sufix}"
        label_number = f"{order.o_number}-{sufix}"

        # Find ALL st_ids that share this suffix, so we can aggregate studies
        # from all sample types that map to the same physical tube
        related_st_ids = st_suffix_map.get(sufix, [st.st_id])

        # Collect work-group studies from ALL sample type IDs with this suffix
        combined_wg_studies: dict[int, list[str]] = defaultdict(list)
        for st_id in related_st_ids:
            wg_data = sample_wg_studies.get(st_id, {})
            for wg_id, codes in wg_data.items():
                for c in codes:
                    if c not in combined_wg_studies[wg_id]:
                        combined_wg_studies[wg_id].append(c)

        if not combined_wg_studies:
            # No studies with print_barcode enabled for this tube → skip sticker
            continue

        # Sort work groups by wg_order_of_print
        sorted_wg_ids = sorted(
            combined_wg_studies.keys(),
            key=lambda wid: (
                (wg_map[wid].wg_order_of_print or 999)
                if wid in wg_map else 999
            ),
        )

        if len(sorted_wg_ids) == 1:
            # Single work group → generate sticker with full name (no abbreviation)
            wg_id = sorted_wg_ids[0]
            wg: WorkGroup | None = wg_map.get(wg_id)
            wg_name = (wg.wg_name or "").upper() if wg else f"GRUPO {wg_id}"
            codes = combined_wg_studies[wg_id]
            tests_line = "-" + "-".join(codes)

            stickers.append({
                "patient_full_name": patient_full_name,
                "identification": identification,
                "enterprise_name": enterprise_name,
                "age_str": age_str,
                "work_group_name": wg_name,
                "barcode_value": barcode_value,
                "label_number": label_number,
                "tests_line": tests_line,
                "sample_type_name": sample_type_name,
            })
        else:
            # Multiple work groups share the same sample type → merge into one sticker.
            # Each work group name is truncated to 5 chars and joined with "-".
            wg_name_parts: list[str] = []
            all_codes: list[str] = []
            for wg_id in sorted_wg_ids:
                wg: WorkGroup | None = wg_map.get(wg_id)
                wg_full_name = (wg.wg_name or "").upper() if wg else f"GRP{wg_id}"
                wg_name_parts.append(wg_full_name[:5])
                all_codes.extend(combined_wg_studies[wg_id])

            combined_wg_name = "-".join(wg_name_parts)
            tests_line = "-" + "-".join(all_codes)

            stickers.append({
                "patient_full_name": patient_full_name,
                "identification": identification,
                "enterprise_name": enterprise_name,
                "age_str": age_str,
                "work_group_name": combined_wg_name,
                "barcode_value": barcode_value,
                "label_number": label_number,
                "tests_line": tests_line,
                "sample_type_name": sample_type_name,
            })

    if not stickers:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se pudieron generar stickers. Verifique que los estudios "
                   "tengan pruebas y tipos de muestra configurados.",
        )

    # 9. Build PDF via Labelary and return
    pdf_bytes, zpl_list = await asyncio.to_thread(build_stickers_result, stickers)
    b64 = pdf_to_base64(pdf_bytes)

    filename = f"stickers_{order.o_number}_{identification.replace(' ', '_')}.pdf"

    return {
        "filename": filename,
        "base64_pdf": b64,
        "order_number": order.o_number,
        "order_id": order_id,
        "total_stickers": len(stickers),
        "zpl_codes": zpl_list,
    }