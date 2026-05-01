"""
Caso de uso: registrar solicitud de examenes recibida via InterfazDG.

Orquesta la busqueda de entidades del dominio y la creacion del InboundOrder.
"""
from datetime import datetime, date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.enterprises.domain.models import Enterprise
from app.domains.interfaces.domain.models import InterfacesRest, InterfacesRestDetail
from app.domains.masters.domain.models import Diagnosis, DocumentType, Service
from app.domains.patients.domain.models import Patient
from app.domains.patients.infrastructure.repository import PatientRepository
from app.domains.requests.infrastructure.repository import InboundOrderRepository
from app.integrations.InterfazDG.models import DGSolicitudExamenes

# Estado inicial de un detalle: Pendiente
INBOUND_DETAIL_STATE_PENDIENTE = 0


async def registrar_solicitud_dg(
    db: AsyncSession,
    solicitud: DGSolicitudExamenes,
) -> int:
    """
    Crea un InboundOrder e InboundOrderDetails a partir de una DGSolicitudExamenes.

    - Primero resuelve la empresa e interfaz configurada.
    - Si el paciente no existe en el sistema, lo crea con los datos del XML.
    - La homologacion de estudios se realiza via InterfacesRest/InterfacesRestDetail
      usando el enterprise_id y el codigo del examen enviado por el HIS (IDEXAMEN).
    - Retorna el io_id del InboundOrder creado.

    Raises:
        HTTPException 422 si faltan datos requeridos en el XML.
        HTTPException 404 si algun estudio no tiene homologacion configurada.
    """
    dg = solicitud.datos_generales
    dp = solicitud.datos_paciente
    do = solicitud.datos_orden

    # --- 1. Buscar empresa por NIT y obtener la interfaz configurada ---
    enterprise_id: Optional[int] = None
    interface_rest_id: Optional[int] = None
    tariff_id: Optional[int] = None

    if do and do.empresa_nit:
        res_ent = await db.execute(
            select(Enterprise).where(Enterprise.en_nit == do.empresa_nit)
        )
        enterprise: Optional[Enterprise] = res_ent.scalars().first()
        if enterprise:
            enterprise_id = enterprise.en_id
            res_iface = await db.execute(
                select(InterfacesRest).where(
                    InterfacesRest.it_enterprise_id == enterprise_id,
                )
            )
            iface: Optional[InterfacesRest] = res_iface.scalars().first()
            if iface:
                interface_rest_id = iface.it_id
                tariff_id = iface.it_tariff_id

    if not interface_rest_id:
        nit = do.empresa_nit if do else "N/A"
        if not enterprise_id:
            detalle = f"No se encontro la empresa con NIT '{nit}' en el sistema."
        else:
            detalle = (
                f"No se encontro una interfaz configurada en InterfacesRest "
                f"para la empresa con NIT '{nit}' (id={enterprise_id})."
            )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detalle,
        )

    # --- 2. Buscar o crear paciente por numero de documento ---
    documento_paciente = dp.codigo if dp else None
    if not documento_paciente:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El XML no contiene el numero de documento del paciente (GPACODIGO).",
        )

    result = await db.execute(
        select(Patient).where(Patient.pt_Number_document == documento_paciente)
    )
    patient: Optional[Patient] = result.scalars().first()

    if patient:
        # El paciente existe: verificar que el tipo de documento coincida
        doc_type_id = await _resolver_tipo_documento(db, dp.tipo_documento if dp else None)
        if doc_type_id is not None and patient.pt_Document_Type_id != doc_type_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"El paciente con documento '{documento_paciente}' ya existe en el sistema "
                    f"pero con un tipo de documento diferente al recibido en la solicitud. "
                    "No se puede registrar la solicitud."
                ),
            )
        # Actualizar campos faltantes si el paciente no los tiene registrados
        updated = False
        if patient.pt_date_of_birth is None and dp and dp.fecha_nacimiento:
            parsed_dob = _parse_date(dp.fecha_nacimiento)
            if parsed_dob is not None:
                patient.pt_date_of_birth = parsed_dob
                updated = True
        if patient.pt_enterprise_id is None and enterprise_id is not None:
            patient.pt_enterprise_id = enterprise_id
            updated = True
        if updated:
            await db.commit()
            await db.refresh(patient)
    else:
        # Paciente no existe -> crearlo con enterprise_id
        patient = await _crear_paciente(db, dp, enterprise_id)

    # --- 3. Homologar estudios via InterfacesRestDetail ---
    detail_data_list: list[dict] = []
    if solicitud.examenes:
        for examen in solicitud.examenes:
            codigo_his = examen.id_examen
            if not codigo_his:
                continue

            res_detail = await db.execute(
                select(InterfacesRestDetail).where(
                    InterfacesRestDetail.itd_interface_rest_id == interface_rest_id,
                    InterfacesRestDetail.itd_send_code == codigo_his,
                )
            )
            detail_map: Optional[InterfacesRestDetail] = res_detail.scalars().first()
            if not detail_map or not detail_map.itd_study_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        f"No existe homologacion para el examen con codigo HIS '{codigo_his}' "
                        f"({examen.nombre_examen or ''}) en la interfaz configurada para la empresa."
                    ),
                )

            detail_data_list.append(
                {
                    "iod_study_id": detail_map.itd_study_id,
                    "iod_state": INBOUND_DETAIL_STATE_PENDIENTE,
                    "iod_observation": examen.observacion,
                }
            )

    if not detail_data_list:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El XML no contiene examenes validos para registrar.",
        )

    # --- 4. Homologar servicio (ARECODIGO -> Services.code -> Services.id) ---
    service_id: Optional[int] = None
    if do and do.area_codigo:
        res_svc = await db.execute(
            select(Service).where(Service.code == do.area_codigo)
        )
        svc: Optional[Service] = res_svc.scalars().first()
        if svc:
            service_id = svc.id

    # --- 5. Homologar diagnostico (CODICIE10 -> Diagnoses.diag_code -> Diagnoses.diag_id) ---
    diagnostic_id: Optional[int] = None
    if dp and dp.diagnostico_codigo:
        res_diag = await db.execute(
            select(Diagnosis).where(Diagnosis.diag_code == dp.diagnostico_codigo)
        )
        diag: Optional[Diagnosis] = res_diag.scalars().first()
        if diag:
            diagnostic_id = diag.diag_id
        print(f"[InterfazDG] diagnostico_codigo='{dp.diagnostico_codigo}' → diagnostic_id={diagnostic_id}")

    # --- 6. Construir datos del InboundOrder ---
    order_data = {
        "io_number_request": dg.ord_consec if dg else None,
        "io_date_request": _parse_datetime(dg.fecha_servicio if dg else None),
        "io_date_transmission": datetime.utcnow(),
        "io_patient_id": patient.pt_id,
        "io_origin": dg.id_origen if dg else None,
        "io_medic_document_number": do.medico_codigo if do else None,
        "io_medic_name": do.medico_nombre if do else None,
        "io_enterprise_id": enterprise_id,
        "io_tariff_id": tariff_id,
        "io_income": dg.tipo_ingreso if dg else None,
        "io_service_id": service_id,
        "io_diagnostic_id": diagnostic_id,
    }

    # --- 7. Crear el InboundOrder con sus detalles ---
    inbound = await InboundOrderRepository.create(db, order_data, detail_data_list)
    return inbound.io_id


async def _crear_paciente(db: AsyncSession, dp, enterprise_id: Optional[int] = None) -> Patient:
    """Crea un paciente nuevo con los datos del XML del HIS."""
    doc_type_id = await _resolver_tipo_documento(db, dp.tipo_documento if dp else None)
    fecha_raw = dp.fecha_nacimiento
    fecha_parseada = _parse_date(fecha_raw)
    print(f"[InterfazDG] fecha_nacimiento raw='{fecha_raw}' parseada='{fecha_parseada}'")
    patient_data = {
        "pt_Number_document": dp.codigo,
        "pt_firts_name": dp.primer_nombre or "",
        "pt_middle_name": dp.segundo_nombre,
        "pt_last_name": dp.primer_apellido or "",
        "pt_second_last_name": dp.segundo_apellido or "",
        "pt_phone_number": dp.telefono,
        "pt_mail": dp.email,
        "pt_address": dp.direccion,
        "pt_date_of_birth": fecha_parseada,
        "pt_sex_type": _mapear_sexo(dp.sexo),
        "pt_Document_Type_id": doc_type_id,
        "pt_enterprise_id": enterprise_id,
    }
    return await PatientRepository.create(db, patient_data)


async def _resolver_tipo_documento(
    db: AsyncSession, codigo_his: Optional[str]
) -> Optional[int]:
    """
    Busca el id del tipo de documento en DocumentsTypes usando dt_id_dinamica,
    que corresponde al id del tipo de documento enviado por el HIS Dinamica (GPATIPDOC).
    Retorna None si no se recibe codigo o no se encuentra coincidencia.
    """
    if not codigo_his:
        return None
    try:
        id_dinamica = int(codigo_his)
    except (ValueError, TypeError):
        return None
    res = await db.execute(
        select(DocumentType).where(DocumentType.dt_id_dinamica == id_dinamica)
    )
    doc_type: Optional[DocumentType] = res.scalars().first()
    return doc_type.dt_id if doc_type else None


# Homologacion sexo HIS -> id Sex_Types del LIS
# 1 (Hombre en HIS) -> 1 (Hombre en LIS)
# 2 (Mujer en HIS)  -> 3 (Mujer en LIS)
_SEXO_HIS_A_LIS: dict[str, int] = {"1": 1, "2": 3}


def _mapear_sexo(valor: Optional[str]) -> Optional[int]:
    """Convierte el codigo de sexo del HIS al id de Sex_Types del LIS."""
    if not valor:
        return None
    return _SEXO_HIS_A_LIS.get(str(valor).strip())


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Intenta parsear una fecha/hora en los formatos comunes del HIS."""
    if not value:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _parse_date(value: Optional[str]) -> Optional[date]:
    """Intenta parsear una fecha en los formatos comunes del HIS."""
    if not value:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
