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
    GradillaPaginatedResponse, GradillaPosicionResponse, GradillaDiscardResponse, SampleDiscardResponse,
    SamplesDiscardRequest, SamplesDiscardResponse,
    TipoGradillaCreate, TipoGradillaUpdate, TipoGradillaResponse, TipoGradillaPaginatedResponse,
    AutoStoreRequest, ManualStoreRequest, ReleasePositionRequest,
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
    discard_rack, discard_rack_by_work_group, discard_sample, discard_samples,
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
    discarted: Optional[bool] = Query(
        None, description="Filtrar por estado de descarte: false = pendientes por descartar, true = ya descartadas"
    ),
    db: AsyncSession = Depends(get_db),
):
    return await list_racks(db, s_id, skip, limit, search, discarted)


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
    description="Elimina la gradilla y sus posiciones. Falla con 422 si todavía tiene muestras almacenadas.",
    dependencies=[Depends(require_permission("Seroteca:ManageRacks"))],
)
async def delete_rack_endpoint(
    g_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await delete_rack(db, g_id, current_user.usr_id)


@router.post(
    "/racks/{g_id}/discard",
    response_model=GradillaDiscardResponse,
    summary="Descartar las muestras de una gradilla",
    description=(
        "Descarta (so_state=4) las muestras de la gradilla cuyos estudios ya están "
        "completamente procesados, registrando un SamplesLog por cada una con el "
        "usuario (tomado del token), la hora y la ubicación de la seroteca. Las "
        "muestras con estudios pendientes (considerando is_required de "
        "StudiesTestDetail) se OMITEN y se reportan en `pending_samples`, sin "
        "bloquear el descarte de las demás. La gradilla solo queda marcada como "
        "completamente descartada (g_discarted=1, `fully_discarded=true`) cuando no "
        "le queda ninguna muestra pendiente."
    ),
    dependencies=[Depends(require_permission("Seroteca:DiscardRack"))],
)
async def discard_rack_endpoint(
    g_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await discard_rack(db, g_id, current_user.usr_id)


@router.post(
    "/racks/{g_id}/discard/work-group/{work_group_id}",
    response_model=GradillaDiscardResponse,
    summary="Descartar las muestras de una gradilla que pertenecen a un grupo de trabajo",
    description=(
        "Descarta (so_state=4), dentro de la gradilla indicada, solo las muestras "
        "cuyos estudios correspondan al grupo de trabajo indicado y que ya estén "
        "completamente procesadas. Las muestras de ese grupo con estudios "
        "pendientes se OMITEN y se reportan en `pending_samples`. La gradilla solo "
        "queda marcada como completamente descartada (`fully_discarded=true`) si, "
        "al terminar, no queda ninguna muestra activa pendiente en TODA la "
        "gradilla (no solo en el grupo indicado)."
    ),
    dependencies=[Depends(require_permission("Seroteca:DiscardRack"))],
)
async def discard_rack_by_work_group_endpoint(
    g_id: int,
    work_group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await discard_rack_by_work_group(db, g_id, work_group_id, current_user.usr_id)


@router.post(
    "/racks/{g_id}/discard/sample/{so_id}",
    response_model=SampleDiscardResponse,
    summary="Descartar una única muestra de una gradilla",
    description=(
        "Descarta (so_state=4) una sola muestra (por so_id) almacenada en la "
        "gradilla indicada, siempre que ya tenga todos sus estudios procesados. "
        "Si la muestra tiene estudios pendientes, retorna 422 indicando cuáles "
        "faltan y no la descarta."
    ),
    dependencies=[Depends(require_permission("Seroteca:DiscardRack"))],
)
async def discard_sample_endpoint(
    g_id: int,
    so_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await discard_sample(db, g_id, so_id, current_user.usr_id)


@router.post(
    "/racks/{g_id}/discard/samples",
    response_model=SamplesDiscardResponse,
    summary="Descartar una lista de muestras de una gradilla",
    description=(
        "Descarta (so_state=4) una lista de muestras (por so_id) almacenadas en la "
        "gradilla indicada, siempre que ya tengan todos sus estudios procesados. Las "
        "que tengan estudios pendientes se OMITEN y se reportan en `pending_samples`, "
        "sin bloquear el descarte de las demás. Los so_id que no correspondan a una "
        "muestra activa de esta gradilla se reportan en `samples_not_found`."
    ),
    dependencies=[Depends(require_permission("Seroteca:DiscardRack"))],
)
async def discard_samples_endpoint(
    g_id: int,
    body: SamplesDiscardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await discard_samples(db, g_id, body.so_ids, current_user.usr_id)


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
    body: ReleasePositionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    return await release_position(db, gp_id, current_user.usr_id, body.justification)


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
