"""Amazon Bedrock provider. Target for the EKS deployment; not wired up yet.

Gemini + local embeddings are the current active path (see app/gemini.py and
app/embeddings.py). Switch to this module once the account's Bedrock access is
unblocked. See docs/SCENARIO.md and the Phase 0 / Phase 2 notes in the build plan.

Model ids verified against account 010928209855 on 2026-08-04:
  - amazon.titan-embed-text-v2:0 returns 1024-dim vectors (not 1536).
  - Claude requires the `us.` inference-profile form. Bare model ids fail with
    "Invocation of model ID ... with on-demand throughput isn't supported".
  - Both currently return AccessDeniedException INVALID_PAYMENT_INSTRUMENT, because
    Anthropic models on Bedrock are billed through AWS Marketplace and the account's
    India-issued card is rejected there.

Titan's 1024 dims do not match the 384 of the active local embedder, so switching
providers requires altering memory_embeddings.embedding and re-embedding every row.
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
