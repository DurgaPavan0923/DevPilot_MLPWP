"""Unit tests for the usage ledger."""

import pytest

from devpilot.llm.base import TokenUsage
from devpilot.llm.ledger import UsageLedger


@pytest.mark.asyncio
async def test_usage_ledger_aggregation():
    ledger = UsageLedger()

    await ledger.record_usage(
        record_id="rec_1",
        provider="openai",
        model="gpt-4o-mini",
        usage=TokenUsage.compute(1000, 200),
        cost_usd=0.0003,
        session_id="session_A",
    )

    await ledger.record_usage(
        record_id="rec_2",
        provider="openai",
        model="gpt-4o-mini",
        usage=TokenUsage.compute(2000, 300),
        cost_usd=0.0005,
        session_id="session_A",
    )

    await ledger.record_usage(
        record_id="rec_3",
        provider="anthropic",
        model="claude-3-5-sonnet",
        usage=TokenUsage.compute(500, 100),
        cost_usd=0.003,
        session_id="session_B",
    )

    global_summary = await ledger.get_summary()
    assert global_summary["total_requests"] == 3
    assert global_summary["total_prompt_tokens"] == 3500
    assert global_summary["total_completion_tokens"] == 600
    assert global_summary["total_tokens"] == 4100
    assert global_summary["total_cost_usd"] == 0.0038

    # Filtered by session
    session_a = await ledger.get_summary(session_id="session_A")
    assert session_a["requests"] == 2
    assert session_a["prompt_tokens"] == 3000
    assert session_a["completion_tokens"] == 500
    assert session_a["cost_usd"] == 0.0008

    recent = await ledger.get_recent_records(limit=2)
    assert len(recent) == 2
