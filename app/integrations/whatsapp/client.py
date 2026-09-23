import asyncio
import base64
import functools
import re

import requests

from app.core.config import settings


class WhatsAppNumberNotFound(Exception):
    """Raised when Evolution reports that the number is not registered on WhatsApp."""

    def __init__(self, number: str):
        super().__init__(
            f"El número {number} no está registrado en WhatsApp. "
            "Verifique que sea correcto e incluya el código de país."
        )


class EvolutionWhatsAppClient:
    """HTTP client for the Evolution WhatsApp API."""

    def __init__(self):
        self._base_url = settings.WHATSAPP_BASE_URL
        self._instance_id = settings.WHATSAPP_INSTANCE_ID
        self._api_key = settings.WHATSAPP_API_KEY

    @property
    def _headers(self) -> dict:
        return {
            "apikey": self._api_key,
            "Content-Type": "application/json",
        }

    @staticmethod
    def _normalize_number(phone_number: str) -> str:
        """Keeps digits only and prepends the default country code when configured."""
        digits = re.sub(r"\D", "", phone_number or "")
        country_code = settings.WHATSAPP_DEFAULT_COUNTRY_CODE
        if country_code and not digits.startswith(country_code):
            digits = f"{country_code}{digits.lstrip('0')}"
        return digits

    def _post(self, url: str, payload: dict, timeout: int) -> dict:
        response = requests.post(url, json=payload, headers=self._headers, timeout=timeout)
        if response.ok:
            return response.json()

        try:
            body = response.json()
        except ValueError:
            body = response.text

        messages = body.get("response", {}).get("message", []) if isinstance(body, dict) else []
        if isinstance(messages, list) and any(
            isinstance(m, dict) and m.get("exists") is False for m in messages
        ):
            raise WhatsAppNumberNotFound(payload["number"])

        raise requests.HTTPError(f"{response.status_code} {response.reason}: {body}", response=response)

    def _send_text_sync(self, phone_number: str, message: str) -> dict:
        url = f"{self._base_url}/message/sendText/{self._instance_id}"
        payload = {
            "number": self._normalize_number(phone_number),
            "text": message,
            "delay": 500,
            "linkPreview": False,
            "mentionsEveryOne": False,
        }
        return self._post(url, payload, timeout=30)

    def _send_pdf_sync(self, phone_number: str, pdf_bytes: bytes, filename: str, caption: str = "") -> dict:
        url = f"{self._base_url}/message/sendMedia/{self._instance_id}"
        media_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
        payload = {
            "number": self._normalize_number(phone_number),
            "mediatype": "document",
            "mimetype": "application/pdf",
            "caption": caption,
            "media": media_base64,
            "fileName": filename,
            "delay": 500,
            "linkPreview": False,
            "mentionsEveryOne": False,
        }
        return self._post(url, payload, timeout=60)

    async def send_text(self, phone_number: str, message: str) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            functools.partial(self._send_text_sync, phone_number, message),
        )

    async def send_pdf(self, phone_number: str, pdf_bytes: bytes, filename: str, caption: str = "") -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            functools.partial(self._send_pdf_sync, phone_number, pdf_bytes, filename, caption),
        )


whatsapp_client = EvolutionWhatsAppClient()
