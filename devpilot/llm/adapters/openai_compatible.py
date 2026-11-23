"""Generic OpenAI-compatible provider adapter for custom endpoints (vLLM, Groq, Together, etc.)."""

from typing import Any

from devpilot.llm.adapters.openai import OpenAIProvider


class OpenAICompatibleProvider(OpenAIProvider):
    """Generic adapter for third-party OpenAI-compatible endpoints."""

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str | None = None,
        timeout_sec: float = 60.0,
        provider_name: str = "openai_compatible",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            model=model,
            api_key=api_key or "not-needed",
            base_url=base_url,
            timeout_sec=timeout_sec,
            **kwargs,
        )
        self._custom_provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._custom_provider_name
