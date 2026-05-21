from decimal import Decimal, InvalidOperation
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select
from app.domains.laboratories.domain.models import Laboratory
from utils.timezone import get_bogota_now
from app.domains.testslabs.domain.models import TestsLab
from app.domains.orders.domain.models import OrdersDetail
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
    async def bulk_update(db: AsyncSession, updates: List[Dict[str, Any]]) -> Tuple[int, Dict[str, List[int]], List[Dict[str, Any]]]:
        """
        Actualiza múltiples laboratorios solo si su estado es < 3 (no validado).
        Cuando se actualiza el resultado, automáticamente establece l_state a 2 (Con Resultados).
        
        Retorna:
            - Cantidad de laboratorios actualizados exitosamente
            - Diccionario con detalles de laboratorios que no se pudieron actualizar
            - Lista de datos de traza por cada laboratorio con resultado actualizado
        """
        if not updates:
            return 0, {"not_found": [], "invalid_state": []}, []
            
        updated_count = 0
        invalid_state_ids = []
        not_found_ids = []
        trace_data_list: List[Dict[str, Any]] = []
        
        for item in updates:
            l_id = item.pop("l_id")
            usr_id = item.pop("l_user_validation_id", None)
            # If no items to update besides l_id, skip
            if not item:
                continue
            
            # Obtener el laboratorio junto con el order_id desde OrdersDetail
            stmt = (
                select(Laboratory, OrdersDetail.od_order_id)
                .join(OrdersDetail, Laboratory.l_order_detail_id == OrdersDetail.od_id)
                .where(Laboratory.l_id == l_id)
            )
            result = await db.execute(stmt)
            row = result.one_or_none()

            if row is None:
                not_found_ids.append(l_id)
                continue

            lab, order_id = row
            
            # Validar que el estado sea < 3 (no validado ni impreso)
            if lab.l_state >= LABORATORY_STATE_VALIDADA:
                invalid_state_ids.append(l_id)
                continue

            # Capturar resultado anterior antes de aplicar cambios
            old_result = lab.l_result
            old_result_comp = lab.l_result_comp

            # Si hay resultado a registrar, establecer estado a 2 (Con Resultados)
            if any(key in item for key in ["l_result", "l_result_comp", "l_result_num"]):
                item["l_state"] = LABORATORY_STATE_CON_RESULTADOS

            # Si viene l_result y el test es de tipo Numérico (N), poblar también l_result_num
            if "l_result" in item and item["l_result"] is not None and lab.l_test_id:
                # Obtener test_type y num_decimal_result del TestsLab asociado
                test_stmt = select(TestsLab.test_type, TestsLab.num_decimal_result).where(TestsLab.id == lab.l_test_id)
                test_result = await db.execute(test_stmt)
                test_row = test_result.one_or_none()
                if test_row and test_row.test_type == "N":
                    try:
                        raw_value = Decimal(str(item["l_result"]).replace(",", "."))
                        decimals = test_row.num_decimal_result
                        if decimals is not None:
                            raw_value = round(raw_value, decimals)
                            item["l_result"] = f"{raw_value:.{decimals}f}"
                        item["l_result_num"] = raw_value
                    except (ValueError, TypeError, InvalidOperation):
                        item["l_result_num"] = None
                
            stmt = (
                update(Laboratory)
                .where(Laboratory.l_id == l_id)
                .values(**item)
            )
            await db.execute(stmt)
            updated_count += 1

            # Registrar datos para la traza si se actualizó algún resultado
            new_result = item.get("l_result")
            new_result_comp = item.get("l_result_comp")
            if new_result is not None or new_result_comp is not None:
                trace_data_list.append({
                    "usr_id": usr_id,
                    "order_id": order_id,
                    "test_id": lab.l_test_id,
                    "old_result": old_result,
                    "old_result_comp": old_result_comp,
                    "new_result": new_result,
                    "new_result_comp": new_result_comp,
                })
            
        # Recalculate formula-based labs for all orders that had results updated
        affected_order_ids = list({t["order_id"] for t in trace_data_list if t.get("order_id")})
        if affected_order_ids:
            await db.flush()
            formula_updated = await LaboratoryRepository._recalculate_formula_labs(db, affected_order_ids)
            updated_count += formula_updated

        await db.commit()
        
        details = {}
        if invalid_state_ids:
            details["invalid_state"] = invalid_state_ids
        if not_found_ids:
            details["not_found"] = not_found_ids
        
        return updated_count, details, trace_data_list

    @staticmethod
    async def _recalculate_formula_labs(db: AsyncSession, order_ids: List[int]) -> int:
        """
        Recomputes result for every formula-based lab in the given orders.

        For each order, fetches all labs together with their test info,
        builds the variable mapping from non-formula results, and evaluates
        each formula. Skips validated/printed labs and labs whose variables
        are not yet available (e.g., a dependency is still pending).

        Returns:
            Number of formula labs updated.
        """
        from utils.formula_processor import process_formula_for_test, FormulaMissingVariableError
        from utils.formula_engine import FormulaError

        updated = 0

        for order_id in order_ids:
            # Fetch all labs in the order with their test metadata
            stmt = (
                select(
                    Laboratory.l_id,
                    Laboratory.l_result_num,
                    Laboratory.l_result,
                    Laboratory.l_state,
                    TestsLab.name_abbreviation,
                    TestsLab.is_formula,
                    TestsLab.formula,
                    TestsLab.num_decimal_result,
                    TestsLab.test_type,
                )
                .join(TestsLab, Laboratory.l_test_id == TestsLab.id)
                .join(OrdersDetail, Laboratory.l_order_detail_id == OrdersDetail.od_id)
                .where(OrdersDetail.od_order_id == order_id)
            )
            rows = (await db.execute(stmt)).all()

            # Build variables from non-formula labs that have a numeric result
            available_results = [
                {
                    "name_abbreviation": row.name_abbreviation,
                    "result_value": row.l_result_num if row.l_result_num is not None else row.l_result,
                }
                for row in rows
                if not row.is_formula and row.name_abbreviation
            ]

            # Evaluate and persist each formula lab
            for row in rows:
                if not row.is_formula or not row.formula:
                    continue
                # Do not overwrite already validated/printed results
                if row.l_state >= LABORATORY_STATE_VALIDADA:
                    continue

                try:
                    computed = process_formula_for_test(
                        row.formula,
                        available_results,
                        num_decimal_result=row.num_decimal_result,
                    )
                except (FormulaMissingVariableError, FormulaError):
                    # Variables not yet available — leave this lab unchanged
                    continue

                if row.num_decimal_result is not None:
                    result_str = f"{computed:.{row.num_decimal_result}f}"
                else:
                    result_str = str(computed)

                await db.execute(
                    update(Laboratory)
                    .where(Laboratory.l_id == row.l_id)
                    .values(
                        l_result=result_str,
                        l_result_num=computed,
                        l_state=LABORATORY_STATE_CON_RESULTADOS,
                    )
                )
                updated += 1

        return updated

    @staticmethod
    async def invalidate_laboratories(db: AsyncSession, laboratory_ids: List[int]) -> Tuple[int, Dict[str, List[int]], List[Dict[str, Any]]]:
        """
        Desvalida laboratorios (cambia estado a 2/Con Resultados) solo si su estado actual es >= 3 (Validada).
        
        Retorna:
            - Cantidad de laboratorios desvalidados exitosamente
            - Diccionario con detalles de laboratorios que no se pudieron desvalidar
            - Lista de datos de traza por cada laboratorio desvalidado exitosamente
        """
        if not laboratory_ids:
            return 0, {"not_found": [], "invalid_state": []}, []
        
        invalidated_count = 0
        invalid_state_ids = []
        not_found_ids = []
        trace_data_list: List[Dict[str, Any]] = []
        
        for l_id in laboratory_ids:
            # Obtener el laboratorio junto con el order_id desde OrdersDetail
            stmt = (
                select(Laboratory, OrdersDetail.od_order_id)
                .join(OrdersDetail, Laboratory.l_order_detail_id == OrdersDetail.od_id)
                .where(Laboratory.l_id == l_id)
            )
            result = await db.execute(stmt)
            row = result.one_or_none()

            if row is None:
                not_found_ids.append(l_id)
                continue

            lab, order_id = row
            
            # Validar que el estado sea >= 3 (Validada o Impreso)
            if lab.l_state < LABORATORY_STATE_VALIDADA:
                invalid_state_ids.append(l_id)
                continue

            # Capturar resultado actual (que se va a desvalidar)
            trace_data_list.append({
                "order_id": order_id,
                "test_id": lab.l_test_id,
                "current_result": lab.l_result,
                "current_result_comp": lab.l_result_comp,
            })
            
            # Actualizar el estado a 2 (Con Resultados — desvalidado)
            update_stmt = (
                update(Laboratory)
                .where(Laboratory.l_id == l_id)
                .values(l_state=LABORATORY_STATE_CON_RESULTADOS)
            )
            await db.execute(update_stmt)
            invalidated_count += 1
        
        await db.commit()
        
        details = {}
        if invalid_state_ids:
            details["invalid_state"] = invalid_state_ids
        if not_found_ids:
            details["not_found"] = not_found_ids
        
        return invalidated_count, details, trace_data_list

    @staticmethod
    async def validate_laboratories(db: AsyncSession, items: List[Dict[str, Any]]) -> Tuple[int, Dict[str, List[int]], List[Dict[str, Any]]]:
        """
        Valida laboratorios por ítem.
        Solo valida si el l_state actual es 2 (Con Resultados).
        - Si el ítem trae l_result o l_result_comp: registra los campos y valida (l_state = 3 Validada).
        - Si solo trae l_nota_validation: guarda la nota sin cambiar el estado.
        - Si no trae ninguno: omite el ítem.

        Retorna:
            - Cantidad de laboratorios validados exitosamente
            - Diccionario con detalles de laboratorios que no se pudieron procesar
            - Lista de datos de traza por cada laboratorio validado exitosamente
        """
        if not items:
            return 0, {"not_found": [], "skipped": []}, []

        validated_count = 0
        not_found_ids = []
        skipped_ids = []
        invalid_state_ids = []
        trace_data_list: List[Dict[str, Any]] = []

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

            # Obtener el laboratorio junto con el order_id desde OrdersDetail
            stmt = (
                select(Laboratory, OrdersDetail.od_order_id)
                .join(OrdersDetail, Laboratory.l_order_detail_id == OrdersDetail.od_id)
                .where(Laboratory.l_id == l_id)
            )
            result = await db.execute(stmt)
            row = result.one_or_none()

            if row is None:
                not_found_ids.append(l_id)
                continue

            lab, order_id = row

            if force_validate or has_result:
                # Solo se puede validar si el estado actual es 2 (Con Resultados)
                if lab.l_state != LABORATORY_STATE_CON_RESULTADOS:
                    invalid_state_ids.append(l_id)
                    continue

                # Capturar resultado anterior antes de actualizar
                old_result = lab.l_result
                old_result_comp = lab.l_result_comp

                # Registrar campos provistos y validar (l_state = 3 Validada)
                fields: Dict[str, Any] = {
                    "l_state": LABORATORY_STATE_VALIDADA,
                    "l_date_validatie": get_bogota_now(),
                }
                for key in ("l_result", "l_result_comp", "l_nota_validation", "l_user_validation_id"):
                    if key in item and item[key] is not None:
                        fields[key] = item[key]
                update_stmt = update(Laboratory).where(Laboratory.l_id == l_id).values(**fields)
                await db.execute(update_stmt)
                validated_count += 1

                # Datos de traza para este laboratorio
                trace_data_list.append({
                    "usr_id": item.get("l_user_validation_id"),
                    "order_id": order_id,
                    "test_id": lab.l_test_id,
                    "old_result": old_result,
                    "old_result_comp": old_result_comp,
                    "new_result": item.get("l_result"),
                    "new_result_comp": item.get("l_result_comp"),
                })
            else:
                # Solo nota: guardar únicamente la nota sin modificar el estado
                update_stmt = update(Laboratory).where(Laboratory.l_id == l_id).values(
                    l_nota_validation=item["l_nota_validation"]
                )
                await db.execute(update_stmt)

        await db.commit()

        details: Dict[str, List[int]] = {}
        if not_found_ids:
            details["not_found"] = not_found_ids
        if skipped_ids:
            details["skipped"] = skipped_ids
        if invalid_state_ids:
            details["invalid_state"] = invalid_state_ids

        return validated_count, details, trace_data_list

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

    @staticmethod
    async def get_by_id(db: AsyncSession, l_id: int):
        """Retorna un Laboratory por su l_id, o None si no existe."""
        result = await db.execute(select(Laboratory).where(Laboratory.l_id == l_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update_graphic(db: AsyncSession, l_id: int, object_name: str):
        """Actualiza l_result_graphic de un laboratorio con el object_name de MinIO."""
        stmt = (
            update(Laboratory)
            .where(Laboratory.l_id == l_id)
            .values(l_result_graphic=object_name)
        )
        await db.execute(stmt)
        await db.commit()
