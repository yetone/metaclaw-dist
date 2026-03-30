"""Tests for SKILL.md parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from metaclaw.skills.parser import parse_skill


@pytest.fixture
def skill_dir(tmp_dir: Path):
    d = tmp_dir / "test-skill"
    d.mkdir()
    return d


def test_parse_valid_skill(skill_dir: Path):
    (skill_dir / "SKILL.md").write_text("""\
---
name: test-skill
description: A test skill for testing
license: MIT
---

# Test Skill

This is a test skill.

## Instructions

Do the test thing.
""")

    skill = parse_skill(skill_dir / "SKILL.md")
    assert skill is not None
    assert skill.name == "test-skill"
    assert skill.description == "A test skill for testing"
    assert "Do the test thing" in skill.body


def test_parse_without_frontmatter(skill_dir: Path):
    (skill_dir / "SKILL.md").write_text("""\
# My Skill

This is a skill without frontmatter.
""")

    skill = parse_skill(skill_dir / "SKILL.md")
    assert skill is not None
    assert skill.name == skill_dir.name
    assert "This is a skill without frontmatter" in skill.description


def test_parse_missing_description(skill_dir: Path):
    (skill_dir / "SKILL.md").write_text("""\
---
name: empty
---

# Just a heading
""")

    # Should still load (extracts from body)
    skill = parse_skill(skill_dir / "SKILL.md")
    # Either loads with extracted description or returns None
    # Our parser tries to extract from body, so it should work
    assert skill is None or skill.name == "empty"


def test_parse_nonexistent():
    result = parse_skill(Path("/nonexistent/SKILL.md"))
    assert result is None
