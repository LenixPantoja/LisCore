from typing import List, Optional

from pydantic import BaseModel


class BarcodeStickerRequest(BaseModel):
    order_id: int
    study_ids: Optional[List[int]] = None


class BarcodeStickerResponse(BaseModel):
    filename: str
    base64_pdf: str
    order_number: str
    order_id: int
    total_stickers: int
    zpl_codes: List[str]
