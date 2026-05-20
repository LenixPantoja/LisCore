from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "CorelisDB"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:4200", "http://localhost:3000", "http://localhost:8080","*"]

    # Database connection from .env
    DB_HOST: str
    DB_PORT: str
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # Database pool settings
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600

    # Timezone
    TIME_ZONE: str = "America/Bogota"

    # JWT Settings
    SECRET_KEY: str = ">8)d0gDf\$GD9`}ym9%qrU6=p{C=4CPo>t1w5V<P=uoe&YegJ"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # MinIO
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool
    MINIO_GRAPHICS_BUCKET: str
    MINIO_SIGNATURES_BUCKET: str
    MINIO_PRESIGNED_EXPIRES_HOURS: int

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
