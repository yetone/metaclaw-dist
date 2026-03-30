"""Tests for WriteFile tool."""

from __future__ import annotations

from pathlib import Path

import pytest

from metaclaw.core.tools.write_file import WriteFileTool


@pytest.fixture
def tool():
    return WriteFileTool()


@pytest.mark.asyncio
async def test_write_new_file(tool: WriteFileTool, tmp_dir: Path):
    f = tmp_dir / "new.txt"
    result = await tool.execute(file_path=str(f), content="hello world")
    assert "Successfully" in result
    assert f.read_text() == "hello world"


@pytest.mark.asyncio
async def test_write_creates_dirs(tool: WriteFileTool, tmp_dir: Path):
    f = tmp_dir / "a" / "b" / "c" / "file.txt"
    result = await tool.execute(file_path=str(f), content="nested")
    assert "Successfully" in result
    assert f.read_text() == "nested"


@pytest.mark.asyncio
async def test_write_overwrites(tool: WriteFileTool, tmp_dir: Path):
    f = tmp_dir / "existing.txt"
    f.write_text("old content")
    result = await tool.execute(file_path=str(f), content="new content")
    assert "Successfully" in result
    assert f.read_text() == "new content"
