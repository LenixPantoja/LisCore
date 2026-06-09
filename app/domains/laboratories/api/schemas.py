from pydantic import BaseModel, model_validator
from typing import Optional, List, Any
from datetime import datetime


class PreliminaryInput(BaseModel):
    """Resultado preliminar individual."""
    lp_result: Optional[str] = None


class LaboratoryBulkUpdateItem(BaseModel):
    l_id: int
    l_result: Optional[str] = None
    l_result_comp: Optional[Any] = None
    l_nota_validation: Optional[str] = None
    l_user_validation_id: Optional[int] = None
    preliminaries: Optional[List[PreliminaryInput]] = None

class LaboratoryBulkUpdateResponse(BaseModel):
    success: bool
    updated_count: int
    message: str
    failed_count: int = 0
    details: dict = {}

class InvalidateLaboratoriesRequest(BaseModel):
    """Schema para desvalidar laboratorios"""
    laboratory_ids: List[int]
    usr_id: int
    note: Optional[str] = None

class InvalidateLaboratoriesResponse(BaseModel):
    """Respuesta de desvalidación de laboratorios"""
    success: bool
    invalidated_count: int
    failed_count: int
    message: str
    details: dict = {}

class ValidateLaboratoryItem(BaseModel):
    l_id: int
    l_result: Optional[str] = None
    l_result_comp: Optional[str] = None
    l_nota_validation: Optional[str] = None
    l_user_validation_id: Optional[int] = None
    validate_unconditionally: bool = False  # True cuando se usa el formato legado laboratory_ids

class ValidateLaboratoriesRequest(BaseModel):
    """Schema para validar laboratorios.

    Acepta dos formatos:
    - Nuevo: `{ "items": [{ "l_id": 1, "l_result": "Negativo" }] }` — permite registrar resultados.
    - Legado: `{ "laboratory_ids": [1, 2, 3] }` — valida directamente sin registrar resultado.
    """
    items: Optional[List[ValidateLaboratoryItem]] = None
    laboratory_ids: Optional[List[int]] = None

    @model_validator(mode='after')
    def normalize_to_items(self) -> 'ValidateLaboratoriesRequest':
        if self.items is None and self.laboratory_ids is not None:
            # Formato legado: convertir IDs a items con validación incondicional
            self.items = [
                ValidateLaboratoryItem(l_id=lid, validate_unconditionally=True)
                for lid in self.laboratory_ids
            ]
        if not self.items:
            raise ValueError("Debe proporcionar 'items' o 'laboratory_ids'.")
        return self

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


class UpdateOrderDetailStateRequest(BaseModel):
    """Schema para cambiar el estado de un estudio en OrdersDetails"""
    state: int  # 0: Normal, 1: Pendiente, 2: Anulado


class UpdateOrderDetailStateResponse(BaseModel):
    """Respuesta del cambio de estado de estudio"""
    success: bool
    od_id: int
    od_order_id: int
    od_study_id: int
    od_state: int
    state_name: str
    message: str


class GraphicLinkRequest(BaseModel):
    """Vincula un object_name ya existente en MinIO al l_result_graphic del laboratorio."""
    object_name: str


class GraphicUploadResponse(BaseModel):
    """Respuesta tras subir o vincular una imagen gráfica."""
    success: bool
    l_id: int
    object_name: str
    url: Optional[str] = None
    message: str
