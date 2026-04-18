from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select
from app.domains.laboratories.domain.models import Laboratory
from typing import List, Dict, Any, Tuple

class LaboratoryRepository:
    @staticmethod
    async def bulk_update(db: AsyncSession, updates: List[Dict[str, Any]]) -> Tuple[int, Dict[str, List[int]]]:
        """
        Actualiza múltiples laboratorios solo si su estado es < 2.
        Cuando se actualiza el resultado, automáticamente establece l_state a 1.
        
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
            
            # Validar que el estado sea < 2
            if lab.l_state >= 2:
                invalid_state_ids.append(l_id)
                continue
            
            # Si hay resultado a registrar, agregar estado a 1
            if any(key in item for key in ["l_result", "l_result_comp", "l_result_num"]):
                item["l_state"] = 1
                
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
        Desvalida laboratorios (cambia estado a 1) solo si su estado actual es >= 2.
        
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
            
            # Validar que el estado sea >= 2
            if lab.l_state < 2:
                invalid_state_ids.append(l_id)
                continue
            
            # Actualizar el estado a 1 (desvalidado)
            stmt = (
                update(Laboratory)
                .where(Laboratory.l_id == l_id)
                .values(l_state=1)
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
    async def validate_laboratories(db: AsyncSession, laboratory_ids: List[int]) -> Tuple[int, Dict[str, List[int]]]:
        """
        Valida laboratorios (cambia estado a 2).
        
        Retorna:
            - Cantidad de laboratorios validados exitosamente
            - Diccionario con detalles de laboratorios que no se pudieron validar
        """
        if not laboratory_ids:
            return 0, {"not_found": []}
        
        validated_count = 0
        not_found_ids = []
        
        for l_id in laboratory_ids:
            # Obtener el laboratorio
            stmt = select(Laboratory).where(Laboratory.l_id == l_id)
            result = await db.execute(stmt)
            lab = result.scalar_one_or_none()
            
            if lab is None:
                not_found_ids.append(l_id)
                continue
            
            # Actualizar el estado a 2 (validado)
            stmt = (
                update(Laboratory)
                .where(Laboratory.l_id == l_id)
                .values(l_state=2)
            )
            await db.execute(stmt)
            validated_count += 1
        
        await db.commit()
        
        details = {}
        if not_found_ids:
            details["not_found"] = not_found_ids
        
        return validated_count, details

    @staticmethod
    async def clear_laboratory_results(db: AsyncSession, laboratory_ids: List[int]) -> Tuple[int, Dict[str, List[int]]]:
        """
        Limpia los resultados de laboratorios y establece el estado a 0, solo si su estado es < 2.
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
            
            # Validar que el estado sea < 2
            if lab.l_state >= 2:
                invalid_state_ids.append(l_id)
                continue
            
            # Limpiar los resultados y establecer estado a 0
            stmt = (
                update(Laboratory)
                .where(Laboratory.l_id == l_id)
                .values(l_result=None, l_result_num=None, l_result_comp=None, l_state=0)
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
