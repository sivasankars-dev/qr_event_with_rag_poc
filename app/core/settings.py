from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    POSTGRES_HOST: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int 

    DATABASE_URL: str | None = None
    SECRET_KEY: str
    ALGORITHM: str

    model_config = ConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

settings = Settings()
