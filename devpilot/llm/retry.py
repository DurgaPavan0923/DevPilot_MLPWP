"""Exponential backoff retry handler with jitter for resilient LLM calls."""

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

from devpilot.core.exceptions import (
    LLMAuthenticationError,
    LLMContextLengthExceededError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
)
from devpilot.core.logging import get_logger

logger = get_logger("devpilot.llm.retry")

T = TypeVar("T")


def is_retryable_exception(exc: Exception) -> bool:
    """Determines if an exception is transient and eligible for retry."""
    if isinstance(exc, (LLMAuthenticationError, LLMContextLengthExceededError)):
        return False
    if isinstance(exc, (LLMRateLimitError, LLMProviderUnavailableError)):
        return True
    if isinstance(
        exc, (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout)
    ):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code in (429, 500, 502, 503, 504)
    return False


async def execute_with_retry(
    func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    min_backoff_sec: float = 1.0,
    max_backoff_sec: float = 30.0,
    provider_name: str = "llm",
    operation_name: str = "chat",
) -> T:
    """Executes an async callable with exponential backoff and randomized jitter."""
    attempt = 0
    while True:
        try:
            return await func()
        except Exception as exc:
            attempt += 1
            if attempt > max_retries or not is_retryable_exception(exc):
                logger.error(
                    "llm_call_failed_unretryable",
                    provider=provider_name,
                    operation=operation_name,
                    attempt=attempt,
                    max_retries=max_retries,
                    error=str(exc),
                )
                raise exc

            # Calculate backoff delay with jitter
            backoff = min_backoff_sec * (2 ** (attempt - 1))
            jitter = random.uniform(0.5, 1.5)
            delay = min(max_backoff_sec, backoff * jitter)

            # Check for Retry-After hint
            if isinstance(exc, LLMRateLimitError) and exc.retry_after:
                delay = max(delay, exc.retry_after)
            elif isinstance(exc, httpx.HTTPStatusError) and "Retry-After" in exc.response.headers:
                try:
                    retry_after_val = float(exc.response.headers["Retry-After"])
                    delay = max(delay, retry_after_val)
                except ValueError:
                    pass

            logger.warning(
                "llm_call_transient_failure_retrying",
                provider=provider_name,
                operation=operation_name,
                attempt=attempt,
                delay_sec=round(delay, 2),
                error=str(exc),
            )
            await asyncio.sleep(delay)
