from typing import List

from pydantic import BaseModel


class BarcodeStickerRequest(BaseModel):
    order_id: int


class BarcodeStickerResponse(BaseModel):
    filename: str
    base64_pdf: str
    order_number: str
    order_id: int
    total_stickers: int
    zpl_codes: List[str]
