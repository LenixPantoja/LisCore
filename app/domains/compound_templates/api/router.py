from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.domains.compound_templates.api.schemas import (
    CompoundTemplateCreate,
    CompoundTemplateUpdate,
    CompoundTemplateResponse,
    CompoundTemplatePaginatedResponse,
    TestCompoundTemplateLinkCreate,
    TestCompoundTemplateLinkUpdate,
    TestCompoundTemplateLinkResponse,
)
from app.domains.compound_templates.application.use_cases.compound_template_use_cases import (
    create_template,
    list_templates,
    get_template,
    update_template,
    delete_template,
    add_test_to_template,
    get_template_test_links,
    update_test_link,
    remove_test_from_template,
    get_templates_for_test,
)

router = APIRouter(redirect_slashes=False)


# ── CRUD Templates ─────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=CompoundTemplateResponse,
    dependencies=[Depends(require_permission("CompoundTemplates:Create"))],
)
async def create(body: CompoundTemplateCreate, db: AsyncSession = Depends(get_db)):
    return await create_template(db, body.model_dump())


@router.get(
    "",
    response_model=CompoundTemplatePaginatedResponse,
    dependencies=[Depends(require_permission("CompoundTemplates:List"))],
)
async def list_all(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    return await list_templates(db, skip, limit, search, active_only)


@router.get(
    "/{ct_id}",
    response_model=CompoundTemplateResponse,
    dependencies=[Depends(require_permission("CompoundTemplates:GetOne"))],
)
async def get_one(ct_id: int, db: AsyncSession = Depends(get_db)):
    return await get_template(db, ct_id)


@router.put(
    "/{ct_id}",
    response_model=CompoundTemplateResponse,
    dependencies=[Depends(require_permission("CompoundTemplates:Update"))],
)
async def update(ct_id: int, body: CompoundTemplateUpdate, db: AsyncSession = Depends(get_db)):
    return await update_template(db, ct_id, body.model_dump(exclude_unset=True))


@router.delete(
    "/{ct_id}",
    dependencies=[Depends(require_permission("CompoundTemplates:Delete"))],
)
async def delete(ct_id: int, db: AsyncSession = Depends(get_db)):
    return await delete_template(db, ct_id)


# ── N:M Links (Template ↔ Tests) ───────────────────────────────────────────────

@router.post(
    "/{ct_id}/tests",
    response_model=TestCompoundTemplateLinkResponse,
    dependencies=[Depends(require_permission("CompoundTemplates:ManageLinks"))],
)
async def link_test(ct_id: int, body: TestCompoundTemplateLinkCreate, db: AsyncSession = Depends(get_db)):
    return await add_test_to_template(db, ct_id, body.model_dump())


@router.get(
    "/{ct_id}/tests",
    response_model=list[TestCompoundTemplateLinkResponse],
    dependencies=[Depends(require_permission("CompoundTemplates:GetOne"))],
)
async def get_linked_tests(ct_id: int, db: AsyncSession = Depends(get_db)):
    return await get_template_test_links(db, ct_id)


@router.patch(
    "/tests/{tct_id}",
    response_model=TestCompoundTemplateLinkResponse,
    dependencies=[Depends(require_permission("CompoundTemplates:ManageLinks"))],
)
async def update_link(tct_id: int, body: TestCompoundTemplateLinkUpdate, db: AsyncSession = Depends(get_db)):
    return await update_test_link(db, tct_id, body.model_dump(exclude_unset=True))


@router.delete(
    "/tests/{tct_id}",
    dependencies=[Depends(require_permission("CompoundTemplates:ManageLinks"))],
)
async def unlink_test(tct_id: int, db: AsyncSession = Depends(get_db)):
    return await remove_test_from_template(db, tct_id)


# ── Query templates by test ────────────────────────────────────────────────────

@router.get(
    "/by-test/{test_id}",
    response_model=list[CompoundTemplateResponse],
    dependencies=[Depends(require_permission("CompoundTemplates:List"))],
)
async def list_by_test(test_id: int, db: AsyncSession = Depends(get_db)):
    return await get_templates_for_test(db, test_id)