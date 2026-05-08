"""
Servicio de la InterfazDG.

Coordina el parsing del XML y la futura integración con el dominio de solicitudes.
"""
from app.integrations.InterfazDG.models import DGSolicitudExamenes
from app.integrations.InterfazDG.parser import parse_solicitud


class InterfazDGService:

    def receive_solicitud(self, raw_body: bytes) -> DGSolicitudExamenes:
        """
        Recibe el cuerpo binario del XML, lo parsea y retorna el modelo.

        En el futuro, aquí se coordinará la creación de un InboundOrder
        en el sistema a partir de la solicitud parseada.
        """
        return parse_solicitud(raw_body)
