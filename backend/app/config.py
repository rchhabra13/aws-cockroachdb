from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cockroachdb_url: str = "postgresql://root@localhost:26257/omninpc?sslmode=disable"

    # which dialogue provider to use: lmstudio | gemini | bedrock
    llm_provider: str = "lmstudio"

    # If the primary provider raises, answer with the fallback instead of failing the
    # turn. Set false to see provider errors surface as request failures.
    llm_fallback_enabled: bool = True
    llm_fallback_provider: str = "lmstudio"

    # local LM Studio server. No quota, no network, no key leaving the machine.
    lm_studio_base_url: str = "http://host.docker.internal:1234"
    lm_studio_api_key: str = ""
    lm_studio_model_id: str = "google/gemma-4-12b"

    # hosted Gemini. Free tier is capped at 20 requests per day per model.
    gemini_api_key: str = ""
    gemini_model_id: str = "gemini-2.5-flash"

    # which embedding provider to use: bedrock | local
    # Not interchangeable at runtime: the two produce different vector widths, and the
    # schema's VECTOR column must match whichever is configured.
    embedding_provider: str = "bedrock"

    aws_region: str = "us-east-1"
    bedrock_dialogue_model_id: str = "us.amazon.nova-pro-v1:0"
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    # Titan V2 accepts 1024, 512, or 256.
    bedrock_embedding_dimensions: int = 1024

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
