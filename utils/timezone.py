"""
Timezone utility for Bogota (America/Bogota)
"""
from datetime import datetime
import pytz

BOGOTA_TZ = pytz.timezone("America/Bogota")

def get_bogota_now() -> datetime:
    """Get current datetime in Bogota timezone (naive, for database storage)"""
    return datetime.now(BOGOTA_TZ).replace(tzinfo=None)

def to_bogota(dt: datetime) -> datetime:
    """Convert a datetime to Bogota timezone"""
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(BOGOTA_TZ)
