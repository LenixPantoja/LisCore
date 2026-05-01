"""
Modelos de datos para la InterfazDG.

Representan la estructura del XML de solicitud de examenes de laboratorio
transmitido por el HIS segun la documentacion de InterfazDG.
"""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class DGDatosGenerales:
    """Datos generales de la transmision."""
    id_origen: Optional[str] = None          # IDOrigen
    ord_consec: Optional[str] = None         # ORDCONSEC  - Consecutivo de la orden en el HIS
    fecha_servicio: Optional[str] = None     # LBHFECSER  - Fecha/hora del servicio
    tipo_ingreso: Optional[str] = None       # AINTIPING
    ip_ordenador: Optional[str] = None       # IPORDENAD
    usuario_codigo: Optional[str] = None     # GENUSUCOD
    usuario_nombre: Optional[str] = None     # GENUSUNOM


@dataclass
class DGDatosPaciente:
    """Informacion del paciente."""
    codigo: Optional[str] = None             # GPACODIGO  - Numero de documento
    tipo_documento: Optional[str] = None     # GPATIPDOC  - Tipo de documento
    primer_apellido: Optional[str] = None    # GPAAPELLI
    segundo_apellido: Optional[str] = None   # GPASEGAPE
    primer_nombre: Optional[str] = None      # GPANOMBRE
    segundo_nombre: Optional[str] = None     # GPASEGNOM
    fecha_nacimiento: Optional[str] = None   # GPAFECNAC
    sexo: Optional[str] = None               # GPASEXPAC
    direccion: Optional[str] = None          # GPADIRECC
    telefono: Optional[str] = None           # GPATELEF1
    tipo_usuario_codigo: Optional[str] = None   # TIPUSUCOD
    tipo_usuario_nombre: Optional[str] = None   # TIPUSUNOM
    municipio_codigo: Optional[str] = None   # GEMCODIGO
    municipio_nombre: Optional[str] = None   # GEMNOMBRE
    diagnostico_codigo: Optional[str] = None # CODICIE10
    diagnostico_nombre: Optional[str] = None # NOMBCIE10
    ocupacion_codigo: Optional[str] = None   # CODIGRADO
    ocupacion_nombre: Optional[str] = None   # NOMBGRADO
    embarazo_codigo: Optional[str] = None    # CODEMBARA
    embarazo_nombre: Optional[str] = None    # NOMEMBARA
    email: Optional[str] = None              # EMAILPACI


@dataclass
class DGDatosOrden:
    """Datos de la orden (empresa, medico, area, servicio)."""
    empresa_nit: Optional[str] = None        # LBHNITENT
    empresa_nombre: Optional[str] = None     # LBHNOMENT
    medico_codigo: Optional[str] = None      # GMECODIGO
    medico_nombre: Optional[str] = None      # GMENOMBRE
    area_codigo: Optional[str] = None        # ARECODIGO
    area_nombre: Optional[str] = None        # ARENOMBRE
    servicio_codigo: Optional[str] = None    # GEECODIGO
    servicio_nombre: Optional[str] = None    # GEENOMBRE


@dataclass
class DGExamen:
    """Examen individual solicitado."""
    oid_solicitud: Optional[str] = None      # OIDSolicitud - ID unico de la solicitud del examen
    cantidad: Optional[str] = None           # LBHCANTID
    id_examen: Optional[str] = None          # IDEXAMEN    - Codigo del examen en el HIS
    nombre_examen: Optional[str] = None      # EXANOMBRE
    detalle_codigo: Optional[str] = None     # EXADETCOD
    detalle_nombre: Optional[str] = None     # EXADETNOM
    observacion: Optional[str] = None        # EXAOBSER


@dataclass
class DGSolicitudExamenes:
    """Solicitud de examenes de laboratorio recibida del HIS."""
    datos_generales: Optional[DGDatosGenerales] = None
    datos_paciente: Optional[DGDatosPaciente] = None
    datos_orden: Optional[DGDatosOrden] = None
    examenes: List[DGExamen] = field(default_factory=list)