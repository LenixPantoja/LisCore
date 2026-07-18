from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException, status
from app.domains.laboratories.infrastructure.repository import LaboratoryRepository
from app.domains.orders.domain.constants import (
    ORDER_DETAIL_STATES, ORDER_DETAIL_STATE_DESCARTADO,
)
from app.domains.orders.domain.order_state_logic import compute_order_state_from_studies
from app.domains.traces.constants import (
    OPERATION_EDIT_RESULT,
    OPERATION_VALIDATE_RESULT,
    OPERATION_INVALIDATE_RESULT,
    OPERATION_VALIDATE_PRELIMINARY,
    OPERATION_INVALIDATE_PRELIMINARY,
)
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

        # Extraer l_ids procesados para sincronizar estados de órdenes después
        processed_l_ids = [
            item["l_id"] for item in data_list
            if item.get("l_id") is not None
        ]

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

        # Sincronizar estados de las órdenes afectadas tras registrar resultados
        if updated_count > 0 and processed_l_ids:
            await _sync_order_states_for_labs(db, processed_l_ids)
        
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
    Después de validar, actualiza el o_order_state de las órdenes afectadas
    respetando is_required de StudiesTestDetail:
      - 4 (Validada) si para cada estudio de la orden, todas las pruebas
        con is_required=True están validadas (l_state in {3, 4}).
      - 3 (Con Resultados) si todas las pruebas requeridas tienen resultados
        (l_state in {2, 3, 4}) pero no todas están validadas.
      - 2 (Pendiente) si al menos un estudio tiene pruebas requeridas sin resultado.
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
    Revisa los estados de los laboratorios de cada orden afectada respetando is_required
    de StudiesTestDetail y actualiza o_order_state:
      - ORDER_STATE_VALIDADA (4) si para cada estudio de la orden, todas las pruebas
        con is_required=True están validadas (l_state in {3, 4}).
      - ORDER_STATE_CON_RESULTADOS (3) si todas las pruebas requeridas tienen
        resultados (l_state in {2, 3, 4}) pero no todas están validadas.
      - ORDER_STATE_PENDIENTE (2) si al menos un estudio tiene pruebas requeridas sin resultado.
    """
    from app.domains.laboratories.domain.models import Laboratory
    from app.domains.orders.domain.models import OrdersDetail, Order
    from app.domains.studieslab.domain.models import StudiesTestDetail

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
        # 2. Obtener todos los labs de la orden junto con su estudio y test
        stmt_labs = (
            select(
                Laboratory.l_state,
                OrdersDetail.od_study_id,
                Laboratory.l_test_id,
            )
            .join(OrdersDetail, Laboratory.l_order_detail_id == OrdersDetail.od_id)
            .where(OrdersDetail.od_order_id == order_id)
        )
        result_labs = await db.execute(stmt_labs)
        labs_data = result_labs.all()  # List of (l_state, od_study_id, l_test_id)

        if not labs_data:
            continue

        # 3. Obtener configuración is_required por estudio
        unique_study_ids = list({row.od_study_id for row in labs_data if row.od_study_id})
        required_tests_by_study: dict[int, set[int]] = {}
        if unique_study_ids:
            std_result = await db.execute(
                select(StudiesTestDetail).where(
                    StudiesTestDetail.studies_id.in_(unique_study_ids),
                    StudiesTestDetail.is_required == True,
                )
            )
            for std in std_result.scalars().all():
                required_tests_by_study.setdefault(std.studies_id, set()).add(std.tests_id)

        # 4. Agrupar labs por estudio: {study_id: {test_id: l_state}}
        study_labs: dict[int, dict[int, int]] = {}
        for row in labs_data:
            sid = row.od_study_id
            if sid not in study_labs:
                study_labs[sid] = {}
            if row.l_test_id is not None:
                study_labs[sid][row.l_test_id] = row.l_state

        # 5. Decidir el estado de la orden (Pendiente / Con Resultados / Validada)
        new_order_state = compute_order_state_from_studies(study_labs, required_tests_by_study)

        # 6. Actualizar la orden
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
    Si al menos un laboratorio es limpiado, actualiza el estado de la orden a Pendiente.
    """
    try:
        if not laboratory_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La lista de IDs de laboratorios no puede estar vacía."
            )
        
        cleared_count, details = await LaboratoryRepository.clear_laboratory_results(db, laboratory_ids)

        await db.commit()

        # Sincronizar estados de las órdenes afectadas tras limpiar resultados
        if cleared_count > 0:
            await _sync_order_states_for_labs(db, laboratory_ids)
        
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


async def upload_laboratory_graphic(
    db: AsyncSession,
    l_id: int,
    file_data: bytes,
    filename: str,
    content_type: str,
) -> dict:
    """
    Sube una imagen a MinIO y guarda el object_name en l_result_graphic del laboratorio.
    """
    from utils.minio_client import upload_graphic, build_graphic_object_name, get_graphic_url

    lab = await LaboratoryRepository.get_by_id(db, l_id)
    if lab is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratorio con l_id={l_id} no encontrado."
        )

    # Determinar la extensión desde el nombre del archivo
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"

    # Obtener order_number y test_code desde las relaciones del lab
    order_number = "NOORDER"
    test_code = "NOTEST"
    if lab.order_detail and getattr(lab.order_detail, "od_order_id", None):
        from app.domains.orders.domain.models import Order
        order = await db.get(Order, lab.order_detail.od_order_id)
        if order and order.o_number:
            order_number = order.o_number
    if lab.test and getattr(lab.test, "code", None):
        test_code = lab.test.code or "NOTEST"

    object_name = build_graphic_object_name(order_number, test_code, l_id, ext)

    try:
        upload_graphic(file_data, object_name, content_type)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al subir la imagen a MinIO: {exc}"
        )

    await LaboratoryRepository.update_graphic(db, l_id, object_name)

    return {
        "success": True,
        "l_id": l_id,
        "object_name": object_name,
        "url": get_graphic_url(object_name),
        "message": "Imagen subida y vinculada correctamente.",
    }


async def link_laboratory_graphic(
    db: AsyncSession,
    l_id: int,
    object_name: str,
) -> dict:
    """
    Vincula un object_name ya existente en MinIO al l_result_graphic del laboratorio.
    Usado por analizadores u otros sistemas que suben imágenes directamente a MinIO.
    """
    from utils.minio_client import get_graphic_url

    lab = await LaboratoryRepository.get_by_id(db, l_id)
    if lab is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratorio con l_id={l_id} no encontrado."
        )

    await LaboratoryRepository.update_graphic(db, l_id, object_name)

    return {
        "success": True,
        "l_id": l_id,
        "object_name": object_name,
        "url": get_graphic_url(object_name),
        "message": "Object name vinculado correctamente al laboratorio.",
    }


async def bulk_update_preliminaries(db: AsyncSession, items: List[dict], usr_id: int = None):
    """
    Valida múltiples resultados preliminares (lp_state = 1 / Validado).
    Cada item debe contener: l_id (laboratorio), lp_id (preliminar).
    Solo permite validar si el lp_state actual es 0 (Pendiente).
    Registra traza en AppTrace por cada preliminar validado.
    """
    try:
        if not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La lista de ítems no puede estar vacía."
            )

        validated_count, details, trace_data_list = await LaboratoryRepository.bulk_update_preliminaries(db, items)

        # Registrar trazas para cada preliminar validado
        for trace in trace_data_list:
            desc = f"Preliminar lp_id={trace['lp_id']} del laboratorio l_id={trace['l_id']}"
            if trace.get("lp_result"):
                desc += f" | resultado: {trace['lp_result']}"

            await register_trace(
                db=db,
                operation_type=OPERATION_VALIDATE_PRELIMINARY,
                operation_description=desc,
                usr_id=usr_id,
                order_id=trace["order_id"],
                test_id=trace["test_id"],
            )

        await db.commit()

        message_parts = [f"Se validaron {validated_count} resultados preliminares correctamente."]

        if details.get("not_found"):
            message_parts.append(f"{len(details['not_found'])} preliminares no fueron encontrados.")
        if details.get("invalid_state"):
            message_parts.append(f"{len(details['invalid_state'])} preliminares no estaban en estado Pendiente.")

        return {
            "success": True,
            "validated_count": validated_count,
            "failed_count": len(details.get("not_found", [])) + len(details.get("invalid_state", [])),
            "message": " ".join(message_parts),
            "details": details,
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al validar los preliminares: {str(e)}"
        )


async def invalidate_preliminaries(db: AsyncSession, items: List[dict], usr_id: int = None, note: str = None):
    """
    Desvalida múltiples resultados preliminares (lp_state = 2 / Desvalidado).
    Cada item debe contener: l_id (laboratorio), lp_id (preliminar).
    Solo permite desvalidar si el lp_state actual es 1 (Validado).
    Registra traza en AppTrace por cada preliminar desvalidado.
    """
    try:
        if not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La lista de ítems no puede estar vacía."
            )

        invalidated_count, details, trace_data_list = await LaboratoryRepository.invalidate_preliminaries(db, items)

        # Registrar trazas para cada preliminar desvalidado
        for trace in trace_data_list:
            desc = f"Preliminar lp_id={trace['lp_id']} del laboratorio l_id={trace['l_id']}"
            if trace.get("lp_result"):
                desc += f" | resultado: {trace['lp_result']}"
            notes = f"Nota: {note}" if note else None

            await register_trace(
                db=db,
                operation_type=OPERATION_INVALIDATE_PRELIMINARY,
                operation_description=desc,
                usr_id=usr_id,
                order_id=trace["order_id"],
                test_id=trace["test_id"],
                notes=notes,
            )

        await db.commit()

        message_parts = [f"Se desvalidaron {invalidated_count} resultados preliminares correctamente."]

        if details.get("not_found"):
            message_parts.append(f"{len(details['not_found'])} preliminares no fueron encontrados.")
        if details.get("invalid_state"):
            message_parts.append(f"{len(details['invalid_state'])} preliminares no estaban en estado Validado.")

        return {
            "success": True,
            "invalidated_count": invalidated_count,
            "failed_count": len(details.get("not_found", [])) + len(details.get("invalid_state", [])),
            "message": " ".join(message_parts),
            "details": details,
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al desvalidar los preliminares: {str(e)}"
        )
