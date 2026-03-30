"""WriteFile tool - Write content to a file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from metaclaw.core.tools.base import BaseTool


class WriteFileTool(BaseTool):
    """Write content to a file, creating parent directories as needed."""

    @property
    def name(self) -> str:
        return "WriteFile"

    @property
    def description(self) -> str:
        return (
            "Write content to a file. Creates the file if it doesn't exist. "
            "Creates parent directories automatically. Overwrites existing content."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to write.",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file.",
                },
            },
            "required": ["file_path", "content"],
        }

    async def execute(self, **kwargs: Any) -> str:
        file_path = kwargs["file_path"]
        content = kwargs["content"]

        path = Path(file_path).expanduser()

        try:
            # Create parent directories
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            path.write_text(content, encoding="utf-8")

            size = path.stat().st_size
            lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
            return f"Successfully wrote {size} bytes ({lines} lines) to {file_path}"

        except PermissionError:
            return f"Error: Permission denied: {file_path}"
        except OSError as e:
            return f"Error writing file: {e}"
