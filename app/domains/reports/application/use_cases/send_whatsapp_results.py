import base64

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.reports.application.use_cases.report_use_cases import generate_laboratory_report
from app.integrations.whatsapp.client import whatsapp_client


async def execute(db: AsyncSession, order_id: int, phone_number: str) -> dict:
    """
    Generates the laboratory PDF for the given order and sends it
    to the provided phone number via WhatsApp (Evolution API).
    """
    report = await generate_laboratory_report(db, order_id)

    pdf_bytes = base64.b64decode(report["base64_pdf"])
    filename = report["filename"]
    order_number = report["order_number"]
    patient_name = report["patient_name"]

    greeting = (
        f"Hola *{patient_name}* 👋\n\n"
        f"Adjuntamos el resultado de su orden *{order_number}*.\n\n"
        "Ante cualquier consulta, no dude en contactarnos. 🩺"
    )

    try:
        await whatsapp_client.send_text(phone_number, greeting)
        await whatsapp_client.send_pdf(
            phone_number=phone_number,
            pdf_bytes=pdf_bytes,
            filename=filename,
            caption=f"Resultados orden {order_number}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al enviar el mensaje por WhatsApp: {exc}",
        )

    return {
        "order_number": order_number,
        "patient_name": patient_name,
        "phone_number": phone_number,
        "message": "Resultados enviados correctamente por WhatsApp.",
    }
