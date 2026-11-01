from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración leída de variables de entorno / archivo .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    secret_key: str = "cambiar-esto-en-produccion-clave-de-desarrollo-0000"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    cors_origins: str = "http://localhost:5173"
    max_upload_mb: int = 5
    seed_password: str = "Demo1234!"
    bcrypt_rounds: int = 12

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        for prefijo in ("postgres://", "postgresql://"):
            if url.startswith(prefijo):
                return "postgresql+psycopg2://" + url[len(prefijo):]
        return url


settings = Settings()