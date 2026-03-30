"""Bash tool - Execute shell commands with configurable sandboxing."""

from __future__ import annotations

import asyncio
import os
import shlex
from typing import Any

from metaclaw.core.tools.base import BaseTool

# Commands blocked in "basic" sandbox mode
BLOCKED_COMMANDS = {
    "rm -rf /",
    "mkfs",
    "dd if=/dev/zero",
    ":(){:|:&};:",  # fork bomb
    "chmod -R 777 /",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "init 0",
    "init 6",
}

# Dangerous patterns in basic sandbox mode
BLOCKED_PATTERNS = [
    "rm -rf /",
    "rm -fr /",
    "> /dev/sd",
    "mkfs.",
    "dd if=/dev/zero of=/dev/",
    ":(){ :|:& };:",
]


class BashTool(BaseTool):
    """Execute bash commands with optional sandboxing."""

    def __init__(
        self,
        working_directory: str = ".",
        sandbox: str = "basic",
        default_timeout: int = 120,
    ):
        self._working_directory = os.path.abspath(working_directory)
        self._sandbox = sandbox
        self._default_timeout = default_timeout

    @property
    def name(self) -> str:
        return "Bash"

    @property
    def description(self) -> str:
        return (
            "Execute a bash command and return its output (stdout + stderr). "
            "Commands run in a persistent working directory. "
            f"Default timeout: {self._default_timeout}s."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute.",
                },
                "timeout": {
                    "type": "integer",
                    "description": f"Timeout in seconds. Default: {self._default_timeout}.",
                },
            },
            "required": ["command"],
        }

    async def execute(self, **kwargs: Any) -> str:
        command = kwargs["command"]
        timeout = kwargs.get("timeout", self._default_timeout)

        # Sandbox check
        if self._sandbox == "basic":
            violation = self._check_sandbox(command)
            if violation:
                return f"Error: Command blocked by sandbox: {violation}"

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._working_directory,
                env={**os.environ},
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                return f"Error: Command timed out after {timeout}s"

            output_parts: list[str] = []

            if stdout:
                decoded = stdout.decode("utf-8", errors="replace")
                output_parts.append(decoded)

            if stderr:
                decoded = stderr.decode("utf-8", errors="replace")
                if decoded.strip():
                    output_parts.append(f"[stderr]\n{decoded}")

            exit_code = process.returncode
            result = "\n".join(output_parts) if output_parts else "(no output)"

            if exit_code != 0:
                result += f"\n\n[exit code: {exit_code}]"

            # Truncate very long output
            max_output = 100_000  # ~100KB
            if len(result) > max_output:
                result = (
                    result[:max_output]
                    + f"\n\n... [truncated, total {len(result)} chars]"
                )

            return result

        except FileNotFoundError:
            return "Error: Shell not found."
        except Exception as e:
            return f"Error executing command: {e}"

    def _check_sandbox(self, command: str) -> str | None:
        """Check if a command is allowed in basic sandbox mode."""
        normalized = command.strip().lower()

        for pattern in BLOCKED_PATTERNS:
            if pattern in normalized:
                return f"Dangerous pattern detected: {pattern}"

        return None

    def set_working_directory(self, path: str) -> None:
        """Update the working directory for subsequent commands."""
        self._working_directory = os.path.abspath(path)
