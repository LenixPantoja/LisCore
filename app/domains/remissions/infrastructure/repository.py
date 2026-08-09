from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.remissions.domain.models import (
    ExternalReferenceLaboratory,
    Remission,
    RemissionDetail,
    RemissionStatesLog,
)
from app.domains.remissions.domain.constants import (
    REMISSION_STATE_PENDING,
    REMISSION_STATE_SHIPPED,
    REMISSION_STATE_RECEIVED_OK,
    REMISSION_STATE_RECEIVED_WITH_NOVELTY,
    REMISSION_STATE_CANCELLED,
    DETAIL_ITEM_STATE_LOADED,
    DETAIL_ITEM_STATE_RECEIVED_OK,
    DETAIL_ITEM_STATE_REJECTED,
    ORDER_DETAIL_STATE_IN_TRANSIT,
    ORDER_DETAIL_STATE_REJECTED,
    ORDER_DETAIL_STATE_PENDING_RESAMPLE,
)
from app.domains.orders.domain.models import Order, OrdersDetail
from app.domains.samples.domain.models import SamplesOrder
from utils.timezone import get_bogota_now


# ──────────────────────────────────────────────
#  ExternalReferenceLaboratories Repository
# ──────────────────────────────────────────────

class ExternalLabRepository:

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> ExternalReferenceLaboratory:
        lab = ExternalReferenceLaboratory(**data)
        db.add(lab)
        await db.flush()
        await db.refresh(lab)
        await db.commit()
        return lab

    @staticmethod
    async def get_by_id(db: AsyncSession, erl_id: int) -> Optional[ExternalReferenceLaboratory]:
        return await db.get(ExternalReferenceLaboratory, erl_id)

    @staticmethod
    async def list_all(db: AsyncSession, active_only: bool = True) -> Sequence[ExternalReferenceLaboratory]:
        stmt = select(ExternalReferenceLaboratory)
        if active_only:
            stmt = stmt.where(ExternalReferenceLaboratory.erl_active == True)
        result = await db.execute(stmt.order_by(ExternalReferenceLaboratory.erl_name))
        return result.scalars().all()

    @staticmethod
    async def update(db: AsyncSession, erl_id: int, data: dict) -> Optional[ExternalReferenceLaboratory]:
        lab = await db.get(ExternalReferenceLaboratory, erl_id)
        if not lab:
            return None
        for key, value in data.items():
            setattr(lab, key, value)
        lab.erl_updated_at = get_bogota_now()
        await db.flush()
        await db.commit()
        await db.refresh(lab)
        return lab

    @staticmethod
    async def delete(db: AsyncSession, erl_id: int) -> Optional[ExternalReferenceLaboratory]:
        lab = await db.get(ExternalReferenceLaboratory, erl_id)
        if lab:
            await db.delete(lab)
            await db.commit()
        return lab


# ──────────────────────────────────────────────
#  Remissions Repository (Core Business Logic)
# ──────────────────────────────────────────────

class RemissionRepository:

    # ── Consecutive Generation ───────────────────────────────────────

    @staticmethod
    async def _generate_consecutive(
        db: AsyncSession, origin_headquarter_id: int
    ) -> str:
        """
        Genera un consecutivo con formato: REM-<AÑO>-<SEDE_ORIGEN_ID>-<SECUENCIAL>
        Ejemplo: REM-2026-1-0043
        """
        current_year = str(date.today().year)
        # Buscar el último consecutivo con el mismo prefijo REM-AÑO-SEDE-
        prefix = f"REM-{current_year}-{origin_headquarter_id}-"
        stmt = (
            select(Remission.rem_consecutive)
            .where(
                Remission.rem_origin_headquarter_id == origin_headquarter_id,
                Remission.rem_consecutive.like(f"REM-{current_year}-%"),
            )
            .order_by(Remission.rem_id.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        last_consecutive = result.scalar()

        if last_consecutive:
            try:
                seq_part = last_consecutive.split("-")[-1]
                next_seq = int(seq_part) + 1
            except (ValueError, IndexError):
                next_seq = 1
        else:
            next_seq = 1

        return f"{prefix}{next_seq:04d}"

    # ── State Logging (atomic audit) ─────────────────────────────────

    @staticmethod
    async def _log_state_change(
        db: AsyncSession,
        remission_id: int,
        state_before: Optional[int],
        state_after: int,
        user_id: int,
        notes: Optional[str] = None,
    ) -> None:
        log_entry = RemissionStatesLog(
            rsl_remission_id=remission_id,
            rsl_state_before=state_before,
            rsl_state_after=state_after,
            rsl_changed_by_user_id=user_id,
            rsl_notes=notes,
        )
        db.add(log_entry)
        await db.flush()

    # ── Validation helpers ───────────────────────────────────────────

    @staticmethod
    async def _validate_headquarter_exists(db: AsyncSession, hq_id: int) -> bool:
        from app.domains.Headquarters.domain.models import Headquarter
        hq = await db.get(Headquarter, hq_id)
        return hq is not None

    @staticmethod
    async def _validate_external_lab_exists(db: AsyncSession, erl_id: int) -> bool:
        lab = await db.get(ExternalReferenceLaboratory, erl_id)
        return lab is not None and lab.erl_active

    @staticmethod
    async def _validate_item_not_in_active_remission(
        db: AsyncSession,
        sample_order_id: int,
        order_detail_id: int,
        exclude_remission_id: Optional[int] = None,
    ) -> bool:
        """
        Verifica que el par (so_id, od_id) NO esté en otra remisión activa
        (estados Pendiente=1 o Enviado=2).
        Retorna True si está LIBRE, False si YA está en uso.
        """
        stmt = select(RemissionDetail).join(
            Remission, RemissionDetail.remd_remission_id == Remission.rem_id
        ).where(
            RemissionDetail.remd_sample_order_id == sample_order_id,
            RemissionDetail.remd_order_detail_id == order_detail_id,
            Remission.rem_state.in_([REMISSION_STATE_PENDING, REMISSION_STATE_SHIPPED]),
        )

        if exclude_remission_id is not None:
            stmt = stmt.where(Remission.rem_id != exclude_remission_id)

        result = await db.execute(stmt)
        existing = result.scalars().first()
        return existing is None  # True = libre, False = en uso

    # ── CRUD: Remission Header ───────────────────────────────────────

    @staticmethod
    async def create_remission(
        db: AsyncSession,
        rem_type: str,
        origin_headquarter_id: int,
        user_id: int,
        dest_headquarter_id: Optional[int] = None,
        dest_external_lab_id: Optional[int] = None,
        observations: Optional[str] = None,
    ) -> Tuple[Remission, Optional[str]]:
        """
        Crea una remisión en estado Pendiente.
        Retorna (Remission, error_message). error_message es None si todo ok.
        """
        # Validar regla de negocio: mutex de destinos
        if rem_type == "LOCAL":
            if dest_headquarter_id is None or dest_external_lab_id is not None:
                return None, "Para remisión LOCAL, rem_dest_headquarter_id es requerido y rem_dest_external_lab_id debe ser nulo."
            if not await RemissionRepository._validate_headquarter_exists(db, dest_headquarter_id):
                return None, f"Sede destino con ID {dest_headquarter_id} no encontrada."
            if dest_headquarter_id == origin_headquarter_id:
                return None, "La sede destino no puede ser la misma que la sede origen."
        elif rem_type == "EXTERNAL":
            if dest_external_lab_id is None or dest_headquarter_id is not None:
                return None, "Para remisión EXTERNAL, rem_dest_external_lab_id es requerido y rem_dest_headquarter_id debe ser nulo."
            if not await RemissionRepository._validate_external_lab_exists(db, dest_external_lab_id):
                return None, f"Laboratorio externo con ID {dest_external_lab_id} no encontrado o inactivo."
        else:
            return None, f"Tipo de remisión inválido: {rem_type}. Use 'LOCAL' o 'EXTERNAL'."

        # Validar sede origen
        if not await RemissionRepository._validate_headquarter_exists(db, origin_headquarter_id):
            return None, f"Sede origen con ID {origin_headquarter_id} no encontrada."

        # Generar consecutivo
        consecutive = await RemissionRepository._generate_consecutive(db, origin_headquarter_id)

        remission = Remission(
            rem_consecutive=consecutive,
            rem_type=rem_type,
            rem_origin_headquarter_id=origin_headquarter_id,
            rem_dest_headquarter_id=dest_headquarter_id,
            rem_dest_external_lab_id=dest_external_lab_id,
            rem_state=REMISSION_STATE_PENDING,
            rem_observations=observations,
            rem_created_by_user_id=user_id,
        )
        db.add(remission)
        await db.flush()

        # Registrar auditoría de creación
        await RemissionRepository._log_state_change(
            db, remission.rem_id, None, REMISSION_STATE_PENDING, user_id,
            notes="Creación de remisión",
        )

        await db.commit()
        await db.refresh(remission)
        return remission, None

    @staticmethod
    async def get_remission_by_id(
        db: AsyncSession, rem_id: int, load_details: bool = False
    ) -> Optional[Remission]:
        if load_details:
            from sqlalchemy.orm import joinedload
            stmt = (
                select(Remission)
                .where(Remission.rem_id == rem_id)
                .options(
                    selectinload(Remission.details)
                        .selectinload(RemissionDetail.sample_order)
                        .selectinload(SamplesOrder.order)
                        .selectinload(Order.patient),
                    selectinload(Remission.details)
                        .selectinload(RemissionDetail.sample_order)
                        .selectinload(SamplesOrder.sample_type),
                    selectinload(Remission.details)
                        .selectinload(RemissionDetail.order_detail)
                        .selectinload(OrdersDetail.study),
                    selectinload(Remission.state_logs),
                    selectinload(Remission.origin_headquarter),
                    selectinload(Remission.dest_headquarter),
                    selectinload(Remission.dest_external_lab),
                    selectinload(Remission.created_by_user),
                )
            )
            result = await db.execute(stmt)
            return result.scalars().first()
        return await db.get(Remission, rem_id)

    @staticmethod
    async def list_remissions(
        db: AsyncSession,
        state: Optional[int] = None,
        type_: Optional[str] = None,
        origin_hq_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Remission]:
        stmt = select(Remission).options(
            selectinload(Remission.origin_headquarter),
            selectinload(Remission.dest_headquarter),
            selectinload(Remission.dest_external_lab),
            selectinload(Remission.created_by_user),
        )
        if state is not None:
            stmt = stmt.where(Remission.rem_state == state)
        if type_ is not None:
            stmt = stmt.where(Remission.rem_type == type_)
        if origin_hq_id is not None:
            stmt = stmt.where(Remission.rem_origin_headquarter_id == origin_hq_id)
        stmt = stmt.order_by(Remission.rem_created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    # ── Items: Add / Remove ──────────────────────────────────────────

    @staticmethod
    async def add_items(
        db: AsyncSession,
        remission_id: int,
        items: List[Dict[str, int]],
        user_id: int,
    ) -> Tuple[Optional[List[RemissionDetail]], Optional[str]]:
        """
        Agrega un array de ítems (par de so_id y od_id) al detalle.
        Solo si la remisión está Pendiente.
        Retorna (details_created, error_message).
        """
        remission = await RemissionRepository.get_remission_by_id(db, remission_id)
        if not remission:
            return None, f"Remisión con ID {remission_id} no encontrada."
        if remission.rem_state != REMISSION_STATE_PENDING:
            return None, "Solo se pueden agregar ítems a remisiones en estado Pendiente."

        created = []
        for item in items:
            so_id = item.get("remd_sample_order_id")
            od_id = item.get("remd_order_detail_id")
            if so_id is None or od_id is None:
                return None, "Cada ítem debe incluir remd_sample_order_id y remd_order_detail_id."

            # Validar que el par no esté en otra remisión activa
            is_free = await RemissionRepository._validate_item_not_in_active_remission(db, so_id, od_id, exclude_remission_id=remission_id)
            if not is_free:
                return None, f"El ítem (so_id={so_id}, od_id={od_id}) ya está en otra remisión activa (Pendiente o Enviado)."

            detail = RemissionDetail(
                remd_remission_id=remission_id,
                remd_sample_order_id=so_id,
                remd_order_detail_id=od_id,
                remd_item_state=DETAIL_ITEM_STATE_LOADED,
            )
            db.add(detail)
            created.append(detail)

        await db.flush()
        if created:
            for d in created:
                await db.refresh(d)
        await db.commit()
        return created, None

    @staticmethod
    async def remove_item(
        db: AsyncSession, remission_id: int, detail_id: int, user_id: int
    ) -> Tuple[Optional[RemissionDetail], Optional[str]]:
        """
        Elimina un ítem del detalle. Solo si la remisión está Pendiente.
        """
        remission = await RemissionRepository.get_remission_by_id(db, remission_id)
        if not remission:
            return None, f"Remisión con ID {remission_id} no encontrada."
        if remission.rem_state != REMISSION_STATE_PENDING:
            return None, "Solo se pueden eliminar ítems de remisiones en estado Pendiente."

        detail = await db.get(RemissionDetail, detail_id)
        if not detail or detail.remd_remission_id != remission_id:
            return None, f"Ítem con ID {detail_id} no encontrado en la remisión {remission_id}."

        await db.delete(detail)
        await db.commit()
        return detail, None

    # ── Ship: Enviar Remisión ────────────────────────────────────────

    @staticmethod
    async def ship_remission(
        db: AsyncSession,
        remission_id: int,
        user_id: int,
        courier_name: Optional[str] = None,
        temperature_courier: Optional[str] = None,
    ) -> Tuple[Optional[Remission], Optional[str]]:
        """
        Cambia el estado a Enviado (2). Registra transportador y temperatura.
        Actualiza los OrdersDetails asociados a estado "En tránsito" (90).
        """
        remission = await RemissionRepository.get_remission_by_id(db, remission_id)
        if not remission:
            return None, f"Remisión con ID {remission_id} no encontrada."
        if remission.rem_state != REMISSION_STATE_PENDING:
            return None, "Solo se pueden enviar remisiones en estado Pendiente."

        # Verificar que tenga al menos un ítem
        details = await db.execute(
            select(RemissionDetail).where(RemissionDetail.remd_remission_id == remission_id)
        )
        if not details.scalars().first():
            return None, "La remisión no tiene ítems. Agregue al menos uno antes de enviar."

        # Registrar auditoría antes del cambio
        old_state = remission.rem_state
        await RemissionRepository._log_state_change(
            db, remission_id, old_state, REMISSION_STATE_SHIPPED, user_id,
            notes=f"Envío: {courier_name or 'N/A'} | Temp: {temperature_courier or 'N/A'}",
        )

        # Actualizar cabecera
        remission.rem_state = REMISSION_STATE_SHIPPED
        remission.rem_courier_name = courier_name
        remission.rem_temperature_courier = temperature_courier
        remission.rem_sent_at = get_bogota_now()

        # Actualizar todos los OrdersDetails de los ítems a estado "En Tránsito"
        detail_records = await db.execute(
            select(RemissionDetail).where(RemissionDetail.remd_remission_id == remission_id)
        )
        for detail in detail_records.scalars().all():
            await db.execute(
                update(OrdersDetail)
                .where(OrdersDetail.od_id == detail.remd_order_detail_id)
                .values(od_state=ORDER_DETAIL_STATE_IN_TRANSIT)
            )

        await db.flush()
        await db.commit()
        await db.refresh(remission)
        return remission, None

    # ── Receive Item: Recepción Unitaria ─────────────────────────────

    @staticmethod
    async def receive_item(
        db: AsyncSession,
        remission_id: int,
        detail_id: int,
        user_id: int,
        item_state: int,
        rejection_reason: Optional[str] = None,
    ) -> Tuple[Optional[RemissionDetail], Optional[str]]:
        """
        Procesa la recepción unitaria de un examen en el destino.
        Actualiza el estado del ítem y, si aplica, el estado de la cabecera.
        """
        remission = await RemissionRepository.get_remission_by_id(db, remission_id)
        if not remission:
            return None, f"Remisión con ID {remission_id} no encontrada."
        if remission.rem_state != REMISSION_STATE_SHIPPED:
            return None, "Solo se pueden recibir ítems de remisiones en estado Enviado."

        detail = await db.get(RemissionDetail, detail_id)
        if not detail or detail.remd_remission_id != remission_id:
            return None, f"Ítem con ID {detail_id} no encontrado en la remisión {remission_id}."

        if item_state not in (DETAIL_ITEM_STATE_RECEIVED_OK, DETAIL_ITEM_STATE_REJECTED):
            return None, f"Estado de ítem inválido: {item_state}. Use 2 (Recibido Conforme) o 3 (Rechazado)."

        if item_state == DETAIL_ITEM_STATE_REJECTED and not rejection_reason:
            return None, "Se requiere razón de rechazo cuando el ítem se marca como Rechazado."

        # Actualizar detalle
        detail.remd_item_state = item_state
        detail.remd_rejection_reason = rejection_reason if item_state == DETAIL_ITEM_STATE_REJECTED else None
        detail.remd_received_by_user_id = user_id
        detail.remd_updated_at = get_bogota_now()

        # Actualizar OrdersDetail según el estado del ítem
        if item_state == DETAIL_ITEM_STATE_REJECTED:
            # Revertir a "Pendiente Toma de Muestra" / "Muestra Rechazada"
            await db.execute(
                update(OrdersDetail)
                .where(OrdersDetail.od_id == detail.remd_order_detail_id)
                .values(od_state=ORDER_DETAIL_STATE_PENDING_RESAMPLE)
            )
        # Si es recibido conforme, el estado del OrdersDetail ya está en tránsito;
        # se puede mantener o cambiar según el flujo de laboratorio.

        await db.flush()

        # Reevaluar estado de la cabecera
        all_details = await db.execute(
            select(RemissionDetail).where(RemissionDetail.remd_remission_id == remission_id)
        )
        all_items = all_details.scalars().all()

        # Verificar si todos los ítems ya fueron procesados (estado != Cargado)
        pending_items = [d for d in all_items if d.remd_item_state == DETAIL_ITEM_STATE_LOADED]
        if not pending_items:
            # Todos procesados — determinar si hubo rechazos
            rejected_items = [d for d in all_items if d.remd_item_state == DETAIL_ITEM_STATE_REJECTED]
            new_header_state = (
                REMISSION_STATE_RECEIVED_WITH_NOVELTY if rejected_items else REMISSION_STATE_RECEIVED_OK
            )

            old_header_state = remission.rem_state
            remission.rem_state = new_header_state
            remission.rem_received_at = get_bogota_now()

            await RemissionRepository._log_state_change(
                db, remission_id, old_header_state, new_header_state, user_id,
                notes=f"Cierre automático — {len(rejected_items)} ítems rechazados" if rejected_items else "Cierre automático — todos conformes",
            )

        await db.flush()
        await db.commit()
        await db.refresh(detail)
        return detail, None

    # ── Orders con estudios remitidos ────────────────────────────────

    @staticmethod
    async def list_orders_with_remitted_studies(
        db: AsyncSession,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        has_annexed_results: Optional[bool] = None,
        external_lab_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Lista (paginado) las órdenes que tienen al menos un estudio configurado
        como remitido a un laboratorio de referencia externo real
        (StudiesLab.external_lab_id, excluyendo el centinela 'LOCAL'). Busca
        directamente en OrdersDetail → StudiesLab, sin depender de
        Remissions/RemissionDetails.

        Cada orden trae sus estudios remitidos anidados en "estudios_remitidos".
        El estado de anexo (ar_file_status) es específico por laboratorio: se
        calcula comparando contra AnnexedResult.ar_external_lab_id, no contra
        la orden completa — así, cargar el PDF de un laboratorio no afecta el
        estado de un estudio remitido a otro laboratorio distinto.

        Retorna (orders, total) — total es la cantidad de órdenes (no de filas).
        """
        from app.domains.annexes.domain.models import AnnexedResult
        from app.domains.studieslab.domain.models import StudiesLab
        from app.domains.patients.domain.models import Patient
        from sqlalchemy import case

        # ── 1. IDs de órdenes que cumplen los filtros (paginado a nivel de orden) ──
        id_stmt = (
            select(Order.o_id)
            .select_from(OrdersDetail)
            .join(StudiesLab, StudiesLab.id == OrdersDetail.od_study_id)
            .join(Order, Order.o_id == OrdersDetail.od_order_id)
            .where(
                StudiesLab.external_lab_id.isnot(None),
                StudiesLab.external_lab_id != 1,
            )
            .distinct()
        )
        if external_lab_id is not None:
            id_stmt = id_stmt.where(StudiesLab.external_lab_id == external_lab_id)
        if date_from is not None:
            id_stmt = id_stmt.where(Order.o_date >= date_from)
        if date_to is not None:
            id_stmt = id_stmt.where(Order.o_date <= date_to)

        if has_annexed_results is not None:
            # Existencia de CUALQUIER anexo con archivo para la orden (sin filtrar por
            # laboratorio): coincide con los anexos antiguos, subidos antes de que
            # existiera ar_external_lab_id, que quedaron con ese campo en NULL.
            ann_sub = select(AnnexedResult.ar_order_id).where(
                AnnexedResult.ar_file.isnot(None), AnnexedResult.ar_file != ""
            )
            if has_annexed_results is True:
                id_stmt = id_stmt.where(Order.o_id.in_(ann_sub))
            else:
                id_stmt = id_stmt.where(~Order.o_id.in_(ann_sub))

        count_stmt = select(func.count()).select_from(id_stmt.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        paged_stmt = id_stmt.order_by(Order.o_id.asc()).offset(skip).limit(limit)
        order_ids = [row[0] for row in (await db.execute(paged_stmt)).all()]

        if not order_ids:
            return [], total

        # ── 2. Cabeceras de orden + paciente ──
        headers_stmt = (
            select(
                Order.o_id,
                Order.o_number,
                Order.o_created_at.label("fecha_ingreso"),
                func.concat_ws(
                    " ",
                    Patient.pt_firts_name,
                    Patient.pt_middle_name,
                    Patient.pt_last_name,
                    Patient.pt_second_last_name,
                ).label("patient_full_name"),
                Patient.pt_Number_document.label("pt_number_document"),
            )
            .select_from(Order)
            .join(Patient, Patient.pt_id == Order.o_his_id)
            .where(Order.o_id.in_(order_ids))
        )
        headers_by_id = {r.o_id: r for r in (await db.execute(headers_stmt)).all()}

        # ── 3. Estudios remitidos (hijos), con estado de anexo por laboratorio ──
        ar_file_status = case(
            (or_(AnnexedResult.ar_file.is_(None), AnnexedResult.ar_file == ""), "Sin resultado Anexo"),
            else_="Cargado",
        ).label("ar_file_status")

        studies_stmt = (
            select(
                OrdersDetail.od_order_id,
                OrdersDetail.od_id.label("order_detail_id"),
                StudiesLab.code.label("study_code"),
                StudiesLab.name.label("study_name"),
                StudiesLab.external_lab_id,
                ExternalReferenceLaboratory.erl_name.label("external_lab_name"),
                ar_file_status,
            )
            .distinct()
            .select_from(OrdersDetail)
            .join(StudiesLab, StudiesLab.id == OrdersDetail.od_study_id)
            .join(ExternalReferenceLaboratory, ExternalReferenceLaboratory.erl_id == StudiesLab.external_lab_id)
            .outerjoin(
                AnnexedResult,
                and_(
                    AnnexedResult.ar_order_id == OrdersDetail.od_order_id,
                    AnnexedResult.ar_external_lab_id == StudiesLab.external_lab_id,
                ),
            )
            .where(
                OrdersDetail.od_order_id.in_(order_ids),
                StudiesLab.external_lab_id.isnot(None),
                StudiesLab.external_lab_id != 1,
            )
        )
        if external_lab_id is not None:
            studies_stmt = studies_stmt.where(StudiesLab.external_lab_id == external_lab_id)

        studies_by_order: Dict[int, List[Dict[str, Any]]] = {}
        seen_details: set = set()
        for r in (await db.execute(studies_stmt)).all():
            if r.order_detail_id in seen_details:
                continue
            seen_details.add(r.order_detail_id)
            studies_by_order.setdefault(r.od_order_id, []).append({
                "order_detail_id": r.order_detail_id,
                "study_code": r.study_code,
                "study_name": r.study_name,
                "external_lab_id": r.external_lab_id,
                "external_lab_name": r.external_lab_name,
                "ar_file_status": r.ar_file_status,
            })

        items = []
        for oid in order_ids:
            h = headers_by_id.get(oid)
            if not h:
                continue
            items.append({
                "o_id": h.o_id,
                "o_number": h.o_number,
                "fecha_ingreso": h.fecha_ingreso,
                "patient_full_name": h.patient_full_name,
                "pt_number_document": h.pt_number_document,
                "estudios_remitidos": studies_by_order.get(oid, []),
            })

        return items, total

    @staticmethod
    async def get_remitted_order_detail_ids(
        db: AsyncSession, order_id: int, external_lab_id: Optional[int] = None
    ) -> List[int]:
        """
        Retorna los od_id de los OrdersDetails de una orden cuyo estudio está
        configurado como remitido a un laboratorio de referencia externo real
        (excluye el centinela 'LOCAL'). Si se indica external_lab_id, solo
        retorna los od_id remitidos a ESE laboratorio específico.
        """
        from app.domains.studieslab.domain.models import StudiesLab

        stmt = (
            select(OrdersDetail.od_id)
            .join(StudiesLab, StudiesLab.id == OrdersDetail.od_study_id)
            .where(
                OrdersDetail.od_order_id == order_id,
                StudiesLab.external_lab_id.isnot(None),
                StudiesLab.external_lab_id != 1,
            )
            .distinct()
        )
        if external_lab_id is not None:
            stmt = stmt.where(StudiesLab.external_lab_id == external_lab_id)
        result = await db.execute(stmt)
        return [row[0] for row in result.all()]

    @staticmethod
    async def mark_remitted_labs_as_annexed(
        db: AsyncSession, order_detail_ids: List[int]
    ) -> Tuple[List[int], List[int]]:
        """
        Escribe l_result = 'PDF ANEXO' y l_state = Con Resultados (2) en todas
        las Laboratories asociadas a los OrdersDetails remitidos indicados,
        siempre que su estado actual sea menor a Validada (3).

        Retorna (ids_actualizados, ids_omitidos_por_ya_validados).
        """
        from app.domains.laboratories.domain.models import Laboratory
        from app.domains.laboratories.domain.constants import (
            LABORATORY_STATE_CON_RESULTADOS,
            LABORATORY_STATE_VALIDADA,
        )

        if not order_detail_ids:
            return [], []

        labs_result = await db.execute(
            select(Laboratory).where(Laboratory.l_order_detail_id.in_(order_detail_ids))
        )
        labs = labs_result.scalars().all()

        updated_ids: List[int] = []
        skipped_ids: List[int] = []
        for lab in labs:
            if lab.l_state >= LABORATORY_STATE_VALIDADA:
                skipped_ids.append(lab.l_id)
                continue
            lab.l_result = "PDF ANEXO"
            lab.l_result_num = None
            lab.l_state = LABORATORY_STATE_CON_RESULTADOS
            updated_ids.append(lab.l_id)

        await db.flush()
        return updated_ids, skipped_ids

    # ── Cancel: Cancelar Remisión ─────────────────────────────────────

    @staticmethod
    async def cancel_remission(
        db: AsyncSession,
        remission_id: int,
        user_id: int,
        notes: Optional[str] = None,
    ) -> Tuple[Optional[Remission], Optional[str]]:
        """
        Cancela la remisión. Solo permitido si está en estado Pendiente.
        """
        remission = await RemissionRepository.get_remission_by_id(db, remission_id)
        if not remission:
            return None, f"Remisión con ID {remission_id} no encontrada."
        if remission.rem_state != REMISSION_STATE_PENDING:
            return None, "Solo se pueden cancelar remisiones en estado Pendiente."

        old_state = remission.rem_state
        remission.rem_state = REMISSION_STATE_CANCELLED

        await RemissionRepository._log_state_change(
            db, remission_id, old_state, REMISSION_STATE_CANCELLED, user_id,
            notes=notes or "Remisión cancelada",
        )

        await db.flush()
        await db.commit()
        await db.refresh(remission)
        return remission, None