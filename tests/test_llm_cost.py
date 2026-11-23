"""Unit tests for pricing catalog and cost calculation."""

from devpilot.llm.cost import calculate_cost, get_model_pricing


def test_pricing_lookup():
    p_gpt4o = get_model_pricing("openai", "gpt-4o")
    assert p_gpt4o.prompt_rate_per_million == 2.50
    assert p_gpt4o.completion_rate_per_million == 10.00

    p_claude = get_model_pricing("anthropic", "claude-3-5-sonnet")
    assert p_claude.prompt_rate_per_million == 3.00
    assert p_claude.completion_rate_per_million == 15.00

    p_gemini = get_model_pricing("gemini", "gemini-1.5-flash")
    assert p_gemini.prompt_rate_per_million == 0.075

    p_local = get_model_pricing("ollama", "deepseek-coder:6.7b")
    assert p_local.prompt_rate_per_million == 0.0
    assert p_local.completion_rate_per_million == 0.0


def test_cost_calculation():
    # 1,000,000 prompt tokens and 1,000,000 completion tokens on GPT-4o
    cost = calculate_cost("openai", "gpt-4o", 1_000_000, 1_000_000)
    assert cost == 12.50

    # 10,000 prompt and 2,000 completion tokens on Claude 3.5 Sonnet
    cost_claude = calculate_cost("anthropic", "claude-3-5-sonnet", 10_000, 2_000)
    # (10000/1e6)*3.00 + (2000/1e6)*15.00 = 0.03 + 0.03 = 0.06
    assert cost_claude == 0.06

    # Ollama cost must be exactly 0
    cost_ollama = calculate_cost("ollama", "deepseek-coder", 500_000, 500_000)
    assert cost_ollama == 0.0
