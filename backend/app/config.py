import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agencydesk"
    )
    jwt_secret: str = os.environ.get("JWT_SECRET", "dev-secret-change-in-prod")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24h, fine for a take-home


settings = Settings()
