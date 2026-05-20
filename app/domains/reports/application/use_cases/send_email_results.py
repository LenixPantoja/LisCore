import base64

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.reports.application.use_cases.report_use_cases import generate_laboratory_report
from app.integrations.email.client import gmail_client


def _build_email_body(patient_name: str, order_number: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
      <title>Resultados de Laboratorio</title>
    </head>
    <body style="margin:0;padding:0;background-color:#f4f6f9;font-family:Arial,Helvetica,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f6f9;padding:40px 0;">
        <tr>
          <td align="center">
            <table width="600" cellpadding="0" cellspacing="0"
                   style="background-color:#ffffff;border-radius:8px;
                          box-shadow:0 2px 8px rgba(0,0,0,0.08);overflow:hidden;">

              <!-- Header -->
              <tr>
                <td style="background-color:#1a6fa8;padding:32px 40px;text-align:center;">
                  <h1 style="margin:0;color:#ffffff;font-size:22px;letter-spacing:0.5px;">
                    🧪 Laboratorio Clínico
                  </h1>
                  <p style="margin:6px 0 0;color:#cce4f5;font-size:13px;">
                    Resultados de Laboratorio
                  </p>
                </td>
              </tr>

              <!-- Body -->
              <tr>
                <td style="padding:36px 40px;">
                  <p style="margin:0 0 16px;font-size:16px;color:#333;">
                    Estimado/a <strong>{patient_name}</strong>,
                  </p>
                  <p style="margin:0 0 24px;font-size:15px;color:#555;line-height:1.6;">
                    Nos complace informarle que los resultados de su orden de laboratorio
                    ya se encuentran disponibles y han sido adjuntados a este correo en
                    formato PDF.
                  </p>

                  <!-- Order card -->
                  <table width="100%" cellpadding="0" cellspacing="0"
                         style="background-color:#f0f7ff;border-left:4px solid #1a6fa8;
                                border-radius:4px;padding:0;margin-bottom:28px;">
                    <tr>
                      <td style="padding:16px 20px;">
                        <p style="margin:0;font-size:13px;color:#888;text-transform:uppercase;
                                  letter-spacing:0.5px;">Número de Orden</p>
                        <p style="margin:4px 0 0;font-size:20px;font-weight:bold;color:#1a6fa8;">
                          {order_number}
                        </p>
                      </td>
                    </tr>
                  </table>

                  <p style="margin:0 0 16px;font-size:15px;color:#555;line-height:1.6;">
                    Por favor, abra el archivo adjunto para consultar sus resultados.
                    Si tiene alguna duda o requiere orientación médica, no dude en
                    contactarnos.
                  </p>

                  <p style="margin:0;font-size:15px;color:#555;line-height:1.6;">
                    Gracias por confiar en nuestros servicios. 🙏
                  </p>
                </td>
              </tr>

              <!-- Divider -->
              <tr>
                <td style="padding:0 40px;">
                  <hr style="border:none;border-top:1px solid #e8edf2;margin:0;"/>
                </td>
              </tr>

              <!-- Footer -->
              <tr>
                <td style="padding:20px 40px;text-align:center;">
                  <p style="margin:0;font-size:12px;color:#aaa;">
                    Este correo fue generado automáticamente. Por favor no responda
                    directamente a este mensaje.
                  </p>
                  <p style="margin:8px 0 0;font-size:12px;color:#aaa;">
                    © 2026 Laboratorio Clínico · Todos los derechos reservados
                  </p>
                </td>
              </tr>

            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """


async def execute(db: AsyncSession, order_id: int, email: str) -> dict:
    """
    Generates the laboratory PDF for the given order and sends it
    to the provided email address via Gmail SMTP.
    """
    report = await generate_laboratory_report(db, order_id)

    pdf_bytes = base64.b64decode(report["base64_pdf"])
    filename = report["filename"]
    order_number = report["order_number"]
    patient_name = report["patient_name"]

    subject = f"Resultados de laboratorio – Orden {order_number}"
    body_html = _build_email_body(patient_name, order_number)

    try:
        await gmail_client.send_pdf(
            recipient=email,
            subject=subject,
            body_html=body_html,
            pdf_bytes=pdf_bytes,
            filename=filename,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al enviar el correo electrónico: {exc}",
        )

    return {
        "order_number": order_number,
        "patient_name": patient_name,
        "email": email,
        "message": "Resultados enviados correctamente por correo electrónico.",
    }
