"""Select a dialogue provider and log fallback use."""

import logging

from app.config import get_settings

log = logging.getLogger(__name__)


def _impl(provider: str):
    if provider == "gemini":
        from app.providers.gemini import generate_dialogue as impl
    elif provider == "bedrock":
        from app.providers.bedrock import generate_dialogue as impl
    else:
        raise ValueError(f"unknown LLM provider: {provider!r}")
    return impl


def generate_dialogue(system_prompt: str, user_message: str, history=None) -> str:
    settings = get_settings()
    primary = settings.llm_provider

    # Invalid primary names should not be hidden by fallback behavior.
    impl = _impl(primary)

    try:
        return impl(system_prompt, user_message, history)
    except Exception as exc:
        fallback = settings.llm_fallback_provider
        if not settings.llm_fallback_enabled or fallback == primary:
            raise
        log.warning(
            "dialogue provider %s failed (%s: %s); falling back to %s",
            primary,
            type(exc).__name__,
            exc,
            fallback,
        )
        return _impl(fallback)(system_prompt, user_message, history)
