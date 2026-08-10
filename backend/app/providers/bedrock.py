"""Amazon Bedrock dialogue and embedding adapter.

Dialogue uses Amazon Nova through the Converse API rather than raw ``invoke_model``.
Converse takes the same request shape for every model, so changing model is a model id
change instead of a new request body.

Embeddings use Titan Text Embeddings V2. Its supported output sizes are 1024, 512, and
256; 384 is not among them, so the schema's vector width is tied to whichever embedding
provider is configured. See app/embeddings.py.
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
        body=json.dumps(
            {
                "inputText": text,
                "dimensions": settings.bedrock_embedding_dimensions,
                "normalize": True,
            }
        ),
    )
    return json.loads(response["body"].read())["embedding"]


def generate_dialogue(system_prompt: str, user_message: str) -> str:
    settings = get_settings()
    response = _client().converse(
        modelId=settings.bedrock_dialogue_model_id,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": user_message}]}],
        inferenceConfig={"maxTokens": 512},
    )
    return response["output"]["message"]["content"][0]["text"]
