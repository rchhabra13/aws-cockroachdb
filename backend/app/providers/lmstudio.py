"""LM Studio provider, for local development without quota limits.

Uses LM Studio's own REST API rather than its OpenAI compatible endpoint, so the
response shape is `output[]` blocks rather than `choices[]`. Reasoning models may emit
additional blocks before the message, so the message block is selected by type rather
than by position.
"""

import httpx

from app.config import get_settings

TIMEOUT = 180.0


def generate_dialogue(system_prompt: str, user_message: str) -> str:
    settings = get_settings()
    response = httpx.post(
        f"{settings.lm_studio_base_url}/api/v1/chat",
        headers={"Authorization": f"Bearer {settings.lm_studio_api_key}"},
        json={
            "model": settings.lm_studio_model_id,
            "system_prompt": system_prompt,
            "input": user_message,
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()

    for block in payload.get("output", []):
        if block.get("type") == "message":
            return block["content"]
    raise RuntimeError(f"LM Studio returned no message block: {payload}")
