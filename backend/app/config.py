from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cockroachdb_url: str = "postgresql://root@localhost:26257/omninpc?sslmode=disable"

    # active path: Gemini dialogue + local embeddings
    gemini_api_key: str = ""
    gemini_model_id: str = "gemini-2.5-flash"

    # target path: Bedrock on EKS (app/providers/bedrock.py), not wired up yet
    aws_region: str = "us-east-1"
    bedrock_dialogue_model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
