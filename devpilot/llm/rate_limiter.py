"""Asynchronous token bucket and concurrency rate limiter for LLM requests."""

import asyncio
import contextlib
import time

from devpilot.core.exceptions import LLMRateLimitError
from devpilot.core.logging import get_logger

logger = get_logger("devpilot.llm.rate_limiter")


class RateLimiter:
    """Token-bucket rate limiter enforcing requests-per-minute (RPM),

    tokens-per-minute (TPM), and max concurrent requests.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        tokens_per_minute: int = 100_000,
        max_concurrency: int = 10,
        provider_name: str = "llm",
    ) -> None:
        self.rpm = max(1, requests_per_minute)
        self.tpm = max(1, tokens_per_minute)
        self.max_concurrency = max(1, max_concurrency)
        self.provider_name = provider_name

        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        self._lock = asyncio.Lock()

        # Token buckets: (current_tokens, last_refill_timestamp)
        self._request_capacity = float(self.rpm)
        self._request_tokens = float(self.rpm)
        self._request_fill_rate = float(self.rpm) / 60.0

        self._token_capacity = float(self.tpm)
        self._available_tokens = float(self.tpm)
        self._token_fill_rate = float(self.tpm) / 60.0

        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._last_refill = now

        self._request_tokens = min(
            self._request_capacity,
            self._request_tokens + (elapsed * self._request_fill_rate),
        )
        self._available_tokens = min(
            self._token_capacity,
            self._available_tokens + (elapsed * self._token_fill_rate),
        )

    async def acquire(self, estimated_tokens: int = 500, timeout: float | None = 30.0) -> None:
        """Acquires permission to make a request, waiting if rate limits are reached."""
        start_time = time.monotonic()

        # Acquire concurrency slot first
        try:
            if timeout is not None:
                await asyncio.wait_for(self._semaphore.acquire(), timeout=timeout)
            else:
                await self._semaphore.acquire()
        except TimeoutError as exc:
            raise LLMRateLimitError(
                f"Rate limiter timed out waiting for concurrency slot on {self.provider_name}",
                provider=self.provider_name,
            ) from exc

        # Enforce RPM and TPM buckets
        while True:
            async with self._lock:
                self._refill()

                has_req_slot = self._request_tokens >= 1.0
                has_token_slot = self._available_tokens >= float(estimated_tokens)

                if has_req_slot and has_token_slot:
                    self._request_tokens -= 1.0
                    self._available_tokens -= float(estimated_tokens)
                    return

                # Calculate required sleep time
                req_wait = (
                    (1.0 - self._request_tokens) / self._request_fill_rate
                    if not has_req_slot
                    else 0.0
                )
                tok_wait = (
                    (float(estimated_tokens) - self._available_tokens) / self._token_fill_rate
                    if not has_token_slot
                    else 0.0
                )
                wait_time = max(req_wait, tok_wait, 0.05)

            elapsed_total = time.monotonic() - start_time
            if timeout is not None and (elapsed_total + wait_time) > timeout:
                self._semaphore.release()
                raise LLMRateLimitError(
                    f"Rate limiter timed out waiting for token bucket on {self.provider_name}",
                    provider=self.provider_name,
                    retry_after=wait_time,
                )

            logger.debug(
                "rate_limit_throttle",
                provider=self.provider_name,
                wait_time=wait_time,
                estimated_tokens=estimated_tokens,
            )
            await asyncio.sleep(min(wait_time, 2.0))

    def release(self) -> None:
        """Releases concurrency slot after request finishes."""
        with contextlib.suppress(ValueError):
            self._semaphore.release()
