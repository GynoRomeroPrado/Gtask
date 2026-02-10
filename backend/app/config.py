"""
Configuración central de la aplicación.
Usa Pydantic Settings para cargar variables de entorno con validación de tipos.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración de la aplicación cargada desde variables de entorno."""

    # --- Base de Datos ---
    database_url: str = "sqlite:///./cerebro_operativo.db"

    # --- Seguridad ---
    secret_key: str = "dev-secret-key-cambiar-en-produccion"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 horas

    # --- Servidor ---
    app_env: str = "development"
    app_port: int = 8000
    app_host: str = "0.0.0.0"
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # --- Google APIs (Fase 1+) ---
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # --- OpenAI (Fase 3) ---
    openai_api_key: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        """Retorna la lista de orígenes CORS permitidos."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    """Singleton de configuración cacheado."""
    return Settings()
