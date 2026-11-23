"""FastAPI REST application and Server-Sent Events (SSE) stream server with safety hardening."""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from devpilot.agent.events import AgentEvent, AgentEventType
from devpilot.agent.runtime import AgentRuntime
from devpilot.config import get_settings
from devpilot.core.exceptions import SafetyError
from devpilot.core.types import AgentConfigPreset, AgentStateEnum, PermissionMode
from devpilot.llm.factory import create_provider
from devpilot.llm.registry import get_registered_providers
from devpilot.repo.index import RepoIndex
from devpilot.repo.scanner import RepoScanner
from devpilot.safety.sandbox import PathSandbox
from devpilot.session.store import SessionRecord, SessionStore

settings = get_settings()
app = FastAPI(
    title="DevPilot Harness API",
    description="REST and SSE streaming backend API for autonomous coding agent harness",
    version="0.1.0",
)

# CORS Configuration: strictly bounded to configured allowed origins (no wildcard with credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

session_store = SessionStore(settings.db_path)
session_event_queues: dict[str, list[asyncio.Queue[AgentEvent]]] = {}
active_runtimes: dict[str, AgentRuntime] = {}
active_tasks: dict[str, asyncio.Task[Any]] = {}
eval_runs_store: dict[str, dict[str, Any]] = {}
workspace_jail = PathSandbox(settings.api.workspace_root)


# Security Dependency: API key / Bearer authentication
async def verify_auth(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    authorization: str | None = Header(None),
) -> None:
    expected_key = settings.api.api_key
    if not expected_key:
        return

    if x_api_key == expected_key:
        return

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        if token == expected_key:
            return

    raise HTTPException(status_code=401, detail="Invalid or missing API authentication credentials")


# Schemas
class CreateSessionRequest(BaseModel):
    session_id: str | None = Field(
        default=None, description="Optional client session ID, generated if omitted"
    )
    preset: AgentConfigPreset = AgentConfigPreset.FULL
    provider: str = "mock"
    model: str = "mock-model"
    repo_path: str = "."
    permission_mode: PermissionMode = PermissionMode.AUTO_SAFE
    task: str | None = None


class StartTaskRequest(BaseModel):
    instruction: str


class ApprovalRequest(BaseModel):
    approved: bool
    reason: str | None = None


class RollbackRequest(BaseModel):
    snapshot_id: str = "baseline"


class LaunchEvalRequest(BaseModel):
    suite_path: str | None = None
    presets: list[str] = Field(default_factory=lambda: ["basic", "fixed_rag", "full"])
    seeds: list[int] = Field(default_factory=lambda: [42, 137, 2026])
    concurrency: int = 4
    limit: int | None = None


@app.get("/api/health")
async def health_check() -> dict[str, Any]:
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "0.1.0",
        "registered_providers": get_registered_providers(),
    }


@app.get("/api/providers", dependencies=[Depends(verify_auth)])
async def list_providers() -> dict[str, Any]:
    return {"providers": get_registered_providers()}


@app.get("/api/sessions", dependencies=[Depends(verify_auth)])
async def list_sessions(
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None, description="Filter sessions by status"),
) -> dict[str, Any]:
    all_sessions = await session_store.list_sessions(limit=limit)
    if status:
        filtered = [s for s in all_sessions if s.status.upper() == status.upper()]
    else:
        filtered = all_sessions
    return {"sessions": [s.model_dump() for s in filtered], "total": len(filtered)}


@app.post("/api/sessions", dependencies=[Depends(verify_auth)])
async def create_session(
    req: CreateSessionRequest, background_tasks: BackgroundTasks
) -> dict[str, Any]:
    session_id = req.session_id or f"sess_{uuid.uuid4().hex[:12]}"

    try:
        validated_repo_path = workspace_jail.resolve_safe_path(req.repo_path)
    except SafetyError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid repository path: {exc}") from exc

    session = SessionRecord(
        id=session_id,
        preset=req.preset.value,
        provider=req.provider,
        model=req.model,
        metadata={
            "repo_path": str(validated_repo_path),
            "permission_mode": req.permission_mode.value,
        },
    )
    await session_store.create_session(session)
    session_event_queues[session_id] = []

    # If task provided upfront, start execution immediately
    if req.task:
        background_tasks.add_task(_execute_task_job, session_id, req.task)

    return {"session": session.model_dump()}


async def _execute_task_job(session_id: str, instruction: str) -> None:
    session = await session_store.get_session(session_id)
    if not session:
        return

    repo_path = Path(session.metadata.get("repo_path", "."))
    llm = create_provider(session.provider, model=session.model)
    preset = AgentConfigPreset(session.preset)
    perm_mode = PermissionMode(
        session.metadata.get("permission_mode", PermissionMode.AUTO_SAFE.value)
    )

    async def broadcast_event(evt: AgentEvent) -> None:
        queues = session_event_queues.get(session_id, [])
        for q in queues:
            await q.put(evt)

    runtime = AgentRuntime(
        session_id=session_id,
        repo_root=repo_path,
        llm=llm,
        preset=preset,
        permission_mode=perm_mode,
        session_store=session_store,
        event_callback=broadcast_event,
    )
    active_runtimes[session_id] = runtime

    await session_store.update_session_status(session_id, "RUNNING")
    try:
        task_coro = asyncio.create_task(runtime.run(instruction))
        active_tasks[session_id] = task_coro
        res = await task_coro
        await session_store.update_session_progress(
            session_id,
            res["status"],
            steps=res["steps"],
            total_tokens=res["total_tokens"],
            total_cost_usd=res["total_cost_usd"],
        )
    except asyncio.CancelledError:
        await session_store.update_session_status(session_id, "STOPPED")
    except Exception as exc:
        await session_store.update_session_status(session_id, "FAILED")
        await broadcast_event(
            AgentEvent(
                type=AgentEventType.ERROR,
                session_id=session_id,
                data={"error": str(exc)},
            )
        )
    finally:
        active_tasks.pop(session_id, None)


@app.get("/api/sessions/{session_id}", dependencies=[Depends(verify_auth)])
async def get_session(session_id: str) -> dict[str, Any]:
    session = await session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    messages = await session_store.get_messages(session_id)
    tool_calls = await session_store.get_tool_calls(session_id)
    snapshots = await session_store.get_snapshots(session_id)
    recoveries = await session_store.get_recovery_events(session_id)

    return {
        "session": session.model_dump(),
        "messages": messages,
        "tool_calls": tool_calls,
        "snapshots": snapshots,
        "recovery_events": recoveries,
    }


@app.post("/api/sessions/{session_id}/tasks", dependencies=[Depends(verify_auth)])
async def start_task(
    session_id: str,
    req: StartTaskRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    session = await session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    background_tasks.add_task(_execute_task_job, session_id, req.instruction)
    return {"status": "TASK_STARTED", "session_id": session_id}


@app.post("/api/sessions/{session_id}/stop", dependencies=[Depends(verify_auth)])
async def stop_session(session_id: str) -> dict[str, Any]:
    task = active_tasks.get(session_id)
    if task and not task.done():
        task.cancel()
    runtime = active_runtimes.get(session_id)
    if runtime and not runtime.fsm.is_terminal():
        runtime.fsm.transition(AgentStateEnum.FAILED, "User cancelled execution")
    await session_store.update_session_status(session_id, "STOPPED")
    return {"status": "STOPPED", "session_id": session_id}


@app.post("/api/sessions/{session_id}/pause", dependencies=[Depends(verify_auth)])
async def pause_session(session_id: str) -> dict[str, Any]:
    runtime = active_runtimes.get(session_id)
    if runtime:
        runtime.fsm.data.is_paused = True
    await session_store.update_session_status(session_id, "PAUSED")
    return {"status": "PAUSED", "session_id": session_id}


@app.post("/api/sessions/{session_id}/resume", dependencies=[Depends(verify_auth)])
async def resume_session(session_id: str, background_tasks: BackgroundTasks) -> dict[str, Any]:
    session = await session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    messages = await session_store.get_messages(session_id)
    if not messages:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume session '{session_id}' because it has no recorded turns or messages",
        )

    async def _resume_job() -> None:
        repo_path = Path(session.metadata.get("repo_path", "."))
        llm = create_provider(session.provider, model=session.model)
        runtime = AgentRuntime(
            session_id=session_id,
            repo_root=repo_path,
            llm=llm,
            session_store=session_store,
        )
        active_runtimes[session_id] = runtime
        await session_store.update_session_status(session_id, "RUNNING")
        res = await runtime.resume()
        await session_store.update_session_progress(
            session_id,
            res["status"],
            steps=res["steps"],
            total_tokens=res["total_tokens"],
            total_cost_usd=res["total_cost_usd"],
        )

    background_tasks.add_task(_resume_job)
    return {"status": "RESUMED", "session_id": session_id}


@app.post("/api/sessions/{session_id}/rollback", dependencies=[Depends(verify_auth)])
async def rollback_session(session_id: str, req: RollbackRequest) -> dict[str, Any]:
    runtime = active_runtimes.get(session_id)
    session = await session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    if not runtime:
        repo_path = Path(session.metadata.get("repo_path", "."))
        runtime = AgentRuntime(
            session_id=session_id,
            repo_root=repo_path,
            llm=create_provider(session.provider, model=session.model),
            session_store=session_store,
        )

    try:
        restored = runtime.rollback(req.snapshot_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "ROLLBACK_COMPLETED", "restored_files": restored}


@app.get("/api/sessions/{session_id}/diff", dependencies=[Depends(verify_auth)])
async def get_session_diff(session_id: str) -> dict[str, Any]:
    runtime = active_runtimes.get(session_id)
    session = await session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    repo_path = Path(session.metadata.get("repo_path", "."))
    # Run git diff against baseline or HEAD
    proc = await asyncio.create_subprocess_exec(
        "git",
        "diff",
        cwd=str(repo_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    diff_text = stdout.decode("utf-8", errors="replace")

    return {
        "session_id": session_id,
        "diff": diff_text,
        "modified_files": sorted(runtime.fsm.data.modified_files) if runtime else [],
    }


@app.get("/api/sessions/{session_id}/events", dependencies=[Depends(verify_auth)])
async def stream_session_events(
    session_id: str,
    last_event_id: int | None = Query(None, description="Last received event step for reconnect"),
    offset: int = Query(0, description="Event offset for replay"),
) -> StreamingResponse:
    queue: asyncio.Queue[AgentEvent] = asyncio.Queue()
    session_event_queues.setdefault(session_id, []).append(queue)

    async def event_generator() -> AsyncIterator[str]:
        try:
            # Replay historical messages if client reconnected
            start_offset = last_event_id or offset
            if start_offset > 0:
                stored = await session_store.get_messages(session_id)
                for msg in stored[start_offset:]:
                    replay_evt = AgentEvent(
                        type=AgentEventType.THOUGHT,
                        session_id=session_id,
                        step=start_offset,
                        data={"replayed": True, "content": msg["content"]},
                    )
                    yield replay_evt.to_sse_line()

            # Initial ping event
            yield f'event: ping\ndata: {{"session_id": "{session_id}"}}\n\n'

            # Stream live events with 15-second heartbeat ping
            while True:
                try:
                    evt = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield evt.to_sse_line()
                    if evt.type == AgentEventType.FINAL:
                        break
                except TimeoutError:
                    yield f'event: ping\ndata: {{"timestamp": "{datetime.now(UTC).isoformat()}"}}\n\n'
        finally:
            if session_id in session_event_queues and queue in session_event_queues[session_id]:
                session_event_queues[session_id].remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/sessions/{session_id}/approval", dependencies=[Depends(verify_auth)])
async def submit_approval(session_id: str, req: ApprovalRequest) -> dict[str, Any]:
    runtime = active_runtimes.get(session_id)
    if not runtime:
        raise HTTPException(status_code=404, detail="Active runtime not found for session")

    runtime.approval_decision = req.approved
    if runtime.pending_approval_event:
        runtime.pending_approval_event.set()

    return {"status": "APPROVAL_RECORDED", "approved": req.approved}


# Repository inspection endpoints
@app.get("/api/repo/tree", dependencies=[Depends(verify_auth)])
async def get_repo_tree(path: str = ".") -> dict[str, Any]:
    try:
        safe_path = workspace_jail.resolve_safe_path(path)
    except SafetyError as exc:
        raise HTTPException(
            status_code=400, detail=f"Access denied outside workspace jail: {exc}"
        ) from exc

    scanner = RepoScanner(safe_path)
    scan = scanner.scan()
    return {
        "repo_root": scan.repo_root,
        "total_files": scan.total_files,
        "languages": scan.languages,
        "files": [f.model_dump() for f in scan.files],
    }


@app.get("/api/repo/file", dependencies=[Depends(verify_auth)])
async def get_repo_file(path: str) -> dict[str, Any]:
    try:
        safe_file = workspace_jail.resolve_safe_path(path)
    except SafetyError as exc:
        raise HTTPException(status_code=400, detail=f"Access denied: {exc}") from exc

    if not safe_file.exists() or not safe_file.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    content = safe_file.read_text(encoding="utf-8", errors="replace")
    return {"path": path, "content": content, "size_bytes": len(content)}


@app.get("/api/repo/index", dependencies=[Depends(verify_auth)])
async def get_repo_index(path: str = ".") -> dict[str, Any]:
    safe_path = workspace_jail.resolve_safe_path(path)
    repo_idx = RepoIndex(safe_path)
    repo_idx.build_full_index()
    return {
        "summary": repo_idx.summary,
        "total_files": repo_idx.scan_result.total_files if repo_idx.scan_result else 0,
        "total_symbols": len(repo_idx.get_all_symbols()),
    }


@app.get("/api/repo/graph", dependencies=[Depends(verify_auth)])
async def get_repo_graph(path: str = ".") -> dict[str, Any]:
    safe_path = workspace_jail.resolve_safe_path(path)
    repo_idx = RepoIndex(safe_path)
    repo_idx.build_full_index()
    if not repo_idx.graph:
        return {"nodes": [], "edges": []}
    return repo_idx.graph.to_dict()


# Evaluation management endpoints
@app.post("/api/eval/runs", dependencies=[Depends(verify_auth)])
async def launch_eval_run(
    req: LaunchEvalRequest, background_tasks: BackgroundTasks
) -> dict[str, Any]:
    run_id = f"eval_{uuid.uuid4().hex[:8]}"
    eval_runs_store[run_id] = {
        "run_id": run_id,
        "status": "RUNNING",
        "created_at": datetime.now(UTC).isoformat(),
        "report": None,
    }

    async def _eval_job() -> None:
        from eval.dataset import TaskSuiteLoader
        from eval.runner import ExperimentRunner

        presets = [AgentConfigPreset(p) for p in req.presets]
        tasks = (
            TaskSuiteLoader.load_from_file(Path(req.suite_path))
            if req.suite_path
            else TaskSuiteLoader.load_builtin_tasks()
        )
        if req.limit and req.limit > 0:
            tasks = tasks[: req.limit]
        runner = ExperimentRunner(
            workspace_dir=Path("."),
            results_dir=Path("eval/results"),
            seeds=req.seeds,
            max_concurrency=req.concurrency,
        )
        report = await runner.run_comparative_experiment(tasks=tasks, presets=presets)
        eval_runs_store[run_id]["status"] = "COMPLETED"
        eval_runs_store[run_id]["report"] = report

    background_tasks.add_task(_eval_job)
    return {"run_id": run_id, "status": "RUNNING"}


@app.get("/api/eval/runs", dependencies=[Depends(verify_auth)])
async def list_eval_runs() -> dict[str, Any]:
    return {"runs": list(eval_runs_store.values())}


@app.get("/api/eval/runs/{run_id}", dependencies=[Depends(verify_auth)])
async def get_eval_run(run_id: str) -> dict[str, Any]:
    run_data = eval_runs_store.get(run_id)
    if not run_data:
        raise HTTPException(status_code=404, detail=f"Eval run '{run_id}' not found")
    return run_data


@app.get("/api/eval/runs/{run_id}/export/latex", dependencies=[Depends(verify_auth)])
async def export_eval_latex(run_id: str) -> PlainTextResponse:
    from eval.export import export_latex_table

    run_data = eval_runs_store.get(run_id)
    if not run_data or not run_data.get("report"):
        raise HTTPException(status_code=404, detail=f"Report for run '{run_id}' not ready")
    latex = export_latex_table(run_data["report"])
    return PlainTextResponse(latex, media_type="text/plain")


@app.get("/api/eval/runs/{run_id}/export/csv", dependencies=[Depends(verify_auth)])
async def export_eval_csv(run_id: str) -> PlainTextResponse:
    from eval.export import export_csv

    run_data = eval_runs_store.get(run_id)
    if not run_data or not run_data.get("report"):
        raise HTTPException(status_code=404, detail=f"Report for run '{run_id}' not ready")
    csv_str = export_csv(run_data["report"])
    return PlainTextResponse(csv_str, media_type="text/csv")


@app.get("/api/eval/latest", dependencies=[Depends(verify_auth)])
async def get_latest_eval_report() -> dict[str, Any]:
    report_file = Path("eval/results/latest_evaluation_report.json")
    if not report_file.exists():
        return {"report": None, "message": "No evaluation runs recorded yet"}
    try:
        report_data = json.loads(report_file.read_text(encoding="utf-8"))
        return {"report": report_data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
