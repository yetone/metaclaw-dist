"""Tool registry and base tool definitions."""

from __future__ import annotations

from typing import Any

from metaclaw.core.tools.base import BaseTool
from metaclaw.core.tools.read_file import ReadFileTool
from metaclaw.core.tools.write_file import WriteFileTool
from metaclaw.core.tools.edit_file import EditFileTool
from metaclaw.core.tools.bash import BashTool


class ToolRegistry:
    """Registry for all available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def get_all(self) -> list[BaseTool]:
        return list(self._tools.values())

    def get_schemas(self) -> list[dict[str, Any]]:
        """Get OpenAI-compatible tool schemas for all registered tools."""
        return [tool.to_schema() for tool in self._tools.values()]


def create_default_registry(
    working_directory: str = ".",
    sandbox: str = "basic",
    max_read_size_kb: int = 100,
    max_read_lines: int = 2000,
) -> ToolRegistry:
    """Create a registry with all default tools."""
    registry = ToolRegistry()
    registry.register(ReadFileTool(max_size_kb=max_read_size_kb, max_lines=max_read_lines))
    registry.register(WriteFileTool())
    registry.register(EditFileTool())
    registry.register(BashTool(working_directory=working_directory, sandbox=sandbox))
    return registry
