from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
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
    async def get_diagnoses_filtered(
        db: AsyncSession, 
        skip: int, 
        limit: int, 
        code: Optional[str] = None, 
        description: Optional[str] = None
    ) -> List[Diagnosis]:
        query = select(Diagnosis)
        if code:
            query = query.filter(Diagnosis.diag_code.ilike(f"%{code}%"))
        if description:
            query = query.filter(Diagnosis.d_description.ilike(f"%{description}%"))
        
        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()
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