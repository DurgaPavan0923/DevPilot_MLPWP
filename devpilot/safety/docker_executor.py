"""Docker sandboxed execution engine and secure host subprocess fallback."""

import asyncio
import contextlib
import os
import shlex
import time
from pathlib import Path

from devpilot.core.exceptions import SafetyError
from devpilot.core.logging import get_logger
from devpilot.core.types import ErrorTypeEnum, ToolResult
from devpilot.core.utils import truncate_output

logger = get_logger("docker_executor")


class DockerExecutor:
    """Executes commands inside an isolated Docker container with resource constraints.

    Guarantees:
    - Non-root user (1000:1000)
    - Network isolated by default (--network none)
    - Resource limits (CPU, memory, pids)
    - Read-only root filesystem with writable bind-mounted workspace
    - Enforced wall-clock timeout with forced kill
    - Output size cap
    """

    def __init__(
        self,
        repo_root: Path,
        image: str = "devpilot-sandbox:latest",
        cpu_limit: float = 2.0,
        mem_limit: str = "4096m",
        pids_limit: int = 128,
        network_mode: str = "none",
        timeout_sec: float = 60.0,
        max_output_chars: int = 40_000,
        sandbox_enabled: bool = True,
        allow_host_fallback: bool = True,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.image = image
        self.cpu_limit = cpu_limit
        self.mem_limit = mem_limit
        self.pids_limit = pids_limit
        self.network_mode = network_mode
        self.timeout_sec = timeout_sec
        self.max_output_chars = max_output_chars
        self.sandbox_enabled = sandbox_enabled
        self.allow_host_fallback = allow_host_fallback

    def is_docker_available(self) -> bool:
        """Checks if Docker daemon is responsive."""
        try:
            import docker

            client = docker.from_env()
            client.ping()
            return True
        except Exception:
            return False

    async def execute(
        self,
        command: str | list[str],
        env: dict[str, str] | None = None,
        timeout_sec: float | None = None,
        workdir: str = "/workspace",
    ) -> ToolResult:
        """Dispatches command execution to Docker container or explicit host fallback."""
        timeout = timeout_sec or self.timeout_sec
        start_time = time.monotonic()

        if self.sandbox_enabled and self.is_docker_available():
            return await self._execute_in_docker(command, env, timeout, workdir, start_time)

        if not self.allow_host_fallback:
            raise SafetyError(
                "Docker sandbox is unavailable or disabled, and host subprocess fallback is disallowed",
                policy="docker_sandbox",
            )

        logger.warning(
            "SECURITY_WARNING: Docker sandbox unavailable or disabled; falling back to host subprocess execution",
            repo_root=str(self.repo_root),
        )
        return await self._execute_on_host(command, env, timeout, start_time)

    async def _execute_in_docker(
        self,
        command: str | list[str],
        env: dict[str, str] | None,
        timeout: float,
        workdir: str,
        start_time: float,
    ) -> ToolResult:

        import docker

        client = docker.from_env()
        cmd_str = command if isinstance(command, str) else " ".join(command)

        volumes = {
            str(self.repo_root): {"bind": "/workspace", "mode": "rw"},
            "/tmp": {"bind": "/tmp", "mode": "rw"},
        }
        environment = {**(env or {}), "PYTHONPATH": "/workspace"}

        loop = asyncio.get_running_loop()

        def _run_container() -> tuple[int, str]:
            container = None
            try:
                container = client.containers.create(
                    image=self.image,
                    command=["sh", "-c", cmd_str],
                    user="1000:1000",
                    network_mode=self.network_mode,
                    mem_limit=self.mem_limit,
                    nano_cpus=int(self.cpu_limit * 1e9),
                    pids_limit=self.pids_limit,
                    read_only=True,
                    volumes=volumes,
                    working_dir=workdir,
                    environment=environment,
                )
                container.start()
                res = container.wait(timeout=int(timeout))
                exit_code = res.get("StatusCode", 1)
                logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
                return exit_code, logs
            except Exception as exc:
                if container:
                    with contextlib.suppress(Exception):
                        container.kill()
                return 124, f"Docker container execution error or timeout: {exc}"
            finally:
                if container:
                    with contextlib.suppress(Exception):
                        container.remove(force=True)

        try:
            exit_code, raw_output = await loop.run_in_executor(None, _run_container)
        except Exception as exc:
            duration = (time.monotonic() - start_time) * 1000
            return ToolResult(
                ok=False,
                output=f"Failed to execute in Docker sandbox: {exc}",
                error_type=ErrorTypeEnum.ENVIRONMENT,
                exit_code=1,
                duration_ms=duration,
                truncated=False,
            )

        duration = (time.monotonic() - start_time) * 1000
        truncated_out, was_truncated = truncate_output(raw_output, max_chars=self.max_output_chars)
        ok = exit_code == 0
        error_type = (
            None if ok else (ErrorTypeEnum.TIMEOUT if exit_code == 124 else ErrorTypeEnum.UNKNOWN)
        )

        return ToolResult(
            ok=ok,
            output=truncated_out,
            error_type=error_type,
            exit_code=exit_code,
            duration_ms=duration,
            truncated=was_truncated,
            metadata={"sandbox": "docker", "image": self.image},
        )

    async def _execute_on_host(
        self,
        command: str | list[str],
        env: dict[str, str] | None,
        timeout: float,
        start_time: float,
    ) -> ToolResult:
        """Executes securely via host create_subprocess_exec (no shell) with argv splitting."""
        if isinstance(command, str):
            # shlex parsing into argv
            try:
                if os.name == "nt":
                    raw_tokens = shlex.split(command, posix=False)
                    argv = [t.strip("\"'") for t in raw_tokens if t.strip("\"'")]
                else:
                    argv = shlex.split(command, posix=True)
            except ValueError as exc:
                return ToolResult(
                    ok=False,
                    output=f"Invalid shell command syntax: {exc}",
                    error_type=ErrorTypeEnum.SYNTAX,
                    exit_code=1,
                    duration_ms=(time.monotonic() - start_time) * 1000,
                    truncated=False,
                )
        else:
            argv = list(command)

        if not argv:
            return ToolResult(
                ok=False,
                output="Empty command provided",
                error_type=ErrorTypeEnum.TOOL_MISUSE,
                exit_code=1,
                duration_ms=0.0,
                truncated=False,
            )

        process_env = {**os.environ, **(env or {}), "PYTHONPATH": str(self.repo_root)}

        try:
            # create_subprocess_exec strictly avoids shell interpretation
            proc = await asyncio.create_subprocess_exec(
                argv[0],
                *argv[1:],
                cwd=str(self.repo_root),
                env=process_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except TimeoutError:
                try:
                    proc.kill()
                    await proc.communicate()
                except Exception:
                    pass
                duration = (time.monotonic() - start_time) * 1000
                return ToolResult(
                    ok=False,
                    output=f"Command timed out after {timeout} seconds",
                    error_type=ErrorTypeEnum.TIMEOUT,
                    exit_code=124,
                    duration_ms=duration,
                    truncated=False,
                )

            raw_output = (
                stdout_bytes.decode("utf-8", errors="replace")
                + stderr_bytes.decode("utf-8", errors="replace")
            ).strip()
            exit_code = proc.returncode or 0
            duration = (time.monotonic() - start_time) * 1000
            truncated_out, was_truncated = truncate_output(
                raw_output, max_chars=self.max_output_chars
            )
            ok = exit_code == 0
            error_type = None if ok else ErrorTypeEnum.UNKNOWN

            return ToolResult(
                ok=ok,
                output=truncated_out,
                error_type=error_type,
                exit_code=exit_code,
                duration_ms=duration,
                truncated=was_truncated,
                metadata={"sandbox": "host_subprocess_exec"},
            )

        except FileNotFoundError:
            duration = (time.monotonic() - start_time) * 1000
            return ToolResult(
                ok=False,
                output=f"Executable not found on system PATH: '{argv[0]}'",
                error_type=ErrorTypeEnum.ENVIRONMENT,
                exit_code=127,
                duration_ms=duration,
                truncated=False,
            )
        except Exception as exc:
            duration = (time.monotonic() - start_time) * 1000
            return ToolResult(
                ok=False,
                output=f"Host subprocess execution error: {exc}",
                error_type=ErrorTypeEnum.ENVIRONMENT,
                exit_code=1,
                duration_ms=duration,
                truncated=False,
            )
