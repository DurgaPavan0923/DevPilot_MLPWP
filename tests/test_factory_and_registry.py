"""Unit tests for Provider Registry and Factory."""

import pytest

from devpilot.core.exceptions import LLMError
from devpilot.llm.adapters.anthropic import AnthropicProvider
from devpilot.llm.adapters.mock import MockProvider
from devpilot.llm.adapters.openai import OpenAIProvider
from devpilot.llm.factory import create_provider
from devpilot.llm.registry import get_registered_providers


def test_registered_providers():
    providers = get_registered_providers()
    assert "mock" in providers
    assert "openai" in providers
    assert "anthropic" in providers
    assert "gemini" in providers
    assert "deepseek" in providers
    assert "ollama" in providers
    assert "openai_compatible" in providers


def test_create_mock_provider():
    p = create_provider("mock", model="custom-mock")
    assert isinstance(p, MockProvider)
    assert p.model == "custom-mock"
    assert p.provider_name == "mock"


def test_create_openai_provider():
    p = create_provider("openai", model="gpt-4o", api_key="sk-test-fake")
    assert isinstance(p, OpenAIProvider)
    assert p.model == "gpt-4o"
    assert p.provider_name == "openai"


def test_create_anthropic_provider():
    p = create_provider("anthropic", model="claude-3-5-sonnet", api_key="sk-ant-test")
    assert isinstance(p, AnthropicProvider)
    assert p.provider_name == "anthropic"


def test_unknown_provider_raises():
    with pytest.raises(LLMError) as exc_info:
        create_provider("unknown_provider_xyz")
    assert "Unknown LLM provider" in str(exc_info.value)
