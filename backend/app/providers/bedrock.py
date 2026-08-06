"""Amazon Bedrock dialogue and embedding adapter.

Dialogue can be selected with ``LLM_PROVIDER=bedrock``. The application memory path
currently imports ``app.embeddings`` directly, so ``embed_text`` in this module is not
active.

Titan Text Embeddings V2 returns 1024-dimensional vectors, while the current schema and
local embedding model use 384 dimensions. Connecting the Bedrock embedding function
therefore requires a schema migration and re-embedding all existing memory rows.
"""

import json

import boto3

from app.config import get_settings

_runtime = None


def _client():
    global _runtime
    if _runtime is None:
        _runtime = boto3.client("bedrock-runtime", region_name=get_settings().aws_region)
    return _runtime


def embed_text(text: str) -> list[float]:
    settings = get_settings()
    response = _client().invoke_model(
        modelId=settings.bedrock_embedding_model_id,
        body=json.dumps({"inputText": text}),
    )
    payload = json.loads(response["body"].read())
    return payload["embedding"]


def generate_dialogue(system_prompt: str, user_message: str) -> str:
    settings = get_settings()
    response = _client().invoke_model(
        modelId=settings.bedrock_dialogue_model_id,
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
                "max_tokens": 512,
            }
        ),
    )
    payload = json.loads(response["body"].read())
    return payload["content"][0]["text"]
