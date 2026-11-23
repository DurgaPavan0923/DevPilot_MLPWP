"""Provider registry for dynamic discovery and registration of LLM adapters."""

from devpilot.core.exceptions import LLMError
from devpilot.llm.base import LLMProvider

_REGISTRY: dict[str, type[LLMProvider]] = {}


def register_provider(name: str, provider_cls: type[LLMProvider]) -> None:
    """Registers an LLM provider adapter class under a unique name."""
    norm_name = name.lower().strip()
    _REGISTRY[norm_name] = provider_cls


def get_provider_class(name: str) -> type[LLMProvider]:
    """Retrieves the registered adapter class for a provider name."""
    norm_name = name.lower().strip()
    if norm_name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY.keys()))
        raise LLMError(
            f"Unknown LLM provider '{name}'. Available providers: {available}",
            provider=name,
        )
    return _REGISTRY[norm_name]


def get_registered_providers() -> list[str]:
    """Returns list of registered provider names."""
    return sorted(_REGISTRY.keys())


# Register built-in providers
def _init_builtin_providers() -> None:
    from devpilot.llm.adapters.anthropic import AnthropicProvider
    from devpilot.llm.adapters.deepseek import DeepSeekProvider
    from devpilot.llm.adapters.gemini import GeminiProvider
    from devpilot.llm.adapters.mock import MockProvider
    from devpilot.llm.adapters.ollama import OllamaProvider
    from devpilot.llm.adapters.openai import OpenAIProvider
    from devpilot.llm.adapters.openai_compatible import OpenAICompatibleProvider

    register_provider("mock", MockProvider)
    register_provider("openai", OpenAIProvider)
    register_provider("anthropic", AnthropicProvider)
    register_provider("gemini", GeminiProvider)
    register_provider("deepseek", DeepSeekProvider)
    register_provider("ollama", OllamaProvider)
    register_provider("openai_compatible", OpenAICompatibleProvider)


_init_builtin_providers()
