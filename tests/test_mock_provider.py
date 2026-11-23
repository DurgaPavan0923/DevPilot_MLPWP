"""Unit tests for MockProvider deterministic behavior and streaming."""

import pytest

from devpilot.llm.adapters.mock import MockProvider


@pytest.mark.asyncio
async def test_mock_provider_default_chat(mock_provider: MockProvider, sample_messages):
    resp = await mock_provider.chat(sample_messages)
    assert resp.provider == "mock"
    assert resp.model == "mock-agent-model"
    assert resp.message.content is not None
    assert "Mock response" in resp.message.content
    assert resp.cost_usd == 0.0
    assert len(mock_provider.recorded_calls) == 1


@pytest.mark.asyncio
async def test_mock_provider_queued_tool_call(mock_provider: MockProvider, sample_messages):
    mock_provider.queue_tool_call(
        name="edit_file",
        arguments={"path": "server.py", "target": "old()", "replacement": "new()"},
        content="I am updating server.py",
    )

    resp = await mock_provider.chat(sample_messages)
    assert resp.finish_reason == "tool_calls"
    assert resp.message.content == "I am updating server.py"
    assert resp.message.tool_calls is not None
    assert len(resp.message.tool_calls) == 1
    assert resp.message.tool_calls[0].name == "edit_file"
    assert resp.message.tool_calls[0].arguments["path"] == "server.py"


@pytest.mark.asyncio
async def test_mock_provider_streaming(mock_provider: MockProvider, sample_messages):
    chunks = []
    async for chunk in mock_provider.stream(sample_messages):
        chunks.append(chunk)

    assert len(chunks) > 1
    assembled_text = "".join(c.delta_text for c in chunks if c.delta_text)
    assert "Mock streaming assistant output" in assembled_text
    final_chunk = chunks[-1]
    assert final_chunk.finish_reason == "stop"
    assert final_chunk.usage is not None
