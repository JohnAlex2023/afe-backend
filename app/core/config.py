from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    # --- Core ---
    environment: str = Field("development", env="ENVIRONMENT")  

    # --- Seguridad / JWT ---
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field("HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(60, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # --- Base de datos ---
    database_url: str = Field(..., env="DATABASE_URL")

    # --- CORS ---
    backend_cors_origins: List[str] | str = Field("", env="BACKEND_CORS_ORIGINS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
