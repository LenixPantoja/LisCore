from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.billing.domain.models import Invoice


async def generate_invoice_number(db: AsyncSession, prefix: str) -> str:
    """
    Generates the next invoice number with format: {PREFIX}{sequence:04d}
    Example: SEDE0001, SEDE0002, ...
    If prefix is empty, uses format: INV0001, INV0002, ...
    """
    safe_prefix = prefix.strip() if prefix else "INV"

    stmt = (
        select(Invoice.inv_number)
        .where(Invoice.inv_number.like(f"{safe_prefix}%"))
        .order_by(Invoice.inv_id.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    last_number = result.scalar()

    next_seq = 1
    if last_number:
        suffix = last_number[len(safe_prefix):]
        try:
            next_seq = int(suffix) + 1
        except ValueError:
            next_seq = 1

    return f"{safe_prefix}{str(next_seq).zfill(4)}"
