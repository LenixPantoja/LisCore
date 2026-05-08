from pydantic import BaseModel


class POSTicketRequest(BaseModel):
    order_id: int


class POSTicketResponse(BaseModel):
    filename: str
    base64_pdf: str
    order_number: str
    order_id: int
