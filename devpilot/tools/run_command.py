"""Tool: run_command with Docker sandbox execution, policy enforcement, and secret redaction."""

from typing import Any

from devpilot.core.types import ErrorTypeEnum, ToolResult
from devpilot.safety.command_policy import CommandPolicy
from devpilot.safety.docker_executor import DockerExecutor
from devpilot.safety.redactor import SecretRedactor
from devpilot.safety.sandbox import PathSandbox
from devpilot.tools.base import Tool


class RunCommandTool(Tool):
    name = "run_command"
    description = "Execute a shell command within the repository root environment with timeout and safety controls."
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command line to execute"},
            "timeout_sec": {
                "type": "number",
                "description": "Maximum seconds to wait before termination",
            },
        },
        "required": ["command"],
    }

    def __init__(
        self,
        sandbox: PathSandbox,
        default_timeout_sec: float = 60.0,
        policy: CommandPolicy | None = None,
        docker_executor: DockerExecutor | None = None,
    ) -> None:
        self.sandbox = sandbox
        self.default_timeout_sec = default_timeout_sec
        self.policy = policy or CommandPolicy()
        self.docker_executor = docker_executor or DockerExecutor(
            repo_root=self.sandbox.repo_root,
            timeout_sec=default_timeout_sec,
            sandbox_enabled=True,
            allow_host_fallback=True,
        )

    async def execute(
        self, command: str = "", timeout_sec: float | None = None, **kwargs: Any
    ) -> ToolResult:
        if not command:
            return ToolResult(
                ok=False,
                output="Missing required argument 'command'",
                error_type=ErrorTypeEnum.TOOL_MISUSE,
            )

        # Validate against dangerous command injection and denylist patterns
        try:
            self.policy.validate_command(command)
        except Exception as exc:
            return ToolResult(
                ok=False,
                output=f"Command validation failed: {str(exc)}",
                error_type=ErrorTypeEnum.PERMISSION,
                metadata={"command": command},
            )

        timeout = timeout_sec or self.default_timeout_sec
        env = kwargs.get("env")

        res = await self.docker_executor.execute(command, env=env, timeout_sec=timeout)

        # Redact secrets before returning
        sanitized_output = SecretRedactor.redact(res.output)
        if not sanitized_output:
            sanitized_output = "(Command produced no output)"

        return ToolResult(
            ok=res.ok,
            output=sanitized_output,
            error_type=res.error_type,
            exit_code=res.exit_code,
            duration_ms=res.duration_ms,
            truncated=res.truncated,
            metadata={**res.metadata, "command": command},
        )
