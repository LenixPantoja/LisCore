from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.domains.laboratories.infrastructure.repository import LaboratoryRepository
from typing import List

async def bulk_update_laboratories(db: AsyncSession, data_list: List[dict]):
    """
    Actualiza múltiples laboratorios solo si su estado es < 2.
    Actualiza l_result, l_result_comp, l_nota_validation y l_user_validation_id de forma selectiva.
    Cuando se registra un resultado, automáticamente establece l_state a 1.
    """
    try:
        if not data_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La lista de laboratorios no puede estar vacía."
            )
        
        updated_count, details = await LaboratoryRepository.bulk_update(db, data_list)
        
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

async def invalidate_laboratories(db: AsyncSession, laboratory_ids: List[int]):
    """
    Desvalida laboratorios (cambia estado a 1) solo si su estado es >= 2.
    """
    try:
        if not laboratory_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La lista de IDs de laboratorios no puede estar vacía."
            )
        
        invalidated_count, details = await LaboratoryRepository.invalidate_laboratories(db, laboratory_ids)
        
        # Construir mensaje según resultados
        message_parts = [f"Se desvalidaron {invalidated_count} laboratorios correctamente."]
        
        if details.get("invalid_state"):
            message_parts.append(f"{len(details['invalid_state'])} laboratorios no fueron desvalidados porque su estado es < 2.")
        
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

async def validate_laboratories(db: AsyncSession, laboratory_ids: List[int]):
    """
    Valida laboratorios (cambia estado a 2).
    """
    try:
        if not laboratory_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La lista de IDs de laboratorios no puede estar vacía."
            )
        
        validated_count, details = await LaboratoryRepository.validate_laboratories(db, laboratory_ids)
        
        # Construir mensaje según resultados
        message_parts = [f"Se validaron {validated_count} laboratorios correctamente."]
        
        if details.get("not_found"):
            message_parts.append(f"{len(details['not_found'])} laboratorios no fueron encontrados.")
        
        return {
            "success": True,
            "validated_count": validated_count,
            "failed_count": len(details.get("not_found", [])),
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

async def clear_laboratory_results(db: AsyncSession, laboratory_ids: List[int]):
    """
    Limpia los resultados de laboratorios y establece el estado a 0, solo si l_state < 2.
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
