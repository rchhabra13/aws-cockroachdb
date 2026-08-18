from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cockroachdb_url: str = "postgresql://root@localhost:26257/omninpc?sslmode=disable"

    # gemini | bedrock
    llm_provider: str = "bedrock"

    # Disable to surface primary-provider errors to the request.
    llm_fallback_enabled: bool = True
    llm_fallback_provider: str = "gemini"

    gemini_api_key: str = ""
    gemini_model_id: str = "gemini-2.5-flash"

    # bedrock | local; schema VECTOR width must match the selected provider.
    embedding_provider: str = "bedrock"

    aws_region: str = "us-east-1"
    bedrock_dialogue_model_id: str = "us.amazon.nova-pro-v1:0"
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    # Titan V2 accepts 1024, 512, or 256.
    bedrock_embedding_dimensions: int = 1024

    # Empty disables authentication on operator routes.
    admin_api_key: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
