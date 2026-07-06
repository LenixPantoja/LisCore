from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.domains.users.infrastructure.models import AppUser

from app.domains.seroteca.api.schemas import (
    SampleLogCreate, SampleLogPaginatedResponse,
    SerotecaCreate, SerotecaUpdate, SerotecaResponse, SerotecaPaginatedResponse,
    GradillaCreate, GradillaUpdate, GradillaResponse, GradillaWithPositionsResponse,
    GradillaPaginatedResponse, GradillaPosicionResponse,
    TipoGradillaCreate, TipoGradillaUpdate, TipoGradillaResponse, TipoGradillaPaginatedResponse,
    AutoStoreRequest, ManualStoreRequest,
)
from app.domains.seroteca.application.use_cases.tracking_use_cases import (
    log_sample_event,
    get_sample_history,
    auto_store_in_rack,
    manual_store_in_position,
    release_position,
)
from app.domains.seroteca.application.use_cases.seroteca_use_cases import (
    create_seroteca, get_seroteca, list_serotecas, update_seroteca, delete_seroteca,
    create_rack, get_rack, list_racks, update_rack, delete_rack,
    create_tipo_gradilla, get_tipo_gradilla, list_tipos_gradilla, update_tipo_gradilla, delete_tipo_gradilla,
    generate_gradilla_sticker,
)

router = APIRouter(prefix="/seroteca", tags=["Seroteca & Tracking"])


# ── Sample Tracking ───────────────────────────────────────────────────────────

@router.post(
    "/samples/track",
    response_model=None,
    dependencies=[Depends(require_permission("Tracking:Log"))],
)
async def track_sample(
    body: SampleLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await log_sample_event(
        db=db,
        barcode=body.barcode,
        state=body.log_state,
        user_id=current_user.usr_id,
        location_id=body.log_location_id,
        notes=body.log_observation,
    )


@router.get(
    "/samples/{barcode}/history",
    response_model=SampleLogPaginatedResponse,
    dependencies=[Depends(require_permission("Tracking:Read"))],
)
async def sample_history(
    barcode: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await get_sample_history(db, barcode, skip, limit)


# ── Serotecas ─────────────────────────────────────────────────────────────────

@router.post(
    "/serotecas",
    response_model=SerotecaResponse,
    dependencies=[Depends(require_permission("Seroteca:Create"))],
)
async def create(
    body: SerotecaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await create_seroteca(db, body.model_dump(), current_user.usr_id)


@router.get(
    "/serotecas",
    response_model=SerotecaPaginatedResponse,
    dependencies=[Depends(require_permission("Seroteca:List"))],
)
async def list_all(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    active_only: bool = Query(False),
    headquarter_id: Optional[int] = Query(None, description="Filtrar por ID de sede"),
    db: AsyncSession = Depends(get_db),
):
    return await list_serotecas(db, skip, limit, search, active_only, headquarter_id)


@router.get(
    "/serotecas/{s_id}",
    response_model=SerotecaResponse,
    dependencies=[Depends(require_permission("Seroteca:GetOne"))],
)
async def get_one(s_id: int, db: AsyncSession = Depends(get_db)):
    return await get_seroteca(db, s_id)


@router.patch(
    "/serotecas/{s_id}",
    response_model=SerotecaResponse,
    dependencies=[Depends(require_permission("Seroteca:Update"))],
)
async def update(
    s_id: int,
    body: SerotecaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await update_seroteca(db, s_id, body.model_dump(exclude_unset=True), current_user.usr_id)


@router.delete(
    "/serotecas/{s_id}",
    dependencies=[Depends(require_permission("Seroteca:Delete"))],
)
async def delete(
    s_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await delete_seroteca(db, s_id, current_user.usr_id)


# ── Gradillas ─────────────────────────────────────────────────────────────────

@router.post(
    "/serotecas/{s_id}/racks",
    response_model=GradillaResponse,
    dependencies=[Depends(require_permission("Seroteca:ManageRacks"))],
)
async def create_rack_endpoint(
    s_id: int,
    body: GradillaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    data = body.model_dump()
    data["g_seroteca_id"] = s_id
    data["g_created_by"] = current_user.usr_id
    return await create_rack(db, data, current_user.usr_id)


@router.get(
    "/serotecas/{s_id}/racks",
    response_model=GradillaPaginatedResponse,
    dependencies=[Depends(require_permission("Seroteca:ManageRacks"))],
)
async def list_racks_endpoint(
    s_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, description="Buscar por nombre de rack"),
    db: AsyncSession = Depends(get_db),
):
    return await list_racks(db, s_id, skip, limit, search)


@router.get(
    "/racks/{g_id}",
    response_model=GradillaWithPositionsResponse,
    dependencies=[Depends(require_permission("Seroteca:ManageRacks"))],
)
async def get_rack_endpoint(g_id: int, db: AsyncSession = Depends(get_db)):
    return await get_rack(db, g_id)


@router.patch(
    "/racks/{g_id}",
    response_model=GradillaResponse,
    dependencies=[Depends(require_permission("Seroteca:ManageRacks"))],
)
async def update_rack_endpoint(
    g_id: int,
    body: GradillaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await update_rack(db, g_id, body.model_dump(exclude_unset=True), current_user.usr_id)


@router.delete(
    "/racks/{g_id}",
    dependencies=[Depends(require_permission("Seroteca:ManageRacks"))],
)
async def delete_rack_endpoint(
    g_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await delete_rack(db, g_id, current_user.usr_id)


# ── Tipos de Gradilla ─────────────────────────────────────────────────────────

@router.post(
    "/tipos-gradilla",
    response_model=TipoGradillaResponse,
    dependencies=[Depends(require_permission("Seroteca:ManageRackTypes"))],
)
async def create_tipo_gradilla_endpoint(
    body: TipoGradillaCreate,
    db: AsyncSession = Depends(get_db),
):
    return await create_tipo_gradilla(db, body.model_dump())


@router.get(
    "/tipos-gradilla",
    response_model=TipoGradillaPaginatedResponse,
    dependencies=[Depends(require_permission("Seroteca:ManageRackTypes"))],
)
async def list_tipos_gradilla_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, description="Buscar por nombre de tipo"),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    return await list_tipos_gradilla(db, skip, limit, search, active_only)


@router.get(
    "/tipos-gradilla/{tg_id}",
    response_model=TipoGradillaResponse,
    dependencies=[Depends(require_permission("Seroteca:ManageRackTypes"))],
)
async def get_tipo_gradilla_endpoint(tg_id: int, db: AsyncSession = Depends(get_db)):
    return await get_tipo_gradilla(db, tg_id)


@router.patch(
    "/tipos-gradilla/{tg_id}",
    response_model=TipoGradillaResponse,
    dependencies=[Depends(require_permission("Seroteca:ManageRackTypes"))],
)
async def update_tipo_gradilla_endpoint(
    tg_id: int,
    body: TipoGradillaUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await update_tipo_gradilla(db, tg_id, body.model_dump(exclude_unset=True))


@router.delete(
    "/tipos-gradilla/{tg_id}",
    dependencies=[Depends(require_permission("Seroteca:ManageRackTypes"))],
)
async def delete_tipo_gradilla_endpoint(tg_id: int, db: AsyncSession = Depends(get_db)):
    return await delete_tipo_gradilla(db, tg_id)


# ── Storage operations ────────────────────────────────────────────────────────

@router.post(
    "/samples/store",
    response_model=GradillaPosicionResponse,
    dependencies=[Depends(require_permission("Seroteca:StoreSample"))],
)
async def auto_store(
    body: AutoStoreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await auto_store_in_rack(db, body.barcode, body.g_id, current_user.usr_id)


@router.post(
    "/positions/{gp_id}/store",
    response_model=GradillaPosicionResponse,
    dependencies=[Depends(require_permission("Seroteca:StoreSample"))],
)
async def manual_store(
    gp_id: int,
    body: ManualStoreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await manual_store_in_position(db, body.barcode, gp_id, current_user.usr_id)


@router.delete(
    "/positions/{gp_id}/release",
    response_model=GradillaPosicionResponse,
    dependencies=[Depends(require_permission("Seroteca:StoreSample"))],
)
async def release(
    gp_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await release_position(db, gp_id, current_user.usr_id)


# ── Gradilla Sticker ──────────────────────────────────────────────────────────

@router.get(
    "/racks/{g_id}/sticker",
    dependencies=[Depends(require_permission("Seroteca:ManageRacks"))],
)
async def get_gradilla_sticker(
    g_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Generate a ZPL + PDF sticker for a gradilla rack."""
    return await generate_gradilla_sticker(db, g_id)
