from pydantic import BaseModel


class LaboratoryReportRequest(BaseModel):
    order_id: int


class LaboratoryReportResponse(BaseModel):
    filename: str
    base64_pdf: str
    order_number: str
    patient_name: str
