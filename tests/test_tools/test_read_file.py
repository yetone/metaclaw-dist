"""Tests for ReadFile tool."""

from __future__ import annotations

from pathlib import Path

import pytest

from metaclaw.core.tools.read_file import ReadFileTool


@pytest.fixture
def tool():
    return ReadFileTool(max_size_kb=10, max_lines=100)


@pytest.mark.asyncio
async def test_read_simple_file(tool: ReadFileTool, tmp_dir: Path):
    f = tmp_dir / "test.txt"
    f.write_text("line 1\nline 2\nline 3\n")

    result = await tool.execute(file_path=str(f))
    assert "line 1" in result
    assert "line 2" in result
    assert "line 3" in result


@pytest.mark.asyncio
async def test_read_with_offset(tool: ReadFileTool, tmp_dir: Path):
    f = tmp_dir / "test.txt"
    f.write_text("\n".join(f"line {i}" for i in range(1, 11)))

    result = await tool.execute(file_path=str(f), offset=5)
    assert "line 5" in result
    assert "line 4" not in result


@pytest.mark.asyncio
async def test_read_with_limit(tool: ReadFileTool, tmp_dir: Path):
    f = tmp_dir / "test.txt"
    f.write_text("\n".join(f"line {i}" for i in range(1, 11)))

    result = await tool.execute(file_path=str(f), limit=3)
    assert "line 1" in result
    assert "line 3" in result
    assert "line 4" not in result


@pytest.mark.asyncio
async def test_read_nonexistent(tool: ReadFileTool):
    result = await tool.execute(file_path="/nonexistent/file.txt")
    assert "Error" in result


@pytest.mark.asyncio
async def test_read_file_has_line_numbers(tool: ReadFileTool, tmp_dir: Path):
    f = tmp_dir / "test.txt"
    f.write_text("hello\nworld\n")

    result = await tool.execute(file_path=str(f))
    assert "1\t" in result
    assert "2\t" in result
