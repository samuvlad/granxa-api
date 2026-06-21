from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://granxa:granxa@localhost:5432/granxa_maps"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    init_db: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
