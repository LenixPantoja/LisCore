from typing import List, Optional, Tuple, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.domains.masters.domain.models import Country, Department, City, DocumentType, SexType, AfiliationType, Regime, Service, TypeLiability, Classification, Technique, WorkGroup, ReferralLocation, Diagnosis
from datetime import date

class MastersRepository:
    @staticmethod
    async def get_all_countries(db: AsyncSession) -> List[Country]:
        """
        Retrieves a list of all active countries.
        """
        result = await db.execute(
            select(Country).filter(Country.country_active == True)
        )
        return result.scalars().all()

    @staticmethod
    async def get_countries_paginated(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        active: Optional[bool] = None
    ) -> Tuple[Sequence[Country], int]:
        """Get countries with pagination"""
        query = select(Country)

        if search:
            query = query.filter(Country.name_country.ilike(f"%{search}%"))
        if active is not None:
            query = query.filter(Country.country_active == active)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(
            query.offset(skip).limit(limit).order_by(Country.id.asc())
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_departments_paginated(
        db: AsyncSession,
        country_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> Tuple[Sequence[Department], int]:
        """Get departments with pagination"""
        query = select(Department)

        if country_id is not None:
            query = query.filter(Department.d_country_id == country_id)
        if search:
            query = query.filter(Department.d_name_department.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(
            query.offset(skip).limit(limit).order_by(Department.d_id.asc())
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_cities_paginated(
        db: AsyncSession,
        department_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> Tuple[Sequence[City], int]:
        """Get cities with pagination"""
        query = select(City)

        if department_id is not None:
            query = query.filter(City.Department_id == department_id)
        if search:
            query = query.filter(City.city_name.ilike(f"%{search}%") | City.city_code.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(
            query.offset(skip).limit(limit).order_by(City.id.asc())
        )
        return result.scalars().all(), total

    # --- CRUD Genérico para nuevas tablas ---
    @staticmethod
    async def create_master(db: AsyncSession, model, data: dict):
        if hasattr(model, 'created_at'):
            data['created_at'] = date.today()
        if hasattr(model, 'updated_at'):
            data['updated_at'] = date.today()
        if hasattr(model, 'update_at'):
            data['update_at'] = date.today()
            
        new_item = model(**data)
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)
        return new_item

    @staticmethod
    async def get_all_master(db: AsyncSession, model):
        result = await db.execute(select(model))
        return result.scalars().all()

    @staticmethod
    async def get_master_by_id(db: AsyncSession, model, item_id: int):
        return await db.get(model, item_id)

    @staticmethod
    async def update_master(db: AsyncSession, model, item_id: int, data: dict):
        item = await db.get(model, item_id)
        if item:
            if hasattr(model, 'updated_at'):
                data['updated_at'] = date.today()
            if hasattr(model, 'update_at'):
                data['update_at'] = date.today()
                
            for key, value in data.items():
                setattr(item, key, value)
            await db.commit()
            await db.refresh(item)
        return item

    @staticmethod
    async def get_diagnoses_paginated(
        db: AsyncSession,
        skip: int,
        limit: int,
        code: Optional[str] = None,
        description: Optional[str] = None,
        search: Optional[str] = None
    ) -> Tuple[Sequence[Diagnosis], int]:
        """Get diagnoses with pagination"""
        query = select(Diagnosis)
        if search:
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    Diagnosis.diag_code.ilike(f"%{search}%"),
                    Diagnosis.d_description.ilike(f"%{search}%"),
                )
            )
        else:
            if code:
                query = query.filter(Diagnosis.diag_code.ilike(f"%{code}%"))
            if description:
                query = query.filter(Diagnosis.d_description.ilike(f"%{description}%"))

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(query.offset(skip).limit(limit).order_by(Diagnosis.diag_id.asc()))
        return result.scalars().all(), total
    @staticmethod
    async def get_all_document_types(db: AsyncSession) -> List[DocumentType]:
        result = await db.execute(select(DocumentType))
        return result.scalars().all()

    @staticmethod
    async def get_all_sex_types(db: AsyncSession) -> List[SexType]:
        result = await db.execute(select(SexType))
        return result.scalars().all()

    @staticmethod
    async def get_all_afiliation_types(db: AsyncSession) -> List[AfiliationType]:
        result = await db.execute(select(AfiliationType))
        return result.scalars().all()

    @staticmethod
    async def get_all_regimes(db: AsyncSession) -> List[Regime]:
        result = await db.execute(select(Regime))
        return result.scalars().all()

    @staticmethod
    async def get_all_services(db: AsyncSession) -> List[Service]:
        result = await db.execute(select(Service))
        return result.scalars().all()

    @staticmethod
    async def get_services_paginated(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        active: Optional[bool] = None
    ) -> Tuple[Sequence[Service], int]:
        """Get services with pagination"""
        query = select(Service)

        if search:
            query = query.filter(Service.name.ilike(f"%{search}%") | Service.code.ilike(f"%{search}%"))
        if active is not None:
            query = query.filter(Service.active == active)

        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        result = await db.execute(
            query.offset(skip).limit(limit).order_by(Service.id.asc())
        )
        return result.scalars().all(), total

    @staticmethod
    async def get_all_type_liabilities(db: AsyncSession) -> List[TypeLiability]:
        result = await db.execute(select(TypeLiability))
        return result.scalars().all()

    @staticmethod
    async def get_all_classifications(db: AsyncSession) -> List[Classification]:
        result = await db.execute(select(Classification))
        return result.scalars().all()
    @staticmethod
    async def get_departments_by_country_id(db: AsyncSession, country_id: int) -> List[Department]:
        """
        Retrieves a list of departments for a given country ID.
        """
        result = await db.execute(
            select(Department).filter(Department.d_country_id == country_id)
        )
        return result.scalars().all()

    @staticmethod
    async def get_cities_by_department_id(db: AsyncSession, department_id: int) -> List[City]:
        """
        Retrieves a list of cities for a given department ID.
        """
        result = await db.execute(
            select(City).filter(City.Department_id == department_id)
        )
        return result.scalars().all()

    # You might want to add methods for getting a single country, department, or city by ID
    # or for creating/updating these entities if needed in the future.