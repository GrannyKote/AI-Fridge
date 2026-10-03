from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/diplom"
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


settings = Settings()
