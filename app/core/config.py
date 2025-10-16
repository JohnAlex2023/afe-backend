# app/core/config.py
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

    # --- Microsoft Graph (para envío de emails) ---
    graph_tenant_id: str = Field("", env="GRAPH_TENANT_ID")
    graph_client_id: str = Field("", env="GRAPH_CLIENT_ID")
    graph_client_secret: str = Field("", env="GRAPH_CLIENT_SECRET")
    graph_from_email: str = Field("notificacionrpa.auto@zentria.com.co", env="GRAPH_FROM_EMAIL")
    graph_from_name: str = Field("Sistema AFE - Notificaciones", env="GRAPH_FROM_NAME")

    # --- SMTP (fallback opcional) ---
    smtp_host: str = Field("smtp.gmail.com", env="SMTP_HOST")
    smtp_port: int = Field(587, env="SMTP_PORT")
    smtp_user: str = Field("", env="SMTP_USER")
    smtp_password: str = Field("", env="SMTP_PASSWORD")
    smtp_from_email: str = Field("noreply@afe.com", env="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field("AFE Sistema de Facturas", env="SMTP_FROM_NAME")
    smtp_use_tls: bool = Field(True, env="SMTP_USE_TLS")
    smtp_use_ssl: bool = Field(False, env="SMTP_USE_SSL")
    smtp_timeout: int = Field(30, env="SMTP_TIMEOUT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
