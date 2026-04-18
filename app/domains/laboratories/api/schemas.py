from pydantic import BaseModel
from typing import Optional, List

class LaboratoryBulkUpdateItem(BaseModel):
    l_id: int
    l_result: Optional[str] = None
    l_result_comp: Optional[str] = None
    l_nota_validation: Optional[str] = None
    l_user_validation_id: Optional[int] = None

class LaboratoryBulkUpdateResponse(BaseModel):
    success: bool
    updated_count: int
    message: str
    failed_count: int = 0
    details: dict = {}

class InvalidateLaboratoriesRequest(BaseModel):
    """Schema para desvalidar laboratorios"""
    laboratory_ids: List[int]

class InvalidateLaboratoriesResponse(BaseModel):
    """Respuesta de desvalidación de laboratorios"""
    success: bool
    invalidated_count: int
    failed_count: int
    message: str
    details: dict = {}

class ValidateLaboratoriesRequest(BaseModel):
    """Schema para validar laboratorios"""
    laboratory_ids: List[int]

class ValidateLaboratoriesResponse(BaseModel):
    """Respuesta de validación de laboratorios"""
    success: bool
    validated_count: int
    failed_count: int
    message: str
    details: dict = {}

class ClearLaboratoryResultsRequest(BaseModel):
    """Schema para limpiar resultados de laboratorios"""
    laboratory_ids: List[int]

class ClearLaboratoryResultsResponse(BaseModel):
    """Respuesta de limpieza de resultados de laboratorios"""
    success: bool
    cleared_count: int
    failed_count: int
    message: str
    details: dict = {}
