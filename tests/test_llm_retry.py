"""Unit tests for exponential backoff and retry mechanism."""

import pytest

from devpilot.core.exceptions import LLMAuthenticationError, LLMProviderUnavailableError
from devpilot.llm.retry import execute_with_retry


@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_failure():
    calls = 0

    async def flaky_call():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise LLMProviderUnavailableError("503 Service Unavailable")
        return "success"

    result = await execute_with_retry(
        flaky_call,
        max_retries=3,
        min_backoff_sec=0.01,
        max_backoff_sec=0.05,
    )

    assert result == "success"
    assert calls == 3


@pytest.mark.asyncio
async def test_retry_aborts_immediately_on_auth_failure():
    calls = 0

    async def auth_fail_call():
        nonlocal calls
        calls += 1
        raise LLMAuthenticationError("Invalid API key")

    with pytest.raises(LLMAuthenticationError):
        await execute_with_retry(
            auth_fail_call,
            max_retries=3,
            min_backoff_sec=0.01,
        )

    # Must NOT retry 401 errors
    assert calls == 1
