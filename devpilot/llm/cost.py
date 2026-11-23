"""Model pricing catalog and cost calculation engine."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    """Pricing rates in USD per 1 Million tokens."""

    prompt_rate_per_million: float
    completion_rate_per_million: float
    cached_prompt_rate_per_million: float | None = None


# Pricing catalog: USD per 1M tokens as of current provider rate cards
MODEL_PRICING_CATALOG: dict[str, ModelPricing] = {
    # Anthropic
    "claude-3-5-sonnet-20241022": ModelPricing(3.00, 15.00, 0.30),
    "claude-3-5-sonnet": ModelPricing(3.00, 15.00, 0.30),
    "claude-3-5-haiku-20241022": ModelPricing(0.80, 4.00, 0.08),
    "claude-3-5-haiku": ModelPricing(0.80, 4.00, 0.08),
    "claude-3-opus-20240229": ModelPricing(15.00, 75.00, 1.50),
    # OpenAI
    "gpt-4o": ModelPricing(2.50, 10.00, 1.25),
    "gpt-4o-2024-08-06": ModelPricing(2.50, 10.00, 1.25),
    "gpt-4o-mini": ModelPricing(0.15, 0.60, 0.075),
    "gpt-4o-mini-2024-07-18": ModelPricing(0.15, 0.60, 0.075),
    "o1": ModelPricing(15.00, 60.00, 7.50),
    "o1-mini": ModelPricing(3.00, 12.00, 1.50),
    "gpt-4-turbo": ModelPricing(10.00, 30.00),
    # Google Gemini
    "gemini-1.5-flash": ModelPricing(0.075, 0.30),
    "gemini-1.5-flash-latest": ModelPricing(0.075, 0.30),
    "gemini-1.5-pro": ModelPricing(1.25, 5.00),
    "gemini-1.5-pro-latest": ModelPricing(1.25, 5.00),
    "gemini-2.0-flash-exp": ModelPricing(0.00, 0.00),
    # DeepSeek
    "deepseek-chat": ModelPricing(0.14, 0.28, 0.014),
    "deepseek-coder": ModelPricing(0.14, 0.28, 0.014),
    "deepseek-reasoner": ModelPricing(0.55, 2.19, 0.14),
    # Local / Mock models
    "ollama": ModelPricing(0.0, 0.0),
    "mock": ModelPricing(0.0, 0.0),
    "mock-model": ModelPricing(0.0, 0.0),
}


def normalize_model_key(model: str) -> str:
    """Normalizes model names for catalog lookup."""
    lowered = model.lower().strip()
    if "/" in lowered:
        lowered = lowered.split("/")[-1]
    return lowered


def get_model_pricing(provider: str, model: str) -> ModelPricing:
    """Retrieves pricing specification for a given provider and model."""
    prov = provider.lower().strip()
    if "ollama" in prov or "local" in prov or "mock" in prov:
        return ModelPricing(0.0, 0.0)

    norm_model = normalize_model_key(model)
    if norm_model in MODEL_PRICING_CATALOG:
        return MODEL_PRICING_CATALOG[norm_model]

    # Partial match search
    for key, pricing in MODEL_PRICING_CATALOG.items():
        if key in norm_model or norm_model in key:
            return pricing

    # Provider-level fallbacks
    if "deepseek" in prov:
        return ModelPricing(0.20, 0.50)
    if "gemini" in prov:
        return ModelPricing(0.15, 0.60)
    if "anthropic" in prov:
        return ModelPricing(3.00, 15.00)

    # Generic default: $1.00 / 1M prompt, $3.00 / 1M completion
    return ModelPricing(1.00, 3.00)


def calculate_cost(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cached_prompt_tokens: int = 0,
) -> float:
    """Computes exact monetary cost in USD based on token counts and pricing rates."""
    pricing = get_model_pricing(provider, model)
    non_cached_prompt = max(0, prompt_tokens - cached_prompt_tokens)

    cost = (non_cached_prompt / 1_000_000.0) * pricing.prompt_rate_per_million
    cost += (completion_tokens / 1_000_000.0) * pricing.completion_rate_per_million

    if cached_prompt_tokens > 0:
        cached_rate = pricing.cached_prompt_rate_per_million or (
            pricing.prompt_rate_per_million * 0.5
        )
        cost += (cached_prompt_tokens / 1_000_000.0) * cached_rate

    return round(cost, 6)
