"""
Script: seed_permissions.py

Inserts all RBAC permissions into the Permissions table.
Idempotent: skips permissions that already exist (by p_name).

Usage:
    python utils/seed_permissions.py
"""

import sys
import os

# Ensure project root is in sys.path so 'app' package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from sqlalchemy import text
from app.core.database import async_session

_PERMISSIONS = [
    # ── AppUsers ──────────────────────────────────────────────────────────
    {"p_name": "AppUsers:Create", "p_description": "Crear nuevos usuarios del sistema", "p_module": "AppUsers"},
    {"p_name": "AppUsers:List",   "p_description": "Listar y buscar usuarios del sistema", "p_module": "AppUsers"},
    {"p_name": "AppUsers:GetOne", "p_description": "Obtener detalle de un usuario", "p_module": "AppUsers"},
    {"p_name": "AppUsers:Update", "p_description": "Actualizar datos de un usuario", "p_module": "AppUsers"},
    {"p_name": "AppUserPermissions:Vinculate", "p_description": "Vincular/desvincular permisos a roles", "p_module": "AppUsers"},

    # ── Permissions ───────────────────────────────────────────────────────
    {"p_name": "Permissions:Read",  "p_description": "Listar y consultar permisos", "p_module": "Permissions"},
    {"p_name": "Permissions:Write", "p_description": "Crear, editar y eliminar permisos", "p_module": "Permissions"},

    # ── Rols ──────────────────────────────────────────────────────────────
    {"p_name": "Rols:Read",   "p_description": "Listar y consultar roles", "p_module": "Rols"},
    {"p_name": "Rols:Create", "p_description": "Crear nuevos roles", "p_module": "Rols"},
    {"p_name": "Rols:Update", "p_description": "Actualizar roles existentes", "p_module": "Rols"},
    {"p_name": "Rols:GetOne", "p_description": "Obtener detalle de un rol con sus permisos", "p_module": "Rols"},

    # ── Patients ──────────────────────────────────────────────────────────
    {"p_name": "Patients:Create", "p_description": "Crear nuevos pacientes", "p_module": "Patients"},
    {"p_name": "Patients:List",   "p_description": "Listar y buscar pacientes", "p_module": "Patients"},
    {"p_name": "Patients:GetOne", "p_description": "Obtener detalle de un paciente", "p_module": "Patients"},
    {"p_name": "Patients:Update", "p_description": "Actualizar datos de un paciente", "p_module": "Patients"},

    # ── Orders ────────────────────────────────────────────────────────────
    {"p_name": "Orders:Create",       "p_description": "Crear órdenes de laboratorio", "p_module": "Orders"},
    {"p_name": "Orders:List",         "p_description": "Listar y buscar órdenes", "p_module": "Orders"},
    {"p_name": "Orders:GetOne",       "p_description": "Obtener detalle básico de una orden", "p_module": "Orders"},
    {"p_name": "Orders:GetDetails",   "p_description": "Obtener detalle completo de una orden", "p_module": "Orders"},
    {"p_name": "Orders:GetFullDetails","p_description": "Obtener detalle completo con resultados", "p_module": "Orders"},
    {"p_name": "Orders:Update",       "p_description": "Actualizar datos de una orden", "p_module": "Orders"},
    {"p_name": "Orders:Edit",         "p_description": "Editar campos específicos de una orden", "p_module": "Orders"},
    {"p_name": "Orders:CancelStudies","p_description": "Cancelar estudios de una orden", "p_module": "Orders"},
    {"p_name": "Orders:GetNextNumber","p_description": "Obtener el siguiente número de orden", "p_module": "Orders"},
    {"p_name": "Orders:GetEvolutionChart","p_description": "Obtener gráfico de evolución de órdenes", "p_module": "Orders"},

    # ── Billing ───────────────────────────────────────────────────────────
    {"p_name": "Billing:Create", "p_description": "Crear facturas", "p_module": "Billing"},
    {"p_name": "Billing:List",   "p_description": "Listar facturas", "p_module": "Billing"},
    {"p_name": "Billing:GetOne", "p_description": "Obtener detalle de una factura", "p_module": "Billing"},
    {"p_name": "Billing:Update", "p_description": "Actualizar una factura", "p_module": "Billing"},
    {"p_name": "Billing:Delete", "p_description": "Eliminar una factura", "p_module": "Billing"},

    # ── Analyzers ─────────────────────────────────────────────────────────
    {"p_name": "Analyzers:CreateGroup",  "p_description": "Crear grupos de analizadores", "p_module": "Analyzers"},
    {"p_name": "Analyzers:ListGroups",   "p_description": "Listar grupos de analizadores", "p_module": "Analyzers"},
    {"p_name": "Analyzers:GetGroup",     "p_description": "Obtener detalle de un grupo de analizadores", "p_module": "Analyzers"},
    {"p_name": "Analyzers:UpdateGroup",  "p_description": "Actualizar un grupo de analizadores", "p_module": "Analyzers"},
    {"p_name": "Analyzers:DeleteGroup",  "p_description": "Eliminar un grupo de analizadores", "p_module": "Analyzers"},
    {"p_name": "Analyzers:Create",       "p_description": "Crear analizadores", "p_module": "Analyzers"},
    {"p_name": "Analyzers:List",         "p_description": "Listar analizadores", "p_module": "Analyzers"},
    {"p_name": "Analyzers:GetOne",       "p_description": "Obtener detalle de un analizador", "p_module": "Analyzers"},
    {"p_name": "Analyzers:Update",       "p_description": "Actualizar un analizador", "p_module": "Analyzers"},
    {"p_name": "Analyzers:Delete",       "p_description": "Eliminar un analizador", "p_module": "Analyzers"},
    {"p_name": "Analyzers:CreateDetail", "p_description": "Crear detalles de analizadores", "p_module": "Analyzers"},
    {"p_name": "Analyzers:ListDetails",  "p_description": "Listar detalles de analizadores", "p_module": "Analyzers"},
    {"p_name": "Analyzers:GetDetail",    "p_description": "Obtener detalle de un ítem de analizador", "p_module": "Analyzers"},
    {"p_name": "Analyzers:UpdateDetail", "p_description": "Actualizar detalle de analizador", "p_module": "Analyzers"},
    {"p_name": "Analyzers:DeleteDetail", "p_description": "Eliminar detalle de analizador", "p_module": "Analyzers"},

    # ── Enterprises ───────────────────────────────────────────────────────
    {"p_name": "Enterprises:Create",      "p_description": "Crear empresas", "p_module": "Enterprises"},
    {"p_name": "Enterprises:List",        "p_description": "Listar empresas", "p_module": "Enterprises"},
    {"p_name": "Enterprises:GetOne",      "p_description": "Obtener detalle de una empresa", "p_module": "Enterprises"},
    {"p_name": "Enterprises:Update",      "p_description": "Actualizar una empresa", "p_module": "Enterprises"},
    {"p_name": "Enterprises:GetContracts","p_description": "Obtener contratos de una empresa", "p_module": "Enterprises"},

    # ── Headquarters ──────────────────────────────────────────────────────
    {"p_name": "Headquarters:Create", "p_description": "Crear sedes", "p_module": "Headquarters"},
    {"p_name": "Headquarters:List",   "p_description": "Listar sedes", "p_module": "Headquarters"},
    {"p_name": "Headquarters:GetOne", "p_description": "Obtener detalle de una sede", "p_module": "Headquarters"},
    {"p_name": "Headquarters:Update", "p_description": "Actualizar una sede", "p_module": "Headquarters"},
    {"p_name": "Headquarters:Delete", "p_description": "Eliminar una sede", "p_module": "Headquarters"},

    # ── Locations ─────────────────────────────────────────────────────────
    {"p_name": "Locations:List",   "p_description": "Listar ubicaciones", "p_module": "Locations"},
    {"p_name": "Locations:GetOne", "p_description": "Obtener detalle de una ubicación", "p_module": "Locations"},

    # ── Masters ───────────────────────────────────────────────────────────
    {"p_name": "Masters:Read",                   "p_description": "Consultar datos maestros", "p_module": "Masters"},
    {"p_name": "Masters:CreateTechnique",        "p_description": "Crear técnicas", "p_module": "Masters"},
    {"p_name": "Masters:UpdateTechnique",        "p_description": "Actualizar técnicas", "p_module": "Masters"},
    {"p_name": "Masters:CreateWorkGroup",        "p_description": "Crear grupos de trabajo", "p_module": "Masters"},
    {"p_name": "Masters:UpdateWorkGroup",        "p_description": "Actualizar grupos de trabajo", "p_module": "Masters"},
    {"p_name": "Masters:CreateReferralLocation", "p_description": "Crear ubicaciones de referencia", "p_module": "Masters"},
    {"p_name": "Masters:UpdateReferralLocation", "p_description": "Actualizar ubicaciones de referencia", "p_module": "Masters"},

    # ── TestsLab ──────────────────────────────────────────────────────────
    {"p_name": "TestsLab:Create",              "p_description": "Crear pruebas de laboratorio", "p_module": "TestsLab"},
    {"p_name": "TestsLab:List",                "p_description": "Listar pruebas de laboratorio", "p_module": "TestsLab"},
    {"p_name": "TestsLab:GetOne",              "p_description": "Obtener detalle de una prueba", "p_module": "TestsLab"},
    {"p_name": "TestsLab:Update",              "p_description": "Actualizar una prueba", "p_module": "TestsLab"},
    {"p_name": "TestsLab:Delete",              "p_description": "Eliminar una prueba", "p_module": "TestsLab"},
    {"p_name": "TestsLab:ManageRanges",        "p_description": "Gestionar rangos de referencia de pruebas", "p_module": "TestsLab"},
    {"p_name": "TestsLab:ManageReferenceValues","p_description": "Gestionar valores de referencia de pruebas", "p_module": "TestsLab"},

    # ── StudiesLab ────────────────────────────────────────────────────────
    {"p_name": "StudiesLab:Create",      "p_description": "Crear estudios de laboratorio", "p_module": "StudiesLab"},
    {"p_name": "StudiesLab:List",        "p_description": "Listar estudios de laboratorio", "p_module": "StudiesLab"},
    {"p_name": "StudiesLab:GetOne",      "p_description": "Obtener detalle de un estudio", "p_module": "StudiesLab"},
    {"p_name": "StudiesLab:Update",      "p_description": "Actualizar un estudio", "p_module": "StudiesLab"},
    {"p_name": "StudiesLab:ManageTests", "p_description": "Gestionar pruebas de un estudio", "p_module": "StudiesLab"},

    # ── Tariffs ───────────────────────────────────────────────────────────
    {"p_name": "Tariffs:Create",        "p_description": "Crear tarifas", "p_module": "Tariffs"},
    {"p_name": "Tariffs:List",          "p_description": "Listar tarifas", "p_module": "Tariffs"},
    {"p_name": "Tariffs:GetOne",        "p_description": "Obtener detalle de una tarifa", "p_module": "Tariffs"},
    {"p_name": "Tariffs:Update",        "p_description": "Actualizar una tarifa", "p_module": "Tariffs"},
    {"p_name": "Tariffs:Delete",        "p_description": "Eliminar una tarifa", "p_module": "Tariffs"},
    {"p_name": "Tariffs:ManageDetails", "p_description": "Gestionar detalles de una tarifa", "p_module": "Tariffs"},

    # ── Contracts ─────────────────────────────────────────────────────────
    {"p_name": "Contracts:Create",      "p_description": "Crear contratos", "p_module": "Contracts"},
    {"p_name": "Contracts:List",        "p_description": "Listar contratos", "p_module": "Contracts"},
    {"p_name": "Contracts:GetOne",      "p_description": "Obtener detalle de un contrato", "p_module": "Contracts"},
    {"p_name": "Contracts:Update",      "p_description": "Actualizar un contrato", "p_module": "Contracts"},
    {"p_name": "Contracts:LinkTariff",  "p_description": "Vincular tarifa a contrato", "p_module": "Contracts"},
    {"p_name": "Contracts:UnlinkTariff","p_description": "Desvincular tarifa de contrato", "p_module": "Contracts"},

    # ── Reports ───────────────────────────────────────────────────────────
    {"p_name": "Reports:GenerateReport","p_description": "Generar reportes PDF de resultados", "p_module": "Reports"},
    {"p_name": "Reports:Dashboard",     "p_description": "Ver estadísticas del dashboard", "p_module": "Reports"},
    {"p_name": "Reports:Kpis",          "p_description": "Ver KPIs del sistema", "p_module": "Reports"},

    # ── Samples ───────────────────────────────────────────────────────────
    {"p_name": "Samples:Create", "p_description": "Crear tipos de muestra", "p_module": "Samples"},
    {"p_name": "Samples:List",   "p_description": "Listar tipos de muestra", "p_module": "Samples"},
    {"p_name": "Samples:GetOne", "p_description": "Obtener detalle de un tipo de muestra", "p_module": "Samples"},
    {"p_name": "Samples:Update", "p_description": "Actualizar un tipo de muestra", "p_module": "Samples"},
    {"p_name": "Samples:Delete", "p_description": "Eliminar un tipo de muestra", "p_module": "Samples"},

    # ── Requests ──────────────────────────────────────────────────────────
    {"p_name": "Requests:Create",      "p_description": "Crear solicitudes de ingreso", "p_module": "Requests"},
    {"p_name": "Requests:List",        "p_description": "Listar solicitudes de ingreso", "p_module": "Requests"},
    {"p_name": "Requests:GetOne",      "p_description": "Obtener detalle de una solicitud", "p_module": "Requests"},
    {"p_name": "Requests:Update",      "p_description": "Actualizar una solicitud de ingreso", "p_module": "Requests"},
    {"p_name": "Requests:Delete",      "p_description": "Eliminar una solicitud de ingreso", "p_module": "Requests"},
    {"p_name": "Requests:CreateOrder", "p_description": "Crear orden desde solicitud de ingreso", "p_module": "Requests"},

    # ── Traces ────────────────────────────────────────────────────────────
    {"p_name": "Traces:Read", "p_description": "Consultar trazabilidad de órdenes y pruebas", "p_module": "Traces"},

    # ── Laboratories ──────────────────────────────────────────────────────
    {"p_name": "Laboratories:BulkUpdate",    "p_description": "Actualización masiva de resultados de laboratorio", "p_module": "Laboratories"},
    {"p_name": "Laboratories:Invalidate",    "p_description": "Desvalidar resultados de laboratorio", "p_module": "Laboratories"},
    {"p_name": "Laboratories:Validate",      "p_description": "Validar resultados de laboratorio", "p_module": "Laboratories"},
    {"p_name": "Laboratories:ClearResults",  "p_description": "Limpiar resultados de laboratorio", "p_module": "Laboratories"},
    {"p_name": "Laboratories:UpdateState",   "p_description": "Cambiar estado de estudios en órdenes", "p_module": "Laboratories"},
    {"p_name": "Laboratories:ManageGraphics","p_description": "Subir y vincular imágenes a resultados", "p_module": "Laboratories"},

    # ── Interfaces ────────────────────────────────────────────────────────
    {"p_name": "Interfaces:Create",        "p_description": "Crear interfaces REST", "p_module": "Interfaces"},
    {"p_name": "Interfaces:List",          "p_description": "Listar interfaces REST", "p_module": "Interfaces"},
    {"p_name": "Interfaces:GetOne",        "p_description": "Obtener detalle de una interfaz REST", "p_module": "Interfaces"},
    {"p_name": "Interfaces:Update",        "p_description": "Actualizar una interfaz REST", "p_module": "Interfaces"},
    {"p_name": "Interfaces:Delete",        "p_description": "Eliminar una interfaz REST", "p_module": "Interfaces"},
    {"p_name": "Interfaces:ManageDetails", "p_description": "Gestionar detalles de interfaces REST", "p_module": "Interfaces"},

    # ── Cities ────────────────────────────────────────────────────────────
    {"p_name": "Cities:List",   "p_description": "Listar ciudades", "p_module": "Cities"},
    {"p_name": "Cities:GetOne", "p_description": "Obtener detalle de una ciudad", "p_module": "Cities"},
]


async def seed():
    async with async_session() as db:
        # Fetch existing permission names
        result = await db.execute(text("SELECT p_name FROM \"Permissions\""))
        existing = {row[0] for row in result.fetchall()}

        to_insert = [p for p in _PERMISSIONS if p["p_name"] not in existing]

        if not to_insert:
            print("✓ All permissions already exist. Nothing to insert.")
            return

        for perm in to_insert:
            await db.execute(
                text(
                    'INSERT INTO "Permissions" (p_name, p_description, p_module) '
                    "VALUES (:p_name, :p_description, :p_module)"
                ),
                perm,
            )

        await db.commit()
        print(f"✓ Inserted {len(to_insert)} new permissions.")
        for p in to_insert:
            print(f"  + {p['p_name']}")


if __name__ == "__main__":
    asyncio.run(seed())
