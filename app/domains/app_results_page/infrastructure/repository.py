from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domains.app_results_page.domain.models import AppResultsPage
from utils.timezone import get_bogota_now


class AppResultsPageRepository:
    @staticmethod
    async def create(db: AsyncSession, data: dict) -> AppResultsPage:
        new_user = AppResultsPage(**data)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user

    @staticmethod
    async def get_by_origin(db: AsyncSession, origin_id: int, access_type: int) -> Optional[AppResultsPage]:
        result = await db.execute(
            select(AppResultsPage).filter(
                AppResultsPage.arp_user_origin_id == origin_id,
                AppResultsPage.arp_user_access_type == access_type,
            )
        )
        return result.scalars().first()

    @staticmethod
    async def get_by_login(db: AsyncSession, login: str) -> Optional[AppResultsPage]:
        result = await db.execute(
            select(AppResultsPage).filter(AppResultsPage.arp_user_login == login)
        )
        return result.scalars().first()

    @staticmethod
    async def get_by_id(db: AsyncSession, arp_user_id: int) -> Optional[AppResultsPage]:
        result = await db.execute(
            select(AppResultsPage).filter(AppResultsPage.arp_user_id == arp_user_id)
        )
        return result.scalars().first()

    @staticmethod
    async def touch_last_access(db: AsyncSession, arp_user: AppResultsPage) -> AppResultsPage:
        arp_user.arp_last_access = get_bogota_now()
        await db.commit()
        await db.refresh(arp_user)
        return arp_user
