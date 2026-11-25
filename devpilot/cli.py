"""DevPilot Command Line Interface (CLI): full operational agent control, indexing, evaluation, and server."""

import asyncio
import uuid
from pathlib import Path

import typer

from devpilot.config import get_settings

app = typer.Typer(
    name="devpilot",
    help="DevPilot: Autonomous Coding Agent Harness with Adaptive Retrieval and Bounded Recovery",
    add_completion=False,
)
settings = get_settings()


@app.command()
def run(
    instruction: str = typer.Argument(..., help="Task instruction for the coding agent"),
    repo_path: str = typer.Option(".", "--repo", "-r", help="Repository path"),
    config: str = typer.Option(
        "full", "--config", "-c", help="Agent configuration preset: basic, fixed_rag, full"
    ),
    provider: str = typer.Option(
        "mock", "--provider", "-p", help="LLM provider: mock, openai, anthropic, ollama, etc."
    ),
    model: str = typer.Option("mock-model", "--model", "-m", help="Model name"),
    permission: str = typer.Option(
        "auto-safe",
        "--permission",
        help="Permission mode: read-only, ask, auto-safe, full",
    ),
    cost_cap: float = typer.Option(2.0, "--cost-cap", help="Maximum USD cost limit"),
    timeout: float = typer.Option(600.0, "--timeout", help="Maximum wall-clock timeout in seconds"),
) -> None:
    """Executes a coding agent task autonomously on the specified repository."""
    from devpilot.agent.events import AgentEvent, AgentEventType
    from devpilot.agent.runtime import AgentRuntime
    from devpilot.core.types import AgentConfigPreset, PermissionMode
    from devpilot.llm.factory import create_provider
    from devpilot.session.store import SessionStore

    preset_enum = AgentConfigPreset(config)
    perm_enum = PermissionMode(permission)
    llm = create_provider(provider, model)
    session_id = f"cli_{uuid.uuid4().hex[:8]}"
    store = SessionStore(settings.db_path)

    typer.secho(
        f"\n[DevPilot] Initializing task on '{repo_path}' [{config} | {provider}:{model}]...",
        fg=typer.colors.CYAN,
        bold=True,
    )

    def on_event(evt: AgentEvent) -> None:
        if evt.type == AgentEventType.STATE_CHANGE:
            typer.secho(f" -> FSM State: {evt.data.get('state')}", fg=typer.colors.BLUE, dim=True)
        elif evt.type == AgentEventType.TOOL_CALL:
            typer.secho(
                f" -> Action: {evt.data.get('name')} {evt.data.get('arguments', {})}",
                fg=typer.colors.YELLOW,
            )
        elif evt.type == AgentEventType.RECOVERY:
            typer.secho(
                f" [!] Recovery Level {evt.data.get('level')}: {evt.data.get('feedback', '')[:120]}...",
                fg=typer.colors.RED,
            )

    runtime = AgentRuntime(
        session_id=session_id,
        repo_root=Path(repo_path),
        llm=llm,
        preset=preset_enum,
        permission_mode=perm_enum,
        session_store=store,
        max_cost_usd=cost_cap,
        timeout_sec=timeout,
        event_callback=on_event,
    )

    result = asyncio.run(runtime.run(instruction))
    status = result.get("status")
    color = typer.colors.GREEN if status in ("COMPLETED", "UNVERIFIED") else typer.colors.RED

    typer.secho(f"\n[DevPilot] Run Finished: {status}", fg=color, bold=True)
    typer.echo(f"  Session ID:      {session_id}")
    typer.echo(f"  Steps:           {result.get('steps')}")
    typer.echo(f"  Total Tokens:    {result.get('total_tokens')}")
    typer.echo(f"  Cost:            ${result.get('total_cost_usd', 0.0):.4f} USD")
    typer.echo(f"  Duration:        {result.get('duration_sec')}s")
    typer.echo(f"  Modified Files:  {result.get('modified_files')}")
    if result.get("reason"):
        typer.echo(f"  Reason:          {result.get('reason')}")


@app.command()
def index(
    repo_path: str = typer.Option(".", "--repo", "-r", help="Repository path to index"),
) -> None:
    """Scans repository, extracts symbols, builds dependency graph, and creates context index."""
    from devpilot.context.chunker import SymbolChunker
    from devpilot.context.dense import DenseSemanticRetriever
    from devpilot.repo.index import RepoIndex

    root = Path(repo_path).resolve()
    typer.secho(f"[DevPilot] Building index for repository: {root}...", fg=typer.colors.CYAN)

    repo_idx = RepoIndex(root)
    repo_idx.build_full_index()
    chunks = SymbolChunker.chunk_repository(repo_idx)
    dense = DenseSemanticRetriever(chunks)

    typer.secho("[DevPilot] Index Complete:", fg=typer.colors.GREEN, bold=True)
    scan = repo_idx.scan_result
    typer.echo(f"  Total Files:      {scan.total_files if scan else 0}")
    typer.echo(f"  Languages:        {list(scan.languages.keys()) if scan else []}")
    typer.echo(f"  Extracted Chunks: {len(chunks)}")
    typer.echo(
        f"  Dense Model:      {'sentence-transformers' if dense.is_neural else 'TF-IDF fallback'}"
    )
    if repo_idx.graph:
        typer.echo(f"  Graph Nodes:      {len(repo_idx.graph.nodes)}")
        typer.echo(f"  Graph Edges:      {len(repo_idx.graph.edge_types)}")


@app.command()
def sessions(
    limit: int = typer.Option(20, "--limit", "-l", help="Number of recent sessions to show"),
) -> None:
    """Lists recent agent sessions, execution statuses, and costs."""
    from devpilot.session.store import SessionStore

    store = SessionStore(settings.db_path)
    records = asyncio.run(store.list_sessions(limit=limit))

    if not records:
        typer.echo("No sessions recorded yet.")
        return

    typer.secho(
        f"{'ID':<20} {'Status':<12} {'Preset':<10} {'Steps':<6} {'Tokens':<8} {'Cost ($)':<10} {'Created':<20}",
        bold=True,
    )
    typer.echo("-" * 88)
    for r in records:
        cost_str = f"${r.total_cost_usd:.4f}"
        created_str = r.created_at[:19].replace("T", " ")
        typer.echo(
            f"{r.id:<20} {r.status:<12} {r.preset:<10} {r.steps:<6} {r.total_tokens:<8} {cost_str:<10} {created_str:<20}"
        )


@app.command()
def resume(
    session_id: str = typer.Argument(..., help="Session ID to resume"),
    repo_path: str = typer.Option(".", "--repo", "-r", help="Repository path"),
    provider: str = typer.Option("mock", "--provider", "-p", help="LLM provider"),
    model: str = typer.Option("mock-model", "--model", "-m", help="Model name"),
) -> None:
    """Resumes an interrupted session from the persistent SQLite store."""
    from devpilot.agent.runtime import AgentRuntime
    from devpilot.llm.factory import create_provider
    from devpilot.session.store import SessionStore

    store = SessionStore(settings.db_path)
    llm = create_provider(provider, model)
    runtime = AgentRuntime(
        session_id=session_id,
        repo_root=Path(repo_path),
        llm=llm,
        session_store=store,
    )

    typer.secho(f"[DevPilot] Resuming session: {session_id}...", fg=typer.colors.CYAN)
    res = asyncio.run(runtime.resume())
    typer.secho(
        f"[DevPilot] Resumed run finished with status: {res.get('status')}", fg=typer.colors.GREEN
    )


@app.command()
def rollback(
    session_id: str = typer.Argument(..., help="Session ID to roll back"),
    snapshot: str = typer.Option("baseline", "--snapshot", "-s", help="Snapshot identifier"),
    repo_path: str = typer.Option(".", "--repo", "-r", help="Repository path"),
) -> None:
    """Rolls back the repository workspace to a captured snapshot checkpoint."""
    from devpilot.agent.runtime import AgentRuntime
    from devpilot.llm.adapters.mock import MockProvider
    from devpilot.session.store import SessionStore

    store = SessionStore(settings.db_path)
    runtime = AgentRuntime(
        session_id=session_id,
        repo_root=Path(repo_path),
        llm=MockProvider(),
        session_store=store,
    )
    restored = runtime.rollback(snapshot)
    typer.secho(
        f"[DevPilot] Rollback to '{snapshot}' completed: {len(restored)} files restored/deleted.",
        fg=typer.colors.GREEN,
    )
    for f in restored:
        typer.echo(f"  - {f}")


@app.command("eval")
def evaluate(
    suite_path: str | None = typer.Option(
        None, "--suite", "-s", help="Path to JSON/YAML suite file"
    ),
    configs: str = typer.Option(
        "basic,fixed_rag,full", "--configs", "-c", help="Presets to evaluate (comma-separated)"
    ),
    seeds: str = typer.Option("42,137,2026", "--seeds", help="Random seeds (comma-separated)"),
    concurrency: int = typer.Option(4, "--concurrency", "-n", help="Parallel trial limit"),
    output_dir: str = typer.Option("results", "--output", "-o", help="Results directory"),
) -> None:
    """Runs comparative evaluation benchmarks across agent configurations."""
    from devpilot.core.types import AgentConfigPreset
    from eval.dataset import TaskSuiteLoader
    from eval.export import export_latex_table, generate_evaluation_figures
    from eval.runner import ExperimentRunner

    presets = [AgentConfigPreset(c.strip()) for c in configs.split(",") if c.strip()]
    seed_list = [int(s.strip()) for s in seeds.split(",") if s.strip()]

    if suite_path:
        tasks = TaskSuiteLoader.load_from_file(Path(suite_path))
    else:
        tasks = TaskSuiteLoader.load_builtin_tasks()

    typer.secho(
        f"[DevPilot Eval] Launching benchmark on {len(tasks)} tasks across {len(presets)} configs with seeds {seed_list}...",
        fg=typer.colors.CYAN,
        bold=True,
    )

    out_path = Path(output_dir)
    runner = ExperimentRunner(
        workspace_dir=Path("."),
        results_dir=out_path,
        seeds=seed_list,
        max_concurrency=concurrency,
    )

    report = asyncio.run(runner.run_comparative_experiment(tasks=tasks, presets=presets))

    # Generate LaTeX and Figures
    latex = export_latex_table(report)
    latex_path = out_path / "table_main_results.tex"
    latex_path.write_text(latex, encoding="utf-8")

    figs = generate_evaluation_figures(report, Path("output_images"))

    typer.secho("\n[DevPilot Eval] Benchmark Completed:", fg=typer.colors.GREEN, bold=True)
    for p_name, data in report.get("configs", {}).items():
        pass_rate = data.get("test_pass_rate", 0.0) * 100.0
        p5 = data.get("avg_precision_at_k", 0.0)
        r5 = data.get("avg_recall_at_k", 0.0)
        typer.echo(
            f"  {p_name.upper():<12} Pass Rate: {pass_rate:5.1f}% | P@5: {p5:.3f} | R@5: {r5:.3f}"
        )

    typer.echo(f"\nArtifacts generated in '{output_dir}':")
    typer.echo(f"  - Report:  {out_path / 'latest_evaluation_report.json'}")
    typer.echo(f"  - LaTeX:   {latex_path}")
    for fig in figs:
        typer.echo(f"  - Figure:  {fig}")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host address"),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port number"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development"),
) -> None:
    """Launches the DevPilot FastAPI server and SSE streaming daemon."""
    import uvicorn

    typer.secho(
        f"[DevPilot] Launching API server at http://{host}:{port}...",
        fg=typer.colors.GREEN,
        bold=True,
    )
    uvicorn.run("devpilot.api.app:app", host=host, port=port, reload=reload)


@app.command()
def version() -> None:
    """Displays DevPilot harness version."""
    from devpilot import __version__

    typer.echo(f"DevPilot v{__version__}")


def main() -> None:
    """Console script entry point."""
    app()


if __name__ == "__main__":
    main()
