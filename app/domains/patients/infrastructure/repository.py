from sqlalchemy.ext.asyncio import AsyncSession

class PatientRepository:

    @staticmethod
    async def create(data, db: AsyncSession):
        db.add(data)
        await db.commit()
        await db.refresh(data)
        return data