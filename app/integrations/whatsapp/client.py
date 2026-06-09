import asyncio
import base64
import functools

import requests

from app.core.config import settings


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

    def _send_text_sync(self, phone_number: str, message: str) -> dict:
        url = f"{self._base_url}/message/sendText/{self._instance_id}"
        payload = {
            "number": phone_number,
            "text": message,
            "delay": 500,
            "linkPreview": False,
            "mentionsEveryOne": False,
        }
        response = requests.post(url, json=payload, headers=self._headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def _send_pdf_sync(self, phone_number: str, pdf_bytes: bytes, filename: str, caption: str = "") -> dict:
        url = f"{self._base_url}/message/sendMedia/{self._instance_id}"
        media_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
        payload = {
            "number": phone_number,
            "mediatype": "document",
            "mimetype": "application/pdf",
            "caption": caption,
            "media": media_base64,
            "fileName": filename,
            "delay": 500,
            "linkPreview": False,
            "mentionsEveryOne": False,
        }
        response = requests.post(url, json=payload, headers=self._headers, timeout=60)
        response.raise_for_status()
        return response.json()

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
