"""Dialogue provider selection.

Set LLM_PROVIDER to choose. Imports are deferred so that an unconfigured provider, for
example Bedrock on an account without access, cannot break startup for the others.
"""

from app.config import get_settings


def generate_dialogue(system_prompt: str, user_message: str) -> str:
    provider = get_settings().llm_provider

    if provider == "lmstudio":
        from app.providers.lmstudio import generate_dialogue as impl
    elif provider == "gemini":
        from app.gemini import generate_dialogue as impl
    elif provider == "bedrock":
        from app.providers.bedrock import generate_dialogue as impl
    else:
        raise ValueError(f"unknown LLM_PROVIDER: {provider}")

    return impl(system_prompt, user_message)
