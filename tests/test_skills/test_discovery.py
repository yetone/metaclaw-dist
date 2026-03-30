"""Tests for skill discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from metaclaw.config import SkillsConfig
from metaclaw.skills.discovery import discover_skills


def test_discover_builtin_skills():
    """Built-in skills should always be found."""
    skills = discover_skills(SkillsConfig())
    names = [s.name for s in skills]
    assert "metaclaw-manager" in names
    assert "onboarding" in names
    assert "channel-setup" in names


def test_discover_custom_skills(tmp_dir: Path):
    """Custom skills in search paths should be found."""
    skill_dir = tmp_dir / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""\
---
name: my-skill
description: A custom skill
---

# My Skill
Custom instructions.
""")

    config = SkillsConfig(search_paths=[str(tmp_dir)])
    skills = discover_skills(config)
    names = [s.name for s in skills]
    assert "my-skill" in names
