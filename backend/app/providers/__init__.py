"""Dialogue provider selection, with a local fallback.

LLM_PROVIDER picks the primary: lmstudio, gemini, or bedrock. Imports are deferred so an
unconfigured provider — Bedrock on an account without model access, say — cannot break
startup for the others.

When LLM_FALLBACK_ENABLED is set, a primary that raises falls back to
LLM_FALLBACK_PROVIDER instead of failing the turn. A hosted provider can be rate limited,
unauthorized, or simply offline mid demo; falling back to the local model keeps the
scenario running. Fallback is deliberately not silent — it logs which provider answered.
"""

import logging

from app.config import get_settings

log = logging.getLogger(__name__)


def _impl(provider: str):
    if provider == "lmstudio":
        from app.providers.lmstudio import generate_dialogue as impl
    elif provider == "gemini":
        from app.providers.gemini import generate_dialogue as impl
    elif provider == "bedrock":
        from app.providers.bedrock import generate_dialogue as impl
    else:
        raise ValueError(f"unknown LLM provider: {provider!r}")
    return impl


def generate_dialogue(system_prompt: str, user_message: str) -> str:
    settings = get_settings()
    primary = settings.llm_provider

    # Resolved before the try block so a misspelled provider name is a startup-style
    # error rather than something the fallback quietly papers over.
    impl = _impl(primary)

    try:
        return impl(system_prompt, user_message)
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
        return _impl(fallback)(system_prompt, user_message)
