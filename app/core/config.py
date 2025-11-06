# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


# Roles del sistema
class Roles:
    """Constantes para roles de usuario."""
    ADMIN = "admin"
    RESPONSABLE = "responsable"
    VIEWER = "viewer"  # Solo lectura


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

    # --- Microsoft OAuth (para autenticación de usuarios) ---
    # Usar el mismo tenant y client_id si se usa la misma app registration
    # O crear variables separadas si se usa una app diferente para auth
    oauth_microsoft_tenant_id: str = Field("", env="OAUTH_MICROSOFT_TENANT_ID")
    oauth_microsoft_client_id: str = Field("", env="OAUTH_MICROSOFT_CLIENT_ID")
    oauth_microsoft_client_secret: str = Field("", env="OAUTH_MICROSOFT_CLIENT_SECRET")
    oauth_microsoft_redirect_uri: str = Field("http://localhost:3000/auth/microsoft/callback", env="OAUTH_MICROSOFT_REDIRECT_URI")
    oauth_microsoft_scopes: str = Field("openid email profile User.Read", env="OAUTH_MICROSOFT_SCOPES")

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
