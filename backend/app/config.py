from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cockroachdb_url: str = "postgresql://root@localhost:26257/omninpc?sslmode=disable"
    gemini_api_key: str = ""
    gemini_model_id: str = "gemini-2.5-flash"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
