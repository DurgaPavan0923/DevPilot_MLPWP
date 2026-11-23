"""Unit tests for asynchronous rate limiter."""

import pytest

from devpilot.core.exceptions import LLMRateLimitError
from devpilot.llm.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_permits_under_capacity():
    limiter = RateLimiter(requests_per_minute=60, tokens_per_minute=10000, max_concurrency=5)
    await limiter.acquire(estimated_tokens=500, timeout=1.0)
    limiter.release()


@pytest.mark.asyncio
async def test_rate_limiter_concurrency_exhaustion():
    limiter = RateLimiter(requests_per_minute=60, tokens_per_minute=10000, max_concurrency=1)
    await limiter.acquire(estimated_tokens=100)

    # Second concurrent acquire should timeout
    with pytest.raises(LLMRateLimitError) as exc_info:
        await limiter.acquire(estimated_tokens=100, timeout=0.1)

    assert "concurrency slot" in str(exc_info.value)
    limiter.release()
