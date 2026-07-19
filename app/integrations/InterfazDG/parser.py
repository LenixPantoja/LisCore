"""
Parser XML para la InterfazDG.

Convierte el XML de solicitud de exámenes del HIS en modelos DG.
Formato de entrada: <DocumentElement> con codificación UTF-16.
"""
import io
import xml.etree.ElementTree as ET
from typing import Optional

from app.integrations.InterfazDG.models import (
    DGSolicitudExamenes,
    DGDatosGenerales,
    DGDatosPaciente,
    DGDatosOrden,
    DGExamen,
)


def _text(parent: Optional[ET.Element], tag: str) -> Optional[str]:
    """Retorna el texto limpio de un sub-elemento o None si no existe."""
    child = parent.find(tag) if parent is not None else None
    if child is None or child.text is None:
        return None
    return child.text.strip() or None


def _parse_root(raw: bytes) -> ET.Element:
    """
    Parsea el XML desde bytes, manejando BOM y declaracion de encoding.

    ElementTree.parse con BytesIO maneja UTF-16 BOM y la declaracion
    <?xml encoding="utf-16"?> correctamente, a diferencia de fromstring
    que requiere un str sin declaracion de encoding.
    """
    return ET.parse(io.BytesIO(raw)).getroot()


def parse_solicitud(raw_body: bytes) -> DGSolicitudExamenes:
    """
    Parsea el cuerpo binario del XML y retorna un DGSolicitudExamenes.

    Estructura XML esperada::

        <DocumentElement>
          <DatosGenerales>
            <IDOrigen />
            <ORDCONSEC />
            <LBHFECSER />
            <AINTIPING />
            <IPORDENAD />
            <GENUSUCOD />
            <GENUSUNOM />
          </DatosGenerales>
          <DatosPaciente>
            <GPACODIGO /><GPATIPDOC /><GPAAPELLI /><GPASEGAPE />
            <GPANOMBRE /><GPASEGNOM /><GPAFECNAC /><GPASEXPAC />
            <GPADIRECC /><GPATELEF1 /><TIPUSUCOD /><TIPUSUNOM />
            <GEMCODIGO /><GEMNOMBRE /><CODICIE10 /><NOMBCIE10 />
            <CODIGRADO /><NOMBGRADO /><CODEMBARA /><NOMEMBARA />
            <EMAILPACI />
          </DatosPaciente>
          <DatosOrden>
            <LBHNITENT /><LBHNOMENT /><GMECODIGO /><GMENOMBRE />
            <ARECODIGO /><ARENOMBRE /><GEECODIGO /><GEENOMBRE />
            <GESERCODIGO /><GESERNOMBRE />
          </DatosOrden>
          <Examenes>
            <Examen>
              <OIDSolicitud /><LBHCANTID /><IDEXAMEN /><EXANOMBRE />
              <EXADETCOD /><EXADETNOM /><EXAOBSER />
            </Examen>
          </Examenes>
        </DocumentElement>
    """
    root = _parse_root(raw_body)

    solicitud = DGSolicitudExamenes()

    # --- DatosGenerales ---
    dg_el = root.find("DatosGenerales")
    if dg_el is not None:
        solicitud.datos_generales = DGDatosGenerales(
            id_origen=_text(dg_el, "IDOrigen"),
            ord_consec=_text(dg_el, "ORDCONSEC"),
            fecha_servicio=_text(dg_el, "LBHFECSER"),
            tipo_ingreso=_text(dg_el, "AINTIPING"),
            ip_ordenador=_text(dg_el, "IPORDENAD"),
            usuario_codigo=_text(dg_el, "GENUSUCOD"),
            usuario_nombre=_text(dg_el, "GENUSUNOM"),
        )

    # --- DatosPaciente ---
    dp_el = root.find("DatosPaciente")
    if dp_el is not None:
        solicitud.datos_paciente = DGDatosPaciente(
            codigo=_text(dp_el, "GPACODIGO"),
            tipo_documento=_text(dp_el, "GPATIPDOC"),
            primer_apellido=_text(dp_el, "GPAAPELLI"),
            segundo_apellido=_text(dp_el, "GPASEGAPE"),
            primer_nombre=_text(dp_el, "GPANOMBRE"),
            segundo_nombre=_text(dp_el, "GPASEGNOM"),
            fecha_nacimiento=_text(dp_el, "GPAFECNAC"),
            sexo=_text(dp_el, "GPASEXPAC"),
            direccion=_text(dp_el, "GPADIRECC"),
            telefono=_text(dp_el, "GPATELEF1"),
            tipo_usuario_codigo=_text(dp_el, "TIPUSUCOD"),
            tipo_usuario_nombre=_text(dp_el, "TIPUSUNOM"),
            municipio_codigo=_text(dp_el, "GEMCODIGO"),
            municipio_nombre=_text(dp_el, "GEMNOMBRE"),
            diagnostico_codigo=_text(dp_el, "CODICIE10"),
            diagnostico_nombre=_text(dp_el, "NOMBCIE10"),
            ocupacion_codigo=_text(dp_el, "CODIGRADO"),
            ocupacion_nombre=_text(dp_el, "NOMBGRADO"),
            embarazo_codigo=_text(dp_el, "CODEMBARA"),
            embarazo_nombre=_text(dp_el, "NOMEMBARA"),
            email=_text(dp_el, "EMAILPACI"),
            municipio_ciudad_codigo=_text(dp_el, "GPACIUDAD"),
        )

    # --- DatosOrden ---
    do_el = root.find("DatosOrden")
    if do_el is not None:
        solicitud.datos_orden = DGDatosOrden(
            empresa_nit=_text(do_el, "LBHNITENT"),
            empresa_nombre=_text(do_el, "LBHNOMENT"),
            medico_codigo=_text(do_el, "GMECODIGO"),
            medico_nombre=_text(do_el, "GMENOMBRE"),
            area_codigo=_text(do_el, "ARECODIGO"),
            area_nombre=_text(do_el, "ARENOMBRE"),
            servicio_codigo=_text(do_el, "GEECODIGO"),
            servicio_nombre=_text(do_el, "GEENOMBRE"),
            geser_codigo=_text(do_el, "GESERCODIGO"),
            geser_nombre=_text(do_el, "GESERNOMBRE"),
        )

    # --- Exámenes ---
    examenes_el = root.find("Examenes")
    if examenes_el is not None:
        for examen_el in examenes_el.findall("Examen"):
            solicitud.examenes.append(
                DGExamen(
                    oid_solicitud=_text(examen_el, "OIDSolicitud"),
                    cantidad=_text(examen_el, "LBHCANTID"),
                    id_examen=_text(examen_el, "IDEXAMEN"),
                    nombre_examen=_text(examen_el, "EXANOMBRE"),
                    detalle_codigo=_text(examen_el, "EXADETCOD"),
                    detalle_nombre=_text(examen_el, "EXADETNOM"),
                    observacion=_text(examen_el, "EXAOBSER"),
                )
            )

    return solicitud
