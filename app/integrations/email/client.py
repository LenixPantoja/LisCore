import asyncio
import functools
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings


class GmailClient:
    """SMTP email client using Gmail with an App Password."""

    def _send_sync(
        self,
        recipient: str,
        subject: str,
        body_html: str,
        attachment_bytes: bytes,
        attachment_filename: str,
    ) -> None:
        msg = MIMEMultipart("mixed")
        msg["From"] = settings.GMAIL_SENDER
        msg["To"] = recipient
        msg["Subject"] = subject

        msg.attach(MIMEText(body_html, "html", "utf-8"))

        pdf_part = MIMEApplication(attachment_bytes, _subtype="pdf")
        pdf_part.add_header(
            "Content-Disposition",
            "attachment",
            filename=attachment_filename,
        )
        msg.attach(pdf_part)

        with smtplib.SMTP(settings.GMAIL_SMTP_HOST, settings.GMAIL_SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.GMAIL_SENDER, settings.GMAIL_APP_PASSWORD)
            server.sendmail(settings.GMAIL_SENDER, recipient, msg.as_string())

    async def send_pdf(
        self,
        recipient: str,
        subject: str,
        body_html: str,
        pdf_bytes: bytes,
        filename: str,
    ) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            functools.partial(
                self._send_sync,
                recipient,
                subject,
                body_html,
                pdf_bytes,
                filename,
            ),
        )


gmail_client = GmailClient()
