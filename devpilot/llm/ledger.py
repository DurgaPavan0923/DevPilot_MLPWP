"""Thread-safe usage ledger tracking token consumption, costs, and audit logs."""

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from devpilot.llm.base import TokenUsage


@dataclass
class UsageRecord:
    """Individual invocation transaction record."""

    id: str
    session_id: str | None
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    duration_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


class UsageLedger:
    """Aggregating ledger for token usage and financial cost accounting."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._records: list[UsageRecord] = []
        self._total_prompt_tokens: int = 0
        self._total_completion_tokens: int = 0
        self._total_cost_usd: float = 0.0
        self._by_model: dict[str, dict[str, Any]] = {}
        self._by_provider: dict[str, dict[str, Any]] = {}

    async def record_usage(
        self,
        record_id: str,
        provider: str,
        model: str,
        usage: TokenUsage,
        cost_usd: float,
        duration_ms: float = 0.0,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UsageRecord:
        """Records a completed LLM invocation transaction."""
        rec = UsageRecord(
            id=record_id,
            session_id=session_id,
            provider=provider,
            model=model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )

        async with self._lock:
            self._records.append(rec)
            self._total_prompt_tokens += usage.prompt_tokens
            self._total_completion_tokens += usage.completion_tokens
            self._total_cost_usd += cost_usd

            # Aggregate by provider
            if provider not in self._by_provider:
                self._by_provider[provider] = {
                    "requests": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                }
            p_entry = self._by_provider[provider]
            p_entry["requests"] += 1
            p_entry["prompt_tokens"] += usage.prompt_tokens
            p_entry["completion_tokens"] += usage.completion_tokens
            p_entry["total_tokens"] += usage.total_tokens
            p_entry["cost_usd"] = round(p_entry["cost_usd"] + cost_usd, 6)

            # Aggregate by model
            if model not in self._by_model:
                self._by_model[model] = {
                    "requests": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                }
            m_entry = self._by_model[model]
            m_entry["requests"] += 1
            m_entry["prompt_tokens"] += usage.prompt_tokens
            m_entry["completion_tokens"] += usage.completion_tokens
            m_entry["total_tokens"] += usage.total_tokens
            m_entry["cost_usd"] = round(m_entry["cost_usd"] + cost_usd, 6)

        return rec

    async def get_summary(self, session_id: str | None = None) -> dict[str, Any]:
        """Returns comprehensive ledger summary metrics."""
        async with self._lock:
            if session_id:
                filtered = [r for r in self._records if r.session_id == session_id]
                prompt = sum(r.prompt_tokens for r in filtered)
                comp = sum(r.completion_tokens for r in filtered)
                cost = sum(r.cost_usd for r in filtered)
                return {
                    "requests": len(filtered),
                    "prompt_tokens": prompt,
                    "completion_tokens": comp,
                    "total_tokens": prompt + comp,
                    "cost_usd": round(cost, 6),
                }

            return {
                "total_requests": len(self._records),
                "total_prompt_tokens": self._total_prompt_tokens,
                "total_completion_tokens": self._total_completion_tokens,
                "total_tokens": self._total_prompt_tokens + self._total_completion_tokens,
                "total_cost_usd": round(self._total_cost_usd, 6),
                "by_provider": dict(self._by_provider),
                "by_model": dict(self._by_model),
            }

    async def get_recent_records(self, limit: int = 50) -> list[dict[str, Any]]:
        """Returns recent transactions."""
        async with self._lock:
            return [asdict(r) for r in self._records[-limit:]]
