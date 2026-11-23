"""Integration tests for Agent Runtime, ReAct execution loop, and state machine."""

from pathlib import Path

import pytest

from devpilot.agent.context_manager import ContextWindowManager
from devpilot.agent.events import AgentEvent, AgentEventType
from devpilot.agent.runtime import AgentRuntime
from devpilot.core.types import AgentConfigPreset, AgentStateEnum, PermissionMode
from devpilot.llm.adapters.mock import MockProvider
from devpilot.llm.base import Message, Role, ToolCall


@pytest.fixture
def repo_dir(tmp_path: Path) -> Path:
    (tmp_path / "server.py").write_text("def run():\n    return 'old_version'\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_server.py").write_text(
        "from server import run\ndef test_server():\n    assert run() == 'new_version'\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.mark.asyncio
async def test_agent_runtime_success_flow(repo_dir: Path):
    mock_llm = MockProvider(model="mock-agent")

    # Round 1: Model calls read_file
    mock_llm.queue_tool_call(
        name="read_file",
        arguments={"path": "server.py"},
        content="Inspecting server.py",
    )
    # Round 2: Model calls edit_file
    mock_llm.queue_tool_call(
        name="edit_file",
        arguments={
            "path": "server.py",
            "target": "return 'old_version'",
            "replacement": "return 'new_version'",
        },
        content="Updating server.py to return new_version",
    )
    # Round 3: Model states completion (no tool calls)
    mock_llm.queue_response(content="Task completed: updated server.py to new_version.")

    emitted_events: list[AgentEvent] = []

    def on_event(evt: AgentEvent):
        emitted_events.append(evt)

    runtime = AgentRuntime(
        session_id="test_session_1",
        repo_root=repo_dir,
        llm=mock_llm,
        preset=AgentConfigPreset.FULL,
        event_callback=on_event,
    )

    result = await runtime.run("Update server.py to return 'new_version'")

    assert result["status"] == "COMPLETED"
    assert "server.py" in result["modified_files"]
    assert runtime.fsm.current_state == AgentStateEnum.DONE

    # Verify event stream
    event_types = [e.type for e in emitted_events]
    assert AgentEventType.STATE_CHANGE in event_types
    assert AgentEventType.RETRIEVAL in event_types
    assert AgentEventType.TOOL_CALL in event_types
    assert AgentEventType.TOOL_RESULT in event_types
    assert AgentEventType.FINAL in event_types


@pytest.mark.asyncio
async def test_agent_runtime_recover_then_success(repo_dir: Path):
    mock_llm = MockProvider(model="mock-agent")

    # Round 1: Model calls edit_file with failing target (not found)
    mock_llm.queue_tool_call(
        name="edit_file",
        arguments={"path": "server.py", "target": "NON_EXISTENT", "replacement": "new"},
        content="Attempting bad edit",
    )
    # Round 2: Model recovers and calls edit_file with correct target
    mock_llm.queue_tool_call(
        name="edit_file",
        arguments={
            "path": "server.py",
            "target": "return 'old_version'",
            "replacement": "return 'new_version'",
        },
        content="Correcting edit target",
    )
    # Round 3: Model finishes
    mock_llm.queue_response(content="Finished recovery and edit.")

    runtime = AgentRuntime(
        session_id="test_recover_session",
        repo_root=repo_dir,
        llm=mock_llm,
        preset=AgentConfigPreset.FULL,
    )

    result = await runtime.run("Fix server.py")
    assert result["status"] == "COMPLETED"
    assert result["recoveries_count"] == 1


@pytest.mark.asyncio
async def test_agent_runtime_read_only_blocks_mutations(repo_dir: Path):
    mock_llm = MockProvider(model="mock-agent")

    # Model tries to edit a file under READ_ONLY mode
    mock_llm.queue_tool_call(
        name="edit_file",
        arguments={"path": "server.py", "target": "old", "replacement": "new"},
        content="Attempting edit under read-only mode",
    )
    mock_llm.queue_response(content="Acknowledged read-only restriction.")

    runtime = AgentRuntime(
        session_id="test_ro_session",
        repo_root=repo_dir,
        llm=mock_llm,
        preset=AgentConfigPreset.FULL,
        permission_mode=PermissionMode.READ_ONLY,
    )

    result = await runtime.run("Modify server.py")
    assert len(result["modified_files"]) == 0
    # The tool result message must record permission denied
    tool_msgs = [m for m in runtime.messages if m.role == Role.TOOL]
    assert len(tool_msgs) >= 1
    assert "Permission denied" in (tool_msgs[0].content or "")


@pytest.mark.asyncio
async def test_agent_runtime_approval_timeout_denies(repo_dir: Path):
    mock_llm = MockProvider(model="mock-agent")

    # Under AUTO_SAFE, run_command requires approval
    mock_llm.queue_tool_call(
        name="run_command",
        arguments={"command": "python -c 'print(1)'"},
        content="Attempting command",
    )
    mock_llm.queue_response(content="Command finished or rejected.")

    events: list[AgentEvent] = []
    runtime = AgentRuntime(
        session_id="test_approval_session",
        repo_root=repo_dir,
        llm=mock_llm,
        preset=AgentConfigPreset.FULL,
        permission_mode=PermissionMode.AUTO_SAFE,
        approval_timeout_sec=0.1,  # Fast timeout for test
        event_callback=events.append,
    )

    await runtime.run("Run command")
    # Verify approval request was emitted
    approval_events = [e for e in events if e.type == AgentEventType.APPROVAL_REQUEST]
    assert len(approval_events) == 1
    # Verify tool result contains rejection/timeout message
    tool_msgs = [m for m in runtime.messages if m.role == Role.TOOL]
    assert len(tool_msgs) >= 1
    assert "rejected or timed out" in (tool_msgs[0].content or "")


@pytest.mark.asyncio
async def test_agent_runtime_multi_tool_call_skipped_results(repo_dir: Path):
    mock_llm = MockProvider(model="mock-agent")

    # Queue two tool calls in the same assistant response
    mock_llm.queue_response(
        content="Attempting two tool calls",
        tool_calls=[
            ToolCall(
                id="tc_1",
                name="edit_file",
                arguments={"path": "server.py", "target": "NON_EXISTENT", "replacement": "x"},
            ),
            ToolCall(
                id="tc_2",
                name="edit_file",
                arguments={"path": "server.py", "target": "second", "replacement": "y"},
            ),
        ],
    )
    mock_llm.queue_response(content="Finished after error.")

    runtime = AgentRuntime(
        session_id="test_batch_session",
        repo_root=repo_dir,
        llm=mock_llm,
        preset=AgentConfigPreset.FULL,
    )

    await runtime.run("Run batch")
    # Both tool calls must have corresponding tool results
    tool_msgs = [m for m in runtime.messages if m.role == Role.TOOL]
    assert len(tool_msgs) >= 2
    # Second tool call must be marked as skipped
    assert "Skipped: previous tool call in batch failed" in (tool_msgs[1].content or "")


def test_context_window_manager_compaction():
    mgr = ContextWindowManager(max_context_tokens=100, trigger_ratio=0.5)

    messages = [
        Message.system("System prompt"),
        Message.user("Initial task"),
    ]
    # Add 10 conversational turns with large text
    for i in range(10):
        messages.append(Message.assistant(content=f"Step {i}: " + ("text " * 30)))
        messages.append(Message.user(content=f"Feedback {i}: " + ("text " * 30)))

    compacted = mgr.compact_history_if_needed(messages, modified_files={"server.py"})
    assert len(compacted) < len(messages)
    assert compacted[0].role == Role.SYSTEM
    assert any("CONTEXT COMPACTED" in (m.content or "") for m in compacted)


@pytest.mark.asyncio
async def test_agent_runtime_step_cap_limit(repo_dir: Path):
    mock_llm = MockProvider(model="mock-agent")
    # Queue multiple repeated tool calls to exceed max_steps=2
    for _ in range(5):
        mock_llm.queue_tool_call(
            name="read_file", arguments={"path": "server.py"}, content="reading"
        )

    runtime = AgentRuntime(
        session_id="test_step_cap",
        repo_root=repo_dir,
        llm=mock_llm,
        max_steps=2,
    )
    result = await runtime.run("Task")
    assert result["status"] == "FAILED"
    assert "MAX_STEPS_EXCEEDED" in result.get("reason", "")
    assert runtime.fsm.current_state == AgentStateEnum.FAILED


@pytest.mark.asyncio
async def test_agent_runtime_timeout_limit(repo_dir: Path):
    mock_llm = MockProvider(model="mock-agent")
    mock_llm.queue_tool_call(name="read_file", arguments={"path": "server.py"}, content="reading")

    runtime = AgentRuntime(
        session_id="test_timeout",
        repo_root=repo_dir,
        llm=mock_llm,
        timeout_sec=0.001,  # immediate timeout
    )
    # Artificial small sleep to ensure elapsed > timeout_sec
    import asyncio

    await asyncio.sleep(0.01)

    result = await runtime.run("Task")
    assert result["status"] == "FAILED"
    assert (
        "TIMEOUT_EXCEEDED" in result.get("reason", "")
        or "timed out" in result.get("reason", "").lower()
    )
    assert runtime.fsm.current_state == AgentStateEnum.FAILED


@pytest.mark.asyncio
async def test_agent_runtime_token_cap_limit(repo_dir: Path):
    from devpilot.llm.base import ChatResponse, TokenUsage

    class HeavyTokenMockProvider(MockProvider):
        async def chat(self, messages, tools=None):
            return ChatResponse(
                message=Message.assistant(content="Large prompt processing"),
                usage=TokenUsage(
                    prompt_tokens=50_000, completion_tokens=60_000, total_tokens=110_000
                ),
                cost_usd=0.05,
                provider="mock",
                model="mock-model",
            )

    heavy_llm = HeavyTokenMockProvider()
    runtime = AgentRuntime(
        session_id="test_token_cap",
        repo_root=repo_dir,
        llm=heavy_llm,
        max_total_tokens=100_000,
    )
    result = await runtime.run("Task")
    assert result["status"] == "FAILED"
    assert "TOKEN_LIMIT_EXCEEDED" in result.get("reason", "")
    assert runtime.fsm.current_state == AgentStateEnum.FAILED


@pytest.mark.asyncio
async def test_agent_runtime_cost_cap_limit(repo_dir: Path):
    from devpilot.llm.base import ChatResponse, TokenUsage

    class ExpensiveMockProvider(MockProvider):
        async def chat(self, messages, tools=None):
            return ChatResponse(
                message=Message.assistant(content="Expensive reasoning step"),
                usage=TokenUsage(prompt_tokens=100, completion_tokens=100, total_tokens=200),
                cost_usd=5.00,  # Exceeds max_cost_usd=1.0
                provider="mock",
                model="mock-model",
            )

    expensive_llm = ExpensiveMockProvider()
    runtime = AgentRuntime(
        session_id="test_cost_cap",
        repo_root=repo_dir,
        llm=expensive_llm,
        max_cost_usd=1.0,
    )
    result = await runtime.run("Task")
    assert result["status"] == "FAILED"
    assert "COST_BUDGET_EXCEEDED" in result.get("reason", "")
    assert runtime.fsm.current_state == AgentStateEnum.FAILED


@pytest.mark.asyncio
async def test_agent_runtime_verification_unverified(tmp_path: Path):
    # Repository with NO test harness (no pytest, no tests dir)
    no_test_repo = tmp_path / "simple_repo"
    no_test_repo.mkdir()
    (no_test_repo / "script.py").write_text("print('hello')\n", encoding="utf-8")

    mock_llm = MockProvider(model="mock-agent")
    mock_llm.queue_tool_call(
        name="edit_file",
        arguments={
            "path": "script.py",
            "target": "print('hello')",
            "replacement": "print('world')",
        },
        content="Editing script without tests",
    )
    mock_llm.queue_response(content="Finished edit.")

    runtime = AgentRuntime(
        session_id="test_unverified_session",
        repo_root=no_test_repo,
        llm=mock_llm,
    )
    result = await runtime.run("Update script")
    # Must report UNVERIFIED since no test suite could verify changes
    assert result["status"] == "UNVERIFIED"
    assert result["verification_status"] == "UNVERIFIED"
    assert "script.py" in result["modified_files"]


@pytest.mark.asyncio
async def test_agent_runtime_session_store_persistence(repo_dir: Path, tmp_path: Path):
    from devpilot.session.store import SessionStore

    db_path = tmp_path / "sessions.db"
    store = SessionStore(db_path)

    mock_llm = MockProvider(model="mock-agent")
    mock_llm.queue_tool_call(
        name="read_file", arguments={"path": "server.py"}, content="reading server.py"
    )
    mock_llm.queue_response(content="Done reading.")

    runtime = AgentRuntime(
        session_id="test_persist_sess",
        repo_root=repo_dir,
        llm=mock_llm,
        session_store=store,
    )
    result = await runtime.run("Read server.py")
    assert result["status"] == "COMPLETED"

    # Verify session persisted in SQLite
    sess = await store.get_session("test_persist_sess")
    assert sess is not None
    assert sess.status == "COMPLETED"

    # Verify messages persisted
    msgs = await store.get_messages("test_persist_sess")
    assert len(msgs) >= 3

    # Verify tool calls persisted
    tool_calls = await store.get_tool_calls("test_persist_sess")
    assert len(tool_calls) >= 1
    assert tool_calls[0]["tool_name"] == "read_file"
    assert tool_calls[0]["ok"] == 1

    # Verify snapshot recorded
    snaps = await store.get_snapshots("test_persist_sess")
    assert len(snaps) >= 1
    assert snaps[0]["id"] == "baseline"


@pytest.mark.asyncio
async def test_agent_runtime_resume_and_rollback(repo_dir: Path, tmp_path: Path):
    from devpilot.session.store import SessionStore

    db_path = tmp_path / "sessions.db"
    store = SessionStore(db_path)

    # Initial session modifies server.py and pauses after step 1
    mock_llm_1 = MockProvider(model="mock-agent")
    mock_llm_1.queue_tool_call(
        name="edit_file",
        arguments={
            "path": "server.py",
            "target": "return 'old_version'",
            "replacement": "return 'v2'",
        },
        content="modifying to v2",
    )
    mock_llm_1.queue_tool_call(
        name="read_file",
        arguments={"path": "server.py"},
        content="inspecting v2",
    )

    runtime_1 = AgentRuntime(
        session_id="resume_sess_1",
        repo_root=repo_dir,
        llm=mock_llm_1,
        session_store=store,
        max_steps=1,  # Step cap stops the run cleanly after step 1
    )
    await runtime_1.run("Start task")
    assert "return 'v2'" in (repo_dir / "server.py").read_text(encoding="utf-8")

    # Test rollback to baseline
    restored = runtime_1.rollback("baseline")
    assert len(restored) >= 1
    assert "return 'old_version'" in (repo_dir / "server.py").read_text(encoding="utf-8")
    assert len(runtime_1.fsm.data.modified_files) == 0

    # Test resume creates new runtime with loaded messages and executes to completion
    mock_llm_2 = MockProvider(model="mock-agent")
    mock_llm_2.queue_tool_call(
        name="edit_file",
        arguments={
            "path": "server.py",
            "target": "return 'old_version'",
            "replacement": "return 'new_version'",
        },
        content="finishing via resume",
    )
    mock_llm_2.queue_response(content="Finished resumed run.")

    runtime_2 = AgentRuntime(
        session_id="resume_sess_1",
        repo_root=repo_dir,
        llm=mock_llm_2,
        session_store=store,
    )
    res = await runtime_2.resume()
    assert res["status"] == "COMPLETED"
    assert "return 'new_version'" in (repo_dir / "server.py").read_text(encoding="utf-8")
