"""Amazon Bedrock adapter for Nova dialogue and Titan embeddings."""

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
        body=json.dumps(
            {
                "inputText": text,
                "dimensions": settings.bedrock_embedding_dimensions,
                "normalize": True,
            }
        ),
    )
    return json.loads(response["body"].read())["embedding"]


def generate_dialogue(system_prompt: str, user_message: str, history=None) -> str:
    settings = get_settings()

    # Stored speaker names must be mapped to Converse roles; order is already chronological.
    messages = []
    for turn in history or []:
        role = "user" if turn["speaker"] == "player" else "assistant"
        messages.append({"role": role, "content": [{"text": turn["content"]}]})
    messages.append({"role": "user", "content": [{"text": user_message}]})

    response = _client().converse(
        modelId=settings.bedrock_dialogue_model_id,
        system=[{"text": system_prompt}],
        messages=messages,
        inferenceConfig={"maxTokens": 512},
    )
    return response["output"]["message"]["content"][0]["text"]
