"""End-to-end general smoke test exercising the full DevPilot harness pipeline with MockProvider."""

import asyncio
import sys
import tempfile
from pathlib import Path

from devpilot.agent.runtime import AgentRuntime
from devpilot.config import get_settings
from devpilot.core.logging import configure_logging, get_logger
from devpilot.core.types import AgentConfigPreset, PermissionMode
from devpilot.llm.adapters.mock import MockProvider
from devpilot.llm.base import ChatResponse, Message, TokenUsage
from devpilot.llm.ledger import UsageLedger
from devpilot.llm.rate_limiter import RateLimiter
from devpilot.llm.registry import get_registered_providers
from devpilot.llm.retry import execute_with_retry


async def main() -> int:
    configure_logging(level="INFO")
    logger = get_logger("smoke_test")
    print("=" * 65)
    print(" DevPilot Comprehensive Full-Pipeline Smoke Test (MockProvider)")
    print("=" * 65)

    # 1. Config & Settings Check
    settings = get_settings()
    print(f"[OK] Settings loaded: env={settings.env}, default_provider={settings.llm.default_provider}")

    # 2. Registry Check
    providers = get_registered_providers()
    print(f"[OK] Registered providers: {', '.join(providers)}")
    assert len(providers) >= 7, "Expected at least 7 providers registered"

    # 3. Provider Factory & Basic Invocations
    mock_llm = MockProvider(model="mock-agent-v1")
    messages = [
        Message.system("You are an autonomous repository agent."),
        Message.user("Analyze the repository structure."),
    ]
    chat_resp = await mock_llm.chat(messages)
    print(f"[OK] Chat invocation returned from {chat_resp.provider}/{chat_resp.model}: {chat_resp.message.content}")

    # 4. Streaming & Rate Limiting Check
    stream_tokens = []
    async for chunk in mock_llm.stream(messages):
        if chunk.delta_text:
            stream_tokens.append(chunk.delta_text)
    print(f"[OK] Streaming verified: received {len(stream_tokens)} token chunks")

    limiter = RateLimiter(requests_per_minute=120, max_concurrency=5)
    await limiter.acquire(estimated_tokens=100)
    limiter.release()
    print("[OK] Rate limiter verified")

    # 5. Retry Handler Check
    retry_count = 0

    async def flaky_op() -> str:
        nonlocal retry_count
        retry_count += 1
        if retry_count < 2:
            from devpilot.core.exceptions import LLMProviderUnavailableError

            raise LLMProviderUnavailableError("Temporary upstream timeout")
        return "recovered"

    recovery_res = await execute_with_retry(flaky_op, max_retries=2, min_backoff_sec=0.01)
    assert recovery_res == "recovered"
    print(f"[OK] Retry handler verified: recovered after {retry_count} attempts")

    # 6. Full Agent Runtime End-to-End Execution
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_dir = Path(tmp_dir)
        (repo_dir / "calculator.py").write_text(
            "def divide(a, b):\n    return a / b\n", encoding="utf-8"
        )
        (repo_dir / "test_calculator.py").write_text(
            "from calculator import divide\n\ndef test_divide():\n    assert divide(10, 2) == 5\n",
            encoding="utf-8",
        )

        agent_llm = MockProvider(model="mock-agent-v1")
        # Script the agent to execute a read_file and then complete
        agent_llm.queue_tool_call(
            name="read_file",
            arguments={"path": "calculator.py", "start_line": 1, "end_line": 10},
        )
        agent_llm.queue_response(
            "Read the file successfully. Everything is in order."
        )

        runtime = AgentRuntime(
            session_id="smoke_session_1",
            repo_root=repo_dir,
            llm=agent_llm,
            preset=AgentConfigPreset.BASIC,
        )

        result = await runtime.run("Inspect calculator.py")
        print(f"[OK] Full Agent Pipeline completed with status: {result.get('status')}")
        assert result.get("status") in ("COMPLETED", "UNVERIFIED")

    # 7. Usage Ledger Check
    ledger = UsageLedger()
    await ledger.record_usage(
        record_id="smoke_rec_1",
        provider="mock",
        model="mock-agent-v1",
        usage=chat_resp.usage,
        cost_usd=chat_resp.cost_usd,
        session_id="smoke_session",
    )
    summary = await ledger.get_summary()
    print(f"[OK] Usage ledger verified: {summary['total_requests']} requests, {summary['total_tokens']} tokens")

    print("=" * 65)
    print(" ALL END-TO-END DEVPILOT SMOKE TESTS PASSED CLEANLY! ")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
