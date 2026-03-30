"""Tests for EditFile tool with exact and fuzzy matching."""

from __future__ import annotations

from pathlib import Path

import pytest

from metaclaw.core.tools.edit_file import EditFileTool


@pytest.fixture
def tool():
    return EditFileTool(fuzzy_threshold=0.6)


@pytest.mark.asyncio
async def test_exact_match(tool: EditFileTool, tmp_dir: Path):
    f = tmp_dir / "test.py"
    f.write_text("def hello():\n    print('hello')\n")

    result = await tool.execute(
        file_path=str(f),
        old_string="print('hello')",
        new_string="print('world')",
    )
    assert "Successfully" in result
    assert "exact match" in result
    assert "print('world')" in f.read_text()


@pytest.mark.asyncio
async def test_fuzzy_match_whitespace(tool: EditFileTool, tmp_dir: Path):
    f = tmp_dir / "test.py"
    f.write_text("def hello():\n    print('hello')\n    return True\n")

    # Slightly different whitespace
    result = await tool.execute(
        file_path=str(f),
        old_string="def hello():\n  print('hello')\n  return True",
        new_string="def hello():\n    print('world')\n    return True",
    )
    assert "Successfully" in result
    assert "fuzzy match" in result


@pytest.mark.asyncio
async def test_no_match(tool: EditFileTool, tmp_dir: Path):
    f = tmp_dir / "test.py"
    f.write_text("def hello():\n    print('hello')\n")

    result = await tool.execute(
        file_path=str(f),
        old_string="completely different content that does not exist anywhere",
        new_string="replacement",
    )
    assert "Error" in result or "Could not find" in result


@pytest.mark.asyncio
async def test_nonexistent_file(tool: EditFileTool):
    result = await tool.execute(
        file_path="/nonexistent/file.txt",
        old_string="old",
        new_string="new",
    )
    assert "Error" in result


@pytest.mark.asyncio
async def test_identical_strings(tool: EditFileTool, tmp_dir: Path):
    f = tmp_dir / "test.txt"
    f.write_text("some content")

    result = await tool.execute(
        file_path=str(f),
        old_string="same",
        new_string="same",
    )
    assert "identical" in result.lower()
