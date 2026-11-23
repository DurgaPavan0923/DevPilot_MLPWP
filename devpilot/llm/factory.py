"""Factory for instantiating and configuring LLM providers with safety defaults."""

from typing import Any

from devpilot.config import get_settings
from devpilot.llm.base import LLMProvider
from devpilot.llm.registry import get_provider_class


def create_provider(
    provider_name: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    **kwargs: Any,
) -> LLMProvider:
    """Instantiates and configures a requested LLM provider."""
    settings = get_settings()

    target_provider = (provider_name or settings.llm.default_provider).lower().strip()
    target_model = model or settings.llm.default_model

    # Determine provider-specific credentials and URLs from settings if not explicitly provided
    target_api_key = api_key
    target_base_url = kwargs.pop("base_url", None)

    if target_provider == "openai":
        target_api_key = target_api_key or settings.openai_api_key
        target_model = target_model if target_model != "mock-model" else "gpt-4o-mini"
    elif target_provider == "anthropic":
        target_api_key = target_api_key or settings.anthropic_api_key
        target_model = (
            target_model if target_model != "mock-model" else "claude-3-5-sonnet-20241022"
        )
    elif target_provider == "gemini":
        target_api_key = target_api_key or settings.gemini_api_key
        target_model = target_model if target_model != "mock-model" else "gemini-1.5-flash"
    elif target_provider == "deepseek":
        target_api_key = target_api_key or settings.deepseek_api_key
        target_model = target_model if target_model != "mock-model" else "deepseek-chat"
    elif target_provider == "ollama":
        target_base_url = target_base_url or settings.ollama_base_url
        target_model = target_model if target_model != "mock-model" else settings.ollama_model
    elif target_provider == "openai_compatible":
        target_api_key = target_api_key or settings.openai_compatible_api_key
        target_base_url = (
            target_base_url or settings.openai_compatible_base_url or "http://localhost:8000/v1"
        )
        target_model = target_model or settings.openai_compatible_model or "custom-model"

    provider_cls = get_provider_class(target_provider)

    init_kwargs = dict(kwargs)
    if target_base_url:
        init_kwargs["base_url"] = target_base_url
    if "timeout_sec" not in init_kwargs:
        init_kwargs["timeout_sec"] = settings.llm.request_timeout_sec

    return provider_cls(
        model=target_model,
        api_key=target_api_key,
        **init_kwargs,
    )


def get_default_provider() -> LLMProvider:
    """Returns the default provider configured in settings."""
    settings = get_settings()
    return create_provider(
        provider_name=settings.llm.default_provider,
        model=settings.llm.default_model,
    )
