from fastapi import APIRouter
from app.domains.patients.api.router import router as patients_router
from app.domains.users.api.router import router as users_router
from app.domains.enterprises.api.router import router as enterprises_router
from app.domains.masters.api.router import router as masters_router
from app.domains.Headquarters.api.router import router as headquarters_router
from app.domains.contractstariffs.api.router import router as contractstariffs_router
from app.domains.samples.api.router import router as samples_router
from app.domains.testslabs.api.router import router as testslabs_router
from app.domains.studieslab.api.router import router as studieslab_router
from app.domains.orders.api.router import router as orders_router
from app.domains.analyzers.api.router import router as analyzers_router
from app.domains.interfaces.api.router import router as interfaces_router
from app.domains.locations.api.router import router as locations_router
from app.domains.cities.api.router import router as cities_router
from app.domains.laboratories.api.router import router as laboratories_router
from app.domains.reports.api.router import router as reports_router
from app.domains.billing.api.router import router as billing_router
from app.domains.requests.api.router import router as requests_router
from app.integrations.InterfazDG.router import router as interfaz_dg_router
from app.domains.traces.api.router import router as traces_router
from app.domains.seroteca.api.router import router as seroteca_router
from app.domains.kpis.api.router import router as kpis_router
from app.domains.annexes.api.router import router as annexes_router

api_router = APIRouter()

api_router.include_router(patients_router, prefix="/patients", tags=["Patients"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(enterprises_router, prefix="/enterprises", tags=["Enterprises"])
api_router.include_router(masters_router, prefix="/masters", tags=["Masters"])
api_router.include_router(headquarters_router, prefix="/headquarters", tags=["Headquarters"])
api_router.include_router(contractstariffs_router, prefix="/contracts-tariffs", tags=["Contracts & Tariffs"])
api_router.include_router(samples_router, prefix="/samples", tags=["Samples"])
api_router.include_router(testslabs_router, prefix="/tests-lab", tags=["Tests Lab"])
api_router.include_router(studieslab_router, prefix="/studies-lab", tags=["Studies Lab"])
api_router.include_router(orders_router, prefix="/orders", tags=["Orders"])
api_router.include_router(analyzers_router, prefix="/analyzers", tags=["Analyzers"])
api_router.include_router(interfaces_router, prefix="/interfaces", tags=["Interfaces"])
api_router.include_router(locations_router, prefix="/locations", tags=["Locations"])
api_router.include_router(cities_router, prefix="/cities", tags=["Cities"])
api_router.include_router(laboratories_router, prefix="/laboratories", tags=["Laboratories"])
api_router.include_router(reports_router, prefix="/reports", tags=["Reports"])
api_router.include_router(billing_router, prefix="/billing", tags=["Billing"])
api_router.include_router(requests_router, prefix="/inbound-orders", tags=["Inbound Orders"])
api_router.include_router(interfaz_dg_router, prefix="/Dinamica/Laboratorio", tags=["InterfazDG"])
api_router.include_router(traces_router, prefix="/traces", tags=["Traces"])
api_router.include_router(seroteca_router)
api_router.include_router(kpis_router, prefix="/kpis", tags=["KPIs"])
api_router.include_router(annexes_router, prefix="/annexes", tags=["Annexed Results"])
