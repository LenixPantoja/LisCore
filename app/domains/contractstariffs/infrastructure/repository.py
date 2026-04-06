from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.domains.contractstariffs.domain.models import Tariff, TariffDetail, Contract, ContractTariff
from datetime import date

class ContractTariffRepository:
    # --- Tariffs ---
    @staticmethod
    async def create_tariff(db: AsyncSession, data: dict) -> Tariff:
        new_tariff = Tariff(**data, t_created_at=date.today(), t_update_at=date.today())
        db.add(new_tariff)
        await db.commit()

        # Re-obtenemos con selectinload para cargar 'details' y evitar el error MissingGreenlet en la serialización
        stmt = select(Tariff).filter(Tariff.t_id == new_tariff.t_id).options(selectinload(Tariff.details))
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_tariffs(db: AsyncSession) -> List[Tariff]:
        result = await db.execute(select(Tariff).options(selectinload(Tariff.details)))
        return result.scalars().all()

    @staticmethod
    async def add_tariff_detail(db: AsyncSession, tariff_id: int, detail_data: dict) -> TariffDetail:
        detail = TariffDetail(**detail_data, td_tariff_id=tariff_id)
        db.add(detail)
        await db.commit()
        await db.refresh(detail)
        return detail

    # --- Contracts ---
    @staticmethod
    async def create_contract(db: AsyncSession, data: dict) -> Contract:
        new_contract = Contract(**data, co_created_at=date.today(), co_updated_at=date.today())
        db.add(new_contract)
        await db.commit()
        await db.refresh(new_contract)
        return new_contract

    @staticmethod
    async def get_contracts(db: AsyncSession, enterprise_id: Optional[int] = None) -> List[Contract]:
        query = select(Contract)
        if enterprise_id:
            query = query.filter(Contract.co_enterprise_id == enterprise_id)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_contract_by_id(db: AsyncSession, contract_id: int) -> Optional[Contract]:
        return await db.get(Contract, contract_id)

    # --- Linking ---
    @staticmethod
    async def link_tariff_to_contract(db: AsyncSession, data: dict) -> ContractTariff:
        link = ContractTariff(**data)
        db.add(link)
        await db.commit()

        # Cargamos la relación 'tariff' y sus respectivos 'details' para la respuesta
        stmt = (
            select(ContractTariff)
            .filter(ContractTariff.ct_id == link.ct_id)
            .options(selectinload(ContractTariff.tariff).selectinload(Tariff.details))
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_contract_tariffs(db: AsyncSession, contract_id: int) -> List[ContractTariff]:
        result = await db.execute(
            select(ContractTariff)
            .filter(ContractTariff.ct_contract_id == contract_id)
            .options(selectinload(ContractTariff.tariff).selectinload(Tariff.details))
        )
        return result.scalars().all()