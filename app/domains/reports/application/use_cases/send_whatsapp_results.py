import base64

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.orders.domain.models import Order
from app.domains.orders.domain.constants import ORDER_STATE_CON_RESULTADOS, ORDER_STATE_IMPRESA
from app.domains.reports.application.use_cases.report_use_cases import generate_laboratory_report
from app.domains.traces.constants import OPERATION_SEND_RESULT_WHATSAPP
from app.integrations.whatsapp.client import whatsapp_client
from utils.trace import register_trace


async def execute(db: AsyncSession, order_id: int, phone_number: str) -> dict:
    """
    Validates the order state, generates the laboratory PDF and sends it
    to the provided phone number via WhatsApp (Evolution API).
    Registers a trace on success.
    """
    order_result = await db.execute(
        select(Order).filter(Order.o_id == order_id)
    )
    order = order_result.scalars().first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden con ID {order_id} no encontrada.",
        )

    if not (ORDER_STATE_CON_RESULTADOS <= order.o_order_state <= ORDER_STATE_IMPRESA):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"No es posible enviar resultados. El estado de la orden es {order.o_order_state}. "
                "Solo se permite enviar órdenes con estado 'Con Resultados' (3), 'Validada' (4) o 'Impresa' (5)."
            ),
        )

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

    await register_trace(
        db=db,
        operation_type=OPERATION_SEND_RESULT_WHATSAPP,
        operation_description=f"Resultado de la orden {order_number} enviado por WhatsApp al número {phone_number}.",
        order_id=order_id,
    )
    await db.commit()

    return {
        "order_number": order_number,
        "patient_name": patient_name,
        "phone_number": phone_number,
        "message": "Resultados enviados correctamente por WhatsApp.",
    }
