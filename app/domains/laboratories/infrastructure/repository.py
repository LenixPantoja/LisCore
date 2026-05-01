from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select
from app.domains.laboratories.domain.models import Laboratory
from app.domains.testslabs.domain.models import TestsLab
from app.domains.laboratories.domain.constants import (
    LABORATORY_STATE_SIN_RESULTADOS,
    LABORATORY_STATE_PENDIENTE,
    LABORATORY_STATE_CON_RESULTADOS,
    LABORATORY_STATE_VALIDADA,
    LABORATORY_STATE_DESCARTADO,
)
from app.domains.orders.domain.constants import (
    ORDER_DETAIL_STATE_INGRESADO,
    ORDER_DETAIL_STATE_PENDIENTE,
    ORDER_DETAIL_STATE_DESCARTADO,
)
from typing import List, Dict, Any, Tuple

class LaboratoryRepository:
    @staticmethod
    async def bulk_update(db: AsyncSession, updates: List[Dict[str, Any]]) -> Tuple[int, Dict[str, List[int]]]:
        """
        Actualiza múltiples laboratorios solo si su estado es < 3 (no validado).
        Cuando se actualiza el resultado, automáticamente establece l_state a 2 (Con Resultados).
        
        Retorna:
            - Cantidad de laboratorios actualizados exitosamente
            - Diccionario con detalles de laboratorios que no se pudieron actualizar
        """
        if not updates:
            return 0, {"not_found": [], "invalid_state": []}
            
        updated_count = 0
        invalid_state_ids = []
        not_found_ids = []
        
        for item in updates:
            l_id = item.pop("l_id")
            # If no items to update besides l_id, skip
            if not item:
                continue
            
            # Obtener el laboratorio
            stmt = select(Laboratory).where(Laboratory.l_id == l_id)
            result = await db.execute(stmt)
            lab = result.scalar_one_or_none()
            
            if lab is None:
                not_found_ids.append(l_id)
                continue
            
            # Validar que el estado sea < 3 (no validado ni impreso)
            if lab.l_state >= LABORATORY_STATE_VALIDADA:
                invalid_state_ids.append(l_id)
                continue
            
            # Si hay resultado a registrar, establecer estado a 2 (Con Resultados)
            if any(key in item for key in ["l_result", "l_result_comp", "l_result_num"]):
                item["l_state"] = LABORATORY_STATE_CON_RESULTADOS

            # Si viene l_result y el test es de tipo Numérico (N), poblar también l_result_num
            if "l_result" in item and item["l_result"] is not None and lab.l_test_id:
                # Obtener test_type del TestsLab asociado
                test_stmt = select(TestsLab.test_type).where(TestsLab.id == lab.l_test_id)
                test_result = await db.execute(test_stmt)
                test_type = test_result.scalar_one_or_none()
                if test_type == "N":
                    try:
                        item["l_result_num"] = float(str(item["l_result"]).replace(",", "."))
                    except (ValueError, TypeError):
                        item["l_result_num"] = None
                
            stmt = (
                update(Laboratory)
                .where(Laboratory.l_id == l_id)
                .values(**item)
            )
            await db.execute(stmt)
            updated_count += 1
            
        await db.commit()
        
        details = {}
        if invalid_state_ids:
            details["invalid_state"] = invalid_state_ids
        if not_found_ids:
            details["not_found"] = not_found_ids
        
        return updated_count, details

    @staticmethod
    async def invalidate_laboratories(db: AsyncSession, laboratory_ids: List[int]) -> Tuple[int, Dict[str, List[int]]]:
        """
        Desvalida laboratorios (cambia estado a 2/Con Resultados) solo si su estado actual es >= 3 (Validada).
        
        Retorna:
            - Cantidad de laboratorios desvalidados exitosamente
            - Diccionario con detalles de laboratorios que no se pudieron desvalidar
        """
        if not laboratory_ids:
            return 0, {"not_found": [], "invalid_state": []}
        
        invalidated_count = 0
        invalid_state_ids = []
        not_found_ids = []
        
        for l_id in laboratory_ids:
            # Obtener el laboratorio
            stmt = select(Laboratory).where(Laboratory.l_id == l_id)
            result = await db.execute(stmt)
            lab = result.scalar_one_or_none()
            
            if lab is None:
                not_found_ids.append(l_id)
                continue
            
            # Validar que el estado sea >= 3 (Validada o Impreso)
            if lab.l_state < LABORATORY_STATE_VALIDADA:
                invalid_state_ids.append(l_id)
                continue
            
            # Actualizar el estado a 2 (Con Resultados — desvalidado)
            stmt = (
                update(Laboratory)
                .where(Laboratory.l_id == l_id)
                .values(l_state=LABORATORY_STATE_CON_RESULTADOS)
            )
            await db.execute(stmt)
            invalidated_count += 1
        
        await db.commit()
        
        details = {}
        if invalid_state_ids:
            details["invalid_state"] = invalid_state_ids
        if not_found_ids:
            details["not_found"] = not_found_ids
        
        return invalidated_count, details

    @staticmethod
    async def validate_laboratories(db: AsyncSession, items: List[Dict[str, Any]]) -> Tuple[int, Dict[str, List[int]]]:
        """
        Valida laboratorios por ítem.
        Solo valida si el l_state actual es 2 (Con Resultados).
        - Si el ítem trae l_result o l_result_comp: registra los campos y valida (l_state = 3 Validada).
        - Si solo trae l_nota_validation: guarda la nota sin cambiar el estado.
        - Si no trae ninguno: omite el ítem.

        Retorna:
            - Cantidad de laboratorios validados exitosamente
            - Diccionario con detalles de laboratorios que no se pudieron procesar
        """
        if not items:
            return 0, {"not_found": [], "skipped": []}

        validated_count = 0
        not_found_ids = []
        skipped_ids = []
        invalid_state_ids = []

        for item in items:
            l_id = item.get("l_id")
            has_result = ("l_result" in item and item["l_result"] is not None) or \
                         ("l_result_comp" in item and item["l_result_comp"] is not None)
            has_note = "l_nota_validation" in item and item["l_nota_validation"] is not None
            force_validate = item.pop("validate_unconditionally", False)

            # Sin resultado, sin nota y sin forzado: omitir
            if not force_validate and not has_result and not has_note:
                skipped_ids.append(l_id)
                continue

            # Obtener el laboratorio
            stmt = select(Laboratory).where(Laboratory.l_id == l_id)
            result = await db.execute(stmt)
            lab = result.scalar_one_or_none()

            if lab is None:
                not_found_ids.append(l_id)
                continue

            if force_validate or has_result:
                # Solo se puede validar si el estado actual es 2 (Con Resultados)
                if lab.l_state != LABORATORY_STATE_CON_RESULTADOS:
                    invalid_state_ids.append(l_id)
                    continue

                # Registrar campos provistos y validar (l_state = 3 Validada)
                fields: Dict[str, Any] = {"l_state": LABORATORY_STATE_VALIDADA}
                for key in ("l_result", "l_result_comp", "l_nota_validation", "l_user_validation_id"):
                    if key in item and item[key] is not None:
                        fields[key] = item[key]
                stmt = update(Laboratory).where(Laboratory.l_id == l_id).values(**fields)
                await db.execute(stmt)
                validated_count += 1
            else:
                # Solo nota: guardar únicamente la nota sin modificar el estado
                stmt = update(Laboratory).where(Laboratory.l_id == l_id).values(
                    l_nota_validation=item["l_nota_validation"]
                )
                await db.execute(stmt)

        await db.commit()

        details: Dict[str, List[int]] = {}
        if not_found_ids:
            details["not_found"] = not_found_ids
        if skipped_ids:
            details["skipped"] = skipped_ids
        if invalid_state_ids:
            details["invalid_state"] = invalid_state_ids

        return validated_count, details

    @staticmethod
    async def clear_laboratory_results(db: AsyncSession, laboratory_ids: List[int]) -> Tuple[int, Dict[str, List[int]]]:
        """
        Limpia los resultados de laboratorios y establece el estado a 0 (Sin Resultados), solo si su estado es < 3 (no validado).
        Establece l_result, l_result_num y l_result_comp a None/NULL y l_state a 0.
        
        Retorna:
            - Cantidad de laboratorios limpios exitosamente
            - Diccionario con detalles de laboratorios que no se pudieron limpiar
        """
        if not laboratory_ids:
            return 0, {"not_found": [], "invalid_state": []}
        
        cleared_count = 0
        invalid_state_ids = []
        not_found_ids = []
        
        for l_id in laboratory_ids:
            # Obtener el laboratorio
            stmt = select(Laboratory).where(Laboratory.l_id == l_id)
            result = await db.execute(stmt)
            lab = result.scalar_one_or_none()
            
            if lab is None:
                not_found_ids.append(l_id)
                continue
            
            # Validar que el estado sea < 3 (no validado ni impreso)
            if lab.l_state >= LABORATORY_STATE_VALIDADA:
                invalid_state_ids.append(l_id)
                continue
            
            # Limpiar los resultados y establecer estado a 0 (Sin Resultados)
            stmt = (
                update(Laboratory)
                .where(Laboratory.l_id == l_id)
                .values(l_result=None, l_result_num=None, l_result_comp=None, l_state=LABORATORY_STATE_SIN_RESULTADOS)
            )
            await db.execute(stmt)
            cleared_count += 1
        
        await db.commit()
        
        details = {}
        if invalid_state_ids:
            details["invalid_state"] = invalid_state_ids
        if not_found_ids:
            details["not_found"] = not_found_ids
        
        return cleared_count, details

    @staticmethod
    async def update_order_detail_state(db: AsyncSession, order_id: int, study_id: int, new_state: int):
        """
        Cambia el estado (od_state) de un estudio en OrdersDetails.
        Busca por od_order_id y od_study_id.

        Cuando new_state == 0 (Ingresado), actualiza también los laboratorios asociados
        a l_state = 1 (Pendiente).

        Estados válidos:
            0 → Ingresado
            1 → Pendiente
            2 → Descartado

        Retorna el registro actualizado o None si no existe.
        """
        from app.domains.orders.domain.models import OrdersDetail

        stmt = select(OrdersDetail).where(
            OrdersDetail.od_order_id == order_id,
            OrdersDetail.od_study_id == study_id
        )
        result = await db.execute(stmt)
        detail = result.scalar_one_or_none()

        if detail is None:
            return None

        if detail.od_state == ORDER_DETAIL_STATE_DESCARTADO:
            return "DISCARDED"

        stmt = (
            update(OrdersDetail)
            .where(
                OrdersDetail.od_order_id == order_id,
                OrdersDetail.od_study_id == study_id
            )
            .values(od_state=new_state)
        )
        await db.execute(stmt)

        # Mapear el nuevo od_state al l_state correspondiente para los laboratorios asociados
        lab_state_map = {
            ORDER_DETAIL_STATE_INGRESADO: LABORATORY_STATE_SIN_RESULTADOS,   # 0 → 0 Sin Resultados
            ORDER_DETAIL_STATE_PENDIENTE: LABORATORY_STATE_PENDIENTE,         # 1 → 1 Pendiente
            ORDER_DETAIL_STATE_DESCARTADO: LABORATORY_STATE_DESCARTADO,       # 2 → 5 Descartado
        }

        if new_state in lab_state_map:
            stmt_labs = (
                update(Laboratory)
                .where(Laboratory.l_order_detail_id == detail.od_id)
                .values(l_state=lab_state_map[new_state])
            )
            await db.execute(stmt_labs)

        await db.commit()
        await db.refresh(detail)
        return detail
