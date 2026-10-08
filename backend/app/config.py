from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url_direct: str | None = Field(default=None, validation_alias="DATABASE_URL")
    postgres_user: str = Field(default="postgres", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", validation_alias="POSTGRES_PASSWORD")
    postgres_host: str | None = Field(default=None, validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    postgres_db: str = Field(default="diplom", validation_alias="POSTGRES_DB")
    db_schema: str = "diplom_all"
    default_group_name: str = "Новая группа пользователей"
    # Ключ подписи JWT. На проде задаётся через JWT_SECRET в .env.
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_ttl_hours: int = 24 * 7
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost",
        "http://127.0.0.1",
    ]
    cors_origin_regex: str = r"https?://.*"

    @property
    def database_url(self) -> str:
        if self.postgres_host:
            user = quote_plus(self.postgres_user)
            password = quote_plus(self.postgres_password)
            return (
                f"postgresql+psycopg://{user}:{password}@"
                f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )

        if self.database_url_direct:
            return self.database_url_direct

        return "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/diplom"


settings = Settings()
