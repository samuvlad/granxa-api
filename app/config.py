from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://granxa:granxa@localhost:5432/granxa_maps"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    init_db: bool = False
    db_echo: bool = False
    run_migrations: bool = True
    jwt_secret: str = "change-me-in-production-please-this-is-not-secure"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 8

    class Config:
        env_file = ".env"


settings = Settings()
