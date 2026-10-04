"""
Cliente HTTP para el servicio externo que renderiza el PDF de resultados de
laboratorio a partir de los datos estructurados (ver
/api/reports/laboratory-results/report-data).

Usado por la v2 de /api/reports/laboratory-results: en vez de generar el PDF
localmente con reportlab, le envía el JSON (parametros + grupos_trabajo) a
este servicio y usa el PDF que responde.
"""
import asyncio
import functools

import requests

from app.core.config import settings

RESULTADO_LABORATORIO_PATH = "/api/reports/resultado-laboratorio"


class PdfRendererClient:
    """Cliente para el servicio externo de renderizado de PDF de resultados."""

    def _render_sync(self, host: str, payload: dict) -> bytes:
        url = f"http://{host}:{settings.PDF_RENDERER_PORT}{RESULTADO_LABORATORIO_PATH}"
        response = requests.post(url, json=payload, timeout=60)

        if not response.ok:
            raise requests.HTTPError(
                f"{response.status_code} {response.reason} al generar el PDF en {url}: "
                f"{response.text[:500]}",
                response=response,
            )

        content_type = response.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower() and not response.content.startswith(b"%PDF"):
            raise ValueError(
                f"El servicio de generación de PDF ({url}) no devolvió un PDF válido "
                f"(Content-Type: {content_type or 'desconocido'})."
            )

        return response.content

    async def render(self, host: str, payload: dict) -> bytes:
        """Envía `payload` (parametros + grupos_trabajo) y retorna los bytes del PDF."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, functools.partial(self._render_sync, host, payload)
        )


pdf_renderer_client = PdfRendererClient()
