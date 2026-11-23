"""Complete Agent Runtime coordinating the FSM, ReAct execution loop, and event streaming."""

import asyncio
import inspect
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from devpilot.agent.context_manager import ContextWindowManager
from devpilot.agent.events import AgentEvent, AgentEventType
from devpilot.agent.prompts import get_system_prompt
from devpilot.agent.state import AgentStateMachine
from devpilot.context.chunker import SymbolChunker
from devpilot.context.fixed_rag import FixedTopKRetriever
from devpilot.context.hybrid import AdaptiveHybridRetriever
from devpilot.context.no_retrieval import NoRetrieval
from devpilot.context.retriever import Retriever
from devpilot.core.logging import get_logger
from devpilot.core.types import (
    AgentConfigPreset,
    AgentStateEnum,
    ErrorTypeEnum,
    PermissionMode,
    ToolResult,
)
from devpilot.llm.base import LLMProvider, Message, Role, ToolCall
from devpilot.recovery.policy import EscalationLevel, RecoveryPolicy
from devpilot.repo.index import RepoIndex
from devpilot.safety.redactor import SecretRedactor
from devpilot.safety.snapshots import SnapshotManager
from devpilot.session.store import SessionRecord, SessionStore
from devpilot.tools.registry import ToolRegistry, get_default_tool_registry
from devpilot.verify.runner import VerificationRunner

logger = get_logger("devpilot.agent.runtime")


class AgentRuntime:
    """Production agent execution harness orchestrating LLM, context engine, tools, and recovery."""

    def __init__(
        self,
        session_id: str,
        repo_root: Path,
        llm: LLMProvider,
        preset: AgentConfigPreset = AgentConfigPreset.FULL,
        permission_mode: PermissionMode = PermissionMode.AUTO_SAFE,
        approval_timeout_sec: float = 30.0,
        tool_registry: ToolRegistry | None = None,
        retriever: Retriever | None = None,
        session_store: SessionStore | None = None,
        max_steps: int = 30,
        max_total_tokens: int = 100_000,
        timeout_sec: float = 600.0,
        max_cost_usd: float = 2.0,
        event_callback: Callable[[AgentEvent], Any] | None = None,
    ) -> None:
        self.session_id = session_id
        self.repo_root = repo_root.resolve()
        self.llm = llm
        self.preset = preset
        self.permission_mode = permission_mode
        self.approval_timeout_sec = approval_timeout_sec
        self.max_steps = max_steps
        self.max_total_tokens = max_total_tokens
        self.timeout_sec = timeout_sec
        self.max_cost_usd = max_cost_usd
        self.event_callback = event_callback
        self.session_store = session_store

        self.fsm = AgentStateMachine(session_id=session_id)
        self.tool_registry = tool_registry or get_default_tool_registry(
            self.repo_root, permission_mode=self.permission_mode
        )
        self.recovery_policy = RecoveryPolicy()
        self.context_manager = ContextWindowManager()
        self.snapshot_manager = SnapshotManager(
            self.tool_registry.tools["read_file"].sandbox  # type: ignore[attr-defined]
        )
        self.verification_runner = VerificationRunner(self.repo_root)

        self.repo_index = RepoIndex(self.repo_root)
        self.retriever = retriever
        self.messages: list[Message] = []
        self.pending_approval_event: asyncio.Event | None = None
        self.approval_decision: bool | None = None
        self.final_verification_status: str | None = None

    async def emit_event(self, event_type: AgentEventType, data: dict[str, Any]) -> AgentEvent:
        """Emits typed streaming event to callback or queue with secret redaction."""
        sanitized_data = SecretRedactor.redact_data(data)
        evt = AgentEvent(
            type=event_type,
            session_id=self.session_id,
            step=self.fsm.data.step,
            data=sanitized_data,
        )
        if self.event_callback:
            if inspect.iscoroutinefunction(self.event_callback):
                await self.event_callback(evt)
            else:
                self.event_callback(evt)
        return evt

    async def run(self, task_instruction: str) -> dict[str, Any]:
        """Executes full autonomous agent loop on given task instruction."""
        logger.info("agent_run_started", session=self.session_id, preset=self.preset.value)

        # Initialize session in persistent store if configured
        if self.session_store:
            provider_name = self.llm.__class__.__name__.lower().replace("provider", "")
            model_name = getattr(self.llm, "model", "default")
            await self.session_store.create_session(
                SessionRecord(
                    id=self.session_id,
                    status="IN_PROGRESS",
                    preset=self.preset.value,
                    provider=provider_name,
                    model=model_name,
                    metadata={"repo_root": str(self.repo_root), "task": task_instruction},
                )
            )

        # 1. State: INIT -> ANALYZE
        self.fsm.transition(AgentStateEnum.ANALYZE, "Beginning repository analysis")
        await self.emit_event(AgentEventType.STATE_CHANGE, {"state": AgentStateEnum.ANALYZE.value})

        # Scan & index repository
        self.repo_index.build_full_index()
        chunks = SymbolChunker.chunk_repository(self.repo_index)

        # Initialize Retriever based on configuration preset
        if self.retriever is None:
            if self.preset == AgentConfigPreset.BASIC:
                self.retriever = NoRetrieval()
            elif self.preset == AgentConfigPreset.FIXED_RAG:
                self.retriever = FixedTopKRetriever(chunks, k=5)
            else:
                self.retriever = AdaptiveHybridRetriever(chunks, graph=self.repo_index.graph)

        # 2. State: ANALYZE -> RETRIEVE
        self.fsm.transition(AgentStateEnum.RETRIEVE, "Querying relevant code context")
        await self.emit_event(AgentEventType.STATE_CHANGE, {"state": AgentStateEnum.RETRIEVE.value})

        retrieved_chunks, trace = await self.retriever.retrieve(task_instruction)
        await self.emit_event(AgentEventType.RETRIEVAL, trace.model_dump())

        # Assemble retrieved code context block with untrusted data boundary
        context_blocks = []
        for rc in retrieved_chunks:
            redacted_chunk = SecretRedactor.redact(rc.content)
            context_blocks.append(
                f'<untrusted_code_context file="{rc.file_path}" lines="{rc.start_line}-{rc.end_line}">\n{redacted_chunk}\n</untrusted_code_context>'
            )
        retrieved_context_str = "\n\n".join(context_blocks)

        # Initialize conversation messages
        system_content = get_system_prompt(self.repo_index.summary, retrieved_context_str)
        self.messages = [
            Message.system(system_content),
            Message.user(f"Task Instruction:\n{task_instruction}"),
        ]

        if self.session_store:
            await self.session_store.record_message(
                self.session_id, Role.SYSTEM.value, system_content
            )
            await self.session_store.record_message(
                self.session_id, Role.USER.value, f"Task Instruction:\n{task_instruction}"
            )

        # Take base snapshot for rollback
        scan_files = self.repo_index.scan_result.files if self.repo_index.scan_result else []
        self.snapshot_manager.capture(
            "baseline", [f.rel_path for f in scan_files if not f.is_binary]
        )
        if self.session_store:
            await self.session_store.record_snapshot(
                self.session_id, "baseline", "Initial repository baseline snapshot"
            )

        # 3. State: RETRIEVE -> PLAN
        self.fsm.transition(AgentStateEnum.PLAN, "Planning solution steps")
        await self.emit_event(AgentEventType.STATE_CHANGE, {"state": AgentStateEnum.PLAN.value})

        return await self._run_react_loop()

    async def resume(self) -> dict[str, Any]:
        """Resumes an existing or interrupted session from the persistent store."""
        if not self.session_store:
            raise ValueError("Cannot resume session without a configured SessionStore")

        record = await self.session_store.get_session(self.session_id)
        if not record:
            raise ValueError(f"Session '{self.session_id}' not found in store")

        stored_messages = await self.session_store.get_messages(self.session_id)
        if not stored_messages:
            raise ValueError(f"No stored messages found for session '{self.session_id}'")

        # Restore messages
        self.messages = []
        for sm in stored_messages:
            role = Role(sm["role"])
            tc_data = json.loads(sm["tool_calls_json"]) if sm.get("tool_calls_json") else None
            tool_calls = None
            if tc_data:
                tool_calls = [ToolCall(**item) for item in tc_data]
            self.messages.append(Message(role=role, content=sm["content"], tool_calls=tool_calls))

        # Restore metrics
        self.fsm.data.step = record.steps
        self.fsm.data.total_cost_usd = record.total_cost_usd

        # Restore modified files from tool call history
        tcs = await self.session_store.get_tool_calls(self.session_id)
        for tc in tcs:
            if tc["ok"]:
                args = json.loads(tc["arguments_json"] or "{}")
                if tc["tool_name"] in ("edit_file", "create_file") and "path" in args:
                    self.fsm.data.modified_files.add(args["path"])
                elif tc["tool_name"] == "delete_file" and "path" in args:
                    self.fsm.data.modified_files.discard(args["path"])

        self.fsm.transition(AgentStateEnum.PLAN, "Resumed session from persistent store")
        await self.emit_event(AgentEventType.STATE_CHANGE, {"state": AgentStateEnum.PLAN.value})

        return await self._run_react_loop()

    def rollback(self, snapshot_id: str = "baseline") -> list[str]:
        """Restores files to a captured snapshot state and clears modified files on baseline."""
        if snapshot_id not in self.snapshot_manager.snapshots:
            if snapshot_id == "baseline":
                self.fsm.data.modified_files.clear()
                return []
            raise ValueError(f"Snapshot '{snapshot_id}' does not exist")
        restored = self.snapshot_manager.rollback(snapshot_id)
        if snapshot_id == "baseline":
            self.fsm.data.modified_files.clear()
        return restored

    async def _run_react_loop(self) -> dict[str, Any]:
        """Core ReAct loop with limit checks, structured recovery, and verification."""
        tool_defs = self.tool_registry.get_definitions()
        failure_reason: str | None = None

        while not self.fsm.is_terminal():
            self.fsm.data.step += 1
            step = self.fsm.data.step

            # 1. Enforce limits: Step cap, Timeout, Token cap, Cost cap
            elapsed_sec = time.monotonic() - self.fsm.data.start_time
            if elapsed_sec > self.timeout_sec:
                failure_reason = f"TIMEOUT_EXCEEDED: Execution timed out ({self.timeout_sec}s)"
                self.fsm.transition(AgentStateEnum.FAILED, failure_reason)
                await self.emit_event(
                    AgentEventType.ERROR, {"error": "TIMEOUT_EXCEEDED", "reason": failure_reason}
                )
                break

            if step > self.max_steps:
                failure_reason = f"MAX_STEPS_EXCEEDED: Maximum steps ({self.max_steps}) exceeded"
                self.fsm.transition(AgentStateEnum.FAILED, failure_reason)
                await self.emit_event(
                    AgentEventType.ERROR, {"error": "MAX_STEPS_EXCEEDED", "reason": failure_reason}
                )
                break

            total_tokens = self.fsm.data.total_prompt_tokens + self.fsm.data.total_completion_tokens
            if total_tokens > self.max_total_tokens:
                failure_reason = (
                    f"TOKEN_LIMIT_EXCEEDED: Total token budget ({self.max_total_tokens}) exceeded"
                )
                self.fsm.transition(AgentStateEnum.FAILED, failure_reason)
                await self.emit_event(
                    AgentEventType.ERROR,
                    {"error": "TOKEN_LIMIT_EXCEEDED", "reason": failure_reason},
                )
                break

            if self.fsm.data.total_cost_usd > self.max_cost_usd:
                failure_reason = (
                    f"COST_BUDGET_EXCEEDED: Cost budget (${self.max_cost_usd}) exceeded"
                )
                self.fsm.transition(AgentStateEnum.FAILED, failure_reason)
                await self.emit_event(
                    AgentEventType.ERROR,
                    {"error": "COST_BUDGET_EXCEEDED", "reason": failure_reason},
                )
                break

            # 2. Context compaction check
            self.messages = self.context_manager.compact_history_if_needed(
                self.messages,
                self.fsm.data.modified_files,
            )

            # 3. Invoke LLM
            try:
                response = await self.llm.chat(self.messages, tools=tool_defs)
            except Exception as exc:
                logger.error("llm_invocation_failed", error=str(exc))
                failure_reason = f"LLM error: {exc}"
                await self.emit_event(AgentEventType.ERROR, {"error": str(exc)})
                self.fsm.transition(AgentStateEnum.FAILED, failure_reason)
                break

            # Record usage
            self.fsm.data.total_prompt_tokens += response.usage.prompt_tokens
            self.fsm.data.total_completion_tokens += response.usage.completion_tokens
            self.fsm.data.total_cost_usd = round(
                self.fsm.data.total_cost_usd + response.cost_usd, 6
            )

            # Check token and cost caps immediately after usage update
            total_tokens = self.fsm.data.total_prompt_tokens + self.fsm.data.total_completion_tokens
            if total_tokens > self.max_total_tokens:
                failure_reason = (
                    f"TOKEN_LIMIT_EXCEEDED: Total token budget ({self.max_total_tokens}) exceeded"
                )
                self.fsm.transition(AgentStateEnum.FAILED, failure_reason)
                await self.emit_event(
                    AgentEventType.ERROR,
                    {"error": "TOKEN_LIMIT_EXCEEDED", "reason": failure_reason},
                )
                break

            if self.fsm.data.total_cost_usd > self.max_cost_usd:
                failure_reason = (
                    f"COST_BUDGET_EXCEEDED: Cost budget (${self.max_cost_usd}) exceeded"
                )
                self.fsm.transition(AgentStateEnum.FAILED, failure_reason)
                await self.emit_event(
                    AgentEventType.ERROR,
                    {"error": "COST_BUDGET_EXCEEDED", "reason": failure_reason},
                )
                break

            await self.emit_event(
                AgentEventType.USAGE,
                {
                    "step": step,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "step_cost_usd": response.cost_usd,
                    "total_cost_usd": self.fsm.data.total_cost_usd,
                },
            )

            asst_msg = response.message
            self.messages.append(asst_msg)

            if self.session_store:
                tc_json = (
                    json.dumps([tc.model_dump() for tc in asst_msg.tool_calls])
                    if asst_msg.tool_calls
                    else None
                )
                await self.session_store.record_message(
                    self.session_id, asst_msg.role.value, asst_msg.content, tc_json
                )

            if asst_msg.content:
                await self.emit_event(AgentEventType.THOUGHT, {"thought": asst_msg.content})

            # Check if model requested tool execution
            if not asst_msg.tool_calls:
                # No more tools called: transition to VERIFY then DONE
                if self.fsm.current_state in (
                    AgentStateEnum.ACT,
                    AgentStateEnum.OBSERVE,
                    AgentStateEnum.PLAN,
                ):
                    if self.fsm.data.modified_files:
                        self.fsm.transition(
                            AgentStateEnum.VERIFY, "Verifying changes with test suite"
                        )
                        await self.emit_event(
                            AgentEventType.STATE_CHANGE, {"state": AgentStateEnum.VERIFY.value}
                        )

                        # Run test suite via VerificationRunner
                        report = await self.verification_runner.run_verification(
                            modified_files=list(self.fsm.data.modified_files)
                        )

                        if report.status == "UNVERIFIED":
                            self.final_verification_status = "UNVERIFIED"
                            self.fsm.transition(
                                AgentStateEnum.DONE,
                                "Task completed without automated verification (no test harness detected)",
                            )
                            await self.emit_event(
                                AgentEventType.STATE_CHANGE, {"state": AgentStateEnum.DONE.value}
                            )
                            break
                        elif report.passed:
                            self.final_verification_status = "VERIFIED"
                            self.fsm.transition(
                                AgentStateEnum.DONE, "All verification tests passed"
                            )
                            await self.emit_event(
                                AgentEventType.STATE_CHANGE, {"state": AgentStateEnum.DONE.value}
                            )
                            break
                        else:
                            # Tests failed: engage structured recovery
                            self.final_verification_status = "FAILED"
                            self.fsm.transition(
                                AgentStateEnum.RECOVER, "Verification test suite failed"
                            )
                            rec_action = self.recovery_policy.handle_tool_error(
                                "verification",
                                {},
                                ToolResult(
                                    ok=False,
                                    output=report.stdout,
                                    error_type=ErrorTypeEnum.TEST_FAILURE,
                                    exit_code=1,
                                    duration_ms=report.duration_ms,
                                    truncated=False,
                                ),
                            )
                            if self.session_store:
                                await self.session_store.record_recovery_event(
                                    self.session_id,
                                    rec_action.level.name,
                                    rec_action.error_type.value,
                                    rec_action.error_signature,
                                    rec_action.feedback_message,
                                    rec_action.should_abort,
                                )
                            await self.emit_event(
                                AgentEventType.RECOVERY,
                                {
                                    "level": rec_action.level.value,
                                    "feedback": rec_action.feedback_message,
                                },
                            )
                            if (
                                rec_action.should_abort
                                or self.recovery_policy.total_recoveries
                                >= self.recovery_policy.global_retry_cap
                            ):
                                failure_reason = "Verification failed and retry cap exhausted"
                                self.fsm.transition(AgentStateEnum.FAILED, failure_reason)
                                break

                            self.messages.append(Message.user(rec_action.feedback_message))
                            if self.session_store:
                                await self.session_store.record_message(
                                    self.session_id, Role.USER.value, rec_action.feedback_message
                                )
                            self.fsm.transition(
                                AgentStateEnum.PLAN, "Replanning after verification failure"
                            )
                            continue
                    else:
                        self.final_verification_status = "NO_MODIFICATIONS"
                        self.fsm.transition(AgentStateEnum.DONE, "Task completed successfully")
                        await self.emit_event(
                            AgentEventType.STATE_CHANGE, {"state": AgentStateEnum.DONE.value}
                        )
                break

            # Transition: PLAN / OBSERVE -> ACT
            if self.fsm.current_state != AgentStateEnum.ACT:
                self.fsm.transition(AgentStateEnum.ACT, "Executing requested tools")
                await self.emit_event(
                    AgentEventType.STATE_CHANGE, {"state": AgentStateEnum.ACT.value}
                )

            # Execute tool calls in batch
            batch_aborted = False
            for idx, tc in enumerate(asst_msg.tool_calls):
                tc_args = tc.get_arguments_dict()
                await self.emit_event(
                    AgentEventType.TOOL_CALL,
                    {
                        "id": tc.id,
                        "name": tc.name,
                        "arguments": tc_args,
                    },
                )

                # Check permissions
                perm = self.tool_registry.permission_manager.check(tc.name, tc_args)
                tool_result: ToolResult | None = None

                if perm.requires_approval:
                    self.pending_approval_event = asyncio.Event()
                    self.approval_decision = None
                    await self.emit_event(
                        AgentEventType.APPROVAL_REQUEST,
                        {
                            "tool_call_id": tc.id,
                            "tool_name": tc.name,
                            "arguments": tc_args,
                            "reason": perm.reason,
                        },
                    )
                    try:
                        await asyncio.wait_for(
                            self.pending_approval_event.wait(),
                            timeout=self.approval_timeout_sec,
                        )
                    except TimeoutError:
                        self.approval_decision = False

                    if not self.approval_decision:
                        tool_result = ToolResult(
                            ok=False,
                            output=f"Tool execution rejected or timed out: {perm.reason}",
                            error_type=ErrorTypeEnum.PERMISSION,
                            exit_code=1,
                            duration_ms=0.0,
                            truncated=False,
                        )
                elif not perm.allowed:
                    tool_result = ToolResult(
                        ok=False,
                        output=f"Permission denied: {perm.reason}",
                        error_type=ErrorTypeEnum.PERMISSION,
                        exit_code=1,
                        duration_ms=0.0,
                        truncated=False,
                    )

                # Execute tool if not blocked by permission
                if tool_result is None:
                    # Capture baseline snapshot before any modifying tool execution
                    if tc.name in ("edit_file", "create_file", "delete_file"):
                        rel_p = str(tc_args.get("path", ""))
                        if rel_p:
                            if "baseline" not in self.snapshot_manager.snapshots:
                                self.snapshot_manager.capture(
                                    "baseline", [rel_p], description="Pre-modification baseline"
                                )
                            else:
                                snap = self.snapshot_manager.snapshots["baseline"]
                                if rel_p not in snap.file_contents:
                                    target = self.snapshot_manager.sandbox.resolve_safe_path(rel_p)
                                    snap.file_contents[rel_p] = (
                                        target.read_bytes()
                                        if (target.exists() and target.is_file())
                                        else None
                                    )

                    try:
                        tool_result = await self.tool_registry.execute(tc.name, tc_args)
                    except Exception as exc:
                        logger.error(
                            "tool_execution_unhandled_exception", tool=tc.name, error=str(exc)
                        )
                        tool_result = ToolResult(
                            ok=False,
                            output=f"Unhandled tool execution error: {exc}",
                            error_type=ErrorTypeEnum.UNKNOWN,
                            exit_code=1,
                            duration_ms=0.0,
                            truncated=False,
                        )

                # Track modified files
                if tool_result.ok:
                    if tc.name in ("edit_file", "create_file") and "path" in tc_args:
                        self.fsm.data.modified_files.add(tc_args["path"])
                    elif tc.name == "delete_file" and "path" in tc_args:
                        self.fsm.data.modified_files.discard(tc_args["path"])

                # Persist tool call in session store
                if self.session_store:
                    await self.session_store.record_tool_call(
                        session_id=self.session_id,
                        call_id=tc.id,
                        tool_name=tc.name,
                        arguments_json=json.dumps(tc_args),
                        ok=tool_result.ok,
                        output=tool_result.output,
                        duration_ms=tool_result.duration_ms,
                    )

                await self.emit_event(
                    AgentEventType.TOOL_RESULT,
                    {
                        "tool_call_id": tc.id,
                        "tool_name": tc.name,
                        "ok": tool_result.ok,
                        "output": tool_result.output[:1000],
                        "duration_ms": tool_result.duration_ms,
                        "truncated": tool_result.truncated,
                    },
                )

                # Append tool observation with untrusted data boundary and redaction
                sanitized_output = SecretRedactor.redact(tool_result.output)
                wrapped_tool_out = f'<untrusted_tool_output tool_name="{tc.name}">\n{sanitized_output}\n</untrusted_tool_output>'
                self.messages.append(Message.tool_result(tc.id, wrapped_tool_out, tc.name))
                if self.session_store:
                    await self.session_store.record_message(
                        self.session_id, Role.TOOL.value, wrapped_tool_out
                    )

                # If tool failed, engage structured recovery ladder
                if not tool_result.ok:
                    batch_aborted = True
                    self.fsm.transition(AgentStateEnum.RECOVER, f"Tool '{tc.name}' error recovery")

                    # Crucial guarantee: any remaining calls in this batch receive a skipped result
                    for rem_tc in asst_msg.tool_calls[idx + 1 :]:
                        skip_msg = f'<untrusted_tool_output tool_name="{rem_tc.name}">\n[Skipped: previous tool call in batch failed]\n</untrusted_tool_output>'
                        self.messages.append(Message.tool_result(rem_tc.id, skip_msg, rem_tc.name))
                        if self.session_store:
                            await self.session_store.record_tool_call(
                                session_id=self.session_id,
                                call_id=rem_tc.id,
                                tool_name=rem_tc.name,
                                arguments_json="{}",
                                ok=False,
                                output="[Skipped: previous tool call in batch failed]",
                                duration_ms=0.0,
                            )
                            await self.session_store.record_message(
                                self.session_id, Role.TOOL.value, skip_msg
                            )

                    rec_action = self.recovery_policy.handle_tool_error(
                        tc.name, tc_args, tool_result
                    )

                    if self.session_store:
                        await self.session_store.record_recovery_event(
                            session_id=self.session_id,
                            level=rec_action.level.name,
                            error_type=rec_action.error_type.value,
                            signature=rec_action.error_signature,
                            feedback=rec_action.feedback_message,
                            abort=rec_action.should_abort,
                        )

                    await self.emit_event(
                        AgentEventType.RECOVERY,
                        {
                            "level": rec_action.level.value,
                            "error_type": rec_action.error_type.value,
                            "signature": rec_action.error_signature,
                            "feedback": rec_action.feedback_message,
                            "abort": rec_action.should_abort,
                        },
                    )

                    # Escalation Level 2: Re-retrieve context if requested
                    if (
                        rec_action.level == EscalationLevel.RE_RETRIEVE_CONTEXT
                        and rec_action.re_retrieve_query
                        and self.retriever
                    ):
                        try:
                            fresh_chunks, _ = await self.retriever.retrieve(
                                rec_action.re_retrieve_query
                            )
                            if fresh_chunks:
                                fresh_blocks = [
                                    f'<untrusted_code_context file="{c.file_path}" lines="{c.start_line}-{c.end_line}">\n{SecretRedactor.redact(c.content)}\n</untrusted_code_context>'
                                    for c in fresh_chunks
                                ]
                                fresh_ctx = "\n\n".join(fresh_blocks)
                                self.messages.append(
                                    Message.user(
                                        f"[FRESH RETRIEVED CONTEXT AFTER ERROR]:\n{fresh_ctx}"
                                    )
                                )
                        except Exception as r_exc:
                            logger.warning("re_retrieval_failed", error=str(r_exc))

                    # Escalation Level 3: Rollback to baseline checkpoint
                    if rec_action.level == EscalationLevel.SWITCH_APPROACH:
                        try:
                            restored = self.rollback("baseline")
                            rec_action.feedback_message += (
                                f"\n[ROLLBACK APPLIED]: Reverted workspace to clean baseline "
                                f"({len(restored)} files restored/deleted)."
                            )
                        except Exception as rb_exc:
                            logger.warning("rollback_failed", error=str(rb_exc))

                    if rec_action.should_abort:
                        failure_reason = "Recovery ladder aborted execution"
                        self.fsm.transition(AgentStateEnum.FAILED, failure_reason)
                        break

                    # Inject recovery guidance into messages
                    self.messages.append(Message.user(rec_action.feedback_message))
                    if self.session_store:
                        await self.session_store.record_message(
                            self.session_id, Role.USER.value, rec_action.feedback_message
                        )
                    self.fsm.transition(AgentStateEnum.PLAN, "Replanning after recovery feedback")
                    break

            # If not aborted, transition: ACT -> OBSERVE
            if (
                not batch_aborted
                and not self.fsm.is_terminal()
                and self.fsm.current_state == AgentStateEnum.ACT
            ):
                self.fsm.transition(AgentStateEnum.OBSERVE, "Observed tool outputs")
                await self.emit_event(
                    AgentEventType.STATE_CHANGE, {"state": AgentStateEnum.OBSERVE.value}
                )

            # Update session progress in store
            if self.session_store:
                await self.session_store.update_session_progress(
                    session_id=self.session_id,
                    status=self.fsm.current_state.value,
                    steps=self.fsm.data.step,
                    total_tokens=self.fsm.data.total_prompt_tokens
                    + self.fsm.data.total_completion_tokens,
                    total_cost_usd=self.fsm.data.total_cost_usd,
                )

        # Assemble Final Report
        is_success = self.fsm.current_state == AgentStateEnum.DONE
        final_status = (
            "UNVERIFIED"
            if (is_success and self.final_verification_status == "UNVERIFIED")
            else ("COMPLETED" if is_success else "FAILED")
        )
        total_time_sec = round(time.monotonic() - self.fsm.data.start_time, 2)

        final_data: dict[str, Any] = {
            "session_id": self.session_id,
            "status": final_status,
            "verification_status": self.final_verification_status or "NONE",
            "steps": self.fsm.data.step,
            "modified_files": sorted(self.fsm.data.modified_files),
            "total_prompt_tokens": self.fsm.data.total_prompt_tokens,
            "total_completion_tokens": self.fsm.data.total_completion_tokens,
            "total_tokens": (
                self.fsm.data.total_prompt_tokens + self.fsm.data.total_completion_tokens
            ),
            "total_cost_usd": self.fsm.data.total_cost_usd,
            "duration_sec": total_time_sec,
            "recoveries_count": self.recovery_policy.total_recoveries,
        }

        if not is_success:
            final_data["reason"] = failure_reason or "Execution stopped without success"

        if self.session_store:
            await self.session_store.update_session_progress(
                session_id=self.session_id,
                status=final_status,
                steps=self.fsm.data.step,
                total_tokens=final_data["total_tokens"],
                total_cost_usd=self.fsm.data.total_cost_usd,
            )

        await self.emit_event(AgentEventType.FINAL, final_data)
        logger.info("agent_run_finished", **final_data)
        return final_data
