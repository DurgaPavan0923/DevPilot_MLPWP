"""DeepSeek API provider adapter (OpenAI-compatible protocol)."""

from typing import Any

from devpilot.llm.adapters.openai import OpenAIProvider


class DeepSeekProvider(OpenAIProvider):
    """Adapter for DeepSeek API endpoints (deepseek-chat, deepseek-reasoner)."""

    def __init__(
        self,
        model: str = "deepseek-chat",
        api_key: str | None = None,
        base_url: str = "https://api.deepseek.com/v1",
        timeout_sec: float = 60.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout_sec=timeout_sec,
            **kwargs,
        )

    @property
    def provider_name(self) -> str:
        return "deepseek"
