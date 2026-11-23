"""Unit tests for configuration and settings."""

from devpilot.config import DevPilotSettings, get_settings
from devpilot.core.types import AgentConfigPreset, PermissionMode


def test_default_settings():
    settings = get_settings()
    assert settings.env in ("development", "production", "test")
    assert settings.llm.default_provider == "mock"
    assert settings.safety.permission_mode == PermissionMode.AUTO_SAFE
    assert settings.safety.max_steps == 30
    assert settings.retrieval.fixed_k == 5
    assert settings.agent_preset == AgentConfigPreset.FULL


def test_custom_settings_override():
    custom = DevPilotSettings(
        env="test",
        host="127.0.0.1",
        port=9000,
        agent_preset=AgentConfigPreset.BASIC,
    )
    assert custom.env == "test"
    assert custom.host == "127.0.0.1"
    assert custom.port == 9000
    assert custom.agent_preset == AgentConfigPreset.BASIC
