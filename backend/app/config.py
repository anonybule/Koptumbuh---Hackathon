from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://dev_admin:devpassword@localhost:5432/koptumbuh_dev"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Official SIMKOPDES Database
    SIMKOPDES_DB_HOST: str = "34.101.155.200"
    SIMKOPDES_DB_PORT: int = 5432
    SIMKOPDES_DB_NAME: str = "hackathon_2026"
    SIMKOPDES_DB_USER: str = "hackathon_participant_2026"
    SIMKOPDES_DB_PASSWORD: str = "*H4ck4thonK3men0P2026@"
    TEAM_PREFIX: str = "JasaAI"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minio_admin"
    MINIO_SECRET_KEY: str = "minio_password"
    MINIO_BUCKET_MEDIA: str = "koptumbuh-media"
    MINIO_BUCKET_EXPORTS: str = "koptumbuh-exports"
    MINIO_BUCKET_BACKUPS: str = "koptumbuh-backups"
    MINIO_SECURE: bool = False

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Evolution API
    EVOLUTION_API_URL: str = "http://evolution:8080"
    EVOLUTION_API_KEY: str = "koptumbuh-evolution-key"
    EVOLUTION_INSTANCE: str = "koptumbuh"
    WHATSAPP_VERIFY_TOKEN: str = "koptumbuh_webhook_secret"
    # Optional alias for Evolution webhook auth (used if EVOLUTION_API_KEY empty)
    WHATSAPP_API_KEY: str = ""

    # JWT
    JWT_SECRET_KEY: str = "hackathon-jasaai-2026"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000"]

    # Rate Limiting
    RATE_LIMIT_WEBHOOK: str = "60/minute"

    # Input Bounds
    MAX_TEXT_LENGTH: int = 4000
    MAX_AUDIO_SECONDS: int = 60
    MAX_MEDIA_SIZE_MB: int = 10
    MIN_PHOTO_CONFIDENCE: float = 0.7

    @property
    def SIMKOPDES_DB_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.SIMKOPDES_DB_USER}:{self.SIMKOPDES_DB_PASSWORD}"
            f"@{self.SIMKOPDES_DB_HOST}:{self.SIMKOPDES_DB_PORT}/{self.SIMKOPDES_DB_NAME}"
        )

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
