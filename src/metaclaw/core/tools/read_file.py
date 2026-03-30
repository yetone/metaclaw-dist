"""ReadFile tool - Read file contents with optional windowing and size limits."""

from __future__ import annotations

from pathlib import Path
from typing import Any


from metaclaw.core.tools.base import BaseTool


class ReadFileTool(BaseTool):
    """Read a file's contents with optional offset/limit and max size enforcement."""

    def __init__(self, max_size_kb: int = 100, max_lines: int = 2000):
        self._max_size_bytes = max_size_kb * 1024
        self._max_lines = max_lines

    @property
    def name(self) -> str:
        return "ReadFile"

    @property
    def description(self) -> str:
        return (
            "Read a file from the filesystem. Returns content with line numbers. "
            "Use offset and limit to read specific portions of large files. "
            f"Content is capped at {self._max_size_bytes // 1024}KB / {self._max_lines} lines."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file to read.",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-based). Default: 1.",
                },
                "limit": {
                    "type": "integer",
                    "description": (
                        f"Maximum number of lines to read. Default: {self._max_lines}."
                    ),
                },
            },
            "required": ["file_path"],
        }

    async def execute(self, **kwargs: Any) -> str:
        file_path = kwargs["file_path"]
        offset = kwargs.get("offset", 1)
        limit = kwargs.get("limit", self._max_lines)

        path = Path(file_path).expanduser()
        if not path.exists():
            return f"Error: File not found: {file_path}"
        if not path.is_file():
            return f"Error: Not a file: {file_path}"

        try:
            raw_bytes = path.read_bytes()
        except PermissionError:
            return f"Error: Permission denied: {file_path}"

        # Check size limit (before line windowing for efficiency)
        total_size = len(raw_bytes)

        # Detect encoding
        try:
            content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content = raw_bytes.decode("latin-1")
            except UnicodeDecodeError:
                return f"Error: Cannot decode file (binary?): {file_path}"

        all_lines = content.splitlines(keepends=True)
        total_lines = len(all_lines)

        # Apply windowing (offset is 1-based)
        start_idx = max(0, offset - 1)
        end_idx = min(start_idx + limit, total_lines)
        selected_lines = all_lines[start_idx:end_idx]

        # Build output with line numbers
        output_parts: list[str] = []
        accumulated_size = 0

        for i, line in enumerate(selected_lines, start=start_idx + 1):
            numbered_line = f"{i}\t{line.rstrip()}"
            line_size = len(numbered_line.encode("utf-8"))

            if accumulated_size + line_size > self._max_size_bytes:
                output_parts.append(
                    f"\n... [truncated at {self._max_size_bytes // 1024}KB limit, "
                    f"showing {i - start_idx - 1}/{end_idx - start_idx} lines]"
                )
                break

            output_parts.append(numbered_line)
            accumulated_size += line_size

        result = "\n".join(output_parts)

        # Add metadata header if windowed or truncated
        header_parts: list[str] = []
        if total_lines > end_idx - start_idx:
            header_parts.append(
                f"[Showing lines {start_idx + 1}-{end_idx} of {total_lines} total "
                f"({total_size} bytes)]"
            )

        if header_parts:
            return "\n".join(header_parts) + "\n" + result

        return result
