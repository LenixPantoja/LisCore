"""
Migration: Seed all modules permissions

Seeds the Permissions table with permissions for every endpoint in the API,
following the Module:Action naming convention.

Modules covered:
  Patients, Orders, Billing, Analyzers, Enterprises, Headquarters,
  Locations, Masters, TestsLab, StudiesLab, Tariffs, Contracts,
  Reports, Samples, Requests, Traces, Laboratories, Interfaces,
  Cities, AppUsers (extra), Permissions, Rols (extra)

Run with: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

revision = "015_seed_all_modules_permissions"
down_revision = "014_add_rp_active_to_rol_permissions"
branch_labels = None
depends_on = None

_permissions_table = table(
    "Permissions",
    column("p_name", sa.String),
    column("p_description", sa.String),
    column("p_module", sa.String),
)

_PERMISSIONS = [
    # ── AppUsers extras (complements migration 013) ───────────────────────
    {"p_name": "AppUsers:GetOne", "p_description": "Obtener detalle de un usuario", "p_module": "AppUsers"},

    # ── Permissions management ────────────────────────────────────────────
    {"p_name": "Permissions:Read",  "p_description": "Listar y consultar permisos", "p_module": "Permissions"},
    {"p_name": "Permissions:Write", "p_description": "Crear, editar y eliminar permisos", "p_module": "Permissions"},

    # ── Rols extras (complements migration 013) ───────────────────────────
    {"p_name": "Rols:GetOne", "p_description": "Obtener detalle de un rol con sus permisos", "p_module": "Rols"},

    # ── Patients ──────────────────────────────────────────────────────────
    {"p_name": "Patients:Create", "p_description": "Crear nuevos pacientes",             "p_module": "Patients"},
    {"p_name": "Patients:List",   "p_description": "Listar y buscar pacientes",           "p_module": "Patients"},
    {"p_name": "Patients:GetOne", "p_description": "Obtener detalle de un paciente",      "p_module": "Patients"},
    {"p_name": "Patients:Update", "p_description": "Actualizar datos de un paciente",     "p_module": "Patients"},

    # ── Orders ────────────────────────────────────────────────────────────
    {"p_name": "Orders:Create",           "p_description": "Crear órdenes de laboratorio",                  "p_module": "Orders"},
    {"p_name": "Orders:List",             "p_description": "Listar órdenes",                                "p_module": "Orders"},
    {"p_name": "Orders:GetOne",           "p_description": "Obtener detalle de una orden",                  "p_module": "Orders"},
    {"p_name": "Orders:Update",           "p_description": "Actualizar campos básicos de una orden",        "p_module": "Orders"},
    {"p_name": "Orders:Edit",             "p_description": "Editar orden y agregar estudios",               "p_module": "Orders"},
    {"p_name": "Orders:CancelStudies",    "p_description": "Anular estudios de una orden",                  "p_module": "Orders"},
    {"p_name": "Orders:GetDetails",       "p_description": "Obtener detalle paginado de una orden",         "p_module": "Orders"},
    {"p_name": "Orders:GetFullDetails",   "p_description": "Obtener detalle completo de una orden",         "p_module": "Orders"},
    {"p_name": "Orders:GetNextNumber",    "p_description": "Consultar el siguiente número de orden",        "p_module": "Orders"},
    {"p_name": "Orders:GetEvolutionChart","p_description": "Consultar gráfico evolutivo de resultados",     "p_module": "Orders"},

    # ── Billing ───────────────────────────────────────────────────────────
    {"p_name": "Billing:Create", "p_description": "Crear facturas",           "p_module": "Billing"},
    {"p_name": "Billing:List",   "p_description": "Listar facturas",          "p_module": "Billing"},
    {"p_name": "Billing:GetOne", "p_description": "Obtener detalle de factura","p_module": "Billing"},
    {"p_name": "Billing:Update", "p_description": "Actualizar facturas",      "p_module": "Billing"},
    {"p_name": "Billing:Delete", "p_description": "Eliminar facturas",        "p_module": "Billing"},

    # ── Analyzers ─────────────────────────────────────────────────────────
    {"p_name": "Analyzers:CreateGroup",  "p_description": "Crear grupos de analizadores",             "p_module": "Analyzers"},
    {"p_name": "Analyzers:ListGroups",   "p_description": "Listar grupos de analizadores",            "p_module": "Analyzers"},
    {"p_name": "Analyzers:GetGroup",     "p_description": "Obtener detalle de grupo de analizadores", "p_module": "Analyzers"},
    {"p_name": "Analyzers:UpdateGroup",  "p_description": "Actualizar grupo de analizadores",         "p_module": "Analyzers"},
    {"p_name": "Analyzers:DeleteGroup",  "p_description": "Eliminar grupo de analizadores",           "p_module": "Analyzers"},
    {"p_name": "Analyzers:Create",       "p_description": "Crear analizadores",                       "p_module": "Analyzers"},
    {"p_name": "Analyzers:List",         "p_description": "Listar analizadores",                      "p_module": "Analyzers"},
    {"p_name": "Analyzers:GetOne",       "p_description": "Obtener detalle de un analizador",         "p_module": "Analyzers"},
    {"p_name": "Analyzers:Update",       "p_description": "Actualizar analizadores",                  "p_module": "Analyzers"},
    {"p_name": "Analyzers:Delete",       "p_description": "Eliminar analizadores",                    "p_module": "Analyzers"},
    {"p_name": "Analyzers:CreateDetail", "p_description": "Crear detalle de analizador",              "p_module": "Analyzers"},
    {"p_name": "Analyzers:ListDetails",  "p_description": "Listar detalles de analizador",            "p_module": "Analyzers"},
    {"p_name": "Analyzers:GetDetail",    "p_description": "Obtener detalle de analizador",            "p_module": "Analyzers"},
    {"p_name": "Analyzers:UpdateDetail", "p_description": "Actualizar detalle de analizador",         "p_module": "Analyzers"},
    {"p_name": "Analyzers:DeleteDetail", "p_description": "Eliminar detalle de analizador",           "p_module": "Analyzers"},

    # ── Enterprises ───────────────────────────────────────────────────────
    {"p_name": "Enterprises:Create",      "p_description": "Crear empresas",                    "p_module": "Enterprises"},
    {"p_name": "Enterprises:List",        "p_description": "Listar empresas",                   "p_module": "Enterprises"},
    {"p_name": "Enterprises:GetOne",      "p_description": "Obtener detalle de una empresa",    "p_module": "Enterprises"},
    {"p_name": "Enterprises:Update",      "p_description": "Actualizar empresas",               "p_module": "Enterprises"},
    {"p_name": "Enterprises:GetContracts","p_description": "Obtener contratos de una empresa",  "p_module": "Enterprises"},

    # ── Headquarters ──────────────────────────────────────────────────────
    {"p_name": "Headquarters:Create", "p_description": "Crear sedes",             "p_module": "Headquarters"},
    {"p_name": "Headquarters:List",   "p_description": "Listar sedes",            "p_module": "Headquarters"},
    {"p_name": "Headquarters:GetOne", "p_description": "Obtener detalle de sede", "p_module": "Headquarters"},
    {"p_name": "Headquarters:Update", "p_description": "Actualizar sedes",        "p_module": "Headquarters"},
    {"p_name": "Headquarters:Delete", "p_description": "Eliminar sedes",          "p_module": "Headquarters"},

    # ── Locations ─────────────────────────────────────────────────────────
    {"p_name": "Locations:List",   "p_description": "Listar ubicaciones",            "p_module": "Locations"},
    {"p_name": "Locations:GetOne", "p_description": "Obtener detalle de ubicación",  "p_module": "Locations"},

    # ── Masters ───────────────────────────────────────────────────────────
    {"p_name": "Masters:Read",                   "p_description": "Consultar tablas maestras (países, ciudades, tipos de doc., etc.)", "p_module": "Masters"},
    {"p_name": "Masters:CreateTechnique",        "p_description": "Crear técnicas",                                                    "p_module": "Masters"},
    {"p_name": "Masters:UpdateTechnique",        "p_description": "Actualizar técnicas",                                               "p_module": "Masters"},
    {"p_name": "Masters:CreateWorkGroup",        "p_description": "Crear grupos de trabajo",                                           "p_module": "Masters"},
    {"p_name": "Masters:UpdateWorkGroup",        "p_description": "Actualizar grupos de trabajo",                                      "p_module": "Masters"},
    {"p_name": "Masters:CreateReferralLocation", "p_description": "Crear ubicaciones de remisión",                                     "p_module": "Masters"},
    {"p_name": "Masters:UpdateReferralLocation", "p_description": "Actualizar ubicaciones de remisión",                                "p_module": "Masters"},

    # ── TestsLab ──────────────────────────────────────────────────────────
    {"p_name": "TestsLab:Create",                "p_description": "Crear exámenes de laboratorio",           "p_module": "TestsLab"},
    {"p_name": "TestsLab:List",                  "p_description": "Listar exámenes de laboratorio",          "p_module": "TestsLab"},
    {"p_name": "TestsLab:GetOne",                "p_description": "Obtener detalle de un examen",            "p_module": "TestsLab"},
    {"p_name": "TestsLab:Update",                "p_description": "Actualizar exámenes de laboratorio",      "p_module": "TestsLab"},
    {"p_name": "TestsLab:Delete",                "p_description": "Eliminar exámenes de laboratorio",        "p_module": "TestsLab"},
    {"p_name": "TestsLab:ManageRanges",          "p_description": "Gestionar rangos de referencia",          "p_module": "TestsLab"},
    {"p_name": "TestsLab:ManageReferenceValues", "p_description": "Gestionar valores de referencia",         "p_module": "TestsLab"},

    # ── StudiesLab ────────────────────────────────────────────────────────
    {"p_name": "StudiesLab:Create",      "p_description": "Crear estudios de laboratorio",           "p_module": "StudiesLab"},
    {"p_name": "StudiesLab:List",        "p_description": "Listar estudios de laboratorio",          "p_module": "StudiesLab"},
    {"p_name": "StudiesLab:GetOne",      "p_description": "Obtener detalle de un estudio",           "p_module": "StudiesLab"},
    {"p_name": "StudiesLab:Update",      "p_description": "Actualizar estudios de laboratorio",      "p_module": "StudiesLab"},
    {"p_name": "StudiesLab:ManageTests", "p_description": "Gestionar exámenes dentro de un estudio", "p_module": "StudiesLab"},

    # ── Tariffs ───────────────────────────────────────────────────────────
    {"p_name": "Tariffs:Create",        "p_description": "Crear tarifas",                           "p_module": "Tariffs"},
    {"p_name": "Tariffs:List",          "p_description": "Listar tarifas",                          "p_module": "Tariffs"},
    {"p_name": "Tariffs:GetOne",        "p_description": "Obtener detalle de una tarifa",            "p_module": "Tariffs"},
    {"p_name": "Tariffs:Update",        "p_description": "Actualizar tarifas",                      "p_module": "Tariffs"},
    {"p_name": "Tariffs:Delete",        "p_description": "Eliminar tarifas",                        "p_module": "Tariffs"},
    {"p_name": "Tariffs:ManageDetails", "p_description": "Gestionar detalle de líneas de tarifas",  "p_module": "Tariffs"},

    # ── Contracts ─────────────────────────────────────────────────────────
    {"p_name": "Contracts:Create",       "p_description": "Crear contratos",                      "p_module": "Contracts"},
    {"p_name": "Contracts:List",         "p_description": "Listar contratos",                     "p_module": "Contracts"},
    {"p_name": "Contracts:GetOne",       "p_description": "Obtener detalle de un contrato",       "p_module": "Contracts"},
    {"p_name": "Contracts:Update",       "p_description": "Actualizar contratos",                 "p_module": "Contracts"},
    {"p_name": "Contracts:LinkTariff",   "p_description": "Vincular tarifa a un contrato",        "p_module": "Contracts"},
    {"p_name": "Contracts:UnlinkTariff", "p_description": "Desvincular tarifa de un contrato",    "p_module": "Contracts"},

    # ── Reports ───────────────────────────────────────────────────────────
    {"p_name": "Reports:GenerateReport", "p_description": "Generar PDF de resultados de laboratorio", "p_module": "Reports"},
    {"p_name": "Reports:Dashboard",      "p_description": "Consultar estadísticas del dashboard",    "p_module": "Reports"},
    {"p_name": "Reports:Kpis",           "p_description": "Consultar KPIs de órdenes",              "p_module": "Reports"},

    # ── Samples ───────────────────────────────────────────────────────────
    {"p_name": "Samples:Create", "p_description": "Crear tipos de muestra",             "p_module": "Samples"},
    {"p_name": "Samples:List",   "p_description": "Listar tipos de muestra",            "p_module": "Samples"},
    {"p_name": "Samples:GetOne", "p_description": "Obtener detalle de tipo de muestra", "p_module": "Samples"},
    {"p_name": "Samples:Update", "p_description": "Actualizar tipos de muestra",        "p_module": "Samples"},
    {"p_name": "Samples:Delete", "p_description": "Eliminar tipos de muestra",          "p_module": "Samples"},

    # ── Requests (InboundOrders) ──────────────────────────────────────────
    {"p_name": "Requests:Create",      "p_description": "Crear solicitudes de ingreso",           "p_module": "Requests"},
    {"p_name": "Requests:List",        "p_description": "Listar solicitudes de ingreso",          "p_module": "Requests"},
    {"p_name": "Requests:GetOne",      "p_description": "Obtener detalle de una solicitud",       "p_module": "Requests"},
    {"p_name": "Requests:Update",      "p_description": "Actualizar solicitudes de ingreso",      "p_module": "Requests"},
    {"p_name": "Requests:Delete",      "p_description": "Eliminar solicitudes de ingreso",        "p_module": "Requests"},
    {"p_name": "Requests:CreateOrder", "p_description": "Crear orden desde solicitud de ingreso", "p_module": "Requests"},

    # ── Traces ────────────────────────────────────────────────────────────
    {"p_name": "Traces:Read", "p_description": "Consultar trazas de órdenes y exámenes", "p_module": "Traces"},

    # ── KPIs ────────────────────────────────────────────────────────────────
    {"p_name": "Kpis:ValidatedStudies", "p_description": "Consultar KPI de estudios validados por mes", "p_module": "Kpis"},

    # ── Laboratories ──────────────────────────────────────────────────────
    {"p_name": "Laboratories:BulkUpdate",    "p_description": "Actualizacion masiva de resultados de laboratorio", "p_module": "Laboratories"},
    {"p_name": "Laboratories:Invalidate",    "p_description": "Desvalidar laboratorios",                         "p_module": "Laboratories"},
    {"p_name": "Laboratories:Validate",      "p_description": "Validar laboratorios con resultados",             "p_module": "Laboratories"},
    {"p_name": "Laboratories:ClearResults",  "p_description": "Limpiar resultados de laboratorio",              "p_module": "Laboratories"},
    {"p_name": "Laboratories:UpdateState",   "p_description": "Cambiar estado de estudio en orden",             "p_module": "Laboratories"},
    {"p_name": "Laboratories:ManageGraphics","p_description": "Subir y vincular imagenes a resultados",         "p_module": "Laboratories"},

    # ── Interfaces ────────────────────────────────────────────────────────
    {"p_name": "Interfaces:Create",        "p_description": "Crear interfaces REST",               "p_module": "Interfaces"},
    {"p_name": "Interfaces:List",          "p_description": "Listar interfaces REST",              "p_module": "Interfaces"},
    {"p_name": "Interfaces:GetOne",        "p_description": "Obtener detalle de interfaz REST",   "p_module": "Interfaces"},
    {"p_name": "Interfaces:Update",        "p_description": "Actualizar interfaces REST",          "p_module": "Interfaces"},
    {"p_name": "Interfaces:Delete",        "p_description": "Eliminar interfaces REST",            "p_module": "Interfaces"},
    {"p_name": "Interfaces:ManageDetails", "p_description": "Gestionar detalles de interfaz REST","p_module": "Interfaces"},

    # ── Cities ────────────────────────────────────────────────────────────
    {"p_name": "Cities:List",   "p_description": "Listar ciudades",           "p_module": "Cities"},
    {"p_name": "Cities:GetOne", "p_description": "Obtener detalle de ciudad", "p_module": "Cities"},
]


def upgrade() -> None:
    conn = op.get_bind()
    existing = {
        row[0]
        for row in conn.execute(sa.text('SELECT p_name FROM "Permissions"')).fetchall()
    }
    new_permissions = [p for p in _PERMISSIONS if p["p_name"] not in existing]
    if new_permissions:
        op.bulk_insert(_permissions_table, new_permissions)


def downgrade() -> None:
    conn = op.get_bind()
    names = [p["p_name"] for p in _PERMISSIONS]
    conn.execute(
        sa.text('DELETE FROM "Permissions" WHERE p_name = ANY(:names)'),
        {"names": names},
    )
