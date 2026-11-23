"""Hardened command safety policy: parse argv, pipeline inspection, and injection defense."""

import os
import re
import shlex
from collections.abc import Sequence
from pathlib import Path

from devpilot.core.exceptions import SafetyError

DANGEROUS_BINARIES = {
    "rm",
    "mkfs",
    "dd",
    "sudo",
    "su",
    "shutdown",
    "reboot",
    "poweroff",
    "init",
    "nc",
    "ncat",
    "netcat",
}

SAFE_EXECUTABLES: set[str] = {
    "python",
    "python3",
    "py",
    "pytest",
    "pip",
    "uv",
    "poetry",
    "node",
    "nodejs",
    "npm",
    "npx",
    "pnpm",
    "yarn",
    "git",
    "cargo",
    "mvn",
    "gradle",
    "gradlew",
    "./gradlew",
    "go",
    "ls",
    "dir",
    "cat",
    "echo",
    "touch",
    "grep",
    "find",
    "ruff",
    "mypy",
    "flake8",
    "black",
    "isort",
    "vitest",
    "jest",
}


def _has_unquoted_operator(cmd: str, operators: list[str]) -> tuple[bool, str]:
    """Checks if any shell control operator appears outside single or double quotes."""
    in_single = False
    in_double = False
    i = 0
    while i < len(cmd):
        char = cmd[i]
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double:
            for op in operators:
                if cmd.startswith(op, i):
                    return True, op
        i += 1
    return False, ""


class CommandPolicy:
    """Enforces strict command-level safety boundaries, denylist patterns, and allowlist rules."""

    def __init__(
        self,
        enforce_allowlist: bool = False,
        custom_denylist: list[str] | None = None,
    ) -> None:
        self.enforce_allowlist = enforce_allowlist
        self.custom_denylist = custom_denylist or []

    def validate_command(self, command: str) -> None:
        """Validates command against dangerous constructs, chained execution, and denylists."""
        cmd = command.strip()
        if not cmd:
            raise SafetyError("Command string cannot be empty", policy="command_policy")

        # 1. Newline injection check
        if "\n" in cmd or "\r" in cmd:
            raise SafetyError(
                "Command execution blocked: multi-line newline injection detected",
                policy="command_injection",
            )

        # 2. Command substitutions: backticks, $(, ${
        has_sub, op = _has_unquoted_operator(cmd, ["`", "$(", "${"])
        if has_sub:
            raise SafetyError(
                f"Command execution blocked: command substitution '{op}' detected: '{cmd}'",
                policy="command_substitution",
                details={"command": cmd},
            )

        # 3. $IFS separator bypass
        if "$IFS" in cmd:
            raise SafetyError(
                f"Command execution blocked: shell IFS variable bypass detected: '{cmd}'",
                policy="command_injection",
                details={"command": cmd},
            )

        # 4. Dangerous piped exfiltration like `curl ... | bash`
        if re.search(
            r"\b(curl|wget|fetch)\b[^\n]*\|\s*(bash|sh|zsh|python|perl|ruby)",
            cmd,
            re.IGNORECASE,
        ):
            raise SafetyError(
                f"Forbidden network execution pipeline detected in '{cmd}'",
                policy="command_denylist",
            )

        # 5. Check unquoted chained command operators: ; && ||
        has_chain, chain_op = _has_unquoted_operator(cmd, [";", "&&", "||"])
        if has_chain:
            raise SafetyError(
                f"Command execution blocked: chained command operator '{chain_op}' not permitted: '{cmd}'",
                policy="command_chaining",
                details={"command": cmd},
            )

        # 6. Check unquoted redirection operators: >> > <
        has_redir, redir_op = _has_unquoted_operator(cmd, [">>", ">", "<"])
        if has_redir:
            raise SafetyError(
                f"Command execution blocked: file redirection operator '{redir_op}' not permitted: '{cmd}'",
                policy="command_redirection",
                details={"command": cmd},
            )

        # 7. Forkbomb check
        if ":(){ :|:& };:" in cmd or ":(){:|:&};:" in cmd:
            raise SafetyError("Forkbomb pattern detected and blocked", policy="command_denylist")

        # 8. Inspect all pipeline segments
        segments = cmd.split("|")
        for segment in segments:
            self._validate_segment(segment.strip())

    def _validate_segment(self, segment: str) -> None:
        if not segment:
            raise SafetyError("Empty pipeline segment detected", policy="command_policy")

        # Parse with shlex into argv tokens
        try:
            if os.name == "nt":
                raw_tokens = shlex.split(segment, posix=False)
                tokens = [t.strip("\"'") for t in raw_tokens if t.strip("\"'")]
            else:
                tokens = shlex.split(segment, posix=True)
        except ValueError as exc:
            raise SafetyError(
                f"Command syntax error or unclosed quote: {exc}",
                policy="command_syntax",
                details={"segment": segment},
            ) from exc

        if not tokens:
            raise SafetyError("No valid tokens in command segment", policy="command_policy")

        # Normalize environment variable prefixes: VAR=val command
        idx = 0
        while idx < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=.*$", tokens[idx]):
            if tokens[idx].startswith(
                ("LD_PRELOAD=", "LD_LIBRARY_PATH=", "DYLD_INSERT_LIBRARIES=")
            ):
                raise SafetyError(
                    f"Forbidden dynamic library preload: '{tokens[idx]}'",
                    policy="env_security",
                )
            idx += 1

        if idx >= len(tokens):
            raise SafetyError(
                "Command contains only environment variables", policy="command_policy"
            )

        cmd_tokens = tokens[idx:]

        # Handle 'env' wrapper: env [-i] VAR=val ... command
        if cmd_tokens[0] in ("env", "/usr/bin/env", "/bin/env"):
            env_idx = 1
            while env_idx < len(cmd_tokens) and (
                cmd_tokens[env_idx].startswith("-")
                or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=.*$", cmd_tokens[env_idx])
            ):
                env_idx += 1
            if env_idx >= len(cmd_tokens):
                raise SafetyError("Empty command following env wrapper", policy="command_policy")
            cmd_tokens = cmd_tokens[env_idx:]

        # Extract and normalize executable
        raw_exe = cmd_tokens[0]
        exe_name = Path(raw_exe).name.lower()
        if exe_name.endswith(".exe"):
            exe_name = exe_name[:-4]

        # 3. Denylist check on executable and arguments
        self._check_executable_rules(exe_name, cmd_tokens)

        # 4. Allowlist enforcement
        if self.enforce_allowlist and exe_name not in SAFE_EXECUTABLES:
            raise SafetyError(
                f"Executable '{exe_name}' is not in the allowed command set",
                policy="command_allowlist",
                details={"executable": exe_name, "raw_command": segment},
            )

    def _check_executable_rules(self, exe_name: str, tokens: Sequence[str]) -> None:
        # Destructive command 'rm'
        if exe_name == "rm":
            args = tokens[1:]
            has_recursive = any(
                a in ("-r", "-R", "-rf", "-fr") or (a.startswith("-") and "r" in a) for a in args
            )
            has_dangerous_target = any(
                a in ("/", "/*", "~", "~/", "..", "$HOME", ".") for a in args
            )
            if has_dangerous_target:
                raise SafetyError(
                    f"Destructive rm command blocked against root/home/parent: '{' '.join(tokens)}'",
                    policy="command_denylist",
                )
            if has_recursive and any(a in ("*", ".") or a.startswith("/") for a in args):
                raise SafetyError(
                    f"Recursive rm command blocked on dangerous target: '{' '.join(tokens)}'",
                    policy="command_denylist",
                )

        # Privilege escalation binaries
        if exe_name in ("sudo", "su"):
            raise SafetyError(
                f"Privilege escalation binary '{exe_name}' is strictly forbidden",
                policy="command_denylist",
                details={"executable": exe_name},
            )

        # Raw disk formatting / block device tools
        if exe_name in ("mkfs", "dd", "fdisk", "parted") or exe_name.startswith("mkfs."):
            raise SafetyError(
                f"Low-level storage/disk utility '{exe_name}' is strictly forbidden",
                policy="command_denylist",
            )

        # System control / poweroff
        if exe_name in ("shutdown", "reboot", "poweroff", "init"):
            raise SafetyError(
                f"System lifecycle command '{exe_name}' is strictly forbidden",
                policy="command_denylist",
            )

        # Network exfiltration
        if exe_name in ("nc", "ncat", "netcat"):
            raise SafetyError(
                f"Arbitrary network binary '{exe_name}' is strictly forbidden",
                policy="command_denylist",
            )

        # xargs wrapper check
        if exe_name == "xargs":
            xargs_target = [t for t in tokens[1:] if not t.startswith("-")]
            if xargs_target:
                target_exe = Path(xargs_target[0]).name.lower()
                if target_exe in DANGEROUS_BINARIES or target_exe.startswith("mkfs."):
                    raise SafetyError(
                        f"xargs invocation of forbidden binary '{target_exe}' blocked",
                        policy="command_denylist",
                    )

        # find -exec wrapper check
        if exe_name == "find" and "-exec" in tokens:
            exec_idx = tokens.index("-exec")
            if exec_idx + 1 < len(tokens):
                target_exe = Path(tokens[exec_idx + 1]).name.lower()
                if target_exe in DANGEROUS_BINARIES or target_exe.startswith("mkfs."):
                    raise SafetyError(
                        f"find -exec invocation of forbidden binary '{target_exe}' blocked",
                        policy="command_denylist",
                    )

        # Inline script checks (python -c, bash -c, node -e)
        if exe_name in ("python", "python3", "py") and "-c" in tokens:
            c_idx = tokens.index("-c")
            if c_idx + 1 < len(tokens):
                script = tokens[c_idx + 1]
                if re.search(r"\b(rmtree|os\.system|subprocess)\b", script):
                    raise SafetyError(
                        "Dangerous inline python script blocked", policy="command_denylist"
                    )

        if exe_name in ("bash", "sh", "zsh") and "-c" in tokens:
            c_idx = tokens.index("-c")
            if c_idx + 1 < len(tokens):
                script = tokens[c_idx + 1]
                self.validate_command(script)
