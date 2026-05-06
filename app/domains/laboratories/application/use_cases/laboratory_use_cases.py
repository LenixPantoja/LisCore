from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException, status
from app.domains.laboratories.infrastructure.repository import LaboratoryRepository
from app.domains.orders.domain.constants import (
    ORDER_DETAIL_STATES, ORDER_DETAIL_STATE_DESCARTADO,
    ORDER_STATE_PENDIENTE, ORDER_STATE_CON_RESULTADOS,
)
from app.domains.laboratories.domain.constants import LABORATORY_STATE_VALIDADA
from app.domains.traces.constants import OPERATION_EDIT_RESULT, OPERATION_VALIDATE_RESULT, OPERATION_INVALIDATE_RESULT
from utils.trace import register_trace
from typing import List

async def bulk_update_laboratories(db: AsyncSession, data_list: List[dict]):
    """
    Actualiza múltiples laboratorios solo si su estado es < 2.
    Actualiza l_result, l_result_comp, l_nota_validation y l_user_validation_id de forma selectiva.
    Cuando se registra un resultado, automáticamente establece l_state a 2 (Con Resultados).
    """
    try:
        if not data_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La lista de laboratorios no puede estar vacía."
            )
        
        updated_count, details, trace_data_list = await LaboratoryRepository.bulk_update(db, data_list)

        # Registrar trazas para cada resultado editado
        for trace in trace_data_list:
            notes_parts = []
            if trace["old_result"] is not None:
                notes_parts.append(f"res anterior: {trace['old_result']}")
            if trace["old_result_comp"] is not None:
                notes_parts.append(f"res_comp anterior: {trace['old_result_comp']}")

            desc_parts = []
            if trace["new_result"] is not None:
                desc_parts.append(f"res: {trace['new_result']}")
            if trace["new_result_comp"] is not None:
                desc_parts.append(f"res_comp: {trace['new_result_comp']}")

            await register_trace(
                db=db,
                operation_type=OPERATION_EDIT_RESULT,
                operation_description="Edición de Resultado - " + ", ".join(desc_parts) if desc_parts else "Edición de Resultado",
                usr_id=trace["usr_id"],
                order_id=trace["order_id"],
                test_id=trace["test_id"],
                notes="; ".join(notes_parts) if notes_parts else None,
            )

        await db.commit()
        
        # Construir mensaje según resultados
        message_parts = [f"Se actualizaron {updated_count} registros de laboratorio exitosamente. Los laboratorios con resultados registrados ahora tienen estado = 1."]
        
        if details.get("invalid_state"):
            message_parts.append(f"{len(details['invalid_state'])} laboratorios no fueron actualizados porque su estado es >= 2.")
        
        if details.get("not_found"):
            message_parts.append(f"{len(details['not_found'])} laboratorios no fueron encontrados.")
        
        return {
            "success": True,
            "updated_count": updated_count,
            "message": " ".join(message_parts),
            "failed_count": len(details.get("invalid_state", [])) + len(details.get("not_found", [])),
            "details": details
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar los laboratorios: {str(e)}"
        )

async def invalidate_laboratories(db: AsyncSession, laboratory_ids: List[int], usr_id: int, note: str = None):
    """
    Desvalida laboratorios (cambia estado a 2/Con Resultados) solo si su estado es >= 3.
    Si al menos un laboratorio es desvalidado, actualiza el estado de la orden a 2 (Pendiente).
    """
    try:
        if not laboratory_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La lista de IDs de laboratorios no puede estar vacía."
            )
        
        invalidated_count, details, trace_data_list = await LaboratoryRepository.invalidate_laboratories(db, laboratory_ids)

        # Registrar trazas para cada laboratorio desvalidado
        for trace in trace_data_list:
            notes_parts = []
            if trace["current_result"] is not None:
                notes_parts.append(f"l_result: {trace['current_result']}")
            if trace["current_result_comp"] is not None:
                notes_parts.append(f"l_result_comp: {trace['current_result_comp']}")
            if note:
                notes_parts.append(f"Nota: {note}")

            await register_trace(
                db=db,
                operation_type=OPERATION_INVALIDATE_RESULT,
                operation_description="Invalidación de Resultado",
                usr_id=usr_id,
                order_id=trace["order_id"],
                test_id=trace["test_id"],
                notes="; ".join(notes_parts) if notes_parts else None,
            )

        await db.commit()

        # Si al menos uno fue desvalidado, actualizar la(s) orden(es) a Pendiente
        if invalidated_count > 0:
            await _sync_order_states_for_labs(db, laboratory_ids)
        
        # Construir mensaje según resultados
        message_parts = [f"Se desvalidaron {invalidated_count} laboratorios correctamente."]
        
        if details.get("invalid_state"):
            message_parts.append(f"{len(details['invalid_state'])} laboratorios no fueron desvalidados porque su estado es < 3.")
        
        if details.get("not_found"):
            message_parts.append(f"{len(details['not_found'])} laboratorios no fueron encontrados.")
        
        return {
            "success": True,
            "invalidated_count": invalidated_count,
            "failed_count": len(details.get("invalid_state", [])) + len(details.get("not_found", [])),
            "message": " ".join(message_parts),
            "details": details
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al desvalidar los laboratorios: {str(e)}"
        )

async def validate_laboratories(db: AsyncSession, items: list):
    """
    Valida laboratorios por ítem:
    - Si el ítem trae l_result o l_result_comp: registra los campos y valida (l_state = 3 / Validada).
    - Si solo trae l_nota_validation: guarda la nota sin cambiar el estado.
    - Si no trae ninguno: omite el ítem.
    Después de validar, actualiza el o_order_state de las órdenes afectadas:
      - 3 (Con Resultados) si todos los laboratorios de la orden están validados.
      - 2 (Pendiente) si al menos uno no está validado.
    """
    try:
        if not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La lista de ítems no puede estar vacía."
            )

        # Guardar l_ids antes de que el repositorio los procese
        l_ids = [item["l_id"] for item in items]

        validated_count, details, trace_data_list = await LaboratoryRepository.validate_laboratories(db, items)

        # Registrar trazas para cada laboratorio validado
        for trace in trace_data_list:
            notes_parts = []
            if trace["old_result"] is not None:
                notes_parts.append(f"res anterior: {trace['old_result']}")
            if trace["old_result_comp"] is not None:
                notes_parts.append(f"res_comp anterior: {trace['old_result_comp']}")

            desc_parts = []
            if trace["new_result"] is not None:
                desc_parts.append(f"res: {trace['new_result']}")
            if trace["new_result_comp"] is not None:
                desc_parts.append(f"res_comp: {trace['new_result_comp']}")

            await register_trace(
                db=db,
                operation_type=OPERATION_VALIDATE_RESULT,
                operation_description="Validación de Resultado - " + ", ".join(desc_parts) if desc_parts else "Validación de Resultado",
                usr_id=trace["usr_id"],
                order_id=trace["order_id"],
                test_id=trace["test_id"],
                
            )

        await db.commit()

        # Actualizar estado de la(s) orden(es) afectada(s)
        if validated_count > 0:
            await _sync_order_states_for_labs(db, l_ids)

        # Construir mensaje según resultados
        message_parts = [f"Se validaron {validated_count} laboratorios correctamente."]

        if details.get("not_found"):
            message_parts.append(f"{len(details['not_found'])} laboratorios no fueron encontrados.")

        if details.get("skipped"):
            message_parts.append(f"{len(details['skipped'])} ítems omitidos por no tener resultado ni nota.")

        if details.get("invalid_state"):
            message_parts.append(f"{len(details['invalid_state'])} laboratorios no tenían estado 'Con Resultados' y no fueron validados.")

        return {
            "success": True,
            "validated_count": validated_count,
            "failed_count": len(details.get("not_found", [])) + len(details.get("invalid_state", [])),
            "message": " ".join(message_parts),
            "details": details
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al validar los laboratorios: {str(e)}"
        )


async def _sync_order_states_for_labs(db: AsyncSession, l_ids: List[int]):
    """
    Revisa los estados de todos los laboratorios de cada orden afectada por los l_ids dados
    y actualiza o_order_state:
      - ORDER_STATE_CON_RESULTADOS (3) si todos los labs de la orden están en l_state = 3.
      - ORDER_STATE_PENDIENTE (2) si al menos uno no está validado.
    """
    from app.domains.laboratories.domain.models import Laboratory
    from app.domains.orders.domain.models import OrdersDetail, Order

    # 1. Obtener order_ids de los labs procesados
    stmt = (
        select(OrdersDetail.od_order_id)
        .join(Laboratory, Laboratory.l_order_detail_id == OrdersDetail.od_id)
        .where(Laboratory.l_id.in_(l_ids))
        .distinct()
    )
    result = await db.execute(stmt)
    order_ids = [row[0] for row in result.fetchall()]

    for order_id in order_ids:
        # 2. Obtener todos los labs de la orden
        stmt_labs = (
            select(Laboratory.l_state)
            .join(OrdersDetail, Laboratory.l_order_detail_id == OrdersDetail.od_id)
            .where(OrdersDetail.od_order_id == order_id)
        )
        result_labs = await db.execute(stmt_labs)
        lab_states = [row[0] for row in result_labs.fetchall()]

        if not lab_states:
            continue

        # 3. Decidir el nuevo estado de la orden
        all_validated = all(s == LABORATORY_STATE_VALIDADA for s in lab_states)
        new_order_state = ORDER_STATE_CON_RESULTADOS if all_validated else ORDER_STATE_PENDIENTE

        # 4. Actualizar la orden
        stmt_order = (
            update(Order)
            .where(Order.o_id == order_id)
            .values(o_order_state=new_order_state)
        )
        await db.execute(stmt_order)

    await db.commit()

async def clear_laboratory_results(db: AsyncSession, laboratory_ids: List[int]):
    """
    Limpia los resultados de laboratorios y establece el estado a 0 (Sin Resultados), solo si l_state < 3.
    """
    try:
        if not laboratory_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La lista de IDs de laboratorios no puede estar vacía."
            )
        
        cleared_count, details = await LaboratoryRepository.clear_laboratory_results(db, laboratory_ids)
        
        # Construir mensaje según resultados
        message_parts = [f"Se limpiaron {cleared_count} laboratorios correctamente y sus estados fueron establecidos a 0."]
        
        if details.get("invalid_state"):
            message_parts.append(f"{len(details['invalid_state'])} laboratorios no fueron limpios porque su estado es >= 2.")
        
        if details.get("not_found"):
            message_parts.append(f"{len(details['not_found'])} laboratorios no fueron encontrados.")
        
        return {
            "success": True,
            "cleared_count": cleared_count,
            "failed_count": len(details.get("invalid_state", [])) + len(details.get("not_found", [])),
            "message": " ".join(message_parts),
            "details": details
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al limpiar los resultados de laboratorios: {str(e)}"
        )


_ORDER_DETAIL_STATE_NAMES = ORDER_DETAIL_STATES
_VALID_ORDER_DETAIL_STATES = set(_ORDER_DETAIL_STATE_NAMES.keys())


async def update_order_detail_state(db: AsyncSession, order_id: int, study_id: int, new_state: int):
    """
    Cambia el estado (od_state) de un estudio en OrdersDetails.

    Estados válidos:
        0 → Normal
        1 → Pendiente
        2 → Anulado
    """
    if new_state not in _VALID_ORDER_DETAIL_STATES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado inválido '{new_state}'. Estados permitidos: 0 (Ingresado), 1 (Pendiente), 2 (Descartado)."
        )

    detail = await LaboratoryRepository.update_order_detail_state(db, order_id, study_id, new_state)

    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el estudio con study_id={study_id} en la orden order_id={order_id}."
        )
    if detail == "DISCARDED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El estudio con study_id={study_id} fue descartado y no puede cambiar de estado."
        )
    return {
        "success": True,
        "od_id": detail.od_id,
        "od_order_id": detail.od_order_id,
        "od_study_id": detail.od_study_id,
        "od_state": detail.od_state,
        "state_name": _ORDER_DETAIL_STATE_NAMES[detail.od_state],
        "message": f"Estado del estudio actualizado a '{_ORDER_DETAIL_STATE_NAMES[new_state]}'."
    }
