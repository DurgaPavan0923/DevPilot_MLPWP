"""Application settings and configuration powered by pydantic-settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from devpilot.core.types import AgentConfigPreset, PermissionMode


class LLMConfig(BaseSettings):
    """Configuration for LLM providers and model invocations."""

    model_config = SettingsConfigDict(env_prefix="DEVPILOT_", extra="ignore")

    default_provider: str = Field(
        default="mock", description="Default provider (anthropic, openai, gemini, etc.)"
    )
    default_model: str = Field(default="mock-model", description="Default model name")
    default_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    request_timeout_sec: float = Field(default=60.0, ge=1.0)
    max_retries: int = Field(default=3, ge=0)
    retry_min_backoff_sec: float = Field(default=1.0, ge=0.1)
    retry_max_backoff_sec: float = Field(default=30.0, ge=1.0)
    rate_limit_requests_per_minute: int = Field(default=60, ge=1)
    rate_limit_tokens_per_minute: int = Field(default=100_000, ge=100)


class SafetyConfig(BaseSettings):
    """Security, permissions, and sandbox constraints."""

    model_config = SettingsConfigDict(env_prefix="DEVPILOT_", extra="ignore")

    permission_mode: PermissionMode = Field(default=PermissionMode.AUTO_SAFE)
    sandbox_enabled: bool = Field(default=False)
    sandbox_timeout_sec: float = Field(default=120.0, ge=1.0)
    max_steps: int = Field(default=30, ge=1)
    max_cost_usd: float = Field(default=2.0, ge=0.01)
    max_total_tokens: int = Field(default=250_000, ge=1000)
    command_timeout_sec: float = Field(default=60.0, ge=1.0)


class RetrievalConfig(BaseSettings):
    """Repository scanning, AST parsing, and hybrid retrieval settings."""

    model_config = SettingsConfigDict(env_prefix="DEVPILOT_RETRIEVAL_", extra="ignore")

    fixed_k: int = Field(default=5, ge=1)
    adaptive_k_min: int = Field(default=2, ge=1)
    adaptive_k_max: int = Field(default=12, ge=2)
    bm25_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    dense_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    graph_weight: float = Field(default=0.2, ge=0.0, le=1.0)
    token_budget_ratio: float = Field(default=0.35, ge=0.1, le=0.8)


class ApiConfig(BaseSettings):
    """API server security, authentication, and origin configuration."""

    model_config = SettingsConfigDict(env_prefix="DEVPILOT_API_", extra="ignore")

    api_key: str | None = Field(
        default=None, description="Optional bearer or x-api-key authentication token"
    )
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    workspace_root: Path = Field(
        default=Path(".").resolve(), description="Jail directory for repo inspection and tasks"
    )
    rate_limit_rpm: int = Field(default=120, ge=1)


class DevPilotSettings(BaseSettings):
    """Global unified DevPilot configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = Field(default="development")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    session_dir: Path = Field(default=Path(".devpilot/sessions"))
    database_url: str = Field(default="sqlite+aiosqlite:///.devpilot/devpilot.db")

    # API Keys
    anthropic_api_key: str | None = Field(default=None)
    openai_api_key: str | None = Field(default=None)
    gemini_api_key: str | None = Field(default=None)
    deepseek_api_key: str | None = Field(default=None)

    # Local / Custom Endpoints
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="deepseek-coder:6.7b")
    openai_compatible_base_url: str | None = Field(default=None)
    openai_compatible_api_key: str | None = Field(default=None)
    openai_compatible_model: str | None = Field(default=None)

    # Sub-configurations
    api: ApiConfig = Field(default_factory=ApiConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    agent_preset: AgentConfigPreset = Field(default=AgentConfigPreset.FULL)
    db_path: Path = Field(default=Path(".devpilot/devpilot.db"))


_settings: DevPilotSettings | None = None


def get_settings() -> DevPilotSettings:
    """Returns singleton cached instance of DevPilotSettings."""
    global _settings
    if _settings is None:
        _settings = DevPilotSettings()
    return _settings
