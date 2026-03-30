"""Tests for Bash tool."""

from __future__ import annotations

import pytest

from metaclaw.core.tools.bash import BashTool


@pytest.fixture
def tool(tmp_dir):
    return BashTool(working_directory=str(tmp_dir), sandbox="basic")


@pytest.mark.asyncio
async def test_simple_command(tool: BashTool):
    result = await tool.execute(command="echo hello")
    assert "hello" in result


@pytest.mark.asyncio
async def test_command_exit_code(tool: BashTool):
    result = await tool.execute(command="false")
    assert "exit code" in result


@pytest.mark.asyncio
async def test_timeout(tool: BashTool):
    result = await tool.execute(command="sleep 10", timeout=1)
    assert "timed out" in result.lower()


@pytest.mark.asyncio
async def test_sandbox_blocks_dangerous(tool: BashTool):
    result = await tool.execute(command="rm -rf /")
    assert "blocked" in result.lower() or "error" in result.lower()


@pytest.mark.asyncio
async def test_stderr_captured(tool: BashTool):
    result = await tool.execute(command="echo error >&2")
    assert "error" in result
